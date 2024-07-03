import typing
from copy import copy

import numpy as np

from spdm.utils.logger import logger
from spdm.utils.type_hint import NumericType, as_array, numeric_type, scalar_type

ExprOpLike = typing.Callable | None


class Functor:
    """
    算符: 用于表示一个运算符，可以是函数，也可以是类的成员函数
    受 np.ufunc 启发而来。
    可以通过 ExprOp(op, method=method) 的方式构建一个 ExprOp 对象。
    """

    """
    ExprNode
    ---------
    ExprNode= Function + Node 是具有 Function 特性的 Node。
    Function 的 value 由 Node.__value__ 提供，

    mesh 可以根据 kwargs 中的 coordinate* 从 Node 所在 Tree 获得

    """

    def __init__(self, func: typing.Callable | None, /, method: str | None = None, label: str = None, **kwargs) -> None:
        self._func = func
        self._method = method
        self._label = label
        self._opts = kwargs

    def __copy__(self) -> typing.Self:
        """复制一个新的 Function 对象"""
        other: Functor = object.__new__(self.__class__)  # type:ignore
        other.__copy_from_(self)
        return other

    def __copy_from_(self, other: typing.Self) -> typing.Self:
        """复制一个新的 Function 对象"""
        self._func = other._func
        self._method = other._method
        self._label = other._label
        self._opts = copy(other._opts)
        return self

    @property
    def __label__(self) -> str:
        return self._label or str(self._func)

    @property
    def __annotation__(self) -> str:
        units = self._opts.get("units", "")
        label = self._opts.get("label", None)
        if label is not None:
            return f"{label}  {units}"
        else:
            return units

    def __domain__(self, *args, **kwargs):
        return True

    def __str__(self) -> str:
        return self.__label__

    def __call__(self, *args, **kwargs):
        if isinstance(getattr(self, "_method", None), str):
            op = getattr(self._func, self._method, None)
        elif self._method is not None:
            raise ValueError(self._method)
        else:
            op = self._func

        if not callable(op):
            return op

        try:
            kwargs.update(self._opts)
            value = op(*args, **kwargs)
        except Exception as error:
            raise RuntimeError(f"Error when apply  op={op} args={args} kwargs={kwargs}!") from error

        return value


class ConstantsFunc(Functor):
    def __init__(self, value: NumericType, **kwargs) -> None:
        super().__init__(None, **kwargs)
        if not isinstance(value, scalar_type):
            raise TypeError(f"value={value} is not a scalar!")
        self._value = value

    def __label__(self) -> str:
        return f"{self._value}"

    def __call__(self, *args, **kwargs):
        if len(args) > 0 and isinstance(args[0], np.ndarray):
            return np.full_like(args[0], self._value)
        else:
            return self._value


class SetpFun(Functor):
    def __init__(self, y: NumericType, *xargs, y0: NumericType = 0.0, **kwargs) -> None:
        super().__init__(None, **kwargs)
        self._y1 = y
        self._y0 = y0
        self._xargs = xargs

    def __label__(self) -> str:
        return r"H"

    def __call__(self, *args, **kwargs):
        return self._y1 if np.all(self._xargs > as_array(args)) else self._y0


class DiracDeltaFun(Functor):
    def __init__(self, y: NumericType, *xargs, y0: NumericType = 0.0, **kwargs) -> None:
        super().__init__(None, **kwargs)
        self._y1 = y
        self._y0 = y0
        self._xargs = xargs

    def __label__(self) -> str:
        return r"\delta"

    def derivative(self, n=1) -> SetpFun:
        if n == 1:
            return SetpFun(self._y1, self._xargs, y0=self._y0)
        else:
            raise NotImplementedError(f"n={n}")

    def __call__(self, *args, **kwargs):
        return self._y1 if np.allclose(self._xargs, as_array(args)) else self._y0


class DerivativeOp(Functor):
    """微分/积分算符"""

    def __init__(self, order, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._order = order

    def __copy__(self) -> typing.Self:
        res: DerivativeOp = super().__copy__()
        res._order = self._order
        return res

    @property
    def order(self) -> int | None:
        return self._order

        # return rf"\frac{{d({Expression._repr_s(self._children[1])})}}{{{Expression._repr_s(self._children[0])}}}"

    def _ppoly(self, *args, **kwargs):
        # if isinstance(self._expr, Variable):
        #     y = self._expr(*args)
        #     x = args[0]
        # elif isinstance(self._expr, Expression):
        #     x = self._expr.domain.points[0]
        #     y = self._expr(*args)
        return interpolate(*args, self._expr(*args)), args

    def __functor__(self):
        return self._expr.derivative(self._order)


def as_functor(expr, *args, **kwargs) -> Functor | None:
    if isinstance(expr, Functor):
        return expr
    elif callable(expr):
        return Functor(expr, *args, **kwargs)
    elif expr is None:
        return None
    else:
        raise TypeError(f"expr={expr} is not callable!")
