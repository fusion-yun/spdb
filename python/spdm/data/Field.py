from __future__ import annotations

import collections.abc
import typing
from enum import Enum
import functools
import numpy as np

from ..mesh.Mesh import Mesh
from ..utils.logger import logger
from ..utils.misc import group_dict_by_prefix
from ..utils.tags import _not_found_
from ..utils.typing import ArrayType, NumericType, array_type, numeric_type
from .ExprNode import ExprNode
from .ExprOp import ExprOp
from .Node import Node
from .Expression import Expression

_T = typing.TypeVar("_T")


class Field(ExprNode[_T]):
    """ Field
        ---------
        Field 是 Function 在流形（manifold/Mesh）上的推广， 用于描述流形上的标量场，矢量场，张量场等。

        Field 所在的流形记为 mesh ，可以是任意维度的，可以是任意形状的，可以是任意拓扑的，可以是任意坐标系的。

        Mesh 网格描述流形的几何结构，比如网格的拓扑结构，网格的几何结构，网格的坐标系等。

        Field 与 Function的区别：
            - Function 的 mesh 是 多个一维数组表示dimensions/axis
            - Field 的 mesh 是 Mesh，可以表示复杂流形上的场等。

        当 Field 不做为 DTree 的节点时， 应直接由Function继承  Field(Function[_T])

    """

    def __init__(self, value, *args, name=None, **kwargs):

        mesh,  kwargs = group_dict_by_prefix(kwargs,  "mesh")

        super().__init__(value, **kwargs)

        if isinstance(mesh, Enum):
            self._mesh = {"type": mesh.name}
        elif isinstance(mesh, str):
            self._mesh = {"type":  mesh}
        elif isinstance(mesh, collections.abc.Sequence) and all(isinstance(d, array_type) for d in mesh):
            self._mesh = {"dims": mesh}
        else:
            self._mesh = mesh if mesh is not None else {}

        if isinstance(self._mesh, collections.abc.Mapping) and len(args) > 0:
            self._mesh["dims"] = args
        elif len(args) > 0:
            raise RuntimeError(f"ignore args={args}")

        self._ppoly = None

    @property
    def mesh(self): return self.__mesh__

    @property
    def __mesh__(self) -> Mesh:
        if isinstance(self._mesh, Mesh):
            return self._mesh

        mesh_desc, metadata = group_dict_by_prefix(self._metadata, "mesh")

        if self._mesh is None:
            self._mesh = mesh_desc
        elif isinstance(self._mesh, collections.abc.Mapping) and mesh_desc is not None:
            self._mesh.update(mesh_desc)
        # else:
        #     raise TypeError(f"self._mesh={self._mesh} is not a Mapping")

        if isinstance(self._parent, Node):
            coordinates, *_ = group_dict_by_prefix(metadata, "coordinate", sep=None)
            coordinates = {int(k): v for k, v in coordinates.items() if k.isdigit()}
            coordinates = dict(sorted(coordinates.items(), key=lambda x: x[0]))

            if len(coordinates) == 0:
                pass
            elif all([isinstance(c, str) and c.startswith('../grid') for c in coordinates.values()]):
                o_mesh = getattr(self._parent, "grid", None)
                if isinstance(o_mesh, Mesh):
                    if len(self._mesh) > 0:
                        logger.warning(f"Ignore {self._mesh}")
                    self._mesh = o_mesh
                elif isinstance(o_mesh, collections.abc.Sequence):
                    self._mesh["dims"] = o_mesh
                elif isinstance(o_mesh, collections.abc.Mapping):
                    self._mesh.update(o_mesh)
                elif o_mesh is not None:
                    raise RuntimeError(f"self._parent.grid is not a Mesh, but {type(o_mesh)}")
            else:
                if self._mesh is None:
                    self._mesh = {}
                self._mesh["dims"] = tuple([(self._parent._find_node_by_path(c, prefix="../") if isinstance(c, str) else c)
                                            for c in coordinates.values()])

        if isinstance(self._mesh, collections.abc.Mapping):
            self._mesh = Mesh(**self._mesh)

        if not isinstance(self._mesh, Mesh):
            raise RuntimeError(f"self._mesh is not a Mesh, but {type(self._mesh)}")

        return self._mesh

    def __domain__(self, *xargs) -> bool: return self.__mesh__.geometry.enclose(*xargs)

    @property
    def points(self) -> typing.List[ArrayType]: return self.__mesh__.points

    def _compile(self, *d, force=False, **kwargs) -> ExprOp:

        if self._ppoly is not None and len(d) == 0 and not force:
            return self._ppoly

        value = self.__array__()

        if value.size == 1:
            # 如果value是标量，无法插值，则返回 value 作为常函数
            return np.squeeze(value).item()

        if tuple(value.shape) != tuple(self.__mesh__.shape):
            raise NotImplementedError(f"{value.shape}!={self.__mesh__.shape}")

        if len(d) == 0 or all(v == 0 for v in d):
            self._ppoly = self.__mesh__.interpolator(value)
            return self._ppoly
        elif self.__mesh__.ndim == 1 and len(d) == 1:
            return self.__mesh__.derivative(d[0], value)
        elif self.__mesh__.ndim == 2 and d == (1,):
            return self._compile(1, 0, **kwargs), self._compile(0, 1, **kwargs)
        elif self.__mesh__.ndim == 3 and d == (1,):
            return self._compile(1, 0, 0, **kwargs), self._compile(0, 1, 0, **kwargs), self._compile(0, 0, 1, **kwargs)
        elif len(d) == 1:
            raise NotImplementedError(f"ndim={self.__mesh__.ndim} d={d}")
        elif len(d) != self.__mesh__.ndim:
            raise RuntimeError(f"Illegal! ndim={self.__mesh__.ndim} d={d}")
        elif all(v == 0 for v in d) and hasattr(self.__mesh__, "interpolator"):
            return self.__mesh__.interpolator(value)
        elif all(v >= 0 for v in d) and hasattr(self.__mesh__, "partial_derivative"):
            return self.__mesh__.partial_derivative(d, value)
        elif all(v <= 0 for v in d) and hasattr(self.__mesh__, "antiderivative"):
            return self.__mesh__.antiderivative([-v for v in d], value)
        else:
            raise NotImplementedError(f"TODO: {d}")

    def compile(self, *d, **kwargs) -> Field[_T]:
        op, *opts = self._compile(*d, **kwargs)
        if len(opts) == 0:
            pass
        elif len(opts) > 0:
            opts = opts[0]
            op = functools.partial(op, **opts)
            if len(opts) > 1:
                logger.warning(f"Function.compile() ignore opts! {opts[1:]}")
        if op is None:
            raise RuntimeError(f"Function.compile() failed! {self.__str__()} ")

        return Field[_T](op, mesh=self.__mesh__, name=f"[{self.__str__()}]")

    def grad(self, n=1) -> Field:
        ppoly = self._compile()

        if isinstance(ppoly, tuple):
            ppoly, opts = ppoly
        else:
            opts = {}

        if self.__mesh__.ndim == 2 and n == 1:
            return Field[typing.Tuple[_T, _T]]((ppoly.partial_derivative(1, 0),
                                                ppoly.partial_derivative(0, 1)),
                                               mesh=self.__mesh__,
                                               name=f"\\nabla({self.__str__()})", **opts)
        elif self.__mesh__.ndim == 3 and n == 1:
            return Field[typing.Tuple[_T, _T, _T]]((ppoly.partial_derivative(1, 0, 0),
                                                    ppoly.partial_derivative(0, 1, 0),
                                                    ppoly.partial_derivative(0, 0, 1)),
                                                   mesh=self.__mesh__,
                                                   name=f"\\nabla({self.__str__()})", **opts)
        elif self.__mesh__.ndim == 2 and n == 2:
            return Field[typing.Tuple[_T, _T, _T]]((ppoly.partial_derivative(2, 0),
                                                    ppoly.partial_derivative(0, 2),
                                                    ppoly.partial_derivative(1, 1)),
                                                   mesh=self.__mesh__,
                                                   name=f"\\nabla^{n}({self.__str__()})", **opts)
        else:
            raise NotImplemented(f"TODO: ndim={self.__mesh__.ndim} n={n}")

    def derivative(self, n=1) -> Field[_T]:
        return Field[_T](super().derivative(n), mesh=self.__mesh__)

    def partial_derivative(self, *d) -> Expression[_T]:
        return Field[_T](super().partial_derivative(*d), mesh=self.__mesh__)

    def antiderivative(self, *d) -> Expression[_T]:
        return Field[_T](super().antiderivative(*d), mesh=self.__mesh__)
