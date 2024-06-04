from __future__ import annotations

import collections.abc
import functools
import typing
from copy import copy

import numpy as np
import scipy.constants
from scipy.interpolate import CubicSpline, PPoly

from ..utils.logger import logger
from ..utils.typing import (ArrayLike, ArrayType, NumericType, array_type,
                            nTupleType)

from ..core.geo_object import GeoObject,BBox
from .point_set import PointSet


@GeoObject.register(["curve", "Curve"])
class Curve(PointSet):
    """ Curve
        曲线，一维几何体
    """

    def __init__(self, *args, uv=None, **kwargs) -> None:
        super().__init__(*args, rank=1, ** kwargs)
        self._metadata["closed"] = np.allclose(self._points[0], self._points[-1])
        self._uv = uv if uv is not None else np.linspace(0, 1.0, self._points.shape[0])

    def __copy__(self) -> Curve:
        other: Curve = super().__copy__()  # type:ignore
        other._uv = self._uv
        return other

    @functools.cached_property
    def dl(self) -> array_type:
        x, y = self.points
        a, b = self.derivative()

        # a = a[:-1]
        # b = b[:-1]
        dx = x[1:]-x[:-1]
        dy = y[1:]-y[:-1]

        m1 = (-a[:-1]*dy+b[:-1]*dx)/(a[:-1]*dx+b[:-1]*dy)

        # a = np.roll(a, 1, axis=0)
        # b = np.roll(b, 1, axis=0)

        m2 = (-a[1:]*dy+b[1:]*dx)/(a[1:]*dx+b[1:]*dy)

        return np.sqrt(dx**2+dy**2)*(1 + (2.0*m1**2+2.0*m2**2-m1*m2)/30)

    @functools.cached_property
    def measure(self) -> float: return np.sum(self.dl)

    def integral(self, func: typing.Callable) -> float:
        x, y = self.points
        val = func(x, y)

        # c_pts = self.points((self._mesh[0][1:] + self._mesh[0][:-1])*0.5)

        return np.sum(0.5*(val[:-1]+val[1:]) * self.dl)

    def coordinates(self, *uvw, **kwargs) -> ArrayType:
        if len(uvw) == 0:
            return self._points
        else:
            return self._spl(*uvw, **kwargs)

    @functools.cached_property
    def _spl(self) -> PPoly:
        return CubicSpline(self._uv, self._points, bc_type="periodic" if self.is_closed else "not-a-knot")

    @functools.cached_property
    def _derivative(self):
        return self._spl.derivative()

    def derivative(self, *args, **kwargs):
        if len(args) == 0:
            args = [self._uv]
        res = self._derivative(*args, **kwargs)
        return res[:, 0], res[:, 1]

    def enclose(self, *args) -> bool:
        if not self.is_closed:
            return False
        return super().enclose(*args)

    def remesh(self, u) -> Curve:
        other: Curve = copy(self)
        if isinstance(u, array_type):
            other._uv = u
        elif callable(u):
            other._uv = u(*self.points)
        else:
            raise TypeError(f"illegal type u={type(u)}")
        return other
