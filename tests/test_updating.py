"""Sensitivity-based model updating: derivatives, and twin-experiment recovery.

The reference structure is a fixed-free spring/mass chain whose springs and
masses are collected into groups.  Each group carries one dimensionless scaling
factor, so the assembly is affine in the parameters and every analytical
derivative has an exact finite-difference counterpart to check against.

The updating tests are *twin experiments*: synthetic "measurements" are
generated from a deliberately detuned truth model, the updater starts from the
nominal one, and the recovered parameters are compared with the truth.
"""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.correlation import correlate, mac_value, pair_modes
from openfemlab.updating import (
    ModalData,
    ModelUpdater,
    Parameter,
    ParameterSet,
    ParameterType,
    ScalingModel,
    UpdatableParameter,
    as_modal_data,
    eigenvalue_sensitivity,
    eigenvalue_to_frequency_sensitivity,
    finite_difference_jacobian,
    modal_sensitivity,
    mode_shape_sensitivity,
    relative_sensitivity,
    track_modes,
    update_model,
)
from tests.modal_reference import (
    SpringMassChain,
    make_model_function,
    two_dof_chain,
    uniform_chain,
)

N_DOF = 10
BASE_STIFFNESS = 1.0e6
BASE_MASS = 2.0


# --------------------------------------------------------------------- helpers


def chain_stiffness(stiffnesses: np.ndarray) -> np.ndarray:
    """Fixed-free chain: spring ``j`` links DOF ``j-1`` (ground for 0) to DOF ``j``."""
    n = stiffnesses.size
    K = np.zeros((n, n))
    for j, k in enumerate(stiffnesses):
        K[j, j] += k
        if j > 0:
            K[j - 1, j - 1] += k
            K[j - 1, j] -= k
            K[j, j - 1] -= k
    return K


def group_masks(n_dof: int, n_groups: int) -> list[np.ndarray]:
    """Contiguous, near-equal partition of the ``n_dof`` springs/masses."""
    bounds = np.linspace(0, n_dof, n_groups + 1).astype(int)
    return [
        np.isin(np.arange(n_dof), np.arange(lo, hi)).astype(float)
        for lo, hi in zip(bounds[:-1], bounds[1:], strict=False)
    ]


def chain_model(
    *,
    n_dof: int = N_DOF,
    n_stiffness_groups: int = 4,
    n_mass_groups: int = 0,
    num_modes: int = 6,
    dof_selection: np.ndarray | None = None,
) -> ScalingModel:
    """Grouped spring/mass chain as an affine :class:`ScalingModel`."""
    stiffness_parts = {
        f"k{g}": chain_stiffness(BASE_STIFFNESS * mask)
        for g, mask in enumerate(group_masks(n_dof, n_stiffness_groups))
    }
    mass_parts = {
        f"m{g}": np.diag(BASE_MASS * mask)
        for g, mask in enumerate(group_masks(n_dof, n_mass_groups))
    }
    base_mass = None if n_mass_groups else np.eye(n_dof) * BASE_MASS
    return ScalingModel(
        stiffness_parts,
        mass_parts,
        base_mass=base_mass,
        num_modes=num_modes,
        dof_selection=dof_selection,
        # The core element/assembly stack is exercised by its own tests; here the
        # matrices are given directly, so the dense eigensolver is enough.
        use_solver=False,
    )


def parameter_set(names, lower=0.5, upper=2.0, **kwargs) -> ParameterSet:
    return ParameterSet(
        [UpdatableParameter(name, 1.0, lower, upper, **kwargs) for name in names]
    )


def correlation_of(target, data) -> tuple[float, float]:
    """``(max |Δf| in %, min MAC)`` of ``data`` against the target mode set."""
    pairing = pair_modes(
        test_shapes=target.mode_shapes,
        fe_shapes=data.mode_shapes,
        test_frequencies=target.frequencies,
        fe_frequencies=data.frequencies,
    )
    errors = np.abs(pairing.frequency_errors_pct)
    return float(errors.max()), float(pairing.mac_values.min())


@pytest.fixture
def model() -> ScalingModel:
    return chain_model()


# ---------------------------------------------------------------- sensitivity


def test_eigenvalue_sensitivity_matches_central_differences(model: ScalingModel) -> None:
    """AC-UPD-001: analytical dλ/dp agrees with finite differences to 1e-6."""
    theta = np.array([1.05, 0.92, 1.11, 0.97])
    eigenvalues, shapes = model.eigen(theta)
    dK, dM = model.derivatives()
    analytic = eigenvalue_sensitivity(shapes, eigenvalues, dK, dM)

    step = 1.0e-6
    numeric = np.empty_like(analytic)
    for k in range(theta.size):
        forward, backward = theta.copy(), theta.copy()
        forward[k] += step
        backward[k] -= step
        numeric[:, k] = (model.eigen(forward)[0] - model.eigen(backward)[0]) / (2.0 * step)

    relative = np.abs(analytic - numeric) / np.abs(numeric)
    assert relative.max() < 1.0e-6


def test_eigenvalue_sensitivity_of_mass_parameters_is_negative() -> None:
    """Scaling up a mass can only lower the eigenvalues it participates in."""
    massy = chain_model(n_mass_groups=2)
    theta = {name: 1.0 for name in massy.parameter_names}
    eigenvalues, shapes = massy.eigen(theta)
    dK, dM = massy.derivatives(["m0", "m1"])
    sensitivity = eigenvalue_sensitivity(shapes, eigenvalues, dK, dM)
    assert np.all(sensitivity < 0.0)


