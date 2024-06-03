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
from ..utils.tree_utils import deep_merge_dict
from ..utils.logger import logger
from ..utils.tags import _not_found_

from .function import Function
from .functor import Functor


class Field(Function):
    """Field

    Field 是 Function 在流形（manifold/Mesh）上的推广， 用于描述流形上的标量场，矢量场，张量场等。

    Field 所在的流形记为 mesh ，可以是任意维度的，可以是任意形状的，可以是任意拓扑的，可以是任意坐标系的。

    Mesh 网格描述流形的几何结构，比如网格的拓扑结构，网格的几何结构，网格的坐标系等。

    Field 与 Function的区别：
        - Function 的 mesh 是一维数组表示dimensions/axis
        - Field 的 mesh 是 Mesh，用以表示复杂流形上的场。
    """

    Domain = Mesh

    def __init__(self, *args, mesh=None, domain=None, **kwargs):
        if domain is None:
            domain = mesh
        elif mesh is not None:
            if isinstance(mesh, dict) and isinstance(dict, dict):
                domain = deep_merge_dict(domain, mesh)
            else:
                raise RuntimeError(f"Redefine mesh or domain ! mesh={mesh}, domain={domain}")
            
        super().__init__(*args, domain=domain, **kwargs)

    @property
    def mesh(self) -> Mesh:
        return self.domain

    def __call__(self, *args, **kwargs) -> typing.Callable[..., ArrayType]:
        # if all([isinstance(a, (array_type, float, int)) for a in args]):
        #     return self.__compile__()(*args, **kwargs)
        # else:
        return super().__call__(*args, **kwargs)

    def __compile__(self) -> typing.Callable[..., array_type]:
        return super().__compile__()

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

    def derivative(self, order: int | typing.Tuple[int], **kwargs) -> Field:
        if isinstance(order, int) and order < 0:
            func = self.__compile__().antiderivative(*order)
            return Field(func, domain=self.domain, label=f"I_{{{order}}}{{{self._render_latex_()}}}")
        elif isinstance(order, collections.abc.Sequence):
            func = self.__compile__().partial_derivative(*order)
            return Field(func, domain=self.domain, label=f"d_{{{order}}}{{{self._render_latex_()}}}")
        else:
            func = self.__compile__().derivative(order)
            return Field(func, domain=self.domain, label=f"d_{{{order}}}{{{self._render_latex_()}}}")

    def antiderivative(self, order: int, *args, **kwargs) -> Field:
        raise NotImplementedError(f"")

    def partial_derivative(self, *args, **kwargs) -> Field:
        return self.derivative(args, **kwargs)
