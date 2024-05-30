from __future__ import annotations

import collections.abc
import typing
import uuid
from copy import copy
from functools import cached_property

import numpy as np

from ..core.htree import List
from ..utils.logger import logger
from ..core.typing import ArrayLike, ArrayType, NumericType, ScalarType, array_type, nTupleType, numeric_type


class BBox:
    def __init__(self, origin: ArrayLike, dimensions: ArrayLike, transform=None, shift=None) -> None:
        self._origin = np.asarray(origin)
        self._dimensions = np.asarray(dimensions)
        self._transform = transform
        self._shift = shift

    def __copy__(self) -> BBox:
        return BBox(self._origin, self._dimensions, self._transform, self._shift)

    def __repr__(self) -> str:
        """x y width height"""
        return f"viewBox=\"{' '.join([*map(str,self._origin)])}  {' '.join([*map(str,self._dimensions)]) }\" transform=\"{self._transform}\" shift=\"{self._shift}\""

    @property
    def origin(self) -> ArrayType:
        return self._origin

    @property
    def dimensions(self) -> ArrayType:
        return self._dimensions

    @property
    def is_valid(self) -> bool:
        return np.all(self._dimensions > 0) == True

    @property
    def is_degraded(self) -> bool:
        return (np.any(np.isclose(self._dimensions, 0.0))) == True

    # def __equal__(self, other: BBox) -> bool:
    #     return np.allclose(self._xmin, other._xmin) and np.allclose(self._xmax, other._xmax)

    # def __or__(self, other: BBox) -> BBox:
    #     if other is None:
    #         return self
    #     else:
    #         return BBox(np.min(self._xmin, other._xmin), np.max(self._xmax, other._xmax))

    # def __and__(self, other: BBox) -> BBox | None:
    #     if other is None:
    #         return None
    #     else:
    #         res = BBox(np.max(self._xmin, other._xmin), np.min(self._xmax, other._xmax))
    #         return res if res.is_valid else None

    @property
    def ndim(self) -> int:
        return len(self._dimensions)

    @property
    def center(self) -> ArrayType:
        return self._origin + self._dimensions * 0.5

    """ center of geometry """

    @property
    def measure(self) -> float:
        return float(np.product(self._dimensions))

    """ measure of geometry, length,area,volume,etc. 默认为 bbox 的体积 """

    def enclose(self, *args) -> bool | array_type:
        """Return True if all args are inside the geometry, False otherwise."""

        if len(args) == 1:

            # if hasattr(args[0], "bbox"):
            #     return self.enclose(args[0].bbox)
            # elif isinstance(args[0], BBox):
            #     return self.enclose(args[0].origin) and self.enclose(args[0].origin+args[0].dimensions)
            if hasattr(args[0], "points"):
                return self.enclose(*args[0].points)
            if isinstance(args[0], collections.abc.Sequence):
                return self.enclose(*args[0])
            elif isinstance(args[0], array_type):
                return self.enclose([args[0][..., idx] for idx in range(self.ndim)])
            else:
                raise TypeError(f"args has wrong type {type(args[0])} {args}")

        elif len(args) == self.ndim:
            if isinstance(args[0], array_type):
                r_pos = [args[idx] - self._origin[idx] for idx in range(self.ndim)]
                return np.bitwise_and.reduce(
                    [((r_pos[idx] >= 0) & (r_pos[idx] <= self._dimensions[idx])) for idx in range(self.ndim)]
                )
            else:
                res = all(
                    [
                        ((args[idx] >= self._origin[idx]) and (args[idx] <= self._origin[idx] + self._dimensions[idx]))
                        for idx in range(self.ndim)
                    ]
                )
                if not res:
                    logger.debug((args, self._origin, self._dimensions))
                return res

        else:
            raise TypeError(f"args has wrong type {type(args[0])} {args}")

    def union(self, other: BBox) -> BBox:
        raise NotImplementedError(f"intersection")

    """ Return the union of self with other. """

    def intersection(self, other: BBox):
        raise NotImplementedError(f"intersection")

    """ Return the intersection of self with other. """

    def reflect(self, point0, pointt1):
        raise NotImplementedError(f"reflect")

    """ reflect  by line"""

    def rotate(self, angle, axis=None):
        raise NotImplementedError(f"rotate")

    """ rotate  by angle and axis"""

    def scale(self, *s, point=None):
        raise NotImplementedError(f"scale")

    """ scale self by *s, point """

    def translate(self, *shift):
        raise NotImplementedError(f"translate")
