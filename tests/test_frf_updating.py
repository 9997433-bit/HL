"""FRF-domain model updating — MS-3.2/MS-3.3/MS-7.3, gate AC-UPD-009.

The rig is the canonical 2-DOF grounded spring/mass chain
(``tests.modal_reference.two_dof_chain``) wrapped in an affine
:class:`~openfemlab.updating.scaling_model.ScalingModel`, damped by a matrix a
third factor scales. Two stiffness factors and one damping factor against a
handful of frequency lines keeps every quantity small enough to check by hand
while still exercising all three terms of the dynamic stiffness.

What is pinned here rather than in the acceptance suite: the provider's
contracts (shapes, weightings, typed failures), the equivalence of the
synthesized block with a direct dynamic-stiffness inversion, and the plumbing
the FRF updater inherits (design-space chain rule, stop reasons, sigma_post).
The recovery gate itself is AC-UPD-009 in ``tests/acceptance/test_updating.py``.
"""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.solver.dynamics import (
    FrequencyResponse,
    RayleighDamping,
    direct_frf,
)
from openfemlab.updating import (
    FRF_WEIGHTINGS,
    FRFResidual,
    FRFState,
    FRFUpdater,
    FRFUpdatingResult,
    ParameterSet,
    ScalingModel,
    UpdatableParameter,
    posterior_sigma,
    update_model_frf,
)
from tests.modal_reference import two_dof_chain

TRUTH = {"k0": 1.15, "k1": 0.88, "c": 1.20}
NOMINAL = {"k0": 1.0, "k1": 1.0, "c": 1.0}
FREE = ("k0", "k1", "c")

#: The 2-DOF rig resonates near 2.4 Hz and 6.0 Hz; the band brackets both.
LINES = np.linspace(1.0, 8.0, 15)
SENSORS = (0, 1)
DRIVE = (1,)


# --------------------------------------------------------------------- helpers


def chain_model() -> ScalingModel:
    """``K(theta) = theta_k0 K_0 + theta_k1 K_1`` with the masses held fixed."""
    chain = two_dof_chain()
    springs = chain.spring_matrices()
    return ScalingModel(
        {"k0": springs[0], "k1": springs[1]},
        base_mass=np.diag(chain.masses),
        num_modes=2,
        use_solver=False,
    )


def reference_damping(model: ScalingModel) -> np.ndarray:
    """``C_ref = alpha M + beta K`` at 3 % over the nominal band."""
    frequencies = model.modal_data(NOMINAL).frequencies
    rayleigh = RayleighDamping.from_frequencies(frequencies[0], frequencies[-1], 0.03, 0.03)
    K, M = model.assemble(NOMINAL)
    return np.asarray(rayleigh.matrix(np.asarray(K), np.asarray(M)), dtype=float)


def synthesize(
    model: ScalingModel,
    damping: np.ndarray,
    values: dict[str, float],
    frequencies: np.ndarray = LINES,
) -> FrequencyResponse:
    """Reference FRFs straight from the M6 dynamic-stiffness inversion."""
    K, M = model.assemble(values)
    return direct_frf(
        frequencies,
        np.asarray(K),
        np.asarray(M),
        float(values["c"]) * damping,
        response_dofs=SENSORS,
        excitation_dofs=DRIVE,
    )


def parameters(**overrides: object) -> ParameterSet:
    return ParameterSet(
        [UpdatableParameter(name, 1.0, 0.5, 2.0, **overrides) for name in FREE]
    )


@pytest.fixture
def model() -> ScalingModel:
    return chain_model()


@pytest.fixture
def damping(model: ScalingModel) -> np.ndarray:
    return reference_damping(model)


@pytest.fixture
def measured(model: ScalingModel, damping: np.ndarray) -> FrequencyResponse:
    return synthesize(model, damping, TRUTH)


@pytest.fixture
def residual(
    model: ScalingModel, damping: np.ndarray, measured: FrequencyResponse
) -> FRFResidual:
    return FRFResidual(model, measured, damping_parts={"c": damping})


