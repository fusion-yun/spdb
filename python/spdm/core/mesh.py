import collections.abc
import typing
import abc
from functools import cache
from enum import Enum

import numpy as np
import numpy.typing as np_tp

from spdm.utils.logger import logger
from spdm.utils.type_hint import ArrayType, NumericType, ScalarType, as_array, array_type
from spdm.utils.tags import _not_found_
from spdm.utils.misc import group_dict_by_prefix

from spdm.core.domain import Domain
from spdm.core.path import Path
from spdm.core.sp_tree import annotation

from spdm.geometry.vector import Vector

from spdm.numlib.numeric import float_nan, bitwise_and
from spdm.numlib.interpolate import interpolate

# from spdm.numlib.numeric import float_nan, meshgrid, bitwise_and


def guess_mesh(holder, prefix="mesh", **kwargs):
    if holder is None or holder is _not_found_:
        return None

    metadata = getattr(holder, "_metadata", {})

    mesh, *_ = group_dict_by_prefix(metadata, prefix, sep=None)

    if mesh is None:
        coordinates, *_ = group_dict_by_prefix(metadata, "coordinate", sep=None)

        if coordinates is not None:
            coordinates = {int(k): v for k, v in coordinates.items() if k.isdigit()}
            coordinates = dict(sorted(coordinates.items(), key=lambda x: x[0]))
            coordinates = [Path(c).find(holder) for c in coordinates.values()]
            if all([isinstance(c, array_type) for c in coordinates]):
                mesh = {"dims": coordinates}

    elif isinstance(mesh, str) and mesh.isidentifier():
        mesh = getattr(holder, mesh, _not_found_)
    elif isinstance(mesh, str):
        mesh = Path(mesh).get(holder, _not_found_)
    elif isinstance(mesh, Enum):
        mesh = {"type": mesh.name}

    elif isinstance(mesh, collections.abc.Sequence) and all(isinstance(d, array_type) for d in mesh):
        mesh = {"dims": mesh}

    elif isinstance(mesh, collections.abc.Mapping):
        pass

    if mesh is None or mesh is _not_found_:
        return guess_mesh(getattr(holder, "_parent", None), prefix=prefix, **kwargs)
    else:
        return mesh

    # if all([isinstance(c, str) and c.startswith("../grid") for c in coordinates.values()]):
    #     o_mesh = getattr(holder, "grid", None)
    #     if isinstance(o_mesh, Mesh):
    #         # if self._mesh is not None and len(self._mesh) > 0:
    #         #     logger.warning(f"Ignore {self._mesh}")
    #         self._domain = o_mesh
    #     elif isinstance(o_mesh, collections.abc.Sequence):
    #         self._domain = update_tree_recursive(self._domain, {"dims": o_mesh})
    #     elif isinstance(o_mesh, collections.abc.Mapping):
    #         self._domain = update_tree_recursive(self._domain, o_mesh)
    #     elif o_mesh is not None:
    #         raise RuntimeError(f"holder.grid is not a Mesh, but {type(o_mesh)}")
    # else:
    #     dims = tuple([(holder.get(c) if isinstance(c, str) else c) for c in coordinates.values()])
    #     self._domain = update_tree_recursive(self._domain, {"dims": dims})


