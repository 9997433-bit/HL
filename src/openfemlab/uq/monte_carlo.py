"""Monte Carlo propagation for solver-backed responses (GAP-11 slice).

The module targets the model-updating workflow: draw perturbed parameter
vectors, evaluate a deterministic forward model, and summarise the resulting
response samples.  It deliberately stays solver-agnostic — the caller supplies
``evaluate(theta) -> array``.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import numpy.typing as npt

__all__ = [
    "NormalUncertainty",
    "MonteCarloResult",
    "sample_normal_parameters",
    "latin_hypercube_samples",
    "monte_carlo_run",
]


@dataclass(frozen=True)
class NormalUncertainty:
    """Independent normal perturbation around a nominal parameter value."""

    mean: float
    std: float

    def __post_init__(self) -> None:
        if self.std < 0.0:
            raise ValueError(f"std must be non-negative, got {self.std}")
        if not np.isfinite(self.mean) or not np.isfinite(self.std):
            raise ValueError("mean and std must be finite")


@dataclass(frozen=True)
class MonteCarloResult:
    """Samples and summary statistics of a Monte Carlo propagation."""

    samples: npt.NDArray[np.float64]
    mean: npt.NDArray[np.float64]
    std: npt.NDArray[np.float64]
    parameters: tuple[str, ...]
    diagnostics: dict[str, Any] = field(default_factory=dict)


def sample_normal_parameters(
    nominal: Mapping[str, float],
    uncertainties: Mapping[str, NormalUncertainty],
    count: int,
    *,
    seed: int | None = None,
) -> tuple[tuple[str, ...], npt.NDArray[np.float64]]:
    """Draw ``count`` independent normal samples around ``nominal``."""
    if count < 1:
        raise ValueError(f"count must be >= 1, got {count}")
    names = tuple(sorted(uncertainties))
    if not names:
        raise ValueError("at least one uncertain parameter is required")
    for name in names:
        if name not in nominal:
            raise KeyError(f"nominal values do not define parameter {name!r}")

    rng = np.random.default_rng(seed)
    draws = np.zeros((count, len(names)), dtype=float)
    for index, name in enumerate(names):
        spec = uncertainties[name]
        draws[:, index] = rng.normal(spec.mean, spec.std, size=count)
    return names, draws


def latin_hypercube_samples(
    count: int,
    dimension: int,
    *,
    seed: int | None = None,
) -> npt.NDArray[np.float64]:
    """Unit hypercube Latin hypercube samples in ``[0, 1)^dimension``."""
    if count < 1:
        raise ValueError(f"count must be >= 1, got {count}")
    if dimension < 1:
        raise ValueError(f"dimension must be >= 1, got {dimension}")
    rng = np.random.default_rng(seed)
    cuts = np.linspace(0.0, 1.0, count + 1)
    samples = np.zeros((count, dimension), dtype=float)
    for axis in range(dimension):
        points = rng.uniform(cuts[:-1], cuts[1:])
        rng.shuffle(points)
        samples[:, axis] = points
    return samples


def monte_carlo_run(
    evaluate: Callable[[Mapping[str, float]], npt.NDArray[np.floating]],
    nominal: Mapping[str, float],
    uncertainties: Mapping[str, NormalUncertainty],
    count: int,
    *,
    seed: int | None = None,
    sampler: str = "independent",
) -> MonteCarloResult:
    """Propagate normal parameter uncertainty through ``evaluate``."""
    names, draws = sample_normal_parameters(nominal, uncertainties, count, seed=seed)
    if sampler not in {"independent", "lhs"}:
        raise ValueError(f"sampler must be 'independent' or 'lhs', got {sampler!r}")

    if sampler == "lhs" and len(names) > 1:
        unit = latin_hypercube_samples(count, len(names), seed=seed)
        for index, name in enumerate(names):
            spec = uncertainties[name]
            draws[:, index] = spec.mean + spec.std * _normal_ppf(unit[:, index])

    responses: list[npt.NDArray[np.float64]] = []
    for row in draws:
        theta = dict(nominal)
        for index, name in enumerate(names):
            theta[name] = float(row[index])
        value = np.asarray(evaluate(theta), dtype=float).reshape(-1)
        responses.append(value)

    stacked = np.vstack(responses)
    return MonteCarloResult(
        samples=stacked,
        mean=np.mean(stacked, axis=0),
        std=np.std(stacked, axis=0, ddof=0),
        parameters=names,
        diagnostics={"count": count, "sampler": sampler, "seed": seed},
    )


def _normal_ppf(probability: npt.NDArray[np.floating]) -> npt.NDArray[np.float64]:
    """Inverse normal CDF without importing SciPy."""
    vector = np.asarray(probability, dtype=float)
    clipped = np.clip(vector, 1e-12, 1.0 - 1e-12)
    return np.sqrt(2.0) * np.vectorize(lambda p: _erfinv(2.0 * p - 1.0))(clipped)


def _erfinv(value: float) -> float:
    """Approximate inverse error function (Winitzki 2008)."""
    sign = 1.0 if value >= 0.0 else -1.0
    x = abs(value)
    if x >= 1.0:
        return sign * 1e6
    ln = np.log(1.0 - x * x)
    first = 2.0 / (np.pi * 0.147) + 0.5 * ln
    second = ln / 0.147
    return sign * np.sqrt(np.sqrt(first * first - second) - first)