# ------------------------------------------------------- the residual provider


def test_the_provider_reports_the_shape_of_the_stacked_residual(residual):
    assert residual.n_lines == LINES.size
    assert residual.n_channels == len(SENSORS) * len(DRIVE)
    assert residual.n_residuals == 2 * LINES.size * len(SENSORS) * len(DRIVE)
    assert residual.channel_labels == ("dof 0/1", "dof 1/1")


def test_the_synthesized_block_is_the_direct_dynamic_stiffness_inversion(
    residual, model, damping
):
    """The provider's synthesis is the M6 kernel, not a second implementation."""
    expected = synthesize(model, damping, TRUTH)

    produced = residual.transfer(TRUTH)

    np.testing.assert_allclose(produced.data, expected.data, rtol=1e-12, atol=0.0)
    np.testing.assert_array_equal(produced.response_dofs, expected.response_dofs)
    np.testing.assert_array_equal(produced.excitation_dofs, expected.excitation_dofs)
    assert produced.response_type == expected.response_type


def test_the_residual_vanishes_at_the_truth_and_not_at_the_nominal(residual):
    at_truth = residual.residual(residual.state(TRUTH))
    at_nominal = residual.residual(residual.state(NOMINAL))

    assert np.max(np.abs(at_truth)) < 1e-12
    assert np.max(np.abs(at_nominal)) > 0.1


def test_the_state_is_modal_data_the_shared_loop_can_carry(residual):
    state = residual.state(NOMINAL)

    assert isinstance(state, FRFState)
    assert state.n_modes == 0
    assert state.mode_shapes is None
    assert state.values == NOMINAL
    assert state.block.shape == (LINES.size, len(SENSORS), len(DRIVE))
    # The synthesis already solved for the columns the Jacobian needs.
    assert state.columns.shape == (LINES.size, 2, 2)


def test_the_magnitude_weighting_equalizes_the_frequency_lines(residual, model, damping):
    """Relative weighting flattens the 1e2 dynamic range of the raw difference."""
    unit = FRFResidual(
        model, residual.measured, damping_parts={"c": damping}, weighting="unit"
    )
    perturbed = {"k0": 1.02, "k1": 1.0, "c": 1.0}

    weighted = np.abs(residual.residual(residual.state(perturbed)))
    raw = np.abs(unit.residual(unit.state(perturbed)))

    assert set(FRF_WEIGHTINGS) == {"magnitude", "unit"}
    assert np.ptp(weighted) < np.ptp(raw)


def test_the_magnitude_floor_caps_the_antiresonance_amplification(
    model, damping, measured
):
    tight = FRFResidual(
        model, measured, damping_parts={"c": damping}, magnitude_floor=1e-6
    )
    loose = FRFResidual(
        model, measured, damping_parts={"c": damping}, magnitude_floor=1e-1
    )

    assert tight.weights.max() > loose.weights.max()
    assert loose.weights.max() == pytest.approx(1.0 / (1e-1 * np.abs(measured.data).max()))


def test_fitting_a_subset_of_the_lines_shortens_the_residual(model, damping, measured):
    subset = FRFResidual(model, measured, damping_parts={"c": damping}, lines=[0, 2, 4])

    assert subset.n_lines == 3
    np.testing.assert_allclose(subset.frequencies, LINES[[0, 2, 4]])
    assert subset.n_residuals == 2 * 3 * len(SENSORS)


def test_an_accelerance_measurement_is_matched_in_its_own_response_type(
    model, damping, measured
):
    """The residual is formed in whatever quantity the measurement carries."""
    accelerance = measured.converted("accelerance")
    provider = FRFResidual(model, accelerance, damping_parts={"c": damping})

    produced = provider.transfer(TRUTH)

    assert produced.response_type == "accelerance"
    np.testing.assert_allclose(produced.data, accelerance.data, rtol=1e-12)
    assert np.max(np.abs(provider.residual(provider.state(TRUTH)))) < 1e-12


