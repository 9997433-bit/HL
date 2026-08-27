"""SSI-COV kernel — lagged output covariances and subspace identification.

Covariance-driven stochastic subspace identification (Peeters & De Roeck,
1999) estimates a discrete state-space model from output-only time histories
without measured excitation.  The estimator forms past/future output block
Hankel matrices and applies a subspace projection; for long stationary
records this is equivalent to the covariance Toeplitz layout while remaining
numerically stable on synthetic and measured data.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import numpy.typing as npt

from ..exceptions import MPEError
from .lscf import _classify
from .types import MPEResult, PoleEstimate, StabilizationDiagram

__all__ = [
    "sample_output_covariances",
    "identify_ssi_cov_order",
    "ssi_cov_diagram",
    "ssi_cov_extract",
]

MAX_DAMPING_RATIO = 0.2
MIN_FREQUENCY_HZ = 0.05


def sample_output_covariances(
    responses: npt.NDArray[np.floating],
    max_lag: int,
) -> tuple[npt.NDArray[np.float64], ...]:
    """Sample lagged output covariances ``R_k = E[y(t+k) y(t)^T]``."""
    data = np.asarray(responses, dtype=float)
    if data.ndim != 2:
        raise MPEError(f"responses must be 2-D (samples, channels), got shape {data.shape}")
    samples, _channels = data.shape
    if samples < max_lag + 2:
        raise MPEError(
            f"need at least {max_lag + 2} samples for block_rows={max_lag}, got {samples}"
        )
    centered = data - np.mean(data, axis=0, keepdims=True)
    covs: list[npt.NDArray[np.float64]] = []
    for lag in range(max_lag + 1):
        if lag == 0:
            covs.append((centered.T @ centered) / samples)
        else:
            block = centered[lag:]
            past = centered[:-lag]
            covs.append((block.T @ past) / (samples - lag))
    return tuple(covs)


def _output_hankel_blocks(
    responses: npt.NDArray[np.float64], block_rows: int
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    samples, channels = responses.shape
    columns = samples - 2 * block_rows + 1
    if columns < block_rows:
        raise MPEError(
            f"need more samples for block_rows={block_rows}: have {samples}, "
            f"need at least {2 * block_rows + block_rows - 1}"
        )
    centered = responses - np.mean(responses, axis=0, keepdims=True)
    scale = 1.0 / np.sqrt(columns)
    past = np.empty((block_rows * channels, columns), dtype=float)
    future = np.empty((block_rows * channels, columns), dtype=float)
    for column in range(columns):
        for row in range(block_rows):
            past[row * channels : (row + 1) * channels, column] = centered[
                column + block_rows - 1 - row
            ]
            future[row * channels : (row + 1) * channels, column] = centered[
                column + 2 * block_rows - 1 - row
            ]
    return past * scale, future * scale


def _discrete_pole_to_modal(z: complex, dt: float) -> tuple[float, float, complex]:
    if abs(z) < 1e-12 or not np.isfinite(z.real) or not np.isfinite(z.imag):
        return 0.0, 1.0, 0.0 + 0.0j
    if abs(z.imag) < 1e-12 and 0.0 < z.real < 1.0:
        return 0.0, 1.0, np.log(z.real) / dt
    s = np.log(z) / dt
    omega = abs(s)
    if omega < 1e-12:
        return 0.0, 1.0, s
    frequency_hz = float(abs(np.imag(s)) / (2.0 * np.pi))
    damping_ratio = float(max(0.0, -np.real(s) / omega))
    return frequency_hz, damping_ratio, s


def _physical_pole(frequency_hz: float, damping_ratio: float, nyquist: float) -> bool:
    return (
        MIN_FREQUENCY_HZ <= frequency_hz <= nyquist
        and 0.0 <= damping_ratio <= MAX_DAMPING_RATIO
        and np.isfinite(frequency_hz)
        and np.isfinite(damping_ratio)
    )


def identify_ssi_cov_order(
    responses: npt.NDArray[np.floating],
    sampling_rate_hz: float,
    order: int,
    *,
    block_rows: int,
) -> tuple[PoleEstimate, ...]:
    """Identify poles at one state-space order from output covariances."""
    if order < 2:
        raise MPEError(f"model order must be >= 2, got {order}")
    if block_rows < order + 1:
        raise MPEError(
            f"block_rows must exceed the model order ({order}); got {block_rows}"
        )
    if sampling_rate_hz <= 0.0:
        raise MPEError(f"sampling_rate_hz must be positive, got {sampling_rate_hz}")

    data = np.asarray(responses, dtype=float)
    past, future = _output_hankel_blocks(data, block_rows)
    combined = np.vstack([past, future])
    _u, singular, _vt = np.linalg.svd(combined, full_matrices=False)
    rank = min(order, singular.size)
    if rank < order:
        raise MPEError(
            f"the output Hankel matrix has rank {rank}, cannot fit order {order}"
        )
    scale = np.sqrt(np.maximum(singular[:rank], 0.0))
    observability = _u[:, :rank] * scale
    channels = int(data.shape[1])
    if observability.shape[0] < 2 * channels:
        raise MPEError("block_rows is too small for the channel count")

    try:
        gamma_minus = observability[: (block_rows - 1) * channels, :]
        gamma_plus = observability[channels : block_rows * channels, :]
        state_matrix = np.linalg.lstsq(gamma_minus, gamma_plus, rcond=None)[0]
    except np.linalg.LinAlgError as exc:  # pragma: no cover
        raise MPEError(f"state matrix identification failed at order {order}") from exc

    nyquist = 0.45 * sampling_rate_hz
    dt = 1.0 / sampling_rate_hz
    values, vectors = np.linalg.eig(state_matrix)
    estimates: list[PoleEstimate] = []
    seen: set[tuple[float, float]] = set()
    for index, value in enumerate(values):
        if abs(np.imag(value)) < 1e-8:
            continue
        frequency_hz, damping_ratio, pole = _discrete_pole_to_modal(value, dt)
        if not _physical_pole(frequency_hz, damping_ratio, nyquist):
            continue
        key = (round(frequency_hz, 6), round(damping_ratio, 6))
        if key in seen:
            continue
        seen.add(key)
        vector = vectors[:, index]
        participation = observability[:channels, :] @ vector
        norm = np.linalg.norm(participation)
        if norm > 0.0:
            participation = participation / norm
        estimates.append(
            PoleEstimate(
                frequency_hz=frequency_hz,
                damping_ratio=damping_ratio,
                pole=pole,
                order=order,
                participation=participation.astype(np.complex128),
                label="new",
            )
        )
    estimates.sort(key=lambda item: (item.frequency_hz, item.damping_ratio))
    return tuple(estimates)


def ssi_cov_diagram(
    responses: npt.NDArray[np.floating],
    sampling_rate_hz: float,
    orders: Sequence[int],
    *,
    block_rows: int | None = None,
    freq_tol: float = 0.02,
    damp_tol: float = 0.10,
    mac_tol: float = 0.90,
) -> StabilizationDiagram:
    """Build a stabilization diagram over SSI-COV model orders."""
    requested = [int(value) for value in orders]
    if not requested:
        raise MPEError("a stabilization diagram needs at least one model order")
    if sorted(set(requested)) != requested:
        raise MPEError(f"the model orders must be strictly increasing, got {requested}")

    samples, channels = np.asarray(responses, dtype=float).shape
    default_rows = max(2 * max(requested) + 2, 20)
    rows = int(default_rows if block_rows is None else block_rows)
    if rows < max(requested) + 1:
        raise MPEError(
            f"block_rows={rows} must exceed the largest order {max(requested)}"
        )
    min_samples = 2 * rows + rows - 1
    if samples < min_samples:
        raise MPEError(
            f"need at least {min_samples} samples for block_rows={rows}, got {samples}"
        )

    levels: list[tuple[PoleEstimate, ...]] = []
    links: list[tuple[int, ...]] = []
    previous: tuple[PoleEstimate, ...] = ()
    for order in requested:
        fitted = identify_ssi_cov_order(
            responses, sampling_rate_hz, order, block_rows=rows
        )
        labelled: list[PoleEstimate] = []
        parents: list[int] = []
        for pole in fitted:
            label, parent = _classify(pole, previous, freq_tol, damp_tol, mac_tol)
            labelled.append(
                PoleEstimate(
                    frequency_hz=pole.frequency_hz,
                    damping_ratio=pole.damping_ratio,
                    pole=pole.pole,
                    order=pole.order,
                    participation=pole.participation,
                    label=label,
                )
            )
            parents.append(parent if levels else -1)
        levels.append(tuple(labelled))
        links.append(tuple(parents))
        previous = tuple(labelled)

    return StabilizationDiagram(
        orders=tuple(requested),
        poles=tuple(levels),
        settings={
            "method": "SSI-COV",
            "block_rows": rows,
            "links": tuple(links),
            "tolerances": {
                "freq_tol": freq_tol,
                "damp_tol": damp_tol,
                "mac_tol": mac_tol,
            },
        },
    )


def ssi_cov_extract(
    responses: npt.NDArray[np.floating],
    sampling_rate_hz: float,
    orders: Sequence[int],
    *,
    block_rows: int | None = None,
    min_count: int = 3,
    freq_tol: float = 0.02,
    damp_tol: float = 0.10,
    mac_tol: float = 0.90,
) -> MPEResult:
    """One-call SSI-COV driver: diagram, pole pick, channel-space shapes."""
    diagram = ssi_cov_diagram(
        responses,
        sampling_rate_hz,
        orders,
        block_rows=block_rows,
        freq_tol=freq_tol,
        damp_tol=damp_tol,
        mac_tol=mac_tol,
    )
    picked = diagram.select(min_count=min_count)
    channels = int(np.asarray(responses).shape[1])
    frequencies = np.array([pole.frequency_hz for pole in picked], dtype=float)
    dampings = np.array([pole.damping_ratio for pole in picked], dtype=float)
    poles = np.array([pole.pole for pole in picked], dtype=np.complex128)
    shapes = np.zeros((channels, picked.__len__()), dtype=np.complex128)
    participation = np.zeros((channels, picked.__len__()), dtype=np.complex128)
    for index, pole in enumerate(picked):
        vector = np.asarray(pole.participation, dtype=np.complex128).reshape(-1)
        shapes[:, index] = vector
        participation[:, index] = vector
    frac = np.ones(channels, dtype=float)
    return MPEResult(
        frequencies_hz=frequencies,
        damping_ratios=dampings,
        poles=poles,
        shapes=shapes,
        participation=participation,
        frac=frac,
        diagnostics={
            "method": "SSI-COV",
            "orders": tuple(int(value) for value in orders),
            "block_rows": diagram.settings.get("block_rows"),
            "tolerances": diagram.settings.get("tolerances", {}),
            "min_count": min_count,
        },
    )
