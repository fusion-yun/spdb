import typing

from spdm.core.sp_tree import annotation
from spdm.core.geo_object import GeoObject
from spdm.geometry.line import Segment
from spdm.geometry.point import Point
from spdm.geometry.polyline import Polyline


class Rectangle(GeoObject, plugin_name="rectangle"):
    pass


RectangleRZ = Rectangle["RZ"]
RectangleXY= Rectangle["XY"]


class Polygon(GeoObject, plugin_name="polygon", rank=2):
    """Polygon 多边形"""

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


class RegularPolygon(Polygon, plugin_name="regular_polygon"):
    """Regular Polygon
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

    def __init__(self, cneter: Point, second_point, num_of_edges: int, **kwargs) -> None:
        super().__init__(cneter, second_point, num_of_edges=num_of_edges, **kwargs)

    @property
    def area(self) -> float:
        return self._impl.area

    @property
    def length(self) -> float:
        return self._impl.length

    center: Point = annotation(alias="points/0")

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
