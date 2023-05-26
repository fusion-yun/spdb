from __future__ import annotations

import collections.abc
import inspect
import typing
from copy import copy
from enum import Enum
import functools
import numpy as np
from scipy.interpolate import (InterpolatedUnivariateSpline,
                               RectBivariateSpline, RegularGridInterpolator,
                               UnivariateSpline, interp1d, interp2d)
from spdm.utils.typing import ArrayType

from ..utils.logger import logger
from ..utils.misc import group_dict_by_prefix, try_get
from ..utils.tags import _not_found_
from ..utils.typing import (ArrayType, NumericType, array_type, numeric_type,
                            scalar_type)
from .Expression import Expression

_T = typing.TypeVar("_T")


class Function(Expression, typing.Generic[_T]):
    """
        Function
        ---------
        A function is a mapping between two sets, the _mesh_ and the  _value_.
        The _value_  is the set of all possible outputs of the function.
        The _mesh_ is the set of all possible inputs  to the function.

        函数定义域为多维空间时，网格采用rectlinear mesh，即每个维度网格表示为一个数组 _dimension_ 。

    """

    def __init__(self, value: NumericType | Expression, *dims: ArrayType, periods=None, fill_value=np.nan, op=None, **kwargs):
        """
            Parameters
            ----------
            value : NumericType
                函数的值
            mesh : typing.List[ArrayType]
                函数的定义域
            args : typing.Any
                位置参数, 用于与mesh_*，coordinate* 一起构建 mesh
            kwargs : typing.Any
                命名参数，
                    mesh_*      : 用于传递给网格的参数
                    coordinate* : 给出各个坐标轴的path
                    op_*        : 用于传递给运算符的参数
                    *           : 用于传递给 Node 的参数

        """

        mesh,  kwargs = group_dict_by_prefix(kwargs,  "mesh")

        if isinstance(value, Expression) or callable(value) and op is None:
            Expression.__init__(self, value, **kwargs)
            self._value = None
        else:
            Expression.__init__(self, op, **kwargs)
            self._value = value

        if isinstance(mesh, Enum):
            self._mesh = {"type": mesh.name}
        elif isinstance(mesh, str):
            self._mesh = {"type":  mesh}
        elif isinstance(mesh, collections.abc.Sequence) and all(isinstance(d, array_type) for d in mesh):
            self._mesh = {"dims": mesh}
        else:
            self._mesh = mesh

        dims = [np.asarray(v) for v in dims]
        if len(dims) == 0:
            pass
        elif self._mesh is None:
            self._mesh = {"dims": dims, "periods": periods}
        elif not isinstance(self._mesh, collections.abc.Mapping):
            logger.warning(f"Function.__init__: mesh is  ignored! {len(dims)} {type(mesh)}")
        else:
            self._mesh["dims"] = dims
            if periods is not None:
                self._mesh["periods"] = periods

        self._ppoly = None

        self._fill_value = fill_value

        # if self._value is not None:
        #     self.validate(strict=True)

    def validate(self, value=None, strict=False) -> bool:
        """ 检查函数的定义域和值是否匹配 """

        m_shape = tuple(self.shape)

        v_shape = ()

        if value is None:
            value = self.__value__()

        if value is None:
            raise RuntimeError(f" value is None! {self.__str__()}")

        if isinstance(value, array_type):
            v_shape = tuple(value.shape)

        if (v_shape == m_shape) or (v_shape[:-1] == m_shape):
            return True
        elif strict:
            raise RuntimeError(f" value.shape is not match with mesh! {v_shape}!={m_shape} ")
        else:
            logger.warning(f" value.shape is not match with mesh! {v_shape}!={m_shape} ")
            return False

    def __duplicate__(self) -> Function:
        """ 复制一个新的 Function 对象 """
        other: Function = super().__duplicate__()
        other._value = self._value
        other._mesh = self._mesh
        return other

    def __serialize__(self) -> typing.Mapping: raise NotImplementedError(f"")

    @classmethod
    def __deserialize__(cls, desc: typing.Mapping) -> Function: raise NotImplementedError(f"")

    @property
    def empty(self) -> bool: return self._value is None and self._mesh is None and super().empty

    @property
    def __type_hint__(self) -> typing.Type:
        """ 获取函数的类型
        """
        orig_class = getattr(self, "__orig_class__", None)

        tp = typing.get_args(orig_class)[0]if orig_class is not None else None

        return tp if inspect.isclass(tp) else float

    @property
    def __mesh__(self) -> typing.Any:
        return self._mesh if self._mesh is not None else super().__mesh__

    @property
    def mesh(self) -> typing.Any: return self._mesh
    """ 函数的定义域，即函数的自变量的取值范围。"""

    @property
    def dimensions(self) -> typing.List[ArrayType]: return self.dims
    """ for rectlinear mesh 每个维度对应一个一维数组，为网格的节点。"""

    @property
    def dims(self) -> typing.List[ArrayType]: return try_get(self.__mesh__, "dims", None)
    """ alias of dimensions """

    @property
    def ndim(self) -> int: return len(self.dims) if self.dims is not None else 0
    """ 函数的维度，即定义域的秩 """

    @property
    def shape(self) -> typing.Tuple[int]: return tuple(len(d) for d in self.dims)
    """ 所需数组的形状 """

    @property
    def periods(self) -> typing.Tuple[float]: return try_get(self._mesh, "periods", None)

    @functools.cached_property
    def bbox(self) -> typing.Tuple[ArrayType, ArrayType]:
        """ bound box 返回包裹函数参数的取值范围的最小多维度超矩形（hyperrectangle） """
        if self.ndim == 1:
            return (np.min(self.dims), np.max(self.dims))
        else:
            return (np.asarray([np.min(d) for d in self.dims], dtype=float),
                    np.asarray([np.max(d) for d in self.dims], dtype=float))

    @functools.cached_property
    def points(self) -> typing.List[ArrayType]:
        if self.__mesh__ is None:
            raise RuntimeError(self.__mesh__)
        elif len(self.dims) == 1:
            return self.dims
        else:
            return np.meshgrid(*self.dims, indexing="ij")

    def __domain__(self, *args) -> bool:
        return np.bitwise_and.reduce([((args[i] >= self.bbox[0][i]) & (args[i] <= self.bbox[1][i])) for i in range(self.ndim)])

    # @property
    # def rank(self) -> int:
    #     """ 函数的秩，rank=1 标量函数， rank=3 矢量函数 None 待定 """
    #     if isinstance(self._value, array_type):
    #         return self._value.shape[-1]
    #     elif isinstance(self._value, tuple):
    #         return len(self._value)
    #     else:
    #         logger.warning(f"Function.rank is not defined!  {type(self._value)} default=1")
    #         return 1

    def __value__(self) -> ArrayType: return self._value
    """ 返回函数的数组 self._value """

    def __array__(self, dtype=None, *args, **kwargs) -> ArrayType:
        """ 重载 numpy 的 __array__ 运算符
                若 self._value 为 array_type 或标量类型 则返回函数执行的结果
        """
        res = self.__value__()

        if res is None or res is _not_found_ and self.callable:
            res = self._value = self.__call__(*self.points)

        if isinstance(res, numeric_type):
            res = np.asarray(res, dtype=self.__type_hint__ if dtype is None else dtype)
        else:
            raise TypeError(f" Can not get value {(res)}! fun={self.__str__()}")
        return res

    def __getitem__(self, *args) -> NumericType: raise NotImplementedError(f"Function.__getitem__ is not implemented!")

    def __setitem__(self, *args) -> None: raise RuntimeError("Function.__setitem__ is prohibited!")

    def _compile(self, *d, force=False, check_nan=True,  **kwargs) -> typing.Callable:
        """ 对函数进行编译，用插值函数替代原始表达式，提高运算速度

            NOTE：
                - 由 points，value  生成插值函数，并赋值给 self._ppoly。 插值函数相对原始表达式的优势是速度快，缺点是精度低。
                - 当函数为expression时，调用 value = self.__call__(*points) 。
            TODO:
                - 支持 JIT 编译, support JIT compile
                - 优化缓存
                - 支持多维插值
                - 支持多维求导，自动微分 auto diff
            -

        """
        if self.ndim == 1 and len(d) > 0:
            if len(d) != 1:
                raise RuntimeError(f" Univariate function has not partial_derivative!")
            ppoly = self._compile(check_nan=check_nan, **kwargs)
            if isinstance(ppoly, tuple):
                ppoly, opts, *_ = ppoly
            else:
                opts = None

            ppoly = ppoly.derivative(d[0])
            if isinstance(opts, collections.abc.Mapping):
                return ppoly, opts
            else:
                return ppoly
        elif self.ndim > 1 and len(d) > 0:
            ppoly = self._compile(check_nan=check_nan, **kwargs)
            if isinstance(ppoly, tuple):
                ppoly, opts, *_ = ppoly
            else:
                opts = None
            if all(v >= 0 for v in d):
                ppoly = ppoly.partial_derivative(*d)
            elif all(v <= 0 for v in d):
                ppoly = ppoly.antiderivative(*[-v for v in d])
            else:
                raise RuntimeError(f"illegal derivative order {d}")

            if isinstance(opts, collections.abc.Mapping):
                return ppoly, opts
            else:
                return ppoly
        elif self._ppoly is not None and not force:
            return self._ppoly

        value = self.__array__()

        if not isinstance(value, array_type):
            raise RuntimeError(f"Function.compile() incorrect value {self.__str__()} value={value}   ")
        elif len(value.shape) == 0 or value.shape == (1,):
            # 如果value是标量，无法插值，则返回 value 作为常函数
            return value

        #  获得坐标点 points
        points = self.points

        m_shape = points[0].shape

        # if all((d.shape if isinstance(d, array_type) else None) for d in points):  # 检查 points 的维度是否一致
        #     m_shape = points[0].shape
        # else:
        #     raise RuntimeError(f"Function.compile() incorrect points  shape  {self.__str__()} {points}")

        if len(value.shape) > len(m_shape):
            raise NotImplementedError(
                f"TODO: interpolate for rank >1 . {value.shape}!={m_shape}!  func={self.__str__()} ")
        elif tuple(value.shape) != tuple(m_shape):
            raise RuntimeError(
                f"Function.compile() incorrect value shape {value.shape}!={m_shape}! value={value} func={self.__str__()} ")

        if len(self.dims) == 1:
            x = self.dims[0]
            if check_nan:
                mark = np.isnan(value)
                nan_count = np.count_nonzero(mark)
                if nan_count > 0:
                    logger.warning(
                        f"{self.__class__.__name__}[{self.__str__()}]: Ignore {nan_count} NaN at {np.argwhere(mark)}.")
                    value = value[~mark]
                    x = x[~mark]

            ppoly = InterpolatedUnivariateSpline(x, value)
        elif len(self.dims) == 2:
            if check_nan:
                mark = np.isnan(value)
                nan_count = np.count_nonzero(mark)
                if nan_count > 0:
                    logger.warning(
                        f"{self.__class__.__name__}[{self.__str__()}]: Replace  {nan_count} NaN by 0 at {np.argwhere(mark)}.")
                    value[mark] = 0.0

            x, y = self.dims
            if isinstance(self.periods, collections.abc.Sequence):
                logger.warning(f"TODO: periods={self.periods}")

            ppoly = RectBivariateSpline(x, y, value), {"grid": False}

        else:
            raise NotImplementedError(f"Multidimensional interpolation for n>2 is not supported.! ndim={self.ndim} ")

        self._ppoly = ppoly
        return ppoly

    def compile(self, *args, **kwargs) -> Function:
        op, *opts = self._compile(*args, **kwargs)
        if len(opts) == 0:
            pass
        elif len(opts) > 0:
            opts = opts[0]
            op = functools.partial(op, **opts)
            if len(opts) > 1:
                logger.warning(f"Function.compile() ignore opts! {opts[1:]}")

        return self.__class__(None, op=op, mesh=self._mesh)

    def _fetch_op(self):
        """
            重载父类的 _fetch_op 方法，获得函数的插值函数

            Returns
            -------
            typing.Callable
                插值函数

        """
        if self._ppoly is not None:  # 如果已经编译过，则直接返回插值函数
            return self._ppoly
        elif self.callable:  # 如果是函数表达式，则返回函数表达式
            return super()._fetch_op()
        else:  # 否则，编译函数
            return self._compile()

    def __call__(self, *args, **kwargs) -> _T | ArrayType | Function:
        """  重载函数调用运算符
            Parameters
            ----------
            args : typing.Any
                位置参数,
            kwargs : typing.Any
        """
        if len(args) == 0:
            return self
        elif any(isinstance(a, Expression) for a in args):
            return Expression(*args, op=self, **kwargs)

        value = self.__value__()

        if isinstance(value, np.ndarray) and len(value.shape) == 0:
            value = value.item()
        elif isinstance(value, collections.abc.Sequence) and not isinstance(value, str):
            value = np.asarray(value)

        if self._mesh is None:  # constants function
            return value
        elif isinstance(value, scalar_type):
            if not isinstance(args[0], np.ndarray):
                return value

            res = np.full_like(args[0], value)

            bbox = self.bbox
            # 生成一个标记数组，标记 args 是否在 bbox 内
            marker = np.bitwise_and.reduce([((args[i] >= bbox[0][i]) & (args[i] <= bbox[1][i]))
                                            for i in range(self.ndim)])
            # 将标记数组转换为索引数组
            res[~marker] = self._fill_value
            return res
        elif isinstance(value, np.ndarray) and all(s == 1 for s in value.shape):
            if len(value.shape) == 0:
                value = value.item()
            else:
                value = np.squeeze(value)

            if not isinstance(args[0], np.ndarray):
                return value
            points = self.points
            marker = np.bitwise_and.reduce([(np.isclose(args[i], points[i][0])) for i in range(self.ndim)])
            res = np.full_like(args[0], value)
            res[~marker] = self._fill_value
            return res
        else:
            return super().__call__(*args,  **kwargs)

    def derivative(self, n=1) -> Function[_T]:
        return self.__class__(None, op=self._compile(n),  mesh=self._mesh, name=f"d_{n}({self.__str__()})")

    def d(self, n=1) -> Function[_T]: return self.derivative(n)

    def partial_derivative(self, *d) -> Function[_T]:
        if len(d) == 0:
            d = (1,)
        return self.__class__[_T](None, op=self._compile(*d), mesh=self._mesh, name=f"d_{d}({self.__str__()})")

    def pd(self, *d) -> Function[_T]: return self.partial_derivative(*d)

    def antiderivative(self, *d) -> Function[_T]:
        if len(d) == 0:
            d = (1,)
        return self.__class__(None, op=self._compile(*[-v for v in d]),  mesh=self._mesh,  name=f"I_{d}({self.__str__()})")

    def dln(self) -> Function[_T]: return self.derivative() / self

    def integral(self, *args, **kwargs) -> _T: return self._compile().integral(*args, **kwargs)

    def roots(self, *args, **kwargs) -> _T: return self._compile().roots(*args, **kwargs)


def function_like(y: NumericType, *args: NumericType, **kwargs) -> Function:
    if len(args) == 0 and isinstance(y, Function):
        return y
    else:
        return Function(y, *args, **kwargs)


class ConstantFunction(Function[_T]):

    def __call__(self, *args, **kwargs) -> _T | ArrayType:
        return super().__call__(*args, **kwargs)
