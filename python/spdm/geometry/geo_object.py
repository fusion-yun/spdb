from __future__ import annotations

import collections.abc
import typing
import uuid
from copy import copy
import numpy as np

from ..core.pluggable import Pluggable
from ..core.typing import array_type
from ..utils.logger import logger

from .bbox import BBox


class GeoObject(Pluggable):
    """Geomertic object
    几何对象，包括点、线、面、体等

    TODO:
        - 支持3D可视化 （Jupyter+？）

    """

    _plugin_prefix = "spdm.geometry"
    _plugin_registry = {}

    def __new__(cls, *args, **kwargs) -> None:
        """ """

        if len(args) > 0 and isinstance(args[0], dict):
            geo_type = args[0].get("$class", None)
        else:
            geo_type = kwargs.pop("type", None)

        # if isinstance(_geo_type, str):
        #     _geo_type = [_geo_type,
        #                  f"spdm.geometry.{_geo_type}#{_geo_type}",
        #                  f"spdm.geometry.{_geo_type}{cls.__name__}#{_geo_type}{cls.__name__}",
        #                  f"spdm.geometry.{_geo_type.capitalize()}#{_geo_type.capitalize()}",
        #                  f"spdm.geometry.{_geo_type.capitalize()}{cls.__name__}#{_geo_type.capitalize()}{cls.__name__}",
        #                  f"spdm.geometry.{cls.__name__}#{_geo_type}"
        #                  ]
        return super().__new__(cls, geo_type)

    def __init__(self, *args, ndim: int = 0, rank: int = -1, **kwargs) -> None:
        self._ndim = ndim
        self._rank = rank if rank >= 0 else ndim

        self._metadata: dict = kwargs.pop("metadata", {})
        self._metadata.update(kwargs)
        self._metadata.setdefault("name", f"{self.__class__.__name__}_{uuid.uuid1()}")

    def __copy__(self) -> GeoObject:
        other: GeoObject = super().__new__(self.__class__)
        other._metadata = copy(self._metadata)
        other._ndim = self._ndim
        other._rank = self._rank
        return other
        # return self.__class__(rank=self.rank, ndim=self.ndim, **self._metadata)

    # def _repr_html_(self) -> str:
    #     """Jupyter 通过调用 _repr_html_ 显示对象"""
    #     from ..view.View import display
    #     return display(self, schema="html")

    def _repr_svg_(self) -> str:
        """Jupyter 通过调用 _repr_html_ 显示对象"""

        from ..view.sp_view import display

        return display(self, schema="svg")

    def __equal__(self, other: GeoObject) -> bool:
        return (
            isinstance(other, GeoObject)
            and self.rank == other.rank
            and self.ndim == other.ndim
            and self.bbox == other.bbox
        )

    @property
    def name(self) -> str:
        return self._metadata.get("name", "unnamed")

    @property
    def rank(self) -> int:
        return self._rank

    """ 几何体（流形）维度  rank <=ndims

            0: point
            1: curve
            2: surface
            3: volume
            >=4: not defined
        The rank of a geometric object refers to the number of independent directions
        in which it extends. For example, a point has rank 0, a line has rank 1,
        a plane has rank 2, and a volume has rank 3.
    """

    @property
    def number_of_dimensions(self) -> int:
        return self._ndim

    """ 几何体所处的空间维度， = 0，1，2，3 ,...
        The dimension of a geometric object, on the other hand, refers to the minimum number of
        coordinates needed to specify any point within it. In general, the rank and dimension of
        a geometric object are the same. However, there are some cases where they can differ.
        For example, a curve that is embedded in three-dimensional space has rank 1 because
        it extends in only one independent direction, but it has dimension 3 because three
        coordinates are needed to specify any point on the curve.
    """

    @property
    def ndim(self) -> int:
        return self._ndim

    """ alias of dimension """

    @property
    def boundary(self) -> GeoObject | None:
        """boundary of geometry which is a geometry of rank-1"""
        if self.is_closed:
            return None
        else:
            raise NotImplementedError(f"{self.__class__.__name__}.boundary")

    @property
    def is_convex(self) -> bool:
        return self._metadata.get("convex", True)

    """ is convex """

    @property
    def is_closed(self) -> bool:
        return self._metadata.get("closed", True)

    @property
    def bbox(self) -> BBox:
        raise NotImplementedError(f"{self.__class__.__name__}.bbox")

    """ boundary box of geometry [ [...min], [...max] ] """

    @property
    def measure(self) -> float:
        return self.bbox.measure

    """ measure of geometry, length,area,volume,etc. 默认为 bbox 的体积 """

    def enclose(self, *args) -> bool | array_type:
        """Return True if all args are inside the geometry, False otherwise."""
        return False if not self.is_closed else self.bbox.enclose(*args)

    def intersection(self, other: GeoObject) -> typing.List[GeoObject]:
        """Return the intersection of self with other."""
        return [self.bbox.intersection(other.bbox)]

    def reflect(self, point0, point1) -> GeoObject:
        """reflect  by line"""
        other = copy(self)
        other._metadata["name"] = f"{self.name}_reflect"
        other.bbox.reflect(point0, point1)
        return other

    def rotate(self, angle, axis=None) -> GeoObject:
        """rotate  by angle and axis"""
        other = copy(self)
        other._metadata["name"] = f"{self.name}_rotate"
        other.bbox.rotate(angle, axis=axis)
        return other

    def scale(self, *s, point=None) -> GeoObject:
        """scale self by *s, point"""
        other = copy(self)
        other._metadata["name"] = f"{self.name}_scale"
        other.bbox.scale(*s, point=point)
        return other

    def translate(self, *shift) -> GeoObject:
        other = copy(self)
        other._metadata["name"] = f"{self.name}_translate"
        other.bbox.translate(*shift)
        return other

    def trim(self):
        raise NotImplementedError(f"{self.__class__.__name__}.trim")

    @staticmethod
    def _normal_points(*args) -> np.ndarray | typing.List[float]:
        if len(args) == 0:
            return []
        elif len(args) == 1:
            return args[0]
        elif isinstance(args[0], (int, float, bool, complex)):
            return list(args)
        elif isinstance(args[0], collections.abc.Sequence):
            return np.asarray([GeoObject._normal_points(*p) for p in args])
        else:
            raise TypeError(f"args has wrong type {type(args[0])} {args}")


