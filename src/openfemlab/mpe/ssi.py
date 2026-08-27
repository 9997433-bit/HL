"""Covariance-driven stochastic subspace identification (SSI-COV).

Operational modal analysis from output-only time histories.  SSI-COV is
distinct from the frequency-response LSCF implementation in
:mod:`openfemlab.mpe.lscf`: it estimates a state-space model from lagged
output covariances and therefore does not require a measured excitation.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import numpy.typing as npt

from ..exceptions import MPEError
from .ssi_cov_kernel import ssi_cov_extract
from .types import MPEResult

__all__ = ["ssi_cov", "simulate_operational_response"]


def simulate_operational_response(
    frequencies_hz: Sequence[float],
    damping_ratios: Sequence[float],
    shapes: npt.NDArray[np.floating],
    *,
    sampling_rate_hz: float,
    samples: int,
    seed: int = 0,
) -> npt.NDArray[np.float64]:
    """Simulate band-limited ambient vibration for SSI oracle tests."""
    from scipy.signal import bilinear, lfilter

    freqs = [float(value) for value in frequencies_hz]
    dampings = [float(value) for value in damping_ratios]
    if len(freqs) != len(dampings):
        raise MPEError("frequencies_hz and damping_ratios must have the same length")
    matrix = np.asarray(shapes, dtype=float)
    if matrix.ndim != 2:
        raise MPEError(f"shapes must be 2-D (channels, modes), got shape {matrix.shape}")
    if matrix.shape[1] != len(freqs):
        raise MPEError(
            f"shapes has {matrix.shape[1]} mode columns but {len(freqs)} modes were given"
        )
    if samples < 32:
        raise MPEError(f"samples must be >= 32, got {samples}")
    if sampling_rate_hz <= 0.0:
        raise MPEError(f"sampling_rate_hz must be positive, got {sampling_rate_hz}")

    rng = np.random.default_rng(seed)
    channels, _modes = matrix.shape
    output = np.zeros((samples, channels), dtype=float)
    excitation = rng.normal(0.0, 1.0, size=samples)
    for mode, (frequency_hz, damping_ratio) in enumerate(zip(freqs, dampings, strict=True)):
        omega = 2.0 * np.pi * frequency_hz
        numerator = [0.0, 0.0, 1.0]
        denominator = [1.0, 2.0 * damping_ratio * omega, omega**2]
        b_coeff, a_coeff = bilinear(numerator, denominator, sampling_rate_hz)
        modal = lfilter(b_coeff, a_coeff, excitation)
        output += modal[:, None] * matrix[:, mode][None, :]
    return output


def ssi_cov(
    responses: Any,
    sampling_rate_hz: float,
    orders: Sequence[int],
    *,
    block_rows: int | None = None,
    min_count: int = 3,
    freq_tol: float = 0.02,
    damp_tol: float = 0.10,
    mac_tol: float = 0.90,
) -> MPEResult:
    """Estimate operational modes with covariance-driven SSI.

    Parameters
    ----------
    responses:
        Real output time histories shaped ``(samples, channels)``.
    sampling_rate_hz:
        Positive sample rate in hertz.
    orders:
        Increasing state-space model orders used to form a stabilization
        diagram.
    block_rows:
        Number of block-Toeplitz rows.  ``None`` selects a data-dependent
        default from the largest requested order.
    min_count:
        Minimum number of consecutive stable orders a pole must survive before
        it is picked from the stabilization diagram.
    freq_tol, damp_tol, mac_tol:
        Stabilization tolerances forwarded to :func:`ssi_cov_extract`.

    Returns
    -------
    MPEResult
        Identified frequencies, damping ratios, and channel-space mode shapes.
    """
    data = np.asarray(responses, dtype=float)
    if data.ndim != 2:
        raise MPEError(f"responses must be 2-D (samples, channels), got shape {data.shape}")
    if data.shape[0] < 32:
        raise MPEError(
            f"SSI-COV needs a longer record than {data.shape[0]} samples; "
            "use at least a few hundred for reliable pole picking"
        )
    return ssi_cov_extract(
        data,
        float(sampling_rate_hz),
        orders,
        block_rows=block_rows,
        min_count=min_count,
        freq_tol=freq_tol,
        damp_tol=damp_tol,
        mac_tol=mac_tol,
    )
