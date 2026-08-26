"""Impulsive-noise repair: vinyl ticks, digital dropouts, edit clicks.

A click is a handful of samples that do not belong to the signal around them.
That is the whole definition, and it is also the algorithm:

1. **Predict.** Fit a short-term linear predictor (an autoregressive model) to
   each analysis frame. Music and speech are highly predictable over the ~1 ms
   an AR model looks back; the model captures the pitch, the formants and the
   noise colour of that moment.
2. **Detect.** Whatever the predictor fails to explain is the residual. Its
   scale is estimated with the median absolute deviation rather than the
   standard deviation, because the outliers being hunted would otherwise
   inflate the very threshold meant to catch them. Samples whose residual
   exceeds a multiple of that scale are flagged.
3. **Interpolate.** The flagged samples are *removed*, not attenuated, and
   replaced by the values that minimise the prediction error given the
   surrounding audio. For a burst of ``m`` samples that is an ``m x m``
   least-squares solve, which reconstructs a sine or a formant exactly rather
   than drawing a straight line across the hole.

The length of a detected burst adapts to the material, which is what keeps the
repair from doing damage. In a tonal passage the predictor is accurate, the
detection threshold is low, and a click rings through the residual for the
length of the model — but interpolating a tonal passage is also nearly exact,
so a generous repair costs nothing. In a noisy passage the residual is large,
only the click itself clears the threshold, and the repair stays surgical.

Runs longer than :attr:`DeClickEffect.max_click_ms` are left alone on purpose:
a 20 ms transient that the predictor cannot follow is a snare drum, not a tick.

Examples
--------
>>> import numpy as np
>>> sr = 48_000
>>> clean = 0.5 * np.sin(2 * np.pi * 440.0 * np.arange(sr) / sr)
>>> damaged = clean.copy()
>>> damaged[12_345] += 0.8                      # one tick
>>> repaired, report = repair_clicks(damaged, sr)
>>> report.count
1
>>> bool(np.max(np.abs(repaired - clean)) < 0.01)
True
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.linalg import solve_toeplitz
from scipy.signal import lfilter

from ..effects.base import Effect
from ..util import as_planar, next_pow2, restore_layout

__all__ = [
    "ClickEvent",
    "DeClickEffect",
    "DeClickReport",
    "detect_clicks",
    "repair_clicks",
    "threshold_sigma_for",
]

#: Residual thresholds, in robust sigmas, that ``sensitivity`` 0 and 1 select.
#: The low end only catches gross damage; the high end will start repairing
#: sharp musical transients, which is why the default sits between them.
THRESHOLD_SIGMA_RANGE = (20.0, 3.0)

#: Default predictor order at 48 kHz. About 0.7 ms of history: long enough to
#: model pitch and formant structure, short enough that the solve stays small.
DEFAULT_ORDER = 32

#: Detected runs closer together than this are merged into one repair.
_MERGE_GAP = 2

#: Length of the window the residual's scale is estimated over, in seconds.
#: One estimate per analysis frame would be wrong the moment a frame contains
#: both a silence and a drum hit: the silence drags the median down and every
#: sample of the hit looks like damage.
_SCALE_WINDOW_S = 0.02

#: Residual floor relative to the frame's RMS. Without it, a perfectly
#: predictable signal (a synthesised tone, digital silence) has a residual scale
#: near the floating-point floor and every rounding error looks like a click.
_NOISE_FLOOR_REL = 1e-3

#: MAD -> standard deviation conversion for normally distributed data.
_MAD_TO_SIGMA = 1.4826


def threshold_sigma_for(sensitivity: float) -> float:
    """Map a ``0..1`` sensitivity control onto a residual threshold in sigmas.

    Examples
    --------
    >>> threshold_sigma_for(0.0), threshold_sigma_for(1.0)
    (20.0, 3.0)
    """
    amount = min(max(float(sensitivity), 0.0), 1.0)
    low, high = THRESHOLD_SIGMA_RANGE
    return low + (high - low) * amount


@dataclass(frozen=True)
class ClickEvent:
    """One repaired burst, in samples."""

    channel: int
    start: int
    stop: int
    peak_residual: float

    @property
    def length(self) -> int:
        return self.stop - self.start

    def seconds(self, sample_rate: float) -> float:
        """Position of the burst in the clip, in seconds."""
        return self.start / float(sample_rate)


@dataclass(frozen=True)
class DeClickReport:
    """What a de-click pass found and how much of the signal it rewrote."""

    events: tuple[ClickEvent, ...]
    duration_s: float
    threshold_sigma: float

    @property
    def count(self) -> int:
        return len(self.events)

    @property
    def repaired_samples(self) -> int:
        return sum(event.length for event in self.events)

    @property
    def per_minute(self) -> float:
        """Click density, the number an archivist actually compares between takes."""
        if self.duration_s <= 0.0:
            return 0.0
        return self.count * 60.0 / self.duration_s

    def in_channel(self, channel: int) -> tuple[ClickEvent, ...]:
        return tuple(event for event in self.events if event.channel == channel)

    def as_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "repaired_samples": self.repaired_samples,
            "per_minute": self.per_minute,
            "threshold_sigma": self.threshold_sigma,
            "duration_s": self.duration_s,
        }

    def __str__(self) -> str:
        if not self.events:
            return "no clicks found"
        return (
            f"{self.count} clicks ({self.per_minute:.1f}/min), "
            f"{self.repaired_samples} samples repaired"
        )


def _autoregressive_model(frame: np.ndarray, order: int) -> np.ndarray | None:
    """Levinson-Durbin AR coefficients ``a`` with ``x[n] ~ sum a_k x[n-k]``.

    Returns ``None`` for a frame with no energy to model.
    """
    n = frame.size
    if n <= order + 1:
        return None
    # Autocorrelation through the FFT: O(n log n) instead of O(n * order), which
    # matters because this runs once per analysis frame of every channel.
    size = next_pow2(2 * n)
    spectrum = np.fft.rfft(frame, size)
    r = np.fft.irfft(np.abs(spectrum) ** 2, size)[: order + 1]
    if r[0] <= 0.0 or not np.all(np.isfinite(r)):
        return None
    # A whisker of ridge keeps the Toeplitz system positive definite when the
    # frame is a pure tone, whose autocorrelation matrix is singular in theory
    # and very nearly so in floating point.
    r = r.copy()
    r[0] *= 1.0 + 1e-9
    r[0] += 1e-30
    try:
        coefficients = solve_toeplitz((r[:-1], r[:-1]), r[1:])
    except Exception:  # pragma: no cover - singular even after the ridge
        return None
    if not np.all(np.isfinite(coefficients)):
        return None
    return np.asarray(coefficients, dtype=np.float64)


def _prediction_residual(signal: np.ndarray, coefficients: np.ndarray) -> np.ndarray:
    """``x[n] - sum a_k x[n-k]``, same length as ``signal``."""
    taps = np.concatenate([[1.0], -coefficients])
    return lfilter(taps, [1.0], signal)


def _local_threshold(
    residual: np.ndarray,
    signal: np.ndarray,
    threshold_sigma: float,
    window: int,
) -> np.ndarray:
    """Per-sample detection threshold, tracking the residual's local scale.

    The scale is a median absolute deviation over short windows, so a burst of
    outliers cannot inflate the threshold that is meant to catch it, and then
    each window's threshold is raised to its loudest neighbour. That last step
    is what keeps a drum hit intact: the window holding the attack is half
    silence and would otherwise be judged against the silence.
    """
    window = max(64, int(window))
    count = max(1, -(-residual.size // window))
    # The last window is short; padding it with NaN rather than zeros keeps the
    # median and the mean over the samples that exist.
    magnitude = np.full(count * window, np.nan, dtype=np.float64)
    magnitude[: residual.size] = np.abs(residual)
    energy = np.full(count * window, np.nan, dtype=np.float64)
    energy[: signal.size] = np.square(signal)

    scale = _MAD_TO_SIGMA * np.nanmedian(magnitude.reshape(count, window), axis=1)
    floor = _NOISE_FLOOR_REL * np.sqrt(np.nanmean(energy.reshape(count, window), axis=1))
    per_window = np.maximum(threshold_sigma * scale, floor)

    edged = np.concatenate([per_window[:1], per_window, per_window[-1:]])
    per_window = np.maximum(np.maximum(edged[:-2], edged[1:-1]), edged[2:])
    thresholds = np.repeat(per_window, window)[: residual.size]
    # A window with no energy at all has no threshold to speak of; nothing in
    # digital silence is a click.
    return np.where(thresholds > 0.0, thresholds, np.inf)


def _runs(flagged: np.ndarray, merge_gap: int = _MERGE_GAP) -> list[tuple[int, int]]:
    """Contiguous ``True`` ranges, merging any separated by ``merge_gap``."""
    indices = np.flatnonzero(flagged)
    if indices.size == 0:
        return []
    breaks = np.flatnonzero(np.diff(indices) > merge_gap)
    starts = indices[np.concatenate(([0], breaks + 1))]
    stops = indices[np.concatenate((breaks, [indices.size - 1]))] + 1
    return list(zip(starts.tolist(), stops.tolist(), strict=True))


def _interpolate_burst(
    channel: np.ndarray,
    start: int,
    stop: int,
    coefficients: np.ndarray,
) -> np.ndarray | None:
    """Least-squares AR interpolation of ``channel[start:stop]``.

    The samples either side are treated as known and the missing ones are
    chosen to minimise the total squared prediction error across the join,
    which is the interpolation the AR model itself implies.
    """
    order = coefficients.size
    left = max(0, start - order)
    right = min(channel.size, stop + order)
    segment = channel[left:right].astype(np.float64, copy=True)
    length = segment.size
    n_rows = length - order
    missing = np.arange(start - left, stop - left)
    if n_rows <= 0 or missing.size == 0 or missing.size >= length:
        return None

    # Row i of A is the prediction error at segment sample i + order.
    taps = np.concatenate([-coefficients[::-1], [1.0]])
    rows = np.lib.stride_tricks.sliding_window_view(np.arange(length), order + 1)
    matrix = np.zeros((n_rows, length), dtype=np.float64)
    np.put_along_axis(matrix, rows, np.broadcast_to(taps, (n_rows, order + 1)), axis=1)

    known = np.setdiff1d(np.arange(length), missing, assume_unique=False)
    a_missing = matrix[:, missing]
    normal = a_missing.T @ a_missing
    rhs = -a_missing.T @ (matrix[:, known] @ segment[known])
    normal[np.diag_indices_from(normal)] += 1e-12 * max(float(np.trace(normal)), 1e-12)
    try:
        values = np.linalg.solve(normal, rhs)
    except np.linalg.LinAlgError:  # pragma: no cover - regularisation makes this rare
        return None
    if not np.all(np.isfinite(values)):
        return None
    return values


def _scan_channel(
    channel: np.ndarray,
    index: int,
    sample_rate: float,
    threshold_sigma: float,
    order: int,
    frame_s: float,
    max_click: int,
    repair: bool,
    output: np.ndarray | None,
) -> list[ClickEvent]:
    """Detect (and optionally repair) one channel, frame by frame."""
    events: list[ClickEvent] = []
    frame_length = max(order * 8, int(round(frame_s * sample_rate)))
    for frame_start in range(0, channel.size, frame_length):
        frame_stop = min(frame_start + frame_length, channel.size)
        frame = channel[frame_start:frame_stop]
        if frame.size <= order * 2:
            continue

        coefficients = _autoregressive_model(frame, order)
        if coefficients is None:
            continue

        residual = _prediction_residual(frame, coefficients)[order:]
        if residual.size == 0:
            continue
        threshold = _local_threshold(
            residual, frame[order:], threshold_sigma, int(round(_SCALE_WINDOW_S * sample_rate))
        )

        flagged = np.abs(residual) > threshold
        if not np.any(flagged):
            continue

        offset = frame_start + order
        for run_start, run_stop in _runs(flagged):
            length = run_stop - run_start
            if length > max_click:
                continue  # a transient the predictor cannot follow, not a click
            start, stop = offset + run_start, offset + run_stop
            peak = float(np.max(np.abs(residual[run_start:run_stop])))
            if repair and output is not None:
                values = _interpolate_burst(channel, start, stop, coefficients)
                if values is None:
                    continue
                output[start:stop] = values
            events.append(ClickEvent(index, start, stop, peak))
    return events


def _scan(
    audio: np.ndarray,
    sample_rate: float,
    sensitivity: float,
    order: int,
    frame_s: float,
    max_click_ms: float,
    channels_last: bool | None,
    repair: bool,
) -> tuple[np.ndarray, np.ndarray, DeClickReport]:
    """Shared body of :func:`detect_clicks` and :func:`repair_clicks`."""
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    planar, was_mono = as_planar(audio, channels_last=channels_last, dtype=np.float64)
    threshold_sigma = threshold_sigma_for(sensitivity)
    max_click = max(1, int(round(max_click_ms * sample_rate / 1000.0)))
    order = max(2, int(order))

    repaired = planar.copy()
    events: list[ClickEvent] = []
    for index, channel in enumerate(planar):
        events.extend(
            _scan_channel(
                channel,
                index,
                sample_rate,
                threshold_sigma,
                order,
                frame_s,
                max_click,
                repair,
                repaired[index] if repair else None,
            )
        )

    report = DeClickReport(
        events=tuple(events),
        duration_s=planar.shape[1] / float(sample_rate),
        threshold_sigma=threshold_sigma,
    )
    return repaired, planar, report


def detect_clicks(
    audio: np.ndarray,
    sample_rate: float,
    sensitivity: float = 0.6,
    order: int = DEFAULT_ORDER,
    frame_s: float = 1.0,
    max_click_ms: float = 2.0,
    channels_last: bool | None = None,
) -> DeClickReport:
    """Find impulsive damage without changing the audio.

    Examples
    --------
    >>> import numpy as np
    >>> sr = 48_000
    >>> audio = 0.4 * np.sin(2 * np.pi * 300.0 * np.arange(sr) / sr)
    >>> detect_clicks(audio, sr).count
    0
    """
    _, _, report = _scan(
        audio, sample_rate, sensitivity, order, frame_s, max_click_ms, channels_last, False
    )
    return report


def repair_clicks(
    audio: np.ndarray,
    sample_rate: float,
    sensitivity: float = 0.6,
    order: int = DEFAULT_ORDER,
    frame_s: float = 1.0,
    max_click_ms: float = 2.0,
    channels_last: bool | None = None,
) -> tuple[np.ndarray, DeClickReport]:
    """Repair impulsive damage, returning ``(audio, report)``.

    The input is never modified, and the result keeps the caller's layout.
    """
    repaired, _, report = _scan(
        audio, sample_rate, sensitivity, order, frame_s, max_click_ms, channels_last, True
    )
    arr = np.asarray(audio)
    was_mono = arr.ndim == 1
    dtype = arr.dtype if arr.dtype in (np.float32, np.float64) else np.float32
    result = restore_layout(repaired.astype(dtype, copy=False), was_mono)
    if channels_last and not was_mono:
        result = np.ascontiguousarray(result.T)
    return result, report


class DeClickEffect(Effect):
    """De-clicker as a rack effect.

    Needs the samples on both sides of a click to interpolate across it and a
    frame of context to model the signal, so it renders offline rather than
    streaming: in a live rack it is skipped until the user commits the render.

    Parameters
    ----------
    sensitivity:
        ``0..1``. Higher flags more; see :func:`threshold_sigma_for` for the
        residual thresholds the ends of the range select.
    order:
        Predictor order. Longer models follow pitched material better and cost
        more per repair.
    max_click_ms:
        Longest burst treated as damage. Anything longer is programme material.

    Examples
    --------
    >>> import numpy as np
    >>> sr = 48_000
    >>> audio = 0.5 * np.sin(2 * np.pi * 440.0 * np.arange(sr) / sr)
    >>> audio[20_000] = 0.99
    >>> effect = DeClickEffect()
    >>> cleaned = effect.process(audio, sr)
    >>> effect.last_report.count
    1
    """

    name = "De-Click"
    is_offline_only = True

    def __init__(
        self,
        sensitivity: float = 0.6,
        order: int = DEFAULT_ORDER,
        max_click_ms: float = 2.0,
        frame_s: float = 1.0,
        enabled: bool = True,
    ) -> None:
        super().__init__(enabled=enabled)
        self.sensitivity = float(sensitivity)
        self.order = int(order)
        self.max_click_ms = float(max_click_ms)
        self.frame_s = float(frame_s)
        self._last_report: DeClickReport | None = None

    @property
    def last_report(self) -> DeClickReport | None:
        """What the most recent :meth:`process` call found."""
        return self._last_report

    def parameters(self) -> dict[str, Any]:
        return {
            **super().parameters(),
            "sensitivity": self.sensitivity,
            "order": self.order,
            "max_click_ms": self.max_click_ms,
            "frame_s": self.frame_s,
        }

    def _process_planar(self, audio: np.ndarray, sample_rate: float) -> np.ndarray:
        repaired, report = repair_clicks(
            audio,
            sample_rate,
            sensitivity=self.sensitivity,
            order=self.order,
            frame_s=self.frame_s,
            max_click_ms=self.max_click_ms,
            channels_last=False,
        )
        self._last_report = report
        return np.asarray(repaired, dtype=audio.dtype)
