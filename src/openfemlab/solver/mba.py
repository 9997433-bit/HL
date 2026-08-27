"""Modal-Based Assembly (MBA) and FRF-Based Assembly (FBA).

FEMtools Dynamics couples substructures in the modal domain (MBA) or through
component FRFs at connection impedances (FBA).  Both paths are deterministic
linear algebra over retained modes (MS-7.7, MS-7.8).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from ..exceptions import SolverError
from .dynamics import FrequencyResponse

__all__ = [
    "ModalComponent",
    "mba_couple",
    "fba_couple_receptances",
    "fba_assemble",
]


@dataclass(frozen=True)
class ModalComponent:
    """Modal model of one substructure."""

    frequencies_hz: npt.NDArray[np.float64]
    mode_shapes: npt.NDArray[np.float64]
    damping_ratios: npt.NDArray[np.float64] | None = None
    modal_masses: npt.NDArray[np.float64] | None = None


def _component_masses(component: ModalComponent) -> npt.NDArray[np.float64]:
    if component.modal_masses is not None:
        masses = np.asarray(component.modal_masses, dtype=np.float64).ravel()
        if masses.size != component.mode_shapes.shape[1]:
            raise SolverError("modal_masses length must match the mode count")
        return masses
    return np.ones(component.mode_shapes.shape[1], dtype=np.float64)


def mba_couple(
    left: ModalComponent,
    right: ModalComponent,
    *,
    left_connection_dof: int = 0,
    right_connection_dof: int = 0,
    connection_stiffness: float,
) -> ModalComponent:
    """Couple two modal components through a spring at the interface (MBA).

    The retained bases are concatenated and a connection stiffness ``k`` is
    projected into modal coordinates.  Undamped coupling is assumed; damping
    ratios are returned as zeros when absent from the inputs.
    """
    stiffness = float(connection_stiffness)
    if stiffness < 0.0:
        raise SolverError(f"connection_stiffness must be non-negative, got {stiffness}")
    phi_left = np.asarray(left.mode_shapes, dtype=np.float64)
    phi_right = np.asarray(right.mode_shapes, dtype=np.float64)
    if phi_left.ndim != 2 or phi_right.ndim != 2:
        raise SolverError("mode_shapes must be 2-D arrays")
    n_left, n_left_modes = phi_left.shape
    n_right, n_right_modes = phi_right.shape
    if n_left_modes != left.frequencies_hz.size or n_right_modes != right.frequencies_hz.size:
        raise SolverError("frequencies_hz length must match mode_shapes columns")
    left_index = int(left_connection_dof)
    right_index = int(right_connection_dof)
    if not (0 <= left_index < n_left):
        raise SolverError(f"left_connection_dof {left_index} outside [0, {n_left})")
    if not (0 <= right_index < n_right):
        raise SolverError(f"right_connection_dof {right_index} outside [0, {n_right})")

    total_dofs = n_left + n_right
    total_modes = n_left_modes + n_right_modes
    phi = np.zeros((total_dofs, total_modes), dtype=np.float64)
    phi[:n_left, :n_left_modes] = phi_left
    phi[n_left:, n_left_modes:] = phi_right

    masses_left = _component_masses(left)
    masses_right = _component_masses(right)
    modal_masses = np.concatenate([masses_left, masses_right])
    omega_left = 2.0 * np.pi * np.asarray(left.frequencies_hz, dtype=np.float64)
    omega_right = 2.0 * np.pi * np.asarray(right.frequencies_hz, dtype=np.float64)
    stiffness_modal = np.concatenate(
        [omega_left**2 * masses_left, omega_right**2 * masses_right]
    )

    connection = np.zeros((total_dofs, total_dofs), dtype=np.float64)
    joint_left = left_index
    joint_right = n_left + right_index
    connection[joint_left, joint_left] += stiffness
    connection[joint_right, joint_right] += stiffness
    connection[joint_left, joint_right] -= stiffness
    connection[joint_right, joint_left] -= stiffness

    stiffness_matrix = np.diag(stiffness_modal) + phi.T @ connection @ phi
    mass_matrix = np.diag(modal_masses)
    try:
        from scipy.linalg import eigh

        eigenvalues, vectors = eigh(stiffness_matrix, mass_matrix)
    except np.linalg.LinAlgError as exc:
        raise SolverError("MBA coupled eigenproblem failed") from exc

    eigenvalues = np.maximum(np.asarray(eigenvalues, dtype=np.float64), 0.0)
    frequencies_hz = np.sqrt(eigenvalues) / (2.0 * np.pi)
    shapes = phi @ vectors
    for column in range(shapes.shape[1]):
        norm = np.linalg.norm(shapes[:, column])
        if norm > 0.0:
            shapes[:, column] /= norm

    if left.damping_ratios is not None and right.damping_ratios is not None:
        dampings = np.concatenate(
            [
                np.asarray(left.damping_ratios, dtype=np.float64).ravel(),
                np.asarray(right.damping_ratios, dtype=np.float64).ravel(),
            ]
        )
    else:
        dampings = np.zeros(total_modes, dtype=np.float64)

    return ModalComponent(
        frequencies_hz=frequencies_hz,
        mode_shapes=shapes,
        damping_ratios=dampings,
        modal_masses=np.ones(total_modes, dtype=np.float64),
    )


def fba_couple_receptances(
    left_receptance: npt.NDArray[np.complexfloating],
    right_receptance: npt.NDArray[np.complexfloating],
    stiffness: float,
) -> npt.NDArray[np.complex128]:
    """Couple drive-point receptances through a spring (FBA, MS-7.8).

    Each input is the uncoupled drive-point receptance at one side of the
    connection spring.  The returned line is the coupled drive-point receptance
    on the left side when force is applied there (right side free).
    """
    h_left = np.asarray(left_receptance, dtype=np.complex128).ravel()
    h_right = np.asarray(right_receptance, dtype=np.complex128).ravel()
    if h_left.shape != h_right.shape:
        raise SolverError(
            f"receptance vectors must match, got {h_left.shape} and {h_right.shape}"
        )
    k = float(stiffness)
    if k < 0.0:
        raise SolverError(f"stiffness must be non-negative, got {k}")
    z_left = 1.0 / h_left
    z_right = 1.0 / h_right
    z_coupled = z_left + k - (k * k) / (z_right + k)
    coupled = 1.0 / z_coupled
    return np.where(np.isfinite(coupled), coupled, 0.0)


def fba_assemble(
    left: FrequencyResponse,
    right: FrequencyResponse,
    *,
    left_dof: int,
    right_dof: int,
    stiffness: float,
    response_dof: int | None = None,
    excitation_dof: int | None = None,
) -> FrequencyResponse:
    """Assemble component FRFs into one drive-point receptance line (FBA)."""
    if left.frequencies.shape != right.frequencies.shape:
        raise SolverError("both FRF sets must share the same frequency line")
    if not np.allclose(left.frequencies, right.frequencies):
        raise SolverError("frequency lines must match pointwise for FBA assembly")
    drive_response = int(response_dof if response_dof is not None else left_dof)
    drive_excitation = int(excitation_dof if excitation_dof is not None else left_dof)
    h_left = left.drive_point(left_dof)
    h_right = right.drive_point(right_dof)
    coupled = fba_couple_receptances(h_left, h_right, stiffness)
    data = coupled[:, None, None]
    return FrequencyResponse(
        left.frequencies.copy(),
        data,
        np.array([drive_response], dtype=int),
        np.array([drive_excitation], dtype=int),
        response_type=left.response_type,
    )
