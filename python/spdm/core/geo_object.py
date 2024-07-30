import abc
import collections.abc
from copy import copy
import typing
import inspect
import numpy as np

from spdm.utils.type_hint import ArrayLike, ArrayType, array_type
from spdm.utils.tags import _not_found_
from spdm.utils.logger import logger

from spdm.core.htree import List, HTree
from spdm.core.sp_tree import annotation, sp_property, SpTree
from spdm.core.pluggable import Pluggable


class BBox:
    """Boundary Box"""

    def __init__(self, origin: ArrayLike = None, dimensions: ArrayLike = None, transform=None, shift=None) -> None:
        self._origin = np.asarray(origin)
        self._dimensions = np.asarray(dimensions)
        self._transform = transform
        self._shift = shift

    def __copy__(self) -> typing.Self:
        return BBox(self._origin, self._dimensions, self._transform, self._shift)

    def __repr__(self) -> str:
        """x y width height"""
        return f"viewBox=\"{' '.join([*map(str,self._origin)])}  {' '.join([*map(str,self._dimensions)]) }\" transform=\"{self._transform}\" shift=\"{self._shift}\""

    @property
    def origin(self) -> ArrayType:
        return self._origin

    @property
    def dimensions(self) -> ArrayType:
        return self._dimensions

    @property
    def is_valid(self) -> bool:
        return np.all(self._dimensions > 0)

    @property
    def is_degraded(self) -> bool:
        return np.any(np.isclose(self._dimensions, 0.0))

    @property
    def is_null(self) -> bool:
        return np.allclose(self._dimensions, 0)

    # def __equal__(self, other: BBox) -> bool:
    #     return np.allclose(self._xmin, other._xmin) and np.allclose(self._xmax, other._xmax)

    # def __or__(self, other: BBox) -> BBox:
    #     if other is None:
    #         return self
    #     else:
    #         return BBox(np.min(self._xmin, other._xmin), np.max(self._xmax, other._xmax))

    # def __and__(self, other: BBox) -> BBox | None:
    #     if other is None:
    #         return None
    #     else:
    #         res = BBox(np.max(self._xmin, other._xmin), np.min(self._xmax, other._xmax))
    #         return res if res.is_valid else None

    @property
    def ndim(self) -> int:
        return len(self._dimensions)

    @property
    def center(self) -> ArrayType:
        """center of geometry"""
        return self._origin + self._dimensions * 0.5

    @property
    def measure(self) -> float:
        """measure of geometry, length,area,volume,etc. 默认为 bbox 的体积"""
        return float(np.product(self._dimensions))

    def enclose(self, *args) -> bool | ArrayType:
        """Return True if all args are inside the geometry, False otherwise."""

        if len(args) == 1:

            # if hasattr(args[0], "bbox"):
            #     return self.enclose(args[0].bbox)
            # elif isinstance(args[0], BBox):
            #     return self.enclose(args[0].origin) and self.enclose(args[0].origin+args[0].dimensions)
            if hasattr(args[0], "points"):
                return self.enclose(*args[0].points)
            if isinstance(args[0], collections.abc.Sequence):
                return self.enclose(*args[0])
            elif isinstance(args[0], array_type):
                return self.enclose([args[0][..., idx] for idx in range(self.ndim)])
            else:
                raise TypeError(f"args has wrong type {type(args[0])} {args}")

        elif len(args) == self.ndim:
            if isinstance(args[0], array_type):
                r_pos = [args[idx] - self._origin[idx] for idx in range(self.ndim)]
                return np.bitwise_and.reduce(
                    [((r_pos[idx] >= 0) & (r_pos[idx] <= self._dimensions[idx])) for idx in range(self.ndim)]
                )
            else:
                res = all(
                    [
                        (
                            (args[idx] >= self._origin[idx])
                            and (args[idx] <= self._origin[idx] + self._dimensions[idx])
                        )
                        for idx in range(self.ndim)
                    ]
                )
                if not res:
                    logger.debug((args, self._origin, self._dimensions))
                return res

        else:
            raise TypeError(f"args has wrong type {type(args[0])} {args}")

    def union(self, other: typing.Self) -> typing.Self:
        """Return the union of self with other."""

        raise NotImplementedError(f"intersection")

    def intersection(self, other: typing.Self):
        """Return the intersection of self with other."""
        raise NotImplementedError(f"intersection")

    def reflect(self, point0, pointt1):
        """reflect  by line"""
        raise NotImplementedError(f"reflect")

    def rotate(self, angle, axis=None):
        """rotate  by angle and axis"""
        raise NotImplementedError(f"rotate")

    def scale(self, *s, point=None):
        """scale self by *s, point"""
        raise NotImplementedError(f"scale")

    def translate(self, *shift):
        raise NotImplementedError(f"translate")


