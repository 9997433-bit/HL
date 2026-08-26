"""Shared conventions and small helpers for the DSP layer.

Buffer convention
-----------------
Every public DSP entry point in :mod:`audio_studio.dsp` speaks *planar* audio:
a ``(n_channels, n_samples)`` float array. Mono may also be passed as a plain
1-D ``(n_samples,)`` array, in which case results are returned 1-D as well.

File I/O libraries (``soundfile``, ``librosa``, PortAudio callbacks) hand back
*interleaved* ``(n_samples, n_channels)`` frames instead, so :func:`as_planar`
and :func:`as_interleaved` are provided to convert at the boundary.
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "MAX_SANE_CHANNELS",
    "as_planar",
    "as_interleaved",
    "restore_layout",
    "db_to_linear",
    "linear_to_db",
    "amplitude_to_db",
    "power_to_db",
    "next_pow2",
    "peak_level",
    "rms_level",
    "true_peak_level",
]

#: Channel counts above this are assumed to be a transposed (interleaved) buffer.
MAX_SANE_CHANNELS = 64

#: Anything quieter than this is clamped before taking a logarithm.
_DB_EPS = 1e-20


def as_planar(
    audio: np.ndarray,
    channels_last: bool | None = None,
    dtype: np.dtype | type | None = None,
) -> tuple[np.ndarray, bool]:
    """Normalise ``audio`` to a planar ``(n_channels, n_samples)`` array.

    Parameters
    ----------
    audio:
        1-D mono or 2-D multichannel audio.
    channels_last:
        ``True`` if the input is interleaved ``(n_samples, n_channels)``,
        ``False`` if it is already planar. ``None`` (the default) auto-detects
        by assuming the *shorter* axis holds the channels, which is correct for
        any buffer longer than its channel count.
    dtype:
        Optional target dtype. Only ``float32``/``float64`` are meaningful;
        integer input is always promoted to ``float32`` because every effect in
        this package works in floating point.

    Returns
    -------
    (planar, was_mono)
        ``was_mono`` records whether the caller passed a 1-D array so that
        :func:`restore_layout` can hand back the same shape.
    """
    arr = np.asarray(audio)
    if arr.ndim == 0:
        raise ValueError("audio must be at least 1-D")

    if dtype is None:
        dtype = arr.dtype if arr.dtype in (np.float32, np.float64) else np.float32
    arr = arr.astype(dtype, copy=False)

    if arr.ndim == 1:
        return arr[np.newaxis, :], True
    if arr.ndim != 2:
        raise ValueError(f"expected 1-D or 2-D audio, got shape {arr.shape}")

    if channels_last is None:
        channels_last = arr.shape[1] < arr.shape[0] or arr.shape[0] > MAX_SANE_CHANNELS
    if channels_last:
        arr = np.ascontiguousarray(arr.T)
    return arr, False


def as_interleaved(planar: np.ndarray) -> np.ndarray:
    """Convert a planar buffer to interleaved ``(n_samples, n_channels)``."""
    arr = np.asarray(planar)
    if arr.ndim == 1:
        return arr[:, np.newaxis]
    return np.ascontiguousarray(arr.T)


def restore_layout(planar: np.ndarray, was_mono: bool) -> np.ndarray:
    """Undo the shape change performed by :func:`as_planar`."""
    if was_mono:
        return planar[0]
    return planar


def db_to_linear(db: float | np.ndarray) -> np.ndarray:
    """Convert a decibel *amplitude* ratio to a linear gain factor."""
    return np.power(10.0, np.asarray(db, dtype=np.float64) / 20.0)


def linear_to_db(linear: float | np.ndarray) -> np.ndarray:
    """Convert a linear amplitude ratio to decibels."""
    values = np.abs(np.asarray(linear, dtype=np.float64))
    return 20.0 * np.log10(np.maximum(values, _DB_EPS))


def amplitude_to_db(
    amplitude: np.ndarray,
    reference: float = 1.0,
    floor_db: float = -200.0,
) -> np.ndarray:
    """Amplitude spectrum -> dB, clamped at ``floor_db``.

    ``reference`` is the amplitude that maps to 0 dB; the default of ``1.0``
    yields dBFS for audio normalised to the +-1.0 full-scale range.
    """
    values = np.abs(np.asarray(amplitude, dtype=np.float64)) / float(reference)
    with np.errstate(divide="ignore"):
        db = 20.0 * np.log10(np.maximum(values, _DB_EPS))
    return np.maximum(db, floor_db)


def power_to_db(
    power: np.ndarray,
    reference: float = 1.0,
    floor_db: float = -200.0,
) -> np.ndarray:
    """Power (or PSD) spectrum -> dB, clamped at ``floor_db``."""
    values = np.asarray(power, dtype=np.float64) / float(reference)
    with np.errstate(divide="ignore"):
        db = 10.0 * np.log10(np.maximum(values, _DB_EPS))
    return np.maximum(db, floor_db)


def next_pow2(n: int) -> int:
    """Smallest power of two greater than or equal to ``n``."""
    if n <= 1:
        return 1
    return 1 << (int(n) - 1).bit_length()


def peak_level(audio: np.ndarray) -> float:
    """Sample peak of a buffer as a linear amplitude."""
    arr = np.asarray(audio)
    if arr.size == 0:
        return 0.0
    return float(np.max(np.abs(arr)))


def rms_level(audio: np.ndarray) -> float:
    """Root-mean-square level of a buffer as a linear amplitude."""
    arr = np.asarray(audio, dtype=np.float64)
    if arr.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(arr))))


def true_peak_level(audio: np.ndarray, oversample: int = 4) -> float:
    """Inter-sample (true) peak estimate, following ITU-R BS.1770 practice.

    The signal is polyphase-upsampled by ``oversample`` (4x is the BS.1770
    minimum for sample rates up to 48 kHz) before the peak is measured, which
    catches reconstruction overshoots that a plain sample peak misses.
    """
    arr = np.asarray(audio, dtype=np.float64)
    if arr.size == 0:
        return 0.0
    if oversample <= 1:
        return peak_level(arr)

    from scipy.signal import resample_poly

    axis = arr.ndim - 1
    upsampled = resample_poly(arr, oversample, 1, axis=axis)
    return float(np.max(np.abs(upsampled)))
