from __future__ import annotations
import abc
import typing
import numpy as np
import numpy.typing as np_tp
import functools
import collections
from enum import Enum

from copy import deepcopy
from .pluggable import Pluggable
from .typing import ArrayType, array_type
from .functor import Functor
from .path import update_tree
from .geo_object import GeoObject, as_geo_object

from ..numlib.numeric import float_nan, meshgrid, bitwise_and
from ..numlib.interpolate import interpolate


from ..utils.tags import _not_found_


class Domain(Pluggable):
    """函数/场的定义域，用以描述函数/场所在流形的离散网格等。可用以构建插值函数，"""

    _metadata = {"fill_value": float_nan}

    def __init__(self, *args, geometry=None, dims=None, **kwargs) -> None:
        self._dims = dims if dims is not None or len(args) == 0 else args
        self._geometry = as_geo_object(geometry)
        self._metadata = update_tree(deepcopy(self.__class__._metadata), kwargs)

    def display(self, obj):
        from ..view import sp_view

        return sp_view.display(self.view_geometry(obj), output="svg")

    def view_geometry(self, value, *args, **kwargs):
        return (*self.points, value)

    @property
    def geometry(self) -> GeoObject:
        """Geometry of the Mesh  网格的几何形状"""
        return self._geometry

    @property
    def label(self) -> str:
        return self._metadata.get("label", "unnamed")

    @property
    def name(self) -> str:
        return self._metadata.get("name", "unamed")

    @property
    def type(self) -> str:
        return self._metadata.get("type", "unknown")

    @property
    def units(self) -> typing.Tuple[str, ...]:
        return tuple(self._metadata.get("units", ["-"]))

    @property
    def is_simple(self) -> bool:
        return self._dims is not None and len(self._dims) > 0

    @property
    def is_empty(self) -> bool:
        return self._dims is None or len(self._dims) == 0 or any([d == 0 for d in self._dims])

    @property
    def is_full(self) -> bool:
        return all([d is None for d in self._dims])

    @property
    def ndim(self) -> int:
        return self.geometry.ndim

    @property
    def rank(self) -> int:
        return self.geometry.rank

    @property
    def shape(self) -> typing.Tuple[int]:
        return None

    @property
    @abc.abstractmethod
    def points(self) -> typing.Tuple[ArrayType]:
        return None

    def interpolate(self, func) -> typing.Callable[..., array_type]:
        xargs = self.points
        if callable(func):
            value = func(*xargs)
        elif isinstance(func, array_type):
            value = func
        else:
            raise TypeError(f"{type(func)} is not array or callable!")

        return interpolate(*xargs, value)

    @functools.cached_property
    def bbox(self) -> typing.Tuple[typing.List[float], typing.List[float]]:
        """函数的定义域"""
        return tuple(([d[0], d[-1]] if not isinstance(d, float) else [d, d]) for d in self.dims)

    def mask(self, *args) -> bool | np_tp.NDArray[np.bool_]:
        # or self._metadata.get("extrapolate", 0) != 1:
        if self.dims is None or len(self.dims) == 0 or self._metadata.get("extrapolate", 0) != "raise":
            return True

        if len(args) != self.ndim:
            raise RuntimeError(f"len(args) != len(self.dims) {len(args)}!={len(self.dims)}")

        v = []
        for i, (xmin, xmax) in enumerate(self.bbox):
            v.append((args[i] >= xmin) & (args[i] <= xmax))

        return bitwise_and.reduce(v)

    def check(self, *x) -> bool | np_tp.NDArray[np.bool_]:
        """当坐标在定义域内时返回 True，否则返回 False"""

        d = [child.__check_domain__(*x) for child in self._children if hasattr(child, "__domain__")]

        if isinstance(self._func, Functor):
            d += [self._func.__domain__(*x)]

        d = [v for v in d if (v is not None and v is not True)]

        if len(d) > 0:
            return np.bitwise_and.reduce(d)
        else:
            return True

    def eval(self, func, *xargs, **kwargs):
        """根据 __domain__ 函数的返回值，对输入坐标进行筛选"""

        mask = self.__domain__().mask(*xargs)

        mask_size = mask.size if isinstance(mask, array_type) else 1
        masked_num = np.sum(mask)

        if not isinstance(mask, array_type) and not isinstance(mask, (bool, np.bool_)):
            raise RuntimeError(f"Illegal mask {mask} {type(mask)}")
        elif masked_num == 0:
            raise RuntimeError(f"Out of domain! {self} {xargs} ")

        if masked_num < mask_size:
            xargs = tuple(
                [
                    (
                        arg[mask]
                        if isinstance(mask, array_type) and isinstance(arg, array_type) and arg.ndim > 0
                        else arg
                    )
                    for arg in xargs
                ]
            )
        else:
            mask = None

        value = func._eval(*xargs, **kwargs)

        if masked_num < mask_size:
            res = value
        elif is_scalar(value):
            res = np.full_like(mask, value, dtype=self._type_hint())
        elif isinstance(value, array_type) and value.shape == mask.shape:
            res = value
        elif value is None:
            res = None
        else:
            res = np.full_like(mask, self.fill_value, dtype=self._type_hint())
            res[mask] = value
        return res
