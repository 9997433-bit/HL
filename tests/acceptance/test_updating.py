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
- **AC-UPD-004** (contract, MS-3.4) — the objective is non-increasing over the
  accepted steps, every run reports a stop reason from the closed
  ``STOP_REASONS`` vocabulary and every token in it is reachable, and a
  wrong-signed Jacobian raises ``UpdatingDivergenceError`` after three
  consecutive accepted increases.
- **AC-UPD-005** (property, MS-3.4) — with four parameters against two
  residuals and an exactly collinear pair, the run completes, keeps every
  iterate inside the parameter bounds, never raises the objective, and leaves
  the unidentifiable direction where it started.
- **AC-UPD-006a** (property, MS-3.5) — the Bayesian MAP step reduces to the
  unregularized Gauss-Newton step as ``C_p^-1 -> 0``: identically at zero prior
  precision, to 1e-8 relative at precision scale 1e-12, and end to end where a
  sigma = 1e6 prior reproduces the AC-UPD-003 answer.
- **AC-UPD-006b** (property, MS-3.5) — the reported ``sigma_post`` never
  exceeds ``sigma_prior``, shrinks monotonically as the prior narrows, and a
  prior far tighter than the data holds ``theta*`` within 3 ``sigma_prior`` of
  ``theta_0`` instead of at the truth AC-UPD-003 recovers.
- **AC-UPD-007** (twin, MS-3.6) — a deliberately duplicated parameter is caught
  by the pre-updating collinearity screen at pairwise cosine > 0.99, one of the
  pair is frozen with a reported reason, and updating still recovers the
  survivor to the AC-UPD-003 gates.
- **AC-UPD-008** (twin, MS-3.2) — on a twin whose two lowest modes swap places
  between the starting point and the truth, per-iteration MAC pairing keeps
  every residual attached to the mode it physically belongs to and recovers the
  parameters; freezing the pairing to the mode order converges onto the wrong
  ones with a zero frequency residual, which is what makes the re-pairing
  load-bearing.
- **AC-UPD-009** (twin, MS-3.2/MS-7.3) — the same chain, damped and detuned in
  three stiffness factors and one damping factor, is recovered from noisy
  synthesized FRFs alone: the MS-3.2 real/imaginary residual reaches
  ``|theta* - theta_true|_inf <= 1e-2`` and FRAC >= 0.99 on frequency lines
  held out of the fit, and the analytic ``dH/dtheta`` matches central finite
  differences to 1e-6.

