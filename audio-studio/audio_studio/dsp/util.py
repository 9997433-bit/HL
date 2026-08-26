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
    "true_peak_candidate_db",
]

#: Channel counts above this are assumed to be a transposed (interleaved) buffer.
MAX_SANE_CHANNELS = 64

#: Anything quieter than this is clamped before taking a logarithm.
_DB_EPS = 1e-20

#: Granularity of the candidate scan, in samples. Screening by block keeps the
#: scan to one strided reduction rather than an index per sample; 512 is where
#: that reduction stops being the dominant cost (~1 ms per channel-minute).
TRUE_PEAK_BLOCK = 512

#: Input samples kept on each side of a candidate before its window is closed.
#: Must be at least :data:`TRUE_PEAK_KERNEL_HALF` for the shortcut to be exact.
TRUE_PEAK_MARGIN = 64

#: Candidate blocks nearer than this are merged. Each window costs a fixed
#: setup, so bridging a short quiet gap is cheaper than starting a new pass.
TRUE_PEAK_MERGE_GAP = 2

#: What one window costs to set up, expressed in samples of interpolation. Used
#: to decide when so many windows have accumulated that a single pass over the
#: whole channel would be cheaper.
TRUE_PEAK_WINDOW_COST = 2048

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

    Only *candidate windows* are interpolated. An interpolated sample is a
    weighted sum of the ``2 * TRUE_PEAK_KERNEL_HALF + 1`` input samples around
    it, so its magnitude cannot exceed ``||h||_1`` times the largest of them.
    Audio whose local maximum is below ``sample_peak / ||h||_1`` therefore
    cannot host the true peak and is skipped;
    :func:`true_peak_candidate_db` is where that level comes from. On sparse
    material that leaves a few thousand samples out of millions to interpolate,
    which is what makes true-peak normalisation usable interactively.

    Windows read their filter context straight out of the source array, so a
    window boundary is not an edge as far as the kernel is concerned, and the
    bound above is a strict one — the shortcut returns the *same* number as
    interpolating everything. ``exact=True`` does interpolate everything, and
    the tests assert the two agree.
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


def true_peak_candidate_db(oversample: int = 4) -> float:
    """Level, relative to the sample peak, below which no true peak can hide.

    The interpolation kernel's largest L1 norm across phases bounds how far an
    inter-sample value can rise above the samples around it, so this is the
    threshold that makes the candidate-window shortcut in
    :func:`true_peak_level` exact rather than merely likely.

    Examples
    --------
    >>> round(true_peak_candidate_db(4), 2)
    -5.64
    """
    phases = _interpolation_phases(int(oversample))
    return float(-linear_to_db(np.abs(phases).sum(axis=0).max()))


def _channel_true_peak(channel: np.ndarray, oversample: int, exact: bool) -> float:
    """True peak of one channel, interpolating only where the peak can be."""
    if channel.size == 0:
        return 0.0
    if exact or channel.size < _TRUE_PEAK_MIN_SPLIT:
        # Phase 0 of the kernel is the identity, so this covers the sample peak.
        return _interpolated_peak(channel, oversample, 0, channel.size)

    blocks = _block_peaks(channel, TRUE_PEAK_BLOCK)
    sample_peak = float(blocks.max())
    if sample_peak <= 0.0:
        return 0.0  # digital silence interpolates to digital silence

    threshold = sample_peak * float(db_to_linear(true_peak_candidate_db(oversample)))
    starts, stops = _candidate_windows(blocks >= threshold, channel.size)
    covered = int(np.sum(stops - starts))
    if covered + starts.size * TRUE_PEAK_WINDOW_COST > channel.size:
        # Too little left to skip to pay for the windows: one pass is cheaper.
        return _interpolated_peak(channel, oversample, 0, channel.size)

    peak = sample_peak
    for start, stop in zip(starts, stops, strict=True):
        peak = max(peak, _interpolated_peak(channel, oversample, int(start), int(stop)))
    return peak


def _block_peaks(channel: np.ndarray, block: int) -> np.ndarray:
    """Largest magnitude in each ``block`` samples, in one pass over the data.

    ``reduceat`` is used rather than a reshape so a channel whose length is not
    a multiple of ``block`` needs no separate tail, and because reducing a
    strided view this way is several times faster than ``max(axis=1)``.
    """
    edges = np.arange(0, channel.size, block)
    return np.maximum(
        np.maximum.reduceat(channel, edges), -np.minimum.reduceat(channel, edges)
    )


def _candidate_windows(hot: np.ndarray, length: int) -> tuple[np.ndarray, np.ndarray]:
    """Merge the hot blocks into padded ``[start, stop)`` ranges of samples."""
    indices = np.flatnonzero(hot)
    if indices.size == 0:  # pragma: no cover - the block holding the peak is always hot
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64)

    breaks = np.flatnonzero(np.diff(indices) > TRUE_PEAK_MERGE_GAP)
    first = indices[np.concatenate(([0], breaks + 1))]
    last = indices[np.concatenate((breaks, [indices.size - 1]))]
    starts = np.maximum(first * TRUE_PEAK_BLOCK - TRUE_PEAK_MARGIN, 0)
    stops = np.minimum((last + 1) * TRUE_PEAK_BLOCK + TRUE_PEAK_MARGIN, length)
    return starts, stops


@lru_cache(maxsize=8)
def _interpolation_phases(oversample: int) -> np.ndarray:
    """Polyphase kernel as a ``(2*KERNEL_HALF + 1, oversample)`` matrix.

    Column ``p`` holds the taps that produce the ``p``-th interpolated sample
    after each input sample, ordered so that a sliding window of the input can
    be multiplied straight through it. Splitting the kernel this way turns
    interpolation into one BLAS matrix product, which runs several times faster
    than the equivalent ``scipy.signal.resample_poly`` call.

    The prototype is normalised so that phase 0 is exactly the input sample —
    a reconstruction filter has to agree with the samples it interpolates
    between, and it lets the sample peak stand in for that phase.
    """
    from scipy.signal import firwin

    half = TRUE_PEAK_KERNEL_HALF * oversample
    # Same anti-imaging filter resample_poly designs for this ratio.
    taps = firwin(2 * half + 1, 1.0 / oversample, window=("kaiser", 5.0)) * oversample
    taps /= taps[half]
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
