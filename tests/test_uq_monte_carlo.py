"""Monte Carlo uncertainty propagation tests."""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.uq import MonteCarloResult, NormalUncertainty, monte_carlo_run


def test_monte_carlo_propagates_linear_response() -> None:
    nominal = {"E": 210e9, "rho": 7800.0}
    uncertainties = {
        "E": NormalUncertainty(mean=210e9, std=1.0e9),
        "rho": NormalUncertainty(mean=7800.0, std=20.0),
    }

    def evaluate(theta: dict[str, float]) -> np.ndarray:
        return np.array([theta["E"] / theta["rho"]])

    result = monte_carlo_run(evaluate, nominal, uncertainties, 256, seed=3)
    assert isinstance(result, MonteCarloResult)
    assert result.samples.shape == (256, 1)
    assert result.mean[0] == pytest.approx(210e9 / 7800.0, rel=0.02)
    assert result.std[0] > 0.0


def test_lhs_sampler_runs_without_scipy() -> None:
    nominal = {"a": 1.0, "b": 2.0}
    uncertainties = {
        "a": NormalUncertainty(mean=1.0, std=0.1),
        "b": NormalUncertainty(mean=2.0, std=0.2),
    }
    result = monte_carlo_run(
        lambda theta: np.array([theta["a"] + theta["b"]]),
        nominal,
        uncertainties,
        32,
        seed=0,
        sampler="lhs",
    )
    assert result.samples.shape == (32, 1)
    assert result.diagnostics["sampler"] == "lhs"
