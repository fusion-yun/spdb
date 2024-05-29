from __future__ import annotations

import typing
import numpy as np
import numpy.typing as np_tp
import functools
import collections

from copy import deepcopy

from ..utils.typing import ArrayType, array_type
from ..utils.numeric import float_nan, meshgrid, bitwise_and
from ..numlib.interpolate import interpolate

from .functor import Functor
from .path import update_tree


class DomainBase:
    """函数定义域"""

    _metadata = {"fill_value": float_nan}

    def __init__(self, *args, **kwargs) -> None:
        if len(args) == 1:
            if isinstance(args[0], dict):
                kwargs = collections.ChainMap(args[0], kwargs)
                args = args[1:]
            elif isinstance(args[0], (list,tuple)):
                args = args[0]

        if len(args) > 0:
            self._dims = args
        else:
            self._dims = kwargs.pop("dims", [])

        if len(kwargs) > 0:
            self._metadata = update_tree(deepcopy(self.__class__._metadata), kwargs)

    @property
    def label(self) -> str:
        return self._metadata.get("label", "unnamed")

    @property
    def is_simple(self) -> bool:
        return len(self._dims) > 0

    @property
    def is_empty(self) -> bool:
        return len(self._dims) == 0 or any([d == 0 for d in self._dims])

    @property
    def is_full(self) -> bool:
        return all([d is None for d in self._dims])

    @property
    def dims(self) -> typing.Tuple[ArrayType]:
        """函数的网格，即定义域的网格"""
        return self._dims

    @property
    def ndims(self) -> int:
        return len(self._dims)

    @property
    def shape(self) -> typing.Tuple[int]:
        return tuple([len(d) for d in self.dims])

    @functools.cached_property
    def points(self) -> typing.Tuple[ArrayType]:
        if len(self.dims) == 1:
            return self.dims
        else:
            return meshgrid(*self.dims, indexing="ij")

    @functools.cached_property
    def bbox(self) -> typing.Tuple[typing.List[float], typing.List[float]]:
        """函数的定义域"""
        return tuple(([d[0], d[-1]] if not isinstance(d, float) else [d, d]) for d in self.dims)

    @property
    def periods(self):
        return None

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

    def interpolate(self, y: array_type, *args, **kwargs):
        x = self.points

        periods = self._metadata.get("periods", None)
        extrapolate = self._metadata.get("extrapolate", 0)

        return interpolate(*x, y, periods=periods, extrapolate=extrapolate)
