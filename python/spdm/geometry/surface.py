from __future__ import annotations

import functools
import typing
from copy import copy
import numpy as np

from ..utils.logger import logger
from ..utils.typing import (ArrayLike, ArrayType, NumericType, array_type,
                            nTupleType)
from ..core.geo_object import GeoObject,BBox
from .point_set import PointSet
from .curve import Curve
from .line import Segment


class Surface(PointSet):
    """ Surface """

    def __init__(self, *args, uv=None, **kwargs) -> None:
        super().__init__(*args, rank=2, **kwargs)
        self._edges: array_type = None
        self._cell: array_type = None
        self._uv = uv

    def enclose(self, *args) -> bool:
        if not self.is_closed:
            return False
        return super().enclose(*args)

    @property
    def boundary(self) -> Curve: return Curve(super().boundary, is_closed=True)

    @functools.cached_property
    def measure(self) -> float: return np.sum(self.dl)

    def coordinates(self, *uvw) -> ArrayType: raise NotImplementedError(f"{self.__class__.__name__}.coordinates")

    def derivative(self, *args, **kwargs): raise NotImplementedError(f"{self.__class__.__name__}.derivative")

    def remesh(self, u) -> Surface:
        other: Surface = copy(self)
        if isinstance(u, array_type):
            other._uv = u
        elif callable(u):
            other._uv = u(*self.points)
        else:
            raise TypeError(f"illegal type u={type(u)}")
        return other

    @property
    def edges(self) -> typing.Generator[Segment, None, None]:
        if self._points.ndim != 2:
            raise NotImplementedError(f"{self.__class__.__name__}.edges for ndim!=2")
        elif self._edges is None:
            for idx in range(self._points.shape[0]-1):
                yield Segment(self._points[idx], self._points[idx+1])
        elif isinstance(self._edges, array_type):
            for b, e in self._edges:
                yield Segment(self._points[b], self._points[e])
        else:
            raise NotImplementedError()
