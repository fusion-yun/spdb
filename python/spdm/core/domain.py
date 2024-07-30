import abc
import typing
import numpy as np
import numpy.typing as np_tp

from spdm.utils.tags import _not_found_
from spdm.utils.type_hint import array_type, ArrayType
from spdm.core.htree import List
from spdm.core.sp_tree import annotation
from spdm.core.sp_object import SpObject
from spdm.core.geo_object import GeoObject
from spdm.numlib.interpolate import interpolate
from spdm.geometry.vector import Vector


class Domain(SpObject):
    """函数/场的定义域，用以描述函数/场所在流形
    - geometry  ：几何边界
    - shape     ：网格所对应数组形状， 例如，均匀网格 的形状为 （n,m) 其中 n,m 都是整数
    - points    ：网格顶点坐标，例如 (x,y) ，其中，x，y 都是形状为 （n,m) 的数组


    """

    def __new__(cls, *args, kind=None, **kwargs) -> typing.Self:
        if cls is Domain and kind is None and all(isinstance(d, np.ndarray) for d in args):
            return super().__new__(DomainPPoly)
        return super().__new__(cls, *args, kind=kind, **kwargs)

    geometry: GeoObject

    ndim: int = annotation(alias="geometry/ndim")
    """所在的空间维度"""

    rank: int = annotation(alias="geometry/rank")
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

    def interpolate(self, func: typing.Callable | ArrayType) -> typing.Callable[..., ArrayType]:
        pass

    def mask(self, *args) -> bool | np_tp.NDArray[np.bool_]:
        pass

    def check(self, *x) -> bool | np_tp.NDArray[np.bool_]:
        pass

    def eval(self, func, *xargs, **kwargs) -> ArrayType:
        pass

    def refresh(self, *args, domain=None, **kwargs) -> typing.Self:
        if domain is not None and domain is not _not_found_:
            self.__setstate__(domain)
        return self


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

        coordinates = None
        dims = None

        if all([isinstance(d, np.ndarray) and d.ndim == ndim for d in args]):
            coordinates = args
            args = []
        elif all([isinstance(d, np.ndarray) and d.ndim == 1 for d in args]):
            dims = args
            args = []

        #     raise RuntimeError(f"Invalid points {args}")
        super().__init__(*args, **kwargs)
        self._coordinates = coordinates
        self.dims = dims

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


_T = typing.TypeVar("_T")


class WithDomain(abc.ABC):
    def __init_subclass__(cls, domain: str = None, **kwargs):
        super().__init_subclass__(**kwargs)
        if domain is not None and getattr(cls, "domain", None) is None:
            cls.domain = annotation(alias=domain, type_hint=Domain)

    @classmethod
    def _get_by_domain(cls, obj: _T, *domain):
        if isinstance(obj, dict):
            return {k: cls._get_by_domain(v, *domain) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [cls._get_by_domain(v, *domain) for v in obj]
        elif callable(obj):
            return obj(*domain)
        else:
            return obj

    @classmethod
    def _set_by_domain(cls, obj: _T, domain, value) -> _T:
        obj[domain] = value

    def find(self, *args, domain: Domain = None, **kwargs) -> typing.Self:
        """取回在 sub_domain 上的数据集"""
        res = super().find(*args, **kwargs)

        if domain is None or domain is self.domain:
            return res
        else:
            return self._get_by_domain(res, domain)

    def update(self, *args, domain: Domain = None, **kwargs):
        """更新在 domain 上的数据集"""
        if domain is None:
            super().update(*args, **kwargs)
        else:
            self._set_by_domain(domain, *args, **kwargs)

    def insert(self, *args, domain: Domain = None, **kwargs):
        """更新在 domain 上的数据集"""
        if domain is None:
            super().insert(*args, **kwargs)
        else:
            self._set_by_domain(domain, *args, **kwargs)


class MultiDomains(Domain, plugin_name="multiblock"):
    sub_domains: List[Domain] = annotation()
