import typing

from ..utils.typing import ArrayType
from ..core.geo_object import GeoObject,BBox

from .line import Line
from .plane import Plane
from .point import Point
from .solid import Solid
from .surface import Surface



@GeoObject.register("circle")
class Circle(GeoObject):
    """ Circle
        圆，具有一个固定圆心和一个固定半径
    """

    def __init__(self, x: float, y: float, r: float, **kwargs) -> None:
        super().__init__(rank=1, ndims=2, is_closed=True, **kwargs)
        self._x = x
        self._y = y
        self._r = r

    @property
    def bbox(self) -> BBox:
        return BBox([self._x - self._r, self._y - self._r], [2.0*self._r, 2.0 * self._r])

    @property
    def x(self) -> float: return self._x

    @property
    def y(self) -> float: return self._y

    @property
    def r(self) -> float: return self._r

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


@GeoObject.register("ellipse")
class Ellipse(GeoObject):
    """ Ellipse
        椭圆，具有一个固定圆心和两个固定半径
    """
    pass


@Plane.register("disc")
class Disc(Plane):
    """ Disc
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
    """ Sphere
        球面
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._boundary = Circle(*args)

    pass


@Solid.register("ball")
class Ball(GeoObject):
    """ Ball
        球体
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._boundary = Sphere(*args)


@Solid.register("cylinder")
class Cylinder(GeoObject):
    """ Cylinder
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
        self._boundary = ToroidalSurface(cross_section.boundary, circle, *args,)
