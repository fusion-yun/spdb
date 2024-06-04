from __future__ import annotations

import abc
import collections.abc
import functools
import typing
from copy import copy

import numpy as np

from ..utils.logger import logger
from ..utils.typing import ArrayLike, ArrayType, NumericType, array_type, nTupleType

from ..core.geo_object import GeoObject,BBox
from .point import Point


class PointSet(GeoObject):
    def __init__(self, *args, **kwargs) -> None:
        if len(args) == 1:
            if isinstance(args[0], collections.abc.Sequence):
                args = args[0]
            elif isinstance(args[0], dict):
                args = [*args[0].values()]

        if len(args) == 0:
            raise RuntimeError(f"{self.__class__.__name__} must have at least one point")
        elif len(args) > 1 and all([isinstance(a, array_type) for a in args]):
            try:
                points = np.stack(args, axis=args[0].ndim)
            except ValueError as error:
                raise ValueError(f"illegal args={args}") from error
        elif isinstance(args[0], PointSet):
            points = args[0]._points
            kwargs = collections.ChainMap(kwargs, args[0]._metadata)
        elif isinstance(args[0], array_type):
            points = args[0]
        else:
            raise TypeError(f"illegal type args[0]={type(args[0])}")

        super().__init__(ndim=points.shape[-1], **kwargs)

        self._points: array_type = points
        self.set_coordinates()

    def set_coordinates(self, *args):
        if len(args) == 0:
            args = self._metadata.get("coordinates", [])
            if isinstance(args, str):
                args = args.split(" ")

        if len(args) == 0:
            return
        if len(args) == 1 and isinstance(args[0], str):
            args = [x.strip() for x in args[0].split(",")]

        self._metadata["coordinates"] = args

        if isinstance(args, collections.abc.Sequence):
            if len(args) != self.ndim:
                raise ValueError(f"coordinates {args} not match ndim {self.ndim}")

        for idx, coord_name in enumerate(args):
            setattr(self, coord_name, self._points[..., idx])

    def __copy__(self) -> PointSet:
        other: PointSet = super().__copy__()  # type:ignore
        other._points = self._points
        other.set_coordinates()
        return other

    def __array__(self) -> array_type:
        return self._points

    @property
    def points(self) -> typing.List[ArrayType]:
        return [self._points[..., idx] for idx in range(self.ndim)]

    @functools.cached_property
    def bbox(self) -> BBox:
        xmin = [np.min(self._points[..., idx]) for idx in range(self.ndim)]
        dims = [np.max(self._points[..., idx]) - xmin[idx] for idx in range(self.ndim)]
        return BBox(xmin, dims)

    @property
    def boundary(self) -> PointSet | None:
        if self.is_closed:
            return None
        elif self._points.ndim == 2:
            if self.rank == 2:
                return PointSet(self._points)
            elif self.rank == 1:
                return PointSet((self._points[0], self._points[1]))
        else:
            raise NotImplementedError(f"{self.__class__.__name__}.boundary")

    @property
    def vertices(self) -> typing.Generator[Point, None, None]:
        if self._points.ndim != 2:
            raise NotImplementedError(f"{self.__class__.__name__}.vertices for ndim!=2")

        for p in self._points:
            yield Point(*p)
