import abc
import typing
import numpy as np
import numpy.typing as np_tp

from spdm.utils.tags import _not_found_
from spdm.utils.type_hint import array_type, ArrayType
from spdm.core.sp_tree import sp_property
from spdm.core.sp_object import SpObject
from spdm.core.geo_object import GeoObjectBase
from spdm.numlib.interpolate import interpolate
from spdm.geometry.vector import Vector


class Domain(SpObject):
    """函数/场的定义域，用以描述函数/场所在流形
    - geometry  ：几何边界
    - shape     ：网格所对应数组形状， 例如，均匀网格 的形状为 （n,m) 其中 n,m 都是整数
    - points    ：网格顶点坐标，例如 (x,y) ，其中，x，y 都是形状为 （n,m) 的数组


    """

    def __new__(cls, *args, kind=None, **kwargs):
        if cls is Domain and kind is None and all(isinstance(d, np.ndarray) for d in args):
            return super().__new__(DomainPPoly)
        return super().__new__(cls, *args, kind=kind, **kwargs)

    geometry: GeoObjectBase

    ndim: int = sp_property(alias="geometry/ndim")
    """所在的空间维度"""

    rank: int = sp_property(alias="geometry/rank")
    """所在流形的维度，0:点， 1:线， 2:面， 3:体"""

    @property
    @abc.abstractmethod
    def points(self) -> array_type:
        return NotImplemented

    @property
    def coordinates(self):
        points = self.points
        return tuple([points[..., i] for i in range(self.ndim)])

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


class DomainExpr(Domain):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        raise NotImplementedError()


class DomainPPoly(Domain):
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
            self._coordinates = args
        elif all([isinstance(d, np.ndarray) and d.ndim == 1 for d in args]):
            self.dims = args
            self._coordinates = None
        else:
            raise RuntimeError(f"Invalid points {args}")
        super().__init__(**kwargs)

    shape: Vector[int]

    dims: typing.Tuple[ArrayType, ...]

    @property
    def points(self) -> array_type:
        return np.stack(self.coordinates).reshape(-1)

    @property
    def coordinates(self) -> typing.Tuple[ArrayType, ...]:
        if self._coordinates is None:
            self._coordinates = np.meshgrid(*self.dims, indexing="ij")
        return self._coordinates

    def interpolate(self, func: array_type, **kwargs):
        return interpolate(
            *self.coordinates,
            func,
            periods=self._metadata.get("periods", None),
            extrapolate=self._metadata.get("extrapolate", 0),
            **kwargs,
        )

    def mask(self, *args) -> bool | np_tp.NDArray[np.bool_]:
        return False

    def check(self, *x) -> bool | np_tp.NDArray[np.bool_]:
        return True

    def eval(self, func, *xargs, **kwargs) -> ArrayType:
        return NotImplemented
