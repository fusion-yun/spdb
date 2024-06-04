import typing
import numpy as np
from ..core.mesh import Mesh
from .mesh_structured import StructuredMesh
from ..utils.typing import ArrayType


@Mesh.register("uniform")
class UniformMesh(StructuredMesh):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        p_min, p_max = self.geometry.bbox
        self._dx = (np.asarray(p_max, dtype=float)-np.asarray(p_min, dtype=float))/np.asarray(self.shape, dtype=float)
        self._orgin = np.asarray(p_min, dtype=float)

    @property
    def origin(self) -> typing.Tuple[float]: return self._dx

    @property
    def dx(self) -> typing.Tuple[float]: return self._dx

    def vertices(self, *args) -> ArrayType:
        if len(args) == 1:
            uvw = np.asarray(uvw, dtype=float)
        else:
            uvw = np.stack(list(args))

        return np.stack([(uvw[i]*self.dx[i]+self.origin[i]) for i in range(self.rank)])


