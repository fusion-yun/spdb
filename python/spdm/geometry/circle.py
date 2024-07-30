import typing
import numpy as np
from spdm.core.geo_object import GeoObject, BBox
from spdm.core.sp_tree import annotation, sp_property
from spdm.geometry.line import Line
from spdm.geometry.plane import Plane
from spdm.geometry.point import Point
from spdm.geometry.solid import Solid
from spdm.geometry.surface import Surface


class Circle(GeoObject, plugin_name="circle", rank=1):
    """Circle
    圆，具有一个固定圆心和一个固定半径
    """

    @sp_property
    def bbox(self) -> BBox:
        o = self.origin
        r = self.radius
        return BBox(o - r, [2.0 * r, 2.0 * r])

    origin: Point = annotation(alias="points/0")

    @sp_property
    def radius(self) -> float:
        return np.sqrt(np.sum((self.points[1] - self.points[0]) ** 2))

    def map(self, u, *args, **kwargs):
        return NotImplemented

    def derivative(self, u, *args, **kwargs):
        return NotImplemented

    def dl(self, u, *args, **kwargs):
        return NotImplemented

    def pullback(self, func, *args, **kwargs):
        return NotImplemented

    def make_one_form(self, func):
        return NotImplemented


class Ellipse(GeoObject, plugin_name="ellipse"):
    """Ellipse
    椭圆，具有一个固定圆心和两个固定半径
    """

    pass




class Disc(Plane, plugin_name="disc"):
    """Disc
    圆盘
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._boundary = Circle(*args)

    @property
    def boundary(self) -> Circle:
        return self._boundary


@Surface.register("sphere")
class Sphere(Surface):
    """Sphere
    球面
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._boundary = Circle(*args)

    pass


@Solid.register("ball")
class Ball(GeoObject):
    """Ball
    球体
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._boundary = Sphere(*args)


@Solid.register("cylinder")
class Cylinder(GeoObject):
    """Cylinder
    圆柱体，具有两个固定端面
    """

    pass


@Surface.register("toroidal_surface")
class ToroidalSurface(Surface):
    def __init__(self, cross_section: Line, circle: Circle, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


@Solid.register("toroidal")
class Toroidal(Solid):
    def __init__(self, section: Plane, circle: Circle, *args, **kwargs) -> None:
        super().__init__(**kwargs)
        self._boundary = ToroidalSurface(
            cross_section.boundary,
            circle,
            *args,
        )
