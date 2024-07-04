

import typing
import numpy as np
import numpy.typing as np_tp
from spdm.utils.logger import logger
from spdm.utils.tags import _not_found_
from spdm.utils.type_hint import array_type
from spdm.core.geo_object import GeoObject, BBox
from spdm.core.sp_tree import sp_property

_T = typing.TypeVar("_T", int, float, complex)


class Point(GeoObject, plugin_name="point"):
    """Point
    点，零维几何体
    """

    def __init__(self, *args, **kwargs) -> None:
        if len(args) == 1 and (isinstance(args[0], dict) or args[0] is _not_found_):
            cache = args[0]
        elif len(args) == 1 and isinstance(args[0], (list, tuple)):
            cache = {"points": np.asarray(args[0])}
        elif len(args) == 1 and isinstance(args[0], np.ndarray):
            cache = {"points": args[0]}
        elif len(args) != 0:
            cache = {"points": np.asarray(args)}
        else:
            cache = _not_found_
        super().__init__(cache, rank=0, **kwargs)

    

    rank: int = 0

    measure: float = 0

    @sp_property
    def ndim(self) -> int:
        return len(self.coordinate)

    @sp_property
    def bbox(self) -> BBox:
        return BBox(self.coordinate)

    def __equal__(self, other) -> bool:
        if isinstance(other, Point):
            return np.all(self.coordinate == other.coordinate)
        else:
            return np.all(self.coordinate == other)

    def __array__(self) -> array_type:
        return self.points

    def __getitem__(self, idx) -> float:
        return self.points[idx]


class PointXY(Point):
    x: float = sp_property(alias="points/0")
    y: float = sp_property(alias="points/1")
    z: float = sp_property(alias="points/2")


class PointRZ(Point):
    r: float = sp_property(alias="points/0")
    z: float = sp_property(alias="points/1")
