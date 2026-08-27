"""Accelerometer mass-loading evaluation for pretest (MS-11.2 extension)."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import numpy.typing as npt

from ..exceptions import PretestError

__all__ = ["accelerometer_frequency_shift", "effective_modal_mass_at_dof"]

_MASS_TOL = 1e-30


def effective_modal_mass_at_dof(
    mode_shapes: npt.NDArray[np.floating],
    dof_index: int,
    modal_masses: Sequence[float] | npt.NDArray[np.floating],
) -> npt.NDArray[np.float64]:
    """Per-mode effective mass contributed at ``dof_index``."""
    shapes = np.asarray(mode_shapes, dtype=float)
    if shapes.ndim != 2:
        raise PretestError(f"mode_shapes must be 2-D, got shape {shapes.shape}")
    index = int(dof_index)
    if index < 0 or index >= shapes.shape[0]:
        raise PretestError(f"dof_index {index} outside [0, {shapes.shape[0]})")
    masses = np.asarray(modal_masses, dtype=float).ravel()
    if masses.size != shapes.shape[1]:
        raise PretestError(
            f"modal_masses length {masses.size} != mode count {shapes.shape[1]}"
        )
    phi = shapes[index, :]
    return (phi**2) / np.maximum(masses, _MASS_TOL)


def accelerometer_frequency_shift(
    frequencies_hz: Sequence[float],
    mode_shapes: npt.NDArray[np.floating],
    dof_index: int,
    modal_masses: Sequence[float] | npt.NDArray[np.floating],
    accelerometer_mass: float,
) -> npt.NDArray[np.float64]:
    """First-order frequency reduction from a point accelerometer mass (MS-11.2).

    Uses the lumped-mass perturbation ``ω_r' ≈ ω_r / sqrt(1 + m_acc / m_eff,r)``
    with ``m_eff,r = m_r / φ_r(d)²`` at the sensor DOF.
    """
    if accelerometer_mass <= 0.0:
        raise PretestError(f"accelerometer_mass must be positive, got {accelerometer_mass}")
    freqs = np.asarray(frequencies_hz, dtype=float).ravel()
    eff = effective_modal_mass_at_dof(mode_shapes, dof_index, modal_masses)
    ratio = 1.0 + accelerometer_mass / np.maximum(eff, _MASS_TOL)
    return freqs / np.sqrt(ratio)
