"""M3 model-updating acceptance suite (``docs/ACCEPTANCE_CRITERIA.md`` section 4).

Implemented here
----------------
- **AC-UPD-001** (oracle, MS-3.3) — the analytic Fox-Kapoor eigenvalue
  sensitivity ``dlambda_i/dp_j = phi_i^T (dK/dp_j - lambda_i dM/dp_j) phi_i``
  matches central finite differences with ``h = 1e-6 p_j,0`` to relative error
  1e-6 for every mode/parameter pair.
- **AC-UPD-002** (oracle, MS-3.3) — the Fox-Kapoor *eigenvector* derivatives
  match central finite differences over the complete modal basis, and their
  truncation error falls monotonically as the basis grows.
- **AC-UPD-003** (twin, MS-3.4) — a model detuned by +/-20 % is recovered from
  noise-free measurements to 1e-3 in at most ten iterations, and the corrected
  model passes the MS-4.2 correlation gates.

The model is the ``ten_dof_chain`` fixture split into three stiffness groups
and two mass groups. The split is affine, so the group matrices *are* the
parameter derivatives, and the test pins the split to the fixture: at
``theta = 1`` the contributions must sum back to the fixture ``K`` and ``M``.
"""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.correlation import modal_scale_factor
from openfemlab.updating import ModelUpdater, ParameterSet, ScalingModel, UpdatableParameter
from openfemlab.updating.sensitivity import eigenvalue_sensitivity, mode_shape_sensitivity

from ._support import (
    criterion,
    dense,
    fixture_matrices,
    load_fixture,
    relative_error,
    spring_chain_parts,
)

#: Gates of AC-UPD-001..003.
SENSITIVITY_RTOL = 1e-6
SHAPE_SENSITIVITY_RTOL = 1e-5
FD_RELATIVE_STEP = 1e-6
RECOVERY_TOLERANCE = 1e-3
MAX_UPDATING_ITERATIONS = 10
FREQUENCY_GATE_PERCENT = 0.1
MAC_GATE = 0.999

NUM_MASSES = 10
NUM_MODES = 6
STIFFNESS_GROUPS = ((1, 2, 3), (4, 5, 6), (7, 8, 9, 10))
MASS_GROUPS = ((1, 2, 3, 4, 5), (6, 7, 8, 9, 10))
PARAMETER_NAMES = ("k1", "k2", "k3", "m1", "m2")

#: Operating points: the nominal model and a detuned one (MS-3.3 holds anywhere).
OPERATING_POINTS = {
    "nominal": np.ones(len(STIFFNESS_GROUPS) + len(MASS_GROUPS)),
    "detuned": np.array([0.80, 1.25, 0.95, 1.10, 0.90]),
}


def _scaling_model(num_modes: int = NUM_MODES) -> ScalingModel:
    stiffness_parts, mass_parts = spring_chain_parts(
        NUM_MASSES, STIFFNESS_GROUPS, MASS_GROUPS
    )
    return ScalingModel(stiffness_parts, mass_parts, num_modes=num_modes)


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


# ----------------------------------------------------- AC-UPD-002 (shapes)


def _aligned_shapes(reference: np.ndarray, shapes: np.ndarray) -> np.ndarray:
    """``shapes`` with each column's sign taken from its MSF against ``reference``.

    Only the *sign* of the modal scale factor may be transferred. Both mode
    sets are already mass normalised, each with respect to its own ``M(theta)``,
    and it is exactly the drift of that normalisation which produces the
    ``-1/2 phi^T dM/dp phi`` term of the Fox-Kapoor derivative. Rescaling by the
    full MSF would divide that term back out; see
    ``test_ac_upd_002_full_msf_rescaling_erases_the_normalization_term``.
    """
    signs = np.array(
        [
            np.sign(np.real(modal_scale_factor(reference[:, column], shapes[:, column])))
            for column in range(shapes.shape[1])
        ]
    )
    signs[signs == 0.0] = 1.0
    return shapes * signs[None, :]


