"""Optional accelerated kernels (Numba JIT when installed).

Install with ``pip install 'openfemlab[accel]'``. Pure NumPy fallbacks keep
behavior identical when Numba is absent.
"""

from __future__ import annotations

from .mac import mac_real_unweighted, numba_available

__all__ = ["mac_real_unweighted", "numba_available"]
