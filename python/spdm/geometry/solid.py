import typing
import abc
from ..core.geo_object import GeoObject, BBox
from .plane import Plane


class Solid(GeoObject, rank=3, plugin_name="solid"):
    """Solid 体，三维几何体
    ======================

    """
