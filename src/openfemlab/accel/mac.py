"""Specialized kernels for the real, unweighted MAC matrix.

:func:`openfemlab.correlation.mac.mac` is deliberately generic: it accepts
complex shapes and an optional DOF weighting, so it conjugates its inputs and
forms weighted ``(ndof, m)`` blocks that a real, unweighted correlation never
needs. This module holds the specialization of that one case in two
interchangeable backends:

``numpy``
    ``Φ_aᵀ Φ_b`` through the BLAS ``dgemm`` that NumPy is linked against, plus
    one reduction pass per shape set for the column norms.
``numba``
    :func:`_mac_real_unweighted`, compiled by :mod:`numba` (the optional
    dependency installed with ``pip install 'openfemlab[accel]'``). It walks
    the DOF rows once and accumulates the cross terms and both norms together,
    so it never materializes an ``(ndof, m)`` temporary.

Which of the two is faster is a property of the deployment rather than of the
algorithm, because the NumPy backend inherits whatever BLAS the local NumPy was
built against: against an optimized multi-threaded BLAS the scalar kernel
cannot compete, while against a reference BLAS the fused pass wins. Selecting
one at import time would therefore make ``mac`` slower on some installs, so
:func:`resolve_backend` measures both on a small probe once per process and
keeps the winner. Set ``OPENFEMLAB_ACCEL_MAC`` to ``numpy`` or ``numba`` to
pin a backend and skip that measurement.
"""

from __future__ import annotations

import importlib.util
import os
import time
from typing import Any

import numpy as np

__all__ = [
    "BACKENDS",
    "BACKEND_ENV",
    "mac_real_unweighted",
    "numba_available",
    "reset_backend",
    "resolve_backend",
]

#: Environment variable pinning the backend; unset means "measure and choose".
BACKEND_ENV = "OPENFEMLAB_ACCEL_MAC"

#: Backends :func:`mac_real_unweighted` can dispatch to.
BACKENDS = ("numpy", "numba")

#: Probe used by the one-off backend measurement, sized like the smallest
#: problem :mod:`openfemlab.correlation.mac` routes here.
_PROBE_DOFS = 8192
_PROBE_MODES = 12
_PROBE_REPEATS = 3

_numba_installed: bool | None = None
_numba_kernel: Any = None
_measured_backend: str | None = None


def numba_available() -> bool:
    """Whether the optional :mod:`numba` dependency is installed.

    Checked through the import system rather than by importing Numba, which
    costs about a second and is wasted on callers that only ask.
    """
    global _numba_installed
    if _numba_installed is None:
        _numba_installed = importlib.util.find_spec("numba") is not None
    return _numba_installed


def reset_backend() -> None:
    """Forget the measured backend so the next call re-runs the probe."""
    global _measured_backend
    _measured_backend = None


def resolve_backend(backend: str | None = None) -> str:
    """Return the backend name to use, measuring the two once if needed.

    ``backend`` (or ``OPENFEMLAB_ACCEL_MAC``) pins the choice; ``None`` or
    ``"auto"`` runs :func:`_faster_backend` on first use and caches its answer
    for the rest of the process.
    """
    requested = backend or os.environ.get(BACKEND_ENV) or "auto"
    if requested not in (*BACKENDS, "auto"):
        raise ValueError(
            f"unknown MAC backend {requested!r}; expected one of "
            f"{', '.join((*BACKENDS, 'auto'))}"
        )
    if requested != "auto":
        return requested
    global _measured_backend
    if _measured_backend is None:
        _measured_backend = _faster_backend()
    return _measured_backend


def mac_real_unweighted(
    shapes_a: np.ndarray,
    shapes_b: np.ndarray,
    *,
    backend: str | None = None,
) -> np.ndarray:
    """MAC matrix of real ``(ndof, ma)`` and ``(ndof, mb)`` shape sets.

    Equivalent to ``mac(shapes_a, shapes_b)`` with no weighting, including its
    ``ValueError`` on a zero-norm mode. The two backends differ only in
    floating-point summation order, so their results agree to rounding rather
    than bit for bit.
    """
    if resolve_backend(backend) == "numba":
        kernel = _require_numba_kernel()
        return kernel(
            np.ascontiguousarray(shapes_a, dtype=np.float64),
            np.ascontiguousarray(shapes_b, dtype=np.float64),
        )
    return _mac_numpy(np.asarray(shapes_a), np.asarray(shapes_b))


