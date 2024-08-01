""" 结构化网格 """

import typing
import numpy as np

from spdm.utils.tags import _not_found_
from spdm.utils.type_hint import ArrayType
from spdm.core.mesh import Mesh


class StructuredMesh(Mesh, plugin_name="structured"):
    """StructureMesh
    结构化网格, 由坐标轴上的点组成的网格
    """

    periods: typing.Tuple[bool, ...]
    """Periodic boundary condition  周期性网格,  标识每个维度周期长度"""

    @property
    def points(self) -> ArrayType:
        return np.stack(self.coordinates, axis=-1)

    @property
    def coordinates(self) -> typing.Tuple[ArrayType, ...]:
        origin = self.bbox.origin
        dimensions = self.bbox.dimensions
        dims = [
            np.linspace(
                origin[i],
                origin[i] + dimensions[i],
                self.shape[i],
                endpoint=self.periods[i] if self.periods is not _not_found_ else True,
            )
            for i in range(self.ndim)
        ]
        return tuple(np.meshgrid(*dims, indexing="ij"))

    def interpolator(self, *args, **kwargs) -> typing.Callable:
        """Interpolator of the Mesh
        网格的插值器, 用于网格上的插值
        返回一个函数，该函数的输入是一个坐标，输出是一个值
        输入坐标若为标量，则返回标量值
        输入坐标若为数组，则返回数组
        """
        raise NotImplementedError(f"{args} {kwargs}")
