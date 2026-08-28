"""Craig-Bampton component mode synthesis."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.linalg as sla

from openfemlab.correlation.reduction import (
    ReductionBasis,
    _block,
    _is_sparse,
    _master_slave,
    guyan_reduction,
)

__all__ = ["CraigBamptonBasis", "build_craig_bampton", "fixed_interface_modes"]


@dataclass(frozen=True, slots=True)
class CraigBamptonBasis:
    """CMS basis: Guyan constraint modes plus fixed-interface normal modes."""

    interface_dofs: np.ndarray
    guyan: ReductionBasis
    fixed_interface_modes: np.ndarray
    fixed_interface_frequencies_hz: np.ndarray
    num_modes: int

    @property
    def transformation(self) -> np.ndarray:
        """Full ``(n, m + k)`` Craig-Bampton basis ``[Psi | Phi]``."""
        psi = np.asarray(self.guyan.transformation, dtype=float)
        phi = np.asarray(self.fixed_interface_modes, dtype=float)
        if phi.size == 0:
            return psi
        return np.hstack([psi, phi])

    @property
    def n_constraint_modes(self) -> int:
        return int(self.guyan.n_master)

    @property
    def n_fixed_interface_modes(self) -> int:
        return int(self.fixed_interface_modes.shape[1])


def fixed_interface_modes(
    stiffness,
    mass,
    interface_dofs,
    *,
    num_modes: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Normal modes of the interior with all interface DOFs fixed."""
    num_modes = int(num_modes)
    if num_modes <= 0:
        ndof = stiffness.shape[0]
        return np.zeros((ndof, 0), dtype=float), np.zeros(0, dtype=float)
    interface = np.asarray(interface_dofs, dtype=np.intp).reshape(-1)
    ndof = stiffness.shape[0]
    master, slave = _master_slave(ndof, interface)
    if slave.size == 0:
        raise ValueError("fixed-interface modes require at least one interior DOF")
    count = min(num_modes, slave.size)
    k_ss = _block(stiffness, slave, slave)
    m_ss = _block(mass, slave, slave)
    k_dense = k_ss.toarray() if _is_sparse(k_ss) else np.asarray(k_ss, dtype=float)
    m_dense = m_ss.toarray() if _is_sparse(m_ss) else np.asarray(m_ss, dtype=float)
    eigenvalues, vectors = sla.eigh(k_dense, m_dense)
    positive = eigenvalues > 1e-12
    eigenvalues = eigenvalues[positive][:count]
    vectors = vectors[:, positive][:, :count]
    full = np.zeros((ndof, vectors.shape[1]), dtype=float)
    full[slave, :] = vectors
    frequencies_hz = np.sqrt(np.maximum(eigenvalues, 0.0)) / (2.0 * np.pi)
    return full, frequencies_hz


def build_craig_bampton(
    stiffness,
    mass,
    interface_dofs,
    *,
    num_modes: int = 0,
) -> CraigBamptonBasis:
    """Build a Craig-Bampton basis with Guyan constraint and fixed-interface modes."""
    interface = np.asarray(interface_dofs, dtype=np.intp).reshape(-1)
    if interface.size == 0:
        raise ValueError("interface_dofs must be non-empty")
    if num_modes < 0:
        raise ValueError("num_modes must be >= 0")
    guyan = guyan_reduction(stiffness, interface)
    phi, frequencies_hz = fixed_interface_modes(
        stiffness, mass, interface, num_modes=num_modes
    )
    return CraigBamptonBasis(
        interface_dofs=interface,
        guyan=guyan,
        fixed_interface_modes=phi,
        fixed_interface_frequencies_hz=frequencies_hz,
        num_modes=int(num_modes),
    )


def reduced_craig_bampton_matrices(
    basis: CraigBamptonBasis,
    stiffness,
    mass,
) -> tuple[np.ndarray, np.ndarray]:
    """Project ``K`` and ``M`` to the Craig-Bampton generalized coordinates."""
    transform = basis.transformation
    k = np.asarray(stiffness, dtype=float)
    m = np.asarray(mass, dtype=float)
    k_red = transform.T @ k @ transform
    m_red = transform.T @ m @ transform
    return 0.5 * (k_red + k_red.T), 0.5 * (m_red + m_red.T)
