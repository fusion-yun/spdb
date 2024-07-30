import typing

from spdm.core.geo_object import GeoObject
from spdm.geometry.point import Point


class PointSet(GeoObject):
    """PointSet 点集
    ================
    A set of points in n-dimensional space.
    """

    Point = Point

    def __class_getitem__(cls, args):
        n_cls = super().__class_getitem__(args)
        n_cls.Point = Point[args]
        return n_cls

    # def __init__(self, *args, **kwargs) -> None:
    #     super().__init__(*args, **kwargs)
    #     self.set_coordinates()
    # def set_coordinates(self, *args):
    #     if len(args) == 0:
    #         args = self._metadata.get("coordinates", [])
    #         if isinstance(args, str):
    #             args = args.split(" ")

    #     if len(args) == 0:
    #         return
    #     if len(args) == 1 and isinstance(args[0], str):
    #         args = [x.strip() for x in args[0].split(",")]

    #     self._metadata["coordinates"] = args

    #     if isinstance(args, collections.abc.Sequence):
    #         if len(args) != self.ndim:
    #             raise ValueError(f"coordinates {args} not match ndim {self.ndim}")

    #     for idx, coord_name in enumerate(args):
    #         setattr(self, coord_name, self._points[..., idx])

    # def __copy__(self) -> typing.Self:
    #     other = super().__copy__()  # type:ignore
    #     return other

    def __iter__(self) -> typing.Generator[Point, None, None]:
        tp = self.__class__.Point
        for p in self.points.reshape(-1, self.ndim):
            yield tp(p)

    @property
    def boundary(self) -> typing.Self | None:
        if self.is_closed:
            return None
        elif self.ndim == 2:
            return self.__class__((self.points[0], self.points[-1]))
        else:
            raise NotImplementedError(f"{self.__class__.__name__}.boundary")

    @property
    def vertices(self) -> typing.Generator[Point, None, None]:
        if self.ndim != 2:
            raise NotImplementedError(f"{self.__class__.__name__}.vertices for ndim!=2")

        for p in self.points.reshape(-1, self.ndim):
            yield Point(*p)


PointSetRZ = PointSet["RZ"]
PointSetXY = PointSet["XY"]
