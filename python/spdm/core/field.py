from __future__ import annotations

from copy import copy, deepcopy
import collections.abc
import functools
import typing
from enum import Enum
import numpy as np

from ..utils.logger import logger
from ..utils.tags import _not_found_
from ..utils.typing import ArrayType, array_type, as_array, is_array

from .mesh import Mesh
from .expression import Expression
from .domain import Domain


class Field(Expression):
    """Field

    Field 是 Function 在流形（manifold/Mesh）上的推广， 用于描述流形上的标量场，矢量场，张量场等。

    Field 所在的流形记为 mesh ，可以是任意维度的，可以是任意形状的，可以是任意拓扑的，可以是任意坐标系的。

    Mesh 网格描述流形的几何结构，比如网格的拓扑结构，网格的几何结构，网格的坐标系等。

    Field 与 Function的区别：
        - Function 的 mesh 是一维数组表示dimensions/axis
        - Field 的 mesh 是 Mesh，用以表示复杂流形上的场。
    """

    Domain = Mesh

    def __init__(self, *args, mesh=_not_found_, **kwargs):
        """
        Usage:
            default:
                Field(value,mesh=CurvilinearMesh(),**kwargs)

            alternate:

                Field(x,y,z,**kwargs) =>  Field(z,mesh={"dims":(x,y)}, **kwargs)

                Field(x,y,z,mesh={"@type":"curvilinear"},**kwargs) =>  Field(z,mesh={"@type":"curvilinear","dims":(x,y)}, **kwargs)

        """
        match len(args):
            case 0:
                value = None
                dims = None
            case 1:
                value = args[0]
                dims = None
            case _:
                value = args[-1]
                dims = args[:-1]

        if dims is None:
            pass
        elif mesh is None:
            mesh = {"dims": dims}
        elif isinstance(mesh, collections.abc.Mapping):
            mesh = collections.ChainMap({"dims": dims}, mesh)
        else:
            raise TypeError(f"illegal mesh type! {type(mesh)}")

        super().__init__(value, domain=mesh, **kwargs)

    @property
    def mesh(self) -> Mesh:
        return self.domain

    def _repr_svg_(self) -> str:
        from ..view import sp_view

        return sp_view.display(self.__view__(), label=self.__label__, output="svg")

    def __view__(self, **kwargs):
        if self.domain is None:
            return {}
        else:
            return self.domain.view(self, label=self.__label__, **kwargs)

    def __compile__(self) -> typing.Callable[..., array_type]:
        """对函数进行编译，用插值函数替代原始表达式，提高运算速度
        - 由 points，value  生成插值函数，并赋值给 self._op
        插值函数相对原始表达式的优势是速度快，缺点是精度低。
        """
        if not callable(self._ppoly):
            if isinstance(self._cache, np.ndarray):
                self._ppoly = self.domain.interpolate(self._cache)
            elif callable(self._op):
                self._ppoly = self.domain.interpolate(self._op)
            else:
                raise RuntimeError(f"Function is not evaluable! {self._op} {self._cache}")

        return self._ppoly

    def __call__(self, *args, **kwargs) -> typing.Callable[..., ArrayType]:
        if all([isinstance(a, (array_type, float, int)) for a in args]):
            return self.__compile__()(*args, **kwargs)
        else:
            return super().__call__(*args, **kwargs)

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
            return Field(func, mesh=self.mesh, label=f"I_{{{order}}}{{{self._render_latex_()}}}")
        elif isinstance(order, collections.abc.Sequence):
            func = self.__compile__().partial_derivative(*order)
            return Field(func, mesh=self.mesh, label=f"d_{{{order}}}{{{self._render_latex_()}}}")
        else:
            func = self.__compile__().derivative(order)
            return Field(func, mesh=self.mesh, label=f"d_{{{order}}}{{{self._render_latex_()}}}")

    def antiderivative(self, order: int, *args, **kwargs) -> Field:
        raise NotImplementedError(f"")

    def partial_derivative(self, *args, **kwargs) -> Field:
        return self.derivative(args, **kwargs)
