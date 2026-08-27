"""Deterministic test signals for the DSP suite.

Kept in a plain module rather than ``conftest.py`` so the generators can be
imported explicitly by name, and so this file does not compete with the
fixtures the core-engine tests define.
"""

from __future__ import annotations

import numpy as np

SR = 48_000


def sine(
    frequency: float,
    duration_s: float = 1.0,
    amplitude: float = 1.0,
    sample_rate: int = SR,
    phase: float = 0.0,
) -> np.ndarray:
    """Mono sine wave as float64."""
    t = np.arange(int(round(duration_s * sample_rate)), dtype=np.float64) / sample_rate
    return amplitude * np.sin(2.0 * np.pi * frequency * t + phase)


def bin_centered_frequency(target_hz: float, fft_size: int, sample_rate: int = SR) -> float:
    """Nearest frequency that lands exactly on an FFT bin.

    Off-bin tones lose up to ~1.4 dB to scalloping depending on the window, so
    amplitude-accuracy assertions have to sit on a bin to be about calibration
    rather than about the window's shape.
    """
    k = round(target_hz * fft_size / sample_rate)
    return k * sample_rate / fft_size


def white_noise(
    duration_s: float = 1.0,
    amplitude: float = 0.1,
    sample_rate: int = SR,
    seed: int = 12_345,
) -> np.ndarray:
    """Reproducible Gaussian noise."""
    rng = np.random.default_rng(seed)
    return amplitude * rng.standard_normal(int(round(duration_s * sample_rate)))


def stereo(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    """Stack two mono signals into a planar stereo buffer."""
    n = min(left.size, right.size)
    return np.stack([left[:n], right[:n]])


def chirp(
    f0: float,
    f1: float,
    duration_s: float = 1.0,
    amplitude: float = 0.5,
    sample_rate: int = SR,
) -> np.ndarray:
    """Linear frequency sweep, useful for checking time/frequency alignment."""
    t = np.arange(int(round(duration_s * sample_rate)), dtype=np.float64) / sample_rate
    rate = (f1 - f0) / max(duration_s, 1e-12)
    return amplitude * np.sin(2.0 * np.pi * (f0 * t + 0.5 * rate * t * t))


def impulse(length: int = 4096, position: int = 0, amplitude: float = 1.0) -> np.ndarray:
    """Unit impulse, for measuring a filter's response directly."""
    signal = np.zeros(int(length), dtype=np.float64)
    signal[int(position)] = amplitude
    return signal


def tone_burst(
    frequency: float,
    total_s: float,
    burst_start_s: float,
    burst_s: float,
    amplitude: float = 0.8,
    sample_rate: int = SR,
) -> np.ndarray:
    """Silence with a tone burst in the middle, for time-alignment checks."""
    signal = np.zeros(int(round(total_s * sample_rate)), dtype=np.float64)
    start = int(round(burst_start_s * sample_rate))
    burst = sine(frequency, burst_s, amplitude, sample_rate)
    signal[start : start + burst.size] = burst[: max(0, signal.size - start)]
    return signal
