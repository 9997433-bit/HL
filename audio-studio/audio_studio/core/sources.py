"""Spec-facing source vocabulary: aliases plus the composite sources.

The Round 2 convergence audit (``.agent_workspace/round2/fable-convergence-audit.md``
§4.1) freezes this module path and the names ``ArraySource`` and
``FileStreamSource``. The implementation landed under the longer, more explicit
``sample_source`` spelling, so both vocabularies are kept alive here rather than
forcing every downstream caller to pick one: the objects are identical, not
wrappers, so ``isinstance`` and identity checks hold across either import.

The composites the audit also freezes live here for real. :class:`RegionSource`
and :class:`LoopSource` express "play this part" and "play it round and round"
as *sources* rather than as transport state, which is what lets them compose:
``LoopSource(RegionSource(clip, chorus))`` loops the chorus and needs no
cooperation from :class:`~audio_studio.core.engine.AudioEngine` at all. The
transport keeps its own selection and loop flags — they are the interactive
front end — but a session, a batch render or a test can now build the same
behaviour without one.
"""

from __future__ import annotations

import numpy as np

from .edit_session import EditSession
from .sample_source import (
    BaseSampleSource,
    MemorySampleSource,
    SampleSource,
    StreamingSampleSource,
    open_source,
)
from .types import SAMPLE_DTYPE, TimeRange

#: An in-memory clip. ``exact`` is ``True``: reads never touch the disk.
ArraySource = MemorySampleSource

#: A file read a block at a time through libsndfile. ``exact`` is ``False``.
FileStreamSource = StreamingSampleSource

#: An edit document, which satisfies the protocol directly.
ChunkTableSource = EditSession

#: Length reported by an endlessly looping source. Large enough that the
#: transport treats it as unbounded (nineteen thousand years at 48 kHz) and
#: small enough to stay well clear of int64 overflow when a caller adds a
#: block size to it.
ENDLESS_FRAMES: int = 1 << 55


class RegionSource(BaseSampleSource):
    """A window onto another source, re-based so the region starts at frame 0.

    Playing a selection is then just playing a shorter source: the caller does
    no offset arithmetic, and neither does anything downstream of it.
    """

    __slots__ = ("_inner", "_owns_inner", "_region")

    def __init__(
        self,
        inner: SampleSource,
        region: TimeRange | None = None,
        *,
        owns_inner: bool = False,
    ) -> None:
        span = TimeRange(0, int(inner.n_frames)) if region is None else region
        self._inner = inner
        self._region = span.clamped(int(inner.n_frames))
        self._owns_inner = bool(owns_inner)

    @property
    def inner(self) -> SampleSource:
        return self._inner

    @property
    def region(self) -> TimeRange:
        """The window into ``inner``, already clamped to its length."""
        return self._region

    @property
    def sample_rate(self) -> int:
        return int(self._inner.sample_rate)

    @property
    def n_frames(self) -> int:
        return self._region.length

    @property
    def n_channels(self) -> int:
        return int(self._inner.n_channels)

    @property
    def exact(self) -> bool:
        return bool(getattr(self._inner, "exact", True))

    def read(self, start: int, n_frames: int) -> np.ndarray:
        start, count = self._clamp(start, n_frames)
        if count == 0:
            return self._empty()
        return self._inner.read(self._region.start + start, count)

    def read_into(self, out: np.ndarray, start: int) -> int:
        """Pass the caller's buffer straight through to the inner source."""
        self._check_out(out)
        start, count = self._clamp(start, int(out.shape[0]))
        if count == 0:
            out[:] = 0.0
            return 0
        written = self._inner.read_into(out[:count], self._region.start + start)
        if written < out.shape[0]:
            out[written:] = 0.0
        return written

    def to_timeline(self, frame: int) -> int:
        """Map a frame in this source back onto the inner source's timeline."""
        return self._region.start + int(frame)

    def close(self) -> None:
        if self._owns_inner:
            self._inner.close()

    def __repr__(self) -> str:
        return f"RegionSource({self._inner!r}, {self._region!r})"


class LoopSource(BaseSampleSource):
    """Wraps a source so that reads past the end fold back to the start.

    With ``repeats=None`` the source is endless and reports
    :data:`ENDLESS_FRAMES` frames; with a count it is exactly that many passes
    long, which is what a bounced loop or a test needs. Either way a single
    :meth:`read` may span the seam, and the block that does is stitched rather
    than truncated — a loop that goes quiet for part of a block at the wrap
    point is the click the feature exists to avoid.
    """

    __slots__ = ("_inner", "_owns_inner", "_repeats")

    def __init__(
        self,
        inner: SampleSource,
        *,
        repeats: int | None = None,
        owns_inner: bool = False,
    ) -> None:
        if repeats is not None and repeats <= 0:
            raise ValueError(f"repeats must be positive or None, got {repeats}")
        self._inner = inner
        self._repeats = None if repeats is None else int(repeats)
        self._owns_inner = bool(owns_inner)

    @property
    def inner(self) -> SampleSource:
        return self._inner

    @property
    def repeats(self) -> int | None:
        return self._repeats

    @property
    def is_endless(self) -> bool:
        return self._repeats is None

    @property
    def cycle_frames(self) -> int:
        """Length of one pass through the inner source."""
        return int(self._inner.n_frames)

    @property
    def sample_rate(self) -> int:
        return int(self._inner.sample_rate)

    @property
    def n_frames(self) -> int:
        cycle = self.cycle_frames
        if cycle == 0:
            return 0
        return ENDLESS_FRAMES if self._repeats is None else cycle * self._repeats

    @property
    def n_channels(self) -> int:
        return int(self._inner.n_channels)

    @property
    def exact(self) -> bool:
        return bool(getattr(self._inner, "exact", True))

    def read(self, start: int, n_frames: int) -> np.ndarray:
        start, count = self._clamp(start, n_frames)
        cycle = self.cycle_frames
        if count == 0 or cycle == 0:
            return self._empty()
        out = np.empty((count, self.n_channels), dtype=SAMPLE_DTYPE)
        return out[: self._gather(out, start, count)]

    def read_into(self, out: np.ndarray, start: int) -> int:
        self._check_out(out)
        wanted = int(out.shape[0])
        start, count = self._clamp(start, wanted)
        written = 0 if self.cycle_frames == 0 else self._gather(out, start, count)
        if written < wanted:
            out[written:] = 0.0
        return written

    def _gather(self, out: np.ndarray, start: int, count: int) -> int:
        """Fill the head of ``out`` from ``start``, wrapping at every seam."""
        cycle = self.cycle_frames
        written = 0
        while written < count:
            offset = (start + written) % cycle
            take = min(count - written, cycle - offset)
            got = self._inner.read_into(out[written : written + take], offset)
            written += got
            if got < take:  # a truncated inner source: stop rather than spin
                break
        return written

    def close(self) -> None:
        if self._owns_inner:
            self._inner.close()

    def __repr__(self) -> str:
        passes = "endless" if self._repeats is None else f"{self._repeats}x"
        return f"LoopSource({self._inner!r}, {passes})"


__all__ = [
    "ENDLESS_FRAMES",
    "ArraySource",
    "BaseSampleSource",
    "ChunkTableSource",
    "FileStreamSource",
    "LoopSource",
    "MemorySampleSource",
    "RegionSource",
    "SampleSource",
    "StreamingSampleSource",
    "open_source",
]
