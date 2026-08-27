"""Tests for optional Numba acceleration."""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.accel.mac import mac_real_unweighted, numba_available
from openfemlab.correlation import mac


def test_mac_real_unweighted_matches_correlation_mac():
    rng = np.random.default_rng(0)
    a = rng.standard_normal((200, 8))
    b = rng.standard_normal((200, 6))
    reference = mac(a, b)
    accelerated = mac_real_unweighted(a, b)
    np.testing.assert_allclose(accelerated, reference, rtol=0.0, atol=1e-12)


def test_correlation_mac_uses_accel_for_large_real_problems():
    rng = np.random.default_rng(1)
    ndof, ma, mb = 120, 15, 12
    a = rng.standard_normal((ndof, ma))
    b = rng.standard_normal((ndof, mb))
    reference = mac(a, b)
    np.testing.assert_allclose(reference, mac(a, b), rtol=0.0, atol=1e-12)


@pytest.mark.skipif(not numba_available(), reason="numba not installed")
def test_numba_kernel_is_available():
    assert numba_available()
