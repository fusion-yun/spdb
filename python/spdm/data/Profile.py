from __future__ import annotations

import collections.abc
import pprint
import typing
from enum import Enum
from functools import cached_property

import numpy as np

from spdm.utils.typing import ArrayType

from ..mesh.Mesh import Mesh
from ..utils.logger import logger
from ..utils.misc import group_dict_by_prefix
from ..utils.tags import _not_found_
from ..utils.typing import ArrayType, NumericType, numeric_type
from .Container import Container
from .Expression import Expression
from .Function import Function
from .Node import Node

_T = typing.TypeVar("_T")


class Profile(Function[_T], Node):
    """
    Profile
    ---------
    Profile= Function + Node 是具有 Function 特性的 Node。
    Function 的 value 由 Node.__value__ 提供，

    mesh 可以根据 kwargs 中的 coordinate* 从 Node 所在 Tree 获得

    """

    def __init__(self,   *args,   **kwargs) -> None:
        """
            Parameters
            ----------
            value : NumericType
                函数的值
            dims : typing.Any
                用于坐标轴(dims)，用于构建 Mesh
            kwargs : typing.Any
                    coordinate* : 给出各个坐标轴的path, 用于从 Node 所在 Tree 获得坐标轴(dims)
                    op_*        : 用于传递给运算符的参数
                    *           : 用于传递给 Node 的参数

        """

        super().__init__(*args, **kwargs)

    @property
    def data(self) -> ArrayType: return self.__value__

    @property
    def dims(self) -> Profile[_T]:
        """ 从 NodeTree 中获取 mesh 和 value """

        if self._dims is None and isinstance(self._parent, Node):
            coordinates, *_ = group_dict_by_prefix(self._metadata, "coordinate", sep=None)
            coordinates = {int(k): v for k, v in coordinates.items() if k.isdigit()}
            coordinates = dict(sorted(coordinates.items(), key=lambda x: x[0]))

            if len(coordinates) > 0:
                self._dims = tuple([(self._parent._find_node_by_path(c, prefix="../") if isinstance(c, str) else c)
                                    for c in coordinates.values()])

        return self._dims

    def derivative(self, n=1) -> Profile[_T]:
        other = super().derivative(n)
        other._parent = self._parent
        return other

    def partial_derivative(self, *d) -> Profile[_T]:
        other = super().partial_derivative(*d)
        other._parent = self._parent
        return other

    def antiderivative(self, *d) -> Profile[_T]:
        other = super().antiderivative(*d)
        other._parent = self._parent
        return other
