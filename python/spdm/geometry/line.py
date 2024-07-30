import collections.abc
import typing
from functools import cached_property

import numpy as np

from spdm.utils.type_hint import ArrayType
from spdm.core.sp_tree import annotation
from spdm.core.geo_object import GeoObject
from spdm.geometry.point import Point
from spdm.geometry.vector import Vector


class Line(GeoObject, plugin_name="line", rank=1):
    """Line
    线，一维几何体
    """

    p0: Point = annotation(alias="points/0")

    p1: Point = annotation(alias="points/1")

    length: float = annotation(alias="measure")

    @property
    def measure(self) -> float:
        return np.Inf

    @property
    def direction(self) -> Vector:
        return Vector(self.p1 - self.p0)

    @property
    def boundary(self) -> typing.List[Point]:
        return [self.p0, self.p1]

    def contains(self, o) -> bool:
        return self._impl.contains(o._impl if isinstance(o, GeoObject) else o)

    def coordinates(self, u: float | np.ndarray | typing.List[np.ndarray] | None = None) -> ArrayType:
        direction = self.direction
        if u is None:
            return [self.p0, self.p1]
        elif isinstance(u, float):
            return self.p0 + self.direction * u
        elif isinstance(u, np.ndarray):
            return np.asarray([(self.p0 + self.direction * v)[:] for v in u])
        elif isinstance(u, collections.abc.Iterable):
            return np.asarray([(self.p0 + direction * v) for v in u])
        else:
            raise RuntimeError(f"Invalid input type {type(u)}")

    def project(self, o) -> Point:
        return Point(self._impl.projection(o._impl if isinstance(o, GeoObject) else o))

    def bisectors(self, o) -> typing.List[GeoObject]:
        return [GeoObject(v) for v in self._impl.bisectors(o._impl if isinstance(o, GeoObject) else o)]

    @cached_property
    def dl(self) -> np.ndarray:
        x, y = np.moveaxis(self.points, -1, 0)

        a, b = self.derivative()

        # a = a[:-1]
        # b = b[:-1]
        dx = x[1:] - x[:-1]
        dy = y[1:] - y[:-1]

        m1 = (-a[:-1] * dy + b[:-1] * dx) / (a[:-1] * dx + b[:-1] * dy)

        # a = np.roll(a, 1, axis=0)
        # b = np.roll(b, 1, axis=0)

        m2 = (-a[1:] * dy + b[1:] * dx) / (a[1:] * dx + b[1:] * dy)

        return np.sqrt(dx**2 + dy**2) * (1 + (2.0 * m1**2 + 2.0 * m2**2 - m1 * m2) / 30)

    def integral(self, func: typing.Callable) -> float:
        x, y = self.xyz
        val = func(x, y)
        # c_pts = self.points((self._mesh[0][1:] + self._mesh[0][:-1])*0.5)

        return np.sum(0.5 * (val[:-1] + val[1:]) * self.dl)

    # def average(self, func: Callable[[_TCoord, _TCoord], _TCoord]) -> float:
    #     return self.integral(func)/self.length

    def encloses_point(self, *x: float, **kwargs) -> bool:
        return super().enclosed(**x, **kwargs)

    def trim(self):
        return NotImplemented


class Ray(Line, plugin_name="ray"):
    pass


class Segment(Line, plugin_name="segment"):
    @property
    def midpoint(self) -> Point:
        return Point((self.p0 + self.p1) * 0.5)