# -------------------------------------------------------------- sensitivities


def central_difference_jacobian(
    provider: FRFResidual, values: dict[str, float], names, step: float = 1e-6
) -> np.ndarray:
    columns = []
    for name in names:
        forward, backward = dict(values), dict(values)
        forward[name] += step
        backward[name] -= step
        columns.append(
            (
                provider.residual(provider.state(forward))
                - provider.residual(provider.state(backward))
            )
            / (2.0 * step)
        )
    return np.column_stack(columns)


@pytest.mark.parametrize("point", ["nominal", "truth"])
def test_the_analytic_jacobian_matches_central_differences(residual, point):
    values = NOMINAL if point == "nominal" else TRUTH
    names = list(FREE)

    analytic = residual.jacobian(values, names, residual.state(values))
    finite = central_difference_jacobian(residual, values, names)

    assert analytic.shape == (residual.n_residuals, len(names))
    assert np.max(np.abs(analytic - finite)) <= 1e-6 * np.max(np.abs(finite))


def test_the_jacobian_needs_no_precomputed_state(residual):
    """Passing the state only saves the factorizations; it changes no number."""
    cached = residual.jacobian(NOMINAL, list(FREE), residual.state(NOMINAL))
    recomputed = residual.jacobian(NOMINAL, list(FREE))

    np.testing.assert_allclose(cached, recomputed, rtol=0.0, atol=0.0)


def test_a_parameter_that_touches_nothing_gets_a_zero_column(model, damping, measured):
    """A name unknown to K, M and C is inert rather than an error."""
    provider = FRFResidual(model, measured, damping_parts={"c": damping})

    jacobian = provider.jacobian(NOMINAL, ["k0", "spectator"])

    assert np.max(np.abs(jacobian[:, 0])) > 0.0
    assert np.all(jacobian[:, 1] == 0.0)


def test_rayleigh_damping_follows_the_stiffness_parameters(model, measured):
    """``dC/dtheta = alpha dM/dtheta + beta dK/dtheta`` for a Rayleigh model."""
    rayleigh = RayleighDamping(alpha=0.5, beta=1e-3)
    provider = FRFResidual(model, measured, damping=rayleigh)

    analytic = provider.jacobian(NOMINAL, ["k0", "k1"])
    finite = central_difference_jacobian(provider, NOMINAL, ["k0", "k1"])

    assert np.max(np.abs(analytic - finite)) <= 1e-6 * np.max(np.abs(finite))
    # Zeroing beta must change the answer, or the damping term is not wired.
    undamped_terms = FRFResidual(model, measured, damping=RayleighDamping(alpha=0.5))
    assert not np.allclose(analytic, undamped_terms.jacobian(NOMINAL, ["k0", "k1"]))


# ------------------------------------------------------------------- updating


def test_the_updater_recovers_the_twin_on_noise_free_frfs(residual):
    updater = FRFUpdater(residual, parameters(), max_iterations=20)

    result = updater.run()

    assert result.converged, result.message
    for name, expected in TRUTH.items():
        assert result.parameters[name] == pytest.approx(expected, abs=1e-6)
    assert result.final_frf_correlation.min_frac > 0.999999


def test_log_scaled_parameters_take_the_design_space_chain_rule(residual):
    """``dr/dx = dr/dp * p`` — the same answer through a different parameterisation."""
    linear = FRFUpdater(residual, parameters(), max_iterations=20).run()
    logarithmic = FRFUpdater(
        residual, parameters(log_scaled=True), max_iterations=20
    ).run()

    for name in FREE:
        assert logarithmic.parameters[name] == pytest.approx(
            linear.parameters[name], abs=1e-6
        )


def test_the_finite_difference_route_reaches_the_same_parameters(residual):
    analytic = FRFUpdater(residual, parameters(), max_iterations=20).run()
    finite = FRFUpdater(
        residual, parameters(), analytic_jacobian=False, max_iterations=20
    ).run()

    for name in FREE:
        assert finite.parameters[name] == pytest.approx(analytic.parameters[name], abs=1e-6)


