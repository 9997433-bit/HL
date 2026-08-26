"""Independent ITU-R BS.1770 / EBU R128 measurement oracle.

This module intentionally lives in ``tools`` rather than the application.  It
gives compliance tests a small, inspectable reference implementation while the
production loudness meter is developed.  Audio is expected as float samples in
``(frames, channels)`` order.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.signal import sosfilt

ABSOLUTE_GATE_LUFS = -70.0
LOUDNESS_OFFSET = -0.691


def _k_weighting_sos(sample_rate: int) -> np.ndarray:
    """Return the two BS.1770 K-weighting biquads for ``sample_rate``."""
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")

    shelf_frequency = 1681.974450955533
    shelf_gain_db = 3.999843853973347
    shelf_q = 0.7071752369554196
    k = math.tan(math.pi * shelf_frequency / sample_rate)
    vh = 10.0 ** (shelf_gain_db / 20.0)
    vb = vh**0.4996667741545416
    denominator = 1.0 + k / shelf_q + k * k
    shelf = np.array(
        [
            (vh + vb * k / shelf_q + k * k) / denominator,
            2.0 * (k * k - vh) / denominator,
            (vh - vb * k / shelf_q + k * k) / denominator,
            1.0,
            2.0 * (k * k - 1.0) / denominator,
            (1.0 - k / shelf_q + k * k) / denominator,
        ],
        dtype=np.float64,
    )

    high_pass_frequency = 38.13547087602444
    high_pass_q = 0.5003270373238773
    k = math.tan(math.pi * high_pass_frequency / sample_rate)
    denominator = 1.0 + k / high_pass_q + k * k
    high_pass = np.array(
        [
            1.0 / denominator,
            -2.0 / denominator,
            1.0 / denominator,
            1.0,
            2.0 * (k * k - 1.0) / denominator,
            (1.0 - k / high_pass_q + k * k) / denominator,
        ],
        dtype=np.float64,
    )
    return np.stack((shelf, high_pass))


def _as_audio(audio: np.ndarray) -> np.ndarray:
    samples = np.asarray(audio, dtype=np.float64)
    if samples.ndim == 1:
        samples = samples[:, np.newaxis]
    if samples.ndim != 2:
        raise ValueError(f"expected (frames, channels), got {samples.shape}")
    if samples.shape[1] < 1 or samples.shape[1] > 6:
        raise ValueError("reference meter supports one to six channels")
    if not np.all(np.isfinite(samples)):
        raise ValueError("audio contains non-finite samples")
    return samples


def _channel_weights(channels: int) -> np.ndarray:
    # BS.1770 order: L, R, C, LFE, Ls, Rs. LFE does not contribute.
    if channels <= 3:
        return np.ones(channels, dtype=np.float64)
    weights = np.ones(channels, dtype=np.float64)
    weights[3] = 0.0
    if channels > 4:
        weights[4:] = 1.41
    return weights


def _weighted_frame_energy(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    filtered = sosfilt(_k_weighting_sos(sample_rate), _as_audio(audio), axis=0)
    return np.square(filtered, dtype=np.float64) @ _channel_weights(filtered.shape[1])


def _window_powers(
    frame_energy: np.ndarray,
    sample_rate: int,
    window_seconds: float,
    step_seconds: float,
) -> np.ndarray:
    window = round(window_seconds * sample_rate)
    step = round(step_seconds * sample_rate)
    if frame_energy.size < window:
        return np.empty(0, dtype=np.float64)
    starts = np.arange(0, frame_energy.size - window + 1, step, dtype=np.int64)
    cumulative = np.concatenate(([0.0], np.cumsum(frame_energy, dtype=np.float64)))
    return (cumulative[starts + window] - cumulative[starts]) / window


def _power_to_loudness(power: np.ndarray | float) -> np.ndarray | float:
    values = np.asarray(power, dtype=np.float64)
    result = LOUDNESS_OFFSET + 10.0 * np.log10(np.maximum(values, 1e-300))
    return float(result) if result.ndim == 0 else result


def integrated_loudness(audio: np.ndarray, sample_rate: int) -> float:
    """Measure gated programme loudness in LUFS."""
    powers = _window_powers(
        _weighted_frame_energy(audio, sample_rate),
        sample_rate,
        window_seconds=0.4,
        step_seconds=0.1,
    )
    if powers.size == 0:
        raise ValueError("integrated loudness requires at least 400 ms of audio")

    loudness = np.asarray(_power_to_loudness(powers))
    absolute = powers[loudness >= ABSOLUTE_GATE_LUFS]
    if absolute.size == 0:
        return -math.inf
    relative_gate = float(_power_to_loudness(np.mean(absolute))) - 10.0
    gated = powers[(loudness >= ABSOLUTE_GATE_LUFS) & (loudness >= relative_gate)]
    return float(_power_to_loudness(np.mean(gated))) if gated.size else -math.inf


def maximum_window_loudness(
    audio: np.ndarray,
    sample_rate: int,
    *,
    window_seconds: float,
    step_seconds: float = 0.1,
) -> float:
    """Return the maximum ungated window loudness (M or S)."""
    powers = _window_powers(
        _weighted_frame_energy(audio, sample_rate),
        sample_rate,
        window_seconds=window_seconds,
        step_seconds=step_seconds,
    )
    if powers.size == 0:
        raise ValueError(f"measurement requires at least {window_seconds:g} s of audio")
    return float(np.max(_power_to_loudness(powers)))


def loudness_range(audio: np.ndarray, sample_rate: int) -> float:
    """Measure LRA using the EBU Tech 3342 short-term distribution."""
    powers = _window_powers(
        _weighted_frame_energy(audio, sample_rate),
        sample_rate,
        window_seconds=3.0,
        step_seconds=1.0,
    )
    if powers.size == 0:
        raise ValueError("LRA requires at least 3 seconds of audio")

    loudness = np.asarray(_power_to_loudness(powers))
    absolute = powers[loudness >= ABSOLUTE_GATE_LUFS]
    if absolute.size == 0:
        return 0.0
    relative_gate = float(_power_to_loudness(np.mean(absolute))) - 20.0
    gated_loudness = loudness[
        (loudness >= ABSOLUTE_GATE_LUFS) & (loudness >= relative_gate)
    ]
    if gated_loudness.size < 2:
        return 0.0
    low, high = np.percentile(gated_loudness, (10.0, 95.0))
    return float(high - low)
