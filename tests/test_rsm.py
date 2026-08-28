"""Tests for quadratic response-surface models."""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.optimization import QuadraticRSM, fit_quadratic_rsm


def test_quadratic_rsm_recovers_plane():
    samples = np.array(
        [
            [0.0, 0.0],
            [1.0, 0.0],
            [0.0, 1.0],
            [1.0, 1.0],
            [0.5, 0.0],
            [0.0, 0.5],
        ],
        dtype=float,
    )

    def truth(row: np.ndarray) -> float:
        x, y = row
        return 1.0 + 2.0 * x + 3.0 * y + 4.0 * x * x + 5.0 * x * y + 6.0 * y * y

    responses = np.array([truth(row) for row in samples])
    model = fit_quadratic_rsm(samples, responses, variable_names=("x", "y"))
    assert isinstance(model, QuadraticRSM)
    probe = np.array([0.2, 0.3])
    assert model.predict(probe) == pytest.approx(truth(probe), rel=1e-9)
    grad = model.gradient(probe)
    step = 1e-6
    fd = np.array(
        [
            (truth(probe + step * basis) - truth(probe - step * basis)) / (2 * step)
            for basis in (np.array([1.0, 0.0]), np.array([0.0, 1.0]))
        ]
    )
    np.testing.assert_allclose(grad, fd, rtol=1e-5, atol=1e-8)
