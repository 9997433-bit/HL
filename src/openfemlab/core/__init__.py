"""Core finite element data structures: model, elements and assembly."""

from __future__ import annotations

from .assembly import AssembledSystem, assemble_mass, assemble_stiffness, assemble_system
from .elements import (
    PLANE_STATES,
    BarElement,
    BeamElement2D,
    BeamElement3D,
    Element,
    Hex8Element,
    Quad4Element,
    SpringElement,
    Tet4Element,
    TrussElement,
    gauss_legendre_2d,
    gauss_legendre_3d,
    plane_constitutive_matrix,
    solid_constitutive_matrix,
)
from .model import (
    DOF,
    ROTATIONAL_DOFS,
    TRANSLATIONAL_DOFS,
    Material,
    Model,
    Node,
    Section,
)

__all__ = [
    "DOF",
    "TRANSLATIONAL_DOFS",
    "ROTATIONAL_DOFS",
    "Material",
    "Section",
    "Node",
    "Model",
    "Element",
    "SpringElement",
    "TrussElement",
    "BarElement",
    "BeamElement2D",
    "BeamElement3D",
    "Quad4Element",
    "Tet4Element",
    "Hex8Element",
    "PLANE_STATES",
    "gauss_legendre_2d",
    "gauss_legendre_3d",
    "plane_constitutive_matrix",
    "solid_constitutive_matrix",
    "AssembledSystem",
    "assemble_system",
    "assemble_stiffness",
    "assemble_mass",
]
