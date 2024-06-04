from __future__ import annotations

import typing
import functools
import collections
import numpy as np
import numpy.typing as np_tp
import collections.abc
from copy import copy, deepcopy

from .expression import Expression, zero
from .functor import Functor
from .path import update_tree, Path
from .domain import Domain, PPolyDomain
from .htree import List

from ..utils.logger import logger
from ..utils.tags import _not_found_
from ..utils.typing import ArrayType, NumericType, array_type, get_args, get_origin, as_array


class Function(Expression):
    """
    Function

    A function is a mapping between two sets, the _domain_ and the  _value_.
    The _value_  is the set of all possible outputs of the function.
    The _domain_ is the set of all possible inputs  to the function.

    函数定义域为多维空间时，网格采用rectlinear mesh，即每个维度网格表示为一个数组 _dims_ 。
    """

    Domain = PPolyDomain

    def __init__(self, *args, domain=None, **metadata):
        """
        Parameters
        ----------
        *x : typing.Tuple[ArrayType]
            自变量
        y : ArrayType
            变量
        kwargs : 命名参数，
                *           : 用于传递给 Node 的参数
        """

        value = None
        if len(args) > 0:
            value = args[-1]

            if domain is None:
                domain = args[:-1]

        super().__init__(value, domain=domain, **metadata)

    def __getitem__(self, idx) -> NumericType:
        assert self._cache is not None, "Function is not indexable!"
        return self._cache[idx]

    def __setitem__(self, idx, value) -> None:
        assert self._op is not None, f"Function is not changable! op={self._op}"
        self._ppoly = None
        self._cache[idx] = value

    def __compile__(self) -> typing.Callable[..., array_type]:
        """对函数进行编译，用插值函数替代原始表达式，提高运算速度
        - 由 points，value  生成插值函数，并赋值给 self._op
        插值函数相对原始表达式的优势是速度快，缺点是精度低。
        """
        if self._ppoly is _not_found_:  # not callable(self._ppoly):
            if self._op is None and isinstance(self._cache, np.ndarray):
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
