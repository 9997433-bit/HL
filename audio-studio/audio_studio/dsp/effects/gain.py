"""Level control: static/ramped gain and peak, RMS or true-peak normalisation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

import numpy as np

from ..util import db_to_linear, linear_to_db, peak_level, rms_level, true_peak_level
from .base import Effect

__all__ = ["GainEffect", "NormalizeMode", "NormalizeEffect", "LevelReport", "measure_levels"]


class GainEffect(Effect):
    """Apply a constant gain, optionally ramping when the value changes.

    A jump in gain between two blocks is a step discontinuity and clicks. When
    ``ramp_ms`` is non-zero the effect interpolates from the previously applied
    gain to the new one over that many milliseconds at the start of the next
    block, which removes the click without needing the caller to schedule
    anything.

    Examples
    --------
    >>> import numpy as np
    >>> out = GainEffect(gain_db=-6.0).process(np.ones(4), 48_000)
    >>> round(float(out[0]), 4)
    0.5012
    """

    name = "Gain"

    def __init__(
        self,
        gain_db: float = 0.0,
        ramp_ms: float = 5.0,
        invert_polarity: bool = False,
        enabled: bool = True,
    ) -> None:
        super().__init__(enabled=enabled)
        self.gain_db = float(gain_db)
        self.ramp_ms = float(ramp_ms)
        self.invert_polarity = bool(invert_polarity)
        self._current: Optional[float] = None

    @property
    def gain_linear(self) -> float:
        """Target gain as a linear factor, polarity included."""
        value = float(db_to_linear(self.gain_db))
        return -value if self.invert_polarity else value

    def reset(self) -> None:
        self._current = None

    def parameters(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "gain_db": self.gain_db,
            "ramp_ms": self.ramp_ms,
            "invert_polarity": self.invert_polarity,
        }

    def _process_planar(self, audio: np.ndarray, sample_rate: float) -> np.ndarray:
        target = self.gain_linear
        n = audio.shape[1]
        start = target if self._current is None else self._current
        self._current = target

        if start == target:
            return audio * np.asarray(target, dtype=audio.dtype)

        ramp_len = min(n, max(1, int(self.ramp_ms * sample_rate / 1000.0)))
        envelope = np.full(n, target, dtype=audio.dtype)
        envelope[:ramp_len] = np.linspace(start, target, ramp_len, endpoint=True, dtype=audio.dtype)
        return audio * envelope


class NormalizeMode(str, Enum):
    """What quantity :class:`NormalizeEffect` drives to the target level.

    ``PEAK``
        Highest sample magnitude. Fast, and what "Normalize to 0 dB" means in
        most editors.
    ``TRUE_PEAK``
        Highest *reconstructed* level, measured on a 4x oversampled copy per
        ITU-R BS.1770. Sample-peak normalisation to 0 dBFS routinely produces
        inter-sample peaks above full scale that clip in a DAC or a lossy
        encoder; this mode is the one to use before delivery.
    ``RMS``
        Root-mean-square energy, a rough loudness match. Can and will clip, so
        pair it with :attr:`NormalizeEffect.ceiling_db`.
    """

    PEAK = "peak"
    TRUE_PEAK = "true_peak"
    RMS = "rms"

    @classmethod
    def coerce(cls, value: "NormalizeMode | str") -> "NormalizeMode":
        if isinstance(value, cls):
            return value
        key = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        try:
            return cls(key)
        except ValueError as exc:
            raise ValueError(f"unknown normalize mode {value!r}") from exc


@dataclass(frozen=True)
class LevelReport:
    """Measured levels of a buffer, all in dBFS."""

    peak_db: float
    true_peak_db: float
    rms_db: float
    crest_factor_db: float
    per_channel_peak_db: tuple[float, ...]

    def __str__(self) -> str:
        return (
            f"peak {self.peak_db:.2f} dBFS, true peak {self.true_peak_db:.2f} dBTP, "
            f"RMS {self.rms_db:.2f} dBFS, crest {self.crest_factor_db:.2f} dB"
        )


def measure_levels(audio: np.ndarray, channels_last: Optional[bool] = None) -> LevelReport:
    """Measure peak, true peak, RMS and crest factor of a buffer."""
    from ..util import as_planar

    planar, _ = as_planar(audio, channels_last=channels_last, dtype=np.float64)
    peak = peak_level(planar)
    rms = rms_level(planar)
    return LevelReport(
        peak_db=float(linear_to_db(peak)),
        true_peak_db=float(linear_to_db(true_peak_level(planar))),
        rms_db=float(linear_to_db(rms)),
        crest_factor_db=float(linear_to_db(peak) - linear_to_db(rms)),
        per_channel_peak_db=tuple(float(linear_to_db(peak_level(ch))) for ch in planar),
    )


class NormalizeEffect(Effect):
    """Scale a buffer so its measured level lands on ``target_db``.

    Normalisation is a single global gain — it needs to see the whole signal
    before it can pick that gain, so this effect is offline only.

    Parameters
    ----------
    target_db:
        Desired level in dBFS. ``-1.0`` is a common mastering headroom target;
        ``-0.1`` is about as hot as is safe with :attr:`NormalizeMode.TRUE_PEAK`.
    mode:
        Which measurement to drive to ``target_db``.
    per_channel:
        ``False`` (default) applies one gain to every channel, preserving the
        stereo image. ``True`` normalises each channel independently, which
        will shift the image and is normally only wanted for multi-mono stems.
    ceiling_db:
        Optional hard limit on the resulting sample peak. RMS normalisation in
        particular can ask for more gain than the headroom allows; setting a
        ceiling caps the gain instead of clipping.

    Examples
    --------
    >>> import numpy as np
    >>> quiet = 0.1 * np.sin(2 * np.pi * 1000 * np.arange(4800) / 48_000)
    >>> loud = NormalizeEffect(target_db=-1.0).process(quiet, 48_000)
    >>> round(float(20 * np.log10(np.max(np.abs(loud)))), 2)
    -1.0
    """

    name = "Normalize"
    is_offline_only = True

    def __init__(
        self,
        target_db: float = -1.0,
        mode: NormalizeMode | str = NormalizeMode.PEAK,
        per_channel: bool = False,
        ceiling_db: Optional[float] = None,
        max_gain_db: float = 60.0,
        enabled: bool = True,
    ) -> None:
        super().__init__(enabled=enabled)
        self.target_db = float(target_db)
        self.mode = NormalizeMode.coerce(mode)
        self.per_channel = bool(per_channel)
        self.ceiling_db = None if ceiling_db is None else float(ceiling_db)
        self.max_gain_db = float(max_gain_db)
        self._last_gain_db: tuple[float, ...] = ()

    @property
    def applied_gain_db(self) -> tuple[float, ...]:
        """Gain chosen by the most recent :meth:`process` call, per channel."""
        return self._last_gain_db

    def parameters(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "target_db": self.target_db,
            "mode": self.mode.value,
            "per_channel": self.per_channel,
            "ceiling_db": self.ceiling_db,
            "max_gain_db": self.max_gain_db,
        }

    def _measure(self, block: np.ndarray) -> float:
        if self.mode is NormalizeMode.PEAK:
            return peak_level(block)
        if self.mode is NormalizeMode.TRUE_PEAK:
            return true_peak_level(block)
        return rms_level(block)

    def _gain_for(self, block: np.ndarray) -> float:
        measured = self._measure(block)
        if measured <= 0.0:
            return 1.0  # digital silence: nothing to normalise
        gain = float(db_to_linear(self.target_db)) / measured
        gain = min(gain, float(db_to_linear(self.max_gain_db)))

        if self.ceiling_db is not None:
            sample_peak = peak_level(block)
            if sample_peak > 0.0:
                gain = min(gain, float(db_to_linear(self.ceiling_db)) / sample_peak)
        return gain

    def _process_planar(self, audio: np.ndarray, sample_rate: float) -> np.ndarray:
        if self.per_channel:
            gains = np.array([self._gain_for(channel) for channel in audio], dtype=np.float64)
            self._last_gain_db = tuple(float(linear_to_db(g)) for g in gains)
            return audio * gains[:, np.newaxis].astype(audio.dtype)

        gain = self._gain_for(audio)
        self._last_gain_db = (float(linear_to_db(gain)),) * audio.shape[0]
        return audio * np.asarray(gain, dtype=audio.dtype)
