"""Fixed-capacity ring buffer decoupling the decode thread from the device callback.

The buffer stores frames as a ``(capacity, channels)`` float32 array. A single
producer (the engine's feeder thread) and a single consumer (the output device
callback) are supported. Reads and writes are guarded by a plain
:class:`threading.Lock` held only for the duration of two ``memcpy``-style slice
assignments, which is short enough for the block sizes used here; a future
C++/JUCE port would swap this for a genuinely lock-free SPSC queue.
"""

from __future__ import annotations

import threading

import numpy as np

from .types import SAMPLE_DTYPE


class RingBuffer:
    """Single-producer / single-consumer circular frame buffer."""

    __slots__ = ("_buffer", "_capacity", "_channels", "_lock", "_read", "_size", "_write")

    def __init__(self, capacity: int, channels: int) -> None:
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity}")
        if channels <= 0:
            raise ValueError(f"channels must be positive, got {channels}")
        self._capacity = int(capacity)
        self._channels = int(channels)
        self._buffer = np.zeros((self._capacity, self._channels), dtype=SAMPLE_DTYPE)
        self._read = 0
        self._write = 0
        self._size = 0
        self._lock = threading.Lock()

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def channels(self) -> int:
        return self._channels

    def __len__(self) -> int:
        with self._lock:
            return self._size

    @property
    def available_read(self) -> int:
        """Frames currently queued for the consumer."""
        with self._lock:
            return self._size

    @property
    def available_write(self) -> int:
        """Free frames the producer may still push."""
        with self._lock:
            return self._capacity - self._size

    def clear(self) -> None:
        """Drop all queued frames (used on seek and stop)."""
        with self._lock:
            self._read = 0
            self._write = 0
            self._size = 0

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

        with self._lock:
            n = min(int(block.shape[0]), self._capacity - self._size)
            if n <= 0:
                return 0
            first = min(n, self._capacity - self._write)
            self._buffer[self._write : self._write + first] = block[:first]
            remainder = n - first
            if remainder:
                self._buffer[:remainder] = block[first:n]
            self._write = (self._write + n) % self._capacity
            self._size += n
            return n

    def read(self, n_frames: int, *, pad: bool = False) -> np.ndarray:
        """Pop up to ``n_frames`` frames.

        With ``pad=True`` the result is always exactly ``n_frames`` long,
        zero-filled on underrun -- what a device callback needs to keep the
        stream glitch-free.
        """
        if n_frames < 0:
            raise ValueError(f"n_frames must be non-negative, got {n_frames}")

        with self._lock:
            n = min(n_frames, self._size)
            out = np.zeros((n_frames if pad else n, self._channels), dtype=SAMPLE_DTYPE)
            if n:
                first = min(n, self._capacity - self._read)
                out[:first] = self._buffer[self._read : self._read + first]
                remainder = n - first
                if remainder:
                    out[first:n] = self._buffer[:remainder]
                self._read = (self._read + n) % self._capacity
                self._size -= n
            return out

    def peek(self, n_frames: int) -> np.ndarray:
        """Return queued frames without consuming them (metering / debugging)."""
        with self._lock:
            n = min(n_frames, self._size)
            out = np.empty((n, self._channels), dtype=SAMPLE_DTYPE)
            if n:
                first = min(n, self._capacity - self._read)
                out[:first] = self._buffer[self._read : self._read + first]
                if n - first:
                    out[first:n] = self._buffer[: n - first]
            return out