def test_eigenvalue_to_frequency_sensitivity_is_the_chain_rule(model: ScalingModel) -> None:
    theta = np.ones(len(model.parameter_names))
    eigenvalues, shapes = model.eigen(theta)
    dK, dM = model.derivatives()
    frequencies = np.sqrt(eigenvalues) / (2.0 * np.pi)

    converted = eigenvalue_to_frequency_sensitivity(
        eigenvalue_sensitivity(shapes, eigenvalues, dK, dM), frequencies
    )
    np.testing.assert_allclose(converted, model.frequency_sensitivity(theta), rtol=1e-12)

    step = 1.0e-6
    for k in range(theta.size):
        forward, backward = theta.copy(), theta.copy()
        forward[k] += step
        backward[k] -= step
        numeric = (model(forward).frequencies - model(backward).frequencies) / (2.0 * step)
        np.testing.assert_allclose(converted[:, k], numeric, rtol=1e-6)


def test_mode_shape_sensitivity_matches_central_differences(model: ScalingModel) -> None:
    """AC-UPD-002: Fox-Kapoor eigenvector derivatives against finite differences."""
    basis = chain_model(num_modes=N_DOF)  # full basis: no truncation error
    theta = np.array([1.03, 0.94, 1.08, 0.99])
    eigenvalues, shapes = basis.eigen(theta)
    dK, dM = basis.derivatives()
    analytic = mode_shape_sensitivity(shapes, eigenvalues, dK, dM, modes=range(4))

    step = 1.0e-6
    for k in range(theta.size):
        forward, backward = theta.copy(), theta.copy()
        forward[k] += step
        backward[k] -= step
        numeric = (basis.eigen(forward)[1] - basis.eigen(backward)[1]) / (2.0 * step)
        np.testing.assert_allclose(analytic[k], numeric[:, :4], atol=1e-6, rtol=1e-4)


def test_truncated_mode_shape_sensitivity_is_the_projection_of_the_exact_one() -> None:
    """Truncating the superposition basis drops exactly the omitted modal terms.

    So the truncated derivative is the mass-orthogonal projection of the exact
    one onto the retained subspace — the modelling error is quantified, not
    just "small".
    """
    theta = np.array([1.04, 0.93, 1.09, 0.98])
    full = chain_model(num_modes=N_DOF)
    eigenvalues, shapes = full.eigen(theta)
    mass = full.assemble(theta)[1]
    dK, dM = full.derivatives()

    exact = mode_shape_sensitivity(shapes, eigenvalues, dK, dM, modes=[0])
    kept = shapes[:, :4]
    truncated = mode_shape_sensitivity(kept, eigenvalues[:4], dK, dM, modes=[0])

    for k in range(theta.size):
        projected = kept @ (kept.T @ (mass @ exact[k, :, 0]))
        np.testing.assert_allclose(truncated[k, :, 0], projected, atol=1e-12)


def test_mode_shape_sensitivity_warns_on_a_degenerate_cluster() -> None:
    """Repeated eigenvalues have no individually differentiable eigenvectors."""
    K = np.diag([1.0e6, 1.0e6, 4.0e6])
    M = np.eye(3)
    shapes = np.eye(3)
    eigenvalues = np.array([1.0e6, 1.0e6, 4.0e6])
    with pytest.warns(RuntimeWarning, match="degenerate"):
        mode_shape_sensitivity(shapes, eigenvalues, [K], [M], modes=[0])


def test_mac_sensitivity_matches_central_differences() -> None:
    basis = chain_model(num_modes=N_DOF)
    theta = np.array([1.02, 0.96, 1.07, 1.01])
    reference = basis.eigen(np.ones(4))[1][:, :4]

    analytic = basis.mac_sensitivity(theta, reference)

    step = 1.0e-6
    numeric = np.empty_like(analytic)
    for k in range(theta.size):
        forward, backward = theta.copy(), theta.copy()
        forward[k] += step
        backward[k] -= step
        plus = basis.eigen(forward)[1]
        minus = basis.eigen(backward)[1]
        for i in range(analytic.shape[0]):
            numeric[i, k] = (
                mac_value(reference[:, i], plus[:, i]) - mac_value(reference[:, i], minus[:, i])
            ) / (2.0 * step)
    np.testing.assert_allclose(analytic, numeric, atol=1e-6)


def test_modal_sensitivity_finite_differences_agree_with_the_analytical_matrix(
    model: ScalingModel,
) -> None:
    theta = np.array([1.10, 0.90, 1.05, 1.00])
    result = modal_sensitivity(model, theta, parameter_names=model.parameter_names, steps=1e-6)
    np.testing.assert_allclose(
        result.matrix, model.frequency_sensitivity(theta), rtol=1e-5, atol=1e-8
    )
    assert result.parameter_names == model.parameter_names
    assert result.shape == (model.num_modes, theta.size)
    assert "k0" in result.table()
    assert np.isfinite(result.relative()).all()


def test_track_modes_follows_a_reordered_mode_set(model: ScalingModel) -> None:
    data = model(np.ones(4))
    shuffled = data.select([2, 0, 3, 1, 4, 5])
    np.testing.assert_array_equal(track_modes(data, shuffled), [1, 3, 0, 2, 4, 5])


# ------------------------------------------------------------------- updating


def test_updating_recovers_perturbed_stiffness_parameters(model: ScalingModel) -> None:
    """Twin experiment: the updater must find the parameters that made the data."""
    truth = {"k0": 0.80, "k1": 1.25, "k2": 0.95, "k3": 1.10}
    target = model(truth)
    parameters = parameter_set(model.parameter_names)

    before = correlation_of(target, model(parameters.as_dict()))
    assert before[0] > 3.0  # the detuned model really is off

    result = update_model(
        model,
        parameters,
        target.frequencies,
        target.mode_shapes,
        sensitivity_function=model.sensitivity_function(parameters.free_names),
        shape_weight=0.0,
    )

    assert result.converged
    after = correlation_of(target, result.modal_data)
    assert after[0] < 1.0e-3
    assert after[1] > 1.0 - 1.0e-9
    for name, value in truth.items():
        assert result.parameters[name] == pytest.approx(value, abs=1.0e-4)


