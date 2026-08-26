"""Bayesian (MAP) model updating — MS-3.5, gates AC-UPD-006a/b.

The rig is the canonical 2-DOF grounded spring/mass chain
(``tests.modal_reference.two_dof_chain``) wrapped in an affine
:class:`~openfemlab.updating.scaling_model.ScalingModel`: two stiffness scaling
factors, two measured frequencies, so the estimator is exactly determined and
every quantity the MAP step produces has a hand-checkable counterpart.

The two contract limits are pinned here at the linear-algebra level and again
through a full updating run: an uninformative prior must reproduce the
Gauss-Newton step exactly, and any proper prior must contract the posterior.
"""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.updating import (
    BayesianUpdater,
    BayesianUpdatingResult,
    GaussianPrior,
    ParameterSet,
    PosteriorEstimate,
    ScalingModel,
    UpdatableParameter,
    covariance_matrix,
    map_step,
    posterior_covariance,
    precision_matrix,
    update_model,
    update_model_bayesian,
)
from tests.modal_reference import two_dof_chain

TRUTH = {"k0": 1.15, "k1": 0.88}


# --------------------------------------------------------------------- helpers


def two_dof_model() -> ScalingModel:
    """The 2-DOF chain as ``K(θ) = θ_k0 K_0 + θ_k1 K_1``, mass held fixed."""
    chain = two_dof_chain()
    springs = chain.spring_matrices()
    return ScalingModel(
        {"k0": springs[0], "k1": springs[1]},
        base_mass=np.diag(chain.masses),
        num_modes=2,
        # The matrices are given directly; the dense fallback eigensolver is
        # all this fixture needs and keeps it independent of the FE core.
        use_solver=False,
    )


def parameters(**overrides: object) -> ParameterSet:
    return ParameterSet(
        [UpdatableParameter(name, 1.0, 0.5, 2.0, **overrides) for name in ("k0", "k1")]
    )


def target_frequencies(model: ScalingModel) -> np.ndarray:
    return model.modal_data(TRUTH).frequencies


@pytest.fixture
def model() -> ScalingModel:
    return two_dof_model()


@pytest.fixture
def linearization(model: ScalingModel) -> tuple[np.ndarray, np.ndarray]:
    """``(J, r)`` of the relative-frequency residual at the nominal model."""
    nominal = model.modal_data({"k0": 1.0, "k1": 1.0})
    measured = target_frequencies(model)
    residual = (nominal.frequencies - measured) / measured
    jacobian = model.frequency_sensitivity({"k0": 1.0, "k1": 1.0}) / measured[:, None]
    return jacobian, residual


def gauss_newton_step(jacobian: np.ndarray, residual: np.ndarray) -> np.ndarray:
    return -np.linalg.solve(jacobian.T @ jacobian, jacobian.T @ residual)


# ------------------------------------------------------- covariance plumbing


def test_covariance_expands_scalar_vector_and_matrix() -> None:
    np.testing.assert_allclose(covariance_matrix(4.0, 2, "c"), 4.0 * np.eye(2))
    np.testing.assert_allclose(covariance_matrix([1.0, 9.0], 2, "c"), np.diag([1.0, 9.0]))
    full = np.array([[2.0, 0.5], [0.5, 3.0]])
    np.testing.assert_allclose(covariance_matrix(full, 2, "c"), full)


def test_covariance_of_none_carries_no_information() -> None:
    assert covariance_matrix(None, 3, "c") is None
    assert precision_matrix(None, 3, "c") is None


def test_precision_is_the_inverse_covariance() -> None:
    full = np.array([[2.0, 0.5], [0.5, 3.0]])
    np.testing.assert_allclose(precision_matrix(full, 2, "c") @ full, np.eye(2), atol=1e-14)


@pytest.mark.parametrize(
    "spec",
    [
        -1.0,
        [1.0, -1.0],
        [1.0, 2.0, 3.0],
        np.array([[1.0, 0.5], [0.2, 1.0]]),
        np.array([[1.0, 2.0], [2.0, 1.0]]),
        np.zeros((2, 2, 2)),
    ],
    ids=["negative", "negative-entry", "wrong-size", "asymmetric", "indefinite", "rank-3"],
)
def test_invalid_covariance_specifications_are_rejected(spec: object) -> None:
    with pytest.raises(ValueError):
        covariance_matrix(spec, 2, "c")