class GeoObject(Pluggable, SpTree, plugin_prefix="spdm/geometry/"):
    """Geomertic object
    几何对象，包括点、线、面、体等

    Geometry object base class
    ===============================
    几何对象基类，两个子类
    - GeoEntity: 几何体，包括点、线、面、体等
    - GeoObjectSet: 几何对象集合，包括多个几何体
    """

    _plugin_registry = {}

    ndim = 3
    """几何体所处的空间维度， = 0,1,2,3,...
        The dimension of a geometric object, on the other hand, refers to the minimum number of
        coordinates needed to specify any point within it. In general, the rank and dimension of
        a geometric object are the same. However, there are some cases where they can differ.
        For example, a curve that is embedded in three-dimensional space has rank 1 because
        it extends in only one independent direction, but it has dimension 3 because three
        coordinates are needed to specify any point on the curve.
        """

    rank = 0
    """几何体（流形）维度  rank <=ndims

            0: point
            1: curve
            2: surface
            3: volume
            >=4: not defined
        The rank of a geometric object refers to the number of independent directions
        in which it extends. For example, a point has rank 0, a line has rank 1,
        a plane has rank 2, and a volume has rank 3.
        """

    @classmethod
    def _create_subclass(cls, arg: str | int):
        """
        example:
            Point["RZ"]
        """
        n_cls_name = cls.__name__

        cls_attrs = {}

        if isinstance(arg, int):
            ndim = arg
        else:
            if isinstance(arg, str):
                coordinates = arg.split()
            elif isinstance(arg, (tuple, list)):
                coordinates = arg
            else:
                raise TypeError(f"{type(arg)} is not str or int")

            n_cls_name += ("".join(coordinates)).upper()

            cls_attrs.update(
                {k.lower(): annotation(alias=["points", (..., idx)]) for idx, k in enumerate(coordinates)}
            )

            ndim = len(coordinates)

        if ndim is not None:
            n_cls_name += f"{ndim}D"
            cls_attrs["ndim"] = ndim

        if len(cls_attrs) == 0:
            n_cls = cls
        else:
            n_cls = type(
                n_cls_name,
                (cls,),
                {"__module__": cls.__module__, "__package__": getattr(cls, "__package__", None), **cls_attrs},
            )
        # else:
        #     n_cls = cls
        #     for k, v in cls_attrs.items():
        #         setattr(n_cls, k, v)

        return n_cls

    def __class_getitem__(cls, args):
        if isinstance(args, tuple):
            return cls._create_subclass(*args)
        else:
            return cls._create_subclass(args)

    def __new__(cls, *args, _entry=None, **kwargs) -> typing.Self:
        if cls is not GeoObject:
            return super().__new__(cls, *args, _entry=_entry, **kwargs)

        else:

            plugin_name = kwargs.pop("kind", None)

            if plugin_name is None and len(args) > 0 and isinstance(args[0], dict):
                plugin_name = args[0].get("type", None)

            if plugin_name is None and _entry is not None:
                plugin_name = _entry.get("type", None) or _entry.get("@type", None)

            return super().__new__(cls, *args, _plugin_name=plugin_name, _entry=_entry, **kwargs)

    def __init_subclass__(cls, ndim: int = None, rank: int = None, **kwargs):

        super().__init_subclass__(**kwargs)

        if ndim is not None:
            cls.ndim = ndim
        if rank is not None:
            cls.rank = rank

    def __init__(self, *args, **kwargs) -> None:

        if len(args) == 1 and (isinstance(args[0], dict) or args[0] is _not_found_):
            pass
        else:
            if len(args) == 1:
                points = np.asarray(args[0])
            else:
                points = np.stack(args, axis=-1)
            args = ({"points": points},)

        super().__init__(*args, **kwargs)

        if not isinstance(self.points, np.ndarray) or len(self.points.shape) == 0:
            raise RuntimeError(f"Illegal points! {self.points.shape} ndim={self.__class__.ndim} {self.__class__}")

        if self.points.shape[-1] != self.__class__.ndim:
            self.ndim = self.points.shape[-1]

    def _repr_svg_(self) -> str:
        """Jupyter 通过调用 _repr_html_ 显示对象"""
        from spdm.view.sp_view import display

        return display(self, schema="svg")

    def __view__(self, *args, **kwargs) -> typing.Self:
        """
        TODO:
        - 支持3D可视化 （Jupyter+？）

        """
        return self

    def __str__(self) -> str:
        return f"<{self.__class__.__name__}> {self.points}</{self.__class__.__name__}>"

    def __equal__(self, other: typing.Self) -> bool:
        return (other.__class__ is self.__class__) and np.all(self.points == other.points)

    name: str

    points: ArrayType
    """几何体控制点的坐标 例如 (x0,y0),(x1,y1)， 
        数组形状为 [*shape,ndim], shape 为控制点网格的形状，ndim 空间维度。"""

    styles: HTree = {}

    @property
    def coordinates(self) -> ArrayType:
        return tuple([self.points[..., idx] for idx in range(self.ndim)])

    def __array__(self) -> ArrayType:
        return self.points

    def __getitem__(self, idx) -> ArrayType | float:
        return self.points[idx]

    def __setitem__(self, idx, value: ArrayType | float):
        self.points[idx] = value

    def __delitem__(self, idx):
        del self.points[idx]

    def __iter__(self) -> typing.Generator[ArrayType, None, None]:
        yield from self.points

    @sp_property
    def bbox(self) -> BBox:
        """boundary box of geometry [ [...min], [...max] ]"""
        xmin = np.asarray([np.min(self.points[..., n]) for n in range(self.ndim)])
        xmax = np.asarray([np.max(self.points[..., n]) for n in range(self.ndim)])
        return BBox(xmin, xmax - xmin)

    @property
    def boundary(self) -> typing.Self | None:
        """boundary of geometry which is a geometry of rank-1"""
        if self.is_closed:
            return None
        else:
            raise NotImplementedError(f"{self.__class__.__name__}.boundary")

    @property
    def is_null(self) -> bool:
        return self.bbox.is_null

    @property
    def is_convex(self) -> bool:
        """is convex"""
        return self._metadata.get("convex", True)

    @property
    def is_closed(self) -> bool:
        return self._metadata.get("closed", True)

    @property
    def measure(self) -> float:
        """measure of geometry, length,area,volume,etc. 默认为 bbox 的体积"""
        return self.bbox.measure

    def enclose(self, *args) -> bool | ArrayType:
        """Return True if all args are inside the geometry, False otherwise."""
        return False if not self.is_closed else self.bbox.enclose(*args)

    def intersection(self, other: typing.Self) -> typing.List[typing.Self]:
        """Return the intersection of self with other."""
        return [self.bbox.intersection(other.bbox)]

    def reflect(self, point0, point1) -> typing.Self:
        """reflect  by line"""
        other = copy(self)
        other._metadata["name"] = f"{self.name}_reflect"
        other.bbox.reflect(point0, point1)
        return other

    def rotate(self, angle, axis=None) -> typing.Self:
        """rotate  by angle and axis"""
        other = copy(self)
        other._metadata["name"] = f"{self.name}_rotate"
        other.bbox.rotate(angle, axis=axis)
        return other

    def scale(self, *s, point=None) -> typing.Self:
        """scale self by *s, point"""
        other = copy(self)
        other._metadata["name"] = f"{self.name}_scale"
        other.bbox.scale(*s, point=point)
        return other

    def translate(self, *shift) -> typing.Self:
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


