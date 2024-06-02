from __future__ import annotations

import typing

import numpy as np
from scipy.interpolate import CubicSpline, PPoly

from ..core.mesh import Mesh
from .mesh_rectilinear import RectilinearMesh


@Mesh.register('ppoly')
class PPolyMesh(RectilinearMesh):
    """Piecewise polynomial Mesh
    """

    def interpolator(self, y, **kwargs) -> PPoly:
        bc_type = self._metadata.get("bc_type", "not-a-knot")
        #  "periodic"         "periodic" if np.all(y[0] == y[-1]) else
        # return interp1d(*self.points, y, **kwargs)
        return CubicSpline(*self.xyz, y, bc_type=bc_type, **kwargs)


__SP_EXPORT__ = PPolyMesh

# class Function1D(Function[_T]):
#     """
#
#     """
#     def __init__(self, x, y,  **kwargs):
#         super().__init__(x, y, **kwargs)

#         if len(self._Mesh) == 0:
#             raise RuntimeError(f"Function must have at least one 'x' argument!")

#         # if len(args) == 0:
#         #     x = kwargs.get("x", 0)
#         #     y = kwargs.get("y", 0)
#         # elif len(args) == 1:
#         #     y = args[0]
#         #     x = None
#         # else:
#         #     x = args[0]
#         #     y = args[1]
#         #     if len(args) > 2:
#         #         raise RuntimeWarning(f"Too much position arguments {args}")
#         # if isinstance(self._x, np.ndarray):
#         #     assert(self._x[0] < self._x[-1])
#         # if y is None or (isinstance(y, (np.ndarray, collections.abc.Sequence)) and len(y) == 0):
#         #     self._data = 0

#         # if isinstance(y, Function):
#         #     if x is None:
#         #         x = y.x_domain
#         #         self._data = y._data
#         #     else:
#         #         self._data = y
#         # elif isinstance(y, PPoly):
#         #     self._data = y
#         #     if x is None:
#         #         x = y.x
#         # else:
#         #     self._data = y

#         # if x is None or len(x) == 0:
#         #     self._x = None
#         #     self._x_domain = [-np.inf, np.inf]
#         # elif isinstance(x, np.ndarray):
#         #     if len(x) == 0:
#         #         logger.error(f"{type(x)} {type(y)}")
#         #     self._x = x
#         #     self._x_domain = [x[0], x[-1]]
#         # elif isinstance(x, collections.abc.Sequence) and len(x) > 0:
#         #     self._x_domain = list(set(x))
#         #     if isinstance(y, np.ndarray):
#         #         self._x = np.linspace(
#         #             self._x_domain[0], self._x_domain[-1], len(y))
#         #     else:
#         #         self._x = None
#         # else:
#         #     self._x_domain = [-np.inf, np.inf]
#         #     self._x = None

#         # if self._data is None or self._data is _not_found_:
#         #     logger.warning(f"Empty function: x={self._x},y={self._data}")
#         # elif isinstance(self._data, np.ndarray) and (self._x is not None and self._x.shape != self._data.shape):
#         #     raise ValueError(f"x.shape  != y.shape {self._x.shape}!={self._data.shape}")
#     def __str__(self) -> str:
#         return pprint.pformat(self.__array__())
#     @property
#     def is_valid(self) -> bool:
#         return self._Mesh is not None and self._data is not None
#     @cached_property
#     def is_constant(self) -> bool:
#         return isinstance(self._data, (int, float))