def test_uninformative_prior_has_zero_precision_and_infinite_sigma() -> None:
    prior = GaussianPrior.uninformative(["k0", "k1"])
    assert not prior.is_informative
    np.testing.assert_allclose(prior.precision(2), np.zeros((2, 2)))
    assert np.all(np.isinf(prior.std(2)))


def test_prior_from_std_squares_the_standard_deviations() -> None:
    prior = GaussianPrior.from_std([0.1, 0.2])
    np.testing.assert_allclose(prior.matrix(2), np.diag([0.01, 0.04]))
    np.testing.assert_allclose(prior.std(2), [0.1, 0.2])
    with pytest.raises(ValueError):
        GaussianPrior.from_std([0.1, 0.0])


def test_prior_mean_defaults_to_the_starting_point() -> None:
    start = np.array([1.0, 1.0])
    np.testing.assert_allclose(GaussianPrior.from_std(0.1).center(2, start), start)
    anchored = GaussianPrior.from_std(0.1, mean=[0.9, 1.1])
    np.testing.assert_allclose(anchored.center(2, start), [0.9, 1.1])
    with pytest.raises(ValueError):
        GaussianPrior.from_std(0.1, mean=[0.9]).center(2, start)


# --------------------------------------------------------------- the MAP step


def test_map_step_without_a_prior_is_the_gauss_newton_step(linearization) -> None:
    jacobian, residual = linearization
    np.testing.assert_allclose(
        map_step(jacobian, residual), gauss_newton_step(jacobian, residual), rtol=1e-14
    )


def test_map_step_reaches_the_gauss_newton_limit_as_the_prior_weakens(linearization) -> None:
    """AC-UPD-006a: the MAP step converges to the GN step as ``C_p⁻¹ -> 0``."""
    jacobian, residual = linearization
    reference = gauss_newton_step(jacobian, residual)
    design = np.array([1.0, 1.0])
    prior_mean = np.array([0.7, 1.3])  # a deliberately off-centre prior

    previous = np.inf
    for scale in (1.0e-2, 1.0e-6, 1.0e-12):
        step = map_step(
            jacobian,
            residual,
            design_values=design,
            prior_mean=prior_mean,
            prior_precision=scale * np.eye(2),
        )
        difference = np.linalg.norm(step - reference) / np.linalg.norm(reference)
        assert difference < previous
        previous = difference
    assert previous <= 1.0e-8


def test_map_step_is_pulled_towards_the_prior_mean(linearization) -> None:
    jacobian, residual = linearization
    design = np.array([1.0, 1.0])
    prior_mean = np.array([1.5, 1.5])
    step = map_step(
        jacobian,
        residual,
        design_values=design,
        prior_mean=prior_mean,
        prior_precision=1.0e6 * np.eye(2),
    )
    np.testing.assert_allclose(design + step, prior_mean, atol=1e-4)


def test_map_step_is_invariant_to_a_uniform_noise_rescaling(linearization) -> None:
    """Without a prior only the *shape* of ``C_ε`` matters, not its scale."""
    jacobian, residual = linearization
    reference = map_step(jacobian, residual)
    for scale in (1.0e-3, 1.0e3):
        np.testing.assert_allclose(
            map_step(jacobian, residual, noise_precision=scale * np.eye(2)),
            reference,
            rtol=1e-10,
        )


def test_map_step_reweights_residuals_by_the_noise_precision() -> None:
    """An over-determined fit follows ``C_ε``: a noisy row is left unfitted."""
    jacobian = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
    residual = np.array([0.1, -0.2, 0.5])

    balanced = residual + jacobian @ map_step(jacobian, residual)
    assert np.min(np.abs(balanced)) > 1.0e-3  # no row is fitted exactly

    downweighted = residual + jacobian @ map_step(
        jacobian, residual, noise_precision=np.diag([1.0, 1.0, 1.0e-8])
    )
    assert np.max(np.abs(downweighted[:2])) < 1.0e-8
    assert abs(downweighted[2]) > 0.1


def test_map_step_rejects_a_residual_of_the_wrong_length(linearization) -> None:
    jacobian, _ = linearization
    with pytest.raises(ValueError, match="rows"):
        map_step(jacobian, np.zeros(3))


# ------------------------------------------------------- posterior covariance


