from ..core.functor import Functor
from ..core.expression import Expression
from ..utils.typing import NumericType, as_array
import typing
from .interpolate import interpolate
import numpy as np


def integral(func, *args, **kwargs):
    return func.integral(*args, **kwargs)


def find_roots(func, *args, **kwargs) -> typing.Generator[typing.Any, None, None]:
    yield from func.find_roots(*args, **kwargs)
