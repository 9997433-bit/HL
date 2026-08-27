"""Tests for DOE → optimization design-space bridge."""

from __future__ import annotations

import numpy as np

from openfemlab.optimization import (
    DesignSpace,
    factorial_design_vectors,
    run_factorial_screen,
)
from openfemlab.updating import ScalingModel, UpdatableParameter

K1 = np.array([[1.0, 0.0], [0.0, 0.0]])
K2 = np.array([[1.0, -1.0], [-1.0, 1.0]])


def _space() -> tuple[ScalingModel, DesignSpace]:
    model = ScalingModel(stiffness_parts={"k1": K1, "k2": K2}, base_mass=np.eye(2))
    params = [
        UpdatableParameter("k1", value=1.0, lower=0.2, upper=5.0),
        UpdatableParameter("k2", value=1.0, lower=0.2, upper=5.0),
    ]
    return model, DesignSpace(params)


def test_factorial_design_vectors_match_space_size() -> None:
    _, space = _space()
    names, physical, design = factorial_design_vectors(
        space, {"k1": (0.8, 1.0), "k2": (1.0, 1.2)}
    )
    assert names == ("k1", "k2")
    assert physical.shape == (4, 2)
    assert design.shape == (4, 2)


def test_run_factorial_screen_evaluates_all_points() -> None:
    model, space = _space()

    def first_frequency(theta: dict[str, float]) -> np.ndarray:
        return np.asarray([model.modal_data(theta).frequencies[0]], dtype=float)

    screen = run_factorial_screen(space, {"k1": (0.8, 1.2), "k2": (1.0,)}, first_frequency)
    assert screen.count == 2
    assert screen.responses.shape == (2, 1)
    assert screen.design.shape == (2, 2)
    assert float(np.max(screen.responses)) > float(np.min(screen.responses))
