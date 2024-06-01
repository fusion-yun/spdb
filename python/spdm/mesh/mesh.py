from __future__ import annotations

import collections.abc
import typing
import numpy as np
from functools import cached_property
from enum import Enum

from ..geometry.geo_object import GeoObject,  as_geo_object
from ..core.domain import DomainBase
from ..core.path import update_tree
from ..core.typing import ArrayType, NumericType, ScalarType, as_array
from ..utils.tags import _not_found_
from ..utils.logger import logger


class Mesh(DomainBase):
    """Mesh  网格

    @NOTE: In general, a mesh provides more flexibility in representing complex geometries and
    can adapt to the local features of the solution, while a grid is simpler to generate
    and can be more efficient for certain types of problems.
    """

    _plugin_registry = {}
    _plugin_prefix = "spdm.mesh.mesh_"

    def __new__(cls, *args, **kwargs) -> typing.Type[typing.Self]:
        if cls is not Mesh:
            return super().__new__(cls)
        else:
            mesh_type = kwargs.pop("type", None)
            if mesh_type is None and len(args) > 0 and isinstance(args[0], dict):
                mesh_type = args[0].get("@type", None)

            if isinstance(mesh_type, Enum):
                mesh_type = mesh_type.name

            if mesh_type is _not_found_ or mesh_type is None or not mesh_type:
                raise ModuleNotFoundError(f"Can not determind the mesh type! {args},{kwargs}")

            return super().__new__(cls, mesh_type)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    @property
    def axis_label(self) -> typing.Tuple[str]:
        return self._metadata.get("axis_label", ["[-]"] * self.ndim)

    @property
    def shape(self) -> typing.Tuple[int, ...]:
        """
        存储网格点数组的形状
        TODO: support multiblock Mesh
        结构化网格 shape   如 [n,m] n,m 为网格的长度dimension
        非结构化网格 shape 如 [<number of vertices>]
        """
        return self._shape

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
