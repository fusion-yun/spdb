import typing
import numpy as np

from spdm.utils.type_hint import ArrayType
from spdm.core.sp_tree import sp_property
from spdm.geometry.point import Point
from spdm.domain.mesh_structured import StructuredMesh


class UniformMesh(StructuredMesh, plugin_name="uniform"):
    """Uniform mesh class 均匀网格类"""

    origin: Point = sp_property(alias="geometry/bbox/origin")

    @property
    def points(self) -> ArrayType:
        return np.linspace()

    @sp_property
    def dx(self) -> typing.Tuple[float]:
        return self.geometry.bbox.dimensions / np.asarray(self.shape, dtype=float)

    @property
    def vertices(self, *args) -> ArrayType:
        if len(args) == 1:
            uvw = np.asarray(uvw, dtype=float)
        else:
            uvw = np.stack(list(args))

        return np.stack([(uvw[i] * self.dx[i] + self.origin[i]) for i in range(self.rank)])
