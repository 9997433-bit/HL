"""Streaming noise gate, delay and feedback-delay-network reverb.

All three processors are causal.  Their offline path therefore uses exactly
the same stateful algorithm as block processing: :class:`Effect` resets the
state and submits the complete buffer as one block, while live playback may
split that buffer at arbitrary boundaries.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.signal import lfilter

from ..util import db_to_linear
from .base import Effect

__all__ = ["NoiseGateEffect", "DelayEffect", "FDNReverbEffect"]


_LEVEL_FLOOR = 1e-20


def _time_coefficient(milliseconds: float, sample_rate: float) -> float:
    """One-pole coefficient whose time constant is ``milliseconds``."""
    if milliseconds <= 0.0:
        return 0.0
    return math.exp(-1.0 / (milliseconds * sample_rate / 1000.0))


class NoiseGateEffect(Effect):
    """Linked-channel downward expander with attack, hold and release.

    Below ``threshold_db`` the transfer curve expands levels by ``ratio``.
    Attenuation is limited by ``floor_db`` so the gate can either reduce room
    tone naturally or, with a low floor, behave like a conventional hard gate.
    The loudest channel drives one gain for every channel, preserving stereo
    position.
    """

    name = "Noise Gate"

    def __init__(
        self,
        threshold_db: float = -45.0,
        attack_ms: float = 5.0,
        release_ms: float = 100.0,
        hold_ms: float = 40.0,
        ratio: float = 4.0,
        floor_db: float = -80.0,
        enabled: bool = True,
        mix: float = 1.0,
    ) -> None:
        super().__init__(enabled=enabled, mix=mix)
        self.threshold_db = float(threshold_db)
        self.attack_ms = float(attack_ms)
        self.release_ms = float(release_ms)
        self.hold_ms = float(hold_ms)
        self.ratio = float(ratio)
        self.floor_db = float(floor_db)

        self._gain_db = self.floor_db
        self._hold_remaining = 0
        self._validate()

    def _validate(self) -> None:
        values = (
            self.threshold_db,
            self.attack_ms,
            self.release_ms,
            self.hold_ms,
            self.ratio,
            self.floor_db,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("noise-gate parameters must be finite")
        if min(self.attack_ms, self.release_ms, self.hold_ms) < 0.0:
            raise ValueError("noise-gate times must not be negative")
        if self.ratio < 1.0:
            raise ValueError("noise-gate ratio must be at least 1:1")
        if self.floor_db > 0.0:
            raise ValueError("noise-gate floor must not exceed 0 dB")

    def prepare(self, sample_rate: float, n_channels: int) -> None:
        self._validate()
        super().prepare(sample_rate, n_channels)
        self.reset()

    def reset(self) -> None:
        self._gain_db = self.floor_db
        self._hold_remaining = 0

    def parameters(self) -> dict[str, Any]:
        return {
            **super().parameters(),
            "threshold_db": self.threshold_db,
            "attack_ms": self.attack_ms,
            "release_ms": self.release_ms,
            "hold_ms": self.hold_ms,
            "ratio": self.ratio,
            "floor_db": self.floor_db,
        }

    def _process_planar(self, audio: np.ndarray, sample_rate: float) -> np.ndarray:
        self._validate()
        if self.ratio == 1.0 or self.floor_db == 0.0:
            self._gain_db = 0.0
            self._hold_remaining = 0
            return audio.copy()

        source = audio.astype(np.float64, copy=False)
        detector = np.max(np.abs(source), axis=0)
        levels_db = 20.0 * np.log10(np.maximum(detector, _LEVEL_FLOOR))
        targets_db = np.clip(
            (self.ratio - 1.0) * (levels_db - self.threshold_db),
            self.floor_db,
            0.0,
        )

        attack = _time_coefficient(self.attack_ms, sample_rate)
        release = _time_coefficient(self.release_ms, sample_rate)
        hold_samples = max(0, int(round(self.hold_ms * sample_rate / 1000.0)))
        gains = np.empty(audio.shape[1], dtype=np.float64)
        current = self._gain_db
        hold = self._hold_remaining

        for index, target in enumerate(targets_db):
            target_value = float(target)
            if target_value >= current:
                # Opening is never delayed by the hold stage.
                current = attack * current + (1.0 - attack) * target_value
                if target_value >= -1e-12:
                    hold = hold_samples
            elif hold > 0:
                hold -= 1
            else:
                current = release * current + (1.0 - release) * target_value
            gains[index] = float(db_to_linear(current))

        self._gain_db = current
        self._hold_remaining = hold
        return (source * gains[np.newaxis, :]).astype(audio.dtype, copy=False)


class DelayEffect(Effect):
    """Feedback delay with a persistent circular buffer.

    ``mix`` is the standard :class:`Effect` dry/wet control.  The wet path is
    the delayed signal, so ``mix=1`` is useful for send-style routing and
    ``mix=0.5`` produces the familiar insert delay.
    """

    name = "Delay"

    def __init__(
        self,
        time_ms: float = 250.0,
        feedback: float = 0.35,
        mix: float = 0.35,
        enabled: bool = True,
    ) -> None:
        super().__init__(enabled=enabled, mix=mix)
        self.time_ms = float(time_ms)
        self.feedback = float(feedback)
        self._delay = np.zeros((0, 0), dtype=np.float64)
        self._position = 0
        self._validate()

    def _validate(self) -> None:
        if not math.isfinite(self.time_ms) or not math.isfinite(self.feedback):
            raise ValueError("delay parameters must be finite")
        if self.time_ms < 0.0:
            raise ValueError("delay time must not be negative")
        if abs(self.feedback) >= 1.0:
            raise ValueError("delay feedback magnitude must be below 1")

    def delay_samples(self, sample_rate: float) -> int:
        """The current delay time rounded to a whole number of samples."""
        return max(0, int(round(self.time_ms * float(sample_rate) / 1000.0)))

    def _prepare_state(self, sample_rate: float, n_channels: int) -> None:
        self._delay = np.zeros(
            (n_channels, self.delay_samples(sample_rate)), dtype=np.float64
        )
        self._position = 0

    def prepare(self, sample_rate: float, n_channels: int) -> None:
        self._validate()
        super().prepare(sample_rate, n_channels)
        self._prepare_state(sample_rate, n_channels)

    def reset(self) -> None:
        self._delay.fill(0.0)
        self._position = 0

    def parameters(self) -> dict[str, Any]:
        return {
            **super().parameters(),
            "time_ms": self.time_ms,
            "feedback": self.feedback,
        }

    def _process_planar(self, audio: np.ndarray, sample_rate: float) -> np.ndarray:
        self._validate()
        delay_samples = self.delay_samples(sample_rate)
        if self._delay.shape != (audio.shape[0], delay_samples):
            self._prepare_state(sample_rate, audio.shape[0])

        source = audio.astype(np.float64, copy=False)
        if delay_samples == 0:
            return source.astype(audio.dtype, copy=True)

        wet = np.empty(audio.shape, dtype=np.float64)
        position = self._position
        for index in range(audio.shape[1]):
            delayed = self._delay[:, position].copy()
            wet[:, index] = delayed
            self._delay[:, position] = source[:, index] + self.feedback * delayed
            position += 1
            if position == delay_samples:
                position = 0

        self._position = position
        return wet.astype(audio.dtype, copy=False)


class FDNReverbEffect(Effect):
    """Compact four-line feedback delay network reverb.

    A normalised Hadamard matrix mixes the feedback paths without increasing
    their energy.  The four mutually-prime-ish delay times avoid an obvious
    single echo, while a one-pole filter in each feedback path provides the
    high-frequency damping expected from an acoustic room.  Work is vectorised
    in chunks no longer than the shortest delay line to keep live CPU use
    bounded while retaining sample-exact state across calls.
    """

    name = "FDN Reverb"

    _BASE_DELAYS_MS = (29.7, 37.1, 41.1, 43.7)
    _INJECTION_SIGNS = np.array((1.0, -1.0, 1.0, -1.0), dtype=np.float64)

    def __init__(
        self,
        room_size: float = 0.6,
        damping: float = 0.35,
        mix: float = 0.25,
        enabled: bool = True,
    ) -> None:
        super().__init__(enabled=enabled, mix=mix)
        self.room_size = float(room_size)
        self.damping = float(damping)

        self._buffers: list[np.ndarray] = []
        self._positions = np.zeros(4, dtype=np.int64)
        self._damping_zi = np.zeros((0, 4), dtype=np.float64)
        self._delay_lengths: tuple[int, ...] = ()
        self._validate()

    def _validate(self) -> None:
        if not math.isfinite(self.room_size) or not math.isfinite(self.damping):
            raise ValueError("reverb parameters must be finite")
        if not 0.0 <= self.room_size <= 1.0:
            raise ValueError("reverb room size must be between 0 and 1")
        if not 0.0 <= self.damping <= 1.0:
            raise ValueError("reverb damping must be between 0 and 1")

    def _lengths(self, sample_rate: float) -> tuple[int, ...]:
        scale = 0.4 + 1.1 * self.room_size
        return tuple(
            max(1, int(round(milliseconds * scale * sample_rate / 1000.0)))
            for milliseconds in self._BASE_DELAYS_MS
        )

    def _feedback(self) -> float:
        return 0.55 + 0.4 * self.room_size

    def _prepare_state(self, sample_rate: float, n_channels: int) -> None:
        self._delay_lengths = self._lengths(sample_rate)
        self._buffers = [
            np.zeros((n_channels, length), dtype=np.float64)
            for length in self._delay_lengths
        ]
        self._positions = np.zeros(4, dtype=np.int64)
        self._damping_zi = np.zeros((n_channels, 4), dtype=np.float64)

    def prepare(self, sample_rate: float, n_channels: int) -> None:
        self._validate()
        super().prepare(sample_rate, n_channels)
        self._prepare_state(sample_rate, n_channels)

    def reset(self) -> None:
        for buffer in self._buffers:
            buffer.fill(0.0)
        self._positions.fill(0)
        self._damping_zi.fill(0.0)

    def parameters(self) -> dict[str, Any]:
        return {
            **super().parameters(),
            "room_size": self.room_size,
            "damping": self.damping,
        }

    @staticmethod
    def _hadamard(values: np.ndarray) -> np.ndarray:
        """Energy-preserving four-point Hadamard transform."""
        a, b, c, d = values[:, 0], values[:, 1], values[:, 2], values[:, 3]
        mixed = np.empty_like(values)
        mixed[:, 0] = (a + b + c + d) * 0.5
        mixed[:, 1] = (a - b + c - d) * 0.5
        mixed[:, 2] = (a + b - c - d) * 0.5
        mixed[:, 3] = (a - b - c + d) * 0.5
        return mixed

    def _process_planar(self, audio: np.ndarray, sample_rate: float) -> np.ndarray:
        self._validate()
        lengths = self._lengths(sample_rate)
        expected_shape = (audio.shape[0], 4)
        if lengths != self._delay_lengths or self._damping_zi.shape != expected_shape:
            self._prepare_state(sample_rate, audio.shape[0])

        source = audio.astype(np.float64, copy=False)
        wet = np.empty(audio.shape, dtype=np.float64)
        shortest = min(lengths)
        feedback = self._feedback()
        offset = 0

        while offset < audio.shape[1]:
            count = min(shortest, audio.shape[1] - offset)
            reads = np.empty((audio.shape[0], 4, count), dtype=np.float64)
            indices: list[np.ndarray] = []
            for line, (buffer, length) in enumerate(zip(self._buffers, lengths)):
                line_indices = (
                    np.arange(count, dtype=np.int64) + self._positions[line]
                ) % length
                indices.append(line_indices)
                reads[:, line, :] = buffer[:, line_indices]

            mixed = self._hadamard(reads)
            damped, state = lfilter(
                [1.0 - self.damping],
                [1.0, -self.damping],
                mixed,
                axis=-1,
                zi=self._damping_zi[..., np.newaxis],
            )
            self._damping_zi = state[..., 0]

            section = source[:, offset : offset + count]
            injection = (
                section[:, np.newaxis, :]
                * self._INJECTION_SIGNS[np.newaxis, :, np.newaxis]
                * 0.5
            )
            writes = injection + feedback * damped
            for line, (buffer, length) in enumerate(zip(self._buffers, lengths)):
                buffer[:, indices[line]] = writes[:, line, :]
                self._positions[line] = (self._positions[line] + count) % length

            wet[:, offset : offset + count] = (
                np.sum(
                    reads
                    * self._INJECTION_SIGNS[np.newaxis, :, np.newaxis],
                    axis=1,
                )
                * 0.5
            )
            offset += count

        return wet.astype(audio.dtype, copy=False)
