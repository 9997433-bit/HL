"""Offline reconstruction of hard-clipped waveform peaks.

Hard clipping replaces the top (or bottom) of a waveform with a short, flat
run.  The samples under that plateau are gone, but the value and slope on both
sides are still available.  This module joins those boundaries with a cubic
Hermite spline.  Unlike a straight line, the spline can form the missing peak;
unlike a spectral repair, it changes only samples known to be on a clipping
rail.

The detector deliberately requires at least two nearly equal samples.  A clean
full-scale sine may touch 1.0 for one sample and is not necessarily clipped,
whereas an ADC or integer encoder produces repeated rail values.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.interpolate import CubicHermiteSpline

from ..effects.base import Effect
from ..util import as_planar, restore_layout

__all__ = [
    "ClipEvent",
    "DeClipEffect",
    "DeClipReport",
    "detect_clipping",
    "repair_clipping",
]


@dataclass(frozen=True, slots=True)
class ClipEvent:
    """One detected clipping plateau, using a half-open sample range."""

    channel: int
    start: int
    stop: int
    level: float
    reconstructed: bool

    @property
    def length(self) -> int:
        return self.stop - self.start

    @property
    def polarity(self) -> int:
        return 1 if self.level >= 0.0 else -1


@dataclass(frozen=True, slots=True)
class DeClipReport:
    """Summary of one clipping detection or reconstruction pass."""

    events: tuple[ClipEvent, ...]
    threshold: float
    duration_s: float

    @property
    def count(self) -> int:
        return len(self.events)

    @property
    def repaired_count(self) -> int:
        return sum(event.reconstructed for event in self.events)

    @property
    def clipped_samples(self) -> int:
        return sum(event.length for event in self.events)

    @property
    def repaired_samples(self) -> int:
        return sum(event.length for event in self.events if event.reconstructed)

    def in_channel(self, channel: int) -> tuple[ClipEvent, ...]:
        return tuple(event for event in self.events if event.channel == channel)

    def as_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "repaired_count": self.repaired_count,
            "clipped_samples": self.clipped_samples,
            "repaired_samples": self.repaired_samples,
            "threshold": self.threshold,
            "duration_s": self.duration_s,
        }


def _validate(
    sample_rate: float,
    threshold: float,
    flat_tolerance: float,
    min_run_samples: int,
) -> tuple[float, float, int]:
    if not np.isfinite(sample_rate) or sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    threshold = float(threshold)
    if not np.isfinite(threshold) or threshold <= 0:
        raise ValueError("threshold must be positive")
    flat_tolerance = float(flat_tolerance)
    if not np.isfinite(flat_tolerance) or flat_tolerance < 0:
        raise ValueError("flat_tolerance must be non-negative")
    min_run_samples = int(min_run_samples)
    if min_run_samples < 2:
        raise ValueError("min_run_samples must be at least 2")
    return threshold, flat_tolerance, min_run_samples


def _flat_clip_mask(
    channel: np.ndarray,
    threshold: float,
    flat_tolerance: float,
) -> np.ndarray:
    """Mark samples belonging to adjacent, same-polarity values on a rail."""
    mask = np.zeros(channel.size, dtype=bool)
    if channel.size < 2:
        return mask
    high = np.abs(channel) >= threshold
    pairs = (
        high[:-1]
        & high[1:]
        & (np.signbit(channel[:-1]) == np.signbit(channel[1:]))
        & (np.abs(np.diff(channel)) <= flat_tolerance)
    )
    mask[:-1] |= pairs
    mask[1:] |= pairs
    return mask


def _runs(mask: np.ndarray, min_run_samples: int) -> list[tuple[int, int]]:
    indices = np.flatnonzero(mask)
    if indices.size == 0:
        return []
    breaks = np.flatnonzero(np.diff(indices) > 1)
    starts = indices[np.concatenate(([0], breaks + 1))]
    stops = indices[np.concatenate((breaks, [indices.size - 1]))] + 1
    return [
        (int(start), int(stop))
        for start, stop in zip(starts, stops, strict=True)
        if stop - start >= min_run_samples
    ]


def _boundary_slope(
    channel: np.ndarray,
    anchor: int,
    *,
    before: bool,
    context_samples: int,
) -> float:
    """Estimate a per-sample derivative from unclipped boundary context."""
    if before:
        first = max(0, anchor - context_samples + 1)
        indices = np.arange(first, anchor + 1)
    else:
        stop = min(channel.size, anchor + context_samples)
        indices = np.arange(anchor, stop)
    if indices.size < 2:
        return 0.0

    # Centring the x axis on the boundary keeps the tiny polynomial solve well
    # conditioned even for an event millions of samples into a recording.
    x = indices.astype(np.float64) - float(anchor)
    degree = min(3, indices.size - 1)
    coefficients = np.polyfit(x, channel[indices], degree)
    return float(np.polyval(np.polyder(coefficients), 0.0))


def _reconstruct_run(
    channel: np.ndarray,
    start: int,
    stop: int,
    context_samples: int,
) -> np.ndarray | None:
    """Cubic Hermite reconstruction between the intact boundary samples."""
    left, right = start - 1, stop
    if left < 0 or right >= channel.size:
        return None
    left_slope = _boundary_slope(
        channel, left, before=True, context_samples=context_samples
    )
    right_slope = _boundary_slope(
        channel, right, before=False, context_samples=context_samples
    )
    spline = CubicHermiteSpline(
        np.array([left, right], dtype=np.float64),
        np.array([channel[left], channel[right]], dtype=np.float64),
        np.array([left_slope, right_slope], dtype=np.float64),
    )
    values = np.asarray(spline(np.arange(start, stop, dtype=np.float64)))
    if not np.all(np.isfinite(values)):
        return None
    return values


def _process(
    audio: np.ndarray,
    sample_rate: float,
    *,
    threshold: float,
    flat_tolerance: float,
    min_run_samples: int,
    max_clip_ms: float,
    context_samples: int,
    channels_last: bool | None,
    repair: bool,
) -> tuple[np.ndarray, DeClipReport, bool]:
    threshold, flat_tolerance, min_run_samples = _validate(
        sample_rate, threshold, flat_tolerance, min_run_samples
    )
    if not np.isfinite(max_clip_ms) or max_clip_ms <= 0:
        raise ValueError("max_clip_ms must be positive")
    if context_samples < 2:
        raise ValueError("context_samples must be at least 2")

    planar, was_mono = as_planar(audio, channels_last=channels_last, dtype=np.float64)
    output = planar.copy()
    maximum = max(1, int(round(float(max_clip_ms) * sample_rate / 1000.0)))
    events: list[ClipEvent] = []

    for channel_index, channel in enumerate(planar):
        mask = _flat_clip_mask(channel, threshold, flat_tolerance)
        for start, stop in _runs(mask, min_run_samples):
            reconstructed = False
            if repair and stop - start <= maximum:
                values = _reconstruct_run(channel, start, stop, int(context_samples))
                if values is not None:
                    output[channel_index, start:stop] = values
                    reconstructed = True
            events.append(
                ClipEvent(
                    channel=channel_index,
                    start=start,
                    stop=stop,
                    level=float(np.median(channel[start:stop])),
                    reconstructed=reconstructed,
                )
            )

    report = DeClipReport(
        events=tuple(events),
        threshold=threshold,
        duration_s=planar.shape[1] / float(sample_rate),
    )
    return output, report, was_mono


def detect_clipping(
    audio: np.ndarray,
    sample_rate: float,
    threshold: float = 0.98,
    *,
    flat_tolerance: float = 1e-6,
    min_run_samples: int = 2,
    channels_last: bool | None = None,
) -> DeClipReport:
    """Detect hard-clipping plateaus without changing ``audio``."""
    _, report, _ = _process(
        audio,
        sample_rate,
        threshold=threshold,
        flat_tolerance=flat_tolerance,
        min_run_samples=min_run_samples,
        max_clip_ms=20.0,
        context_samples=4,
        channels_last=channels_last,
        repair=False,
    )
    return report


def repair_clipping(
    audio: np.ndarray,
    sample_rate: float,
    threshold: float = 0.98,
    *,
    flat_tolerance: float = 1e-6,
    min_run_samples: int = 2,
    max_clip_ms: float = 20.0,
    context_samples: int = 4,
    channels_last: bool | None = None,
) -> tuple[np.ndarray, DeClipReport]:
    """Reconstruct clipped runs and return ``(audio, report)``.

    The input is never modified. Shape, layout, and floating dtype follow the
    caller, matching the rest of the DSP repair API.
    """
    output, report, was_mono = _process(
        audio,
        sample_rate,
        threshold=threshold,
        flat_tolerance=flat_tolerance,
        min_run_samples=min_run_samples,
        max_clip_ms=max_clip_ms,
        context_samples=context_samples,
        channels_last=channels_last,
        repair=True,
    )
    source = np.asarray(audio)
    dtype = source.dtype if source.dtype in (np.float32, np.float64) else np.float32
    result = restore_layout(output.astype(dtype, copy=False), was_mono)
    if channels_last and not was_mono:
        result = np.ascontiguousarray(result.T)
    return result, report


class DeClipEffect(Effect):
    """Offline cubic reconstruction of hard-clipped waveform peaks."""

    name = "De-Clip"
    is_offline_only = True

    def __init__(
        self,
        threshold: float = 0.98,
        max_clip_ms: float = 20.0,
        context_samples: int = 4,
        flat_tolerance: float = 1e-6,
        min_run_samples: int = 2,
        enabled: bool = True,
        mix: float = 1.0,
        *,
        clip_threshold: float | None = None,
    ) -> None:
        super().__init__(enabled=enabled, mix=mix)
        self.threshold = float(threshold if clip_threshold is None else clip_threshold)
        self.max_clip_ms = float(max_clip_ms)
        self.context_samples = int(context_samples)
        self.flat_tolerance = float(flat_tolerance)
        self.min_run_samples = int(min_run_samples)
        self._last_report: DeClipReport | None = None

    @property
    def clip_threshold(self) -> float:
        """Alias for hosts that call the detection level a clip threshold."""
        return self.threshold

    @clip_threshold.setter
    def clip_threshold(self, value: float) -> None:
        self.threshold = float(value)

    @property
    def last_report(self) -> DeClipReport | None:
        return self._last_report

    def parameters(self) -> dict[str, Any]:
        return {
            **super().parameters(),
            "threshold": self.threshold,
            "max_clip_ms": self.max_clip_ms,
            "context_samples": self.context_samples,
            "flat_tolerance": self.flat_tolerance,
            "min_run_samples": self.min_run_samples,
        }

    def _process_planar(self, audio: np.ndarray, sample_rate: float) -> np.ndarray:
        repaired, report = repair_clipping(
            audio,
            sample_rate,
            threshold=self.threshold,
            flat_tolerance=self.flat_tolerance,
            min_run_samples=self.min_run_samples,
            max_clip_ms=self.max_clip_ms,
            context_samples=self.context_samples,
            channels_last=False,
        )
        self._last_report = report
        return np.asarray(repaired, dtype=audio.dtype)
