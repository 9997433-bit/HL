"""Deterministic stimuli described by EBU Tech 3341 and Tech 3342."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

SAMPLE_RATE = 48_000
TONE_FREQUENCY_HZ = 1_000.0


@dataclass(frozen=True)
class LoudnessVector:
    case_id: str
    description: str
    segments: tuple[tuple[float, float], ...]
    expected_integrated_lufs: float


@dataclass(frozen=True)
class LraVector:
    case_id: str
    description: str
    segments: tuple[tuple[float, float], ...]
    expected_lra_lu: float


TECH_3341_VECTORS = (
    LoudnessVector(
        "3341-1",
        "20 s stereo 1 kHz sine, -23 dBFS peak per channel",
        ((20.0, -23.0),),
        -23.0,
    ),
    LoudnessVector(
        "3341-2",
        "20 s stereo 1 kHz sine, -33 dBFS peak per channel",
        ((20.0, -33.0),),
        -33.0,
    ),
    LoudnessVector(
        "3341-3",
        "10 s at -36 dBFS, 60 s at -23 dBFS, 10 s at -36 dBFS",
        ((10.0, -36.0), (60.0, -23.0), (10.0, -36.0)),
        -23.0,
    ),
)

TECH_3342_VECTORS = (
    LraVector(
        "3342-1",
        "20 s at -20 dBFS followed by 20 s at -30 dBFS",
        ((20.0, -20.0), (20.0, -30.0)),
        10.0,
    ),
    # Skeleton entries from Tech 3342 Table 1. Enable as product-meter
    # integration expands; the synthetic generator already supports them.
    LraVector(
        "3342-2",
        "20 s at -20 dBFS followed by 20 s at -15 dBFS",
        ((20.0, -20.0), (20.0, -15.0)),
        5.0,
    ),
    LraVector(
        "3342-3",
        "20 s at -40 dBFS followed by 20 s at -20 dBFS",
        ((20.0, -40.0), (20.0, -20.0)),
        20.0,
    ),
)


def synthesize_segments(
    segments: tuple[tuple[float, float], ...],
    *,
    sample_rate: int = SAMPLE_RATE,
) -> np.ndarray:
    """Synthesize in-phase stereo sine segments as ``float32`` samples."""
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    parts: list[np.ndarray] = []
    phase_samples = 0
    for duration_seconds, peak_dbfs in segments:
        frame_count = round(duration_seconds * sample_rate)
        if frame_count <= 0:
            raise ValueError("segment durations must be positive")
        sample_numbers = np.arange(
            phase_samples,
            phase_samples + frame_count,
            dtype=np.float64,
        )
        amplitude = 10.0 ** (peak_dbfs / 20.0)
        mono = amplitude * np.sin(
            2.0 * np.pi * TONE_FREQUENCY_HZ * sample_numbers / sample_rate
        )
        parts.append(np.repeat(mono[:, np.newaxis], 2, axis=1).astype(np.float32))
        phase_samples += frame_count
    return np.concatenate(parts, axis=0)