def test_posterior_without_a_prior_is_the_inverse_fisher_information(linearization) -> None:
    jacobian, _ = linearization
    np.testing.assert_allclose(
        posterior_covariance(jacobian), np.linalg.inv(jacobian.T @ jacobian), rtol=1e-10
    )


def test_a_prior_can_only_contract_the_posterior(linearization) -> None:
    """AC-UPD-006b at the algebra level: ``σ_post ≤ σ_prior`` componentwise."""
    jacobian, _ = linearization
    prior = GaussianPrior.from_std([0.05, 0.05])
    covariance = posterior_covariance(jacobian, prior_precision=prior.precision(2))
    sigma_post = np.sqrt(np.diag(covariance))
    assert np.all(sigma_post <= prior.std(2))

    unregularized = np.sqrt(np.diag(posterior_covariance(jacobian)))
    assert np.all(sigma_post <= unregularized)


def test_posterior_of_an_unidentifiable_direction_stays_finite() -> None:
    """A duplicated column makes ``JᵀJ`` singular; the estimate must not blow up."""
    jacobian = np.array([[1.0, 1.0], [2.0, 2.0]])
    covariance = posterior_covariance(jacobian)
    assert np.all(np.isfinite(covariance))


def test_the_prior_bounds_the_posterior_of_an_unidentifiable_direction() -> None:
    jacobian = np.array([[1.0, 1.0], [2.0, 2.0]])
    prior = GaussianPrior.from_std(0.2)
    covariance = posterior_covariance(jacobian, prior_precision=prior.precision(2))
    np.testing.assert_array_less(np.sqrt(np.diag(covariance)), prior.std(2) + 1e-12)


# ------------------------------------------------------------ full MAP runs


def test_weak_prior_recovers_the_twin_truth(model: ScalingModel) -> None:
    result = update_model_bayesian(
        model,
        parameters(),
        target_frequencies(model),
        prior=GaussianPrior.from_std(1.0e3),
        method="gauss-newton",
    )
    assert isinstance(result, BayesianUpdatingResult)
    assert result.converged
    recovered = np.array([result.parameters[name] for name in ("k0", "k1")])
    truth = np.array([TRUTH["k0"], TRUTH["k1"]])
    assert np.max(np.abs(recovered - truth)) <= 1.0e-3


def test_weak_prior_run_matches_the_deterministic_updater(model: ScalingModel) -> None:
    """AC-UPD-006a end to end: a vanishing prior leaves the GN result untouched."""
    deterministic = update_model(
        model, parameters(), target_frequencies(model), method="gauss-newton"
    )
    bayesian = update_model_bayesian(
        model,
        parameters(),
        target_frequencies(model),
        prior=GaussianPrior.from_std(1.0e6),
        method="gauss-newton",
    )
    for name in ("k0", "k1"):
        assert bayesian.parameters[name] == pytest.approx(deterministic.parameters[name], abs=1e-8)


def test_posterior_is_reported_per_parameter(model: ScalingModel) -> None:
    result = update_model_bayesian(
        model,
        parameters(),
        target_frequencies(model),
        prior=GaussianPrior.from_std([0.1, 0.2]),
    )
    posterior = result.posterior
    assert isinstance(posterior, PosteriorEstimate)
    assert posterior.names == ["k0", "k1"]
    assert posterior.covariance.shape == (2, 2)
    np.testing.assert_allclose(posterior.covariance, posterior.covariance.T, atol=1e-15)
    assert np.all(np.isfinite(posterior.std))
    np.testing.assert_allclose(posterior.std, result.posterior_std)
    np.testing.assert_allclose(np.diag(posterior.correlation()), np.ones(2), atol=1e-12)


def test_posterior_contracts_relative_to_the_prior(model: ScalingModel) -> None:
    """AC-UPD-006b, first half: σ_post ≤ σ_prior for every parameter."""
    prior = GaussianPrior.from_std([0.1, 0.2])
    result = update_model_bayesian(model, parameters(), target_frequencies(model), prior=prior)
    assert np.all(result.posterior.std <= prior.std(2))


