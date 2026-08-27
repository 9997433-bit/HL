"""Rigid-body property extraction (RBPE) — FEMtools RBPE subset.

Full RBPE from FRFs requires a dedicated identification step; this module
starts with model-based totals and a low-mode CG estimate for lumped models
(MS-10.7).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from ..exceptions import MPEError

__all__ = ["RigidBodyProperties", "from_lumped_masses", "rbpe_from_frf"]


@dataclass(frozen=True)
class RigidBodyProperties:
    """Rigid-body mass properties of a structure."""

    total_mass: float
    center_of_gravity: npt.NDArray[np.float64]
    inertia_tensor: npt.NDArray[np.float64] | None = None


def from_lumped_masses(
    node_coords: npt.NDArray[np.floating],
    nodal_masses: npt.NDArray[np.floating],
) -> RigidBodyProperties:
    """Total mass and center of gravity from nodal lumped masses."""
    coords = np.asarray(node_coords, dtype=np.float64)
    masses = np.asarray(nodal_masses, dtype=np.float64).ravel()
    if coords.ndim != 2 or coords.shape[1] != 3:
        raise MPEError(f"node_coords must be (n, 3), got {coords.shape}")
    if masses.size != coords.shape[0]:
        raise MPEError(f"nodal_masses length {masses.size} != node count {coords.shape[0]}")
    if np.any(masses < 0.0):
        raise MPEError("nodal_masses must be non-negative")
    total = float(masses.sum())
    if total <= 0.0:
        raise MPEError("total mass must be positive")
    cog = (masses[:, None] * coords).sum(axis=0) / total
    # Diagonal inertia about CG for lumped masses (RBPE subset).
    relative = coords - cog
    inertia = np.zeros((3, 3), dtype=np.float64)
    for mass, point in zip(masses, relative, strict=True):
        x, y, z = point
        inertia[0, 0] += mass * (y**2 + z**2)
        inertia[1, 1] += mass * (x**2 + z**2)
        inertia[2, 2] += mass * (x**2 + y**2)
        inertia[0, 1] -= mass * x * y
        inertia[0, 2] -= mass * x * z
        inertia[1, 2] -= mass * y * z
    inertia[1, 0] = inertia[0, 1]
    inertia[2, 0] = inertia[0, 2]
    inertia[2, 1] = inertia[1, 2]
    return RigidBodyProperties(total_mass=total, center_of_gravity=cog, inertia_tensor=inertia)


def rbpe_from_frf(*_args, **_kwargs) -> RigidBodyProperties:
    """Extract rigid-body properties from low-frequency FRF measurements."""
    raise MPEError(
        "RBPE from FRFs is specified for Round 7 Wave 2; "
        "use from_lumped_masses for model-based properties today"
    )