def test_updating_recovers_mixed_stiffness_and_mass_parameters() -> None:
    """Anchoring one mass makes the mixed K/M parameterisation identifiable."""
    massy = chain_model(n_stiffness_groups=3, n_mass_groups=2)
    truth = {"k0": 1.20, "k1": 0.85, "k2": 1.05, "m0": 1.15, "m1": 1.00}
    target = massy(truth)
    parameters = ParameterSet(
        [
            UpdatableParameter(name, 1.0, 0.5, 2.0, fixed=(name == "m1"))
            for name in massy.parameter_names
        ]
    )

    result = update_model(
        massy,
        parameters,
        target.frequencies,
        target.mode_shapes,
        sensitivity_function=massy.sensitivity_function(parameters.free_names),
        shape_weight=0.0,
    )

    assert result.converged
    for name, value in truth.items():
        assert result.parameters[name] == pytest.approx(value, abs=1.0e-3)


def test_all_stiffness_and_mass_free_is_identifiable_only_up_to_a_common_factor() -> None:
    """Eigenvalues only see K/M, so a uniform rescaling is a null direction.

    Every group's stiffness *and* mass being free leaves a one-parameter family
    of exact fits.  The updater must still reach a perfect fit and land on that
    family rather than wander off it.
    """
    massy = chain_model(n_stiffness_groups=3, n_mass_groups=2)
    truth = {"k0": 1.20, "k1": 0.85, "k2": 1.05, "m0": 1.15, "m1": 0.90}
    target = massy(truth)
    parameters = parameter_set(massy.parameter_names)

    result = update_model(massy, parameters, target.frequencies, shape_weight=0.0)

    assert result.final_cost < 1.0e-20
    ratios = np.array(
        [result.parameters[name] / truth[name] for name in massy.parameter_names]
    )
    np.testing.assert_allclose(ratios, ratios[0], rtol=1e-9)


def test_updating_improves_correlation_from_sensor_dofs_only() -> None:
    """Only five DOFs are instrumented, and the MAC residual is active."""
    sensors = np.arange(0, N_DOF, 2)
    measured = chain_model(dof_selection=sensors)
    truth = {"k0": 0.85, "k1": 1.20, "k2": 1.10, "k3": 0.92}
    target = measured(truth)
    parameters = parameter_set(measured.parameter_names)

    before = correlation_of(target, measured(parameters.as_dict()))
    result = update_model(
        measured,
        parameters,
        target.frequencies,
        target.mode_shapes,
        shape_weight=1.0,
    )
    after = correlation_of(target, result.modal_data)

    assert after[0] < before[0] / 100.0
    assert after[1] >= before[1]
    assert result.final_cost < result.initial_cost * 1.0e-6


def test_updating_improves_a_noisy_target_without_overfitting(model: ScalingModel) -> None:
    """With measurement noise the residual cannot vanish, but it must shrink."""
    truth = {"k0": 0.88, "k1": 1.18, "k2": 0.96, "k3": 1.06}
    target = model(truth)
    rng = np.random.default_rng(20260826)
    noisy = target.frequencies * (1.0 + 0.005 * rng.standard_normal(target.n_modes))
    parameters = parameter_set(model.parameter_names)

    result = update_model(model, parameters, noisy, shape_weight=0.0)

    assert result.cost_reduction > 0.9
    recovered = np.array([result.parameters[name] for name in model.parameter_names])
    expected = np.array([truth[name] for name in model.parameter_names])
    assert np.abs(recovered - expected).max() < 0.05


def test_finite_difference_and_analytical_jacobians_reach_the_same_optimum(
    model: ScalingModel,
) -> None:
    truth = {"k0": 0.90, "k1": 1.15, "k2": 1.02, "k3": 0.95}
    target = model(truth)

    finite = update_model(model, parameter_set(model.parameter_names), target.frequencies)
    names = model.parameter_names
    analytic = update_model(
        model,
        parameter_set(names),
        target.frequencies,
        sensitivity_function=model.sensitivity_function(names),
    )

    for name in names:
        assert finite.parameters[name] == pytest.approx(analytic.parameters[name], abs=1.0e-6)


# --------------------------------------------------- analytic MAC-row Jacobian


def small_twin() -> tuple[ScalingModel, ModalData, ParameterSet]:
    """Six-DOF, two-group chain measured at three sensors.

    ``num_modes`` covers every DOF, so the modal superposition behind the
    eigenvector derivatives is complete and the Fox & Kapoor MAC derivative is
    exact rather than truncated.
    """
    twin = chain_model(
        n_dof=6, n_stiffness_groups=2, num_modes=6, dof_selection=np.array([1, 3, 5])
    )
    return twin, twin({"k0": 0.85, "k1": 1.20}), parameter_set(["k0", "k1"])


def linearization_point(updater: ModelUpdater) -> tuple[np.ndarray, list, np.ndarray, ModalData]:
    """The ``jacobian`` arguments at the updater's starting point."""
    x = updater.parameters.design_values()
    data = updater.evaluate(x)
    pairs = updater.pair(data)
    return x, pairs, updater.residual(data, pairs), data


def test_analytic_mac_rows_match_finite_differences_on_a_small_twin() -> None:
    """Both blocks of ``dr/dx`` — relative frequency and ``1 - sqrt(MAC)``."""
    twin, target, parameters = small_twin()
    names = parameters.free_names
    numeric = ModelUpdater(
        twin, parameters, target.frequencies, target.mode_shapes, shape_weight=1.0
    )
    analytic = ModelUpdater(
        twin,
        parameters,
        target.frequencies,
        target.mode_shapes,
        shape_weight=1.0,
        sensitivity_function=twin.sensitivity_function(names),
        shape_sensitivity_function=twin.shape_sensitivity_function(names),
    )

    x, pairs, residual, data = linearization_point(numeric)
    finite = numeric.jacobian(x, pairs, residual, data)
    exact = analytic.jacobian(x, pairs, residual, data)

    assert finite.shape == (2 * len(pairs), len(names))
    mac_block = slice(len(pairs), None)
    assert np.abs(finite[mac_block]).max() > 1.0e-3  # the MAC rows are not trivially zero
    np.testing.assert_allclose(exact, finite, rtol=1.0e-5, atol=1.0e-9)


