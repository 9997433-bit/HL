"""Ring buffer semantics: wrap-around, under/overrun handling and SPSC concurrency."""

from __future__ import annotations

import threading
import time
import tracemalloc

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


@pytest.mark.parametrize("capacity", [0, -4])
def test_a_degenerate_capacity_is_rejected(capacity: int) -> None:
    with pytest.raises(ValueError, match="capacity must be positive"):
        RingBuffer(capacity, 2)


def test_a_degenerate_channel_count_is_rejected() -> None:
    with pytest.raises(ValueError, match="channels must be positive"):
        RingBuffer(16, 0)


def test_a_negative_read_length_is_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        RingBuffer(16, 1).read(-1)


# ---------------------------------------------------------------------------
# lock-free bookkeeping
# ---------------------------------------------------------------------------


def test_the_frame_counters_are_monotonic_across_wraps() -> None:
    """Indices never wrap, so 'full' and 'empty' can never look alike."""
    ring = RingBuffer(8, 1)

    for cycle in range(10):
        assert ring.write(ramp(8, 1, offset=cycle * 8)) == 8
        assert ring.read(8).shape == (8, 1)

    assert ring.frames_written == 80
    assert ring.frames_read == 80
    assert ring.available_read == 0


def test_overruns_and_underruns_are_counted() -> None:
    ring = RingBuffer(8, 1)

    ring.write(ramp(20, 1))  # 8 accepted, 12 dropped
    ring.read(12, pad=True)  # 8 delivered, 4 zero-filled

    assert ring.overrun_frames == 12
    assert ring.underrun_frames == 4

    ring.reset_xrun_counters()
    assert (ring.overrun_frames, ring.underrun_frames) == (0, 0)


def test_writing_into_a_full_buffer_counts_the_whole_block() -> None:
    ring = RingBuffer(4, 1)
    ring.write(ramp(4, 1))

    assert ring.write(ramp(6, 1)) == 0
    assert ring.overrun_frames == 6


def test_clear_only_moves_the_read_counter_forward() -> None:
    """Clearing must never resurrect frames the consumer has already taken."""
    ring = RingBuffer(16, 1)
    ring.write(ramp(10, 1))
    ring.read(4)
    before = ring.frames_read

    ring.clear()

    assert ring.frames_read >= before
    assert ring.frames_read == ring.frames_written
    assert ring.available_read == 0
    assert ring.available_write == 16


def test_clear_on_an_empty_buffer_is_a_no_op() -> None:
    ring = RingBuffer(16, 2)

    ring.clear()

    assert (ring.frames_read, ring.frames_written) == (0, 0)


# ---------------------------------------------------------------------------
# the real-time read surface
# ---------------------------------------------------------------------------


def test_read_into_fills_the_caller_buffer_and_pads_the_tail() -> None:
    ring = RingBuffer(16, 2)
    ring.write(ramp(6))
    out = np.full((10, 2), -1.0, dtype=np.float32)

    delivered = ring.read_into(out)

    assert delivered == 6
    assert np.array_equal(out[:6], ramp(6))
    assert np.all(out[6:] == 0.0)
    assert ring.underrun_frames == 4


def test_read_into_handles_a_wrapped_region() -> None:
    ring = RingBuffer(10, 1)
    ring.write(ramp(8, 1))
    ring.read(6)
    ring.write(ramp(6, 1, offset=100))
    out = np.empty((8, 1), dtype=np.float32)

    assert ring.read_into(out) == 8
    assert np.array_equal(out[:, 0], np.array([6, 7, 100, 101, 102, 103, 104, 105], np.float32))


def test_read_into_rejects_a_mis_shaped_buffer() -> None:
    ring = RingBuffer(16, 2)

    with pytest.raises(ValueError, match=r"out must be \(frames, 2\)"):
        ring.read_into(np.empty((4, 3), dtype=np.float32))


def test_the_realtime_path_does_not_allocate_per_block() -> None:
    """The whole point of read_into: a device callback that never hits malloc.

    Not literally zero bytes — the monotonic counters are Python ints, so each
    one costs a 32-byte object that immediately replaces its predecessor. What
    must not happen is an allocation that scales with the audio, and 100 kB of
    frames moving through for well under 1 kB of churn says it does not.
    """
    ring = RingBuffer(4_096, 2)
    out = np.empty((256, 2), dtype=np.float32)
    block = ramp(256)
    for _ in range(4):  # warm up numpy's internal caches and this frame's locals
        ring.write(block)
        ring.read_into(out)

    tracemalloc.start()
    try:
        before = tracemalloc.take_snapshot()
        for _ in range(100):
            ring.write(block)
            ring.read_into(out)
        after = tracemalloc.take_snapshot()
    finally:
        tracemalloc.stop()

    moved = 100 * block.nbytes
    grew = sum(
        entry.size_diff
        for entry in after.compare_to(before, "filename")
        if entry.traceback[0].filename.endswith("ring_buffer.py")
    )
    assert grew < 1_024, f"steady-state read/write allocated {grew} bytes for {moved} moved"


def test_drop_fast_forwards_without_copying() -> None:
    ring = RingBuffer(32, 1)
    ring.write(ramp(20, 1))

    assert ring.drop(5) == 5
    assert ring.available_read == 15
    assert np.array_equal(ring.read(3)[:, 0], np.array([5, 6, 7], np.float32))

    assert ring.drop(1_000) == 12  # clamped to what is queued
    assert ring.available_read == 0


def test_drop_rejects_a_negative_count() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        RingBuffer(8, 1).drop(-1)


