"""Three-band parametric equaliser built from RBJ cookbook biquads.

Each band is an independent second-order section whose type, frequency, gain
and Q are all adjustable, so the "3-band" default layout (low shelf / peaking
mid / high shelf) is only a starting point — any band can become a peak, a
shelf, a pass filter or a notch.

Filtering runs through ``scipy.signal.sosfilt`` in second-order-section form,
which stays numerically well-behaved at the low corner frequencies where a
direct-form high-order implementation would lose precision.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
from scipy.signal import sosfilt, sosfreqz

from ..util import db_to_linear
from .base import Effect

__all__ = ["FilterType", "EQBand", "ThreeBandEQ", "ParametricEQ"]


class FilterType(str, Enum):
    """Biquad response shapes from the Audio EQ Cookbook."""

    PEAKING = "peaking"
    LOW_SHELF = "low_shelf"
    HIGH_SHELF = "high_shelf"
    LOW_PASS = "low_pass"
    HIGH_PASS = "high_pass"
    BAND_PASS = "band_pass"
    NOTCH = "notch"
    ALL_PASS = "all_pass"

    @classmethod
    def coerce(cls, value: "FilterType | str") -> "FilterType":
        if isinstance(value, cls):
            return value
        key = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "bell": cls.PEAKING,
            "peak": cls.PEAKING,
            "lowshelf": cls.LOW_SHELF,
            "highshelf": cls.HIGH_SHELF,
            "lowpass": cls.LOW_PASS,
            "highpass": cls.HIGH_PASS,
            "bandpass": cls.BAND_PASS,
            "allpass": cls.ALL_PASS,
        }
        if key in aliases:
            return aliases[key]
        try:
            return cls(key)
        except ValueError as exc:
            raise ValueError(f"unknown filter type {value!r}") from exc

    @property
    def uses_gain(self) -> bool:
        """Whether ``gain_db`` affects this response shape."""
        return self in (FilterType.PEAKING, FilterType.LOW_SHELF, FilterType.HIGH_SHELF)


@dataclass
class EQBand:
    """One parametric band.

    Parameters
    ----------
    frequency:
        Centre frequency for peaking/notch/bandpass, or corner frequency for
        shelves and pass filters, in hertz.
    gain_db:
        Boost (positive) or cut (negative). Ignored by filter types where
        :attr:`FilterType.uses_gain` is false.
    q:
        Quality factor. For a peaking filter, bandwidth in octaves is roughly
        ``2/Q`` at moderate Q; for a shelf it controls the steepness of the
        transition, with ``1/sqrt(2)`` giving the classic maximally-flat knee.
    """

    frequency: float = 1000.0
    gain_db: float = 0.0
    q: float = 0.707
    type: FilterType = FilterType.PEAKING
    enabled: bool = True
    label: str = ""

    def __post_init__(self) -> None:
        self.type = FilterType.coerce(self.type)
        self.frequency = float(self.frequency)
        self.gain_db = float(self.gain_db)
        self.q = float(self.q)
        if self.frequency <= 0:
            raise ValueError("band frequency must be positive")
        if self.q <= 0:
            raise ValueError("band Q must be positive")

    @property
    def is_bypassed(self) -> bool:
        """A gain-type band at exactly 0 dB is a pass-through; skip its maths."""
        return not self.enabled or (self.type.uses_gain and self.gain_db == 0.0)

    def bandwidth_octaves(self) -> float:
        """Equivalent bandwidth in octaves, the alternative to Q in many UIs."""
        return (2.0 / math.log(2.0)) * math.asinh(1.0 / (2.0 * self.q))

    def set_bandwidth_octaves(self, octaves: float) -> None:
        """Set :attr:`q` from a bandwidth expressed in octaves."""
        if octaves <= 0:
            raise ValueError("bandwidth must be positive")
        self.q = 1.0 / (2.0 * math.sinh(math.log(2.0) / 2.0 * octaves))

    def biquad(self, sample_rate: float) -> np.ndarray:
        """Normalised ``[b0, b1, b2, a0, a1, a2]`` coefficients (a0 == 1)."""
        return _design_biquad(self.type, self.frequency, self.gain_db, self.q, sample_rate)

    def parameters(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "frequency": self.frequency,
            "gain_db": self.gain_db,
            "q": self.q,
            "enabled": self.enabled,
            "label": self.label,
        }


def _design_biquad(
    filter_type: FilterType,
    frequency: float,
    gain_db: float,
    q: float,
    sample_rate: float,
) -> np.ndarray:
    """RBJ Audio EQ Cookbook biquad, normalised so that ``a0 == 1``.

    The corner frequency is clamped just below Nyquist: a band parked above it
    has no meaning after sampling, and letting ``tan`` blow up there would
    produce NaNs rather than an obviously wrong but stable response.
    """
    nyquist = sample_rate / 2.0
    f0 = min(max(float(frequency), 1e-6), nyquist * 0.999)
    w0 = 2.0 * math.pi * f0 / sample_rate
    cos_w0 = math.cos(w0)
    sin_w0 = math.sin(w0)
    alpha = sin_w0 / (2.0 * q)
    A = 10.0 ** (gain_db / 40.0)  # amplitude gain of a shelf/peak is sqrt(power)

    if filter_type is FilterType.PEAKING:
        b0 = 1.0 + alpha * A
        b1 = -2.0 * cos_w0
        b2 = 1.0 - alpha * A
        a0 = 1.0 + alpha / A
        a1 = -2.0 * cos_w0
        a2 = 1.0 - alpha / A
    elif filter_type is FilterType.LOW_SHELF:
        sqrtA = math.sqrt(A)
        shared = 2.0 * sqrtA * alpha
        b0 = A * ((A + 1.0) - (A - 1.0) * cos_w0 + shared)
        b1 = 2.0 * A * ((A - 1.0) - (A + 1.0) * cos_w0)
        b2 = A * ((A + 1.0) - (A - 1.0) * cos_w0 - shared)
        a0 = (A + 1.0) + (A - 1.0) * cos_w0 + shared
        a1 = -2.0 * ((A - 1.0) + (A + 1.0) * cos_w0)
        a2 = (A + 1.0) + (A - 1.0) * cos_w0 - shared
    elif filter_type is FilterType.HIGH_SHELF:
        sqrtA = math.sqrt(A)
        shared = 2.0 * sqrtA * alpha
        b0 = A * ((A + 1.0) + (A - 1.0) * cos_w0 + shared)
        b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * cos_w0)
        b2 = A * ((A + 1.0) + (A - 1.0) * cos_w0 - shared)
        a0 = (A + 1.0) - (A - 1.0) * cos_w0 + shared
        a1 = 2.0 * ((A - 1.0) - (A + 1.0) * cos_w0)
        a2 = (A + 1.0) - (A - 1.0) * cos_w0 - shared
    elif filter_type is FilterType.LOW_PASS:
        b0 = (1.0 - cos_w0) / 2.0
        b1 = 1.0 - cos_w0
        b2 = b0
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_w0
        a2 = 1.0 - alpha
    elif filter_type is FilterType.HIGH_PASS:
        b0 = (1.0 + cos_w0) / 2.0
        b1 = -(1.0 + cos_w0)
        b2 = b0
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_w0
        a2 = 1.0 - alpha
    elif filter_type is FilterType.BAND_PASS:  # constant 0 dB peak gain
        b0 = alpha
        b1 = 0.0
        b2 = -alpha
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_w0
        a2 = 1.0 - alpha
    elif filter_type is FilterType.NOTCH:
        b0 = 1.0
        b1 = -2.0 * cos_w0
        b2 = 1.0
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_w0
        a2 = 1.0 - alpha
    else:  # ALL_PASS
        b0 = 1.0 - alpha
        b1 = -2.0 * cos_w0
        b2 = 1.0 + alpha
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_w0
        a2 = 1.0 - alpha

    return np.array([b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0], dtype=np.float64)


_IDENTITY_SOS = np.array([1.0, 0.0, 0.0, 1.0, 0.0, 0.0], dtype=np.float64)


class ParametricEQ(Effect):
    """Cascade of arbitrarily many :class:`EQBand` sections."""

    name = "Parametric EQ"

    def __init__(
        self,
        bands: Optional[Sequence[EQBand]] = None,
        output_gain_db: float = 0.0,
        enabled: bool = True,
    ) -> None:
        super().__init__(enabled=enabled)
        self.bands: List[EQBand] = list(bands or [])
        self.output_gain_db = float(output_gain_db)
        self._zi: Optional[np.ndarray] = None
        self._sos_cache: Optional[np.ndarray] = None
        self._cache_key: Optional[tuple] = None

    # -- coefficients -----------------------------------------------------

    def _state_key(self, sample_rate: float) -> tuple:
        return (float(sample_rate),) + tuple(
            (b.type, b.frequency, b.gain_db, b.q, b.enabled) for b in self.bands
        )

    def sos(self, sample_rate: float) -> np.ndarray:
        """Second-order-section matrix for the currently active bands.

        Always contains at least one section (an identity pass-through) so the
        streaming state layout stays constant while bands are toggled.
        """
        key = self._state_key(sample_rate)
        if self._sos_cache is not None and self._cache_key == key:
            return self._sos_cache
        sections = [band.biquad(sample_rate) for band in self.bands if not band.is_bypassed]
        matrix = np.stack(sections) if sections else _IDENTITY_SOS[np.newaxis, :].copy()
        self._sos_cache = matrix
        self._cache_key = key
        self._zi = None
        return matrix

    def frequency_response(
        self,
        frequencies: np.ndarray,
        sample_rate: float,
    ) -> np.ndarray:
        """Complex transfer function sampled at ``frequencies`` (Hz).

        Use ``20*log10(abs(...))`` for the magnitude curve an EQ UI draws, and
        ``numpy.angle`` for the phase trace.
        """
        freqs = np.asarray(frequencies, dtype=np.float64)
        _, response = sosfreqz(self.sos(sample_rate), worN=freqs, fs=sample_rate)
        return response * db_to_linear(self.output_gain_db)

    def magnitude_response_db(
        self,
        frequencies: np.ndarray,
        sample_rate: float,
    ) -> np.ndarray:
        """Magnitude of :meth:`frequency_response` in dB."""
        magnitude = np.abs(self.frequency_response(frequencies, sample_rate))
        return 20.0 * np.log10(np.maximum(magnitude, 1e-12))

    def response_curve(
        self,
        sample_rate: float,
        n_points: int = 512,
        f_min: float = 20.0,
        f_max: Optional[float] = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """``(frequencies, magnitude_db)`` on a log grid, ready to plot."""
        f_max = f_max if f_max is not None else sample_rate / 2.0
        freqs = np.geomspace(max(f_min, 1e-3), min(f_max, sample_rate / 2.0), n_points)
        return freqs, self.magnitude_response_db(freqs, sample_rate)

    # -- Effect ------------------------------------------------------------

    def prepare(self, sample_rate: float, n_channels: int) -> None:
        super().prepare(sample_rate, n_channels)
        self._sos_cache = None
        self._cache_key = None
        self._zi = None

    def reset(self) -> None:
        self._zi = None

    def parameters(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "output_gain_db": self.output_gain_db,
            "bands": [band.parameters() for band in self.bands],
        }

    def _process_planar(self, audio: np.ndarray, sample_rate: float) -> np.ndarray:
        sos = self.sos(sample_rate)
        n_channels = audio.shape[0]

        if self._zi is None or self._zi.shape != (sos.shape[0], n_channels, 2):
            # Zero initial state, not scipy's DC steady state: audio starts from
            # silence, so a zero-state filter is both the causal answer and the
            # one whose impulse response is the filter's actual impulse response.
            self._zi = np.zeros((sos.shape[0], n_channels, 2), dtype=np.float64)

        filtered, self._zi = sosfilt(sos, audio.astype(np.float64, copy=False), axis=-1, zi=self._zi)
        if self.output_gain_db != 0.0:
            filtered = filtered * db_to_linear(self.output_gain_db)
        return filtered.astype(audio.dtype, copy=False)


class ThreeBandEQ(ParametricEQ):
    """The classic low / mid / high parametric layout.

    Defaults mirror a mixing-console channel strip: a 100 Hz low shelf, a
    sweepable 1 kHz bell, and an 8 kHz high shelf, all flat until moved.

    Examples
    --------
    >>> eq = ThreeBandEQ(low_gain_db=6.0, mid_frequency=2500.0, mid_gain_db=-3.0)
    >>> round(float(eq.magnitude_response_db([2500.0], 48_000)[0]), 2)
    -3.0
    """

    name = "3-Band EQ"

    def __init__(
        self,
        low_frequency: float = 100.0,
        low_gain_db: float = 0.0,
        low_q: float = 0.707,
        mid_frequency: float = 1000.0,
        mid_gain_db: float = 0.0,
        mid_q: float = 1.0,
        high_frequency: float = 8000.0,
        high_gain_db: float = 0.0,
        high_q: float = 0.707,
        output_gain_db: float = 0.0,
        enabled: bool = True,
    ) -> None:
        bands = [
            EQBand(low_frequency, low_gain_db, low_q, FilterType.LOW_SHELF, label="Low"),
            EQBand(mid_frequency, mid_gain_db, mid_q, FilterType.PEAKING, label="Mid"),
            EQBand(high_frequency, high_gain_db, high_q, FilterType.HIGH_SHELF, label="High"),
        ]
        super().__init__(bands=bands, output_gain_db=output_gain_db, enabled=enabled)

    @property
    def low(self) -> EQBand:
        return self.bands[0]

    @property
    def mid(self) -> EQBand:
        return self.bands[1]

    @property
    def high(self) -> EQBand:
        return self.bands[2]

    def set_low(self, frequency: Optional[float] = None, gain_db: Optional[float] = None,
                q: Optional[float] = None) -> "ThreeBandEQ":
        return self._set(self.low, frequency, gain_db, q)

    def set_mid(self, frequency: Optional[float] = None, gain_db: Optional[float] = None,
                q: Optional[float] = None) -> "ThreeBandEQ":
        return self._set(self.mid, frequency, gain_db, q)

    def set_high(self, frequency: Optional[float] = None, gain_db: Optional[float] = None,
                 q: Optional[float] = None) -> "ThreeBandEQ":
        return self._set(self.high, frequency, gain_db, q)

    def _set(
        self,
        band: EQBand,
        frequency: Optional[float],
        gain_db: Optional[float],
        q: Optional[float],
    ) -> "ThreeBandEQ":
        if frequency is not None:
            band.frequency = float(frequency)
        if gain_db is not None:
            band.gain_db = float(gain_db)
        if q is not None:
            band.q = float(q)
        return self