def _central_difference_shapes(
    model: ScalingModel, theta: np.ndarray, *, rescale: bool = False
) -> np.ndarray:
    """``dPhi/dp`` by central differences, shaped like :func:`mode_shape_sensitivity`."""
    _, reference = model.eigen(theta)
    steps = FD_RELATIVE_STEP * np.abs(theta)
    derivatives = np.zeros((theta.size, *reference.shape))
    for index, step in enumerate(steps):
        forward, backward = theta.copy(), theta.copy()
        forward[index] += step
        backward[index] -= step
        _, plus = model.eigen(forward)
        _, minus = model.eigen(backward)
        if rescale:
            factors = [
                np.real(modal_scale_factor(reference[:, c], plus[:, c]))
                for c in range(plus.shape[1])
            ]
            plus = plus * np.array(factors)[None, :]
            factors = [
                np.real(modal_scale_factor(reference[:, c], minus[:, c]))
                for c in range(minus.shape[1])
            ]
            minus = minus * np.array(factors)[None, :]
        else:
            plus = _aligned_shapes(reference, plus)
            minus = _aligned_shapes(reference, minus)
        derivatives[index] = (plus - minus) / (2.0 * step)
    return derivatives


def _shape_sensitivity_error(analytic: np.ndarray, finite: np.ndarray) -> np.ndarray:
    """Componentwise error per (parameter, mode), scaled by that vector's peak.

    A componentwise *relative* error is meaningless where a derivative
    component passes through zero, so each ``dphi_i/dp_j`` vector is normalised
    by its own infinity norm — the strictest scaling that stays well posed.
    """
    peaks = np.max(np.abs(analytic), axis=1)
    return np.max(np.abs(analytic - finite), axis=1) / peaks


@criterion("AC-UPD-002")
@pytest.mark.parametrize("point", sorted(OPERATING_POINTS))
def test_ac_upd_002_shape_sensitivity_matches_central_differences(point):
    """Fox-Kapoor ``dphi_i/dp_j`` over the full basis agrees with central FD."""
    theta = OPERATING_POINTS[point]
    model = _scaling_model(num_modes=NUM_MASSES)
    eigenvalues, shapes = model.eigen(theta)
    stiffness_derivatives, mass_derivatives = model.derivatives()

    analytic = mode_shape_sensitivity(
        shapes, eigenvalues, stiffness_derivatives, mass_derivatives
    )
    finite = _central_difference_shapes(model, theta)

    assert analytic.shape == (len(model.parameter_names), NUM_MASSES, NUM_MASSES)
    # The superposition divides by eigenvalue gaps, so the gate only means
    # something while the spectrum stays separated.
    assert np.min(np.diff(eigenvalues)) > 1e-2 * eigenvalues[-1]

    error = _shape_sensitivity_error(analytic, finite)
    worst = np.unravel_index(int(np.argmax(error)), error.shape)
    assert np.max(error) <= SHAPE_SENSITIVITY_RTOL, (
        f"{point}: worst error {np.max(error):.3e} for "
        f"d(phi_{worst[1] + 1})/d({model.parameter_names[worst[0]]})"
    )


@criterion("AC-UPD-002")
def test_ac_upd_002_derivatives_respect_the_mass_normalization_constraint():
    """``2 phi^T M dphi/dp = -phi^T dM/dp phi`` — the constraint fixing the self term."""
    theta = OPERATING_POINTS["detuned"]
    model = _scaling_model(num_modes=NUM_MASSES)
    eigenvalues, shapes = model.eigen(theta)
    stiffness_derivatives, mass_derivatives = model.derivatives()
    _, mass = model.assemble(theta)

    analytic = mode_shape_sensitivity(
        shapes, eigenvalues, stiffness_derivatives, mass_derivatives
    )

    for index, name in enumerate(model.parameter_names):
        projected = 2.0 * np.einsum("dm,dm->m", shapes, dense(mass) @ analytic[index])
        derivative = mass_derivatives[index]
        expected = (
            np.zeros(NUM_MASSES)
            if derivative is None
            else -np.einsum("dm,dm->m", shapes, dense(derivative) @ shapes)
        )
        np.testing.assert_allclose(projected, expected, rtol=0.0, atol=1e-12, err_msg=name)


