"""Optional accelerated kernels for hot correlation paths.

Install the extra with ``pip install 'openfemlab[accel]'``. Nothing here is
required: every kernel has a NumPy route that produces the same result, and
:mod:`openfemlab.correlation` falls back to its generic implementation when
the extra is absent. See :mod:`openfemlab.accel.mac` for how the backend is
chosen.
"""

from __future__ import annotations

from openfemlab.accel.mac import (
    BACKEND_ENV,
    BACKENDS,
    mac_real_unweighted,
    numba_available,
    reset_backend,
    resolve_backend,
)

__all__ = [
    "BACKENDS",
    "BACKEND_ENV",
    "mac_real_unweighted",
    "numba_available",
    "reset_backend",
    "resolve_backend",
]