def test_the_run_reports_through_the_shared_updating_vocabulary(residual):
    result = FRFUpdater(residual, parameters(), max_iterations=20).run()

    assert isinstance(result, FRFUpdatingResult)
    assert result.stop_reason in ("step_tol", "cost_tol", "gradient_tol")
    assert result.accepted_costs == sorted(result.accepted_costs, reverse=True)
    assert result.final_cost < result.initial_cost
    # sigma_post falls back to the least-squares estimate for a deterministic run.
    assert sorted(posterior_sigma(result)) == sorted(FREE)
    assert "FRF correlation" in result.report()


def test_the_modal_correlation_of_an_frf_run_is_empty_rather_than_invented(residual):
    """No mode table was supplied, so the MS-4.2 modal gates report nothing."""
    result = FRFUpdater(residual, parameters(), max_iterations=20).run()

    assert result.initial_correlation.n_paired == 0
    assert result.final_correlation.n_paired == 0
    assert not result.final_correlation.is_correlated()
    # The correlation an FRF run does have is the MS-7.4 block.
    assert result.final_frf_correlation.n_channels == residual.n_channels
    assert result.initial_frf_correlation.min_frac < result.final_frf_correlation.min_frac


def test_the_convenience_wrapper_matches_the_explicit_run(residual):
    explicit = FRFUpdater(residual, parameters(), max_iterations=20).run()
    wrapped = update_model_frf(residual, parameters(), max_iterations=20)

    assert wrapped.parameters == pytest.approx(explicit.parameters)


def test_freezing_a_parameter_leaves_it_out_of_the_jacobian(residual):
    frozen = ParameterSet(
        [
            UpdatableParameter(name, 1.0, 0.5, 2.0, fixed=(name == "c"))
            for name in FREE
        ]
    )

    result = FRFUpdater(residual, frozen, max_iterations=20).run()

    assert result.parameters["c"] == 1.0
    assert result.sensitivity.matrix.shape[1] == 2
    assert result.sensitivity.parameter_names == ["k0", "k1"]


# ------------------------------------------------------------ typed failures


def test_the_provider_rejects_a_measurement_that_is_not_a_frequency_response(model):
    with pytest.raises(TypeError, match="FrequencyResponse"):
        FRFResidual(model, np.zeros((4, 2, 1)))


def test_the_provider_rejects_an_unknown_weighting(model, measured):
    with pytest.raises(ValueError, match="unknown FRF weighting"):
        FRFResidual(model, measured, weighting="decibel")


@pytest.mark.parametrize("floor", [0.0, -1.0, 2.0])
def test_the_provider_rejects_a_magnitude_floor_outside_the_unit_interval(
    model, measured, floor
):
    with pytest.raises(ValueError, match="magnitude_floor"):
        FRFResidual(model, measured, magnitude_floor=floor)


def test_the_provider_rejects_an_empty_or_out_of_range_line_selection(model, measured):
    with pytest.raises(ValueError, match="at least one frequency line"):
        FRFResidual(model, measured, lines=[])
    with pytest.raises(ValueError, match="outside the measured line"):
        FRFResidual(model, measured, lines=[0, LINES.size])


def test_the_provider_rejects_an_identically_zero_measurement(model, measured):
    empty = FrequencyResponse(
        frequencies=measured.frequencies,
        data=np.zeros_like(measured.data),
        response_dofs=measured.response_dofs,
        excitation_dofs=measured.excitation_dofs,
    )
    with pytest.raises(ValueError, match="identically zero"):
        FRFResidual(model, empty)


def test_the_updater_rejects_modal_data_from_a_foreign_model(residual):
    from openfemlab.updating import ModalData

    updater = FRFUpdater(residual, parameters())

    with pytest.raises(TypeError, match="FRFState"):
        updater.residual(ModalData(np.array([1.0])), [(0, 0)])
