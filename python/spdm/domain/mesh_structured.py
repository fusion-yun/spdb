import typing
import numpy as np

from spdm.utils.type_hint import ArrayType
from spdm.core.mesh import Mesh
from spdm.geometry.vector import Vector


class StructuredMesh(Mesh, plugin_name="structured"):
    """StructureMesh
    结构化网格上的点可以表示为长度为n=rank的归一化ntuple，记作 uv，uv_r \\in [0,1]
    """

    periods: Vector[bool]
    """Periodic boundary condition  周期性网格,  标识每个维度周期长度"""

    def coordinates(self, *uvw) -> ArrayType:
        if len(uvw) == 1:
            uvw = uvw[0]
        return np.stack([((uvw[i]) * self.scale[i] + self.origin[i]) for i in range(self.rank)])

    def parametric_coordinates(self, *xyz) -> ArrayType:
        if len(uvw) == 1:
            uvw = uvw[0]
        return np.stack([((xyz[i] - self.origin[i]) / self.scale[i]) for i in range(self.rank)])

    def interpolator(self, *args, **kwargs) -> typing.Callable:
        """Interpolator of the Mesh
        网格的插值器, 用于网格上的插值
        返回一个函数，该函数的输入是一个坐标，输出是一个值
        输入坐标若为标量，则返回标量值
        输入坐标若为数组，则返回数组
        """
        raise NotImplementedError(f"{args} {kwargs}")