@criterion("AC-UPD-002")
def test_ac_upd_002_full_msf_rescaling_erases_the_normalization_term():
    """Differencing MSF-*rescaled* shapes drops the mass self term, and only that.

    Rescaling by the full modal scale factor re-normalises every perturbed mode
    onto the baseline, which is precisely the component the mass-normalisation
    constraint pins down. Stiffness parameters survive it (their self term is
    zero); mass parameters do not, and this pins the choice made in
    :func:`_aligned_shapes`.
    """
    theta = OPERATING_POINTS["nominal"]
    model = _scaling_model(num_modes=NUM_MASSES)
    eigenvalues, shapes = model.eigen(theta)
    stiffness_derivatives, mass_derivatives = model.derivatives()

    analytic = mode_shape_sensitivity(
        shapes, eigenvalues, stiffness_derivatives, mass_derivatives
    )
    rescaled = _central_difference_shapes(model, theta, rescale=True)
    error = _shape_sensitivity_error(analytic, rescaled)

    mass_only = [
        index
        for index in range(len(model.parameter_names))
        if stiffness_derivatives[index] is None
    ]
    stiffness_only = [
        index for index in range(len(model.parameter_names)) if index not in mass_only
    ]
    assert mass_only, "the fixture must expose mass-only parameters"

    assert np.max(error[stiffness_only]) <= SHAPE_SENSITIVITY_RTOL
    assert np.min(error[mass_only]) > 1e-2

    # What the rescaling removed is exactly the self term along phi_i itself.
    recovered = rescaled.copy()
    for index in range(len(model.parameter_names)):
        derivative = mass_derivatives[index]
        if derivative is None:
            continue
        self_term = -0.5 * np.einsum("dm,dm->m", shapes, dense(derivative) @ shapes)
        recovered[index] += shapes * self_term[None, :]
    assert np.max(_shape_sensitivity_error(analytic, recovered)) <= SHAPE_SENSITIVITY_RTOL


@criterion("AC-UPD-002")
@pytest.mark.parametrize("point", sorted(OPERATING_POINTS))
def test_ac_upd_002_truncation_error_falls_monotonically_with_the_basis(point):
    """Every extra basis mode strictly shrinks the truncation error, to zero at full rank.

    The superposition ``dphi_1/dp = sum_{r != 1} c_r phi_r`` drops one term per
    missing basis mode, so the Euclidean norm of the truncation error is the
    tail of a sum of squares and must fall with every mode added. Reported for
    the fundamental mode, which is the one a truncated basis hurts most.
    """
    theta = OPERATING_POINTS[point]
    model = _scaling_model(num_modes=NUM_MASSES)
    eigenvalues, shapes = model.eigen(theta)
    stiffness_derivatives, mass_derivatives = model.derivatives()

    exact = mode_shape_sensitivity(
        shapes, eigenvalues, stiffness_derivatives, mass_derivatives, modes=[0]
    )
    reference_norm = np.linalg.norm(exact)

    errors = []
    for size in range(2, NUM_MASSES + 1):
        truncated = mode_shape_sensitivity(
            shapes[:, :size],
            eigenvalues[:size],
            stiffness_derivatives,
            mass_derivatives,
            modes=[0],
        )
        errors.append(float(np.linalg.norm(truncated - exact) / reference_norm))

    assert all(
        later < earlier for earlier, later in zip(errors, errors[1:], strict=False)
    ), f"{point}: truncation errors are not strictly decreasing: {errors}"
    # A two-mode basis is badly wrong and the complete basis is exact.
    assert errors[0] > 0.1
    assert errors[-1] <= 1e-12


# ------------------------------------------------------- AC-UPD-003 (twins)

#: Twin experiments: which factors are free, and their true (detuned) values.
TWINS = {
    "stiffness": (("k1", "k2", "k3"), {"k1": 0.80, "k2": 1.20, "k3": 0.80}),
    "stiffness_and_mass": (("k1", "k2", "m1"), {"k1": 0.80, "k2": 1.20, "m1": 1.20}),
    "two_factors": (("k1", "m2"), {"k1": 1.20, "m2": 0.80}),
}


