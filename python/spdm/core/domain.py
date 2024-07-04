import abc
import typing
import numpy as np
import numpy.typing as np_tp

from spdm.utils.tags import _not_found_
from spdm.utils.type_hint import array_type, ArrayType
from spdm.core.sp_tree import sp_property
from spdm.core.sp_object import SpObject
from spdm.core.geo_object import GeoObject
from spdm.numlib.interpolate import interpolate
from spdm.numlib.numeric import float_nan, bitwise_and
from spdm.geometry.vector import Vector


class Domain(SpObject):
    """函数/场的定义域，用以描述函数/场所在流形
    - geometry  ：几何边界
    - shape     ：网格所对应数组形状， 例如，均匀网格 的形状为 （n,m) 其中 n,m 都是整数
    - points    ：网格顶点坐标，例如 (x,y) ，其中，x，y 都是形状为 （n,m) 的数组


    """

    def __new__(cls, *args, **kwargs):
        d_type = kwargs.get("type", None)
        if cls is Domain and d_type is None and all(isinstance(d, np.ndarray) for d in args):
            return super().__new__(PPolyDomain)
        return super().__new__(cls, *args, **kwargs)

    geometry: GeoObject

    ndim: int = sp_property(alias="geometry/ndim")
    """所在的空间维度"""

    rank: int = sp_property(alias="geometry/rank")
    """所在流形的维度，0:点， 1:线， 2:面， 3:体"""

    @property
    def is_simple(self) -> bool:
        return self.shape is not None and len(self.shape) > 0

    @property
    def is_empty(self) -> bool:
        return self.shape is None or len(self.shape) == 0 or any(d == 0 for d in self.shape)

    @property
    def is_full(self) -> bool:
        return all(d is None for d in self.shape)

    @property
    def is_null(self) -> bool:
        return all(d == 0 for d in self.shape)

    @abc.abstractmethod
    def interpolate(self, func: typing.Callable | ArrayType) -> typing.Callable[..., ArrayType]:
        pass

    @abc.abstractmethod
    def mask(self, *args) -> bool | np_tp.NDArray[np.bool_]:
        pass

    @abc.abstractmethod
    def check(self, *x) -> bool | np_tp.NDArray[np.bool_]:
        pass

    @abc.abstractmethod
    def eval(self, func, *xargs, **kwargs) -> ArrayType:
        pass


class PPolyDomain(Domain):
    """多项式定义域。
    根据离散网格点构建插值
          extrapolate: int |str
            控制当自变量超出定义域后的值
            * if ext=0  or 'extrapolate', return the extrapolated value. 等于 定义域无限
            * if ext=1  or 'nan', return nan
    """

    def __init__(self, *args, **kwargs):
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
        super().__init__(**kwargs)

    shape: Vector[int]

    @property
    def points(self) -> typing.Tuple[array_type, ...]:
        if self._points is not None and self._points is not _not_found_:
            pass
        elif self._dims is not None:
            self._points = np.meshgrid(*self._dims, indexing="ij")
        return self._points

    def interpolate(self, func: array_type, **kwargs):

        periods = self._metadata.get("periods", None)
        extrapolate = self._metadata.get("extrapolate", 0)

        return interpolate(*self.points, func, periods=periods, extrapolate=extrapolate, **kwargs)

    def mask(self, *args) -> bool | np_tp.NDArray[np.bool_]:
        return False

    def check(self, *x) -> bool | np_tp.NDArray[np.bool_]:
        return True

    def eval(self, func, *xargs, **kwargs) -> ArrayType:
        return NotImplemented()
