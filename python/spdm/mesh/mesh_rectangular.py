from .mesh import Mesh
from ..core.typing import ArrayType
from .mesh_rectilinear import RectilinearMesh


@Mesh.register(["rectangular", "rect"])
class RectangularMesh(RectilinearMesh):
    """ Rectangular Mesh, which is alias of RectilinearMesh
    矩形网格
    """

    @property
    def dim1(self) -> ArrayType: return self._dims[0]

    @property
    def dim2(self) -> ArrayType: return self._dims[1]


