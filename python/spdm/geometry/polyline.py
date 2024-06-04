import collections.abc
import typing

import numpy as np

from ..utils.typing import ArrayType
from ..core.geo_object import GeoObject,BBox
from .point_set import PointSet


@GeoObject.register(["polyline", "Polyline"])
class Polyline(PointSet):

    def __init__(self, *args,  **kwargs) -> None:
        super().__init__(*args, rank=1, **kwargs)
