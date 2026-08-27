"""Design-of-experiments helper tests."""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.uq import doe_box_run, doe_levels, doe_lhs_run


def test_doe_levels_builds_a_full_factorial_grid() -> None:
    names, samples = doe_levels({"b": [10.0, 20.0], "a": [1.0, 2.0]})

    assert names == ("a", "b")
    assert samples.shape == (4, 2)
    assert samples.tolist() == [
        [1.0, 10.0],
        [1.0, 20.0],
        [2.0, 10.0],
        [2.0, 20.0],
    ]


def test_doe_levels_requires_at_least_one_factor() -> None:
    with pytest.raises(ValueError, match="at least one factor"):
        doe_levels({})


def test_doe_box_run_evaluates_every_corner() -> None:
    nominal = {"offset": 5.0}

    def evaluate(theta: dict[str, float]) -> np.ndarray:
        return np.array([theta["a"] * theta["b"] + theta["offset"]])

    result = doe_box_run(
        evaluate,
        nominal,
        {"a": [1.0, 2.0], "b": [3.0, 4.0]},
    )

    assert result.samples.shape == (4, 1)
    assert result.mean[0] == pytest.approx(np.mean(result.samples[:, 0]))
    assert result.diagnostics["sampler"] == "full_factorial"
    assert result.diagnostics["count"] == 4


def test_doe_lhs_run_maps_unit_samples_into_bounds() -> None:
    nominal = {"c": 0.0}

    def evaluate(theta: dict[str, float]) -> np.ndarray:
        return np.array([theta["x"] + theta["y"]])

    result = doe_lhs_run(
        evaluate,
        nominal,
        {"x": (0.0, 1.0), "y": (10.0, 20.0)},
        count=8,
        seed=2,
    )

    assert result.samples.shape == (8, 1)
    assert result.diagnostics["sampler"] == "lhs_box"
    assert result.diagnostics["seed"] == 2