def test_the_analytic_mac_jacobian_never_perturbs_the_model() -> None:
    """The whole residual is differentiated in closed form: no extra evaluations."""
    twin, target, parameters = small_twin()
    names = parameters.free_names
    updater = ModelUpdater(
        twin,
        parameters,
        target.frequencies,
        target.mode_shapes,
        shape_weight=1.0,
        sensitivity_function=twin.sensitivity_function(names),
        shape_sensitivity_function=twin.shape_sensitivity_function(names),
    )

    x, pairs, residual, data = linearization_point(updater)
    before = updater.n_evaluations
    updater.jacobian(x, pairs, residual, data)

    assert updater.n_evaluations == before


def test_the_difference_shape_residual_still_falls_back_to_finite_differences() -> None:
    """Only ``1 - sqrt(MAC)`` has a Fox & Kapoor derivative here."""
    twin, target, parameters = small_twin()
    names = parameters.free_names
    updater = ModelUpdater(
        twin,
        parameters,
        target.frequencies,
        target.mode_shapes,
        shape_weight=1.0,
        shape_residual="difference",
        sensitivity_function=twin.sensitivity_function(names),
        shape_sensitivity_function=twin.shape_sensitivity_function(names),
    )

    x, pairs, residual, data = linearization_point(updater)
    before = updater.n_evaluations
    updater.jacobian(x, pairs, residual, data)

    assert updater.n_evaluations == before + 2 * len(names)


def test_the_analytic_and_finite_difference_mac_paths_reach_the_same_optimum() -> None:
    """Same recovered twin, fewer model evaluations."""
    twin, target, parameters = small_twin()
    names = parameters.free_names
    common = dict(shape_weight=1.0, max_iterations=20)

    numeric = ModelUpdater(twin, parameters, target.frequencies, target.mode_shapes, **common)
    analytic = ModelUpdater(
        twin,
        parameters,
        target.frequencies,
        target.mode_shapes,
        sensitivity_function=twin.sensitivity_function(names),
        shape_sensitivity_function=twin.shape_sensitivity_function(names),
        **common,
    )
    finite_result = numeric.run()
    analytic_result = analytic.run()

    assert analytic_result.converged, analytic_result.message
    for name, value in {"k0": 0.85, "k1": 1.20}.items():
        assert analytic_result.parameters[name] == pytest.approx(value, abs=1.0e-6)
        assert analytic_result.parameters[name] == pytest.approx(
            finite_result.parameters[name], abs=1.0e-6
        )
    assert analytic.n_evaluations < numeric.n_evaluations


def test_gauss_newton_and_levenberg_marquardt_agree(model: ScalingModel) -> None:
    truth = {"k0": 0.93, "k1": 1.12, "k2": 0.98, "k3": 1.04}
    target = model(truth)
    common = dict(shape_weight=0.0)

    gn = update_model(model, parameter_set(model.parameter_names), target.frequencies,
                      method="gauss-newton", **common)
    lm = update_model(model, parameter_set(model.parameter_names), target.frequencies,
                      method="levenberg-marquardt", **common)

    for name in model.parameter_names:
        assert gn.parameters[name] == pytest.approx(truth[name], abs=1.0e-3)
        assert lm.parameters[name] == pytest.approx(truth[name], abs=1.0e-3)


def test_log_scaled_parameters_recover_the_truth(model: ScalingModel) -> None:
    """Design space is log(θ), so the physical factors stay positive by construction."""
    truth = {"k0": 0.75, "k1": 1.30, "k2": 1.00, "k3": 0.90}
    target = model(truth)
    parameters = ParameterSet(
        [
            UpdatableParameter(name, 1.0, 0.2, 5.0, log_scaled=True)
            for name in model.parameter_names
        ]
    )

    result = update_model(model, parameters, target.frequencies, target.mode_shapes,
                          shape_weight=0.0)

    assert result.converged
    for name, value in truth.items():
        assert result.parameters[name] == pytest.approx(value, abs=1.0e-3)


def test_fixed_parameters_are_not_touched(model: ScalingModel) -> None:
    truth = {"k0": 0.85, "k1": 1.20, "k2": 1.00, "k3": 1.00}
    target = model(truth)
    parameters = ParameterSet(
        [
            UpdatableParameter("k0", 1.0, 0.5, 2.0),
            UpdatableParameter("k1", 1.0, 0.5, 2.0),
            UpdatableParameter("k2", 1.0, 0.5, 2.0, fixed=True),
            UpdatableParameter("k3", 1.0, 0.5, 2.0, fixed=True),
        ]
    )

    result = update_model(model, parameters, target.frequencies, shape_weight=0.0)

    assert result.parameters["k2"] == 1.0
    assert result.parameters["k3"] == 1.0
    assert result.parameters["k0"] == pytest.approx(0.85, abs=5.0e-3)


def test_underdetermined_updating_stays_bounded_and_monotone() -> None:
    """AC-UPD-005: fewer residuals than parameters must not blow the iterates up."""
    sparse_data = chain_model(n_stiffness_groups=6, num_modes=2)
    truth = dict(
        zip(
            sparse_data.parameter_names,
            [0.85, 1.15, 0.95, 1.10, 0.90, 1.05],
            strict=False,
        )
    )
    target = sparse_data(truth)
    parameters = parameter_set(sparse_data.parameter_names, lower=0.6, upper=1.6)

    result = update_model(
        sparse_data,
        parameters,
        target.frequencies,
        shape_weight=0.0,
        regularization=1.0e-3,
    )

    values = np.array(list(result.parameters.values()))
    assert np.all((values >= 0.6 - 1e-12) & (values <= 1.6 + 1e-12))
    costs = [record.cost for record in result.history if record.accepted]
    assert costs == sorted(costs, reverse=True)
    assert result.final_cost <= result.initial_cost


