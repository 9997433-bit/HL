"""Deterministic stimuli described by EBU Tech 3341 and Tech 3342.

Every expected value here is derived from the standards rather than from any
meter. For a 1 kHz tone the K-weighting gain (+0.691 dB) cancels the BS.1770
calibration offset (-0.691 LU) exactly, so a stereo tone of peak amplitude
``a`` in both channels reads ``20*log10(a)`` LUFS: the -23 dBFS signal of
Tech 3341 test 1 must read -23.0 LUFS, and every level and gating case below
follows from summing the block powers by hand.

The vectors are grouped by what they exercise:

``TECH_3341_VECTORS``
    Programme loudness, including both gates.
``TECH_3341_CHANNEL_VECTORS``
    Channel weighting: surrounds count +1.5 dB, the LFE not at all.
``TECH_3341_TRUE_PEAK_VECTORS``
    Inter-sample peaks, the part of BS.1770-4 a sample-peak meter cannot see.
``TECH_3342_VECTORS``
    Loudness range.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

SAMPLE_RATE = 48_000
TONE_FREQUENCY_HZ = 1_000.0

#: Tech 3341 states +-0.1 LU on a loudness reading and Tech 3342 +-1 LU on a
#: loudness range. Its true-peak tolerance is asymmetric: a meter may under-read
#: by 0.4 dB or over-read by 0.2 dB.
TOLERANCE_LU = 0.1
LRA_TOLERANCE_LU = 1.0
TRUE_PEAK_MAX_UNDERREAD_DB = 0.4
TRUE_PEAK_MAX_OVERREAD_DB = 0.2

#: Level used to mean digital silence in a segment list.
SILENCE_DBFS = -math.inf


@dataclass(frozen=True)
class LoudnessVector:
    """A programme built from stereo tone segments, and what it must read."""

    case_id: str
    description: str
    segments: tuple[tuple[float, float], ...]
    expected_integrated_lufs: float
    tolerance_lu: float = TOLERANCE_LU


@dataclass(frozen=True)
class ChannelLoudnessVector:
    """A steady multichannel tone, for the channel-weighting rules."""

    case_id: str
    description: str
    levels_dbfs: tuple[float, ...]
    duration_s: float
    expected_integrated_lufs: float
    tolerance_lu: float = TOLERANCE_LU


@dataclass(frozen=True)
class TruePeakVector:
    """A tone whose peak falls between samples, and the dBTP it must read."""

    case_id: str
    description: str
    sample_rate: int
    frequency_hz: float
    amplitude_dbfs: float
    phase_degrees: float
    expected_dbtp: float
    expected_sample_peak_dbfs: float
    max_underread_db: float = TRUE_PEAK_MAX_UNDERREAD_DB
    max_overread_db: float = TRUE_PEAK_MAX_OVERREAD_DB

    @property
    def minimum_accepted_dbtp(self) -> float:
        return self.expected_dbtp - self.max_underread_db

    @property
    def maximum_accepted_dbtp(self) -> float:
        return self.expected_dbtp + self.max_overread_db


@dataclass(frozen=True)
class LraVector:
    case_id: str
    description: str
    segments: tuple[tuple[float, float], ...]
    expected_lra_lu: float
    tolerance_lu: float = LRA_TOLERANCE_LU


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
    LoudnessVector(
        "3341-4",
        "the same programme wrapped in 10 s of -72 dBFS: below the absolute gate",
        (
            (10.0, -72.0),
            (10.0, -36.0),
            (60.0, -23.0),
            (10.0, -36.0),
            (10.0, -72.0),
        ),
        -23.0,
    ),
    LoudnessVector(
        "3341-5",
        "20 s at -26, 20.1 s at -20, 20 s at -26: everything survives both gates",
        ((20.0, -26.0), (20.1, -20.0), (20.0, -26.0)),
        # (40 s * 10^-2.6 + 20.1 s * 10^-2.0) / 60.1 s -> -22.997 LUFS
        -22.997,
    ),
    LoudnessVector(
        "3341-6",
        "digital silence either side of the programme must not be averaged in",
        ((20.0, SILENCE_DBFS), (20.0, -23.0), (20.0, SILENCE_DBFS)),
        -23.0,
    ),
    LoudnessVector(
        "3341-7",
        "a -55 dBFS passage sits under the relative gate and is discarded",
        ((20.0, -23.0), (40.0, -55.0)),
        -23.0,
    ),
)

TECH_3341_CHANNEL_VECTORS = (
    ChannelLoudnessVector(
        "3341-ch-stereo",
        "the same tone in both channels is 3 LU louder than in one",
        (-23.0, -23.0),
        20.0,
        -23.0,
    ),
    ChannelLoudnessVector(
        "3341-ch-surround",
        "5.1 at -30 dBFS front and -26 dBFS surround, weighted per BS.1770 Table 3",
        # L R C LFE Ls Rs. 3 * 10^-3.0 / 2 + 1.41 * 2 * 10^-2.6 / 2 -> -22.97 LUFS
        (-30.0, -30.0, -30.0, -60.0, -26.0, -26.0),
        20.0,
        -22.974,
    ),
    ChannelLoudnessVector(
        "3341-ch-lfe",
        "a full-scale LFE changes nothing: the LFE is excluded, not attenuated",
        (-30.0, -30.0, -30.0, -3.0, -26.0, -26.0),
        20.0,
        -22.974,
    ),
)

TECH_3341_TRUE_PEAK_VECTORS = tuple(
    TruePeakVector(
        f"3341-tp-{rate}",
        f"997 Hz at 0 dBFS, {rate} Hz: a full-scale tone is 0 dBTP at any rate",
        rate,
        997.0,
        0.0,
        0.0,
        expected_dbtp=0.0,
        expected_sample_peak_dbfs=0.0,
    )
    for rate in (44_100, 48_000, 96_000, 192_000)
) + tuple(
    TruePeakVector(
        f"3341-tp-quarter-{rate}",
        f"{rate // 4} Hz at -6 dBFS sampled 45 degrees off the peak, {rate} Hz: "
        "every sample reads 3 dB low and only interpolation finds the waveform",
        rate,
        rate / 4.0,
        -6.02,
        45.0,
        expected_dbtp=-6.02,
        expected_sample_peak_dbfs=-9.03,
    )
    for rate in (44_100, 48_000, 96_000)
) + (
    TruePeakVector(
        "3341-tp-quarter-phase-48000",
        "12 kHz at -12 dBFS sampled 22.5 degrees off the peak, 48 kHz: "
        "the sample peak is 20 log10(cos(22.5 degrees)) = 0.688 dB low",
        48_000,
        12_000.0,
        -12.0,
        22.5,
        expected_dbtp=-12.0,
        expected_sample_peak_dbfs=-12.6877,
    ),
)

TECH_3342_VECTORS = (
    LraVector(
        "3342-1",
        "20 s at -20 dBFS followed by 20 s at -30 dBFS",
        ((20.0, -20.0), (20.0, -30.0)),
        10.0,
    ),
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


def _amplitude(peak_dbfs: float) -> float:
    return 0.0 if not math.isfinite(peak_dbfs) else 10.0 ** (peak_dbfs / 20.0)


def synthesize_segments(
    segments: tuple[tuple[float, float], ...],
    *,
    sample_rate: int = SAMPLE_RATE,
) -> np.ndarray:
    """Synthesize in-phase stereo sine segments as ``float32`` samples.

    Segments are ``(duration_s, peak_dbfs)`` pairs; a level of ``-inf`` means
    digital silence. Phase runs continuously across the joins, so a level
    change is a level change and not also a click.
    """
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
        mono = _amplitude(peak_dbfs) * np.sin(
            2.0 * np.pi * TONE_FREQUENCY_HZ * sample_numbers / sample_rate
        )
        parts.append(np.repeat(mono[:, np.newaxis], 2, axis=1).astype(np.float32))
        phase_samples += frame_count
    return np.concatenate(parts, axis=0)


def synthesize_channels(
    levels_dbfs: tuple[float, ...],
    duration_s: float,
    *,
    sample_rate: int = SAMPLE_RATE,
) -> np.ndarray:
    """A steady 1 kHz tone at a different level in each channel.

    Returned as ``(frames, channels)`` in ITU order (L, R, C, LFE, Ls, Rs).
    """
    frame_count = round(duration_s * sample_rate)
    if frame_count <= 0:
        raise ValueError("duration must be positive")
    t = np.arange(frame_count, dtype=np.float64) / sample_rate
    tone = np.sin(2.0 * np.pi * TONE_FREQUENCY_HZ * t)
    amplitudes = np.array([_amplitude(level) for level in levels_dbfs], dtype=np.float64)
    return (tone[:, np.newaxis] * amplitudes[np.newaxis, :]).astype(np.float32)


def synthesize_true_peak(vector: TruePeakVector, duration_s: float = 1.0) -> np.ndarray:
    """The tone of a true-peak vector, as ``(frames, 1)`` float32."""
    frame_count = round(duration_s * vector.sample_rate)
    n = np.arange(frame_count, dtype=np.float64)
    phase = math.radians(vector.phase_degrees)
    tone = _amplitude(vector.amplitude_dbfs) * np.sin(
        2.0 * np.pi * vector.frequency_hz * n / vector.sample_rate + phase
    )
    return tone[:, np.newaxis].astype(np.float32)
