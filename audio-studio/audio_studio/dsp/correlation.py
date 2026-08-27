"""Stereo phase correlation metering.

The correlation meter answers one production question: does this stereo
program survive a mono fold-down? The reading is the zero-lag normalised
cross-correlation of the left and right channels,

.. math:: r = \\frac{\\sum l \\cdot r}{\\sqrt{\\sum l^2 \\cdot \\sum r^2}}

which is what the needle on a hardware correlation meter shows: ``+1`` for
identical (or merely panned) material, ``0`` for unrelated channels, and
``-1`` for polarity-inverted material that cancels in mono. The normalisation
makes the reading level-independent — a quiet out-of-phase pad reads ``-1``
just as loudly as a hot one, because it cancels in mono just the same.

:func:`phase_correlation` measures a whole buffer in one call, which is what
an analysis report over a selection wants. :class:`CorrelationMeter` is the
streaming form: feed it arbitrary-sized blocks and read a needle smoothed over
:attr:`~CorrelationMeter.window_ms`, the ballistic that keeps a live meter
readable instead of flickering at every zero crossing.
"""

from __future__ import annotations

import math

import numpy as np

from .util import as_planar

__all__ = ["CorrelationMeter", "phase_correlation"]

#: Integration window of the streaming meter's exponential smoothing, chosen
#: to match the ~300 ms ballistics of hardware correlation meters.
DEFAULT_WINDOW_MS = 300.0

#: Mean-square level below which a channel pair is treated as silent. Digital
#: silence has no phase, so the meter holds its reading instead of computing
#: 0/0. Well below the 24-bit noise floor squared.
_SILENCE_POWER = 1e-20


def _pair(audio: np.ndarray, channels_last: bool | None) -> tuple[np.ndarray, np.ndarray]:
    """Left/right float64 views of ``audio``; mono is its own pair."""
    array = np.asarray(audio)
    if array.size == 0:
        empty = np.zeros(0, dtype=np.float64)
        return empty, empty
    planar, _was_mono = as_planar(array, channels_last, dtype=np.float64)
    left = planar[0]
    right = planar[1] if planar.shape[0] > 1 else planar[0]
    return left, right


def phase_correlation(audio: np.ndarray, channels_last: bool | None = None) -> float:
    """Zero-lag correlation of the first two channels, in ``[-1.0, +1.0]``.

    Mono input reads ``+1.0`` — a single channel is trivially mono-compatible.
    Digital silence also reads ``+1.0`` for the same reason: nothing cancels.
    Buffers with more than two channels are measured on their first pair,
    which is the L/R bus every hardware correlation meter watches.
    """
    left, right = _pair(audio, channels_last)
    if left.size == 0:
        return 1.0
    left_power = float(np.dot(left, left))
    right_power = float(np.dot(right, right))
    if left_power <= _SILENCE_POWER or right_power <= _SILENCE_POWER:
        return 1.0
    ratio = float(np.dot(left, right)) / math.sqrt(left_power * right_power)
    return max(-1.0, min(ratio, 1.0))


class CorrelationMeter:
    """Streaming phase correlation with hardware-meter ballistics.

    Feed :meth:`process_block` the blocks a live path already produces; the
    :attr:`correlation` needle is the zero-lag correlation of the audio inside
    an exponentially weighted window of ``window_ms``. Smoothing is applied to
    the three underlying accumulators (``l*r``, ``l**2``, ``r**2``) rather
    than to the ratio, so loud audio moves the needle proportionally faster
    than quiet audio — the same weighting the one-shot measurement applies
    within a single buffer.

    On silence the accumulators decay together and the needle holds its last
    reading instead of jumping; a fresh meter reads ``+1.0`` until it has
    heard anything, because there is nothing to warn about yet.
    """

    def __init__(self, sample_rate: int, *, window_ms: float = DEFAULT_WINDOW_MS) -> None:
        if sample_rate <= 0:
            raise ValueError(f"sample_rate must be positive, got {sample_rate}")
        if window_ms <= 0.0:
            raise ValueError(f"window_ms must be positive, got {window_ms}")
        self._sample_rate = int(sample_rate)
        self._window_frames = self._sample_rate * float(window_ms) / 1000.0
        self._cross = 0.0
        self._left_power = 0.0
        self._right_power = 0.0
        self._correlation = 1.0
        self._frames_processed = 0

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def window_ms(self) -> float:
        """Integration window of the smoothing, in milliseconds."""
        return self._window_frames / self._sample_rate * 1000.0

    @property
    def frames_processed(self) -> int:
        """Frames consumed since construction or the last :meth:`reset`."""
        return self._frames_processed

    @property
    def correlation(self) -> float:
        """The needle: smoothed correlation in ``[-1.0, +1.0]``."""
        return self._correlation

    def reset(self) -> None:
        """Forget all audio; the needle returns to its idle ``+1.0``."""
        self._cross = 0.0
        self._left_power = 0.0
        self._right_power = 0.0
        self._correlation = 1.0
        self._frames_processed = 0

    def process_block(
        self, block: np.ndarray, channels_last: bool | None = None
    ) -> float:
        """Consume one block and return the updated :attr:`correlation`."""
        left, right = _pair(block, channels_last)
        frames = left.size
        if frames == 0:
            return self._correlation

        # One smoothing step per block, weighted by the block's own length,
        # keeps the ballistic independent of how the caller slices its audio.
        keep = math.exp(-frames / self._window_frames)
        blend = 1.0 - keep
        self._cross = keep * self._cross + blend * float(np.dot(left, right)) / frames
        self._left_power = (
            keep * self._left_power + blend * float(np.dot(left, left)) / frames
        )
        self._right_power = (
            keep * self._right_power + blend * float(np.dot(right, right)) / frames
        )
        self._frames_processed += frames

        if self._left_power > _SILENCE_POWER and self._right_power > _SILENCE_POWER:
            ratio = self._cross / math.sqrt(self._left_power * self._right_power)
            self._correlation = max(-1.0, min(ratio, 1.0))
        return self._correlation