_TGeo = typing.TypeVar("_TGeo", bound=GeoObject)


class GeoObjectSet(List[_TGeo], GeoObject):
    """Geometry object set"""

    OBJ_TYPE = _TGeo

    def __class_getitem__(cls, item):
        n_cls = super().__class_getitem__(item)

        if not inspect.isclass(n_cls):
            return n_cls

        g_cls = n_cls.__args__[0]
        if issubclass(g_cls, GeoObject):
            n_cls.rank = g_cls.rank
            n_cls.ndim = g_cls.ndim

        return n_cls

    def __init__(self, *args, _entry=None, _parent=None, **metadata):
        List.__init__(self, *args, _entry=_entry, _parent=_parent)
        GeoObject.__init__(self, **metadata)

    # def __svg__(self) -> str:
    #     return f"<g >\n" + "\t\n".join([g.__svg__ for g in self if isinstance(g, GeoObject)]) + "</g>"
    def __str__(self) -> str:
        contents = "\n\t".join([str(g) for g in self])
        return f"""<{self.__class__.__name__}> {contents} </{self.__class__.__name__}>"""

    @sp_property
    def bbox(self) -> BBox:
        return np.bitwise_or.reduce([g.bbox for g in self if isinstance(g, GeoObject)])

    def enclose(self, other) -> bool:
        return all([g.enclose(other) for g in self if isinstance(g, GeoObject)])

    @property
    def points(self) -> ArrayType:
        return np.stack([surf.points for surf in self], axis=0)


def as_geo_object(*args, **kwargs) -> GeoObject | GeoObjectSet:
    if len(args) == 1 and (args[0] is None or args[0] is _not_found_):
        return None
    elif len(kwargs) > 0 or len(args) != 1:
        return GeoObject(*args, **kwargs)
    elif isinstance(args[0], GeoObject):
        return args[0]
    elif isinstance(args[0], collections.abc.Sequence):
        return GeoObjectSet(*args, **kwargs)
    else:
        return GeoObject(*args, **kwargs)
