""" Point module"""

from spdm.core.geo_object import GeoObject


class Point(GeoObject, rank=0, plugin_name="point"):
    """Point
    点，零维几何体
    """


PointXY = Point["XY"]
PointRZ = Point["RZ"]