The model is the ``ten_dof_chain`` fixture split into three stiffness groups
and two mass groups. The split is affine, so the group matrices *are* the
parameter derivatives, and the test pins the split to the fixture: at
``theta = 1`` the contributions must sum back to the fixture ``K`` and ``M``.
"""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.correlation import modal_scale_factor
from openfemlab.exceptions import UpdatingDivergenceError
from openfemlab.solver.dynamics import (
    FrequencyResponse,
    RayleighDamping,
    direct_frf,
    frac,
)
from openfemlab.updating import (
    BayesianUpdater,
    BayesianUpdatingResult,
    FRFResidual,
    FRFUpdater,
    GaussianPrior,
    ModelUpdater,
    ParameterSet,
    ScalingModel,
    UpdatableParameter,
    map_step,
)
from openfemlab.updating.sensitivity import eigenvalue_sensitivity, mode_shape_sensitivity
from openfemlab.updating.updater import CONVERGED_REASONS, STOP_REASONS
from openfemlab.workflow import run_correction, select_parameters

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

#: Gates of AC-UPD-006a/b. The MAP twin is the AC-UPD-003 ``stiffness`` case,
#: so the deterministic answer the weak-prior limit must reproduce is already
#: pinned by the tests above.
GAUSS_NEWTON_LIMIT = 1e-8
PRIOR_PRECISION_SCALES = (1.0e-2, 1.0e-6, 1.0e-12)
PRIOR_STANDARD_DEVIATIONS = (1.0, 0.1, 0.01)
TIGHT_PRIOR_STD = 0.01
CREDIBLE_SIGMAS = 3.0
BAYES_CASE = "stiffness"

#: An off-centre prior mean for AC-UPD-006a, so a vanishing MAP correction can
#: only come from the vanishing precision and not from a prior that agrees.
BAYES_PRIOR_MEAN = (0.70, 1.30, 0.90)

#: Gate of AC-UPD-007; its recovery half reuses the AC-UPD-003 gates above.
COLLINEARITY_COSINE = 0.99

NUM_MASSES = 10
NUM_MODES = 6
STIFFNESS_GROUPS = ((1, 2, 3), (4, 5, 6), (7, 8, 9, 10))
MASS_GROUPS = ((1, 2, 3, 4, 5), (6, 7, 8, 9, 10))
PARAMETER_NAMES = ("k1", "k2", "k3", "m1", "m2")

#: AC-UPD-007 twin: ``k1`` is detuned and ``k1_twin`` scales the same springs.
DUPLICATED_TRUTH = {"k1": 1.20, "k2": 0.80, "k3": 1.15, "k1_twin": 1.00}

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


# ------------------------------------- AC-UPD-006a/b Bayesian MAP (MS-3.5)


def _bayes_free() -> tuple[str, ...]:
    return TWINS[BAYES_CASE][0]


def _map_linearization() -> tuple[np.ndarray, np.ndarray]:
    """``(J, r)`` of the relative-frequency residual at the nominal model.

    Assembled here rather than read back from a run: AC-UPD-006a compares two
    estimators on one linearization, so the linearization must not be produced
    by either of them.
    """
    free, truth = TWINS[BAYES_CASE]
    model = _scaling_model()
    measured = _twin_target(model, truth).frequencies
    nominal = {name: 1.0 for name in model.parameter_names}
    residual = (model.modal_data(nominal).frequencies - measured) / measured
    jacobian = model.frequency_sensitivity(nominal, list(free)) / measured[:, None]
    return jacobian, residual


def _gauss_newton_step(jacobian: np.ndarray, residual: np.ndarray) -> np.ndarray:
    return -np.linalg.solve(jacobian.T @ jacobian, jacobian.T @ residual)


def _run_bayesian_twin(prior: GaussianPrior) -> BayesianUpdatingResult:
    """``_run_twin(BAYES_CASE)`` with the MAP estimator swapped in.

    Same model, same twin, same analytical Jacobian and iteration budget, so
    the only difference against the deterministic run is the prior term.
    """
    free, truth = TWINS[BAYES_CASE]
    model = _scaling_model()
    target = _twin_target(model, truth)
    updater = BayesianUpdater(
        model,
        _twin_parameters(free),
        target.frequencies,
        target.mode_shapes,
        prior=prior,
        max_iterations=MAX_UPDATING_ITERATIONS,
        shape_weight=0.0,
        sensitivity_function=model.sensitivity_function(list(free)),
    )
    return updater.run()


@criterion("AC-UPD-006a")
def test_ac_upd_006a_an_uninformative_prior_is_exactly_gauss_newton():
    """At ``C_p^-1 = 0`` the limit is an identity, not an approximation."""
    free = _bayes_free()
    jacobian, residual = _map_linearization()
    prior = GaussianPrior.uninformative(free)

    step = map_step(
        jacobian,
        residual,
        design_values=np.ones(len(free)),
        prior_mean=np.array(BAYES_PRIOR_MEAN),
        prior_precision=prior.precision(len(free)),
    )

    np.testing.assert_allclose(step, _gauss_newton_step(jacobian, residual), rtol=1e-12)


@criterion("AC-UPD-006a")
def test_ac_upd_006a_the_map_step_converges_to_the_gauss_newton_step():
    """The MAP/GN gap falls with ``C_p^-1`` and clears 1e-8 at precision 1e-12."""
    free = _bayes_free()
    jacobian, residual = _map_linearization()
    reference = _gauss_newton_step(jacobian, residual)
    scale = np.linalg.norm(reference)

    differences = [
        float(
            np.linalg.norm(
                map_step(
                    jacobian,
                    residual,
                    design_values=np.ones(len(free)),
                    prior_mean=np.array(BAYES_PRIOR_MEAN),
                    prior_precision=precision * np.eye(len(free)),
                )
                - reference
            )
            / scale
        )
        for precision in PRIOR_PRECISION_SCALES
    ]

    # The gate says nothing unless the strongest prior of the sweep bends the
    # step in the first place.
    assert differences[0] > 0.1
    assert all(
        later < earlier
        for earlier, later in zip(differences, differences[1:], strict=False)
    ), f"MAP/GN differences are not decreasing: {differences}"
    assert differences[-1] <= GAUSS_NEWTON_LIMIT


@criterion("AC-UPD-006a")
def test_ac_upd_006a_a_vanishing_prior_leaves_the_deterministic_run_untouched():
    """End to end: a sigma = 1e6 prior reproduces the AC-UPD-003 recovery."""
    free = _bayes_free()
    deterministic, _ = _run_twin(BAYES_CASE)
    bayesian = _run_bayesian_twin(GaussianPrior.from_std(1.0e6))

    assert bayesian.converged, bayesian.message
    assert bayesian.iterations <= MAX_UPDATING_ITERATIONS
    difference = max(
        abs(bayesian.parameters[name] - deterministic.parameters[name]) for name in free
    )
    assert difference <= GAUSS_NEWTON_LIMIT, f"MAP drifted from Gauss-Newton by {difference:.3e}"
    assert bayesian.final_correlation.max_abs_freq_error_pct <= FREQUENCY_GATE_PERCENT
    assert bayesian.final_correlation.min_mac >= MAC_GATE


@criterion("AC-UPD-006b")
@pytest.mark.parametrize("sigma", PRIOR_STANDARD_DEVIATIONS)
def test_ac_upd_006b_the_posterior_is_never_wider_than_the_prior(sigma):
    """``sigma_post <= sigma_prior`` componentwise, and below the data-only width."""
    free = _bayes_free()
    prior = GaussianPrior.from_std(sigma)
    result = _run_bayesian_twin(prior)
    data_only = _run_bayesian_twin(GaussianPrior.uninformative(free))

    posterior = result.posterior
    assert posterior.names == list(free)
    assert np.all(posterior.std <= prior.std(len(free)))
    assert np.all(posterior.std <= data_only.posterior.std)
    np.testing.assert_allclose(np.diag(posterior.correlation()), np.ones(len(free)), atol=1e-12)


@criterion("AC-UPD-006b")
def test_ac_upd_006b_tightening_the_prior_shrinks_the_posterior():
    """Every narrowing of the prior strictly narrows every posterior marginal."""
    widths = [
        _run_bayesian_twin(GaussianPrior.from_std(sigma)).posterior.std
        for sigma in PRIOR_STANDARD_DEVIATIONS
    ]

    assert all(
        np.all(tighter < wider)
        for wider, tighter in zip(widths, widths[1:], strict=False)
    ), f"posterior widths do not contract with the prior: {widths}"


@criterion("AC-UPD-006b")
def test_ac_upd_006b_a_tight_prior_holds_the_solution_within_three_sigma():
    """A prior far tighter than the data pins ``theta*`` to ``theta_0``."""
    free, truth = TWINS[BAYES_CASE]
    result = _run_bayesian_twin(GaussianPrior.from_std(TIGHT_PRIOR_STD))

    start = np.ones(len(free))
    theta = np.array([result.parameters[name] for name in free])
    expected = np.array([truth[name] for name in free])
    limit = CREDIBLE_SIGMAS * TIGHT_PRIOR_STD

    assert result.converged, result.message
    assert np.max(np.abs(theta - start)) <= limit
    # The gate only means something because the data pull is real and refused:
    # the truth AC-UPD-003 recovers on this very rig sits far outside the ball.
    assert np.max(np.abs(expected - start)) > limit
    assert np.max(np.abs(theta - expected)) > RECOVERY_TOLERANCE

    lower, upper = result.posterior.interval(free[0], sigmas=CREDIBLE_SIGMAS)
    assert lower < result.parameters[free[0]] < upper


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
    assert np.max(np.abs(recovered - expected)) <= RECOVERY_TOLERANCE

    summary = report.final_correlation.summary
    assert summary.max_abs_freq_error_pct <= FREQUENCY_GATE_PERCENT
    assert summary.min_mac >= MAC_GATE


# ------------------------------------- AC-UPD-004 convergence and divergence

#: Gates handed to the updater for the ``gates_met`` exit. Loose next to the
#: MS-4.2 gates above, so the run reaches them well before it converges.
GATE_MIN_MAC = 0.99
GATE_MAX_FREQ_PCT = 0.5

#: Overrides that drive the twin onto each stop reason in turn.
#:
#: MS-3.4 names four termination criteria — the parameter step, the cost
#: decrease, the correlation gates and the iteration cap. The loop can also
#: reach a stationary point (``gradient_tol``) and exhaust its line search
#: (``no_step``), and the run below pins the whole set, so a seventh reason
#: cannot appear without this criterion being revisited.
#:
#: The twin is exactly solvable, so its gradient collapses to round-off before
#: either tolerance can fire; that is why every case other than ``gradient_tol``
#: has to switch the gradient test off to reach the criterion it is about.
AC_UPD_004_REASONS = {
    "gradient_tol": {},
    "step_tol": {"gradient_tolerance": 0.0},
    "cost_tol": {
        "gradient_tolerance": 0.0,
        "parameter_tolerance": 0.0,
        # Loose enough that the first step's ~95 % reduction already counts as
        # converged, which keeps the exit off the round-off floor.
        "cost_tolerance": 0.99,
    },
    "gates_met": {
        "target_min_mac": GATE_MIN_MAC,
        "target_max_freq_error_pct": GATE_MAX_FREQ_PCT,
    },
    "max_iter": {
        "max_iterations": 1,
        "gradient_tolerance": 0.0,
        "parameter_tolerance": 0.0,
        "cost_tolerance": 0.0,
    },
    "no_step": {
        "gradient_tolerance": 0.0,
        "parameter_tolerance": 0.0,
        "cost_tolerance": 0.0,
    },
}


def _wrong_sign_sensitivity(model: ScalingModel, free):
    """MS-3.4's "wrong-sign residual injection", as an analytical Jacobian.

    Handing the updater ``-dr/dx`` makes every Gauss-Newton step point uphill.
    With the line search switched off those steps are taken anyway, which is
    the situation the divergence guard exists for: a run walking away from the
    solution one accepted step at a time.
    """
    honest = model.sensitivity_function(list(free))

    def evaluate(*args, **kwargs):
        return -np.asarray(honest(*args, **kwargs), dtype=float)

    return evaluate


def _updater(case: str, **overrides) -> ModelUpdater:
    """An AC-UPD-003 twin updater with the analytical Jacobian, plus overrides.

    ``sensitivity_function="wrong_sign"`` swaps in :func:`_wrong_sign_sensitivity`
    so the divergence cases stay readable at the call site.
    """
    free, truth = TWINS[case]
    model = _scaling_model()
    target = _twin_target(model, truth)
    options = {
        "sensitivity_function": model.sensitivity_function(list(free)),
        "shape_weight": 0.0,
        "max_iterations": MAX_UPDATING_ITERATIONS,
    }
    options.update(overrides)
    if options.get("sensitivity_function") == "wrong_sign":
        options["sensitivity_function"] = _wrong_sign_sensitivity(model, free)
    return ModelUpdater(
        model, _twin_parameters(free), target.frequencies, target.mode_shapes, **options
    )


@criterion("AC-UPD-004")
@pytest.mark.parametrize("case", sorted(TWINS))
def test_ac_upd_004_the_objective_is_non_increasing_over_accepted_steps(case):
    """The line search only ever accepts a step that lowers ``J`` (MS-3.4)."""
    result = _updater(case).run()

    costs = result.accepted_costs
    assert costs, "the run accepted no step"
    assert costs == [record.cost for record in result.history if record.accepted]
    assert all(
        later <= earlier for earlier, later in zip(costs, costs[1:], strict=False)
    ), f"{case}: {costs}"
    assert costs[0] <= result.initial_cost
    assert result.final_cost == costs[-1]


@criterion("AC-UPD-004")
@pytest.mark.parametrize("case", sorted(TWINS))
def test_ac_upd_004_the_stop_reason_is_machine_readable(case):
    """``stop_reason`` is a token from a closed vocabulary, not prose."""
    result = _updater(case).run()

    assert result.stop_reason in STOP_REASONS
    assert result.converged is (result.stop_reason in CONVERGED_REASONS)
    assert result.message and result.message != result.stop_reason
    assert result.stop_reason in result.report()


@criterion("AC-UPD-004")
@pytest.mark.parametrize("reason", sorted(AC_UPD_004_REASONS))
def test_ac_upd_004_every_documented_stop_reason_is_reachable(reason):
    """Every token in the vocabulary is produced by some run of this model.

    A vocabulary nothing can produce would be no contract at all, so the
    reasons are driven one at a time by switching off whichever tests would
    otherwise fire first.
    """
    assert set(AC_UPD_004_REASONS) == set(STOP_REASONS)

    result = _updater("stiffness", **AC_UPD_004_REASONS[reason]).run()

    assert result.stop_reason == reason, result.report()
    assert result.converged is (reason in CONVERGED_REASONS)


@criterion("AC-UPD-004")
def test_ac_upd_004_the_gates_stop_the_run_before_the_tolerances_do():
    """``gates_met`` is an early exit, not a relabelled convergence."""
    gated = _updater(
        "stiffness",
        target_min_mac=GATE_MIN_MAC,
        target_max_freq_error_pct=GATE_MAX_FREQ_PCT,
    ).run()
    ungated = _updater("stiffness").run()

    assert gated.stop_reason == "gates_met"
    assert gated.converged
    assert gated.iterations < ungated.iterations
    assert gated.final_correlation.min_mac >= GATE_MIN_MAC
    assert gated.final_correlation.max_abs_freq_error_pct <= GATE_MAX_FREQ_PCT


@criterion("AC-UPD-004")
def test_ac_upd_004_a_wrong_sign_jacobian_aborts_as_a_divergence():
    """Three consecutive rising accepted steps raise ``UpdatingDivergenceError``."""
    updater = _updater(
        "stiffness", sensitivity_function="wrong_sign", line_search=False, max_iterations=20
    )

    with pytest.raises(UpdatingDivergenceError) as excinfo:
        updater.run()

    error = excinfo.value
    assert error.iteration == 3
    assert len(error.costs) == 3
    assert all(
        later > earlier for earlier, later in zip(error.costs, error.costs[1:], strict=False)
    ), error.costs


@criterion("AC-UPD-004")
def test_ac_upd_004_the_line_search_is_what_keeps_the_same_problem_from_diverging():
    """The guard is a backstop, not the first line of defence.

    The identical wrong-signed Jacobian with the line search left on cannot
    take a single uphill step, so the run stops at ``no_step`` with the initial
    model untouched instead of aborting. That contrast is what makes the
    divergence above a property of the run rather than of the model.
    """
    result = _updater(
        "stiffness", sensitivity_function="wrong_sign", max_iterations=20
    ).run()

    assert result.stop_reason == "no_step"
    assert not result.converged
    assert result.final_cost <= result.initial_cost
    assert result.accepted_costs == []


@criterion("AC-UPD-004")
def test_ac_upd_004_the_divergence_patience_is_the_documented_three_steps():
    """MS-3.4 says three, and the guard fires on exactly the patience it is given."""
    for patience in (1, 2, 3):
        updater = _updater(
            "stiffness",
            sensitivity_function="wrong_sign",
            line_search=False,
            max_iterations=20,
            divergence_patience=patience,
        )
        with pytest.raises(UpdatingDivergenceError) as excinfo:
            updater.run()
        assert excinfo.value.iteration == patience

    with pytest.raises(ValueError, match="divergence_patience"):
        _updater("stiffness", divergence_patience=0)


# --------------------------------------------- AC-UPD-005 ill-posed robustness

#: The over-parameterized statement: every spring group *and* the duplicate is
#: free, against a target of fewer modes than there are parameters.
ILL_POSED_TRUTH = {"k1": 1.20, "k2": 0.80, "k3": 1.15, "k1_twin": 1.00}
ILL_POSED_MODES = 2
PARAMETER_LOWER = 0.5
PARAMETER_UPPER = 2.0
NULL_SPACE_TOLERANCE = 1e-12


def _ill_posed_updater(**overrides) -> ModelUpdater:
    """More parameters than residuals, two of them exactly collinear.

    ``k1`` and ``k1_twin`` scale the same springs, so the sensitivity matrix is
    rank deficient by construction; restricting the target to two modes and
    dropping the shape residual leaves two residuals for four free parameters,
    which is the under-determined half of MS-3.4's robustness requirement.
    Unlike AC-UPD-007 the collinearity screen is deliberately bypassed here —
    the point is what the bare loop does when nobody removed the degeneracy.
    """
    model = _duplicated_model()
    names = list(model.parameter_names)
    target = model.modal_data(ILL_POSED_TRUTH)
    parameters = ParameterSet(
        [
            UpdatableParameter(name, 1.0, PARAMETER_LOWER, PARAMETER_UPPER)
            for name in names
        ]
    )
    options = {
        "sensitivity_function": model.sensitivity_function(names),
        "shape_weight": 0.0,
        "max_iterations": 30,
    }
    options.update(overrides)
    return ModelUpdater(
        model, parameters, target.frequencies[:ILL_POSED_MODES], None, **options
    )


def _iterates(result) -> np.ndarray:
    """``(n_iterations, n_parameters)`` table of the parameters at each step."""
    names = sorted(result.parameters)
    return np.array(
        [[record.parameters[name] for name in names] for record in result.history],
        dtype=float,
    )


@criterion("AC-UPD-005")
def test_ac_upd_005_the_statement_really_is_under_determined():
    """Guard: four parameters, two residuals, and a rank-deficient Jacobian."""
    result = _ill_posed_updater().run()

    assert len(result.parameters) == 4
    jacobian = result.sensitivity.matrix
    assert jacobian.shape == (ILL_POSED_MODES, 4)
    assert np.linalg.matrix_rank(jacobian) < jacobian.shape[1]
    # The duplicated pair is the degeneracy: identical sensitivity columns.
    names = list(result.sensitivity.parameter_names)
    left, right = names.index("k1"), names.index("k1_twin")
    np.testing.assert_allclose(jacobian[:, left], jacobian[:, right], rtol=1e-10)


@criterion("AC-UPD-005")
@pytest.mark.parametrize("method", ["levenberg-marquardt", "gauss-newton"])
def test_ac_upd_005_the_ill_posed_run_completes_without_raising(method):
    """No exception, a finite answer, and a stop reason from the vocabulary."""
    result = _ill_posed_updater(method=method).run()

    assert result.stop_reason in STOP_REASONS
    assert np.all(np.isfinite(list(result.parameters.values())))
    assert np.isfinite(result.final_cost)
    assert result.history, "the run recorded no iterations"


@criterion("AC-UPD-005")
@pytest.mark.parametrize("method", ["levenberg-marquardt", "gauss-newton"])
def test_ac_upd_005_every_iterate_stays_inside_the_bounds(method):
    """Bounded iterates: the projection holds at every recorded step, not just the last."""
    result = _ill_posed_updater(method=method).run()

    iterates = _iterates(result)
    assert iterates.size
    assert np.all(iterates >= PARAMETER_LOWER - 1e-12), iterates.min()
    assert np.all(iterates <= PARAMETER_UPPER + 1e-12), iterates.max()
    for parameter in result.parameter_set:
        assert parameter.lower <= parameter.value <= parameter.upper


@criterion("AC-UPD-005")
@pytest.mark.parametrize("method", ["levenberg-marquardt", "gauss-newton"])
def test_ac_upd_005_the_objective_is_non_increasing_and_bounded(method):
    """``J`` falls monotonically and the iterates do not run away."""
    result = _ill_posed_updater(method=method).run()

    costs = result.accepted_costs
    assert costs
    assert all(
        later <= earlier for earlier, later in zip(costs, costs[1:], strict=False)
    ), costs
    assert result.final_cost < result.initial_cost
    assert np.max(np.abs(_iterates(result))) <= PARAMETER_UPPER


@criterion("AC-UPD-005")
def test_ac_upd_005_the_unidentifiable_direction_is_left_where_it_started():
    """What an under-determined run may and may not claim.

    Two residuals cannot pin four parameters, so no individual value here is
    recoverable — not even the sum ``k1 + k1_twin`` that collapsing the
    duplicate leaves behind, because three effective factors still outnumber
    the two frequencies. What the run must *not* do is wander along the null
    space: the pair enters the stiffness identically and starts from the same
    value, so their difference is the degenerate direction, and the iteration
    has to leave it at zero from the first step to the last. The fit is the
    part that is determined, and it is reached.
    """
    result = _ill_posed_updater(regularization=1e-6).run()

    recovered = result.parameters
    assert recovered["k1"] == pytest.approx(
        recovered["k1_twin"], abs=NULL_SPACE_TOLERANCE
    )

    names = sorted(recovered)
    left, right = names.index("k1"), names.index("k1_twin")
    iterates = _iterates(result)
    drift = np.max(np.abs(iterates[:, left] - iterates[:, right]))
    assert drift <= NULL_SPACE_TOLERANCE, drift

    # The identifiable combination did move: the run fitted, it did not idle.
    assert recovered["k1"] + recovered["k1_twin"] > 2.0
    assert result.final_correlation.max_abs_freq_error_pct <= FREQUENCY_GATE_PERCENT


# ------------------------------------------------- AC-UPD-008 mode switching

#: A four-DOF model whose first two modes belong to independent substructures,
#: so a parameter change moves one past the other and the mode *order* stops
#: matching the mode *identity*. The spectator modes above them stay put, which
#: is what makes a wrong pairing visible as a frequency error rather than as
#: general noise.
CROSSING_SPECTATORS = (9.0, 16.0)
CROSSING_TRUTH = {"ka": 3.0, "kb": 0.5}
CROSSING_BOUNDS = (0.1, 10.0)

#: The pairing must be exact on this twin: the shapes are unit vectors, so a
#: correct pair has MAC 1 and any other pair has MAC 0.
CROSSING_MAC_TOLERANCE = 1e-12


def _crossing_model() -> ScalingModel:
    stiffness_parts = {
        "ka": np.diag([1.0, 0.0, 0.0, 0.0]),
        "kb": np.diag([0.0, 4.0, 0.0, 0.0]),
    }
    return ScalingModel(
        stiffness_parts,
        base_stiffness=np.diag([0.0, 0.0, *CROSSING_SPECTATORS]),
        base_mass=np.eye(4),
        num_modes=4,
        use_solver=False,
    )


def _crossing_parameters() -> ParameterSet:
    lower, upper = CROSSING_BOUNDS
    return ParameterSet(
        [
            UpdatableParameter(name, 1.0, lower, upper, kind="stiffness")
            for name in ("ka", "kb")
        ]
    )


def _crossing_updater(pairing: str = "mac") -> ModelUpdater:
    model = _crossing_model()
    target = model.modal_data(CROSSING_TRUTH)
    return ModelUpdater(
        model,
        _crossing_parameters(),
        target.frequencies,
        target.mode_shapes,
        mode_pairing=pairing,
        shape_weight=0.0,
        max_iterations=MAX_UPDATING_ITERATIONS,
        sensitivity_function=model.sensitivity_function(["ka", "kb"]),
    )


@criterion("AC-UPD-008")
def test_ac_upd_008_the_twin_really_crosses_two_modes():
    """Guard: the two lowest modes swap places between the start and the truth."""
    model = _crossing_model()
    start = model.modal_data({"ka": 1.0, "kb": 1.0})
    truth = model.modal_data(CROSSING_TRUTH)

    # Mode "a" is the one living on DOF 0; at the start it is the lowest mode
    # and at the truth it is the second, so the order reverses on the way.
    assert int(np.argmax(np.abs(start.mode_shapes[0, :]))) == 0
    assert int(np.argmax(np.abs(truth.mode_shapes[0, :]))) == 1
    assert start.frequencies[0] < start.frequencies[1]
    assert truth.frequencies[0] < truth.frequencies[1]


@criterion("AC-UPD-008")
def test_ac_upd_008_re_pairing_recovers_the_true_parameters_through_the_crossing():
    """Per-iteration MAC pairing keeps the residuals on the physical modes."""
    updater = _crossing_updater("mac")

    result = updater.run()

    assert result.converged, result.message
    for name, expected in CROSSING_TRUTH.items():
        assert result.parameters[name] == pytest.approx(expected, abs=RECOVERY_TOLERANCE)
    assert result.final_correlation.max_abs_freq_error_pct <= FREQUENCY_GATE_PERCENT
    assert result.final_correlation.min_mac >= MAC_GATE


@criterion("AC-UPD-008")
def test_ac_upd_008_every_iterate_is_paired_to_the_physically_correct_mode():
    """Ground-truth MAC tracking over the recorded trajectory, not just its end.

    The pairing is recomputed from the parameters each accepted step recorded,
    so this reads the actual path the run took — including the iterates on the
    far side of the crossing, where the pairing is no longer the identity.
    """
    updater = _crossing_updater("mac")
    result = updater.run()
    target_shapes = updater.target.mode_shapes
    trajectory = [{"ka": 1.0, "kb": 1.0}, *(record.parameters for record in result.history)]

    orderings = set()
    for values in trajectory:
        data = updater.model(values)
        pairs = updater.pair(data)
        assert len(pairs) == target_shapes.shape[1]
        for test_index, fe_index in pairs:
            overlap = abs(float(target_shapes[:, test_index] @ data.mode_shapes[:, fe_index]))
            assert overlap == pytest.approx(1.0, abs=CROSSING_MAC_TOLERANCE), (
                f"target mode {test_index} was paired to model mode {fe_index}"
            )
        orderings.add(tuple(fe for _, fe in pairs))

    assert len(orderings) > 1, "the trajectory never crossed, so nothing was re-paired"


@criterion("AC-UPD-008")
def test_ac_upd_008_freezing_the_pairing_to_the_mode_order_gets_it_wrong():
    """Why the re-pairing is load-bearing rather than a detail of the loop.

    With ``mode_pairing="order"`` the residual keeps target mode 0 attached to
    model mode 0 across the crossing. The run still converges, and it drives
    its frequency residual to zero — onto the parameters that put the right
    frequencies on the *wrong* modes. Only the shape correlation exposes it,
    which is why the criterion asks for ground-truth MAC tracking rather than
    for a converged run.
    """
    result = _crossing_updater("order").run()

    assert result.converged
    recovered = np.array([result.parameters[name] for name in CROSSING_TRUTH])
    expected = np.array(list(CROSSING_TRUTH.values()))
    assert np.max(np.abs(recovered - expected)) > RECOVERY_TOLERANCE
    assert result.final_correlation.min_mac < MAC_GATE


# ------------------------------------------ AC-UPD-009 FRF residual updating

#: The damped twin: the AC-UPD-003 chain with its masses held fixed, three
#: stiffness factors detuned by up to 20 % and the damping level by 30 %.
FRF_FREE = ("k1", "k2", "k3", "c")
FRF_TRUTH = {"k1": 0.80, "k2": 1.20, "k3": 0.85, "c": 1.30}

#: Instrumentation: four sensors along the chain, driven at the free end.
FRF_SENSOR_DOFS = (1, 4, 7, 9)
FRF_DRIVE_DOFS = (9,)

#: 2 % modal damping at both ends of the nominal spectrum, and a band wide
#: enough to bracket every resonance of both the nominal and the true model.
FRF_DAMPING_RATIO = 0.02
FRF_BAND = (0.02, 0.34)
FRF_NUM_LINES = 129

#: Every second line is fitted and the rest are the independent check, so the
#: held-out gate reads lines the residual never saw.
FRF_FITTED_LINES = np.arange(0, FRF_NUM_LINES, 2)
FRF_HELD_OUT_LINES = np.arange(1, FRF_NUM_LINES, 2)

#: Multiplicative complex measurement noise, seeded per AC section 1.4.
FRF_NOISE = 0.02
FRF_SEED = 20260826

#: Gates of AC-UPD-009.
FRF_RECOVERY_TOLERANCE = 1e-2
FRAC_GATE = 0.99
FRF_SENSITIVITY_RTOL = 1e-6
FRF_ROUTE_AGREEMENT = 1e-5
FRF_MAX_ITERATIONS = 30


def _frf_model() -> ScalingModel:
    """The AC-UPD-003 chain with the masses folded into the fixed base."""
    stiffness_parts, mass_parts = spring_chain_parts(
        NUM_MASSES, STIFFNESS_GROUPS, MASS_GROUPS
    )
    return ScalingModel(
        stiffness_parts,
        base_mass=sum(mass_parts.values()),
        num_modes=NUM_MASSES,
        use_solver=False,
    )


def _frf_reference_damping(model: ScalingModel) -> np.ndarray:
    """``C_ref = alpha M + beta K`` at 2 % over the nominal band.

    The updated factor ``c`` scales this matrix, so ``dC/dc = C_ref`` exactly
    and the damping level is identifiable alongside the stiffness.
    """
    nominal = {name: 1.0 for name in model.parameter_names}
    frequencies = model.modal_data(nominal).frequencies
    rayleigh = RayleighDamping.from_frequencies(
        frequencies[0], frequencies[-1], FRF_DAMPING_RATIO, FRF_DAMPING_RATIO
    )
    K, M = model.assemble(nominal)
    return dense(rayleigh.matrix(K, M))


def _frf_synthesis(
    model: ScalingModel,
    reference_damping: np.ndarray,
    values: dict[str, float],
    frequencies: np.ndarray,
):
    """Invert the dynamic stiffness at the sensor set for one parameter point.

    Assembled straight from the M6 kernel rather than through the provider
    under test, so the twin's "measurement" and the model it is judged against
    do not share an implementation.
    """
    K, M = model.assemble(values)
    return direct_frf(
        frequencies,
        dense(K),
        dense(M),
        float(values["c"]) * reference_damping,
        response_dofs=FRF_SENSOR_DOFS,
        excitation_dofs=FRF_DRIVE_DOFS,
    )


def _frf_measurement(
    model: ScalingModel, reference_damping: np.ndarray, frequencies: np.ndarray
) -> FrequencyResponse:
    """The truth FRFs with 2 % multiplicative complex noise on every entry."""
    clean = _frf_synthesis(model, reference_damping, FRF_TRUTH, frequencies)
    rng = np.random.default_rng(FRF_SEED)
    shape = clean.data.shape
    noise = FRF_NOISE * (
        rng.standard_normal(shape) + 1j * rng.standard_normal(shape)
    ) / np.sqrt(2.0)
    return FrequencyResponse(
        frequencies=clean.frequencies,
        data=clean.data * (1.0 + noise),
        response_dofs=clean.response_dofs,
        excitation_dofs=clean.excitation_dofs,
        response_type=clean.response_type,
    )


def _frf_rig() -> tuple[ScalingModel, np.ndarray, FrequencyResponse, FRFResidual]:
    """``(model, C_ref, measurement, residual provider)`` of the twin."""
    model = _frf_model()
    reference_damping = _frf_reference_damping(model)
    line = np.linspace(*FRF_BAND, FRF_NUM_LINES)
    measured = _frf_measurement(model, reference_damping, line)
    residual = FRFResidual(
        model,
        measured,
        damping_parts={"c": reference_damping},
        lines=FRF_FITTED_LINES,
    )
    return model, reference_damping, measured, residual


def _frf_parameters() -> ParameterSet:
    return ParameterSet(
        [
            UpdatableParameter(
                name,
                value=1.0,
                lower=0.5,
                upper=2.0,
                kind="damping" if name == "c" else "stiffness",
            )
            for name in FRF_FREE
        ]
    )


def _frf_nominal() -> dict[str, float]:
    return {name: 1.0 for name in FRF_FREE}


def _frf_run(*, analytic_jacobian: bool = True):
    """Run the FRF updater on the twin; returns ``(updater, result, error)``."""
    _, _, _, residual = _frf_rig()
    updater = FRFUpdater(
        residual,
        _frf_parameters(),
        analytic_jacobian=analytic_jacobian,
        max_iterations=FRF_MAX_ITERATIONS,
    )
    result = updater.run()
    error = max(abs(result.parameters[name] - FRF_TRUTH[name]) for name in FRF_FREE)
    return updater, result, error


def _held_out_frac(
    model: ScalingModel,
    reference_damping: np.ndarray,
    measured: FrequencyResponse,
    values: dict[str, float],
) -> np.ndarray:
    """Per-channel FRAC against the measurement on the unfitted lines."""
    lines = FRF_HELD_OUT_LINES
    reference = measured.data[lines].reshape(lines.size, -1)
    trial = _frf_synthesis(
        model, reference_damping, values, measured.frequencies[lines]
    ).data.reshape(lines.size, -1)
    return np.atleast_1d(frac(reference, trial, axis=0))


def _central_difference_frf_jacobian(
    residual: FRFResidual, values: dict[str, float], names: list[str]
) -> np.ndarray:
    """``dr/dtheta`` by central differences of the assembled residual vector."""
    columns = []
    for name in names:
        forward, backward = dict(values), dict(values)
        forward[name] += FD_RELATIVE_STEP
        backward[name] -= FD_RELATIVE_STEP
        columns.append(
            (
                residual.residual(residual.state(forward))
                - residual.residual(residual.state(backward))
            )
            / (2.0 * FD_RELATIVE_STEP)
        )
    return np.column_stack(columns)


@criterion("AC-UPD-009")
def test_ac_upd_009_the_damped_twin_starts_uncorrelated_and_is_really_noisy():
    """Guard: the nominal FRFs fail the gate, and the measurement carries noise."""
    model, damping, measured, residual = _frf_rig()
    nominal = _frf_nominal()

    fitted = residual.correlation(residual.state(nominal))
    held_out = _held_out_frac(model, damping, measured, nominal)

    assert fitted.max_frac < FRAC_GATE
    assert held_out.max() < FRAC_GATE

    clean = _frf_synthesis(model, damping, FRF_TRUTH, measured.frequencies).data
    deviation = float(np.mean(np.abs(measured.data - clean) / np.abs(clean)))
    assert 0.5 * FRF_NOISE < deviation < 2.0 * FRF_NOISE


@criterion("AC-UPD-009")
def test_ac_upd_009_the_analytic_frf_sensitivity_matches_central_differences():
    """``dH/dp = -H (dK - omega^2 dM + i omega dC) H`` agrees to 1e-6 relative."""
    _, _, _, residual = _frf_rig()
    nominal = _frf_nominal()
    names = list(FRF_FREE)

    analytic = residual.jacobian(nominal, names, residual.state(nominal))
    finite = _central_difference_frf_jacobian(residual, nominal, names)

    assert analytic.shape == (residual.n_residuals, len(names))
    error = np.max(np.abs(analytic - finite)) / np.max(np.abs(finite))
    assert error <= FRF_SENSITIVITY_RTOL, f"worst relative error {error:.3e}"


@criterion("AC-UPD-009")
def test_ac_upd_009_the_frf_residual_recovers_the_detuned_factors():
    """Stiffness and damping come back out of the noisy FRFs to 1e-2."""
    updater, result, error = _frf_run()

    assert result.converged, result.message
    assert result.stop_reason in CONVERGED_REASONS
    assert error <= FRF_RECOVERY_TOLERANCE, f"worst factor error {error:.3e}"
    assert result.final_cost < result.initial_cost
    assert result.initial_frf_correlation.min_frac < FRAC_GATE
    assert result.final_frf_correlation.min_frac >= FRAC_GATE
    # One model evaluation per accepted iteration: the analytic Jacobian is
    # the active path, not a finite-difference sweep behind it.
    assert updater.n_evaluations <= 2 * result.iterations + 1


@criterion("AC-UPD-009")
def test_ac_upd_009_the_held_out_frequency_lines_confirm_the_update():
    """FRAC >= 0.99 on lines the residual never saw — the criterion's gate."""
    model, damping, measured, _ = _frf_rig()
    _, result, _ = _frf_run()

    before = _held_out_frac(model, damping, measured, _frf_nominal())
    after = _held_out_frac(model, damping, measured, result.parameters)

    assert after.min() >= FRAC_GATE, f"worst held-out FRAC {after.min():.4f}"
    # The gate measures the update rather than the twin: the starting model is
    # nowhere near it on the very same lines.
    assert before.max() < FRAC_GATE


