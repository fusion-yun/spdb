
from __future__ import annotations

import collections
import collections.abc
import typing
from copy import copy
from functools import cached_property

import numpy as np
import scipy.constants
from scipy.interpolate import CubicSpline, PPoly
from spdm.geometry.GeoObject import GeoObject

from ..utils.logger import logger
from ..utils.typing import ArrayType, array_type, nTupleType

from .curve import Curve

TWOPI = 2.0*scipy.constants.pi


@Curve.register("cubic_spline_curve")
class CubicSplineCurve(Curve):
    def __init__(self, *args, uv=None,  **kwargs) -> None:

        super().__init__(*args, **kwargs)
        self._points = points
        self._uv = uv if uv is None else np.linspace(0, 1, self._points.shape[0])

    def __copy__(self) -> CubicSplineCurve:
        other: CubicSplineCurve = super().__copy__()  # type:ignore
        other._points = self._points
        other._uv = self._uv
        return other



    def coordinates(self, *uvw, **kwargs) -> ArrayType:
        if len(uvw) == 0:
            return self._points
        else:
            return self._spl(*uvw, **kwargs)

    @cached_property
    def _spl(self) -> PPoly:
        return CubicSpline(self._uv, self._points, bc_type="periodic" if self.is_closed else "not-a-knot")

    @cached_property
    def _derivative(self):
        return self._spl.derivative()

    def derivative(self, *args, **kwargs):
        if len(args) == 0:
            args = [self._uv]
        res = self._derivative(*args, **kwargs)
        return res[:, 0], res[:, 1]

    @cached_property
    def bbox(self) -> BBox:
        """ bbox of geometry """
        points = self._points
        return BBox([np.min(x) for x in points], [np.max(x) for x in points])

    def enclose(self, *args) -> bool:
        if not self.is_closed:
            return False
        return super().enclose(*args)

    def remesh(self, u) -> CubicSplineCurve:
        other = copy(self)
        if isinstance(u, array_type):
            other._uv = u
        elif callable(u):
            other._uv = u(*self.points)
        else:
            raise TypeError(f"illegal type u={type(u)}")
        return other