def test_collinear_parameters_still_converge() -> None:
    """AC-UPD-007: a duplicated parameter is redundant, not fatal."""
    mask = group_masks(N_DOF, 2)
    parts = {
        "k_left": chain_stiffness(BASE_STIFFNESS * mask[0]),
        "k_right_a": chain_stiffness(0.5 * BASE_STIFFNESS * mask[1]),
        "k_right_b": chain_stiffness(0.5 * BASE_STIFFNESS * mask[1]),
    }
    collinear = ScalingModel(
        parts, base_mass=np.eye(N_DOF) * BASE_MASS, num_modes=4, use_solver=False
    )
    target = collinear({"k_left": 0.85, "k_right_a": 1.20, "k_right_b": 1.20})
    parameters = parameter_set(collinear.parameter_names)

    result = update_model(
        collinear, parameters, target.frequencies, shape_weight=0.0, regularization=1.0e-6
    )

    assert result.final_cost < result.initial_cost * 1.0e-4
    assert result.parameters["k_left"] == pytest.approx(0.85, abs=1.0e-3)
    # Only the sum of the two collinear factors is observable.
    assert result.parameters["k_right_a"] + result.parameters["k_right_b"] == pytest.approx(
        2.40, abs=1.0e-3
    )


def test_updater_repairs_modes_when_the_order_switches() -> None:
    """Mode switching during updating must not scramble the residual ordering."""
    switching = chain_model(n_stiffness_groups=2, num_modes=4)
    target = switching({"k0": 1.60, "k1": 0.60})
    parameters = parameter_set(switching.parameter_names, lower=0.4, upper=2.0)

    updater = ModelUpdater(
        switching,
        parameters,
        target.frequencies,
        target.mode_shapes,
        shape_weight=0.0,
    )
    result = updater.run()

    assert result.final_correlation.min_mac > 0.99
    assert result.parameters["k0"] == pytest.approx(1.60, abs=1.0e-3)
    assert updater.n_evaluations > 0


def test_updating_reports_a_readable_history(model: ScalingModel) -> None:
    target = model({"k0": 0.9, "k1": 1.1, "k2": 1.0, "k3": 1.0})
    result = update_model(model, parameter_set(model.parameter_names), target.frequencies,
                          shape_weight=0.0)

    assert result.history
    assert all(record.iteration > 0 for record in result.history)
    assert result.sensitivity is not None
    assert result.sensitivity.shape[1] == 4
    text = result.report()
    assert "converged" in text and "k0" in text


# ------------------------------------------------------------ error handling


def test_updater_rejects_unknown_options(model: ScalingModel) -> None:
    with pytest.raises(TypeError, match="unknown updating option"):
        ModelUpdater(model, parameter_set(model.parameter_names), [1.0], nonsense=1)


def test_updater_rejects_an_all_fixed_parameter_set(model: ScalingModel) -> None:
    parameters = ParameterSet(
        [UpdatableParameter(name, 1.0, 0.5, 2.0, fixed=True) for name in model.parameter_names]
    )
    with pytest.raises(ValueError, match="all parameters are fixed"):
        ModelUpdater(model, parameters, [1.0])


def test_scaling_model_rejects_missing_parameter_values(model: ScalingModel) -> None:
    with pytest.raises(KeyError, match="missing values"):
        model({"k0": 1.0})


def test_scaling_model_needs_at_least_one_contribution() -> None:
    with pytest.raises(ValueError, match="at least one parameterised contribution"):
        ScalingModel({}, {})


def test_parameter_declaration_converts_to_a_design_variable() -> None:
    declared = Parameter(
        "E.steel", "material.1.E", reference=2.1e11, lower=0.8, upper=1.25,
        element_ids=(1, 2), kind=ParameterType.STIFFNESS,
    )
    assert declared.normalize(2.1e11) == pytest.approx(1.0)
    assert declared.denormalize(1.1) == pytest.approx(2.31e11)

    variable = declared.to_updatable()
    assert variable.name == "E.steel"
    assert variable.targets == (1, 2)
    assert variable.design_bounds == (0.8, 1.25)
    assert variable.clip(2.0) == 1.25


# ----------------------------------------------------- internal solver wiring


def test_scaling_model_matches_the_internal_modal_solver() -> None:
    """ScalingModel must give the same modes through ModalSolver and the fallback."""
    pytest.importorskip(
        "openfemlab.solver.modal", reason="internal solver stack not importable yet"
    )
    theta = np.array([1.05, 0.95, 1.10, 0.90])
    fallback = chain_model()
    through_solver = chain_model()
    through_solver.use_solver = True

    reference = fallback(theta)
    solved = through_solver(theta)

    np.testing.assert_allclose(solved.frequencies, reference.frequencies, rtol=1e-9)
    for i in range(reference.n_modes):
        assert mac_value(reference.mode_shapes[:, i], solved.mode_shapes[:, i]) > 1.0 - 1e-9


# ---------------------------------------------------------------------------
# Callable-model cases (reconciled from the R1-O2 updating branch)
#
# Everything above drives the affine ``ScalingModel``.  A real updating run
# usually wraps an external solver in a plain ``{name: value} -> modal data``
# callable instead, so the cases below exercise that entry point, the parameter
# bookkeeping behind it, and the residual/regularisation options it exposes.
# ---------------------------------------------------------------------------

TWO_PI = 2.0 * np.pi


