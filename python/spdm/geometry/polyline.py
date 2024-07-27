from spdm.core.geo_object import GeoObject


class Polyline(GeoObject, plugin_name="polyline", rank=1):
    pass


class Polyline2D(Polyline, plugin_name="polyline2d", ndim=2, rank=1):
    pass
