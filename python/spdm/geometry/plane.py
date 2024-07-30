from spdm.core.geo_object import GeoObject


class Plane(GeoObject, rank=2, plugin_name="plane"):
    """Plane
    平面，二维几何体
    """

    @property
    def boundary(self) -> GeoObject:
        raise NotImplementedError(f"{self.__class__.__name__}")

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
