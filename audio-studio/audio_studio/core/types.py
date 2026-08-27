"""Fundamental value types shared by the engine, the UI and the DSP layer.

Everything in :mod:`audio_studio.core` is deliberately free of any Qt import so
that the audio engine can be exercised head-lessly from unit tests and reused
from a future non-Qt front-end (or a C++/JUCE port).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Final

import numpy as np

#: Internal working sample format. Every decoded file is converted to
#: non-interleaved-by-column ``float32`` in ``[-1.0, 1.0]`` so that the DSP
#: chain never has to branch on the source bit depth.
SAMPLE_DTYPE: Final = np.float32

#: Smallest amplitude mapped to a finite dBFS value (-120 dBFS).
MIN_AMPLITUDE: Final[float] = 1e-6


class TransportState(enum.Enum):
    """Playback state of :class:`~audio_studio.core.engine.AudioEngine`."""

    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"

    @property
    def is_active(self) -> bool:
        """True while the output stream should be pulling audio."""
        return self is TransportState.PLAYING


@dataclass(frozen=True, slots=True)
class TimeRange:
    """A half-open frame range ``[start, end)`` on a clip's timeline."""

    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < 0:
            raise ValueError(f"TimeRange bounds must be non-negative, got {self!r}")
        if self.end < self.start:
            raise ValueError(f"TimeRange end precedes start: {self!r}")

    @property
    def length(self) -> int:
        return self.end - self.start

    @property
    def is_empty(self) -> bool:
        return self.end == self.start

    def clamped(self, limit: int) -> TimeRange:
        """Return this range clipped to ``[0, limit]``."""
        start = min(max(self.start, 0), limit)
        end = min(max(self.end, start), limit)
        return TimeRange(start, end)

    def to_seconds(self, sample_rate: int) -> tuple[float, float]:
        return self.start / sample_rate, self.end / sample_rate

    @staticmethod
    def from_seconds(start: float, end: float, sample_rate: int) -> TimeRange:
        lo, hi = sorted((start, end))
        return TimeRange(int(round(lo * sample_rate)), int(round(hi * sample_rate)))


@dataclass(frozen=True, slots=True)
class AudioFormat:
    """Container/codec metadata preserved from the decoded source file."""

    sample_rate: int
    channels: int
    subtype: str = "PCM_16"
    container: str = "WAV"

    @property
    def bit_depth(self) -> int | None:
        """Best-effort bit depth parsed from the libsndfile subtype string."""
        digits = "".join(ch for ch in self.subtype if ch.isdigit())
        return int(digits) if digits else None

    def describe(self) -> str:
        depth = self.bit_depth
        depth_text = f"{depth}-bit" if depth else self.subtype
        layout = {1: "Mono", 2: "Stereo"}.get(self.channels, f"{self.channels}ch")
        return f"{self.sample_rate / 1000:g} kHz · {depth_text} · {layout} · {self.container}"


@dataclass(slots=True)
class AudioBuffer:
    """A block of PCM audio held as a ``(frames, channels)`` float32 array."""

    data: np.ndarray
    sample_rate: int

    def __post_init__(self) -> None:
        if self.sample_rate <= 0:
            raise ValueError(f"sample_rate must be positive, got {self.sample_rate}")
        array = np.asarray(self.data)
        if array.ndim == 1:
            array = array[:, np.newaxis]
        if array.ndim != 2:
            raise ValueError(f"AudioBuffer expects a 1-D or 2-D array, got {array.ndim}-D")
        self.data = np.ascontiguousarray(array, dtype=SAMPLE_DTYPE)

    @property
    def n_frames(self) -> int:
        return int(self.data.shape[0])

    @property
    def n_channels(self) -> int:
        return int(self.data.shape[1])

    @property
    def duration(self) -> float:
        """Length in seconds."""
        return self.n_frames / self.sample_rate

    def slice(self, rng: TimeRange) -> AudioBuffer:
        clipped = rng.clamped(self.n_frames)
        return AudioBuffer(self.data[clipped.start : clipped.end], self.sample_rate)

    def peak(self) -> float:
        if self.n_frames == 0:
            return 0.0
        return float(np.max(np.abs(self.data)))

    def rms(self) -> float:
        if self.n_frames == 0:
            return 0.0
        return float(np.sqrt(np.mean(np.square(self.data, dtype=np.float64))))

    def to_mono(self) -> np.ndarray:
        """Downmix to a 1-D array by averaging channels."""
        if self.n_channels == 1:
            return self.data[:, 0]
        return self.data.mean(axis=1, dtype=np.float32)

    @classmethod
    def silence(cls, n_frames: int, n_channels: int, sample_rate: int) -> AudioBuffer:
        return cls(np.zeros((n_frames, n_channels), dtype=SAMPLE_DTYPE), sample_rate)


@dataclass(slots=True)
class LevelReading:
    """Per-channel metering snapshot published by the engine."""

    peak: tuple[float, ...] = field(default_factory=tuple)
    rms: tuple[float, ...] = field(default_factory=tuple)

    @property
    def is_empty(self) -> bool:
        return not self.peak


def amplitude_to_db(amplitude: float, floor_db: float = -120.0) -> float:
    """Convert a linear amplitude to dBFS, clamped at ``floor_db``."""
    if amplitude <= MIN_AMPLITUDE:
        return floor_db
    return max(floor_db, 20.0 * float(np.log10(amplitude)))


def db_to_amplitude(db: float) -> float:
    """Convert dBFS to a linear amplitude factor."""
    return float(10.0 ** (db / 20.0))


def format_timecode(seconds: float, *, show_millis: bool = True) -> str:
    """Render seconds as ``H:MM:SS.mmm`` (hours omitted when zero)."""
    negative = seconds < 0
    seconds = abs(float(seconds))
    total_ms = int(round(seconds * 1000.0))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, millis = divmod(rem, 1000)

    text = f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"
    if show_millis:
        text += f".{millis:03d}"
    return ("-" if negative else "") + text
