from spdm.geometry.surface import Surface
from spdm.geometry.solid import Solid
from spdm.geometry.plane import Plane
from spdm.geometry.curve import Curve
from spdm.geometry.circle import Circle


class ToroidalSurface(Surface, plugin_name="toroidal_surface"):
    def __init__(self, cross_section: Curve, circle: Circle, **kwargs) -> None:
        super().__init__(**kwargs)


@Surface.register("toroidal")
class Toroidal(Solid, plugin_name="toroidal"):
    def __init__(self, cross_section: Plane, circle: Circle, *args, **kwargs) -> None:
        super().__init__(**kwargs)
        self._boundary = ToroidalSurface(
            cross_section.boundary,
            circle,
            *args,
        )
