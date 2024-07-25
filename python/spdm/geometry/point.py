import typing
import numpy as np
import numpy.typing as np_tp
from spdm.utils.logger import logger
from spdm.utils.tags import _not_found_
from spdm.utils.type_hint import array_type
from spdm.core.geo_object import GeoObject, BBox
from spdm.core.sp_tree import annotation

_T = typing.TypeVar("_T", int, float, complex)


class Point(GeoObject, rank=0, plugin_name="point"):
    """Point
    点，零维几何体
    """


PointXY = Point["XY"]
PointRZ = Point["RZ"]
