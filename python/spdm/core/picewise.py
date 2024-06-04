from __future__ import annotations
import warnings
import typing
from copy import copy, deepcopy
import functools
import collections.abc
import numpy as np

from ..utils.typing import ArrayType
from ..utils.tags import _not_found_
from ..utils.typing import ArrayType, NumericType, array_type, as_array, is_scalar, is_array, numeric_type
from ..utils.logger import logger
from ..utils.misc import group_dict_by_prefix
from ..numlib.interpolate import interpolate

from .functor import Functor
from .entry import Entry
from .htree import HTreeNode, HTree, HTreeNode, List
from .domain import Domain
from .path import update_tree, Path
from .functor import Functor, DerivativeOp
from .expression import Expression

class Piecewise1(Expression):
    """PiecewiseFunction
    A piecewise function. 一维或多维，分段函数
    """

    def __init__(self, piecewise_func: typing.List[typing.Tuple[Expression | float | int, Expression]], **kwargs):
        super().__init__(None, **kwargs)
        self._piecewise = piecewise_func

    def __copy__(self) -> Piecewise:
        res = super().__copy__()
        res._piecewise = self._piecewise
        return res

    def __call__(self, *args, **kwargs) -> NumericType:
        if len(args) == 0:
            return self

        elif any([callable(val) for val in args]):
            return super().__call__(*args, **kwargs)

        elif isinstance(args[0], float):
            for func, cond in self._piecewise:
                if not cond(*args, **kwargs):
                    continue
                else:
                    res = func(*args, **kwargs)
                    break
            else:
                raise RuntimeError(f"Can not fit any condition! {args}")

            return res
        elif isinstance(args[0], array_type):
            res = np.full_like(args[0], np.nan)
            for func, cond in self._piecewise:
                marker = cond(*args, **kwargs)
                if callable(func):
                    _args = [(a[marker] if isinstance(a, array_type) else a) for a in args]
                    _kwargs = {k: (v[marker] if isinstance(v, array_type) else v) for k, v in kwargs.items()}
                    res[marker] = func(*_args, **_kwargs)
                else:
                    res[marker] = func

            return res
        else:
            raise TypeError(f"PiecewiseFunction only support single float or  1D array, {args}")


def piecewise(func_cond, size=None, **kwargs):
    if not isinstance(func_cond, list):
        raise TypeError(f"Illegal type {type(func_cond)}")
    elif all([isinstance(func, (array_type, float, int)) and isinstance(cond, array_type) for func, cond in func_cond]):
        res = np.full_like(func_cond[0][0], np.nan)
        for func, cond in func_cond:
            if np.sum(cond) == 0:
                continue
            if isinstance(func, array_type) and func.size == res.size:
                res[cond] = func[cond]
            else:
                res[cond] = func

        return res
    else:
        return Piecewise(func_cond, **kwargs)