class Mesh(Domain, plugin_prefix="spdm.mesh.mesh_"):
    """Mesh  网格

    @NOTE: In general, a mesh provides more flexibility in representing complex geometries and
    can adapt to the local features of the solution, while a grid is simpler to generate
    and can be more efficient for certain types of problems.
    """

    _plugin_registry = {}

    @property
    def axis_label(self) -> typing.Tuple[str, ...]:
        return self._metadata.get("axis_label", ["[-]"] * self.ndim)

    shape: Vector[int]
    """
        存储网格点数组的形状
        结构化网格 shape   如 [n,m] n,m 为网格的长度dimension
        非结构化网格 shape 如 [<number of vertices>]
    """

    @property
    @abc.abstractmethod
    def points(self) -> array_type:
        """网格点的 _空间坐标_  形状为 [...shape,ndim]"""

    @property
    def coordinates(self) -> typing.Tuple[ArrayType, ...]:
        return tuple([self.points[..., i] for i in range(self.ndim)])

    @property
    def cells(self) -> typing.Any:
        """refer to the individual units that make up the mesh"""
        raise NotImplementedError(f"{self.__class__.__name__}.cells")

    def interpolate(self, func: typing.Callable | ArrayType, *args, **kwargs) -> typing.Callable[..., ArrayType]:
        xargs = self.coordinates
        if callable(func):
            value = func(*xargs)
        elif isinstance(func, array_type):
            value = func
        else:
            raise TypeError(f"{type(func)} is not array or callable!")

        return interpolate(*xargs, value)

    def mask(self, *args) -> bool | np_tp.NDArray[np.bool_]:
        # or self._metadata.get("extrapolate", 0) != 1:
        if self.shape is None or len(self.shape) == 0 or self._metadata.get("extrapolate", 0) != "raise":
            return True

        if len(args) != len(self.shape):
            raise RuntimeError(f"len(args) != len(self.dims) {len(args)}!={len(self.shape)}")

        v = []
        for i, (xmin, xmax) in enumerate(self.geometry.bbox):
            v.append((args[i] >= xmin) & (args[i] <= xmax))

        return bitwise_and.reduce(v)

    def check(self, *x) -> bool | np_tp.NDArray[np.bool_]:
        """当坐标在定义域内时返回 True，否则返回 False"""

        d = [child.__check_domain__(*x) for child in self._children if hasattr(child, "__domain__")]

        if isinstance(self._func, Functor):
            d += [self._func.__domain__(*x)]

        d = [v for v in d if (v is not None and v is not True)]

        if len(d) > 0:
            return np.bitwise_and.reduce(d)
        else:
            return True

    def eval(self, func, *xargs, **kwargs):
        """根据 __domain__ 函数的返回值，对输入坐标进行筛选"""

        mask = self.mask(*xargs)

        mask_size = mask.size if isinstance(mask, array_type) else 1
        masked_num = np.sum(mask)

        if not isinstance(mask, array_type) and not isinstance(mask, (bool, np.bool_)):
            raise RuntimeError(f"Illegal mask {mask} {type(mask)}")

        if masked_num == 0:
            raise RuntimeError(f"Out of domain! {self} {xargs} ")

        if masked_num < mask_size:
            xargs = tuple(
                (arg[mask] if isinstance(mask, array_type) and isinstance(arg, array_type) and arg.ndim > 0 else arg)
                for arg in xargs
            )
        else:
            mask = None

        value = func._eval(*xargs, **kwargs)

        if masked_num < mask_size:
            res = value
        elif is_scalar(value):
            res = np.full_like(mask, value, dtype=self._type_hint())
        elif isinstance(value, array_type) and value.shape == mask.shape:
            res = value
        elif value is None:
            res = None
        else:
            res = np.full_like(mask, self.fill_value, dtype=self._type_hint())
            res[mask] = value
        return res

    def partial_derivative(self, order, y: NumericType, *args, **kwargs) -> typing.Callable[..., NumericType]:
        raise NotImplementedError(f"{self.__class__.__name__}.partial_derivative")

    def antiderivative(self, y: NumericType, *args, **kwargs) -> typing.Callable[..., NumericType]:
        raise NotImplementedError(f"{self.__class__.__name__}.antiderivative")

    def integrate(self, y: NumericType, *args, **kwargs) -> ScalarType:
        raise NotImplementedError(f"{self.__class__.__name__}.integrate")

    def view(self, obj, view_point="rz", label=None, **kwargs):
        """将 obj 画在 domain 上，默认为 n维 contour。"""

        # view_point = ("RZ",)
        geo = {"$type": "contour"}

        match view_point.lower():
            case "rz":
                geo["$data"] = (*self.coordinates, np.asarray(obj))
                geo["$styles"] = {
                    "label": label,
                    "axis_label": self.axis_label,
                    "$matplotlib": {"levels": 40, "cmap": "jet"},
                    **kwargs,
                }
        return geo


class NullMesh(Mesh, plugin_name=["null"]):
    def __init__(self, *args, **kwargs) -> None:
        if len(args) > 0 or len(kwargs) > 0:
            raise RuntimeError(f"Ignore args {args} and kwargs {kwargs}")
        super().__init__()


def as_mesh(*args, **kwargs) -> Mesh:
    if len(args) == 1 and isinstance(args[0], Mesh):
        return args[0]
    else:
        return Mesh(*args, **kwargs)
