import collections.abc
import typing
from copy import copy

import numpy as np
from scipy.interpolate import (
    InterpolatedUnivariateSpline,
    RectBivariateSpline,
    RegularGridInterpolator,
    UnivariateSpline,
    interp1d,
    interp2d,
)

from ..core.functor import Functor
from ..utils.logger import logger
from ..utils.typing import array_type


class RectInterpolateOp(Functor):
    def __init__(self, *xy, periods=None, check_nan=False, extrapolate=1, **kwargs) -> None:
        super().__init__(None)

        if len(xy) == 0:
            raise RuntimeError(f"Illegal dims={xy} ")

        self._value = xy[-1]
        self._dims = xy[:-1]
        self._periods = periods
        self._opts: dict = kwargs
        self._check_nan = check_nan
        self._extrapolate = extrapolate
        self._shape = tuple(len(d) for d in self._dims)
        self._ppoly = None
        if isinstance(self._value, array_type) and len(self._value.shape) > 0:
            if len(self._value.shape) > len(self._shape):
                raise NotImplementedError(
                    f"TODO: interpolate for rank >1 . { self._value.shape}!={self._shape}!  {xy} func={self.__str__()} "
                )
            elif tuple(self._value.shape) != tuple(self._shape):
                raise RuntimeError(
                    f"Function.compile() incorrect value shape { self._value.shape}!={self._shape}! func={self.__str__()} "
                )

    @property
    def ppoly(self):
        if self._ppoly is not None:
            return self._ppoly

        if len(self._dims) == 0:
            raise RuntimeError(f"Illegal dims={self._dims} ")

        value = self._value

        if callable(value):
            value = value(*np.meshgrid(*self._dims, indexing="ij"))

        if not isinstance(value, array_type) or not np.all(value.shape == self._shape):
            raise TypeError((value))

        elif len(self._dims) == 1:
            x = self._dims[0]

            if len(x) == 0:
                raise RuntimeError(f"x is empty!")

            if self._check_nan:
                mark = np.isnan(value)
                nan_count = np.count_nonzero(mark)

                if nan_count == len(value):
                    raise RuntimeError(f"value is NaN!")
                elif nan_count > 0:
                    # logger.warning(  f"{self.__class__.__name__}[{self.__str__()}]: Ignore {nan_count} NaN at {np.argwhere(mark)}.")
                    value = value[~mark]
                    x = x[~mark]

            try:
                self._ppoly = InterpolatedUnivariateSpline(x, value, ext=self._extrapolate)    
            except Exception as error:
                raise RuntimeError(f"Can not create Interpolator! \n x={x} value={value}") from error

        elif len(self._dims) == 2:
            if self._check_nan:
                mark = np.isnan(value)
                nan_count = np.count_nonzero(mark)
                if nan_count > 0:
                    logger.warning(
                        f"{self.__class__.__name__}[{self.__str__()}]: Replace  {nan_count} NaN by 0 at {np.argwhere(mark)}."
                    )
                    value[mark] = 0.0

            # if isinstance(self.periods, collections.abc.Sequence):
            #     logger.warning(f"TODO: periods={self.periods}")

            self._ppoly = RectBivariateSpline(*self._dims, value)
            self._opts = {"grid": False}

        else:
            self._ppoly = RegularGridInterpolator(self._dims, value)

        return self._ppoly

    def __call__(self, *args, **kwargs) -> typing.Any:
        try:
            res = self.ppoly(*args, **kwargs, **self._opts)
        except ValueError as e:
            raise RuntimeError(f"{self.__class__.__name__}[{self.__str__()}]") from e
        except TypeError as e:
            raise TypeError(f"{args}") from e

        if not isinstance(args[0], array_type) or args[0].size == 1:
            return np.squeeze(res, axis=0).item()
        else:
            return res

    def derivative(self, n=1) -> Functor:
        return Functor(self.ppoly.derivative(n), **self._opts)

    def partial_derivative(self, *d) -> Functor:
        if len(d) > 0:
            label = f"d_({self.__str__()})"
        else:
            label = f"d_{d}({self.__str__()})"

        return Functor(self.ppoly.partial_derivative(*d), label=label, **self._opts)

    def antiderivative(self, *d) -> Functor:
        return Functor(self.ppoly.antiderivative(*d), **self._opts)


def interpolate(*args, type="rectlinear", **kwargs) -> Functor:
    match type:
        case "rectlinear":
            res = RectInterpolateOp(*args, **kwargs)
        case _:
            raise NotImplementedError(f"type={type}")
    return res
