"""Lock-free SPSC ring buffer decoupling the decode thread from the device callback.

The buffer stores frames as a ``(capacity, channels)`` float32 array addressed
by two *monotonically increasing* frame counters. ``_write`` is owned by the
single producer (the engine's feeder thread) and ``_read`` by the single
consumer (the output device callback); neither thread ever writes the other's
counter, so no mutual exclusion is required and the device callback can never
be blocked by the feeder.

Correctness rests on three properties:

* **Single writer per counter.** Because ``_read <= _write`` always holds and
  both only ever grow, ``_write - _read`` is the queued frame count and
  ``capacity - (_write - _read)`` the free space — the classic "never let the
  buffer become ambiguous at full" trick, without wasting a slot.
* **Publish after copy.** Each side copies its frames *before* advancing its
  counter. In CPython a counter update is a single ``STORE_ATTR`` bytecode, so
  under the GIL the payload is always visible before the index that publishes
  it. A C++/JUCE port would spell this out as a release store paired with an
  acquire load.
* **Conservative snapshots.** A thread reads the other side's counter first and
  its own second. A stale value can then only make the buffer look *fuller*
  (to the producer) or *emptier* (to the consumer) than it really is, which
  costs a little throughput and never corrupts data.

:meth:`RingBuffer.clear` is the one control-thread operation. It only ever
moves the read counter forward, so a concurrent consumer can lose the race but
can never be made to replay frames it has already delivered.
"""

from __future__ import annotations

import numpy as np

from .types import SAMPLE_DTYPE


class RingBuffer:
    """Single-producer / single-consumer circular frame buffer."""

    __slots__ = (
        "_buffer",
        "_capacity",
        "_channels",
        "_overrun_frames",
        "_read",
        "_underrun_frames",
        "_write",
    )

    def __init__(self, capacity: int, channels: int) -> None:
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity}")
        if channels <= 0:
            raise ValueError(f"channels must be positive, got {channels}")
        self._capacity = int(capacity)
        self._channels = int(channels)
        self._buffer = np.zeros((self._capacity, self._channels), dtype=SAMPLE_DTYPE)
        # Monotonic frame counters. ``_read`` belongs to the consumer, ``_write``
        # to the producer; Python ints never wrap so the difference is exact.
        self._read = 0
        self._write = 0
        self._overrun_frames = 0
        self._underrun_frames = 0

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def channels(self) -> int:
        return self._channels

    def __len__(self) -> int:
        return self.available_read

    @property
    def available_read(self) -> int:
        """Frames currently queued for the consumer."""
        write = self._write
        read = self._read
        # Clamped because a control thread (which owns neither counter) can
        # observe the two loads straddling a concurrent update.
        return min(max(write - read, 0), self._capacity)

    @property
    def available_write(self) -> int:
        """Free frames the producer may still push."""
        return self._capacity - self.available_read

    @property
    def frames_written(self) -> int:
        """Total frames accepted since construction (never reset by :meth:`clear`)."""
        return self._write

    @property
    def frames_read(self) -> int:
        """Total frames handed to the consumer, including frames dropped by :meth:`clear`."""
        return self._read

    @property
    def overrun_frames(self) -> int:
        """Frames refused because the consumer fell behind.

        Stays at zero for a producer that sizes each write to
        :attr:`available_write`, so a non-zero reading is real backpressure.
        """
        return self._overrun_frames

    @property
    def underrun_frames(self) -> int:
        """Frames the consumer had to zero-fill because the producer fell behind."""
        return self._underrun_frames

    def reset_xrun_counters(self) -> None:
        self._overrun_frames = 0
        self._underrun_frames = 0

    def clear(self) -> None:
        """Drop all queued frames (used on seek and stop).

        Called from the control thread. The read counter is only ever advanced,
        so racing with an in-flight :meth:`read` can at worst discard a block
        the consumer had already taken — never resurrect one.
        """
        write = self._write
        if write > self._read:
            self._read = write

    def write(self, frames: np.ndarray) -> int:
        """Append frames, returning how many were accepted.

        Frames beyond the free space are dropped rather than blocking, so a
        stalled consumer can never deadlock the producer.
        """
        block = np.asarray(frames, dtype=SAMPLE_DTYPE)
        if block.ndim == 1:
            block = block[:, np.newaxis]
        if block.shape[1] != self._channels:
            raise ValueError(
                f"channel count mismatch: buffer has {self._channels}, got {block.shape[1]}"
            )

        offered = int(block.shape[0])
        write = self._write
        free = self._capacity - (write - self._read)
        n = min(offered, free)
        if n <= 0:
            self._overrun_frames += offered
            return 0

        index = write % self._capacity
        first = min(n, self._capacity - index)
        self._buffer[index : index + first] = block[:first]
        remainder = n - first
        if remainder:
            self._buffer[:remainder] = block[first:n]

        # Publish only after the payload is in place.
        self._write = write + n
        if n < offered:
            self._overrun_frames += offered - n
        return n

    def read(self, n_frames: int, *, pad: bool = False) -> np.ndarray:
        """Pop up to ``n_frames`` frames.

        With ``pad=True`` the result is always exactly ``n_frames`` long,
        zero-filled on underrun -- what a device callback needs to keep the
        stream glitch-free.
        """
        if n_frames < 0:
            raise ValueError(f"n_frames must be non-negative, got {n_frames}")

        read = self._read
        available = max(self._write - read, 0)
        n = min(n_frames, available)
        out = np.zeros((n_frames if pad else n, self._channels), dtype=SAMPLE_DTYPE)
        if n:
            index = read % self._capacity
            first = min(n, self._capacity - index)
            out[:first] = self._buffer[index : index + first]
            remainder = n - first
            if remainder:
                out[first:n] = self._buffer[:remainder]
            # Free the slots only after the payload has been copied out.
            self._read = read + n
        if n < n_frames:
            self._underrun_frames += n_frames - n
        return out

    def peek(self, n_frames: int) -> np.ndarray:
        """Return queued frames without consuming them (metering / debugging)."""
        read = self._read
        n = max(min(n_frames, self._write - read), 0)
        out = np.empty((n, self._channels), dtype=SAMPLE_DTYPE)
        if n:
            index = read % self._capacity
            first = min(n, self._capacity - index)
            out[:first] = self._buffer[index : index + first]
            if n - first:
                out[first:n] = self._buffer[: n - first]
        return out
