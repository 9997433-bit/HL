"""Core finite element data structures: model, elements and assembly."""

from __future__ import annotations

from .assembly import AssembledSystem, assemble_mass, assemble_stiffness, assemble_system
from .elements import (
    PLANE_STATES,
    BarElement,
    BeamElement2D,
    Element,
    Quad4Element,
    SpringElement,
    TrussElement,
    gauss_legendre_2d,
    plane_constitutive_matrix,
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
    "Quad4Element",
    "PLANE_STATES",
    "gauss_legendre_2d",
    "plane_constitutive_matrix",
    "AssembledSystem",
    "assemble_system",
    "assemble_stiffness",
    "assemble_mass",
]