@criterion("AC-UPD-009")
def test_ac_upd_009_the_finite_difference_route_reaches_the_same_answer():
    """The analytic Jacobian is an accelerator, not a different estimator."""
    analytic_updater, analytic, _ = _frf_run()
    finite_updater, finite, error = _frf_run(analytic_jacobian=False)

    assert error <= FRF_RECOVERY_TOLERANCE
    difference = max(
        abs(analytic.parameters[name] - finite.parameters[name]) for name in FRF_FREE
    )
    assert difference <= FRF_ROUTE_AGREEMENT, (
        f"the two Jacobian routes disagree by {difference:.3e}"
    )
    assert finite_updater.n_evaluations > 4 * analytic_updater.n_evaluations


@criterion("AC-UPD-010")
def test_ac_upd_010_resolver_scaling_spec_recovers_a_twin():
    """Dotted targets build an affine scaling model that recovers a perturbed E."""
    from openfemlab.core.model import Material, Section
    from openfemlab.mesh.simple import bar_mesh
    from openfemlab.updating import Parameter, ParameterType, update_model
    from openfemlab.updating.resolver import resolve_scaling_spec

    steel = Material(E=2.1e11, density=7850.0, name="steel")
    section = Section(area=1.0e-4, name="strip")
    model = bar_mesh(1.0, 10, steel, section, fixed_start=True, fixed_end=False)
    parameter = Parameter(
        "E.steel",
        "materials.steel.E",
        reference=steel.E,
        lower=0.5,
        upper=2.0,
        kind=ParameterType.STIFFNESS,
    )
    spec = resolve_scaling_spec(model, [parameter], num_modes=3)
    truth = {"E.steel": 1.15}
    target = spec.scaling_model(truth)

    result = update_model(
        spec.scaling_model,
        spec.parameter_set(),
        target.frequencies,
        target.mode_shapes,
    )

    assert result.converged
    assert result.parameters["E.steel"] == pytest.approx(truth["E.steel"], rel=1e-3)
