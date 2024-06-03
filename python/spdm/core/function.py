from __future__ import annotations

import typing
import functools
import collections
import numpy as np
import numpy.typing as np_tp
from copy import copy, deepcopy

from .typing import ArrayType, NumericType, array_type, get_args, get_origin, as_array
from .expression import Expression, zero
from .functor import Functor
from .path import update_tree, Path
from .domain import Domain
from .htree import List

from ..utils.logger import logger
from ..utils.tags import _not_found_
from ..numlib.interpolate import interpolate


class PPolyDomain(Domain):
    """多项式定义域。
    根据离散网格点构建插值
    """

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        if len(args) == 1 and isinstance(args[0], tuple):
            args = args[0]

        if all([isinstance(d, np.ndarray) for d in args]):
            self._points = args
        else:
            raise RuntimeError(f"Invalid points {args}")

    @property
    def points(self) -> typing.Tuple[ArrayType]:
        return self._points

    def interpolate(self, y: array_type, **kwargs):

        periods = self._metadata.get("periods", None)
        extrapolate = self._metadata.get("extrapolate", 0)

        return interpolate(*self.points, y, periods=periods, extrapolate=extrapolate, **kwargs)


class Function(Expression):
    """
    Function

    A function is a mapping between two sets, the _domain_ and the  _value_.
    The _value_  is the set of all possible outputs of the function.
    The _domain_ is the set of all possible inputs  to the function.

    函数定义域为多维空间时，网格采用rectlinear mesh，即每个维度网格表示为一个数组 _dims_ 。
    """

    Domain = PPolyDomain

    def __init__(self, *args, domain=None, value=None, **kwargs):
        """
        Parameters
        ----------
        *x : typing.Tuple[ArrayType]
            自变量
        y : ArrayType
            变量
        kwargs : 命名参数，
                *           : 用于传递给 Node 的参数
        extrapolate: int |str
            控制当自变量超出定义域后的值
            * if ext=0  or 'extrapolate', return the extrapolated value. 等于 定义域无限
            * if ext=1  or 'nan', return nan
        """
        func = None
        if len(args) > 0:
            if domain is None:
                domain = args[:-1]
            elif len(args) > 1:
                if isinstance(domain, dict):
                    domain["dims"] = args[:-1]
                else:
                    raise RuntimeError(f"Redefine domain {args[:-1]} or {domain}")

            if callable(args[-1]):
                func = args[-1]
            else:
                value = args[-1]

        super().__init__(func, domain=domain, value=value, **kwargs)

    def __getitem__(self, idx) -> NumericType:
        assert self._cache is not None, "Function is not indexable!"
        return self._cache[idx]

    def __setitem__(self, idx, value) -> None:
        assert self._cache is not None, "Function is not changable!"
        self._op = None
        self._cache[idx] = value

    @property
    def domain(self) -> Function.Domain:
        return super().domain

    def __compile__(self) -> typing.Callable[..., array_type]:
        """对函数进行编译，用插值函数替代原始表达式，提高运算速度
        - 由 points，value  生成插值函数，并赋值给 self._op
        插值函数相对原始表达式的优势是速度快，缺点是精度低。
        """
        if not callable(self._ppoly):
            if isinstance(self._cache, np.ndarray):
                self._ppoly = self.domain.interpolate(self._cache)
            elif callable(self._op):
                self._ppoly = self.domain.interpolate(self._op)
            else:
                raise RuntimeError(f"Function is not evaluable! {self._op} {self._cache}")

        return self._ppoly

    def validate(self, value=None, strict=False) -> bool:
        """检查函数的定义域和值是否匹配"""

        m_shape = tuple(self.shape)

        v_shape = ()

        if value is None:
            value = self._cache

        if value is None:
            raise RuntimeError(f" value is None! {self.__str__()}")

        if isinstance(value, array_type):
            v_shape = tuple(value.shape)

        if (v_shape == m_shape) or (v_shape[:-1] == m_shape):
            return True
        elif strict:
            raise RuntimeError(f" value.shape is not match with dims! {v_shape}!={m_shape} ")
        else:
            logger.warning(f" value.shape is not match with dims! {v_shape}!={m_shape} ")
            return False


class Polynomials(Expression):
    """A wrapper for numpy.polynomial
    TODO: imcomplete
    """

    def __init__(
        self,
        coeff,
        *args,
        type: str = None,
        domain=None,
        window=None,
        symbol="x",
        preprocess=None,
        postprocess=None,
        **kwargs,
    ) -> None:
        match type:
            case "chebyshev":
                from numpy.polynomial.chebyshev import Chebyshev

                Op = Chebyshev
            case "hermite":
                from numpy.polynomial.hermite import Hermite

                Op = Hermite
            case "hermite":
                from numpy.polynomial.hermite_e import HermiteE

                Op = HermiteE
            case "laguerre":
                from numpy.polynomial.laguerre import Laguerre

                Op = Laguerre
            case "legendre":
                from numpy.polynomial.legendre import Legendre

                Op = Legendre
            case _:  # "power"
                import numpy.polynomial.polynomial as polynomial

                Op = polynomial

        op = Op(coeff, domain=domain, window=window, symbol=symbol)

        super().__init__(op, *args, **kwargs)
        self._preprocess = preprocess
        self._postprocess = postprocess

    def __eval__(self, x: array_type | float, *args, **kwargs) -> array_type | float:
        if len(args) + len(kwargs) > 0:
            logger.warning(f"Ignore arguments {args} {kwargs}")

        if not isinstance(x, (array_type, float)):
            return super().__call__(x)

        if self._preprocess is not None:
            x = self._preprocess(x)

        y = self._op(x)

        if self._postprocess is not None:
            y = self._postprocess(y)

        return y


def function_like(y: NumericType, *args: NumericType, **kwargs) -> Function:
    if len(args) == 0 and isinstance(y, Function):
        return y
    else:
        return Function(y, *args, **kwargs)
