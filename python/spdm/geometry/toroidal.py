
from .surface import Surface
from .solid import Solid
from .plane import Plane
from .curve import Curve
from .circle import Circle


@Surface.register("toroidal_surface")
class ToroidalSurface(Surface):
    def __init__(self, cross_section: Curve, circle: Circle, **kwargs) -> None:
        super().__init__(**kwargs)


@Surface.register("toroidal")
class Toroidal(Solid):
    def __init__(self, cross_section: Plane, circle: Circle, *args, **kwargs) -> None:
        super().__init__(**kwargs)
        self._boundary = ToroidalSurface(cross_section.boundary, circle, *args,)