_TG = typing.TypeVar("_TG")


class GeoObjectSet(typing.List[GeoObject]):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args)
        rank = kwargs.pop("rank", None)
        ndim = kwargs.pop("ndim", None)
        if rank is None:
            ranks = [obj.rank for obj in self if isinstance(obj, GeoObject)]
            rank = max(ranks) if len(ranks) > 0 else 0

        if ndim is None:
            ndim_list = [obj.ndim for obj in self if isinstance(obj, GeoObject)]
            if len(ndim_list) > 0:
                ndim = max(ndim_list)  # [0]
            else:
                raise RuntimeError(f"Can not get ndim from {ndim_list}")
        self._rank = rank
        self._ndim = ndim
        self._metadata = kwargs
        # GeoObject.__init__(self, rank=rank, ndim=ndim, **kwargs)

    def _repr_svg_(self) -> str:
        """Jupyter 通过调用 _repr_html_ 显示对象"""
        from ..view.sp_view import display

        return display(self, schema="svg")

    # def __svg__(self) -> str:
    #     return f"<g >\n" + "\t\n".join([g.__svg__ for g in self if isinstance(g, GeoObject)]) + "</g>"

    @property
    def bbox(self) -> BBox:
        return np.bitwise_or.reduce([g.bbox for g in self if isinstance(g, GeoObject)])

    def enclose(self, other) -> bool:
        return all([g.enclose(other) for g in self if isinstance(g, GeoObject)])

    # class Box(GeoObject):
    #     def __init__(self, *args, **kwargs) -> None:
    #         super().__init__(*args, **kwargs)

    #     @property
    #     def bbox(self) -> typing.Tuple[ArrayType, ArrayType]: return self._points[0], self._points[1]

    #     def enclose(self, *xargs) -> bool:
    #         if all([isinstance(x, numeric_type) for x in xargs]):  # 点坐标
    #             if len(xargs) != self.ndim:
    #                 raise RuntimeError(f"len(xargs)={len(xargs)}!=self.ndim={self.ndim} {xargs}")
    #             xmin, xmax = self.bbox
    #             return np.bitwise_and.reduce([((xargs[i] >= xmin[i]) & (xargs[i] <= xmax[i])) for i in range(self.ndim)])
    #         elif len(xargs) == 1 and isinstance(xargs[0], GeoObject):
    #             raise NotImplementedError(f"{self.__class__.__name__}.enclose(GeoObject)")
    #         else:
    #             return np.bitwise_and.reduce([self.enclose(x) for x in xargs])


def as_geo_object(*args, **kwargs) -> GeoObject | GeoObjectSet:
    if len(kwargs) > 0 or len(args) != 1:
        return GeoObject(*args, **kwargs)
    elif isinstance(args[0], GeoObject):
        return args[0]
    elif isinstance(args[0], collections.abc.Sequence):
        return GeoObjectSet(*args, **kwargs)
    else:
        return GeoObject(*args)
