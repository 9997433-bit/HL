"""Spectral selection editing: attenuate or remove a band of a signal.

This is the offline half of Adobe Audition's spectral frequency display, where
a rectangle drawn over the spectrogram is attenuated or deleted outright. The
time axis of that rectangle is handled by the caller — it selects which samples
to hand over — so everything here is about the *frequency* axis: build a
per-bin gain mask, multiply the STFT by it, and resynthesise with the weighted
overlap-add inverse in :mod:`audio_studio.dsp.spectral`.

Two details make the difference between a usable notch and an obvious one:

*Feathering.*
    A rectangular mask is a brick-wall filter re-designed on every frame, and
    its impulse response rings for the whole window. Tapering the mask across a
    couple of bins on each side of the band costs a little selectivity and buys
    a large drop in the "birdie" artefacts that hard gating is known for. The
    taper sits *outside* the requested band, so the band the caller asked for
    is always attenuated in full.

*Overlap.*
    The mask varies from frame to frame only because the signal does, but the
    reconstruction still has to be seamless. The default 75%-overlap Hann
    analysis is well past the point where WOLA resynthesis of a modified
    spectrum stops sounding like a sequence of windows.

Examples
--------
>>> import numpy as np
>>> sr = 48_000
>>> t = np.arange(sr) / sr
>>> signal = 0.5 * np.sin(2 * np.pi * 1_000 * t) + 0.5 * np.sin(2 * np.pi * 5_000 * t)
>>> cleaned = remove_band(signal, sr, SpectralBand(4_800.0, 5_200.0))
>>> def level(x, frequency):                # amplitude of one tone, by projection
...     phasor = np.exp(-2j * np.pi * frequency * np.arange(x.size) / sr)
...     return float(2 * abs(np.vdot(phasor, x)) / x.size)
>>> body = cleaned[sr // 4 : -sr // 4]      # away from the analysis edges
>>> round(level(body, 1_000.0), 3), level(body, 5_000.0) < 1e-4
(0.5, True)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .spectral import SpectralAnalyzer, SpectralConfig
from .util import MAX_SANE_CHANNELS, as_planar, next_pow2
from .windows import WindowType

__all__ = [
    "ATTENUATION_DB",
    "DEFAULT_FFT_SIZE",
    "TRANSITION_BINS",
    "SpectralBand",
    "apply_spectral_gain",
    "attenuate_band",
    "band_gain",
    "remove_band",
]

#: Transform length used when the caller does not choose one. At 48 kHz this
#: is a 23 Hz bin spacing and a 43 ms window — fine enough to pick a hum
#: harmonic out from between two notes, short enough not to smear a transient
#: across the whole selection.
DEFAULT_FFT_SIZE: int = 2048

#: Default attenuation for :func:`attenuate_band`. Deep enough to push a
#: resonance or a cough well below the material around it, shallow enough that
#: what is left still sounds like part of the recording.
ATTENUATION_DB: float = -12.0

#: Width of the mask's raised-cosine skirt, in FFT bins on each side.
TRANSITION_BINS: float = 2.0


@dataclass(frozen=True, slots=True)
class SpectralBand:
    """A closed frequency interval ``[low_hz, high_hz]`` to be gained."""

    low_hz: float
    high_hz: float

    def __post_init__(self) -> None:
        low, high = sorted((float(self.low_hz), float(self.high_hz)))
        if low < 0.0:
            raise ValueError(f"band edges must be non-negative, got {self!r}")
        if not math.isfinite(high):
            raise ValueError(f"band edges must be finite, got {self!r}")
        object.__setattr__(self, "low_hz", low)
        object.__setattr__(self, "high_hz", high)

    @property
    def width_hz(self) -> float:
        return self.high_hz - self.low_hz

    @property
    def center_hz(self) -> float:
        """Geometric centre — the bin a musician would call the middle."""
        if self.low_hz <= 0.0:
            return self.high_hz / 2.0
        return math.sqrt(self.low_hz * self.high_hz)

    @property
    def is_empty(self) -> bool:
        return self.width_hz <= 0.0

    def clamped(self, nyquist_hz: float) -> SpectralBand:
        """Clip the band to ``[0, nyquist_hz]``."""
        limit = max(float(nyquist_hz), 0.0)
        return SpectralBand(min(self.low_hz, limit), min(self.high_hz, limit))

    def describe(self) -> str:
        return f"{self.low_hz:.0f}–{self.high_hz:.0f} Hz"


def band_gain(
    frequencies: np.ndarray,
    band: SpectralBand,
    gain: float,
    transition_hz: float = 0.0,
) -> np.ndarray:
    """Per-bin multipliers: ``gain`` inside ``band``, ``1.0`` outside.

    ``transition_hz`` adds a raised-cosine skirt on each side of the band,
    outside it, so the requested interval is always gained in full.
    """
    bins = np.asarray(frequencies, dtype=np.float64)
    if band.is_empty:
        return np.ones_like(bins)

    if transition_hz <= 0.0:
        inside = (bins >= band.low_hz) & (bins <= band.high_hz)
        return np.where(inside, float(gain), 1.0)

    rise = np.clip((bins - (band.low_hz - transition_hz)) / transition_hz, 0.0, 1.0)
    fall = np.clip(((band.high_hz + transition_hz) - bins) / transition_hz, 0.0, 1.0)
    weight = 0.5 - 0.5 * np.cos(np.pi * np.minimum(rise, fall))
    return 1.0 + (float(gain) - 1.0) * weight


def apply_spectral_gain(
    audio: np.ndarray,
    sample_rate: float,
    band: SpectralBand,
    gain_db: float,
    *,
    fft_size: int = DEFAULT_FFT_SIZE,
    hop_size: int | None = None,
    window: WindowType | str = WindowType.HANN,
    transition_hz: float | None = None,
    channels_last: bool | None = None,
) -> np.ndarray:
    """Gain one frequency band of ``audio`` by ``gain_db``.

    ``gain_db=-inf`` removes the band outright. Every sample handed in is
    processed; restrict the *time* extent of the edit by slicing the buffer
    before the call.

    The result has the same shape, layout and dtype family as the input, so an
    interleaved ``(n_frames, n_channels)`` editor buffer comes back
    interleaved.
    """
    planar, was_mono, interleaved = _to_planar(audio, channels_last)
    n_samples = int(planar.shape[1])
    gain = 0.0 if gain_db == -math.inf else float(10.0 ** (float(gain_db) / 20.0))

    if n_samples == 0 or band.is_empty or gain == 1.0 or sample_rate <= 0:
        return _restore(planar.copy(), was_mono, interleaved)

    config = SpectralConfig(
        sample_rate=sample_rate,
        fft_size=_usable_fft_size(fft_size, n_samples),
        hop_size=hop_size,
        window=window,
        center=True,
        dtype=planar.dtype,
    )
    analyzer = SpectralAnalyzer(config)
    skirt = (
        TRANSITION_BINS * config.bin_spacing_hz if transition_hz is None else float(transition_hz)
    )
    mask = band_gain(config.frequencies(), band.clamped(sample_rate / 2.0), gain, skirt)

    stft = analyzer.stft(planar, channels_last=False)
    stft *= mask.astype(stft.real.dtype, copy=False)
    return _restore(analyzer.istft(stft, length=n_samples), was_mono, interleaved)


def attenuate_band(
    audio: np.ndarray,
    sample_rate: float,
    band: SpectralBand,
    gain_db: float = ATTENUATION_DB,
    **kwargs,
) -> np.ndarray:
    """Duck one band by ``gain_db`` (-12 dB by default)."""
    return apply_spectral_gain(audio, sample_rate, band, gain_db, **kwargs)


def remove_band(
    audio: np.ndarray,
    sample_rate: float,
    band: SpectralBand,
    **kwargs,
) -> np.ndarray:
    """Zero one band and resynthesise what is left."""
    return apply_spectral_gain(audio, sample_rate, band, -math.inf, **kwargs)


def _usable_fft_size(fft_size: int, n_samples: int) -> int:
    """``fft_size``, never longer than the signal rounded up to a power of two.

    A window longer than the audio it analyses spends its resolution on the
    zero padding around it, and makes the WOLA denominator vanish over most of
    a short selection.
    """
    return max(4, min(int(fft_size), next_pow2(n_samples)))


def _to_planar(
    audio: np.ndarray, channels_last: bool | None
) -> tuple[np.ndarray, bool, bool]:
    """``(planar, was_mono, was_interleaved)``, resolving auto-detected layout."""
    array = np.asarray(audio)
    if array.ndim == 2 and channels_last is None:
        channels_last = array.shape[1] < array.shape[0] or array.shape[0] > MAX_SANE_CHANNELS
    dtype = np.float64 if array.dtype == np.float64 else np.float32
    planar, was_mono = as_planar(array, channels_last=channels_last, dtype=dtype)
    return planar, was_mono, bool(channels_last) and not was_mono


def _restore(planar: np.ndarray, was_mono: bool, interleaved: bool) -> np.ndarray:
    if was_mono:
        return planar[0]
    return np.ascontiguousarray(planar.T) if interleaved else planar
