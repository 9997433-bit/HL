"""Boundary contracts for modal solving and FE/test DOF alignment."""

from __future__ import annotations

import numpy as np
import pytest
from numpy.linalg import LinAlgError
from scipy.linalg import eigh


def _align_test_dofs(
    analytical_dofs: list[str],
    analytical_modes: np.ndarray,
    test_dofs: list[str],
    test_modes: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Reduce analytical modes to ordered test DOFs, rejecting unknown sensors."""
    if len(set(analytical_dofs)) != len(analytical_dofs):
        raise ValueError("analytical DOF labels must be unique")
    if len(set(test_dofs)) != len(test_dofs):
        raise ValueError("test DOF labels must be unique")
    if analytical_modes.shape[1] != len(analytical_dofs):
        raise ValueError("analytical mode width does not match its DOF labels")
    if test_modes.shape[1] != len(test_dofs):
        raise ValueError("test mode width does not match its DOF labels")

    analytical_index = {label: index for index, label in enumerate(analytical_dofs)}
    unknown = [label for label in test_dofs if label not in analytical_index]
    if unknown:
        raise KeyError(f"test DOFs absent from analytical model: {unknown}")
    selected = [analytical_index[label] for label in test_dofs]
    return analytical_modes[:, selected], test_modes


def _mac(vector_a: np.ndarray, vector_b: np.ndarray) -> float:
    numerator = abs(np.vdot(vector_a, vector_b)) ** 2
    denominator = np.vdot(vector_a, vector_a).real * np.vdot(
        vector_b, vector_b
    ).real
    if denominator == 0.0:
        raise ValueError("MAC is undefined for a zero mode shape")
    return float(numerator / denominator)


def test_zero_mass_is_rejected_by_generalized_symmetric_solver() -> None:
    stiffness = np.diag([2.0, 3.0])
    singular_mass = np.diag([1.0, 0.0])

    assert np.min(np.linalg.eigvalsh(singular_mass)) == 0.0
    with pytest.raises(LinAlgError):
        eigh(stiffness, singular_mass, check_finite=True)


def test_rigid_mode_is_retained_as_zero_frequency() -> None:
    stiffness = np.array([[1.0, -1.0], [-1.0, 1.0]])
    mass = np.eye(2)

    eigenvalues, mode_shapes = eigh(stiffness, mass)
    frequencies_hz = np.sqrt(np.clip(eigenvalues, 0.0, None)) / (2.0 * np.pi)

    np.testing.assert_allclose(eigenvalues, [0.0, 2.0], atol=1.0e-14)
    assert frequencies_hz[0] == pytest.approx(0.0, abs=1.0e-14)
    assert mode_shapes[0, 0] == pytest.approx(mode_shapes[1, 0], abs=1.0e-14)
    np.testing.assert_allclose(
        stiffness @ mode_shapes[:, 0],
        np.zeros(2),
        atol=1.0e-14,
    )


def test_repeated_roots_validate_eigenspace_not_vector_orientation() -> None:
    stiffness = 4.0 * np.eye(3)
    mass = 2.0 * np.eye(3)

    eigenvalues, mode_shapes = eigh(stiffness, mass)

    np.testing.assert_allclose(eigenvalues, np.full(3, 2.0), atol=1.0e-14)
    np.testing.assert_allclose(
        mode_shapes.T @ mass @ mode_shapes,
        np.eye(3),
        atol=1.0e-14,
    )
    # The basis inside a repeated-root subspace is arbitrary; its projector is not.
    projector = mode_shapes @ mode_shapes.T @ mass
    np.testing.assert_allclose(projector, np.eye(3), atol=1.0e-14)


def test_missing_analytical_dofs_are_reduced_to_shared_test_coordinates() -> None:
    analytical_dofs = ["node_1:x", "node_2:x", "node_3:x", "node_4:x"]
    test_dofs = ["node_1:x", "node_3:x", "node_4:x"]
    analytical_modes = np.array(
        [
            [0.5, 0.5, 0.5, 0.5],
            [0.6532814824381883, 0.2705980500730985, -0.2705980500730985, -0.6532814824381883],
        ]
    )
    test_modes = np.array(
        [
            [1.0, 1.0, 1.0],
            [-0.8166018530477354, 0.3382475625913731, 0.8166018530477354],
        ]
    )

    aligned_analytical, aligned_test = _align_test_dofs(
        analytical_dofs, analytical_modes, test_dofs, test_modes
    )

    assert aligned_analytical.shape == aligned_test.shape == (2, 3)
    assert _mac(aligned_analytical[0], aligned_test[0]) == pytest.approx(1.0)
    assert _mac(aligned_analytical[1], aligned_test[1]) == pytest.approx(1.0)


def test_test_dof_missing_from_model_is_reported() -> None:
    analytical_dofs = ["node_1:x", "node_2:x"]
    analytical_modes = np.array([[1.0, 0.0]])
    test_dofs = ["node_1:x", "sensor_99:x"]
    test_modes = np.array([[1.0, 0.25]])

    with pytest.raises(KeyError, match="sensor_99:x"):
        _align_test_dofs(
            analytical_dofs, analytical_modes, test_dofs, test_modes
        )
