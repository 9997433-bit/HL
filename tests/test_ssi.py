"""Unit tests for SSI-COV operational modal analysis."""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.exceptions import MPEError
from openfemlab.mpe import ssi_cov
from openfemlab.mpe.ssi import simulate_operational_response

FREQUENCIES = (4.0, 9.5)
DAMPINGS = (0.015, 0.02)
SHAPES = np.array([[1.0, 0.8], [1.2, -0.6], [0.7, 1.1]])
FS = 200.0
SAMPLES = 8192
ORDERS = tuple(range(8, 25, 2))


def _record() -> np.ndarray:
    return simulate_operational_response(
        FREQUENCIES,
        DAMPINGS,
        SHAPES,
        sampling_rate_hz=FS,
        samples=SAMPLES,
        seed=17,
    )


def test_ssi_cov_recovers_a_two_mode_oracle() -> None:
    result = ssi_cov(
        _record(),
        FS,
        range(6, 20, 2),
        block_rows=30,
        min_count=2,
        freq_tol=0.05,
        damp_tol=0.15,
        mac_tol=0.85,
    )
    frequencies = list(result.frequencies_hz)
    assert any(abs(value - FREQUENCIES[0]) < 0.6 for value in frequencies)
    assert any(abs(value - FREQUENCIES[1]) < 0.6 for value in frequencies)
    assert all(0.0 <= ratio <= 0.08 for ratio in result.damping_ratios)


def test_ssi_cov_is_deterministic_on_identical_input() -> None:
    record = _record()
    kwargs = dict(
        block_rows=30,
        min_count=2,
        freq_tol=0.05,
        damp_tol=0.15,
        mac_tol=0.85,
    )
    left = ssi_cov(record, FS, range(6, 20, 2), **kwargs)
    right = ssi_cov(record, FS, range(6, 20, 2), **kwargs)
    assert np.array_equal(left.frequencies_hz, right.frequencies_hz)
    assert np.array_equal(left.damping_ratios, right.damping_ratios)


def test_ssi_cov_rejects_degenerate_records() -> None:
    with pytest.raises(MPEError, match="2-D"):
        ssi_cov(np.zeros(32), FS, ORDERS)
    with pytest.raises(MPEError, match="longer record"):
        ssi_cov(np.zeros((16, 2)), FS, ORDERS)
