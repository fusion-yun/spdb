""" 流体模型 """

from spdm.core.sp_tree import annotation
from spdm.core.domain import Domain
from spdm.core.mesh import Mesh
from spdm.core.field import VectorField

from spdm.model.context import Context


class Electromagnetic(Context):
    """流体场"""

    domain: Domain = annotation(alias="grid")

    grid: Mesh

    B: VectorField

    E: VectorField

    J: VectorField