# @cached_property
# def is_periodic(self) -> bool:
#     return self.is_constant \
#         or (isinstance(self._data, np.ndarray) and np.all(self._data[0] == self._data[-1])) \
#         or np.all(self.__call__(self.x_min) == self.__call__(self.x_max))
# @property
# def is_bounded(self):
#     return not (self.x_min == -np.inf or self.x_max == np.inf)
# @property
# def continuous(self) -> bool:
#     return len(self.x_domain) == 2
# @property
# def x_min(self) -> float:
#     return self.x_domain[0]
# @property
# def x_max(self) -> float:
#     return self.x_domain[-1]
# @property
# def _Mesh(self) -> np.ndarray:
#     return self._x  # type:ignore
# @_Mesh.setter
# def _Mesh(self, x: np.ndarray):
#     if isinstance(self._data, np.ndarray) and len(self._data) != len(x):
#         raise ValueError(f"len(x) != len(y) {len(x)} != {len(self._data)}")
#     self._x = x
# def setdefault_x(self, x):
#     if self._x is None:
#         self._Mesh = x
#     return self._x
# def __len__(self) -> int:
#     if self._Mesh is not None:
#         return len(self._Mesh)
#     else:
#         raise RuntimeError(f"Can not get length from {type(self._data)} or {type(self._Mesh)}")
# def __array__(self) -> np.ndarray:
#     if isinstance(self._data, np.ndarray):
#         return self._data
#     elif hasattr(self._data.__class__, "__entry__"):
#         v = self._data.__entry__().__value__()
#         if v is None or v is _not_found_:
#             raise ValueError(f"Can not get value from {self._data}")
#         self._data = np.asarray(v, dtype=self.__type_hint__)
#     else:
#         return self.__call__()
# @cached_property
# def __fun_op__(self) -> PPoly:
#     if isinstance(self._data,  PPoly):
#         return self._data
#     elif self._Mesh is None:
#         raise ValueError(f"_Mesh is None")
#     elif isinstance(self._data, np.ndarray):
#         assert (self._Mesh.size == self._data.size)
#         return create_spline(self._Mesh,  self._data)
#     else:
#         return create_spline(self._Mesh,  self.__call__(self._Mesh))
# def __call__(self, x=None, /,  **kwargs) -> typing.Union[np.ndarray, float]:
#     if x is None:
#         x = self._Mesh
#     if x is None:
#         raise RuntimeError(f"_Mesh is None!")
#     if x is self._Mesh and isinstance(self._data, np.ndarray):
#         return self._data
#     if self._data is None:
#         raise RuntimeError(f"Illegal function! y is None {self.__class__}")
#     elif isinstance(self._data, (int, float)):
#         if isinstance(x, np.ndarray):
#             return np.full(x.shape, self._data)
#         else:
#             return self._data
#     elif callable(self._data):
#         return np.asarray(self._data(x, **kwargs), dtype=float)
#     # elif hasattr(y, "__array__"):
#     #     y = y.__array__
#     elif x is not self._Mesh and isinstance(self._data, np.ndarray):
#         return self.__fun_op__(x, **kwargs)
#     else:
#         raise TypeError((type(x), (self._data)))
# def resample(self, x_min, x_max=None, /, **kwargs):
#     if x_min is None or (x_max is not None and x_min <= self.x_min and self.x_max <= x_max):
#         if len(kwargs) > 0:
#             logger.warning(f"ignore key-value arguments {kwargs.keys()}")
#             # TODO: Insert points in rapidly changing places.
#         return self
#     elif x_max is None:
#         return Function(x_min, self.__call__(x_min, **kwargs))
#     x_min = max(self.x_min, x_min)
#     x_max = min(self.x_max, x_max)
#     if x_min > x_max or np.isclose(x_min, x_max) or x_max <= self.x_min:
#         raise ValueError(f"{x_min,x_max}  not in  {self.x_min,self.x_max}")
#     elif isinstance(self._Mesh, np.ndarray):
#         idx_min = np.argmax(self._Mesh >= x_min)
#         idx_max = np.argmax(self._Mesh > x_max)
#         if idx_max > idx_min:
#             pass
#         elif idx_max == 0 and np.isclose(self._Mesh[-1], x_max):
#             idx_max = -1
#         else:
#             logger.debug((x_min, x_max, idx_min, idx_max, self._Mesh))
#         if isinstance(self._data, np.ndarray):
#             return Function(self._Mesh[idx_min:idx_max], self._data[idx_min:idx_max])
#         else:
#             return Function(self._Mesh[idx_min:idx_max],  self.__call__(self._Mesh[idx_min:idx_max]))
#     elif callable(self._data):
#         return Function([x_min, x_max], self._data)
#     else:
#         raise TypeError((type(self._Mesh), type(self._data)))
#         # return _Mesh, np.asarray(self.__call__(_Mesh), dtype=float)
# def __setitem__(self, idx, value):
#     if hasattr(self, "_interpolator"):
#         delattr(self, "_interpolator")
#     self.__real_array__()[idx] = value
# def _prepare(self, x, y):
#     if not isinstance(x, [collections.abc.Sequence, np.ndarray]):
#         x = np.asarray([x])
#     if isinstance(y, [collections.abc.Sequence, np.ndarray]):
#         y = np.asarray(y)
#     elif y is not None:
#         y = np.asarray([y])
#     else:
#         y = self.__call__(x)
#     return x, y
# def insert(self, x, y=None):
#     res = Function(*self._prepare(x, y), func=self._func)
#     raise NotImplementedError('Insert points!')
#     return res
# def __len__(self):
#     return len(self.x) if self.x is not None else 0
