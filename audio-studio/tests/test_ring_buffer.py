"""Ring buffer semantics, including wrap-around and under/overrun handling."""

from __future__ import annotations

import numpy as np
import pytest

from audio_studio.core.ring_buffer import RingBuffer


def ramp(n_frames: int, channels: int = 2, offset: int = 0) -> np.ndarray:
    values = np.arange(offset, offset + n_frames, dtype=np.float32)
    return np.repeat(values[:, np.newaxis], channels, axis=1)


def test_write_then_read_returns_identical_frames() -> None:
    ring = RingBuffer(64, 2)
    block = ramp(16)

    assert ring.write(block) == 16
    assert ring.available_read == 16
    assert ring.available_write == 48
    assert np.array_equal(ring.read(16), block)
    assert ring.available_read == 0


def test_reads_and_writes_wrap_around_the_capacity() -> None:
    ring = RingBuffer(10, 1)
    ring.write(ramp(8, 1))
    ring.read(6)  # read pointer now at 6

    ring.write(ramp(6, 1, offset=100))  # writes 4 at the tail, 2 at the head
    out = ring.read(8)

    assert out.shape == (8, 1)
    assert np.array_equal(out[:, 0], np.array([6, 7, 100, 101, 102, 103, 104, 105], np.float32))


def test_overflow_drops_the_excess_instead_of_blocking() -> None:
    ring = RingBuffer(8, 1)

    written = ring.write(ramp(20, 1))

    assert written == 8
    assert ring.available_write == 0
    assert np.array_equal(ring.read(8)[:, 0], np.arange(8, dtype=np.float32))


def test_underrun_pads_with_silence_when_requested() -> None:
    ring = RingBuffer(16, 2)
    ring.write(np.ones((4, 2), dtype=np.float32))

    padded = ring.read(10, pad=True)

    assert padded.shape == (10, 2)
    assert np.all(padded[:4] == 1.0)
    assert np.all(padded[4:] == 0.0)
    assert ring.read(1).shape == (0, 2)


def test_clear_discards_queued_frames() -> None:
    ring = RingBuffer(16, 2)
    ring.write(np.ones((10, 2), dtype=np.float32))

    ring.clear()

    assert ring.available_read == 0
    assert ring.available_write == 16


def test_peek_does_not_consume() -> None:
    ring = RingBuffer(16, 1)
    ring.write(ramp(5, 1))

    first = ring.peek(5)
    second = ring.peek(5)

    assert np.array_equal(first, second)
    assert ring.available_read == 5


def test_channel_mismatch_is_rejected() -> None:
    ring = RingBuffer(8, 2)

    with pytest.raises(ValueError, match="channel count mismatch"):
        ring.write(np.zeros((4, 3), dtype=np.float32))


def test_mono_input_is_promoted_to_two_dimensions() -> None:
    ring = RingBuffer(8, 1)

    assert ring.write(np.array([0.1, 0.2, 0.3], dtype=np.float32)) == 3
    assert ring.read(3).shape == (3, 1)