def two_dof_problem(truth=(1.25, 0.80), n_modes=2):
    """2-DOF chain: synthetic test data generated from a perturbed truth model."""
    chain = two_dof_chain()
    model = make_model_function(
        chain, n_modes=n_modes, stiffness_groups={"k1": [0], "k2": [1]}
    )
    target = model({"k1": truth[0], "k2": truth[1]})
    parameters = [
        UpdatableParameter("k1", value=1.0, lower=0.4, upper=2.5),
        UpdatableParameter("k2", value=1.0, lower=0.4, upper=2.5),
    ]
    return chain, model, target, parameters


# ------------------------------------------------------------ parameter model


def test_parameter_defaults_are_a_unit_scaling_factor() -> None:
    parameter = UpdatableParameter("k_web")

    assert parameter.value == 1.0
    assert parameter.initial == 1.0
    assert parameter.kind is ParameterType.STIFFNESS
    assert parameter.change_pct == 0.0


def test_parameter_clips_to_its_bounds() -> None:
    parameter = UpdatableParameter("k", value=1.0, lower=0.8, upper=1.2)

    assert parameter.set_value(5.0) == 1.2
    assert parameter.set_value(0.0) == 0.8
    assert parameter.change_pct == pytest.approx(-20.0)

    parameter.reset()
    assert parameter.value == 1.0


def test_parameter_rejects_inconsistent_definitions() -> None:
    with pytest.raises(ValueError):
        UpdatableParameter("k", value=3.0, lower=0.5, upper=2.0)
    with pytest.raises(ValueError):
        UpdatableParameter("k", lower=2.0, upper=0.5)
    with pytest.raises(ValueError):
        UpdatableParameter("", value=1.0)
    with pytest.raises(ValueError):
        UpdatableParameter("k", step=0.0)


def test_log_scaled_parameter_round_trips_through_design_space() -> None:
    parameter = UpdatableParameter("m", value=1.4, lower=0.1, upper=10.0, log_scaled=True)

    design = parameter.to_design()

    assert design == pytest.approx(np.log(1.4))
    assert parameter.from_design(design) == pytest.approx(1.4)
    assert parameter.design_bounds == pytest.approx((np.log(0.1), np.log(10.0)))


def test_log_scaled_parameter_needs_a_positive_lower_bound() -> None:
    with pytest.raises(ValueError):
        UpdatableParameter("k", value=1.0, lower=0.0, upper=2.0, log_scaled=True)


def test_parameter_set_indexing_and_bookkeeping() -> None:
    parameters = ParameterSet(
        [
            UpdatableParameter("k1", value=1.1, targets=(1, 2)),
            UpdatableParameter("m1", value=0.9, kind=ParameterType.MASS, fixed=True),
        ]
    )

    assert parameters.names == ["k1", "m1"]
    assert parameters.free_names == ["k1"]
    assert parameters["m1"].kind is ParameterType.MASS
    assert parameters[0].targets == (1, 2)
    assert "k1" in parameters and len(parameters) == 2
    assert parameters.as_dict() == {"k1": 1.1, "m1": 0.9}
    assert [p.name for p in parameters.of_kind("mass")] == ["m1"]
    with pytest.raises(KeyError):
        parameters["nope"]


def test_parameter_set_rejects_duplicate_names() -> None:
    with pytest.raises(ValueError):
        ParameterSet([UpdatableParameter("k"), UpdatableParameter("k")])


def test_design_space_updates_only_touch_free_parameters() -> None:
    parameters = ParameterSet(
        [
            UpdatableParameter("k1", value=1.0, lower=0.5, upper=1.5),
            UpdatableParameter("k2", value=1.0, fixed=True),
        ]
    )

    assert parameters.design_values() == pytest.approx([1.0])

    values = parameters.apply_design([9.0])  # clipped to the upper bound

    assert values == {"k1": 1.5, "k2": 1.0}
    assert parameters.copy().as_dict() == values
    assert "k1" in parameters.table()


# ----------------------------------------------------------------- modal data


def test_as_modal_data_accepts_the_common_solver_return_types() -> None:
    frequencies = np.array([1.0, 2.0])
    shapes = np.eye(2)

    class SolverResult:
        natural_frequencies = frequencies
        eigenvectors = shapes

    assert as_modal_data(ModalData(frequencies, shapes)).n_modes == 2
    assert as_modal_data((frequencies, shapes)).mode_shapes.shape == (2, 2)
    assert as_modal_data({"frequencies": frequencies}).n_modes == 2
    assert as_modal_data([1.0, 2.0, 3.0]).n_modes == 3
    assert as_modal_data(SolverResult()).mode_shapes.shape == (2, 2)
    with pytest.raises(TypeError):
        as_modal_data(object())


def test_modal_data_eigenvalues_follow_the_frequencies() -> None:
    data = ModalData(np.array([1.0, 4.0]))

    assert data.eigenvalues == pytest.approx((TWO_PI * np.array([1.0, 4.0])) ** 2)


def test_modal_data_rejects_a_mismatched_shape_matrix() -> None:
    with pytest.raises(ValueError):
        ModalData(np.array([1.0, 2.0]), np.ones((4, 3)))


# ---------------------------------------------------------------- sensitivity


def test_eigenvalue_sensitivity_needs_the_mass_matrix_for_unnormalized_modes() -> None:
    chain = two_dof_chain()
    modes = chain.modes()
    _, mass = chain.matrices()
    rescaled = modes.mode_shapes * np.array([3.0, -2.0])

    reference = eigenvalue_sensitivity(
        modes.mode_shapes, modes.eigenvalues, chain.spring_matrices()
    )
    with_mass = eigenvalue_sensitivity(
        rescaled, modes.eigenvalues, chain.spring_matrices(), mass_matrix=mass
    )

    assert with_mass == pytest.approx(reference, rel=1e-10)


