"""Linked-channel compressor and true-peak brickwall limiter.

Both processors are causal and keep all detector, gain and delay state between
blocks.  Their offline path therefore runs the exact same algorithm as their
streaming path: offline processing resets the state and submits one large
block, while streaming may split that block at arbitrary boundaries.

Lookahead is implemented as a real delay.  The returned buffer consequently
starts with ``lookahead_ms`` of silence (plus the true-peak interpolator's
small FIR delay for :class:`LimiterEffect`) and has the same length as its
input.  A host that compensates plugin latency can move the result back on the
timeline; the live rack simply incurs that delay.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from ..util import (
    TRUE_PEAK_KERNEL_HALF,
    _interpolation_phases,
    db_to_linear,
    linear_to_db,
)
from .base import Effect

__all__ = ["CompressorEffect", "LimiterEffect"]


_LEVEL_FLOOR = 1e-20


def _time_coefficient(milliseconds: float, sample_rate: float) -> float:
    """One-pole coefficient whose time constant is ``milliseconds``."""
    if milliseconds <= 0.0:
        return 0.0
    return math.exp(-1.0 / (milliseconds * sample_rate / 1000.0))


def _delay_block(
    audio: np.ndarray,
    buffer: np.ndarray,
    position: int,
) -> tuple[np.ndarray, int]:
    """Push ``audio`` through a fixed-size circular delay."""
    delay = buffer.shape[1]
    if delay == 0:
        return audio.astype(np.float64, copy=True), 0

    output = np.empty(audio.shape, dtype=np.float64)
    source = audio.astype(np.float64, copy=False)
    for index in range(audio.shape[1]):
        output[:, index] = buffer[:, position]
        buffer[:, position] = source[:, index]
        position += 1
        if position == delay:
            position = 0
    return output, position


class CompressorEffect(Effect):
    """Soft-knee peak compressor with attack, release and lookahead.

    The side chain is linked across channels: the loudest channel determines
    one gain applied to every channel, preserving the stereo image.  The
    static curve is conventional downward compression.  Below the knee it is
    unity; above it, levels rise by one dB for every ``ratio`` dB at the input.

    Parameters are expressed in the units normally shown by a dynamics UI:
    ``threshold_db`` and ``knee_db`` in dBFS, times in milliseconds.
    """

    name = "Compressor"

    def __init__(
        self,
        threshold_db: float = -18.0,
        ratio: float = 4.0,
        attack_ms: float = 10.0,
        release_ms: float = 100.0,
        lookahead_ms: float = 5.0,
        knee_db: float = 6.0,
        enabled: bool = True,
        mix: float = 1.0,
    ) -> None:
        super().__init__(enabled=enabled, mix=mix)
        self.threshold_db = float(threshold_db)
        self.ratio = float(ratio)
        self.attack_ms = float(attack_ms)
        self.release_ms = float(release_ms)
        self.lookahead_ms = float(lookahead_ms)
        self.knee_db = float(knee_db)

        self._delay = np.zeros((0, 0), dtype=np.float64)
        self._delay_position = 0
        self._gain_db = 0.0
        self._last_gain_reduction_db = 0.0
        self._validate()

    @property
    def gain_reduction_db(self) -> float:
        """Positive gain reduction at the end of the most recent block."""
        return self._last_gain_reduction_db

    def latency_samples(self, sample_rate: float) -> int:
        """Lookahead delay at ``sample_rate``."""
        return max(0, int(round(self.lookahead_ms * float(sample_rate) / 1000.0)))

    def _validate(self) -> None:
        values = (
            self.threshold_db,
            self.ratio,
            self.attack_ms,
            self.release_ms,
            self.lookahead_ms,
            self.knee_db,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("compressor parameters must be finite")
        if self.ratio < 1.0:
            raise ValueError("compressor ratio must be at least 1:1")
        if min(self.attack_ms, self.release_ms, self.lookahead_ms, self.knee_db) < 0.0:
            raise ValueError("compressor times and knee must not be negative")

    def _prepare_delay(self, sample_rate: float, n_channels: int) -> None:
        delay = self.latency_samples(sample_rate)
        self._delay = np.zeros((n_channels, delay), dtype=np.float64)
        self._delay_position = 0

    def prepare(self, sample_rate: float, n_channels: int) -> None:
        self._validate()
        super().prepare(sample_rate, n_channels)
        self._prepare_delay(sample_rate, n_channels)
        self._gain_db = 0.0
        self._last_gain_reduction_db = 0.0

    def reset(self) -> None:
        self._delay.fill(0.0)
        self._delay_position = 0
        self._gain_db = 0.0
        self._last_gain_reduction_db = 0.0

    def parameters(self) -> dict[str, Any]:
        return {
            **super().parameters(),
            "threshold_db": self.threshold_db,
            "ratio": self.ratio,
            "attack_ms": self.attack_ms,
            "release_ms": self.release_ms,
            "lookahead_ms": self.lookahead_ms,
            "knee_db": self.knee_db,
        }

    def _static_gain_db(self, level_db: np.ndarray) -> np.ndarray:
        """Gain prescribed by the soft-knee transfer curve."""
        slope = 1.0 / self.ratio - 1.0
        distance = level_db - self.threshold_db
        if self.knee_db == 0.0:
            return np.where(distance > 0.0, slope * distance, 0.0)

        half_knee = self.knee_db / 2.0
        gain = np.zeros_like(level_db)
        above = distance >= half_knee
        inside = (distance > -half_knee) & ~above
        gain[above] = slope * distance[above]
        gain[inside] = (
            slope * np.square(distance[inside] + half_knee) / (2.0 * self.knee_db)
        )
        return gain

    def _process_planar(self, audio: np.ndarray, sample_rate: float) -> np.ndarray:
        self._validate()
        expected_delay = self.latency_samples(sample_rate)
        if self._delay.shape != (audio.shape[0], expected_delay):
            self._prepare_delay(sample_rate, audio.shape[0])
            self._gain_db = 0.0

        delayed, self._delay_position = _delay_block(
            audio, self._delay, self._delay_position
        )
        detector = np.max(np.abs(audio.astype(np.float64, copy=False)), axis=0)
        levels_db = 20.0 * np.log10(np.maximum(detector, _LEVEL_FLOOR))
        targets_db = self._static_gain_db(levels_db)

        attack = _time_coefficient(self.attack_ms, sample_rate)
        release = _time_coefficient(self.release_ms, sample_rate)
        gains = np.empty(audio.shape[1], dtype=np.float64)
        current = self._gain_db
        for index, target in enumerate(targets_db):
            coefficient = attack if target < current else release
            current = coefficient * current + (1.0 - coefficient) * float(target)
            gains[index] = float(db_to_linear(current))

        self._gain_db = current
        self._last_gain_reduction_db = max(0.0, -current)
        return (delayed * gains[np.newaxis, :]).astype(audio.dtype, copy=False)


class LimiterEffect(Effect):
    """Linked true-peak lookahead brickwall limiter.

    Detection uses the polyphase reconstruction kernel from
    :func:`audio_studio.dsp.util.true_peak_level`, not sample peaks.  Each
    reconstructed peak schedules instantaneous attenuation before the
    corresponding source samples leave the lookahead delay.  Gain is held
    across the interpolation window and then released smoothly.

    ``ceiling_db`` is a dBTP value.  A small internal guard accommodates
    floating-point rounding and the new inter-sample components that any
    time-varying gain can create; it is intentionally not exposed as a second
    user ceiling.
    """

    name = "True Peak Limiter"

    def __init__(
        self,
        ceiling_db: float = -1.0,
        release_ms: float = 50.0,
        lookahead_ms: float = 5.0,
        oversample: int = 4,
        enabled: bool = True,
        mix: float = 1.0,
    ) -> None:
        super().__init__(enabled=enabled, mix=mix)
        self.ceiling_db = float(ceiling_db)
        self.release_ms = float(release_ms)
        self.lookahead_ms = float(lookahead_ms)
        self.oversample = int(oversample)

        self._delay = np.zeros((0, 0), dtype=np.float64)
        self._delay_position = 0
        self._source_history = np.zeros((0, 2 * TRUE_PEAK_KERNEL_HALF), dtype=np.float64)
        self._gain = 1.0
        self._hold = 0
        self._last_gain_reduction_db = 0.0
        self._validate()

    @property
    def gain_reduction_db(self) -> float:
        """Positive gain reduction at the end of the most recent block."""
        return self._last_gain_reduction_db

    def detector_lookahead_samples(self, sample_rate: float) -> int:
        """Samples by which gain changes precede the reconstructed peak."""
        requested = int(round(self.lookahead_ms * float(sample_rate) / 1000.0))
        return max(TRUE_PEAK_KERNEL_HALF, requested)

    def latency_samples(self, sample_rate: float) -> int:
        """Total delay, including the true-peak interpolator's FIR context."""
        return TRUE_PEAK_KERNEL_HALF + self.detector_lookahead_samples(sample_rate)

    def _validate(self) -> None:
        if not all(
            math.isfinite(value)
            for value in (self.ceiling_db, self.release_ms, self.lookahead_ms)
        ):
            raise ValueError("limiter parameters must be finite")
        if self.ceiling_db > 0.0:
            raise ValueError("true-peak ceiling must not exceed 0 dBTP")
        if min(self.release_ms, self.lookahead_ms) < 0.0:
            raise ValueError("limiter times must not be negative")
        if self.oversample < 2:
            raise ValueError("true-peak oversampling must be at least 2x")

    def _prepare_state(self, sample_rate: float, n_channels: int) -> None:
        delay = self.latency_samples(sample_rate)
        self._delay = np.zeros((n_channels, delay), dtype=np.float64)
        self._delay_position = 0
        self._source_history = np.zeros(
            (n_channels, 2 * TRUE_PEAK_KERNEL_HALF), dtype=np.float64
        )

    def prepare(self, sample_rate: float, n_channels: int) -> None:
        self._validate()
        super().prepare(sample_rate, n_channels)
        self._prepare_state(sample_rate, n_channels)
        self._gain = 1.0
        self._hold = 0
        self._last_gain_reduction_db = 0.0

    def reset(self) -> None:
        self._delay.fill(0.0)
        self._source_history.fill(0.0)
        self._delay_position = 0
        self._gain = 1.0
        self._hold = 0
        self._last_gain_reduction_db = 0.0

    def parameters(self) -> dict[str, Any]:
        return {
            **super().parameters(),
            "ceiling_db": self.ceiling_db,
            "release_ms": self.release_ms,
            "lookahead_ms": self.lookahead_ms,
            "oversample": self.oversample,
        }

    def _true_peak_detector(self, audio: np.ndarray) -> np.ndarray:
        """Per-centre true peaks, carrying FIR context between blocks."""
        half = TRUE_PEAK_KERNEL_HALF
        span = 2 * half + 1
        source = audio.astype(np.float64, copy=False)
        combined = np.concatenate((self._source_history, source), axis=1)
        windows = np.lib.stride_tricks.sliding_window_view(combined, span, axis=-1)
        phases = _interpolation_phases(self.oversample).astype(np.float64, copy=False)
        reconstructed = windows @ phases
        self._source_history = combined[:, -2 * half :].copy()
        return np.max(np.abs(reconstructed), axis=(0, 2))

    def _process_planar(self, audio: np.ndarray, sample_rate: float) -> np.ndarray:
        self._validate()
        expected_delay = self.latency_samples(sample_rate)
        expected_history = (audio.shape[0], 2 * TRUE_PEAK_KERNEL_HALF)
        if (
            self._delay.shape != (audio.shape[0], expected_delay)
            or self._source_history.shape != expected_history
        ):
            self._prepare_state(sample_rate, audio.shape[0])
            self._gain = 1.0
            self._hold = 0

        detector = self._true_peak_detector(audio)
        delayed, self._delay_position = _delay_block(
            audio, self._delay, self._delay_position
        )

        # A quarter-dB guard covers float32 rounding, finite FIR edge effects,
        # and the small new ISPs that time-varying gain can create.
        guarded_ceiling = float(db_to_linear(self.ceiling_db - 0.25))
        targets = np.minimum(1.0, guarded_ceiling / np.maximum(detector, _LEVEL_FLOOR))
        release = _time_coefficient(self.release_ms, sample_rate)
        hold_samples = self.detector_lookahead_samples(sample_rate) + TRUE_PEAK_KERNEL_HALF

        gains = np.empty(audio.shape[1], dtype=np.float64)
        current = self._gain
        hold = self._hold
        for index, target in enumerate(targets):
            target_value = float(target)
            if target_value < current:
                current = target_value
                hold = hold_samples
            elif hold > 0:
                hold -= 1
            else:
                current = release * current + (1.0 - release) * target_value
            gains[index] = current

        self._gain = current
        self._hold = hold
        self._last_gain_reduction_db = max(0.0, -float(linear_to_db(current)))
        output = delayed * gains[np.newaxis, :]

        # The true-peak detector includes phase zero, but clipping here also
        # protects against a ceiling change while delayed samples are pending.
        sample_ceiling = float(db_to_linear(self.ceiling_db))
        np.clip(output, -sample_ceiling, sample_ceiling, out=output)
        return output.astype(audio.dtype, copy=False)
