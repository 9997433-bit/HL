"""Harmonic force identification from ODS and receptance data (MS-3.2)."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from ..exceptions import SolverError

__all__ = ["identify_harmonic_forces"]


def identify_harmonic_forces(
    ods: npt.ArrayLike,
    receptance: npt.ArrayLike,
    *,
    rcond: float | None = None,
) -> npt.NDArray[np.complex128]:
    """Recover equivalent harmonic forces from an ODS and a receptance matrix.

    At one frequency ``u = H(w) f``.  Given the measured displacement vector
    ``ods`` and the model receptance ``H`` (square, ``n_dof × n_dof``), this
    solves ``f = H⁺ u`` in the least-squares sense (MS-3.2 harmonic load ID).
    """
    displacement = np.asarray(ods, dtype=np.complex128).ravel()
    matrix = np.asarray(receptance, dtype=np.complex128)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise SolverError("receptance must be a square 2-D matrix")
    if displacement.size != matrix.shape[0]:
        raise SolverError(
            f"ODS length {displacement.size} must match receptance size {matrix.shape[0]}"
        )
    forces, residuals, rank, _ = np.linalg.lstsq(matrix, displacement, rcond=rcond)
    if rank < displacement.size:
        raise SolverError("receptance matrix is rank deficient for force identification")
    reconstructed = matrix @ forces
    scale = float(np.max(np.abs(displacement)))
    if scale > 0.0:
        error = float(np.max(np.abs(reconstructed - displacement)) / scale)
        if error > 1e-6:
            raise SolverError(
                f"identified forces do not reproduce the ODS (relative error {error:.3e})"
            )
    return np.asarray(forces, dtype=np.complex128)
