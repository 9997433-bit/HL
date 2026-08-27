"""Structural Dynamics Modification (SDM) — modal-domain stiffness/mass changes.

FEMtools Dynamics uses SDM to predict how added springs, masses or tuned
absorbers shift resonance frequencies without rebuilding the full FE model.
This module projects modifications onto a retained modal basis and resolves the
modified eigenproblem in modal coordinates (MS-7.6).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from ..exceptions import SolverError

__all__ = [
    "PointModification",
    "apply_point_modifications",
    "modified_frequencies_hz",
]


@dataclass(frozen=True)
class PointModification:
    """Stiffness and/or mass increment at one global DOF index."""

    dof_index: int
    stiffness_delta: float = 0.0
    mass_delta: float = 0.0


def apply_point_modifications(
    stiffness: npt.NDArray[np.floating],
    mass: npt.NDArray[np.floating],
    modifications: Sequence[PointModification],
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Return ``(K + ΔK, M + ΔM)`` with sparse-safe dense copies."""
    k = np.asarray(stiffness, dtype=np.float64)
    m = np.asarray(mass, dtype=np.float64)
    if k.shape != m.shape or k.ndim != 2:
        raise SolverError(f"K and M must be square and matching, got {k.shape} and {m.shape}")
    size = k.shape[0]
    for item in modifications:
        index = int(item.dof_index)
        if index < 0 or index >= size:
            raise SolverError(f"modification DOF {index} outside [0, {size})")
        if item.stiffness_delta:
            k[index, index] += float(item.stiffness_delta)
        if item.mass_delta:
            m[index, index] += float(item.mass_delta)
    return k, m


def modified_frequencies_hz(
    stiffness: npt.NDArray[np.floating],
    mass: npt.NDArray[np.floating],
    mode_shapes: npt.NDArray[np.floating],
    *,
    modifications: Sequence[PointModification] = (),
    num_modes: int | None = None,
) -> npt.NDArray[np.float64]:
    """Predict modified natural frequencies [Hz] in the retained modal basis.

    Forms ``K_r = Φᵀ K_mod Φ``, ``M_r = Φᵀ M_mod Φ`` and solves the dense
    generalized eigenproblem.  This is the SDM frequency prediction step before
    MBA couples substructures (MS-7.6).
    """
    phi = np.asarray(mode_shapes, dtype=np.float64)
    if phi.ndim != 2:
        raise SolverError(f"mode_shapes must be 2-D, got shape {phi.shape}")
    count = int(num_modes if num_modes is not None else phi.shape[1])
    if count < 1 or count > phi.shape[1]:
        raise SolverError(f"num_modes must be in [1, {phi.shape[1]}], got {count}")
    phi = phi[:, :count]
    k_mod, m_mod = apply_point_modifications(stiffness, mass, modifications)
    k_r = phi.T @ k_mod @ phi
    m_r = phi.T @ m_mod @ phi
    try:
        from scipy.linalg import eigh

        eigenvalues = eigh(k_r, m_r, eigvals_only=True)
    except np.linalg.LinAlgError as exc:
        raise SolverError("the modified modal eigenproblem is singular") from exc
    eigenvalues = np.maximum(eigenvalues, 0.0)
    return np.sqrt(eigenvalues) / (2.0 * np.pi)