def _mac_numpy(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """BLAS route: one ``dgemm`` for the cross terms, one pass per norm."""
    cross = a.T @ b
    norm_a = np.einsum("ij,ij->j", a, a)
    norm_b = np.einsum("ij,ij->j", b, b)
    denominator = np.outer(norm_a, norm_b)
    if np.any(denominator <= 0.0):
        raise ValueError("zero-norm mode shape encountered")
    return np.clip(cross * cross / denominator, 0.0, 1.0)


def _mac_real_unweighted(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Fused kernel: accumulate cross terms and both norms in one DOF sweep.

    Compiled by :func:`_require_numba_kernel`; the DOF index is the *outer*
    loop so that every inner iteration reads along a contiguous row of the
    ``(ndof, m)`` inputs. Running this unaccelerated is orders of magnitude
    slower than :func:`_mac_numpy` and only the compiled form is dispatched to.
    """
    ndof, ma = a.shape
    mb = b.shape[1]
    cross = np.zeros((ma, mb))
    norm_a = np.zeros(ma)
    norm_b = np.zeros(mb)
    for d in range(ndof):
        for i in range(ma):
            value = a[d, i]
            norm_a[i] += value * value
            for j in range(mb):
                cross[i, j] += value * b[d, j]
        for j in range(mb):
            value = b[d, j]
            norm_b[j] += value * value

    for i in range(ma):
        if norm_a[i] <= 0.0:
            raise ValueError("zero-norm mode shape encountered")
    for j in range(mb):
        if norm_b[j] <= 0.0:
            raise ValueError("zero-norm mode shape encountered")

    out = np.empty((ma, mb))
    for i in range(ma):
        for j in range(mb):
            value = cross[i, j] * cross[i, j] / (norm_a[i] * norm_b[j])
            out[i, j] = min(max(value, 0.0), 1.0)
    return out


def _compiled_numba_kernel() -> Any:
    """Compile :func:`_mac_real_unweighted` once, or return ``None``.

    ``fastmath`` stays off on purpose: it lets the compiler reassociate the
    accumulations, which would make the result depend on the SIMD width of the
    host and cost this package the reproducibility the rest of it promises.
    """
    global _numba_kernel
    if _numba_kernel is None:
        try:
            import numba

            _numba_kernel = numba.njit(cache=True)(_mac_real_unweighted)
        except Exception:  # pragma: no cover - a broken optional accelerator
            _numba_kernel = False
    return _numba_kernel or None


def _require_numba_kernel() -> Any:
    kernel = _compiled_numba_kernel()
    if kernel is None:
        raise ImportError(
            "the 'numba' MAC backend needs the optional Numba dependency; "
            "install it with: pip install 'openfemlab[accel]'"
        )
    return kernel


def _faster_backend() -> str:
    """Time both backends on a fixed probe and name the faster one.

    Numba's compilation is paid before the clock starts, so what is compared
    is steady-state throughput; a caller who cannot afford the one-off compile
    pins ``OPENFEMLAB_ACCEL_MAC=numpy`` instead.
    """
    kernel = _compiled_numba_kernel()
    if kernel is None:
        return "numpy"
    generator = np.random.default_rng(0)
    a = generator.standard_normal((_PROBE_DOFS, _PROBE_MODES))
    b = generator.standard_normal((_PROBE_DOFS, _PROBE_MODES))
    numba_seconds = _best_of(lambda: kernel(a, b))
    numpy_seconds = _best_of(lambda: _mac_numpy(a, b))
    return "numba" if numba_seconds < numpy_seconds else "numpy"


def _best_of(call: Any) -> float:
    """Fastest of :data:`_PROBE_REPEATS` timed runs, after one warm-up."""
    call()
    best = float("inf")
    for _ in range(_PROBE_REPEATS):
        started = time.perf_counter()
        call()
        best = min(best, time.perf_counter() - started)
    return best
