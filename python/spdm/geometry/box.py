from spdm.geometry.solid import Solid


class Box(Solid, plugin_name="box"):
    """Box 矩形，n维几何体"""

    @property
    def is_closed(self) -> bool:
        return True

    @property
    def is_convex(self) -> bool:
        return True


class Box2D(Solid, plugin_name="box2d", ndim=2):
    pass