def test_frequency_sensitivity_matches_a_direct_finite_difference() -> None:
    chain = two_dof_chain()
    modes = chain.modes()
    analytical = eigenvalue_to_frequency_sensitivity(
        eigenvalue_sensitivity(modes.mode_shapes, modes.eigenvalues, chain.spring_matrices()),
        modes.frequencies,
    )

    numerical = modal_sensitivity(
        lambda scales: chain.modes(stiffness_scales=scales),
        np.ones(2),
        parameter_names=["k1", "k2"],
        steps=1e-6,
    )

    assert analytical == pytest.approx(numerical.matrix, rel=1e-6)
    assert numerical.response_labels == ["f1", "f2"]


def test_relative_frequency_sensitivity_of_a_uniform_stiffness_scaling_is_one_half() -> None:
    chain = uniform_chain(4)

    sensitivity = modal_sensitivity(
        lambda scale: chain.modes(stiffness_scales=np.full(4, scale[0])),
        [1.0],
        parameter_names=["k"],
        steps=1e-6,
    )

    # f ~ sqrt(k), so d(ln f)/d(ln k) = 1/2 for every mode.
    assert sensitivity.relative().ravel() == pytest.approx(np.full(4, 0.5), rel=1e-5)
    assert relative_sensitivity(
        sensitivity.matrix, [1.0], sensitivity.response_values
    ) == pytest.approx(sensitivity.relative())


def test_modal_sensitivity_tracks_modes_across_a_reordering_solver() -> None:
    chain = SpringMassChain(masses=[1.0, 1.0], stiffnesses=[1000.0, 1000.0])

    def response(scale):
        data = chain.modes(stiffness_scales=[scale[0], 1.0])
        # Hand the output back reversed to emulate a solver that does not
        # preserve the mode ordering between calls.
        return ModalData(data.frequencies[::-1], data.mode_shapes[:, ::-1])

    sensitivity = modal_sensitivity(response, [1.0], steps=1e-5)

    assert sensitivity.matrix.shape == (2, 1)
    assert np.all(sensitivity.matrix > 0.0)


def test_finite_difference_schemes_agree_on_a_smooth_response() -> None:
    chain = two_dof_chain()

    def frequencies(scales):
        return chain.modes(stiffness_scales=scales).frequencies

    central = finite_difference_jacobian(frequencies, np.ones(2), steps=1e-6)
    forward = finite_difference_jacobian(frequencies, np.ones(2), steps=1e-7, scheme="forward")

    assert central == pytest.approx(forward, rel=1e-4)
    with pytest.raises(ValueError):
        finite_difference_jacobian(frequencies, np.ones(2), scheme="banana")


# ------------------------------------------------------- callable-model runs


def test_updating_recovers_the_perturbed_stiffness_of_a_two_dof_model() -> None:
    _, model, target, parameters = two_dof_problem(truth=(1.25, 0.80))

    result = ModelUpdater(model, parameters, target.frequencies, target.mode_shapes).run()

    assert result.converged
    assert result.parameters["k1"] == pytest.approx(1.25, rel=1e-4)
    assert result.parameters["k2"] == pytest.approx(0.80, rel=1e-4)
    assert result.final_correlation.max_abs_freq_error_pct < 1e-3
    assert result.final_correlation.mean_mac > 0.9999
    assert result.final_cost < 1e-12


def test_updating_improves_both_the_mac_and_the_frequency_error() -> None:
    chain = uniform_chain(6)
    model = make_model_function(
        chain,
        n_modes=4,
        stiffness_groups={"k_lower": [0, 1, 2], "k_upper": [3, 4, 5]},
        mass_groups={"m_tip": [5]},
    )
    truth = {"k_lower": 1.30, "k_upper": 0.75, "m_tip": 1.20}
    target = model(truth)
    nominal = model({"k_lower": 1.0, "k_upper": 1.0, "m_tip": 1.0})
    parameters = [
        UpdatableParameter("k_lower", lower=0.5, upper=2.0),
        UpdatableParameter("k_upper", lower=0.5, upper=2.0),
        UpdatableParameter("m_tip", lower=0.5, upper=2.0, kind=ParameterType.MASS),
    ]

    before = correlate(
        target.frequencies, nominal.frequencies, target.mode_shapes, nominal.mode_shapes
    )
    result = update_model(model, parameters, target.frequencies, target.mode_shapes)

    assert before.mean_mac < 0.99
    assert before.max_abs_freq_error_pct > 5.0
    assert result.final_correlation.mean_mac > before.mean_mac
    assert result.final_correlation.min_mac > 0.999
    assert result.final_correlation.max_abs_freq_error_pct < 0.01
    for name, value in truth.items():
        assert result.parameters[name] == pytest.approx(value, rel=1e-3)


def test_updating_with_a_measured_dof_subset_and_noisy_targets() -> None:
    chain = uniform_chain(8)
    model = make_model_function(
        chain,
        n_modes=3,
        stiffness_groups={"k_root": [0, 1], "k_mid": [2, 3, 4], "k_tip": [5, 6, 7]},
        dofs=[1, 3, 5, 7],
    )
    truth = {"k_root": 1.20, "k_mid": 0.85, "k_tip": 1.10}
    clean = model(truth)

    rng = np.random.default_rng(11)
    noisy = ModalData(
        clean.frequencies * (1.0 + 0.002 * rng.standard_normal(clean.frequencies.size)),
        clean.mode_shapes + 0.01 * rng.standard_normal(clean.mode_shapes.shape),
    )
    parameters = [
        UpdatableParameter(name, lower=0.5, upper=2.0, log_scaled=True) for name in truth
    ]

    result = update_model(model, parameters, noisy.frequencies, noisy.mode_shapes)

    assert result.cost_reduction > 0.9
    assert result.final_correlation.max_abs_freq_error_pct < 0.5
    for name, value in truth.items():
        assert result.parameters[name] == pytest.approx(value, rel=0.05)