def test_the_available_methods_mirror_the_properties() -> None:
    ring = RingBuffer(16, 1)
    ring.write(ramp(5, 1))

    assert ring.read_available() == ring.available_read == 5
    assert ring.write_available() == ring.available_write == 11


# ---------------------------------------------------------------------------
# single-producer / single-consumer stress
# ---------------------------------------------------------------------------


def _spsc_transfer(
    ring: RingBuffer, total: int, *, producer_block: int, consumer_block: int
) -> tuple[np.ndarray, list[str]]:
    """Push a ramp through the ring from one thread and drain it from another.

    Returns everything the consumer saw, so the caller can assert that the
    stream came out in order with nothing duplicated, reordered or invented.
    """
    errors: list[str] = []
    received: list[np.ndarray] = []
    done = threading.Event()

    def produce() -> None:
        try:
            written = 0
            while written < total:
                # Offer only what the buffer says it can take, exactly as the
                # engine's feeder does. If ``available_write`` ever over-reports,
                # the write below silently truncates and the stream comes out short.
                room = min(ring.available_write, producer_block, total - written)
                if room <= 0:
                    time.sleep(0)  # yield to the consumer instead of spinning hot
                    continue
                block = ramp(room, ring.channels, offset=written)
                written += ring.write(block)
        except Exception as exc:  # noqa: BLE001 - surfaced as a test failure
            errors.append(f"producer: {exc!r}")
        finally:
            done.set()

    def consume() -> None:
        try:
            drained = 0
            while drained < total:
                block = ring.read(consumer_block)
                if block.shape[0] == 0:
                    if done.is_set() and ring.available_read == 0:
                        break
                    time.sleep(0)
                    continue
                received.append(block)
                drained += block.shape[0]
        except Exception as exc:  # noqa: BLE001
            errors.append(f"consumer: {exc!r}")

    producer = threading.Thread(target=produce, name="producer")
    consumer = threading.Thread(target=consume, name="consumer")
    producer.start()
    consumer.start()
    producer.join(timeout=60.0)
    consumer.join(timeout=60.0)
    if producer.is_alive() or consumer.is_alive():
        errors.append("a worker did not finish within the timeout")

    stream = np.vstack(received) if received else np.zeros((0, ring.channels), np.float32)
    return stream, errors


@pytest.mark.parametrize(
    ("capacity", "producer_block", "consumer_block"),
    [
        (1024, 256, 256),  # matched block sizes
        (1024, 333, 128),  # producer ahead, unaligned
        (1024, 64, 512),  # consumer ahead, unaligned
        (257, 64, 61),  # capacity coprime with both block sizes
        (4, 1, 1),  # pathologically small buffer
    ],
)
def test_a_producer_and_a_consumer_transfer_the_stream_intact(
    capacity: int, producer_block: int, consumer_block: int
) -> None:
    """No lock is held anywhere here: order and content still have to be exact."""
    total = 60_000
    ring = RingBuffer(capacity, 2)

    stream, errors = _spsc_transfer(
        ring, total, producer_block=producer_block, consumer_block=consumer_block
    )

    assert not errors
    assert stream.shape == (total, 2)
    assert np.array_equal(stream, ramp(total, 2))
    assert ring.overrun_frames == 0  # a producer that respects available_write never drops
    assert ring.available_read == 0
    assert ring.frames_written == ring.frames_read == total


def test_a_slow_consumer_makes_the_producer_drop_rather_than_block() -> None:
    """Overrun policy: a stalled device must never wedge the feeder thread."""
    ring = RingBuffer(512, 1)
    stop = threading.Event()
    attempted = 0

    def produce() -> None:
        nonlocal attempted
        while not stop.is_set():
            ring.write(ramp(256, 1))
            attempted += 256

    producer = threading.Thread(target=produce, daemon=True)
    producer.start()
    time.sleep(0.15)
    stop.set()
    producer.join(timeout=5.0)

    assert not producer.is_alive()
    assert attempted > 0
    assert ring.overrun_frames > 0  # frames were dropped, not queued forever


def test_a_slow_producer_makes_the_consumer_underrun_rather_than_stall() -> None:
    """Underrun policy: the device callback always gets a full block, on time."""
    ring = RingBuffer(512, 2)
    deadline = time.perf_counter() + 0.2
    blocks = 0

    def produce() -> None:
        while time.perf_counter() < deadline:
            ring.write(ramp(16, 2))
            time.sleep(0.005)

    producer = threading.Thread(target=produce, daemon=True)
    producer.start()
    while time.perf_counter() < deadline:
        assert ring.read(256, pad=True).shape == (256, 2)
        blocks += 1
    producer.join(timeout=5.0)

    assert blocks > 0
    assert ring.underrun_frames > 0


def test_clearing_from_a_third_thread_never_replays_delivered_frames() -> None:
    """A seek races the device callback; the read counter must stay monotonic."""
    ring = RingBuffer(2_048, 1)
    stop = threading.Event()
    violations: list[str] = []

    def produce() -> None:
        while not stop.is_set():
            ring.write(ramp(128, 1))

    def observe() -> None:
        previous = 0
        while not stop.is_set():
            current = ring.frames_read
            if current < previous:
                violations.append(f"read counter went backwards: {previous} -> {current}")
            previous = current

    workers = [threading.Thread(target=fn, daemon=True) for fn in (produce, observe)]
    for worker in workers:
        worker.start()
    try:
        for _ in range(2_000):
            ring.read(64)
            ring.clear()
    finally:
        stop.set()
        for worker in workers:
            worker.join(timeout=5.0)

    assert not violations
    assert ring.frames_read <= ring.frames_written
