from __future__ import annotations

from copy import copy, deepcopy
import collections.abc
import functools
import typing
from enum import Enum
import numpy as np
import numpy.typing as np_tp

from spdm.core.typing import array_type

from .domain import DomainBase
from ..mesh.mesh import Mesh
from ..utils.logger import logger
from ..utils.misc import group_dict_by_prefix
from ..utils.tags import _not_found_
from .typing import ArrayType, array_type, as_array, is_array
from ..numlib.numeric import float_nan, meshgrid, bitwise_and

from .expression import Expression
from .functor import Functor
from .path import update_tree, Path


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


class Field(Expression):
    """Field

    Field 是 Function 在流形（manifold/Mesh）上的推广， 用于描述流形上的标量场，矢量场，张量场等。

    Field 所在的流形记为 mesh ，可以是任意维度的，可以是任意形状的，可以是任意拓扑的，可以是任意坐标系的。

    Mesh 网格描述流形的几何结构，比如网格的拓扑结构，网格的几何结构，网格的坐标系等。

    Field 与 Function的区别：
        - Function 的 mesh 是一维数组表示dimensions/axis
        - Field 的 mesh 是 Mesh，可以表示复杂流形上的场等。
    """

    Domain = Mesh

    def __init__(self, *xy, **kwargs):
        mesh, kwargs = group_dict_by_prefix(kwargs, prefixes="mesh")

        super().__init__(None, **kwargs)

        if len(xy) == 0:
            raise RuntimeError(f"illegal x,y {xy} ")

        value = xy[-1]

        dims = xy[:-1]

        if isinstance(value, (Functor, Expression)) or callable(value):
            func = value
            value = None
        else:
            func = None
            value = as_array(value)

        if mesh is not None:
            if len(dims) == 0:
                pass
            elif isinstance(mesh, dict):
                mesh["dims"] = dims
            else:
                raise RuntimeError(f"'mesh' is defined, ignore dims={dims} {mesh}")

        elif "domain" in kwargs:
            mesh = kwargs["domain"]
            if len(dims) > 0:
                raise RuntimeError(f"'mesh' is defined, ignore dims={dims}")
        else:
            mesh = dims

        self._op = func
        self._mesh = mesh
        self._cache = value
        self._ppoly = None

    def __geometry__(self, view_point="RZ", **kwargs):
        """
        plot o-point,x-point,lcfs,separatrix and contour of psi
        """

        geo = {}

        match view_point.lower():
            case "rz":
                geo["$data"] = (*self.mesh.points, self.__array__())
                geo["$styles"] = {
                    "label": self.__label__,
                    "axis_label": self.mesh.axis_label,
                    "$matplotlib": {"levels": 40, "cmap": "jet"},
                }
        return geo

    def _repr_svg_(self) -> str:
        from ..view.View import display

        return display(self.__geometry__(), output="svg")

    @property
    def mesh(self) -> Mesh:
        if isinstance(self._mesh, Mesh):
            return self._mesh

        if self._mesh is None or self._mesh is _not_found_ or len(self._mesh) == 0:
            self._mesh = guess_mesh(self, prefix="mesh")

        if not isinstance(self._mesh, Mesh):
            mesh_desc, *_ = group_dict_by_prefix(self._metadata, prefixes="mesh", sep="_")
            self._mesh = Mesh(self._mesh, parent=self, **(mesh_desc or {}))

        return self._mesh

    @property
    def domain(self) -> DomainBase:
        return self.mesh

    def __call__(self, *args, **kwargs) -> typing.Callable[..., ArrayType]:
        if all([isinstance(a, (array_type, float, int)) for a in args]):
            return self.__ppoly__()(*args, **kwargs)
        else:
            return super().__call__(*args, **kwargs)

    def grad(self, n=1) -> Field:
        ppoly = self.__functor__()

        if isinstance(ppoly, tuple):
            ppoly, opts = ppoly
        else:
            opts = {}

        if self.mesh.ndim == 2 and n == 1:
            return Field(
                (ppoly.partial_derivative(1, 0), ppoly.partial_derivative(0, 1)),
                mesh=self.mesh,
                name=f"\\nabla({self.__str__()})",
                **opts,
            )
        elif self.mesh.ndim == 3 and n == 1:
            return Field(
                (
                    ppoly.partial_derivative(1, 0, 0),
                    ppoly.partial_derivative(0, 1, 0),
                    ppoly.partial_derivative(0, 0, 1),
                ),
                mesh=self.mesh,
                name=f"\\nabla({self.__str__()})",
                **opts,
            )
        elif self.mesh.ndim == 2 and n == 2:
            return Field(
                (ppoly.partial_derivative(2, 0), ppoly.partial_derivative(0, 2), ppoly.partial_derivative(1, 1)),
                mesh=self.mesh,
                name=f"\\nabla^{n}({self.__str__()})",
                **opts,
            )
        else:
            raise NotImplemented(f"TODO: ndim={self.mesh.ndim} n={n}")

    def __array__(self) -> array_type:
        if self._cache is None or self._cache is _not_found_:
            if self._op is None:
                raise RuntimeError(f"op is not defined!")
            x = self.domain.points
            if len(x) == 0:
                raise RuntimeError(f"Domain is not defined!")
            
            self._cache = self._op(*x)
            
        return self._cache

    def __ppoly__(self):
        if self._ppoly is None:
            self._ppoly = self.domain.interpolate(self.__array__())
        return self._ppoly

    def derivative(self, order, *args, **kwargs) -> Field:
        if isinstance(order, int) and order < 0:
            func = self.__ppoly__().antiderivative(*order)
            return Field(func, mesh=self.mesh, label=f"I_{{{order}}}{{{self._render_latex_()}}}")
        elif isinstance(order, collections.abc.Sequence):
            func = self.__ppoly__().partial_derivative(*order)
            return Field(func, mesh=self.mesh, label=f"d_{{{order}}}{{{self._render_latex_()}}}")
        else:
            func = self.__ppoly__().derivative(order)
            return Field(func, mesh=self.mesh, label=f"d_{{{order}}}{{{self._render_latex_()}}}")

    def antiderivative(self, order: int, *args, **kwargs) -> Field:
        raise NotImplementedError(f"")

    def partial_derivative(self, order: typing.Tuple[int, ...], *args, **kwargs) -> Field:
        return self.derivative(order, *args, **kwargs)
