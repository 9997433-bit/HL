"""Numba-accelerated MAC for real, unweighted shape matrices."""

from __future__ import annotations

import numpy as np

__all__ = ["mac_real_unweighted", "numba_available"]

_NUMBA_READY: bool | None = None
_MAC_NUMBA = None


def numba_available() -> bool:
    """Return True when Numba can compile the MAC kernel."""
    global _NUMBA_READY
    if _NUMBA_READY is None:
        try:
            import numba  # noqa: F401

            _NUMBA_READY = True
        except ImportError:
            _NUMBA_READY = False
    return _NUMBA_READY


def mac_real_unweighted(
    shapes_a: np.ndarray,
    shapes_b: np.ndarray,
) -> np.ndarray:
    """MAC matrix for real ``(ndof, ma)`` and ``(ndof, mb)`` without weighting."""
    a = np.ascontiguousarray(np.asarray(shapes_a, dtype=np.float64))
    b = np.ascontiguousarray(np.asarray(shapes_b, dtype=np.float64))
    if numba_available():
        return _get_mac_numba()(a, b)
    return _mac_numpy(a, b)


def _mac_numpy(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    cross = a.T @ b
    norm_a = np.sum(a * a, axis=0)
    norm_b = np.sum(b * b, axis=0)
    denom = np.outer(norm_a, norm_b)
    if np.any(denom <= 0.0):
        raise ValueError("zero-norm mode shape encountered")
    return np.clip((cross * cross) / denom, 0.0, 1.0)


def _get_mac_numba():
    global _MAC_NUMBA
    if _MAC_NUMBA is None:
        import numba as nb

        @nb.njit(cache=True, fastmath=True)
        def _kernel(a: np.ndarray, b: np.ndarray) -> np.ndarray:
            ndof, ma = a.shape
            mb = b.shape[1]
            out = np.empty((ma, mb), dtype=np.float64)
            norm_a = np.empty(ma, dtype=np.float64)
            norm_b = np.empty(mb, dtype=np.float64)
            for i in range(ma):
                s = 0.0
                for d in range(ndof):
                    s += a[d, i] * a[d, i]
                norm_a[i] = s
            for j in range(mb):
                s = 0.0
                for d in range(ndof):
                    s += b[d, j] * b[d, j]
                norm_b[j] = s
            for i in range(ma):
                for j in range(mb):
                    if norm_a[i] <= 0.0 or norm_b[j] <= 0.0:
                        raise ValueError("zero-norm mode shape encountered")
                    cross = 0.0
                    for d in range(ndof):
                        cross += a[d, i] * b[d, j]
                    value = (cross * cross) / (norm_a[i] * norm_b[j])
                    if value < 0.0:
                        value = 0.0
                    elif value > 1.0:
                        value = 1.0
                    out[i, j] = value
            return out

        _MAC_NUMBA = _kernel
    return _MAC_NUMBA