def test_frequency_only_updating_works_without_measured_mode_shapes() -> None:
    _, model, target, parameters = two_dof_problem(truth=(1.15, 0.90))

    result = update_model(model, parameters, target.frequencies, shape_weight=0.0)

    assert result.parameters["k1"] == pytest.approx(1.15, rel=1e-4)
    assert result.parameters["k2"] == pytest.approx(0.90, rel=1e-4)
    assert result.final_correlation.max_abs_freq_error_pct < 1e-3


def test_the_shape_difference_residual_also_converges() -> None:
    """``shape_residual="difference"`` drives MSF-scaled per-DOF differences."""
    _, model, target, parameters = two_dof_problem(truth=(1.10, 0.95))

    result = update_model(
        model,
        parameters,
        target.frequencies,
        target.mode_shapes,
        shape_residual="difference",
    )

    assert result.parameters["k1"] == pytest.approx(1.10, rel=1e-3)
    assert result.final_correlation.min_mac > 0.9999


def test_regularization_pulls_the_solution_towards_the_initial_model() -> None:
    """Also guards the parameter isolation the Tikhonov term depends on.

    Both runs are handed the same parameter objects, so an updater that wrote
    its solution back into them would silently make ``x0`` the first run's
    answer and the regularisation a no-op.
    """
    _, model, target, parameters = two_dof_problem(truth=(1.40, 0.70))

    free = update_model(model, parameters, target.frequencies, target.mode_shapes)
    regularized = update_model(
        model, parameters, target.frequencies, target.mode_shapes, regularization=1.0
    )

    def distance(result):
        return sum(abs(value - 1.0) for value in result.parameters.values())

    assert distance(regularized) < distance(free)


def test_the_updater_leaves_the_callers_parameter_objects_untouched() -> None:
    _, model, target, parameters = two_dof_problem(truth=(1.30, 0.75))

    first = update_model(model, parameters, target.frequencies, target.mode_shapes)

    assert [p.value for p in parameters] == [1.0, 1.0]

    second = update_model(model, parameters, target.frequencies, target.mode_shapes)

    assert second.parameters == first.parameters
    assert second.initial_cost == pytest.approx(first.initial_cost)


def test_parameter_bounds_are_never_violated() -> None:
    _, model, target, _ = two_dof_problem(truth=(1.60, 0.60))
    tight = [
        UpdatableParameter("k1", value=1.0, lower=0.95, upper=1.05),
        UpdatableParameter("k2", value=1.0, lower=0.95, upper=1.05),
    ]

    result = update_model(model, tight, target.frequencies, target.mode_shapes)

    assert 0.95 <= result.parameters["k1"] <= 1.05
    assert 0.95 <= result.parameters["k2"] <= 1.05
    # Even a run that cannot reach the truth must not make the fit worse.
    assert result.final_cost <= result.initial_cost


def test_hungarian_mode_pairing_updates_as_well_as_the_greedy_pass() -> None:
    """``mode_pairing="optimal"`` re-pairs globally instead of greedily."""
    _, model, target, parameters = two_dof_problem(truth=(1.35, 0.72))

    greedy = update_model(model, parameters, target.frequencies, target.mode_shapes)
    optimal = update_model(
        model, parameters, target.frequencies, target.mode_shapes, mode_pairing="optimal"
    )

    assert optimal.parameters["k1"] == pytest.approx(greedy.parameters["k1"], rel=1e-6)
    assert optimal.final_correlation.min_mac > 0.9999
    with pytest.raises(ValueError, match="unknown mode pairing strategy"):
        update_model(model, parameters, target.frequencies, mode_pairing="clairvoyant")


def test_history_records_a_monotonically_improving_cost() -> None:
    _, model, target, parameters = two_dof_problem(truth=(1.35, 0.78))

    result = update_model(model, parameters, target.frequencies, target.mode_shapes)

    costs = [record.cost for record in result.history]
    assert costs == sorted(costs, reverse=True)
    assert result.history[-1].mean_mac >= result.history[0].mean_mac
    assert result.history[-1].parameters == result.parameters
    assert result.sensitivity is not None
    assert result.sensitivity.matrix.shape[1] == 2


def test_updater_rejects_an_unknown_method() -> None:
    _, model, target, parameters = two_dof_problem()

    with pytest.raises(ValueError, match="unknown updating method"):
        ModelUpdater(model, parameters, target.frequencies, method="newton")


def test_the_analytical_sensitivity_path_uses_fewer_model_evaluations() -> None:
    chain = two_dof_chain()
    _, model, target, parameters = two_dof_problem(truth=(1.20, 0.85))

    def analytical(values, data):
        modes = chain.modes(stiffness_scales=np.array([values["k1"], values["k2"]]))
        return eigenvalue_to_frequency_sensitivity(
            eigenvalue_sensitivity(modes.mode_shapes, modes.eigenvalues, chain.spring_matrices()),
            modes.frequencies,
        )

    finite = ModelUpdater(model, parameters, target.frequencies, shape_weight=0.0)
    by_differences = finite.run()
    exact = ModelUpdater(
        model,
        parameters,
        target.frequencies,
        shape_weight=0.0,
        sensitivity_function=analytical,
    )
    by_fox_kapoor = exact.run()

    assert exact.n_evaluations < finite.n_evaluations
    assert by_fox_kapoor.parameters["k1"] == pytest.approx(
        by_differences.parameters["k1"], rel=1e-6
    )


def test_updating_drives_the_internal_modal_solver_through_a_callable() -> None:
    solver_module = pytest.importorskip("openfemlab.solver.modal")
    chain = uniform_chain(4)

    def model(values):
        K, M = chain.matrices(stiffness_scales=np.full(4, values["k_all"]))
        return solver_module.ModalSolver.from_matrices(K, M).solve(num_modes=3)

    target = model({"k_all": 1.44})

    result = update_model(
        model,
        [UpdatableParameter("k_all", lower=0.5, upper=2.0)],
        target.frequencies,
        target.mode_shapes,
    )

    assert result.parameters["k_all"] == pytest.approx(1.44, rel=1e-4)
