import typing

from spdm.core.geo_object import GeoObject
from spdm.geometry.line import Segment
from spdm.geometry.polygon import Polygon


class Polyhedron(GeoObject, plugin_name="polyhedron"):

    @property
    def is_convex(self) -> bool:
        return True

    @property
    def edges(self) -> typing.Generator[Segment, None, None]:
        raise NotImplementedError()

    @property
    def faces(self) -> typing.Generator[Polygon, None, None]:
        raise NotImplementedError()

    @property
    def boundary(self) -> typing.Generator[Polygon, None, None]:
        yield from self.faces
