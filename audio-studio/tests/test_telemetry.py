"""Triple-buffered render-to-UI level telemetry."""

from __future__ import annotations

import threading

import numpy as np
import pytest

from audio_studio.core.telemetry import EngineTelemetry, LevelSnapshot


def test_initial_snapshot_is_empty_and_preallocated() -> None:
    telemetry = EngineTelemetry(2, block_size=4)

    snapshot = telemetry.read_levels()

    assert isinstance(snapshot, LevelSnapshot)
    assert snapshot.is_empty
    assert snapshot.peak.shape == (2,)
    assert snapshot.rms.shape == (2,)
    assert snapshot.peak.dtype == np.float64
    assert snapshot.rms.dtype == np.float64


def test_publish_block_reports_per_channel_peak_and_rms() -> None:
    telemetry = EngineTelemetry(2, block_size=4)
    block = np.array(
        [
            [1.0, 0.25],
            [-0.5, -0.25],
            [0.0, 0.25],
            [0.5, -0.25],
        ],
        dtype=np.float32,
    )

    telemetry.publish_block(block)
    snapshot = telemetry.read_levels()

    assert not snapshot.is_empty
    assert snapshot.peak == pytest.approx((1.0, 0.25))
    assert snapshot.rms == pytest.approx((np.sqrt(0.375), 0.25))


def test_publish_and_read_reuse_exactly_three_snapshots() -> None:
    telemetry = EngineTelemetry(1, block_size=8)
    block = np.empty((8, 1), dtype=np.float32)
    slot_ids: set[int] = set()
    array_ids = {
        id(array)
        for slot in telemetry._slots  # noqa: SLF001 - verifies the allocation contract
        for array in (slot.peak, slot.rms)
    }

    for value in np.linspace(0.1, 0.9, 12):
        block.fill(value)
        telemetry.publish_block(block)
        slot_ids.add(id(telemetry.read_levels()))

    assert len(slot_ids) == 3
    assert {
        id(array)
        for slot in telemetry._slots  # noqa: SLF001 - verifies arrays were not replaced
        for array in (slot.peak, slot.rms)
    } == array_ids


def test_reader_slot_is_not_overwritten_until_the_next_read() -> None:
    telemetry = EngineTelemetry(1, block_size=4)
    block = np.full((4, 1), 0.25, dtype=np.float32)
    telemetry.publish_block(block)
    held = telemetry.read_levels()

    for value in (0.5, 0.6, 0.7, 0.8):
        block.fill(value)
        telemetry.publish_block(block)

    assert held.peak[0] == pytest.approx(0.25)
    assert held.rms[0] == pytest.approx(0.25)
    latest = telemetry.read_levels()
    assert latest.peak[0] == pytest.approx(0.8)


def test_read_without_a_publish_returns_the_same_object() -> None:
    telemetry = EngineTelemetry(2)

    first = telemetry.read_levels()

    assert telemetry.read_levels() is first
    assert telemetry.read() is first


def test_clear_publishes_an_empty_reused_slot() -> None:
    telemetry = EngineTelemetry(2)
    telemetry.publish((0.8, 0.4), (0.5, 0.25))
    assert not telemetry.read_levels().is_empty

    telemetry.clear()
    cleared = telemetry.read_levels()

    assert cleared.is_empty
    assert np.array_equal(cleared.peak, np.zeros(2))
    assert np.array_equal(cleared.rms, np.zeros(2))


def test_concurrent_reader_never_observes_a_torn_snapshot() -> None:
    telemetry = EngineTelemetry(2)
    peak = np.zeros(2, dtype=np.float64)
    rms = np.zeros(2, dtype=np.float64)
    started = threading.Event()
    finished = threading.Event()

    def produce() -> None:
        started.set()
        for value in range(1, 20_000):
            peak.fill(value)
            rms.fill(value * 0.5)
            telemetry.publish(peak, rms)
        finished.set()

    writer = threading.Thread(target=produce)
    writer.start()
    started.wait(timeout=1.0)
    while not finished.is_set():
        snapshot = telemetry.read_levels()
        if not snapshot.is_empty:
            assert snapshot.peak[0] == snapshot.peak[1]
            assert snapshot.rms[0] == snapshot.rms[1]
            assert snapshot.rms[0] == snapshot.peak[0] * 0.5
    writer.join(timeout=1.0)
    assert not writer.is_alive()


