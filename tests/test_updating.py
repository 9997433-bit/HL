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

from openfemlab.correlation import mac_value, pair_modes
from openfemlab.updating import (
    ModelUpdater,
    Parameter,
    ParameterSet,
    ParameterType,
    ScalingModel,
    UpdatableParameter,
    eigenvalue_sensitivity,
    eigenvalue_to_frequency_sensitivity,
    modal_sensitivity,
    mode_shape_sensitivity,
    track_modes,
    update_model,
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
