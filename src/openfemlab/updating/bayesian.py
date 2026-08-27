"""Bayesian (MAP) model updating with a Gaussian prior — spec anchor MS-3.5.

Deterministic maximum-a-posteriori counterpart of the Gauss-Newton /
Levenberg-Marquardt loop in :mod:`openfemlab.updating.updater`.  The objective
gains a prior term,

    J(θ) = ½ rᵀ C_ε⁻¹ r + ½ (θ − θ₀)ᵀ C_p⁻¹ (θ − θ₀)

with ``r`` the residual the deterministic updater already assembles, ``C_ε``
the measurement-noise covariance and ``C_p`` the prior covariance of the
parameters.  Linearising ``r`` gives the MAP step

    (Jᵀ C_ε⁻¹ J + C_p⁻¹) Δθ = −[ Jᵀ C_ε⁻¹ r + C_p⁻¹ (θ − θ₀) ]

and, at the solution, the Laplace approximation of the posterior

    C_post ≈ (Jᵀ C_ε⁻¹ J + C_p⁻¹)⁻¹

whose diagonal is reported as a per-parameter σ_post.  Two limits are the
contract (AC-UPD-006a/b): as ``C_p⁻¹ → 0`` the step must reduce to the
unregularised Gauss-Newton step, and a prior can only ever *shrink* the
posterior, so ``σ_post ≤ σ_prior`` componentwise.

Everything happens in the updater's **design space** (see
:mod:`openfemlab.updating.parameters`): the prior is a distribution over the
free design variables, which for the default linear parameterisation are the
dimensionless scaling factors themselves and for ``log_scaled`` parameters are
their logarithms (a lognormal prior on the factor).

Sampling-based posteriors (MCMC/TMCMC) are out of scope here; ``h(θ)``,
``C_ε`` and ``C_p`` are exposed so a sampler can reuse them later.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, fields
from typing import Any

import numpy as np

from .parameters import ParameterSet, UpdatableParameter
from .updater import ModelUpdater, UpdatingResult

__all__ = [
    "GaussianPrior",
    "PosteriorEstimate",
    "BayesianUpdatingResult",
    "BayesianUpdater",
    "covariance_matrix",
    "precision_matrix",
    "map_step",
    "posterior_covariance",
    "posterior_sigma",
    "update_model_bayesian",
]

CovarianceSpec = float | Sequence[float] | np.ndarray | None


def covariance_matrix(spec: CovarianceSpec, size: int, name: str) -> np.ndarray | None:
    """Expand a covariance specification into an ``(size, size)`` matrix.

    ``spec`` may be ``None`` (no information — returns ``None``), a scalar
    variance (isotropic), a length-``size`` vector of variances (diagonal), or
    a full symmetric positive-definite matrix.
    """
    if spec is None:
        return None
    array = np.asarray(spec, dtype=float)
    if array.ndim == 0:
        value = float(array)
        if not np.isfinite(value) or value <= 0.0:
            raise ValueError(f"{name}: variance must be finite and positive, got {value}")
        return value * np.eye(size)
    if array.ndim == 1:
        if array.size != size:
            raise ValueError(f"{name}: expected {size} variances, got {array.size}")
        if not np.all(np.isfinite(array)) or np.any(array <= 0.0):
            raise ValueError(f"{name}: variances must be finite and positive")
        return np.diag(array)
    if array.ndim == 2:
        if array.shape != (size, size):
            raise ValueError(f"{name}: expected shape ({size}, {size}), got {array.shape}")
        if not np.allclose(array, array.T, rtol=0.0, atol=1e-12 * max(1.0, _scale(array))):
            raise ValueError(f"{name}: covariance matrix must be symmetric")
        symmetric = 0.5 * (array + array.T)
        if np.min(np.linalg.eigvalsh(symmetric)) <= 0.0:
            raise ValueError(f"{name}: covariance matrix must be positive definite")
        return symmetric
    raise ValueError(f"{name}: expected a scalar, a vector or a matrix, got {array.ndim} axes")


def precision_matrix(spec: CovarianceSpec, size: int, name: str) -> np.ndarray | None:
    """Inverse of :func:`covariance_matrix`; ``None`` means "no information"."""
    covariance = covariance_matrix(spec, size, name)
    if covariance is None:
        return None
    return np.linalg.inv(covariance)


def _scale(matrix: np.ndarray) -> float:
    return float(np.max(np.abs(matrix))) if matrix.size else 1.0


def _weighted(jacobian: np.ndarray, noise_precision: np.ndarray | None) -> np.ndarray:
    """``Jᵀ C_ε⁻¹`` (or ``Jᵀ`` for an uninformative / identity noise model)."""
    if noise_precision is None:
        return jacobian.T
    return jacobian.T @ noise_precision


def _symmetrize(matrix: np.ndarray) -> np.ndarray:
    return 0.5 * (matrix + matrix.T)


@dataclass
class GaussianPrior:
    """Gaussian prior ``N(mean, covariance)`` over the free design variables.

    Attributes
    ----------
    covariance:
        Prior covariance ``C_p`` as a scalar variance, a vector of per-parameter
        variances, or a full matrix.  ``None`` is the improper uniform prior
        (``C_p⁻¹ = 0``), which makes the MAP step identical to Gauss-Newton.
    mean:
        Prior mean ``θ₀``.  ``None`` (the default) anchors the prior at the
        starting point of the updating run.
    names:
        Optional parameter names, carried through to the posterior report.
    """

    covariance: CovarianceSpec = None
    mean: Sequence[float] | np.ndarray | None = None
    names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        self.names = tuple(self.names)
        if self.mean is not None:
            self.mean = np.asarray(self.mean, dtype=float).ravel()

    @classmethod
    def from_std(
        cls,
        std: float | Sequence[float] | np.ndarray,
        mean: Sequence[float] | np.ndarray | None = None,
        names: Sequence[str] = (),
    ) -> GaussianPrior:
        """Build a diagonal prior from standard deviations instead of variances."""
        array = np.asarray(std, dtype=float)
        if np.any(array <= 0.0):
            raise ValueError("prior standard deviations must be positive")
        return cls(covariance=array**2, mean=mean, names=tuple(names))

    @classmethod
    def uninformative(cls, names: Sequence[str] = ()) -> GaussianPrior:
        """The improper flat prior; the MAP estimate is then the GN estimate."""
        return cls(covariance=None, names=tuple(names))

    @property
    def is_informative(self) -> bool:
        return self.covariance is not None

    def matrix(self, size: int) -> np.ndarray | None:
        return covariance_matrix(self.covariance, size, "prior_covariance")

    def precision(self, size: int) -> np.ndarray:
        """``C_p⁻¹``, the zero matrix for an uninformative prior."""
        precision = precision_matrix(self.covariance, size, "prior_covariance")
        return np.zeros((size, size)) if precision is None else precision

    def std(self, size: int) -> np.ndarray:
        """Per-parameter σ_prior; ``inf`` where the prior carries no information."""
        covariance = self.matrix(size)
        if covariance is None:
            return np.full(size, np.inf)
        return np.sqrt(np.diag(covariance))

    def center(self, size: int, fallback: np.ndarray) -> np.ndarray:
        """Prior mean, defaulting to ``fallback`` (the run's starting point)."""
        if self.mean is None:
            return np.asarray(fallback, dtype=float).ravel()
        if self.mean.size != size:
            raise ValueError(f"prior mean has {self.mean.size} entries, expected {size}")
        return self.mean


@dataclass
class PosteriorEstimate:
    """Laplace posterior of a MAP run, in the updater's design space."""

    names: list[str]
    mean: np.ndarray
    covariance: np.ndarray
    prior_std: np.ndarray

    @property
    def std(self) -> np.ndarray:
        """Per-parameter posterior standard deviations σ_post."""
        return np.sqrt(np.clip(np.diag(self.covariance), 0.0, None))

    @property
    def variance(self) -> np.ndarray:
        return np.clip(np.diag(self.covariance), 0.0, None)

    def correlation(self) -> np.ndarray:
        """Posterior correlation matrix, ``inf``-free and unit-diagonal."""
        sigma = self.std
        safe = np.where(sigma > 0.0, sigma, 1.0)
        return self.covariance / np.outer(safe, safe)

    def interval(self, parameter: str | int, sigmas: float = 2.0) -> tuple[float, float]:
        """Credible interval ``mean ± sigmas·σ_post`` for one parameter."""
        index = self.names.index(parameter) if isinstance(parameter, str) else int(parameter)
        half_width = sigmas * float(self.std[index])
        return float(self.mean[index]) - half_width, float(self.mean[index]) + half_width

    def as_dict(self) -> dict[str, dict[str, float]]:
        return {
            name: {
                "mean": float(self.mean[i]),
                "sigma_post": float(self.std[i]),
                "sigma_prior": float(self.prior_std[i]),
            }
            for i, name in enumerate(self.names)
        }

    def table(self) -> str:
        header = f"{'name':<20} {'MAP':>12} {'sigma_post':>12} {'sigma_prior':>12}"
        lines = [header, "-" * len(header)]
        sigma = self.std
        for i, name in enumerate(self.names):
            lines.append(
                f"{name:<20} {self.mean[i]:12.6f} {sigma[i]:12.6e} {self.prior_std[i]:12.6e}"
            )
        return "\n".join(lines)


@dataclass
class BayesianUpdatingResult(UpdatingResult):
    """:class:`~openfemlab.updating.updater.UpdatingResult` plus the posterior."""

    posterior: PosteriorEstimate | None = None

    @property
    def posterior_std(self) -> np.ndarray | None:
        return None if self.posterior is None else self.posterior.std

    def report(self) -> str:
        base = super().report()
        if self.posterior is None:  # pragma: no cover - only without a Jacobian
            return base
        return f"{base}\n\n{self.posterior.table()}"


def map_step(
    jacobian: np.ndarray,
    residual: np.ndarray,
    *,
    design_values: np.ndarray | None = None,
    prior_mean: np.ndarray | None = None,
    prior_precision: np.ndarray | None = None,
    noise_precision: np.ndarray | None = None,
) -> np.ndarray:
    """Linearised MAP increment ``Δθ`` at the current point.

    With ``prior_precision`` ``None`` or zero this is exactly the unregularised
    Gauss-Newton step ``−(JᵀJ)⁻¹ Jᵀ r`` (AC-UPD-006a).
    """
    jacobian = np.atleast_2d(np.asarray(jacobian, dtype=float))
    residual = np.asarray(residual, dtype=float).ravel()
    if jacobian.shape[0] != residual.size:
        raise ValueError(
            f"jacobian has {jacobian.shape[0]} rows but the residual has {residual.size} entries"
        )
    n = jacobian.shape[1]
    weighted = _weighted(jacobian, noise_precision)
    hessian = weighted @ jacobian
    gradient = weighted @ residual
    if prior_precision is not None:
        prior_precision = np.asarray(prior_precision, dtype=float)
        hessian = hessian + prior_precision
        if design_values is not None:
            offset = np.asarray(design_values, dtype=float).ravel()
            if prior_mean is not None:
                offset = offset - np.asarray(prior_mean, dtype=float).ravel()
            gradient = gradient + prior_precision @ offset
    return _solve(_symmetrize(hessian), -gradient, n)


def posterior_covariance(
    jacobian: np.ndarray,
    *,
    prior_precision: np.ndarray | None = None,
    noise_precision: np.ndarray | None = None,
) -> np.ndarray:
    """Laplace posterior covariance ``(Jᵀ C_ε⁻¹ J + C_p⁻¹)⁻¹``.

    A rank-deficient information matrix (fewer independent residuals than
    parameters, no prior) falls back to the pseudo-inverse, which reports a
    zero variance for the unidentifiable directions rather than raising.
    """
    jacobian = np.atleast_2d(np.asarray(jacobian, dtype=float))
    information = _weighted(jacobian, noise_precision) @ jacobian
    if prior_precision is not None:
        information = information + np.asarray(prior_precision, dtype=float)
    information = _symmetrize(information)
    try:
        return _symmetrize(np.linalg.inv(information))
    except np.linalg.LinAlgError:
        return _symmetrize(np.linalg.pinv(information))


def posterior_sigma(result: UpdatingResult) -> dict[str, float]:
    """Per-parameter σ_post of an updating run, keyed by parameter name.

    A MAP run — one driven by :class:`BayesianUpdater` — already carries the
    Laplace posterior ``(Jᵀ C_ε⁻¹ J + C_p⁻¹)⁻¹`` evaluated at the solution, and
    that is what gets reported.  A deterministic run has neither ``C_ε`` nor
    ``C_p``, so it falls back to the least-squares counterpart
    ``C_post ≈ σ² (JᵀJ)⁻¹`` with ``σ²`` estimated from the final residual: a
    weaker statement, but it keeps the column populated.

    The values live in the updater's design space, so a ``log_scaled``
    parameter reports the spread of ``log(factor)`` rather than of the factor.
    """
    if isinstance(result, BayesianUpdatingResult) and result.posterior is not None:
        posterior = result.posterior
        return {
            name: float(value)
            for name, value in zip(posterior.names, posterior.std, strict=False)
        }

    sensitivity = result.sensitivity
    if sensitivity is None or sensitivity.matrix.size == 0:
        return {}
    jacobian = np.asarray(sensitivity.matrix, dtype=float)
    n_residuals, n_parameters = jacobian.shape
    dof = max(n_residuals - n_parameters, 1)
    variance = 2.0 * result.final_cost / dof
    covariance = np.linalg.pinv(jacobian.T @ jacobian) * variance
    diagonal = np.clip(np.diag(covariance), 0.0, None)
    return {
        name: float(np.sqrt(value))
        for name, value in zip(sensitivity.parameter_names, diagonal, strict=False)
    }


def _solve(matrix: np.ndarray, rhs: np.ndarray, size: int) -> np.ndarray:
    try:
        step = np.linalg.solve(matrix, rhs)
    except np.linalg.LinAlgError:
        step = np.linalg.lstsq(matrix, rhs, rcond=None)[0]
    if not np.all(np.isfinite(step)):  # pragma: no cover - numerical safety net
        step = np.linalg.lstsq(matrix, rhs, rcond=None)[0]
    return step.reshape(size)


class BayesianUpdater(ModelUpdater):
    """MAP updater: the LM loop driven by the regularised MAP normal equations.

    Adds two inputs to :class:`~openfemlab.updating.updater.ModelUpdater`:

    prior:
        A :class:`GaussianPrior` over the free design variables (or, as a
        shortcut, anything :func:`covariance_matrix` accepts as ``C_p``).
        Omitted, the run is an ordinary Gauss-Newton/LM run and the posterior
        is the plain Fisher-information estimate.
    noise_covariance:
        ``C_ε`` over the assembled residual vector — scalar, per-entry vector,
        or full matrix.  Omitted, the residual weights already baked in by
        ``UpdatingOptions`` are taken as the whitening.
    """

    def __init__(
        self,
        model: Any,
        parameters: ParameterSet | Sequence[UpdatableParameter],
        target_frequencies: Sequence[float] | np.ndarray,
        target_shapes: np.ndarray | None = None,
        *,
        prior: GaussianPrior | CovarianceSpec = None,
        noise_covariance: CovarianceSpec = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(model, parameters, target_frequencies, target_shapes, **kwargs)
        if prior is None or isinstance(prior, GaussianPrior):
            self.prior = prior or GaussianPrior.uninformative()
        else:
            self.prior = GaussianPrior(covariance=prior)
        if not self.prior.names:
            self.prior.names = tuple(self.parameters.free_names)
        self.noise_covariance = noise_covariance
        self._prior_precision = self.prior.precision(self.n_parameters)
        self._noise_cache: tuple[int, np.ndarray | None] | None = None

    @property
    def n_parameters(self) -> int:
        return len(self.parameters.free)

    # ------------------------------------------------------------------
    # covariance plumbing
    # ------------------------------------------------------------------
    def prior_precision(self) -> np.ndarray:
        """``C_p⁻¹`` over the free design variables."""
        return self._prior_precision

    def noise_precision(self, n_residuals: int) -> np.ndarray | None:
        """``C_ε⁻¹`` for a residual of ``n_residuals`` entries (``None`` = identity)."""
        if self._noise_cache is None or self._noise_cache[0] != n_residuals:
            precision = precision_matrix(self.noise_covariance, n_residuals, "noise_covariance")
            self._noise_cache = (n_residuals, precision)
        return self._noise_cache[1]

    # ------------------------------------------------------------------
    # estimator hooks
    # ------------------------------------------------------------------
    def cost(self, residual: np.ndarray) -> float:
        precision = self.noise_precision(residual.size)
        if precision is None:
            return super().cost(residual)
        return 0.5 * float(residual @ (precision @ residual))

    def penalty(self, design_values: np.ndarray, reference_values: np.ndarray) -> float:
        offset = design_values - self.prior.center(self.n_parameters, reference_values)
        prior_term = 0.5 * float(offset @ (self._prior_precision @ offset))
        return prior_term + super().penalty(design_values, reference_values)

    def normal_equations(
        self,
        jacobian: np.ndarray,
        residual: np.ndarray,
        design_values: np.ndarray,
        reference_values: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        weighted = _weighted(jacobian, self.noise_precision(residual.size))
        hessian = weighted @ jacobian + self._prior_precision
        offset = design_values - self.prior.center(self.n_parameters, reference_values)
        gradient = weighted @ residual + self._prior_precision @ offset
        beta = float(self.options.regularization)
        if beta > 0.0:
            hessian = hessian + beta * np.eye(hessian.shape[0])
            gradient = gradient + beta * (design_values - reference_values)
        return _symmetrize(hessian), gradient

    # ------------------------------------------------------------------
    # run
    # ------------------------------------------------------------------
    def run(self) -> BayesianUpdatingResult:
        """Run the MAP loop and attach the Laplace posterior at the solution."""
        result = super().run()
        posterior = self._posterior(result)
        payload = {f.name: getattr(result, f.name) for f in fields(UpdatingResult)}
        return BayesianUpdatingResult(**payload, posterior=posterior)

    def _posterior(self, result: UpdatingResult) -> PosteriorEstimate | None:
        """Laplace posterior from a Jacobian re-evaluated at the MAP point."""
        data = result.modal_data
        if data is None:  # pragma: no cover - run() always reports modal data
            return None
        design_values = self.parameters.design_values()
        pairs = self.pair(data)
        residual = self.residual(data, pairs)
        jacobian = self.jacobian(design_values, pairs, residual, data)
        covariance = posterior_covariance(
            jacobian,
            prior_precision=self._prior_precision,
            noise_precision=self.noise_precision(residual.size),
        )
        return PosteriorEstimate(
            names=list(self.parameters.free_names),
            mean=design_values,
            covariance=covariance,
            prior_std=self.prior.std(self.n_parameters),
        )


def update_model_bayesian(
    model: Any,
    parameters: ParameterSet | Sequence[UpdatableParameter],
    target_frequencies: Sequence[float] | np.ndarray,
    target_shapes: np.ndarray | None = None,
    *,
    prior: GaussianPrior | CovarianceSpec = None,
    noise_covariance: CovarianceSpec = None,
    **kwargs: Any,
) -> BayesianUpdatingResult:
    """Convenience wrapper: build a :class:`BayesianUpdater` and run it."""
    updater = BayesianUpdater(
        model,
        parameters,
        target_frequencies,
        target_shapes,
        prior=prior,
        noise_covariance=noise_covariance,
        **kwargs,
    )
    return updater.run()
