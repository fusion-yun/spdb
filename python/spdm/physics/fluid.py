""" 流体模型 """

from spdm.core.htree import Set
from spdm.core.sp_tree import SpTree, annotation
from spdm.core.domain import WithDomain, Domain
from spdm.core.mesh import Mesh
from spdm.core.field import Field, VectorField, TensorField

from spdm.model.context import Context
from spdm.physics.species import Species


class FluidSpecies(WithDomain, Species, SpTree, domain=".../grid"):
    """流体组份"""

    density: Field
    temperature: Field
    pressure: Field
    velocity: VectorField  # 速度
    stress: TensorField  # 协强张量


class FluidIon(FluidSpecies):
    """离子流体描述"""


class FluidElectrons(FluidSpecies, label="electron"):
    """电子流体描述"""


class Fluid(Context):
    """流体场"""

    domain: Domain = annotation(alias="grid")

    grid: Mesh

    species: Set[FluidSpecies]

    B: VectorField

    E: VectorField

    J: VectorField
