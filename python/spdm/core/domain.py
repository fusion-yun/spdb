import abc
import typing
import functools
import numpy as np

from spdm.utils.tags import _not_found_
from spdm.utils.type_hint import array_type, ArrayType
from spdm.core.sp_tree import annotation, sp_property
from spdm.core.sp_object import SpObject
from spdm.core.geo_object import BBox, GeoObject

from spdm.numlib.interpolate import interpolate


class Domain(SpObject):
    """Domain 描述空间底流形$B$，Field/Function 是在底流形上的函数或称为纤维丛 $F$。"""

    def __new__(cls, *args, kind=None, **kwargs) -> typing.Self:
        """根据参数确定 Domain 的类型"""
        if cls is Domain and kind is None and all(isinstance(d, np.ndarray) for d in args):
            return super().__new__(DomainPPoly)
        return super().__new__(cls, *args, kind=kind, **kwargs)

    # ------------------------------------------------------------------------------------------------------------------
    # 网格几何属性

    ndim: int = annotation(alias="geometry/ndim")
    """流形所在空间的维度"""

    rank: int = annotation(alias="geometry/rank")
    """流形的维度，0:点， 1:线， 2:面， 3:体"""

    geometry: GeoObject
    """流形的几何形状"""

    @sp_property
    def bbox(self) -> BBox:
        """返回边界的包围盒，默认为 geometry 的包围盒"""
        return self.geometry.bbox

    period: typing.Tuple[bool, ...]
    """周期性边界条件，用以描述边界的周期性，例如，边界的周期性为 (True,False) 表示第一个维度为周期性，第二个维度为非周期性"""

    margin: typing.Tuple[int, ...]
    """ 边界边界的宽度，用以描述边界的宽度，例如，边界的宽度为 1，表示边界的宽度为 1 个网格单元"""

    # -------------------------------------------------------------------------------------------------------------------
    # 网格点

    shape: typing.Tuple[bool, ...]
    """
        网格点数组的形状
        结构化网格 shape   如 [n,m] n,m 为网格的长度dimension
        非结构化网格 shape 如 [<number of vertices>]
    """

    @property
    def points(self) -> ArrayType:
        """网格顶点（vertices）的 _坐标_  形状为 [(x0,y0,z0),(x1,y1,z1)...] ，返回数组形状为 shape= (...mesh.shape,ndim)"""
        raise NotImplementedError(f"{self.__class__.__name__}.points")

    @property
    def coordinates(self) -> typing.Tuple[ArrayType, ...]:
        """网格 __坐标__，形如 (X,Y,Z) ，其中 X,Y,Z 为网格点的坐标数组。 返回数组形状为 shape= (ndim,...mesh.shape)"""
        return tuple([self.points[..., i] for i in range(self.ndim)])

    # -------------------------------------------------------------------------------------------------------------------
    # 流形属性
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

    # -------------------------------------------------------------------------------------------------------------------
    # 底流形$B$上定义的运算操作

    def execute(self, func: typing.Callable, *args, **kwargs) -> ArrayType:
        """在定义域上执行函数"""
        raise NotImplementedError(f"{self.__class__.__name__}.execute")

    def interpolate(self, func: typing.Callable | ArrayType, *args, **kwargs) -> typing.Callable[..., ArrayType]:
        """依据网格对数字插值，返回插值函数"""
        raise NotImplementedError(f"{self.__class__.__name__}.interpolate")

    def partial_derivative(
        self, order, y: typing.Callable | ArrayType, *args, **kwargs
    ) -> typing.Callable[..., ArrayType]:
        """返回偏导数函数"""
        raise NotImplementedError(f"{self.__class__.__name__}.partial_derivative")

    def antiderivative(self, y: typing.Callable | ArrayType, *args, **kwargs) -> typing.Callable[..., ArrayType]:
        """返回积分函数"""
        raise NotImplementedError(f"{self.__class__.__name__}.antiderivative")

    # def integrate(self, y: typing.Callable | ArrayType, *args, **kwargs) -> ScalarType:
    #     """返回积分函数"""
    #     raise NotImplementedError(f"{self.__class__.__name__}.integrate")

    # -------------------------------------------------------------------------------------------------------------------
    # obsolete
    # def mask(self, *args) -> bool | np_tp.NDArray[np.bool_]:
    #     pass
    # def check(self, *x) -> bool | np_tp.NDArray[np.bool_]:
    #     pass


_TDomain = typing.TypeVar("_TDomain", bound=Domain)


class SubDomainTraits(abc.ABC):
    """
    部分定义域，用以描述函数/场所在流形的一部分。
    - 用以区分边界，内部
    """

    def __init__(self, *args, _parent: _TDomain, **kwargs):
        super().__init__(*args, _parent=_parent, **kwargs)

    indices: ArrayType
    """ 子域在主域网格点索引 """

    @functools.cached_property
    def points(self) -> ArrayType:
        if not isinstance(self._parent, Domain):
            raise RuntimeError(f"Invalid parent {self._parent}")

        return self._parent.points[self.indices]


class SubDomain(typing.Generic[_TDomain], Domain):
    """部分定义域，用以描述函数/场所在流形的一部分。
    - 用以区分边界，内部
    - 用以区分网格的 vertical、edge 和 Cell
    """

    def __class_getitem__(cls, params):
        if not isinstance(params, tuple):
            params = (params, tuple)

        cls_name = f"{cls.__name__}[{','.join(p.__name__ for p in params)}]"

        return type(cls_name, (SubDomainTraits, *params), {})

    @property
    def points(self) -> ArrayType:
        return super().points


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

    shape: typing.Tuple[int]

    dims: typing.Tuple[ArrayType, ...]

    @property
    def points(self) -> array_type:
        return np.stack(self.coordinates).reshape(-1)

    @property
    def coordinates(self) -> typing.Tuple[ArrayType, ...]:
        if self._coordinates is None:
            self._coordinates = np.meshgrid(*self.dims, indexing="ij")
        return self._coordinates

    def interpolate(self, value: ArrayType, *args, **kwargs) -> typing.Callable[..., ArrayType]:
        """构建插值函数"""
        return interpolate(
            *self.coordinates,
            value,
            *args,
            periods=self._metadata.get("periods", None),
            extrapolate=self._metadata.get("extrapolate", 0),
            **kwargs,
        )


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
