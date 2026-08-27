"""Design-of-experiments helpers for uncertainty studies."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

import numpy as np
import numpy.typing as npt

from .monte_carlo import MonteCarloResult, latin_hypercube_samples

__all__ = ["doe_box_run", "doe_levels"]


def doe_levels(
    factors: Mapping[str, Sequence[float]],
) -> tuple[tuple[str, ...], npt.NDArray[np.float64]]:
    """Full factorial grid over discrete factor levels."""
    if not factors:
        raise ValueError("at least one factor is required")
    names = tuple(sorted(factors))
    grids = [np.asarray(factors[name], dtype=float) for name in names]
    mesh = np.meshgrid(*grids, indexing="ij")
    stacked = np.column_stack([level.reshape(-1) for level in mesh])
    return names, stacked


def doe_box_run(
    evaluate: Callable[[Mapping[str, float]], npt.NDArray[np.floating]],
    nominal: Mapping[str, float],
    factors: Mapping[str, Sequence[float]],
) -> MonteCarloResult:
    """Evaluate a full factorial design over ``factors``."""
    names, samples = doe_levels(factors)
    responses: list[npt.NDArray[np.float64]] = []
    for row in samples:
        theta = dict(nominal)
        for index, name in enumerate(names):
            theta[name] = float(row[index])
        responses.append(np.asarray(evaluate(theta), dtype=float).reshape(-1))
    stacked = np.vstack(responses)
    return MonteCarloResult(
        samples=stacked,
        mean=np.mean(stacked, axis=0),
        std=np.std(stacked, axis=0, ddof=0),
        parameters=names,
        diagnostics={"count": int(samples.shape[0]), "sampler": "full_factorial"},
    )


def doe_lhs_run(
    evaluate: Callable[[Mapping[str, float]], npt.NDArray[np.floating]],
    nominal: Mapping[str, float],
    bounds: Mapping[str, tuple[float, float]],
    count: int,
    *,
    seed: int | None = None,
) -> MonteCarloResult:
    """Map an LHS sample in ``[low, high]`` for each bounded factor."""
    if count < 1:
        raise ValueError(f"count must be >= 1, got {count}")
    if not bounds:
        raise ValueError("at least one bounded factor is required")
    names = tuple(sorted(bounds))
    unit = latin_hypercube_samples(count, len(names), seed=seed)
    samples = np.zeros((count, len(names)), dtype=float)
    for index, name in enumerate(names):
        low, high = bounds[name]
        samples[:, index] = low + unit[:, index] * (high - low)
    responses: list[npt.NDArray[np.float64]] = []
    for row in samples:
        theta = dict(nominal)
        for index, name in enumerate(names):
            theta[name] = float(row[index])
        responses.append(np.asarray(evaluate(theta), dtype=float).reshape(-1))
    stacked = np.vstack(responses)
    return MonteCarloResult(
        samples=stacked,
        mean=np.mean(stacked, axis=0),
        std=np.std(stacked, axis=0, ddof=0),
        parameters=names,
        diagnostics={"count": count, "sampler": "lhs_box", "seed": seed},
    )
