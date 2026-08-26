"""Non-destructive editing: a copy-on-write document plus an undoable command stack.

An :class:`AudioDocument` is an immutable list of :class:`Segment` views onto
immutable :class:`Chunk` arrays. Cutting ten seconds out of the middle of an
hour-long clip rewrites a handful of segment records and copies nothing; only a
command that actually changes sample values (gain, fade, silence) materialises
new chunks, and then only for the chunks the range touches. That is what makes
an unbounded undo history affordable — successive revisions share almost all of
their storage.

Editing goes through :class:`EditSession`, which owns the current document, a
clipboard and an :class:`UndoStack`. Because every revision is immutable, the
session publishes an edit by rebinding a single attribute: a feeder thread
reading through :meth:`EditSession.read` either sees the whole edit or none of
it, and never a half-spliced document.

:class:`EditSession` also satisfies the
:class:`~audio_studio.core.sample_source.SampleSource` protocol, so the
transport can play an edited document straight from the undo stack without
flattening it first.
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from bisect import bisect_right
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Final

import numpy as np

from .types import SAMPLE_DTYPE, AudioBuffer, TimeRange, db_to_amplitude

#: Frames per storage chunk. Small enough that a localised edit rewrites little,
#: large enough that a long document stays a short list of segments.
DEFAULT_CHUNK_FRAMES: Final[int] = 1 << 16

#: Envelope shapes accepted by :class:`FadeCommand`.
FADE_SHAPES: Final[tuple[str, ...]] = ("linear", "cosine", "exponential")


class EditError(RuntimeError):
    """Raised when a command cannot be applied to the current document."""


# ---------------------------------------------------------------- storage


@dataclass(frozen=True, slots=True)
class Chunk:
    """An immutable block of samples, shared freely between revisions."""

    data: np.ndarray

    def __post_init__(self) -> None:
        array = np.asarray(self.data, dtype=SAMPLE_DTYPE)
        if array.ndim == 1:
            array = array[:, np.newaxis]
        if array.ndim != 2:
            raise ValueError(f"a chunk must be 2-D, got {array.ndim}-D")
        array = np.ascontiguousarray(array)
        # Freezing the view is what makes sharing safe: a stale segment from an
        # undone revision can never observe a later edit. Ownership of the
        # underlying allocation is the caller's job — every constructor in this
        # module hands over an array no one else still holds a reference to.
        array.setflags(write=False)
        object.__setattr__(self, "data", array)

    @property
    def n_frames(self) -> int:
        return int(self.data.shape[0])

    @property
    def n_channels(self) -> int:
        return int(self.data.shape[1])


@dataclass(frozen=True, slots=True)
class Segment:
    """A half-open window ``[start, start + length)`` onto one :class:`Chunk`."""

    chunk: Chunk
    start: int
    length: int

    def __post_init__(self) -> None:
        if self.start < 0 or self.length < 0:
            raise ValueError(f"segment bounds must be non-negative, got {self!r}")
        if self.start + self.length > self.chunk.n_frames:
            raise ValueError(f"segment runs past the end of its chunk: {self!r}")

    @property
    def end(self) -> int:
        return self.start + self.length

    @property
    def data(self) -> np.ndarray:
        return self.chunk.data[self.start : self.end]

    def sub(self, offset: int, length: int) -> Segment:
        """A shorter window on the same chunk — no sample is copied."""
        offset = max(0, min(offset, self.length))
        length = max(0, min(length, self.length - offset))
        return Segment(self.chunk, self.start + offset, length)


def _split_into_chunks(data: np.ndarray, chunk_frames: int) -> tuple[Segment, ...]:
    total = int(data.shape[0])
    if total == 0:
        return ()
    return tuple(
        Segment(Chunk(data[offset : offset + chunk_frames]), 0, min(chunk_frames, total - offset))
        for offset in range(0, total, chunk_frames)
    )


class AudioDocument:
    """An immutable, chunk-shared view of an editable clip."""

    __slots__ = ("_channels", "_n_frames", "_offsets", "_sample_rate", "_segments")

    def __init__(
        self,
        segments: Iterable[Segment],
        sample_rate: int,
        n_channels: int,
    ) -> None:
        if sample_rate <= 0:
            raise ValueError(f"sample_rate must be positive, got {sample_rate}")
        if n_channels <= 0:
            raise ValueError(f"n_channels must be positive, got {n_channels}")

        kept: list[Segment] = []
        offsets: list[int] = []
        total = 0
        for segment in segments:
            if segment.length == 0:
                continue
            if segment.chunk.n_channels != n_channels:
                raise ValueError(
                    f"segment has {segment.chunk.n_channels} channels, document has {n_channels}"
                )
            offsets.append(total)
            kept.append(segment)
            total += segment.length

        self._segments: tuple[Segment, ...] = tuple(kept)
        self._offsets: tuple[int, ...] = tuple(offsets)
        self._n_frames = total
        self._sample_rate = int(sample_rate)
        self._channels = int(n_channels)

    # ------------------------------------------------------------ factories

    @classmethod
    def from_array(
        cls,
        data: np.ndarray,
        sample_rate: int,
        *,
        chunk_frames: int = DEFAULT_CHUNK_FRAMES,
        copy: bool = True,
    ) -> AudioDocument:
        """Chunk ``data`` into a document.

        ``copy=False`` adopts the array instead of duplicating it, and is only
        safe when the caller has just produced it and drops its own reference —
        the document has no other way to stop an outside write from mutating
        history that revisions are sharing.
        """
        array = np.asarray(data, dtype=SAMPLE_DTYPE)
        if array.ndim == 1:
            array = array[:, np.newaxis]
        if array.ndim != 2:
            raise ValueError(f"expected a (frames, channels) array, got {array.ndim}-D")
        if chunk_frames <= 0:
            raise ValueError(f"chunk_frames must be positive, got {chunk_frames}")
        if copy or not array.flags.c_contiguous:
            array = np.array(array, dtype=SAMPLE_DTYPE, order="C")
        return cls(_split_into_chunks(array, chunk_frames), sample_rate, int(array.shape[1]))

    @classmethod
    def from_buffer(
        cls, buffer: AudioBuffer, *, chunk_frames: int = DEFAULT_CHUNK_FRAMES, copy: bool = True
    ) -> AudioDocument:
        return cls.from_array(buffer.data, buffer.sample_rate, chunk_frames=chunk_frames, copy=copy)

    @classmethod
    def silence(cls, n_frames: int, sample_rate: int, n_channels: int) -> AudioDocument:
        if n_frames <= 0:
            return cls((), sample_rate, n_channels)
        chunk = Chunk(np.zeros((n_frames, n_channels), dtype=SAMPLE_DTYPE))
        return cls((Segment(chunk, 0, n_frames),), sample_rate, n_channels)

    # ------------------------------------------------------------ properties

    @property
    def segments(self) -> tuple[Segment, ...]:
        return self._segments

    @property
    def n_frames(self) -> int:
        return self._n_frames

    @property
    def n_channels(self) -> int:
        return self._channels

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def duration(self) -> float:
        return self._n_frames / self._sample_rate

    @property
    def n_segments(self) -> int:
        return len(self._segments)

    def stored_frames(self) -> int:
        """Frames held in distinct chunks — the document's real memory cost.

        Two revisions that share a chunk count it once, which is how a test can
        prove that copy-on-write is doing its job.
        """
        seen: dict[int, int] = {}
        for segment in self._segments:
            seen.setdefault(id(segment.chunk), segment.chunk.n_frames)
        return sum(seen.values())

    def __len__(self) -> int:
        return self._n_frames

    def __repr__(self) -> str:
        return (
            f"AudioDocument({self._n_frames} frames, {self._channels}ch @ "
            f"{self._sample_rate} Hz, {len(self._segments)} segments)"
        )

    # --------------------------------------------------------------- reading

    def _locate(self, frame: int) -> int:
        """Index of the segment containing ``frame`` (``len(segments)`` past the end)."""
        if frame >= self._n_frames:
            return len(self._segments)
        return bisect_right(self._offsets, frame) - 1

    def read(self, start: int, n_frames: int) -> np.ndarray:
        """Copy ``[start, start + n_frames)`` into a fresh contiguous array."""
        start = max(0, min(int(start), self._n_frames))
        count = max(0, min(int(n_frames), self._n_frames - start))
        out = np.empty((count, self._channels), dtype=SAMPLE_DTYPE)
        self._gather(out, start, count)
        return out

    def read_into(self, out: np.ndarray, start: int) -> int:
        """Fill a caller-owned buffer, zero-padding past the end. Allocates nothing."""
        if out.ndim != 2 or out.shape[1] != self._channels:
            raise ValueError(f"out must be (frames, {self._channels}), got {out.shape}")
        wanted = int(out.shape[0])
        start = max(0, min(int(start), self._n_frames))
        count = min(wanted, self._n_frames - start)
        self._gather(out, start, count)
        if count < wanted:
            out[count:] = 0.0
        return count

    def _gather(self, out: np.ndarray, start: int, count: int) -> None:
        """Walk the segment list, copying each overlapping slice into ``out``."""
        if count <= 0:
            return
        index = self._locate(start)
        written = 0
        while written < count and index < len(self._segments):
            segment = self._segments[index]
            offset = start + written - self._offsets[index]
            take = min(count - written, segment.length - offset)
            source = segment.start + offset
            out[written : written + take] = segment.chunk.data[source : source + take]
            written += take
            index += 1

    def to_array(self) -> np.ndarray:
        return self.read(0, self._n_frames)

    def to_buffer(self) -> AudioBuffer:
        return AudioBuffer(self.to_array(), self._sample_rate)

    # -------------------------------------------------------------- splicing

    def _rebuild(self, segments: Iterable[Segment]) -> AudioDocument:
        return AudioDocument(segments, self._sample_rate, self._channels)

    def _cut_at(self, frame: int) -> tuple[list[Segment], list[Segment]]:
        """Split the segment list at ``frame``, dividing one segment if needed."""
        frame = max(0, min(int(frame), self._n_frames))
        head: list[Segment] = []
        tail: list[Segment] = []
        for index, segment in enumerate(self._segments):
            offset = self._offsets[index]
            if offset + segment.length <= frame:
                head.append(segment)
            elif offset >= frame:
                tail.append(segment)
            else:
                boundary = frame - offset
                head.append(segment.sub(0, boundary))
                tail.append(segment.sub(boundary, segment.length - boundary))
        return head, tail

    def slice(self, rng: TimeRange) -> AudioDocument:
        """The sub-document covering ``rng``, still sharing the original chunks."""
        clipped = rng.clamped(self._n_frames)
        if clipped.is_empty:
            return self._rebuild(())
        _, tail = self._cut_at(clipped.start)
        middle = AudioDocument(tail, self._sample_rate, self._channels)
        head, _ = middle._cut_at(clipped.length)
        return self._rebuild(head)

    def delete(self, rng: TimeRange) -> AudioDocument:
        clipped = rng.clamped(self._n_frames)
        if clipped.is_empty:
            return self
        head, _ = self._cut_at(clipped.start)
        _, tail = self._cut_at(clipped.end)
        return self._rebuild([*head, *tail])

    def insert(self, at: int, other: AudioDocument) -> AudioDocument:
        if other.n_channels != self._channels:
            raise EditError(
                f"cannot insert {other.n_channels}-channel audio into a "
                f"{self._channels}-channel document"
            )
        if other.sample_rate != self._sample_rate:
            raise EditError(
                f"cannot insert {other.sample_rate} Hz audio into a {self._sample_rate} Hz document"
            )
        if other.n_frames == 0:
            return self
        head, tail = self._cut_at(at)
        return self._rebuild([*head, *other.segments, *tail])

    def replace(self, rng: TimeRange, other: AudioDocument) -> AudioDocument:
        return self.delete(rng).insert(rng.clamped(self._n_frames).start, other)

    def concat(self, other: AudioDocument) -> AudioDocument:
        return self.insert(self._n_frames, other)

    def map_range(self, rng: TimeRange, fn: Callable[[np.ndarray], np.ndarray]) -> AudioDocument:
        """Rewrite one range through ``fn``, leaving every other chunk shared."""
        clipped = rng.clamped(self._n_frames)
        if clipped.is_empty:
            return self
        processed = np.asarray(fn(self.read(clipped.start, clipped.length)), dtype=SAMPLE_DTYPE)
        if processed.ndim == 1:
            processed = processed[:, np.newaxis]
        if processed.shape != (clipped.length, self._channels):
            raise EditError(
                f"in-place edit must preserve the shape "
                f"{(clipped.length, self._channels)}, got {processed.shape}"
            )
        rewritten = AudioDocument.from_array(processed, self._sample_rate, copy=False)
        return self.replace(clipped, rewritten)


# ---------------------------------------------------------------- commands


class EditCommand(ABC):
    """One reversible edit.

    :meth:`apply` may record whatever it needs to reverse itself — commands are
    single-use and stay bound to the revision they were applied to. Storing the
    displaced audio is cheap because it is itself a chunk-sharing document.
    """

    label: str = "Edit"

    @abstractmethod
    def apply(self, document: AudioDocument) -> AudioDocument: ...

    @abstractmethod
    def revert(self, document: AudioDocument) -> AudioDocument: ...

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.label!r})"


class _RangeCommand(EditCommand):
    """Base for commands that rewrite a range in place and restore it verbatim."""

    def __init__(self, rng: TimeRange) -> None:
        self._range = rng
        self._original: AudioDocument | None = None

    @property
    def range(self) -> TimeRange:
        return self._range

    @abstractmethod
    def _process(self, block: np.ndarray, sample_rate: int) -> np.ndarray: ...

    def apply(self, document: AudioDocument) -> AudioDocument:
        clipped = self._range.clamped(document.n_frames)
        if clipped.is_empty:
            raise EditError(f"{self.label}: empty range {self._range!r}")
        self._range = clipped
        self._original = document.slice(clipped)
        rate = document.sample_rate
        return document.map_range(clipped, lambda block: self._process(block, rate))

    def revert(self, document: AudioDocument) -> AudioDocument:
        if self._original is None:
            raise EditError(f"{self.label}: revert() before apply()")
        return document.replace(self._range, self._original)


class DeleteCommand(EditCommand):
    """Remove a range and close the gap."""

    label = "Delete"

    def __init__(self, rng: TimeRange) -> None:
        self._range = rng
        self._removed: AudioDocument | None = None

    @property
    def range(self) -> TimeRange:
        return self._range

    @property
    def removed(self) -> AudioDocument | None:
        """The audio taken out, kept so undo can splice it back."""
        return self._removed

    def apply(self, document: AudioDocument) -> AudioDocument:
        clipped = self._range.clamped(document.n_frames)
        if clipped.is_empty:
            raise EditError(f"{self.label}: empty range {self._range!r}")
        self._range = clipped
        self._removed = document.slice(clipped)
        return document.delete(clipped)

    def revert(self, document: AudioDocument) -> AudioDocument:
        if self._removed is None:
            raise EditError(f"{self.label}: revert() before apply()")
        return document.insert(self._range.start, self._removed)


class CutCommand(DeleteCommand):
    """Delete a range and hand it to the session clipboard."""

    label = "Cut"


class PasteCommand(EditCommand):
    """Insert audio at a frame, or replace a selection with it."""

    label = "Paste"

    def __init__(self, at: int, payload: AudioDocument, *, replacing: TimeRange | None = None):
        self._at = int(at)
        self._payload = payload
        self._replaced_range = replacing
        self._replaced: AudioDocument | None = None
        self._inserted = 0

    @property
    def inserted_range(self) -> TimeRange:
        return TimeRange(self._at, self._at + self._inserted)

    def apply(self, document: AudioDocument) -> AudioDocument:
        if self._payload.n_frames == 0:
            raise EditError(f"{self.label}: nothing on the clipboard")
        result = document
        if self._replaced_range is not None:
            clipped = self._replaced_range.clamped(document.n_frames)
            self._replaced_range = clipped
            self._replaced = document.slice(clipped)
            result = document.delete(clipped)
            self._at = clipped.start
        self._at = max(0, min(self._at, result.n_frames))
        self._inserted = self._payload.n_frames
        return result.insert(self._at, self._payload)

    def revert(self, document: AudioDocument) -> AudioDocument:
        result = document.delete(TimeRange(self._at, self._at + self._inserted))
        if self._replaced is not None and self._replaced_range is not None:
            result = result.insert(self._replaced_range.start, self._replaced)
        return result


class InsertSilenceCommand(EditCommand):
    """Push everything after ``at`` later by inserting silence."""

    label = "Insert Silence"

    def __init__(self, at: int, n_frames: int) -> None:
        self._at = int(at)
        self._n_frames = int(n_frames)

    def apply(self, document: AudioDocument) -> AudioDocument:
        if self._n_frames <= 0:
            raise EditError(f"{self.label}: need a positive length, got {self._n_frames}")
        self._at = max(0, min(self._at, document.n_frames))
        silence = AudioDocument.silence(self._n_frames, document.sample_rate, document.n_channels)
        return document.insert(self._at, silence)

    def revert(self, document: AudioDocument) -> AudioDocument:
        return document.delete(TimeRange(self._at, self._at + self._n_frames))


class SilenceCommand(_RangeCommand):
    """Mute a range without changing the timeline length."""

    label = "Silence"

    def _process(self, block: np.ndarray, _sample_rate: int) -> np.ndarray:
        return np.zeros_like(block)


class GainCommand(_RangeCommand):
    """Scale a range by a fixed number of decibels."""

    label = "Gain"

    def __init__(self, rng: TimeRange, gain_db: float) -> None:
        super().__init__(rng)
        self._gain_db = float(gain_db)

    @property
    def gain_db(self) -> float:
        return self._gain_db

    def _process(self, block: np.ndarray, _sample_rate: int) -> np.ndarray:
        return block * SAMPLE_DTYPE(db_to_amplitude(self._gain_db))


class FadeCommand(_RangeCommand):
    """Apply a fade-in or fade-out envelope across a range."""

    label = "Fade"

    def __init__(self, rng: TimeRange, *, direction: str = "in", shape: str = "linear") -> None:
        super().__init__(rng)
        if direction not in ("in", "out"):
            raise ValueError(f"direction must be 'in' or 'out', got {direction!r}")
        if shape not in FADE_SHAPES:
            raise ValueError(f"shape must be one of {FADE_SHAPES}, got {shape!r}")
        self._direction = direction
        self._shape = shape
        self.label = f"Fade {direction.capitalize()}"

    @property
    def direction(self) -> str:
        return self._direction

    @property
    def shape(self) -> str:
        return self._shape

    def _process(self, block: np.ndarray, _sample_rate: int) -> np.ndarray:
        n = block.shape[0]
        # ``endpoint=False`` on a fade-in would never reach unity gain; a fade
        # that does not close the seam is exactly the click it exists to avoid.
        ramp = np.linspace(0.0, 1.0, n, dtype=np.float64) if n > 1 else np.ones(1)
        if self._shape == "cosine":
            envelope = 0.5 - 0.5 * np.cos(np.pi * ramp)
        elif self._shape == "exponential":
            envelope = ramp**2
        else:
            envelope = ramp
        if self._direction == "out":
            envelope = envelope[::-1]
        return (block * envelope[:, np.newaxis]).astype(SAMPLE_DTYPE)


class ReverseCommand(_RangeCommand):
    """Play a range backwards; its own inverse, but recorded like any other edit."""

    label = "Reverse"

    def _process(self, block: np.ndarray, _sample_rate: int) -> np.ndarray:
        return block[::-1]


class TrimCommand(EditCommand):
    """Discard everything outside a range (Audition's "trim to selection")."""

    label = "Trim"

    def __init__(self, rng: TimeRange) -> None:
        self._range = rng
        self._head: AudioDocument | None = None
        self._tail: AudioDocument | None = None

    def apply(self, document: AudioDocument) -> AudioDocument:
        clipped = self._range.clamped(document.n_frames)
        if clipped.is_empty:
            raise EditError(f"{self.label}: empty range {self._range!r}")
        self._range = clipped
        self._head = document.slice(TimeRange(0, clipped.start))
        self._tail = document.slice(TimeRange(clipped.end, document.n_frames))
        return document.slice(clipped)

    def revert(self, document: AudioDocument) -> AudioDocument:
        if self._head is None or self._tail is None:
            raise EditError(f"{self.label}: revert() before apply()")
        return self._head.concat(document).concat(self._tail)


# --------------------------------------------------------------- undo stack


@dataclass(frozen=True, slots=True)
class UndoEntry:
    """One applied command together with the revision it produced."""

    command: EditCommand
    before: AudioDocument
    after: AudioDocument

    @property
    def label(self) -> str:
        return self.command.label


class UndoStack:
    """Linear undo history with a bounded depth and a clean-state marker."""

    __slots__ = ("_clean_index", "_entries", "_index", "_limit")

    def __init__(self, limit: int = 200) -> None:
        if limit <= 0:
            raise ValueError(f"limit must be positive, got {limit}")
        self._entries: list[UndoEntry] = []
        self._index = 0  # number of entries currently applied
        self._limit = int(limit)
        self._clean_index = 0

    @property
    def limit(self) -> int:
        return self._limit

    @property
    def index(self) -> int:
        return self._index

    @property
    def depth(self) -> int:
        return len(self._entries)

    @property
    def can_undo(self) -> bool:
        return self._index > 0

    @property
    def can_redo(self) -> bool:
        return self._index < len(self._entries)

    @property
    def undo_label(self) -> str | None:
        return self._entries[self._index - 1].label if self.can_undo else None

    @property
    def redo_label(self) -> str | None:
        return self._entries[self._index].label if self.can_redo else None

    @property
    def is_clean(self) -> bool:
        """True when the document matches the last saved revision."""
        return self._index == self._clean_index

    def set_clean(self) -> None:
        self._clean_index = self._index

    def labels(self) -> list[str]:
        return [entry.label for entry in self._entries]

    def push(self, command: EditCommand, before: AudioDocument, after: AudioDocument) -> None:
        """Record an already-applied command, discarding any redo branch."""
        del self._entries[self._index :]
        self._entries.append(UndoEntry(command, before, after))
        self._index += 1
        if len(self._entries) > self._limit:
            dropped = len(self._entries) - self._limit
            del self._entries[:dropped]
            self._index -= dropped
            self._clean_index = max(self._clean_index - dropped, -1)

    def undo(self) -> UndoEntry:
        if not self.can_undo:
            raise EditError("nothing to undo")
        self._index -= 1
        return self._entries[self._index]

    def redo(self) -> UndoEntry:
        if not self.can_redo:
            raise EditError("nothing to redo")
        entry = self._entries[self._index]
        self._index += 1
        return entry

    def clear(self) -> None:
        self._entries.clear()
        self._index = 0
        self._clean_index = 0

    def __len__(self) -> int:
        return len(self._entries)


# -------------------------------------------------------------- the session

SessionListener = Callable[["EditSession"], None]


class EditSession:
    """The editable document, its clipboard and its history.

    Reads are lock-free by construction: the current document is an immutable
    object rebound in one assignment, so a playback thread calling :meth:`read`
    always works against a complete revision. Mutations are serialised by a
    lock, which only ever contends with other *editing* calls.
    """

    __slots__ = (
        "_clipboard",
        "_document",
        "_listeners",
        "_lock",
        "_revision",
        "_undo",
    )

    def __init__(
        self,
        document: AudioDocument | AudioBuffer | None = None,
        *,
        sample_rate: int = 44_100,
        n_channels: int = 2,
        undo_limit: int = 200,
    ) -> None:
        if isinstance(document, AudioBuffer):
            document = AudioDocument.from_buffer(document)
        elif document is None:
            document = AudioDocument((), sample_rate, n_channels)
        self._document = document
        self._undo = UndoStack(undo_limit)
        self._clipboard: AudioDocument | None = None
        self._listeners: list[SessionListener] = []
        self._revision = 0
        self._lock = threading.RLock()

    # ------------------------------------------------------------ factories

    @classmethod
    def from_buffer(cls, buffer: AudioBuffer, *, undo_limit: int = 200) -> EditSession:
        return cls(AudioDocument.from_buffer(buffer), undo_limit=undo_limit)

    @classmethod
    def from_array(
        cls, data: np.ndarray, sample_rate: int, *, undo_limit: int = 200
    ) -> EditSession:
        return cls(AudioDocument.from_array(data, sample_rate), undo_limit=undo_limit)

    # ----------------------------------------------------------- properties

    @property
    def document(self) -> AudioDocument:
        return self._document

    @property
    def undo_stack(self) -> UndoStack:
        return self._undo

    @property
    def clipboard(self) -> AudioDocument | None:
        return self._clipboard

    @property
    def revision(self) -> int:
        """Bumped on every change; cheap invalidation key for caches and views."""
        return self._revision

    @property
    def sample_rate(self) -> int:
        return self._document.sample_rate

    @property
    def n_frames(self) -> int:
        return self._document.n_frames

    @property
    def n_channels(self) -> int:
        return self._document.n_channels

    @property
    def duration(self) -> float:
        return self._document.duration

    @property
    def is_modified(self) -> bool:
        return not self._undo.is_clean

    # -------------------------------------------------- SampleSource surface

    def read(self, start: int, n_frames: int) -> np.ndarray:
        # One attribute load: the revision cannot change under our feet.
        return self._document.read(start, n_frames)

    def read_into(self, out: np.ndarray, start: int) -> int:
        """Serve the feeder thread straight from the current revision."""
        return self._document.read_into(out, start)

    @property
    def exact(self) -> bool:
        """An edit document is already in memory, so reads never block."""
        return True

    @property
    def last_error(self) -> Exception | None:
        return None

    def read_range(self, rng: TimeRange) -> np.ndarray:
        clipped = rng.clamped(self.n_frames)
        return self.read(clipped.start, clipped.length)

    def to_buffer(self, rng: TimeRange | None = None) -> AudioBuffer:
        document = self._document
        return (document if rng is None else document.slice(rng)).to_buffer()

    def close(self) -> None:
        """Present for the SampleSource protocol; a session owns no OS handle."""

    # ------------------------------------------------------------ listeners

    def add_listener(self, listener: SessionListener) -> None:
        self._listeners.append(listener)

    def remove_listener(self, listener: SessionListener) -> None:
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _publish(self, document: AudioDocument) -> None:
        self._document = document
        self._revision += 1
        for listener in tuple(self._listeners):
            listener(self)

    # ------------------------------------------------------------- mutation

    def reset(self, document: AudioDocument | AudioBuffer | None) -> None:
        """Load a new document and drop the history (used when opening a file)."""
        if isinstance(document, AudioBuffer):
            document = AudioDocument.from_buffer(document)
        with self._lock:
            self._undo.clear()
            self._clipboard = None
            self._publish(
                document
                if document is not None
                else AudioDocument((), self.sample_rate, self.n_channels)
            )
            self._undo.set_clean()

    def execute(self, command: EditCommand) -> AudioDocument:
        """Apply ``command`` and push it onto the history."""
        with self._lock:
            before = self._document
            after = command.apply(before)
            self._undo.push(command, before, after)
            self._publish(after)
            return after

    def undo(self) -> bool:
        """Step back one revision; returns False when the history is exhausted."""
        with self._lock:
            if not self._undo.can_undo:
                return False
            entry = self._undo.undo()
            restored = entry.command.revert(self._document)
            self._publish(restored)
            return True

    def redo(self) -> bool:
        with self._lock:
            if not self._undo.can_redo:
                return False
            entry = self._undo.redo()
            self._publish(entry.command.apply(self._document))
            return True

    @property
    def can_undo(self) -> bool:
        return self._undo.can_undo

    @property
    def can_redo(self) -> bool:
        return self._undo.can_redo

    # ------------------------------------------------------ editing verbs

    def _require_range(self, rng: TimeRange) -> TimeRange:
        clipped = rng.clamped(self.n_frames)
        if clipped.is_empty:
            raise EditError(f"empty selection {rng!r}")
        return clipped

    def copy(self, rng: TimeRange) -> AudioDocument:
        """Put a range on the clipboard without touching the document."""
        clipped = self._require_range(rng)
        with self._lock:
            self._clipboard = self._document.slice(clipped)
            return self._clipboard

    def cut(self, rng: TimeRange) -> AudioDocument:
        with self._lock:
            command = CutCommand(self._require_range(rng))
            self.execute(command)
            assert command.removed is not None
            self._clipboard = command.removed
            return self._clipboard

    def delete(self, rng: TimeRange) -> AudioDocument:
        return self.execute(DeleteCommand(self._require_range(rng)))

    def paste(
        self,
        at: int,
        payload: AudioDocument | AudioBuffer | np.ndarray | None = None,
        *,
        replacing: TimeRange | None = None,
    ) -> AudioDocument:
        """Insert the clipboard (or ``payload``) at ``at``."""
        with self._lock:
            document = self._as_document(payload) if payload is not None else self._clipboard
            if document is None or document.n_frames == 0:
                raise EditError("nothing on the clipboard")
            return self.execute(PasteCommand(at, document, replacing=replacing))

    def insert_silence(self, at: int, n_frames: int) -> AudioDocument:
        return self.execute(InsertSilenceCommand(at, n_frames))

    def silence(self, rng: TimeRange) -> AudioDocument:
        return self.execute(SilenceCommand(self._require_range(rng)))

    def apply_gain(self, rng: TimeRange, gain_db: float) -> AudioDocument:
        return self.execute(GainCommand(self._require_range(rng), gain_db))

    def fade_in(self, rng: TimeRange, *, shape: str = "linear") -> AudioDocument:
        return self.execute(FadeCommand(self._require_range(rng), direction="in", shape=shape))

    def fade_out(self, rng: TimeRange, *, shape: str = "linear") -> AudioDocument:
        return self.execute(FadeCommand(self._require_range(rng), direction="out", shape=shape))

    def reverse(self, rng: TimeRange) -> AudioDocument:
        return self.execute(ReverseCommand(self._require_range(rng)))

    def trim(self, rng: TimeRange) -> AudioDocument:
        return self.execute(TrimCommand(self._require_range(rng)))

    def _as_document(self, payload: AudioDocument | AudioBuffer | np.ndarray) -> AudioDocument:
        if isinstance(payload, AudioDocument):
            return payload
        if isinstance(payload, AudioBuffer):
            return AudioDocument.from_buffer(payload)
        return AudioDocument.from_array(payload, self.sample_rate)

    def __repr__(self) -> str:
        return (
            f"EditSession({self.n_frames} frames, {self.n_channels}ch @ "
            f"{self.sample_rate} Hz, rev {self._revision}, "
            f"{self._undo.index}/{self._undo.depth} undo)"
        )


__all__ = [
    "DEFAULT_CHUNK_FRAMES",
    "FADE_SHAPES",
    "AudioDocument",
    "Chunk",
    "CutCommand",
    "DeleteCommand",
    "EditCommand",
    "EditError",
    "EditSession",
    "FadeCommand",
    "GainCommand",
    "InsertSilenceCommand",
    "PasteCommand",
    "ReverseCommand",
    "Segment",
    "SilenceCommand",
    "TrimCommand",
    "UndoEntry",
    "UndoStack",
]