def test_reconfigure_changes_channel_count_before_rendering() -> None:
    telemetry = EngineTelemetry(1, block_size=64)

    telemetry.configure(4, block_size=128)

    snapshot = telemetry.read_levels()
    assert telemetry.channels == 4
    assert telemetry.block_size == 128
    assert snapshot.is_empty
    assert snapshot.peak.shape == (4,)


def test_publish_rejects_a_block_larger_than_its_workspace() -> None:
    telemetry = EngineTelemetry(2, block_size=4)

    with pytest.raises(ValueError, match="workspace"):
        telemetry.publish_block(np.zeros((5, 2), dtype=np.float32))


def test_capture_block_alone_publishes_nothing() -> None:
    telemetry = EngineTelemetry(2, block_size=4)

    telemetry.capture_block(np.full((4, 2), 0.5, dtype=np.float32))

    assert telemetry.read_levels().is_empty


def test_publish_pending_measures_the_captured_block() -> None:
    telemetry = EngineTelemetry(2, block_size=4)
    block = np.array(
        [
            [1.0, 0.25],
            [-0.5, -0.25],
            [0.0, 0.25],
            [0.5, -0.25],
        ],
        dtype=np.float32,
    )
    telemetry.capture_block(block)

    assert telemetry.publish_pending() is True
    snapshot = telemetry.read_levels()

    assert not snapshot.is_empty
    assert snapshot.peak == pytest.approx((1.0, 0.25))
    assert snapshot.rms == pytest.approx((np.sqrt(0.375), 0.25))


def test_publish_pending_without_a_fresh_capture_is_a_no_op() -> None:
    telemetry = EngineTelemetry(1, block_size=4)

    assert telemetry.publish_pending() is False

    telemetry.capture_block(np.full((4, 1), 0.5, dtype=np.float32))
    assert telemetry.publish_pending() is True
    assert telemetry.publish_pending() is False  # already drained


def test_clear_drops_a_pending_capture() -> None:
    telemetry = EngineTelemetry(1, block_size=4)
    telemetry.capture_block(np.full((4, 1), 0.5, dtype=np.float32))

    telemetry.clear()

    assert telemetry.publish_pending() is False
    assert telemetry.read_levels().is_empty


def test_capture_block_clamps_an_oversized_block() -> None:
    telemetry = EngineTelemetry(1, block_size=4)
    block = np.full((6, 1), 0.5, dtype=np.float32)
    block[4:] = 1.0  # beyond the workspace: must not reach the meter

    telemetry.capture_block(block)

    assert telemetry.publish_pending() is True
    assert telemetry.read_levels().peak[0] == pytest.approx(0.5)


def test_capture_block_silently_drops_a_channel_mismatch() -> None:
    telemetry = EngineTelemetry(2, block_size=4)

    telemetry.capture_block(np.full((4, 3), 0.5, dtype=np.float32))

    assert telemetry.publish_pending() is False


def test_capture_and_publish_reuse_preallocated_buffers() -> None:
    telemetry = EngineTelemetry(1, block_size=8)
    capture_id = id(telemetry._capture)  # noqa: SLF001 - verifies the allocation contract
    workspace_id = id(telemetry._workspace)  # noqa: SLF001
    block = np.empty((8, 1), dtype=np.float32)

    for value in np.linspace(0.1, 0.9, 9):
        block.fill(value)
        telemetry.capture_block(block)
        assert telemetry.publish_pending() is True

    assert id(telemetry._capture) == capture_id  # noqa: SLF001
    assert id(telemetry._workspace) == workspace_id  # noqa: SLF001
    assert telemetry.read_levels().peak[0] == pytest.approx(0.9)
