"""Neutral (solver-independent) model exchange contract.

This is the *interchange* representation described in ``docs/ARCHITECTURE.md``
§L1: a flat, array-first description of a structure that can be produced by an
importer (Nastran/UNV/meshio) just as easily as by the internal solver. It
deliberately knows nothing about element formulations.

The internal solver works on :class:`openfemlab.core.model.Model` instead,
which owns nodes, bound elements, constraints, and DOF numbering. The two are
distinguished by the ``Neutral`` prefix here; conversion between them lands
with the io layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np
import numpy.typing as npt

from openfemlab.core.dofs import DofMap

__all__ = ["ElementType", "NeutralMaterial", "NeutralProperty", "NeutralModel"]


class ElementType(Enum):
    """Connectivity block kinds understood by the internal solver."""

    ROD2 = "rod2"          # 2-node axial rod
    BEAM2 = "beam2"        # 2-node Euler-Bernoulli / Timoshenko beam
    TRI3 = "tri3"          # 3-node shell/membrane
    QUAD4 = "quad4"        # 4-node shell/membrane
    TET4 = "tet4"          # 4-node solid
    HEX8 = "hex8"          # 8-node solid
    MASS1 = "mass1"        # 1-node lumped mass
    SPRING2 = "spring2"    # 2-node spring/bushing


@dataclass(frozen=True, slots=True)
class NeutralMaterial:
    """Linear elastic isotropic material (anisotropy: Round 3)."""

    id: int
    E: float                 # Young's modulus [Pa]
    nu: float                # Poisson's ratio [-]
    rho: float               # density [kg/m^3]
    name: str = ""


@dataclass(frozen=True, slots=True)
class NeutralProperty:
    """Element property set (section/thickness), referencing a material."""

    id: int
    material_id: int
    values: dict[str, float] = field(default_factory=dict)  # e.g. A, Iy, Iz, J, t
    name: str = ""


@dataclass(slots=True)
class NeutralModel:
    """Solver-independent FE model.

    Attributes
    ----------
    nodes:
        Coordinates, shape ``(n_nodes, 3)`` float64.
    node_ids:
        External labels, shape ``(n_nodes,)`` int64; stable across io round-trips.
    elements:
        Connectivity blocks per element type; each array has shape
        ``(n_elem, nodes_per_elem)`` and stores **node ids** (not row indices).
    element_property_ids:
        Property id per element, aligned with ``elements`` blocks.
    materials / properties:
        Lookup tables by id.
    dof_map:
        Global DOF ordering; ``None`` until assigned by the solver or an importer.
    meta:
        Free-form provenance (units, source file, solver name).
    """

    nodes: npt.NDArray[np.float64]
    node_ids: npt.NDArray[np.int64]
    elements: dict[ElementType, npt.NDArray[np.int64]] = field(default_factory=dict)
    element_property_ids: dict[ElementType, npt.NDArray[np.int64]] = field(default_factory=dict)
    materials: dict[int, NeutralMaterial] = field(default_factory=dict)
    properties: dict[int, NeutralProperty] = field(default_factory=dict)
    dof_map: DofMap | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.nodes = np.asarray(self.nodes, dtype=np.float64)
        self.node_ids = np.asarray(self.node_ids, dtype=np.int64)
        if self.nodes.ndim != 2 or self.nodes.shape[1] != 3:
            raise ValueError("nodes must have shape (n_nodes, 3)")
        if self.node_ids.shape != (self.nodes.shape[0],):
            raise ValueError("node_ids must have shape (n_nodes,)")

    @property
    def n_nodes(self) -> int:
        return self.nodes.shape[0]

    @property
    def n_elements(self) -> int:
        return sum(int(conn.shape[0]) for conn in self.elements.values())

    def __repr__(self) -> str:
        return (
            f"NeutralModel(n_nodes={self.n_nodes}, n_elements={self.n_elements}, "
            f"blocks={[t.value for t in self.elements]})"
        )
