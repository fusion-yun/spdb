import typing
import collections.abc
import numpy as np

from ..core.typing import ArrayLike, ArrayType, as_array

from ..utils.tags import _not_found_

from ..core.mesh import Mesh


class StructuredMesh(Mesh):
    """StructureMesh
    结构化网格上的点可以表示为长度为n=rank的归一化ntuple，记作 uv，uv_r \\in [0,1]
    """

    def __init__(self, *args, cycles=None, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        _, self._dims = Mesh._guess_mesh_type(*args, **kwargs)

        if isinstance(cycles, collections.abc.Sequence):
            for idx, d in enumerate(self._dims):
                if (
                    isinstance(cycles, collections.abc.Sequence)
                    and cycles[idx] is not None
                    and not np.isclose(d[-1] - d[0], cycles[idx])
                ):
                    raise RuntimeError(f"idx={idx} periods {cycles[idx]} is not compatible with dims [{d[0]},{d[-1]}] ")
                if not np.all(d[1:] > d[:-1]):
                    raise RuntimeError(f"dims[{idx}] is not increasing")

        ndim = len(self._dims)

        self._origin = np.asarray([0.0] * ndim)
        self._scale = np.asarray([1.0] * ndim)
        self._cycles = tuple(cycles) if cycles is not None else tuple([1.0] * ndim)

    @property
    def dims(self) -> typing.Tuple[ArrayType]:
        return self._dims

    @property
    def dimensions(self) -> typing.Tuple[ArrayType]:
        return self._dims

    @property
    def ndim(self) -> int:
        return len(self._dims)

    @property
    def origin(self) -> ArrayType:
        """源点"""
        return self._origin

    @property
    def scale(self) -> ArrayType:
        """比例尺"""
        return self._scale

    @property
    def cycles(self) -> typing.Tuple[float]:
        """Periodic boundary condition  周期性网格,  标识每个维度周期长度"""
        return self._cycles

    @property
    def rank(self) -> int:
        return len(self._dims)

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
