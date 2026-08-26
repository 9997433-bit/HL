"""M3 model-updating acceptance suite (``docs/ACCEPTANCE_CRITERIA.md`` section 4).

Implemented here
----------------
- **AC-UPD-001** (oracle, MS-3.3) — the analytic Fox-Kapoor eigenvalue
  sensitivity ``dlambda_i/dp_j = phi_i^T (dK/dp_j - lambda_i dM/dp_j) phi_i``
  matches central finite differences with ``h = 1e-6 p_j,0`` to relative error
  1e-6 for every mode/parameter pair.

The model is the ``ten_dof_chain`` fixture split into three stiffness groups
and two mass groups. The split is affine, so the group matrices *are* the
parameter derivatives, and the test pins the split to the fixture: at
``theta = 1`` the contributions must sum back to the fixture ``K`` and ``M``.
"""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.updating import ScalingModel
from openfemlab.updating.sensitivity import eigenvalue_sensitivity

from ._support import (
    criterion,
    dense,
    fixture_matrices,
    load_fixture,
    relative_error,
    spring_chain_parts,
)

#: Gates of AC-UPD-001.
SENSITIVITY_RTOL = 1e-6
FD_RELATIVE_STEP = 1e-6

NUM_MASSES = 10
NUM_MODES = 6
STIFFNESS_GROUPS = ((1, 2, 3), (4, 5, 6), (7, 8, 9, 10))
MASS_GROUPS = ((1, 2, 3, 4, 5), (6, 7, 8, 9, 10))

#: Operating points: the nominal model and a detuned one (MS-3.3 holds anywhere).
OPERATING_POINTS = {
    "nominal": np.ones(len(STIFFNESS_GROUPS) + len(MASS_GROUPS)),
    "detuned": np.array([0.80, 1.25, 0.95, 1.10, 0.90]),
}


def _scaling_model() -> ScalingModel:
    stiffness_parts, mass_parts = spring_chain_parts(
        NUM_MASSES, STIFFNESS_GROUPS, MASS_GROUPS
    )
    return ScalingModel(stiffness_parts, mass_parts, num_modes=NUM_MODES)


def _central_difference_eigenvalues(model: ScalingModel, theta: np.ndarray) -> np.ndarray:
    """``dlambda/dp`` by central differences with the MS-3.3 step ``1e-6 p_j,0``."""
    steps = FD_RELATIVE_STEP * np.abs(theta)
    columns = []
    for index, step in enumerate(steps):
        forward, backward = theta.copy(), theta.copy()
        forward[index] += step
        backward[index] -= step
        plus, _ = model.eigen(forward)
        minus, _ = model.eigen(backward)
        columns.append((plus - minus) / (2.0 * step))
    return np.column_stack(columns)


@criterion("AC-UPD-001")
def test_ac_upd_001_parameterization_reproduces_the_chain_fixture():
    """At ``theta = 1`` the group contributions sum back to the fixture matrices."""
    K, M = fixture_matrices(load_fixture("ten_dof_chain"))
    model = _scaling_model()

    assembled_K, assembled_M = model.assemble(np.ones(len(model.parameter_names)))

    np.testing.assert_allclose(dense(assembled_K), K, rtol=0.0, atol=0.0)
    np.testing.assert_allclose(dense(assembled_M), M, rtol=0.0, atol=0.0)


@criterion("AC-UPD-001")
@pytest.mark.parametrize("point", sorted(OPERATING_POINTS))
def test_ac_upd_001_eigenvalue_sensitivity_matches_central_differences(point):
    """Analytic ``dlambda_i/dp_j`` agrees with central FD to 1e-6 relative."""
    theta = OPERATING_POINTS[point]
    model = _scaling_model()
    eigenvalues, shapes = model.eigen(theta)
    stiffness_derivatives, mass_derivatives = model.derivatives()

    analytic = eigenvalue_sensitivity(
        shapes, eigenvalues, stiffness_derivatives, mass_derivatives
    )
    finite = _central_difference_eigenvalues(model, theta)

    assert analytic.shape == (NUM_MODES, len(model.parameter_names))
    # A relative gate is only meaningful while no entry sits in the FD noise.
    assert np.min(np.abs(finite)) > 1e-4 * np.max(np.abs(finite))

    error = relative_error(analytic, finite)
    worst = np.unravel_index(int(np.argmax(error)), error.shape)
    assert np.max(error) <= SENSITIVITY_RTOL, (
        f"{point}: worst relative error {np.max(error):.3e} at mode {worst[0] + 1}, "
        f"parameter {model.parameter_names[worst[1]]}"
    )


@criterion("AC-UPD-001")
def test_ac_upd_001_sensitivity_signs_follow_the_physics():
    """Stiffening raises every eigenvalue, added mass lowers it."""
    model = _scaling_model()
    theta = OPERATING_POINTS["nominal"]
    eigenvalues, shapes = model.eigen(theta)
    stiffness_derivatives, mass_derivatives = model.derivatives()

    sensitivity = eigenvalue_sensitivity(
        shapes, eigenvalues, stiffness_derivatives, mass_derivatives
    )

    stiffness_columns = len(STIFFNESS_GROUPS)
    assert np.all(sensitivity[:, :stiffness_columns] > 0.0)
    assert np.all(sensitivity[:, stiffness_columns:] < 0.0)
