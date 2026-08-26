"""Multi-resolution min/max/RMS pyramid backing the waveform display.

Drawing a fully zoomed-out hour-long file must not touch every sample, so the
clip is summarised once into a mip-map of envelopes. Each level stores the
minimum, maximum and sum-of-squares of a fixed number of frames; a repaint then
reduces the *coarsest level that is still finer than one pixel* down to the
requested bin count, which keeps redraw cost proportional to widget width
rather than to file length.

Building the mip-map still costs one pass over the samples, so
:mod:`audio_studio.core.peaks_cache` persists the finished levels next to the
audio file and rebuilds them through :meth:`PeakPyramid.from_levels`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

#: Frames collapsed into a single bin at pyramid level 0.
BASE_DECIMATION: int = 256

#: Frames-per-bin ratio between consecutive levels.
LEVEL_RATIO: int = 4

#: Levels coarser than this many bins add no value and are not built.
MIN_LEVEL_BINS: int = 512


@dataclass(slots=True)
class Envelope:
    """Per-bin waveform summary; every array is ``(n_bins, channels)``."""

    minimum: np.ndarray
    maximum: np.ndarray
    rms: np.ndarray

    @property
    def n_bins(self) -> int:
        return int(self.minimum.shape[0])

    @property
    def n_channels(self) -> int:
        return int(self.minimum.shape[1])


@dataclass(slots=True)
class PyramidLevel:
    """One mip-map level: ``decimation`` source frames collapsed per bin.

    ``sumsq`` and ``counts`` are kept instead of a finished RMS so that a
    coarser level can be folded out of a finer one without bias.
    """

    decimation: int
    minimum: np.ndarray
    maximum: np.ndarray
    sumsq: np.ndarray
    counts: np.ndarray

    @property
    def n_bins(self) -> int:
        return int(self.minimum.shape[0])

    @property
    def n_channels(self) -> int:
        return int(self.minimum.shape[1])


class PeakPyramid:
    """Lazily-reduced envelope cache for one immutable clip."""

    __slots__ = ("_channels", "_levels", "_n_frames", "_samples")

    _samples: np.ndarray | None
    _n_frames: int
    _channels: int
    _levels: list[PyramidLevel]

    def __init__(self, samples: np.ndarray, *, base_decimation: int = BASE_DECIMATION) -> None:
        data = np.asarray(samples, dtype=np.float32)
        if data.ndim == 1:
            data = data[:, np.newaxis]
        if data.ndim != 2:
            raise ValueError(f"expected a (frames, channels) array, got {data.ndim}-D")
        if base_decimation < 2:
            raise ValueError(f"base_decimation must be >= 2, got {base_decimation}")

        self._samples = data
        self._n_frames = int(data.shape[0])
        self._channels = int(data.shape[1])
        self._levels = self._build(data, base_decimation)

    @property
    def n_frames(self) -> int:
        return self._n_frames

    @property
    def n_channels(self) -> int:
        return self._channels

    @property
    def n_levels(self) -> int:
        return len(self._levels)

    @property
    def levels(self) -> tuple[PyramidLevel, ...]:
        """The mip-map, finest first — what a disk cache serialises."""
        return tuple(self._levels)

    @property
    def base_decimation(self) -> int:
        """Frames per bin at the finest level, or 0 for an empty clip."""
        return int(self._levels[0].decimation) if self._levels else 0

    @property
    def has_samples(self) -> bool:
        """False for a pyramid restored from disk without its source frames."""
        return self._samples is not None

    @classmethod
    def from_levels(
        cls,
        levels: Sequence[PyramidLevel],
        *,
        n_frames: int,
        n_channels: int,
        samples: np.ndarray | None = None,
    ) -> PeakPyramid:
        """Rebuild a pyramid from levels reduced earlier, e.g. by a disk cache.

        ``samples`` stays optional: without the source frames the finest level
        bounds how far a zoomed-in view can resolve, which is the trade a cache
        makes for a clip that is streamed rather than held in RAM.
        """
        n_frames = int(n_frames)
        n_channels = int(n_channels)
        if n_frames < 0:
            raise ValueError(f"n_frames must not be negative, got {n_frames}")
        if n_channels < 1:
            raise ValueError(f"n_channels must be positive, got {n_channels}")

        ordered = list(levels)
        for level in ordered:
            if level.decimation < 2:
                raise ValueError(f"level decimation must be >= 2, got {level.decimation}")
            shape = level.minimum.shape
            if len(shape) != 2 or shape[1] != n_channels:
                raise ValueError(f"level shape {shape} does not match {n_channels} channels")
            if level.maximum.shape != shape or level.sumsq.shape != shape:
                raise ValueError("level min/max/sumsq arrays disagree on shape")
            if level.counts.shape != (shape[0],):
                raise ValueError("level counts array does not match its bin count")

        data: np.ndarray | None = None
        if samples is not None:
            data = np.asarray(samples, dtype=np.float32)
            if data.ndim == 1:
                data = data[:, np.newaxis]
            if data.shape != (n_frames, n_channels):
                raise ValueError(
                    f"samples {data.shape} do not match the cached geometry "
                    f"({n_frames}, {n_channels})"
                )

        pyramid = cls.__new__(cls)
        pyramid._samples = data
        pyramid._n_frames = n_frames
        pyramid._channels = n_channels
        pyramid._levels = ordered
        return pyramid

    def _build(self, data: np.ndarray, base_decimation: int) -> list[PyramidLevel]:
        levels: list[PyramidLevel] = []
        if self._n_frames == 0:
            return levels

        levels.append(self._reduce_samples(data, base_decimation))
        while levels[-1].minimum.shape[0] > MIN_LEVEL_BINS * LEVEL_RATIO:
            levels.append(self._reduce_level(levels[-1]))
        return levels

    def _reduce_samples(self, data: np.ndarray, decimation: int) -> PyramidLevel:
        n_full, tail = divmod(self._n_frames, decimation)
        n_bins = n_full + (1 if tail else 0)

        minimum = np.empty((n_bins, self._channels), dtype=np.float32)
        maximum = np.empty((n_bins, self._channels), dtype=np.float32)
        sumsq = np.empty((n_bins, self._channels), dtype=np.float64)
        counts = np.full(n_bins, decimation, dtype=np.int64)

        if n_full:
            block = data[: n_full * decimation].reshape(n_full, decimation, self._channels)
            minimum[:n_full] = block.min(axis=1)
            maximum[:n_full] = block.max(axis=1)
            sumsq[:n_full] = np.square(block, dtype=np.float64).sum(axis=1)
        if tail:
            rest = data[n_full * decimation :]
            minimum[n_full] = rest.min(axis=0)
            maximum[n_full] = rest.max(axis=0)
            sumsq[n_full] = np.square(rest, dtype=np.float64).sum(axis=0)
            counts[n_full] = tail

        return PyramidLevel(decimation, minimum, maximum, sumsq, counts)

    @staticmethod
    def _reduce_level(prev: PyramidLevel) -> PyramidLevel:
        n_prev = prev.minimum.shape[0]
        channels = prev.minimum.shape[1]
        n_full, tail = divmod(n_prev, LEVEL_RATIO)
        n_bins = n_full + (1 if tail else 0)

        minimum = np.empty((n_bins, channels), dtype=np.float32)
        maximum = np.empty((n_bins, channels), dtype=np.float32)
        sumsq = np.empty((n_bins, channels), dtype=np.float64)
        counts = np.empty(n_bins, dtype=np.int64)

        if n_full:
            end = n_full * LEVEL_RATIO
            minimum[:n_full] = prev.minimum[:end].reshape(n_full, LEVEL_RATIO, channels).min(axis=1)
            maximum[:n_full] = prev.maximum[:end].reshape(n_full, LEVEL_RATIO, channels).max(axis=1)
            sumsq[:n_full] = prev.sumsq[:end].reshape(n_full, LEVEL_RATIO, channels).sum(axis=1)
            counts[:n_full] = prev.counts[:end].reshape(n_full, LEVEL_RATIO).sum(axis=1)
        if tail:
            minimum[n_full] = prev.minimum[n_full * LEVEL_RATIO :].min(axis=0)
            maximum[n_full] = prev.maximum[n_full * LEVEL_RATIO :].max(axis=0)
            sumsq[n_full] = prev.sumsq[n_full * LEVEL_RATIO :].sum(axis=0)
            counts[n_full] = prev.counts[n_full * LEVEL_RATIO :].sum()

        return PyramidLevel(prev.decimation * LEVEL_RATIO, minimum, maximum, sumsq, counts)

    def envelope(self, start_frame: int, end_frame: int, n_bins: int) -> Envelope:
        """Summarise ``[start_frame, end_frame)`` into exactly ``n_bins`` bins."""
        if n_bins <= 0:
            raise ValueError(f"n_bins must be positive, got {n_bins}")

        start = max(0, min(int(start_frame), self._n_frames))
        end = max(start, min(int(end_frame), self._n_frames))
        span = end - start

        if span == 0 or self._n_frames == 0:
            zeros = np.zeros((n_bins, max(self._channels, 1)), dtype=np.float32)
            return Envelope(zeros, zeros.copy(), zeros.copy())

        frames_per_bin = span / n_bins
        level = self._select_level(frames_per_bin)
        if level is None:
            samples = self._samples
            if samples is not None:
                return self._envelope_from_samples(samples, start, end, n_bins)
            # Restored from a cache that carries no source frames: the finest
            # level is as sharp as this pyramid can be.
            if not self._levels:
                zeros = np.zeros((n_bins, max(self._channels, 1)), dtype=np.float32)
                return Envelope(zeros, zeros.copy(), zeros.copy())
            level = self._levels[0]
        return self._envelope_from_level(level, start, end, n_bins)

    def _select_level(self, frames_per_bin: float) -> PyramidLevel | None:
        """Coarsest level whose bins still fit inside one output bin."""
        chosen: PyramidLevel | None = None
        for level in self._levels:
            if level.decimation <= frames_per_bin / 2.0:
                chosen = level
            else:
                break
        return chosen

    def _envelope_from_samples(
        self, samples: np.ndarray, start: int, end: int, n_bins: int
    ) -> Envelope:
        starts = self._bin_starts(start, end, n_bins, limit=self._n_frames)
        return self._reduce_ranges(samples, samples, None, None, starts, end)

    def _envelope_from_level(
        self, level: PyramidLevel, start: int, end: int, n_bins: int
    ) -> Envelope:
        n_level_bins = level.minimum.shape[0]
        starts = self._bin_starts(
            start / level.decimation, end / level.decimation, n_bins, limit=n_level_bins
        )
        stop = min(int(np.ceil(end / level.decimation)), n_level_bins)
        return self._reduce_ranges(
            level.minimum, level.maximum, level.sumsq, level.counts, starts, stop
        )

    @staticmethod
    def _bin_starts(lo: float, hi: float, n_bins: int, *, limit: int) -> np.ndarray:
        """Left edge of every output bin, expressed in source-array indices."""
        edges = np.linspace(lo, hi, n_bins + 1)[:-1]
        return np.clip(np.floor(edges).astype(np.int64), 0, max(limit - 1, 0))

    @staticmethod
    def _reduce_ranges(
        minimum_src: np.ndarray,
        maximum_src: np.ndarray,
        sumsq_src: np.ndarray | None,
        counts_src: np.ndarray | None,
        starts: np.ndarray,
        stop: int,
    ) -> Envelope:
        # ``reduceat`` extends its final segment to the end of the array, so the
        # sources are sliced to the visible span first and the bin offsets are
        # rebased onto that slice.
        first = int(starts[0])
        stop = max(int(stop), first + 1)
        offsets = starts - first

        min_view = minimum_src[first:stop]
        max_view = maximum_src[first:stop]
        sumsq_view = (
            np.square(min_view, dtype=np.float64) if sumsq_src is None else sumsq_src[first:stop]
        )
        counts_view = (
            np.ones(min_view.shape[0], dtype=np.int64)
            if counts_src is None
            else counts_src[first:stop]
        )

        # A bin whose start equals the next bin's start reduces to a single
        # element, which is the wanted behaviour when zoomed past 1:1.
        mins = np.minimum.reduceat(min_view, offsets, axis=0)
        maxs = np.maximum.reduceat(max_view, offsets, axis=0)
        sums = np.add.reduceat(sumsq_view, offsets, axis=0)
        counts = np.add.reduceat(counts_view, offsets, axis=0).astype(np.float64)
        np.maximum(counts, 1.0, out=counts)

        rms = np.sqrt(np.maximum(sums, 0.0) / counts[:, np.newaxis]).astype(np.float32)
        return Envelope(
            np.ascontiguousarray(mins, dtype=np.float32),
            np.ascontiguousarray(maxs, dtype=np.float32),
            rms,
        )
