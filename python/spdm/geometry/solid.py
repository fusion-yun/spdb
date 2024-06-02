import typing
import abc
from ..core.geo_object import GeoObject,BBox
from .plane import Plane


class Solid(GeoObject):
    """ Line
        线，一维几何体
    """

    def __init__(self, *args,  **kwargs) -> None:
        super().__init__(*args, rank=3, **kwargs)

    @abc.abstractproperty
    def points(self, *args, **kwargs):
        raise NotImplementedError(f"{self.__class__.__name__}")

    @abc.abstractproperty
    def boundary(self) -> typing.List[Plane]:
        raise NotImplementedError(f"{self.__class__.__name__}")
