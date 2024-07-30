""" rectilinear Mesh """

import typing
import functools

import numpy as np

from spdm.utils.tags import _not_found_
from spdm.utils.type_hint import ArrayType, array_type
from spdm.core.function import Function

from spdm.geometry.box import Box, Box2D
from spdm.numlib.interpolate import interpolate
from spdm.mesh.mesh_structured import StructuredMesh


class RectilinearMesh(StructuredMesh, plugin_name=["rectilinear", "rectangular", "rect"]):
    """A `rectilinear Mesh` is a tessellation by rectangles or rectangular cuboids (also known as rectangular
     parallelepipeds)    that are not, in general, all congruent to each other. The cells may still be indexed by
     integers as above, but the mapping from indexes to vertex coordinates is less uniform than in a regular Mesh.
     An example of a rectilinear Mesh that is not regular appears on logarithmic scale graph paper.
    -- [https://en.wikipedia.org/wiki/Regular_Mesh]

    RectlinearMesh

    可以视为由 n=rank 条称为axis的曲线 curve 平移张成的空间。

    xyz= sum([ axis[i](uvw[i]) for i in range(rank) ])

    """

    def __init__(self, *args, **kwargs):
        if len(args) == 1 and isinstance(args[0], dict):
            cache = args[0]
        elif len(args) == 1 and args[0] is _not_found_:
            cache = {}
        else:
            cache = {"dims": args}

        super().__init__(cache, **kwargs)

        if self.dims is _not_found_:
            dims = list(self.get(f"dim{i}", _not_found_) for i in range(10))
            dims = [d for d in dims if d is not _not_found_]
            if len(dims) > 0:
                self._cache["dims"] = tuple(dims)
            else:
                raise RuntimeError(f"dims not found in {self._cache}")
        assert all(d.ndim == 1 for d in self.dims), f"Illegal dims shape! {self.dims}"
        assert all(
            np.all(d[1:] > d[:-1]) for d in self.dims
        ), f"'dims' must be monotonically increasing.! {self.dims}"

        self.shape = tuple([d.size for d in self.dims])

        if len(self.dims) == 2:
            self.geometry = Box2D([min(d) for d in self.dims], [max(d) for d in self.dims])
        else:
            self.geometry = Box([min(d) for d in self.dims], [max(d) for d in self.dims])

        self._aixs = [Function(d, np.linspace(0, 1.0, len(d))) for i, d in enumerate(self.dims)]

    dims: typing.Tuple[ArrayType, ...]

    @functools.cached_property
    def dx(self) -> ArrayType:
        return np.asarray([(d[-1] - d[0]) / len(d) for d in self.dims])

    @property
    def coordinates(self) -> typing.Tuple[ArrayType, ...]:
        return tuple(np.meshgrid(*self.dims, indexing="ij"))

    def interpolate(self, func: ArrayType | typing.Callable[..., array_type], **kwargs):
        """生成插值器
        method: "linear",   "nearest", "slinear", "cubic", "quintic" and "pchip"
        """
        if callable(func):
            value = func(*self.coordinates)
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

        return interpolate(*self.dims, value, periods=self.periods, **kwargs)
