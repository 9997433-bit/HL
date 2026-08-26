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

from functools import lru_cache

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

#: Samples this far below the sample peak cannot host the true peak (see
#: :func:`true_peak_level`), so the audio around them is never oversampled.
TRUE_PEAK_CANDIDATE_DB = -3.0

#: Input samples kept on each side of a candidate before its window is closed.
TRUE_PEAK_MARGIN = 24

#: Candidate windows nearer than this are merged. Each window costs a fixed
#: setup, so bridging a short quiet gap is cheaper than starting a new pass.
TRUE_PEAK_MERGE_GAP = 512

#: Once candidate windows cover this fraction of a channel there is nothing
#: left to skip, and one contiguous pass beats many small ones.
TRUE_PEAK_FULL_COVERAGE = 0.5

#: Half-length of the interpolation kernel in input samples. ``6`` gives a
#: ``2*6*4 + 1`` tap prototype, i.e. ~12 taps per phase at 4x — the length
#: ITU-R BS.1770-4 Annex 2 specifies for its own true-peak interpolator.
TRUE_PEAK_KERNEL_HALF = 6

#: Interpolated samples produced per BLAS call. Sized so the strided input copy
#: stays in cache: ``chunk * (2 * KERNEL_HALF + 1)`` floats.
_TRUE_PEAK_CHUNK = 1 << 16

#: Channels shorter than this are oversampled whole; picking windows out of
#: them costs more than the interpolation it saves.
_TRUE_PEAK_MIN_SPLIT = 8192


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


def true_peak_level(audio: np.ndarray, oversample: int = 4, *, exact: bool = False) -> float:
    """Inter-sample (true) peak estimate, following ITU-R BS.1770 practice.

    The signal is polyphase-upsampled by ``oversample`` (4x is the BS.1770
    minimum for sample rates up to 48 kHz) before the peak is measured, which
    catches reconstruction overshoots that a plain sample peak misses.

    Only *candidate windows* are interpolated. Reconstruction convolves the
    signal with a windowed sinc whose L1 norm is barely above one, so audio
    whose samples all sit well below the sample peak cannot host the maximum:
    the interpolated magnitude there is bounded by ``||h||_1`` times the local
    sample magnitude. Windows are therefore grown around every sample within
    :data:`TRUE_PEAK_CANDIDATE_DB` of the sample peak and only those are
    interpolated — on sparse material that is a few thousand samples out of
    millions, which is what makes true-peak normalisation usable interactively.

    Windows read their filter context straight out of the source array, so a
    window boundary is not an edge as far as the kernel is concerned and the
    result is *identical* to interpolating the whole buffer. ``exact=True``
    does exactly that, and the tests assert the two agree.
    """
    arr = np.asarray(audio)
    if arr.size == 0:
        return 0.0
    if oversample <= 1:
        return peak_level(arr)

    # float32 carries ~7 digits, four more than any peak read-out resolves, and
    # halves the cost of the interpolation matmul below.
    arr = arr.astype(np.float32, copy=False)
    channels = arr.reshape(1, -1) if arr.ndim == 1 else arr.reshape(-1, arr.shape[-1])
    return max(_channel_true_peak(channel, int(oversample), exact) for channel in channels)


def _channel_true_peak(channel: np.ndarray, oversample: int, exact: bool) -> float:
    """True peak of one channel, interpolating only where the peak can be."""
    magnitude = np.abs(channel)
    sample_peak = float(magnitude.max()) if magnitude.size else 0.0
    if sample_peak <= 0.0:
        return 0.0  # digital silence interpolates to digital silence

    if exact or channel.size < _TRUE_PEAK_MIN_SPLIT:
        return _interpolated_peak(channel, oversample, 0, channel.size)

    starts, stops = _candidate_windows(
        magnitude >= sample_peak * float(db_to_linear(TRUE_PEAK_CANDIDATE_DB)),
        margin=TRUE_PEAK_MARGIN,
        length=channel.size,
    )
    if int(np.sum(stops - starts)) > channel.size * TRUE_PEAK_FULL_COVERAGE:
        return _interpolated_peak(channel, oversample, 0, channel.size)

    peak = sample_peak
    for start, stop in zip(starts, stops, strict=True):
        peak = max(peak, _interpolated_peak(channel, oversample, int(start), int(stop)))
    return peak


def _candidate_windows(
    hot: np.ndarray, margin: int, length: int
) -> tuple[np.ndarray, np.ndarray]:
    """Merge the runs of ``True`` in ``hot`` into padded ``[start, stop)`` windows."""
    indices = np.flatnonzero(hot)
    if indices.size == 0:  # pragma: no cover - the sample peak is always hot
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64)

    gap = max(2 * margin, TRUE_PEAK_MERGE_GAP)
    breaks = np.flatnonzero(np.diff(indices) > gap)
    starts = np.maximum(indices[np.concatenate(([0], breaks + 1))] - margin, 0)
    stops = np.minimum(indices[np.concatenate((breaks, [indices.size - 1]))] + margin + 1, length)
    return starts, stops


@lru_cache(maxsize=8)
def _interpolation_phases(oversample: int) -> np.ndarray:
    """Polyphase kernel as a ``(2*KERNEL_HALF + 1, oversample)`` matrix.

    Column ``p`` holds the taps that produce the ``p``-th interpolated sample
    after each input sample, ordered so that a sliding window of the input can
    be multiplied straight through it. Splitting the kernel this way turns
    interpolation into one BLAS matrix product, which runs several times faster
    than the equivalent ``scipy.signal.resample_poly`` call.
    """
    from scipy.signal import firwin

    half = TRUE_PEAK_KERNEL_HALF * oversample
    # Same anti-imaging filter resample_poly designs for this ratio.
    taps = firwin(2 * half + 1, 1.0 / oversample, window=("kaiser", 5.0)) * oversample
    padded = np.concatenate([taps, np.zeros(oversample - 1)])
    phases = padded.reshape(-1, oversample)[::-1]
    return np.ascontiguousarray(phases, dtype=np.float32)


def _interpolated_peak(channel: np.ndarray, oversample: int, start: int, stop: int) -> float:
    """Largest interpolated magnitude between input samples ``start`` and ``stop``."""
    phases = _interpolation_phases(oversample)
    span = phases.shape[0]  # 2 * TRUE_PEAK_KERNEL_HALF + 1
    half = TRUE_PEAK_KERNEL_HALF
    peak = 0.0

    for chunk_start in range(start, stop, _TRUE_PEAK_CHUNK):
        chunk_stop = min(chunk_start + _TRUE_PEAK_CHUNK, stop)
        context = _padded_slice(channel, chunk_start - half, chunk_stop + half)
        window = np.lib.stride_tricks.sliding_window_view(context, span)
        peak = max(peak, float(np.max(np.abs(window @ phases))))
    return peak


def _padded_slice(channel: np.ndarray, start: int, stop: int) -> np.ndarray:
    """``channel[start:stop]``, zero-filled where the range runs off either end."""
    lead, trail = max(0, -start), max(0, stop - channel.size)
    body = channel[max(start, 0) : min(stop, channel.size)]
    if not lead and not trail:
        return body
    return np.concatenate([np.zeros(lead, body.dtype), body, np.zeros(trail, body.dtype)])
