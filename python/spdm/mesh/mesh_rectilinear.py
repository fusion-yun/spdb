import collections
import collections.abc
import typing
from functools import cached_property

import numpy as np

from spdm.utils.logger import logger
from spdm.utils.tags import _not_found_
from spdm.utils.type_hint import ArrayType, NumericType, ScalarType, array_type, numeric_type, scalar_type
from spdm.core.path import Path
from spdm.core.function import Function
from spdm.core.sp_tree import sp_property
from spdm.core.geo_object import BBox, GeoObject

from spdm.geometry.box import Box
from spdm.geometry.curve import Curve
from spdm.geometry.line import Line
from spdm.geometry.point import Point
from spdm.numlib.interpolate import interpolate

from spdm.core.mesh import Mesh

from spdm.mesh.mesh_structured import StructuredMesh


class RectilinearMesh(StructuredMesh, plugin_name=["rectilinear", "rectangular", "rect"]):
    """A `rectilinear Mesh` is a tessellation by rectangles or rectangular cuboids (also known as rectangular parallelepipeds)
    that are not, in general, all congruent to each other. The cells may still be indexed by integers as above, but the
    mapping from indexes to vertex coordinates is less uniform than in a regular Mesh. An example of a rectilinear Mesh
    that is not regular appears on logarithmic scale graph paper.
    -- [https://en.wikipedia.org/wiki/Regular_Mesh]

    RectlinearMesh

    可以视为由 n=rank 条称为axis的曲线 curve 平移张成的空间。

    xyz= sum([ axis[i](uvw[i]) for i in range(rank) ])

    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if self.dims is _not_found_:
            dims = list(self.get(f"dim{i}", _not_found_) for i in range(10))
            dims = [d for d in dims if d is not _not_found_]
            if len(dims) > 0:
                self._cache["dims"] = tuple(dims)
            else:
                raise RuntimeError(f"dims not found in {self._cache}")

        assert all(d.ndim == 1 for d in self.dims), f"Illegal dims shape! {self.dims}"
        assert all(np.all(d[1:] > d[:-1]) for d in self.dims), f"'dims' must be monotonically increasing.! {self.dims}"

        if self.geometry is _not_found_:
            self._cache["geometry"] = Box([min(d) for d in self.dims], [max(d) for d in self.dims])

        self._aixs = [Function(d, np.linspace(0, 1.0, len(d))) for i, d in enumerate(self.dims)]

    dims: typing.Tuple[ArrayType, ...]

    dim1: ArrayType = sp_property(alias="dims/0")

    dim2: ArrayType = sp_property(alias="dims/1")

    @cached_property
    def dx(self) -> ArrayType:
        return np.asarray([(d[-1] - d[0]) / len(d) for d in self.dims])

    def coordinates(self, *uvw) -> ArrayType:
        """网格点的 _空间坐标_
        @return: _数组_ 形状为 [geometry.dimension,<shape of uvw ...>]
        """
        if len(uvw) == 1 and self.rank != 1:
            uvw = uvw[0]
        return np.stack([self.dims[i](uvw[i]) for i in range(self.rank)], axis=-1)

    @cached_property
    def vertices(self) -> ArrayType:
        """网格点的 _空间坐标_"""
        if self.geometry.rank == 1:
            return (self.dims[0],)
        else:
            return np.stack(self.points, axis=-1)

    @cached_property
    def points(self) -> typing.List[ArrayType]:
        """网格点的 _空间坐标_"""
        if self.geometry.rank == 1:
            return (self.dims[0],)
        else:
            return np.meshgrid(*self.dims, indexing="ij")

    def interpolate(self, func: ArrayType | typing.Callable[..., array_type], **kwargs):
        """生成插值器
        method: "linear",   "nearest", "slinear", "cubic", "quintic" and "pchip"
        """
        if callable(func):
            value = func(*self.points)
        elif not isinstance(func, np.ndarray):
            value = getattr(func, "_cache", None)
        else:
            value = func

        if not isinstance(value, np.ndarray):
            raise ValueError(f"value must be np.ndarray, but {type(value)} {value}")

        elif tuple(value.shape) != tuple(self.shape):
            raise NotImplementedError(f"{func.shape}!={self.shape}")

        if np.any(tuple(value.shape) != tuple(self.shape)):
            raise ValueError(f"{value} {self.shape}")

        return interpolate(*self._dims, value, periods=self._periods, **kwargs)