def _twin_target(model: ScalingModel, truth: dict[str, float]):
    """Noise-free "measurements": the modal data of the detuned twin."""
    values = {name: truth.get(name, 1.0) for name in model.parameter_names}
    return model.modal_data(values)


def _twin_parameters(free: tuple[str, ...]) -> ParameterSet:
    """All factors start at the nominal 1.0; everything outside ``free`` is fixed."""
    return ParameterSet(
        [
            UpdatableParameter(
                name,
                value=1.0,
                lower=0.5,
                upper=2.0,
                kind="stiffness" if name.startswith("k") else "mass",
                fixed=name not in free,
            )
            for name in PARAMETER_NAMES
        ]
    )


def _run_twin(case: str, *, shape_weight: float = 0.0) -> tuple:
    free, truth = TWINS[case]
    model = _scaling_model()
    target = _twin_target(model, truth)
    extra = (
        {"sensitivity_function": model.sensitivity_function(list(free))}
        if shape_weight == 0.0
        else {}
    )
    updater = ModelUpdater(
        model,
        _twin_parameters(free),
        target.frequencies,
        target.mode_shapes,
        max_iterations=MAX_UPDATING_ITERATIONS,
        shape_weight=shape_weight,
        **extra,
    )
    result = updater.run()
    recovered = np.array([result.parameters[name] for name in free])
    expected = np.array([truth[name] for name in free])
    return result, float(np.max(np.abs(recovered - expected)))


@criterion("AC-UPD-003")
@pytest.mark.parametrize("case", sorted(TWINS))
def test_ac_upd_003_the_detuned_twin_is_not_already_correlated(case):
    """Guard: at ``theta = 1`` the twin violates both MS-4.2 gates it must end up passing."""
    result, _ = _run_twin(case)
    initial = result.initial_correlation

    assert initial.max_abs_freq_error_pct > FREQUENCY_GATE_PERCENT
    assert initial.min_mac < MAC_GATE


@criterion("AC-UPD-003")
@pytest.mark.parametrize("case", sorted(TWINS))
def test_ac_upd_003_updating_recovers_the_true_factors(case):
    """+/-20 % detuning is recovered to 1e-3 within ten iterations, gates met."""
    result, error = _run_twin(case)
    final = result.final_correlation

    assert result.converged, result.message
    assert result.iterations <= MAX_UPDATING_ITERATIONS
    assert error <= RECOVERY_TOLERANCE, f"{case}: worst factor error {error:.3e}"
    assert final.max_abs_freq_error_pct <= FREQUENCY_GATE_PERCENT
    assert final.min_mac >= MAC_GATE


@criterion("AC-UPD-003")
@pytest.mark.parametrize("case", sorted(TWINS))
def test_ac_upd_003_the_objective_never_increases(case):
    """Every recorded iteration is an accepted step with a non-increasing cost."""
    result, _ = _run_twin(case)
    costs = [record.cost for record in result.history]

    assert costs, "the run recorded no iterations"
    assert all(record.accepted for record in result.history)
    assert all(
        later <= earlier for earlier, later in zip(costs, costs[1:], strict=False)
    ), f"{case}: cost history is not non-increasing: {costs}"
    assert costs[-1] < 1e-20 * result.initial_cost


@criterion("AC-UPD-003")
def test_ac_upd_003_recovery_survives_shape_residuals_and_a_fd_jacobian():
    """The same twin is recovered through the finite-difference/MAC-residual path.

    Dropping ``sensitivity_function`` and enabling the shape residual swaps the
    analytical Jacobian for central differences of the whole residual vector,
    which is the route a user without derivative matrices takes.
    """
    result, error = _run_twin("stiffness", shape_weight=1.0)

    assert result.converged, result.message
    assert result.iterations <= MAX_UPDATING_ITERATIONS
    assert error <= RECOVERY_TOLERANCE
    assert result.final_correlation.min_mac >= MAC_GATE
    assert result.final_correlation.max_abs_freq_error_pct <= FREQUENCY_GATE_PERCENT
