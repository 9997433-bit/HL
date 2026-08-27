"""Contract tests for the optional acceleration layer.

Two properties matter here and neither is about speed. The accelerated kernels
must agree with the generic :func:`openfemlab.correlation.mac` they stand in
for — same values, same failures — and the dispatch that reaches them must be
invisible: installing the extra may change which code runs, never what
``mac`` returns. The NumPy backend is exercised everywhere; the Numba tests
skip themselves when the extra is absent, which is the default install and
what CI runs.
"""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.accel import mac as accel_mac
from openfemlab.accel import mac_real_unweighted, numba_available, resolve_backend
from openfemlab.correlation.mac import ACCEL_MAC_MIN_WORK, accelerated_mac, mac

requires_numba = pytest.mark.skipif(
    not numba_available(), reason="the optional 'accel' extra is not installed"
)


def shape_sets(ndof: int, ma: int, mb: int, seed: int = 0):
    rng = np.random.default_rng(seed)
    return rng.standard_normal((ndof, ma)), rng.standard_normal((ndof, mb))


@pytest.fixture(autouse=True)
def unpinned_backend(monkeypatch):
    """Run each test against the backend the package would choose itself."""
    monkeypatch.delenv(accel_mac.BACKEND_ENV, raising=False)


# ------------------------------------------------------------ kernel parity


@pytest.mark.parametrize("backend", accel_mac.BACKENDS)
def test_backends_reproduce_the_generic_mac(backend):
    if backend == "numba" and not numba_available():
        pytest.skip("the optional 'accel' extra is not installed")
    a, b = shape_sets(400, 8, 6)
    np.testing.assert_allclose(
        mac_real_unweighted(a, b, backend=backend), mac(a, b), rtol=0.0, atol=1e-12
    )


@pytest.mark.parametrize("backend", accel_mac.BACKENDS)
def test_backends_reject_a_zero_norm_mode(backend):
    if backend == "numba" and not numba_available():
        pytest.skip("the optional 'accel' extra is not installed")
    a, b = shape_sets(300, 4, 4)
    a[:, 2] = 0.0
    with pytest.raises(ValueError, match="zero-norm mode shape"):
        mac_real_unweighted(a, b, backend=backend)


@pytest.mark.parametrize("backend", accel_mac.BACKENDS)
def test_backends_keep_the_defining_mac_properties(backend):
    """Self-correlation is 1 on the diagonal, symmetric, bounded, scale-free."""
    if backend == "numba" and not numba_available():
        pytest.skip("the optional 'accel' extra is not installed")
    a, _ = shape_sets(250, 5, 5, seed=4)
    automac = mac_real_unweighted(a, a, backend=backend)

    np.testing.assert_allclose(np.diag(automac), 1.0, rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(automac, automac.T, rtol=0.0, atol=1e-15)
    assert np.all((automac >= 0.0) & (automac <= 1.0))

    scaled = a * np.array([1.0, -3.0, 0.25, 1e4, -1e-3])
    np.testing.assert_allclose(
        mac_real_unweighted(a, scaled, backend=backend), automac, rtol=0.0, atol=1e-12
    )


@requires_numba
def test_the_two_backends_agree_with_each_other():
    a, b = shape_sets(2_000, 12, 9, seed=11)
    np.testing.assert_allclose(
        mac_real_unweighted(a, b, backend="numba"),
        mac_real_unweighted(a, b, backend="numpy"),
        rtol=0.0,
        atol=1e-12,
    )


# --------------------------------------------------------- backend selection


def test_resolve_backend_honors_an_explicit_request():
    assert resolve_backend("numpy") == "numpy"
    assert resolve_backend("numba") == "numba"


def test_resolve_backend_reads_the_environment(monkeypatch):
    monkeypatch.setenv(accel_mac.BACKEND_ENV, "numpy")
    assert resolve_backend() == "numpy"


def test_resolve_backend_rejects_an_unknown_name():
    with pytest.raises(ValueError, match="unknown MAC backend"):
        resolve_backend("cuda")


def test_auto_selection_names_a_real_backend_and_is_cached(monkeypatch):
    monkeypatch.setattr(accel_mac, "_measured_backend", None)
    chosen = resolve_backend()
    assert chosen in accel_mac.BACKENDS
    assert accel_mac._measured_backend == chosen

    monkeypatch.setattr(
        accel_mac, "_faster_backend", lambda: pytest.fail("re-measured a cached choice")
    )
    assert resolve_backend() == chosen


def test_auto_selection_falls_back_to_numpy_without_numba(monkeypatch):
    monkeypatch.setattr(accel_mac, "_compiled_numba_kernel", lambda: None)
    assert accel_mac._faster_backend() == "numpy"


def test_requesting_numba_without_the_extra_explains_the_install(monkeypatch):
    monkeypatch.setattr(accel_mac, "_compiled_numba_kernel", lambda: None)
    with pytest.raises(ImportError, match=r"openfemlab\[accel\]"):
        mac_real_unweighted(*shape_sets(50, 2, 2), backend="numba")


# ---------------------------------------------------------------- dispatch


def test_small_problems_stay_on_the_generic_route():
    a, b = shape_sets(40, 3, 3)
    assert a.shape[0] * a.shape[1] * b.shape[1] < ACCEL_MAC_MIN_WORK
    assert accelerated_mac(a, b, None) is None


def test_weighted_and_non_float64_correlations_stay_on_the_generic_route():
    ndof, modes = 4_000, 20
    a, b = shape_sets(ndof, modes, modes)
    assert ndof * modes * modes >= ACCEL_MAC_MIN_WORK

    assert accelerated_mac(a, b, np.ones(ndof)) is None
    assert accelerated_mac(a.astype(np.float32), b.astype(np.float32), None) is None
    complex_a = a.astype(np.complex128)
    assert accelerated_mac(complex_a, b.astype(np.complex128), None) is None


@requires_numba
def test_a_large_real_correlation_is_dispatched_to_the_accel_layer():
    a, b = shape_sets(4_000, 20, 20, seed=5)
    dispatched = accelerated_mac(a, b, None)
    assert dispatched is not None
    np.testing.assert_allclose(dispatched, mac(a, b), rtol=0.0, atol=1e-12)


@pytest.mark.parametrize("backend", accel_mac.BACKENDS)
def test_mac_is_unchanged_by_the_backend_in_use(monkeypatch, backend):
    """The public result must not depend on which kernel the dispatch picked."""
    if backend == "numba" and not numba_available():
        pytest.skip("the optional 'accel' extra is not installed")
    a, b = shape_sets(4_000, 20, 18, seed=7)
    cross = a.T @ b
    expected = np.clip(
        cross * cross / np.outer(np.sum(a * a, axis=0), np.sum(b * b, axis=0)), 0.0, 1.0
    )

    monkeypatch.setenv(accel_mac.BACKEND_ENV, backend)
    np.testing.assert_allclose(mac(a, b), expected, rtol=0.0, atol=1e-12)


def test_dispatch_preserves_the_zero_norm_failure():
    a, b = shape_sets(4_000, 20, 20, seed=9)
    a[:, 0] = 0.0
    with pytest.raises(ValueError, match="zero-norm mode shape"):
        mac(a, b)
