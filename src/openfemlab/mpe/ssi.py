"""Covariance-driven stochastic subspace identification (SSI-COV).

This module reserves the public API for operational modal analysis from
output-only time histories.  SSI-COV is distinct from the frequency-response
LSCF implementation in :mod:`openfemlab.mpe.lscf`: it estimates a state-space
model from lagged output covariances and therefore does not require a measured
excitation.

The numerical backend is intentionally not included yet.  Keeping the stub
public lets callers design integrations against a stable signature without
mistaking an incomplete estimator for a production implementation.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .types import MPEResult

__all__ = ["ssi_cov"]


def ssi_cov(
    responses: Any,
    sampling_rate_hz: float,
    orders: Sequence[int],
    *,
    block_rows: int | None = None,
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
        Number of block-Toeplitz rows.  ``None`` will select a data-dependent
        default when the estimator is implemented.

    Returns
    -------
    MPEResult
        Identified frequencies, damping ratios, and channel-space mode shapes.

    Raises
    ------
    NotImplementedError
        Always.  The signature is reserved, but the SSI-COV numerical backend
        has not landed.
    """
    raise NotImplementedError(
        "SSI-COV operational modal analysis is not implemented yet; "
        "use fit_lscf() for frequency-response-based modal extraction"
    )
