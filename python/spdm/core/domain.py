from __future__ import annotations
import abc
import typing
import numpy as np
import numpy.typing as np_tp

from spdm.utils.tags import _not_found_
from spdm.utils.type_hint import ArrayType, array_type
from spdm.core.sp_object import SpObject, sp_property
from spdm.core.functor import Functor
from spdm.core.geo_object import GeoObject
from spdm.geometry.vector import Vector

from spdm.numlib.numeric import float_nan, bitwise_and
from spdm.numlib.interpolate import interpolate


class Domain(SpObject, fill_value=float_nan):
    """函数/场的定义域，用以描述函数/场所在流形
    - geometry  ：几何边界
    - shape     ：网格所对应数组形状， 例如，均匀网格 的形状为 （n,m) 其中 n,m 都是整数
    - points    ：网格顶点坐标，例如 (x,y) ，其中，x，y 都是形状为 （n,m) 的数组


    """

    def __new__(cls, *args, _plugin_name=None, **kwargs):
        if cls is Domain and _plugin_name is None and all(isinstance(d, np.ndarray) for d in args):
            return super().__new__(PPolyDomain)
        return super().__new__(cls, *args, _plugin_name=_plugin_name, **kwargs)

    geometry: GeoObject

    shape: Vector[int]
    """
        存储网格点数组的形状
        结构化网格 shape   如 [n,m] n,m 为网格的长度dimension
        非结构化网格 shape 如 [<number of vertices>]
    """
    ndim: int = sp_property(alias="geometry.ndim")
    """所在的空间维度"""

    rank: int = sp_property(alias="geometry.rank")
    """所在流形的维度，0:点， 1:线， 2:面， 3:体"""

    points: typing.Tuple[ArrayType, ...]
    """ 网格对应的网格点坐标，ndim 个 形状为 shape 的数组。"""

    @property
    def is_simple(self) -> bool:
        return self.shape is not None and len(self.shape) > 0

    @property
    def is_empty(self) -> bool:
        return self.shape is None or len(self.shape) == 0 or any(d == 0 for d in self.shape)

    @property
    def is_full(self) -> bool:
        return all(d is None for d in self.shape)

    def view(self, obj, **kwargs):
        """将 obj 画在 domain 上，默认为 n维 contour。"""
        return {
            "$type": "contour",
            "$data": (*self.points, np.asarray(obj)),
            "style": kwargs,
        }

    def interpolate(self, func: typing.Callable | array_type) -> typing.Callable[..., array_type]:
        xargs = self.points
        if callable(func):
            value = func(*xargs)
        elif isinstance(func, array_type):
            value = func
        else:
            raise TypeError(f"{type(func)} is not array or callable!")

        return interpolate(*xargs, value)

    def mask(self, *args) -> bool | np_tp.NDArray[np.bool_]:
        # or self._metadata.get("extrapolate", 0) != 1:
        if self.shape is None or len(self.shape) == 0 or self._metadata.get("extrapolate", 0) != "raise":
            return True

        if len(args) != len(self.shape):
            raise RuntimeError(f"len(args) != len(self.dims) {len(args)}!={len(self.shape)}")

        v = []
        for i, (xmin, xmax) in enumerate(self.geometry.bbox):
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

        mask = self.mask(*xargs)

        mask_size = mask.size if isinstance(mask, array_type) else 1
        masked_num = np.sum(mask)

        if not isinstance(mask, array_type) and not isinstance(mask, (bool, np.bool_)):
            raise RuntimeError(f"Illegal mask {mask} {type(mask)}")

        if masked_num == 0:
            raise RuntimeError(f"Out of domain! {self} {xargs} ")

        if masked_num < mask_size:
            xargs = tuple(
                (arg[mask] if isinstance(mask, array_type) and isinstance(arg, array_type) and arg.ndim > 0 else arg)
                for arg in xargs
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


class PPolyDomain(Domain):
    """多项式定义域。
    根据离散网格点构建插值
          extrapolate: int |str
            控制当自变量超出定义域后的值
            * if ext=0  or 'extrapolate', return the extrapolated value. 等于 定义域无限
            * if ext=1  or 'nan', return nan
    """

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        if len(args) == 1 and isinstance(args[0], tuple):
            args = args[0]
        ndim = len(args)

        if all([isinstance(d, np.ndarray) and d.ndim == ndim for d in args]):
            self._points = args
        elif all([isinstance(d, np.ndarray) and d.ndim == 1 for d in args]):
            self._dims = args
            self._points = None
        else:
            raise RuntimeError(f"Invalid points {args}")

    @property
    def shape(self) -> typing.Tuple[int, ...]:
        if self._dims is not None:
            return tuple([d.size for d in self._dims])
        elif self._points is not None:
            return self._points[0].shape
        else:
            raise RuntimeError(f"illegal domain!")

    @property
    def points(self) -> typing.Tuple[array_type, ...]:
        if self._points is not None and self._points is not _not_found_:
            pass
        elif self._dims is not None:
            self._points = np.meshgrid(*self._dims, indexing="ij")
        return self._points

    def interpolate(self, y: array_type, **kwargs):

        periods = self._metadata.get("periods", None)
        extrapolate = self._metadata.get("extrapolate", 0)

        return interpolate(*self.points, y, periods=periods, extrapolate=extrapolate, **kwargs)
