from __future__ import annotations

import typing
import numpy as np
import numpy.typing as np_tp
from spdm.utils.logger import logger
from spdm.utils.type_hint import array_type
from spdm.core.geo_object import GeoObject, BBox
from spdm.core.sp_tree import sp_property

_T = typing.TypeVar("_T", int, float, complex)


class Point(GeoObject, plugin_name="point"):
    """Point
    点，零维几何体
    """

    coordinate: array_type

    x: float = sp_property(alias="coordinate/0")
    y: float = sp_property(alias="coordinate/1")
    z: float = sp_property(alias="coordinate/2")

    measure: float = 0

    @property
    def points(self):
        return self._coord
