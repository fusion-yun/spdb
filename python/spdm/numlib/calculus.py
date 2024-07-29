import typing
import numpy as np
from jax import grad

from spdm.utils.tags import _not_found_

from spdm.core.functor import Functor
from spdm.core.expression import Expression
from spdm.utils.type_hint import NumericType, as_array
from spdm.utils.type_hint import ArrayType, NumericType, array_type, is_scalar, PrimaryType
from spdm.numlib.interpolate import interpolate


def integral(func, *args, **kwargs):
    return func.integral(*args, **kwargs)


def find_roots(func, *args, **kwargs) -> typing.Generator[typing.Any, None, None]:
    yield from func.find_roots(*args, **kwargs)


class Derivative(Expression):
    """导数表达式"""

    def __init__(self, *args, **kwargs):
        super().__init__(None, *args, **kwargs)

    @property
    def order(self) -> int:
        return self._kwargs.get("order", 1)

    def _render_latex_(self) -> str:
        expr: Expression = self._children[0]

        if expr is None or expr is _not_found_:
            return self.__label__

        match self.order:
            case 0:
                text = expr._render_latex_()
            case 1:
                text = f"d{expr._render_latex_()}"
            case -1:
                text = rf"\int \left({expr._render_latex_()} \right)"
            case -2:
                text = rf"\iint \left({expr._render_latex_()} \right)"
            case _:
                if self.order > 1:
                    text = rf"d_{{\left[{self.order}\right]}}{expr._render_latex_()}"
                elif self.order < 0:
                    text = rf"\intop^{{{-self.order}}}\left({expr._render_latex_()}\right)"
                else:
                    text = expr._render_latex_()
        return text

    def __compile__(self) -> typing.Callable[..., array_type]:
        if callable(self._ppoly):
            return self._ppoly

        expr = self._children[0]

        if isinstance(expr, Expression):
            expr_ppoly = expr.__compile__()
        elif not callable(expr):
            raise TypeError(f"{type(expr)} is not a Expression!")

        if expr_ppoly is None:
            raise RuntimeError(f"PPoly is None! {self}")
        elif not hasattr(expr_ppoly.__class__, "derivative"):
            raise RuntimeError(f"Can not not derivative PPoly {expr_ppoly.__class__}!")
        elif self.order > 0:
            self._ppoly = expr_ppoly.derivative(self.order)
        elif self.order < 0:
            self._ppoly = expr_ppoly.antiderivative(-self.order)
        else:
            self._ppoly = expr_ppoly

        if not callable(self._ppoly):
            raise RuntimeError(f"Failed to compile expression! {str(self)}")

        return self._ppoly


class Antiderivative(Derivative):
    """antiderivate 表达式"""

    def __init__(self, *args, order=1, **kwargs):
        super().__init__(*args, order=-order, **kwargs)


def derivative(*args, order=1, **kwargs) -> Derivative:
    func = Derivative(*args, order=order, **kwargs)
    if all([isinstance(d, (array_type, float, int)) for d in args[1:]]):
        _, *x = args
        return func(*x)
    else:
        return func


def antiderivative(*args, order=1, **kwargs) -> Derivative:
    return Antiderivative(*args, order=order, **kwargs)


class PartialDerivative(Derivative):
    def __repr__(self) -> str:
        return f"d_{{{self.order}}} ({Expression._repr_s(self._expr)})"


def partial_derivative(*args, **kwargs) -> PartialDerivative:
    return PartialDerivative(*args, **kwargs)