def test_a_tight_prior_keeps_the_solution_within_three_sigma(model: ScalingModel) -> None:
    """AC-UPD-006b, second half: a tight prior dominates the data pull."""
    sigma = 0.01
    result = update_model_bayesian(
        model,
        parameters(),
        target_frequencies(model),
        prior=GaussianPrior.from_std(sigma),
    )
    offsets = np.array([abs(result.parameters[name] - 1.0) for name in ("k0", "k1")])
    assert np.all(offsets <= 3.0 * sigma)
    # ...and it does not recover the truth: the prior is deliberately wrong.
    assert abs(result.parameters["k0"] - TRUTH["k0"]) > 3.0 * sigma


def test_tighter_priors_shrink_the_posterior_monotonically(model: ScalingModel) -> None:
    widths = []
    for sigma in (1.0, 0.1, 0.01):
        result = update_model_bayesian(
            model,
            parameters(),
            target_frequencies(model),
            prior=GaussianPrior.from_std(sigma),
        )
        widths.append(result.posterior.std)
    assert np.all(widths[1] < widths[0])
    assert np.all(widths[2] < widths[1])


def test_a_bare_covariance_is_accepted_as_a_prior(model: ScalingModel) -> None:
    updater = BayesianUpdater(model, parameters(), target_frequencies(model), prior=0.04)
    assert isinstance(updater.prior, GaussianPrior)
    np.testing.assert_allclose(updater.prior.std(2), [0.2, 0.2])
    assert updater.prior.names == ("k0", "k1")


def test_noise_covariance_scales_the_reported_posterior(model: ScalingModel) -> None:
    """Ten times noisier measurements give ten times wider posteriors."""
    measured = target_frequencies(model)
    base = update_model_bayesian(model, parameters(), measured, noise_covariance=1.0)
    noisy = update_model_bayesian(model, parameters(), measured, noise_covariance=100.0)
    np.testing.assert_allclose(noisy.posterior.std, 10.0 * base.posterior.std, rtol=1e-6)


def test_noise_covariance_of_the_wrong_size_is_rejected(model: ScalingModel) -> None:
    updater = BayesianUpdater(
        model, parameters(), target_frequencies(model), noise_covariance=[1.0, 1.0, 1.0]
    )
    with pytest.raises(ValueError, match="noise_covariance"):
        updater.run()


def test_log_scaled_parameters_put_the_prior_in_log_space(model: ScalingModel) -> None:
    """The prior lives in design space, so ``log_scaled`` makes it lognormal."""
    result = update_model_bayesian(
        model,
        parameters(log_scaled=True),
        target_frequencies(model),
        prior=GaussianPrior.from_std(1.0e3),
        method="gauss-newton",
    )
    recovered = np.array([result.parameters[name] for name in ("k0", "k1")])
    np.testing.assert_allclose(recovered, [TRUTH["k0"], TRUTH["k1"]], atol=1e-3)
    np.testing.assert_allclose(result.posterior.mean, np.log(recovered), rtol=1e-9)


def test_shape_residuals_are_carried_through_the_map_loop() -> None:
    """MAC rows enlarge the residual; the noise model must follow its length."""
    model = two_dof_model()
    truth = model.modal_data(TRUTH)
    result = update_model_bayesian(
        model,
        parameters(),
        truth.frequencies,
        truth.mode_shapes,
        prior=GaussianPrior.from_std(1.0e3),
        noise_covariance=1.0,
    )
    assert result.final_cost < result.initial_cost
    assert result.posterior.covariance.shape == (2, 2)


def test_report_appends_the_posterior_table(model: ScalingModel) -> None:
    result = update_model_bayesian(
        model, parameters(), target_frequencies(model), prior=GaussianPrior.from_std(0.1)
    )
    report = result.report()
    assert "sigma_post" in report and "sigma_prior" in report
    assert "k0" in report and "k1" in report

    summary = result.posterior.as_dict()
    assert set(summary) == {"k0", "k1"}
    assert summary["k0"]["sigma_prior"] == pytest.approx(0.1)

    low, high = result.posterior.interval("k0", sigmas=2.0)
    assert low < result.posterior.mean[0] < high


def test_updating_without_a_prior_still_reports_a_posterior(model: ScalingModel) -> None:
    """No prior is still a valid MAP run: the posterior is the Fisher estimate."""
    result = update_model_bayesian(
        model, parameters(), target_frequencies(model), method="gauss-newton"
    )
    assert np.all(np.isinf(result.posterior.prior_std))
    assert np.all(np.isfinite(result.posterior.std))
