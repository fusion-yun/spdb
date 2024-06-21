
import typing
import numpy as np


from spdm.core.functor import Functor
from spdm.core.expression import Expression
from spdm.utils.type_hint import NumericType, as_array
from spdm.numlib.interpolate import interpolate


def integral(func, *args, **kwargs):
    return func.integral(*args, **kwargs)


def find_roots(func, *args, **kwargs) -> typing.Generator[typing.Any, None, None]:
    yield from func.find_roots(*args, **kwargs)
