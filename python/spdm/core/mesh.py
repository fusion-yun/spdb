from __future__ import annotations

import abc
import collections.abc
import typing
import numpy as np
from functools import cached_property
from enum import Enum

from .geo_object import GeoObject, as_geo_object
from .domain import Domain
from .path import update_tree
from ..utils.typing import ArrayType, NumericType, ScalarType, as_array
from ..utils.tags import _not_found_
from ..utils.misc import group_dict_by_prefix
from ..utils.logger import logger
from .path import update_tree, Path
from ..numlib.numeric import float_nan, meshgrid, bitwise_and


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
            if all([is_array(c) for c in coordinates]):
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


class Mesh(Domain):
    """Mesh  网格

    @NOTE: In general, a mesh provides more flexibility in representing complex geometries and
    can adapt to the local features of the solution, while a grid is simpler to generate
    and can be more efficient for certain types of problems.
    """

    _plugin_registry = {}
    _plugin_prefix = "spdm.mesh.mesh_"

    @classmethod
    def _guess_mesh(cls, *args, **kwargs) -> dict:
        if len(args) > 0 and isinstance(args[0], collections.abc.Mapping):
            desc = collections.ChainMap(args[0], kwargs)
            if len(args) > 1:
                logger.warning(f"ignore args {args[1:]}")
        else:
            desc = kwargs

        mesh_type = desc.get("@type", None) or desc.get("type", None)

        # 当没有明确指定 mesh_type 时，根据 dims 猜测 mesh_type
        dims = desc.get("dims", None)
        if dims is not None:
            pass
        elif all([isinstance(d, np.ndarray) for d in args]):
            dims = args
            desc["dims"] = dims
        else:
            dims, desc = group_dict_by_prefix(desc, prefixes="dim", sep=None)
            if isinstance(dims, dict):
                dims = {int(k): v for k, v in dims.items() if k.isdigit()}
                dims = dict(sorted(dims.items(), key=lambda x: x[0]))
                dims = tuple([as_array(d) for d in dims.values()])
                desc["dims"] = dims

        if mesh_type is None and dims is not None and all([isinstance(a, np.ndarray) for a in dims]):
            ndim = len(dims)
            if all([d.ndim == 1 for d in dims]):
                desc["@type"] = "rectilinear"
            elif all([d.ndim == ndim for d in dims]):
                desc["@type"] = "curvilinear"

        return desc

    def __new__(cls, *args, **kwargs) -> typing.Type[typing.Self]:
        if cls is not Mesh:
            return super().__new__(cls, *args, **kwargs)

        desc = cls._guess_mesh(*args, **kwargs)

        mesh_type = desc.get("$type", None) or desc.get("@type", None) or desc.get("type", None)

        if not isinstance(mesh_type, str):
            raise RuntimeError(f"Unable to determine mesh type! {desc} ")

        return super().__new__(cls, mesh_type)

    def __init__(self, *args, **kwargs) -> None:
        """
        Usage:
            Mesh(x,y) => Mesh(type="structured",dims=(x,y),**kwargs)
        """
        desc = self.__class__._guess_mesh(*args, **kwargs)
        geometry = desc.pop("geometry", None)
        super().__init__(desc, geometry=geometry)

    @property
    def axis_label(self) -> typing.Tuple[str]:
        return self._metadata.get("axis_label", ["[-]"] * self.ndim)

    @property
    @abc.abstractmethod
    def shape(self) -> typing.Tuple[int, ...]:
        """
        存储网格点数组的形状
        TODO: support multiblock Mesh
        结构化网格 shape   如 [n,m] n,m 为网格的长度dimension
        非结构化网格 shape 如 [<number of vertices>]
        """
        pass

    def parametric_coordinates(self, *xyz) -> ArrayType:
        """parametric coordinates

        网格点的 _参数坐标_
        Parametric coordinates, also known as computational coordinates or intrinsic coordinates,
        are a way to represent the position of a point within an element of a mesh.
        一般记作 u,v,w \in [0,1] ,其中 0 表示“起点”或 “原点” origin，1 表示终点end
        mesh的参数坐标(u,v,w)，(...,0)和(...,1)表示边界

        @return: 数组形状为 [geometry.rank, <shape of xyz ...>]的数组
        """
        if len(xyz) == 0:
            return np.stack(np.meshgrid(*[np.linspace(0.0, 1.0, n, endpoint=True) for n in self.shape]))
        else:
            raise NotImplementedError(f"{self.__class__.__name__}.parametric_coordinates for unstructured mesh")

    def coordinates(self, *uvw) -> ArrayType:
        """网格点的 _空间坐标_
        @return: _数组_ 形状为 [<shape of uvw ...>,geometry.ndim]
        """
        return self.geometry.coordinates(uvw if len(uvw) > 0 else self.parametric_coordinates())

    def uvw(self) -> ArrayType:
        return self.parametric_coordinates(*xyz)
        """ alias of parametric_coordiantes"""

    @cached_property
    def vertices(self) -> ArrayType:
        """coordinates of vertice of mesh  [<shape...>, geometry.ndim]"""
        return self.geometry.coordinates(self.parametric_coordinates())

    @cached_property
    def points(self) -> typing.List[ArrayType]:
        """alias of vertices, change the shape to tuple"""
        return [self.vertices[..., idx] for idx in range(self.ndim)]

    @cached_property
    def xyz(self) -> typing.List[ArrayType]:
        return self.points

    @property
    def cells(self) -> typing.Any:
        raise NotImplementedError(f"{self.__class__.__name__}.cells")

    """ refer to the individual units that make up the mesh"""

    def interpolator(self, y: NumericType, *args, **kwargs) -> typing.Callable[..., NumericType]:
        raise NotImplementedError(f"{self.__class__.__name__}.interpolator")

    def partial_derivative(self, order, y: NumericType, *args, **kwargs) -> typing.Callable[..., NumericType]:
        raise NotImplementedError(f"{self.__class__.__name__}.partial_derivative")

    def antiderivative(self, y: NumericType, *args, **kwargs) -> typing.Callable[..., NumericType]:
        raise NotImplementedError(f"{self.__class__.__name__}.antiderivative")

    def integrate(self, y: NumericType, *args, **kwargs) -> ScalarType:
        raise NotImplementedError(f"{self.__class__.__name__}.integrate")

    def eval(self, func, *args, **kwargs) -> ArrayType:
        return func(*self.points)

    def display(self, obj, *args, view_point="rz", label=None, **kwargs):
        # view_point = ("RZ",)
        geo = {}

        match view_point.lower():
            case "rz":
                geo["$data"] = (*self.points, obj.__array__())
                geo["$styles"] = {
                    "label": label,
                    "axis_label": self.axis_label,
                    "$matplotlib": {"levels": 40, "cmap": "jet"},
                }
        return geo


@Mesh.register(["null", None])
class NullMesh(Mesh):
    def __init__(self, *args, **kwargs) -> None:
        if len(args) > 0 or len(kwargs) > 0:
            raise RuntimeError(f"Ignore args {args} and kwargs {kwargs}")
        super().__init__()


@Mesh.register("regular")
class RegularMesh(Mesh):
    pass


def as_mesh(*args, **kwargs) -> Mesh:
    if len(args) == 1 and isinstance(args[0], Mesh):
        if len(kwargs) > 0:
            logger.warning(f"Ignore kwargs {kwargs}")
        return args[0]
    else:
        return Mesh(*args, **kwargs)
