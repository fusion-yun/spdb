import collections.abc
import typing

import numpy as np

from ..utils.typing import ArrayType

from ..core.geo_object import GeoObject,BBox
from .line import Segment
from .point import Point
from .point_set import PointSet
from .polyline import Polyline


@GeoObject.register(["polygon", "Polygon"])
class Polygon(PointSet):
    """ Polygon 多边形 """

    def __init__(self, *args,  **kwargs) -> None:
        super().__init__(*args, rank=2, **kwargs)

    @property
    def is_valid(self) -> bool:
        if self.ndim == 2:
            return True
        else:
            raise NotImplementedError(f"{self.__class__.__name__}")

    @property
    def vertices(self) -> typing.Generator[Point, None, None]:
        for p in self._points:
            yield Point(*p)

    @property
    def edges(self) -> typing.Generator[Segment, None, None]:
        pt_iter = self.vertices
        first_pt = next(pt_iter)
        current_pt = first_pt
        while True:
            try:
                next_pt = next(pt_iter)
                yield Segment(current_pt, next_pt)
                current_pt = next_pt
            except StopIteration:
                yield Segment(current_pt, first_pt)
                break

    @property
    def boundary(self) -> Polyline:
        return Polyline(self._points, is_closed=True)


@Polygon.register("rectangle")
class Rectangle(GeoObject):
    def __init__(self, x, y, width, height, ** kwargs) -> None:
        super().__init__(**kwargs)
        self._x = x
        self._y = y
        self._width = width
        self._height = height

    @property
    def bbox(self) -> BBox: return BBox([self._x, self._y], [self._width, self._height])


@Polygon.register("regular_polygon")
class RegularPolygon(Polygon):
    """ Regular Polygon
        正多边形

        cneter: Point or tuple or list  
            中心点
        radius: float
            半径
        num_of_edges: int
            边数
        rot: float
            旋转角度
    """

    def __init__(self, center: Point, radius: float, num_of_edges: int, *args, **kwargs) -> None:
        center = Point(center) if not isinstance(center, Point) else center
        super().__init__(*args, **kwargs)

    @property
    def area(self) -> float:
        return self._impl.area

    @property
    def length(self) -> float:
        return self._impl.length

    @property
    def center(self) -> Point:
        return Point(self._impl.center)

    @property
    def radius(self) -> float:
        return self._impl.radius

    @property
    def inradius(self) -> float:
        return self._impl.inradius

    @property
    def rotation(self) -> float:
        return self._impl.rotation

    @property
    def vertices(self) -> typing.Generator[Point, None, None]:
        for p in self._impl.vertices:
            yield Point(p)
