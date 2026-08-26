"""M3 model-updating acceptance suite (``docs/ACCEPTANCE_CRITERIA.md`` section 4).

Implemented here
----------------
- **AC-UPD-001** (oracle, MS-3.3) — the analytic Fox-Kapoor eigenvalue
  sensitivity ``dlambda_i/dp_j = phi_i^T (dK/dp_j - lambda_i dM/dp_j) phi_i``
  matches central finite differences with ``h = 1e-6 p_j,0`` to relative error
  1e-6 for every mode/parameter pair.
- **AC-UPD-007** (twin, MS-3.6) — a deliberately duplicated parameter is caught
  by the pre-updating collinearity screen at pairwise cosine > 0.99, one of the
  pair is frozen with a reported reason, and updating still recovers the
  survivor to the AC-UPD-003 gates.

The model is the ``ten_dof_chain`` fixture split into three stiffness groups
and two mass groups. The split is affine, so the group matrices *are* the
parameter derivatives, and the test pins the split to the fixture: at
``theta = 1`` the contributions must sum back to the fixture ``K`` and ``M``.
"""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.updating import ScalingModel, UpdatableParameter
from openfemlab.updating.sensitivity import eigenvalue_sensitivity
from openfemlab.workflow import run_correction, select_parameters

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

#: Gates of AC-UPD-007; the recovery half is the AC-UPD-003 gate set.
COLLINEARITY_COSINE = 0.99
RECOVERY_ATOL = 1e-3
RECOVERY_FREQ_PCT = 0.1
RECOVERY_MAC = 0.999

NUM_MASSES = 10
NUM_MODES = 6
STIFFNESS_GROUPS = ((1, 2, 3), (4, 5, 6), (7, 8, 9, 10))
MASS_GROUPS = ((1, 2, 3, 4, 5), (6, 7, 8, 9, 10))

#: AC-UPD-007 twin: ``k1`` is detuned and ``k1_twin`` scales the same springs.
DUPLICATED_TRUTH = {"k1": 1.20, "k2": 0.80, "k3": 1.15, "k1_twin": 1.00}

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


def _duplicated_model() -> ScalingModel:
    """The same chain with a second factor scaling exactly the first spring group.

    ``k1`` and ``k1_twin`` share an element set, so only their sum is
    identifiable — the rank deficiency MS-3.6 exists to catch. The nodal masses
    stay unparameterized so the only degeneracy is the deliberate one.
    """
    stiffness_parts, mass_parts = spring_chain_parts(
        NUM_MASSES, STIFFNESS_GROUPS, MASS_GROUPS
    )
    stiffness_parts["k1_twin"] = stiffness_parts["k1"].copy()
    return ScalingModel(
        stiffness_parts,
        base_mass=sum(mass_parts.values()),
        num_modes=NUM_MODES,
        use_solver=False,
    )


def _duplicated_run():
    """S1-S6 on the duplicated-parameter twin, all four factors declared free."""
    model = _duplicated_model()
    measured = model.modal_data(DUPLICATED_TRUTH)
    parameters = [
        UpdatableParameter(name, 1.0, 0.5, 2.0) for name in model.parameter_names
    ]
    return run_correction(model, measured, None, parameters, seed=0)


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


# --------------------------------------------- AC-UPD-007 collinearity screen


@criterion("AC-UPD-007")
def test_ac_upd_007_the_screen_frees_one_of_an_exactly_collinear_pair():
    """A duplicated column is a cosine-1 detection on the sensitivity matrix alone."""
    sensitivity = np.array(
        [
            [1.0, 0.0, 1.0],
            [0.0, 2.0, 0.0],
            [1.0, 1.0, 1.0],
        ]
    )

    selection = select_parameters(sensitivity, ["a", "b", "a_twin"])

    frozen = [d for d in selection.diagnostics if not d.selected]
    assert len(frozen) == 1
    assert frozen[0].reason == "collinear"
    assert {frozen[0].name, frozen[0].collinear_with} == {"a", "a_twin"}
    assert frozen[0].max_cosine > COLLINEARITY_COSINE
    # Dropping the redundant column is what makes the normal equations solvable:
    # the full matrix is rank-deficient, the retained subset is well conditioned.
    assert selection.condition_number > 1.0 / np.finfo(float).eps
    assert selection.selected_condition_number < 10.0


@criterion("AC-UPD-007")
def test_ac_upd_007_the_duplicated_parameter_is_detected_and_frozen():
    """S3 flags the pair at cosine > 0.99 and reports which twin it froze, and why."""
    report = _duplicated_run()
    selection = report.parameter_selection

    assert selection.frozen == ["k1_twin"]
    assert set(selection.selected) == {"k1", "k2", "k3"}

    diagnostic = next(d for d in selection.diagnostics if d.name == "k1_twin")
    assert diagnostic.reason == "collinear"
    assert diagnostic.collinear_with == "k1"
    assert diagnostic.max_cosine > COLLINEARITY_COSINE

    entry = report.parameter("k1_twin")
    assert not entry.selected
    assert entry.freeze_reason == "collinear"
    assert entry.final == 1.0
    assert "collinear with k1" in selection.table()


@criterion("AC-UPD-007")
def test_ac_upd_007_updating_still_meets_the_recovery_gates():
    """With the twin frozen the run converges and the survivor lands on the truth."""
    report = _duplicated_run()

    assert report.status == "PASS", report.failure
    selected = report.parameter_selection.selected
    recovered = np.array([report.parameter(name).final for name in selected])
    expected = np.array([DUPLICATED_TRUTH[name] for name in selected])
    assert np.max(np.abs(recovered - expected)) <= RECOVERY_ATOL

    summary = report.final_correlation.summary
    assert summary.max_abs_freq_error_pct <= RECOVERY_FREQ_PCT
    assert summary.min_mac >= RECOVERY_MAC
