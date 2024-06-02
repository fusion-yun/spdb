from __future__ import annotations

from copy import copy, deepcopy
import collections.abc
import functools
import typing
from enum import Enum
import numpy as np
import numpy.typing as np_tp

from spdm.core.typing import array_type

from .domain import Domain
from .typing import ArrayType, array_type, as_array, is_array
from .mesh import Mesh

from ..utils.logger import logger
from ..utils.tags import _not_found_

from .expression import Expression
from .functor import Functor


class Field(Expression):
    """Field

    Field 是 Function 在流形（manifold/Mesh）上的推广， 用于描述流形上的标量场，矢量场，张量场等。

    Field 所在的流形记为 mesh ，可以是任意维度的，可以是任意形状的，可以是任意拓扑的，可以是任意坐标系的。

    Mesh 网格描述流形的几何结构，比如网格的拓扑结构，网格的几何结构，网格的坐标系等。

    Field 与 Function的区别：
        - Function 的 mesh 是一维数组表示dimensions/axis
        - Field 的 mesh 是 Mesh，可以表示复杂流形上的场等。
    """

    Domain = Mesh

    def __init__(self, *args, value=None, domain=None, **kwargs):

        if len(args) == 0:
            raise RuntimeError(f"illegal x,y {args} ")

        if domain is None:
            domain = kwargs.pop("mesh", None)

        if len(args) > 0:
            value = args[-1]
            dims = args[:-1]

        if isinstance(value, (Functor, Expression)) or callable(value):
            func = value
            value = None
        else:
            func = None
            value = as_array(value)

        if isinstance(domain, dict):
            domain["dims"] = dims
        else:
            domain = dims

        super().__init__(func, domain=domain, value=value, **kwargs)

    def __geometry__(self, *args, label=None, **kwargs):
        return self.domain.view_geometry(self.__array__(), *args, label=label or self.__label__, **kwargs)

    def _repr_svg_(self) -> str:
        return self.domain.display(self.__array__(), label=self.__label__)

    @property
    def mesh(self) -> Mesh:
        return self.domain

    # def __call__(self, *args, **kwargs) -> typing.Callable[..., ArrayType]:
    #     if all([isinstance(a, (array_type, float, int)) for a in args]):
    #         return self.__compile__()(*args, **kwargs)
    #     else:
    #         return super().__call__(*args, **kwargs)
    # def __compile__(self) -> typing.Callable[..., array_type]:

    #     if not callable(self._ppoly):
    #         # 构建插值多项式近似
    #         self._ppoly = self.domain.interpolate(self._value)

    #     return self._ppoly

    def grad(self, n=1) -> Field:
        ppoly = self.__functor__()

        if isinstance(ppoly, tuple):
            ppoly, opts = ppoly
        else:
            opts = {}

        if self.mesh.ndim == 2 and n == 1:
            return Field(
                (ppoly.partial_derivative(1, 0), ppoly.partial_derivative(0, 1)),
                mesh=self.mesh,
                name=f"\\nabla({self.__str__()})",
                **opts,
            )
        elif self.mesh.ndim == 3 and n == 1:
            return Field(
                (
                    ppoly.partial_derivative(1, 0, 0),
                    ppoly.partial_derivative(0, 1, 0),
                    ppoly.partial_derivative(0, 0, 1),
                ),
                mesh=self.mesh,
                name=f"\\nabla({self.__str__()})",
                **opts,
            )
        elif self.mesh.ndim == 2 and n == 2:
            return Field(
                (ppoly.partial_derivative(2, 0), ppoly.partial_derivative(0, 2), ppoly.partial_derivative(1, 1)),
                mesh=self.mesh,
                name=f"\\nabla^{n}({self.__str__()})",
                **opts,
            )
        else:
            raise NotImplemented(f"TODO: ndim={self.mesh.ndim} n={n}")

    def __compile__(self):
        if self._ppoly is None:
            self._ppoly = self.domain.interpolate(self.__array__())
        return self._ppoly

    def derivative(self, order, *args, **kwargs) -> Field:
        if isinstance(order, int) and order < 0:
            func = self.__compile__().antiderivative(*order)
            return Field(func, domain=self.mesh, label=f"I_{{{order}}}{{{self._render_latex_()}}}")
        elif isinstance(order, collections.abc.Sequence):
            func = self.__compile__().partial_derivative(*order)
            return Field(func, domain=self.mesh, label=f"d_{{{order}}}{{{self._render_latex_()}}}")
        else:
            func = self.__compile__().derivative(order)
            return Field(func, domain=self.mesh, label=f"d_{{{order}}}{{{self._render_latex_()}}}")

    def antiderivative(self, order: int, *args, **kwargs) -> Field:
        raise NotImplementedError(f"")

    def partial_derivative(self, order: typing.Tuple[int, ...], *args, **kwargs) -> Field:
        return self.derivative(order, *args, **kwargs)
