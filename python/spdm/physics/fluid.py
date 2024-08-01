""" 流体模型 """

from spdm.core.htree import Set
from spdm.core.sp_tree import SpTree, annotation
from spdm.core.domain import WithDomain, Domain
from spdm.core.mesh import Mesh
from spdm.core.field import Field, VectorField, TensorField

from spdm.model.context import Context
from spdm.physics.species import Species


class FluidSpecies(WithDomain, Species, domain=".../grid"):
    """流体组份"""

    density: Field
    velocity: VectorField  # 速度
    temperature: Field
    pressure: Field
    diffusion: TensorField  # 扩散系数场


class FluidIon(FluidSpecies, SpTree):
    """离子流体描述"""


class FluidElectrons(Species, SpTree, label="electron"):
    """电子流体描述"""


class Fluid(Context):
    """流体场"""

    domain: Domain = annotation(alias="grid")

    grid: Mesh

    species: Set[FluidSpecies]

    B: VectorField

    E: VectorField
