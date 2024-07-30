import typing
import numpy as np


_T = typing.TypeVar("_T", bool, int, float, complex)


class Vector(np.ndarray[_T]):
    def __init__(self, *args):
        super().__init__(list(args))
