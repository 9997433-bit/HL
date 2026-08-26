"""Random-access sample providers behind a single protocol.

The transport does not care whether the frames it plays live in RAM, are being
pulled off disk a block at a time, or are synthesised by an edit graph — it
only needs to ask "give me ``n`` frames starting at ``start``". Expressing that
as :class:`SampleSource` is what lets a one-hour 96 kHz session open instantly
(:class:`StreamingSampleSource`) while short clips and edited documents keep the
zero-copy in-memory path (:class:`MemorySampleSource`).

Every implementation returns a freshly allocated, C-contiguous
``(n_frames, channels)`` float32 array and clamps out-of-range requests to the
source length instead of raising, because the caller is usually a feeder thread
that must not throw.
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from collections import OrderedDict
from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np

from .types import SAMPLE_DTYPE, AudioBuffer, TimeRange

#: Frames pulled from disk in one libsndfile call. At 48 kHz stereo float32 a
#: block is 512 kB, large enough that seek overhead disappears into the read and
#: small enough that a handful of cached blocks stay in L3/page cache.
DEFAULT_BLOCK_FRAMES: int = 65_536

#: Decoded blocks retained per streaming source. Playback is sequential, so a
#: short LRU absorbs the read-ahead of the feeder without pinning the file.
DEFAULT_CACHE_BLOCKS: int = 8


@runtime_checkable
class SampleSource(Protocol):
    """Anything the transport can play: a random-access window onto PCM audio."""

    @property
    def sample_rate(self) -> int: ...

    @property
    def n_frames(self) -> int: ...

    @property
    def n_channels(self) -> int: ...

    def read(self, start: int, n_frames: int) -> np.ndarray:
        """Return ``[start, start + n_frames)`` as ``(frames, channels)`` float32."""
        ...

    def close(self) -> None: ...


class BaseSampleSource(ABC):
    """Shared plumbing: bounds clamping, slicing helpers, context management."""

    @property
    @abstractmethod
    def sample_rate(self) -> int: ...

    @property
    @abstractmethod
    def n_frames(self) -> int: ...

    @property
    @abstractmethod
    def n_channels(self) -> int: ...

    @abstractmethod
    def read(self, start: int, n_frames: int) -> np.ndarray: ...

    @property
    def duration(self) -> float:
        rate = self.sample_rate
        return self.n_frames / rate if rate else 0.0

    def _clamp(self, start: int, n_frames: int) -> tuple[int, int]:
        """Intersect the request with the source, returning ``(start, count)``."""
        total = self.n_frames
        start = max(0, min(int(start), total))
        count = max(0, min(int(n_frames), total - start))
        return start, count

    def _empty(self) -> np.ndarray:
        return np.zeros((0, max(self.n_channels, 1)), dtype=SAMPLE_DTYPE)

    def read_range(self, rng: TimeRange) -> np.ndarray:
        clipped = rng.clamped(self.n_frames)
        return self.read(clipped.start, clipped.length)

    def to_buffer(self, rng: TimeRange | None = None) -> AudioBuffer:
        """Materialise the whole source (or one range) into memory."""
        data = self.read(0, self.n_frames) if rng is None else self.read_range(rng)
        return AudioBuffer(data, self.sample_rate)

    def blocks(self, block_frames: int = DEFAULT_BLOCK_FRAMES, *, start: int = 0):
        """Iterate the source in bounded chunks, for analysis that must not slurp."""
        if block_frames <= 0:
            raise ValueError(f"block_frames must be positive, got {block_frames}")
        position = max(0, int(start))
        total = self.n_frames
        while position < total:
            block = self.read(position, min(block_frames, total - position))
            if block.shape[0] == 0:
                return
            yield block
            position += block.shape[0]

    def close(self) -> None:
        """Release any backing resource. Idempotent by contract."""

    def __enter__(self) -> BaseSampleSource:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


class MemorySampleSource(BaseSampleSource):
    """Sample source backed by an :class:`AudioBuffer` already in RAM."""

    __slots__ = ("_buffer",)

    def __init__(self, buffer: AudioBuffer | np.ndarray, sample_rate: int | None = None) -> None:
        if isinstance(buffer, AudioBuffer):
            if sample_rate is not None and sample_rate != buffer.sample_rate:
                raise ValueError(
                    "sample_rate contradicts the buffer's own rate "
                    f"({sample_rate} vs {buffer.sample_rate})"
                )
            self._buffer = buffer
        else:
            if sample_rate is None:
                raise ValueError("sample_rate is required when constructing from a raw array")
            self._buffer = AudioBuffer(buffer, sample_rate)

    @property
    def buffer(self) -> AudioBuffer:
        return self._buffer

    @property
    def sample_rate(self) -> int:
        return self._buffer.sample_rate

    @property
    def n_frames(self) -> int:
        return self._buffer.n_frames

    @property
    def n_channels(self) -> int:
        return self._buffer.n_channels

    def read(self, start: int, n_frames: int) -> np.ndarray:
        start, count = self._clamp(start, n_frames)
        if count == 0:
            return self._empty()
        # Copied so a caller can hold or mutate the block without aliasing the clip.
        return np.array(self._buffer.data[start : start + count], dtype=SAMPLE_DTYPE)

    def view(self, start: int, n_frames: int) -> np.ndarray:
        """Zero-copy variant for callers that promise not to mutate the result."""
        start, count = self._clamp(start, n_frames)
        return self._buffer.data[start : start + count]

    def to_buffer(self, rng: TimeRange | None = None) -> AudioBuffer:
        return self._buffer if rng is None else self._buffer.slice(rng)

    def __repr__(self) -> str:
        return (
            f"MemorySampleSource({self.n_frames} frames, "
            f"{self.n_channels}ch @ {self.sample_rate} Hz)"
        )


class StreamingSampleSource(BaseSampleSource):
    """Sample source that decodes from disk on demand through libsndfile.

    Requests are served from an LRU of fixed-size decoded blocks, so sequential
    playback costs one ``seek`` + one ``read`` per block rather than per call,
    and a short backwards jump (a loop point, a scrub) usually hits the cache.

    The instance is safe to share between the feeder thread and the GUI thread:
    the file handle and the cache sit behind one lock. Nothing here belongs on
    the device callback — the callback drains the ring buffer, which is exactly
    what the ring buffer exists for.
    """

    __slots__ = (
        "_block_frames",
        "_cache",
        "_cache_blocks",
        "_channels",
        "_closed",
        "_handle",
        "_lock",
        "_n_frames",
        "_path",
        "_sample_rate",
        "_subtype",
    )

    def __init__(
        self,
        path: str | Path,
        *,
        block_frames: int = DEFAULT_BLOCK_FRAMES,
        cache_blocks: int = DEFAULT_CACHE_BLOCKS,
    ) -> None:
        if block_frames <= 0:
            raise ValueError(f"block_frames must be positive, got {block_frames}")
        if cache_blocks <= 0:
            raise ValueError(f"cache_blocks must be positive, got {cache_blocks}")

        import soundfile as sf

        self._path = Path(path)
        self._block_frames = int(block_frames)
        self._cache_blocks = int(cache_blocks)
        self._cache: OrderedDict[int, np.ndarray] = OrderedDict()
        self._lock = threading.Lock()
        self._closed = False

        try:
            self._handle = sf.SoundFile(str(self._path), mode="r")
        except Exception as exc:  # noqa: BLE001 - normalised into the loader's error type
            from .loader import AudioLoadError

            raise AudioLoadError(f"Cannot stream {self._path}: {exc}") from exc

        self._sample_rate = int(self._handle.samplerate)
        self._channels = int(self._handle.channels)
        self._n_frames = int(self._handle.frames)
        self._subtype = str(self._handle.subtype or "UNKNOWN")

    # ------------------------------------------------------------- metadata

    @property
    def path(self) -> Path:
        return self._path

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def n_frames(self) -> int:
        return self._n_frames

    @property
    def n_channels(self) -> int:
        return self._channels

    @property
    def block_frames(self) -> int:
        return self._block_frames

    @property
    def subtype(self) -> str:
        return self._subtype

    @property
    def is_closed(self) -> bool:
        return self._closed

    def audio_format(self):  # noqa: ANN201 - avoids a circular import at module scope
        """Container metadata matching what :func:`~.loader.probe` would report."""
        from .types import AudioFormat

        container = self._path.suffix.lstrip(".").upper() or "UNKNOWN"
        with self._lock:
            if not self._closed:
                container = str(self._handle.format or container)
        return AudioFormat(
            sample_rate=self._sample_rate,
            channels=self._channels,
            subtype=self._subtype,
            container=container,
        )

    # ------------------------------------------------------------------ I/O

    def read(self, start: int, n_frames: int) -> np.ndarray:
        start, count = self._clamp(start, n_frames)
        if count == 0:
            return self._empty()

        out = np.empty((count, self._channels), dtype=SAMPLE_DTYPE)
        written = 0
        while written < count:
            position = start + written
            block_index = position // self._block_frames
            offset = position - block_index * self._block_frames
            block = self._block(block_index)
            take = min(count - written, block.shape[0] - offset)
            if take <= 0:  # truncated file: stop rather than spin
                return out[:written]
            out[written : written + take] = block[offset : offset + take]
            written += take
        return out

    def _block(self, index: int) -> np.ndarray:
        with self._lock:
            cached = self._cache.get(index)
            if cached is not None:
                self._cache.move_to_end(index)
                return cached
            if self._closed:
                raise ValueError(f"read from a closed StreamingSampleSource: {self._path}")

            start = index * self._block_frames
            self._handle.seek(start)
            data = self._handle.read(
                self._block_frames, dtype="float32", always_2d=True, fill_value=None
            )
            block = np.ascontiguousarray(data, dtype=SAMPLE_DTYPE)
            self._cache[index] = block
            while len(self._cache) > self._cache_blocks:
                self._cache.popitem(last=False)
            return block

    def prefetch(self, start: int, n_frames: int) -> None:
        """Warm the cache for a range that is about to be played."""
        start, count = self._clamp(start, n_frames)
        if count == 0:
            return
        first = start // self._block_frames
        last = (start + count - 1) // self._block_frames
        for index in range(first, min(last, first + self._cache_blocks - 1) + 1):
            self._block(index)

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._cache.clear()
            try:
                self._handle.close()
            except Exception:  # noqa: BLE001 - closing twice must not explode
                pass

    def __repr__(self) -> str:
        return (
            f"StreamingSampleSource({self._path.name!r}, {self._n_frames} frames, "
            f"{self._channels}ch @ {self._sample_rate} Hz)"
        )


def open_source(
    path: str | Path,
    *,
    streaming: bool | None = None,
    memory_limit_frames: int = 30 * 60 * 48_000,
) -> BaseSampleSource:
    """Open ``path`` as the cheapest source that can serve it.

    With ``streaming=None`` the decision is made from the file's length: short
    material is decoded up front (fastest random access, needed for waveform
    summaries) while anything past ``memory_limit_frames`` is streamed.
    """
    from .loader import load_audio, probe

    path = Path(path)
    if streaming is None:
        try:
            import soundfile as sf

            info = sf.info(str(path))
            streaming = int(info.frames) > memory_limit_frames
        except Exception:  # noqa: BLE001 - let the real decoder report the failure
            streaming = False
    if streaming:
        return StreamingSampleSource(path)
    probe(path)  # surfaces an unreadable container as AudioLoadError
    return MemorySampleSource(load_audio(path).buffer)
