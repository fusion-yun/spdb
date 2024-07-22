import collections.abc
import typing
import numpy as np

from spdm.utils.logger import logger
from spdm.utils.tags import _not_found_
from spdm.utils.type_hint import ArrayType, array_type
from spdm.core.path import Path
from spdm.core.mesh import Mesh
from spdm.core.expression import Expression


# def make_mesh(*dims):
#     # if isinstance(mesh, Mesh):
#     #     if len(dims) > 0:
#     #         logger.warning(f"Ignore dims {dims}")
#     #     return mesh
#     # if mesh is _not_found_:
#     #     mesh = {}
#     # elif isinstance(mesh, str):
#     #     mesh = {"type": mesh}
#     # elif not isinstance(mesh, dict):
#     #     raise TypeError(f"Illegal mesh type! {mesh}")

#     if len(dims) == 0:
#         return None

#     mesh = {}

#     if not all(isinstance(d, np.ndarray) for d in dims):
#         raise TypeError(f"Illegal dims! {dims}")
#     elif all(d.ndim == 1 for d in dims):
#         mesh.setdefault("type", "rectilinear")
#         mesh["dims"] = dims
#     elif all(d.shape == dims[0].shape for d in dims[1:]) and len(dims[0].shape) == len(dims):
#         mesh.setdefault("type", "curvilinear")
#         mesh["dims"] = dims
#     else:
#         raise RuntimeError(f"Can not make mesh from {mesh}")

#     return Mesh(mesh)


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

    def __init__(self, *args, mesh=None, **kwargs):
        """
        Usage:
            default:
                Field(value,mesh=CurvilinearMesh(),**kwargs)

            alternate:

                Field(x,y,z,**kwargs) =>  Field(z,mesh={"dims":(x,y)}, **kwargs)

                Field(x,y,z,mesh={"type":"curvilinear"},**kwargs) =>  Field(z,mesh={"type":"curvilinear","dims":(x,y)}, **kwargs)

        """
        # value = _not_found_ if len(args) == 0 else args[-1]

        # if mesh is _not_found_:
        #     obj = kwargs.get("_parent", _not_found_)
        #     while obj is not _not_found_:
        #         if (metadata := getattr(obj, "_metadata", _not_found_)) is not _not_found_:
        #             mesh = metadata.get("domain", _not_found_)
        #             if mesh is not _not_found_:
        #                 mesh = getattr(obj, mesh, _not_found_)
        #         if mesh is not _not_found_:
        #             break
        #         obj = getattr(obj, "_parent", _not_found_)

        if mesh is None and len(args) > 1:
            dims = args[:-1]
            mesh = {}

            if not all(isinstance(d, np.ndarray) for d in dims):
                raise TypeError(f"Illegal dims! {dims}")
            elif all(d.ndim == 1 for d in dims):
                mesh.setdefault("type", "rectilinear")
                mesh["dims"] = dims
            elif all(d.shape == dims[0].shape for d in dims[1:]) and len(dims[0].shape) == len(dims):
                mesh.setdefault("type", "curvilinear")
                mesh["dims"] = dims

        super().__init__(*args[-1:], domain=mesh, **kwargs)

    @property
    def mesh(self) -> Mesh:
        return self.domain

    def __view__(self, **kwargs):
        if self.domain is None:
            return {}
        else:
            return self.domain.view(self, label=str(self), **kwargs)

    def __compile__(self) -> typing.Callable[..., array_type]:
        """对函数进行编译，用插值函数替代原始表达式，提高运算速度
        - 由 points，value  生成插值函数，并赋值给 self._op
        插值函数相对原始表达式的优势是速度快，缺点是精度低。
        """
        if not callable(self._ppoly):
            if self._cache is _not_found_ and self._entry is not None:
                self._cache = self._entry.get()

            if self._cache is not _not_found_:
                self._ppoly = self.domain.interpolate(self._cache)
            elif callable(self._op):
                self._ppoly = self.domain.interpolate(self._op)
            else:
                raise RuntimeError(f"Function is not evaluable! {self._op} {self._cache}")

        return self._ppoly

    def _eval(self, *args, **kwargs) -> typing.Callable[..., ArrayType]:
        return self.__compile__()(*args, **kwargs)

    def grad(self, n=1) -> typing.Self:
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

    def derivative(self, order: int | typing.Tuple[int], **kwargs) -> typing.Self:
        if isinstance(order, int) and order < 0:
            func = self.__compile__().antiderivative(*order)
            return Field(func, mesh=self.mesh, label=f"I_{{{order}}}{{{self._render_latex_()}}}")
        elif isinstance(order, collections.abc.Sequence):
            func = self.__compile__().partial_derivative(*order)
            return Field(func, mesh=self.mesh, label=f"d_{{{order}}}{{{self._render_latex_()}}}")
        else:
            func = self.__compile__().derivative(order)
            return Field(func, mesh=self.mesh, label=f"d_{{{order}}}{{{self._render_latex_()}}}")

    def antiderivative(self, order: int, *args, **kwargs) -> typing.Self:
        raise NotImplementedError(f"")

    def partial_derivative(self, *args, **kwargs) -> typing.Self:
        return self.derivative(args, **kwargs)
