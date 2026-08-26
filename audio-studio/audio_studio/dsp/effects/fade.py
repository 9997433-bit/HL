"""Fade in / fade out with the curve shapes an editor is expected to offer.

Curve choice matters more than it looks. A linear amplitude ramp sounds like it
rushes the middle of the fade because loudness perception is closer to
logarithmic, and crossfading two uncorrelated signals with linear ramps dips
3 dB in the middle. Hence :class:`FadeShape` offers logarithmic and equal-power
alternatives alongside the linear default.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

import numpy as np

from ..util import db_to_linear
from .base import Effect

__all__ = ["FadeShape", "FadeEffect", "fade_envelope", "apply_fade"]


class FadeShape(str, Enum):
    """Shape of the gain envelope over the fade duration.

    ``LINEAR``
        Straight amplitude ramp. Neutral, and the right choice for very short
        de-click fades.
    ``LOGARITHMIC``
        Straight line in *decibels*, from :attr:`FadeEffect.floor_db` to unity.
        This is the fade that sounds most even to the ear over long durations.
    ``EXPONENTIAL``
        Squared amplitude ramp: stays quiet longer, then rushes up at the end.
    ``COSINE``
        Raised-cosine S-curve, tangent to flat at both ends, so it joins the
        surrounding audio without a slope discontinuity.
    ``EQUAL_POWER``
        Square-root ramp whose *power* is linear. Two of these back to back
        crossfade uncorrelated material at constant loudness.
    """

    LINEAR = "linear"
    LOGARITHMIC = "logarithmic"
    EXPONENTIAL = "exponential"
    COSINE = "cosine"
    EQUAL_POWER = "equal_power"

    @classmethod
    def coerce(cls, value: FadeShape | str) -> FadeShape:
        if isinstance(value, cls):
            return value
        key = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "log": cls.LOGARITHMIC,
            "exp": cls.EXPONENTIAL,
            "s_curve": cls.COSINE,
            "scurve": cls.COSINE,
            "sine": cls.EQUAL_POWER,
            "constant_power": cls.EQUAL_POWER,
        }
        if key in aliases:
            return aliases[key]
        try:
            return cls(key)
        except ValueError as exc:
            raise ValueError(f"unknown fade shape {value!r}") from exc


def fade_envelope(
    length: int,
    shape: FadeShape | str = FadeShape.LINEAR,
    fade_in: bool = True,
    curve: float = 0.0,
    floor_db: float = -60.0,
    dtype: np.dtype | type = np.float64,
) -> np.ndarray:
    """Build a gain envelope of ``length`` samples rising from 0 to 1.

    Parameters
    ----------
    curve:
        Skew in ``[-1, 1]`` applied on top of ``shape``, matching the draggable
        curve handle in a DAW's fade UI. Positive values make the fade start
        slower and finish faster; negative values do the reverse; ``0`` leaves
        the base shape untouched.
    floor_db:
        Level the logarithmic shape starts from. A true ``-inf`` start is not
        representable, and anything below about -60 dB is inaudible anyway.

    Returns
    -------
    numpy.ndarray
        ``length`` gains. ``fade_in=False`` returns the time-reversed (falling)
        envelope, so a fade-in and a fade-out of equal length are exact
        mirrors and sum to a click-free crossfade.
    """
    shape = FadeShape.coerce(shape)
    length = int(length)
    if length <= 0:
        return np.zeros(0, dtype=dtype)
    if length == 1:
        return np.ones(1, dtype=dtype)

    t = np.linspace(0.0, 1.0, length, endpoint=True, dtype=np.float64)

    curve = float(np.clip(curve, -1.0, 1.0))
    if curve != 0.0:
        # Map the [-1, 1] handle onto a power in [1/4, 4]; t**p keeps the
        # endpoints pinned at 0 and 1 whatever the skew.
        t = np.power(t, 4.0**curve)

    if shape is FadeShape.LINEAR:
        envelope = t
    elif shape is FadeShape.EXPONENTIAL:
        envelope = np.square(t)
    elif shape is FadeShape.EQUAL_POWER:
        envelope = np.sqrt(t)
    elif shape is FadeShape.COSINE:
        envelope = 0.5 - 0.5 * np.cos(np.pi * t)
    else:  # LOGARITHMIC — linear in dB from floor_db up to 0 dB
        floor = float(min(floor_db, -1.0))
        envelope = db_to_linear(floor * (1.0 - t))
        # Re-anchor so the fade truly starts at silence rather than at floor_db.
        start = envelope[0]
        envelope = (envelope - start) / (1.0 - start)

    if not fade_in:
        envelope = envelope[::-1]
    return np.ascontiguousarray(envelope, dtype=dtype)


def apply_fade(
    audio: np.ndarray,
    sample_rate: float,
    fade_in_s: float = 0.0,
    fade_out_s: float = 0.0,
    shape: FadeShape | str = FadeShape.LINEAR,
    curve: float = 0.0,
    channels_last: bool | None = None,
) -> np.ndarray:
    """Convenience wrapper: build a :class:`FadeEffect` and run it once."""
    effect = FadeEffect(
        fade_in_s=fade_in_s, fade_out_s=fade_out_s, shape=shape, curve=curve
    )
    return effect.process(audio, sample_rate, channels_last=channels_last)


class FadeEffect(Effect):
    """Fade the head and/or tail of a buffer.

    Both fades are measured from the ends of the buffer, so the effect needs to
    know the total length and is offline only. Overlapping fades (in + out
    longer than the signal) are shrunk proportionally rather than fighting each
    other in the middle.

    Examples
    --------
    >>> import numpy as np
    >>> faded = FadeEffect(fade_in_s=0.5).process(np.ones(48_000), 48_000)
    >>> float(faded[0]), round(float(faded[24_000]), 3), float(faded[-1])
    (0.0, 1.0, 1.0)
    """

    name = "Fade"
    is_offline_only = True

    def __init__(
        self,
        fade_in_s: float = 0.0,
        fade_out_s: float = 0.0,
        shape: FadeShape | str = FadeShape.LINEAR,
        curve: float = 0.0,
        floor_db: float = -60.0,
        enabled: bool = True,
    ) -> None:
        super().__init__(enabled=enabled)
        self.fade_in_s = float(fade_in_s)
        self.fade_out_s = float(fade_out_s)
        self.shape = FadeShape.coerce(shape)
        self.curve = float(curve)
        self.floor_db = float(floor_db)
        if self.fade_in_s < 0 or self.fade_out_s < 0:
            raise ValueError("fade durations must be non-negative")

    def parameters(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "fade_in_s": self.fade_in_s,
            "fade_out_s": self.fade_out_s,
            "shape": self.shape.value,
            "curve": self.curve,
            "floor_db": self.floor_db,
        }

    def envelope(self, n_samples: int, sample_rate: float) -> np.ndarray:
        """The full-length gain envelope this effect would multiply in.

        Exposed so a waveform view can draw the fade handles over the audio.
        """
        n = int(n_samples)
        gains = np.ones(n, dtype=np.float64)
        if n == 0:
            return gains

        n_in = int(round(self.fade_in_s * sample_rate))
        n_out = int(round(self.fade_out_s * sample_rate))
        if n_in + n_out > n and n_in + n_out > 0:
            scale = n / (n_in + n_out)
            n_in = int(n_in * scale)
            n_out = n - n_in
        n_in = min(max(n_in, 0), n)
        n_out = min(max(n_out, 0), n - n_in)

        if n_in > 0:
            gains[:n_in] = fade_envelope(
                n_in, self.shape, fade_in=True, curve=self.curve, floor_db=self.floor_db
            )
        if n_out > 0:
            gains[n - n_out :] = fade_envelope(
                n_out, self.shape, fade_in=False, curve=self.curve, floor_db=self.floor_db
            )
        return gains

    def _process_planar(self, audio: np.ndarray, sample_rate: float) -> np.ndarray:
        if self.fade_in_s == 0.0 and self.fade_out_s == 0.0:
            return audio.copy()
        gains = self.envelope(audio.shape[1], sample_rate).astype(audio.dtype, copy=False)
        return audio * gains
