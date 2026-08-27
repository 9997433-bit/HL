"""Zero-allocation discipline of the ``render_into`` device path.

``AudioEngine.render_into`` is pulled from the real-time device thread, so in
steady state it must not allocate: no fresh sample arrays, no NumPy reduction
temporaries, no per-callback growth. These tests pin that contract with
tracemalloc (the pattern established in ``test_sample_source``) and verify the
meter split that makes it possible — the callback only captures its block into
preallocated telemetry storage, and the feeder thread measures and publishes.
"""

from __future__ import annotations

import inspect
import time
import tracemalloc

import numpy as np
import pytest

from audio_studio.core.engine import AudioEngine
from audio_studio.core.output import NullOutput
from audio_studio.core.sample_source import MemorySampleSource
from audio_studio.core.types import AudioBuffer

BLOCK = 256
SAMPLE_RATE = 48_000

#: Files whose allocations count against the callback. The waits and asserts
#: in this test file allocate freely, but they are attributed elsewhere.
RENDER_PATH_FILES = ("engine.py", "ring_buffer.py", "telemetry.py")

#: Live-memory growth allowed across a measured window. Steady state keeps a
#: handful of rebound counters alive (ints and floats, tens of bytes); a single
#: per-callback block allocation would exceed this bound many times over.
ALLOWED_GROWTH_BYTES = 4_096


def _constant_engine(value: float = 0.5, seconds: float = 5.0) -> AudioEngine:
    """An engine playing a constant-amplitude stereo source at 48 kHz."""
    frames = int(SAMPLE_RATE * seconds)
    buffer = AudioBuffer(np.full((frames, 2), value, dtype=np.float32), SAMPLE_RATE)
    engine = AudioEngine(NullOutput(realtime=False), block_size=BLOCK, ring_blocks=8)
    engine.set_source(MemorySampleSource(buffer))
    return engine


def _wait_for_block(engine: AudioEngine, timeout: float = 2.0) -> None:
    """Give the feeder thread its chance to keep the ring fed."""
    deadline = time.monotonic() + timeout
    while engine.buffered_frames < BLOCK:
        if time.monotonic() > deadline:
            raise AssertionError("feeder thread did not keep the ring buffer fed")
        time.sleep(0.0005)


def _render_path_growth(
    before: tracemalloc.Snapshot, after: tracemalloc.Snapshot
) -> int:
    return sum(
        entry.size_diff
        for entry in after.compare_to(before, "filename")
        if entry.traceback[0].filename.endswith(RENDER_PATH_FILES)
    )


def test_render_into_steady_state_allocates_nothing() -> None:
    engine = _constant_engine()
    out = np.empty((BLOCK, 2), dtype=np.float32)
    try:
        engine.play()
        for _ in range(8):  # warm up: gain snap, interpolator, meter capture
            _wait_for_block(engine)
            engine.render_into(out)

        tracemalloc.start()
        try:
            before = tracemalloc.take_snapshot()
            for _ in range(200):
                _wait_for_block(engine)
                assert engine.render_into(out) == BLOCK
            after = tracemalloc.take_snapshot()
        finally:
            tracemalloc.stop()
    finally:
        engine.shutdown()

    grew = _render_path_growth(before, after)
    assert grew < ALLOWED_GROWTH_BYTES, (
        f"render_into path allocated {grew} bytes over 200 callbacks"
    )


def test_render_into_does_not_allocate_through_volume_and_mute_ramps() -> None:
    """Gain changes take the ramp branch; it must reuse its preallocated curve."""
    engine = _constant_engine()
    out = np.empty((BLOCK, 2), dtype=np.float32)
    try:
        engine.play()
        for _ in range(4):
            _wait_for_block(engine)
            engine.render_into(out)

        tracemalloc.start()
        try:
            before = tracemalloc.take_snapshot()
            for volume, muted in ((0.25, False), (1.0, True), (0.5, False)):
                engine.volume = volume
                engine.muted = muted
                for _ in range(8):  # 8 blocks ≈ 42 ms: well past the 10 ms ramp
                    _wait_for_block(engine)
                    engine.render_into(out)
            after = tracemalloc.take_snapshot()
        finally:
            tracemalloc.stop()
    finally:
        engine.shutdown()

    grew = _render_path_growth(before, after)
    assert grew < ALLOWED_GROWTH_BYTES, (
        f"gain-ramp render path allocated {grew} bytes over 24 callbacks"
    )


def test_render_into_zero_fill_path_allocates_nothing() -> None:
    """A stopped transport zero-fills the block without touching the allocator."""
    engine = AudioEngine(NullOutput(realtime=False), block_size=BLOCK)
    out = np.empty((BLOCK, 1), dtype=np.float32)
    try:
        assert engine.render_into(out) == 0  # warm up the code path

        tracemalloc.start()
        try:
            before = tracemalloc.take_snapshot()
            for _ in range(100):
                assert engine.render_into(out) == 0
            after = tracemalloc.take_snapshot()
        finally:
            tracemalloc.stop()
    finally:
        engine.shutdown()

    assert np.all(out == 0.0)
    grew = _render_path_growth(before, after)
    assert grew < ALLOWED_GROWTH_BYTES, (
        f"zero-fill render path allocated {grew} bytes over 100 callbacks"
    )


def test_render_callback_source_contains_no_meter_reductions() -> None:
    """The SOTA C3 discipline: no meter math inside the device callback."""
    source = inspect.getsource(AudioEngine.render_into)
    assert "_update_levels" not in source
    assert "publish_block" not in source
    assert "capture_block" in source  # the meter still gets its data


def test_meter_levels_flow_from_device_capture_to_feeder_publish() -> None:
    engine = _constant_engine(value=0.5)
    out = np.empty((BLOCK, 2), dtype=np.float32)
    try:
        engine.play()
        _wait_for_block(engine)
        assert engine.render_into(out) == BLOCK

        deadline = time.monotonic() + 2.0
        levels = engine.levels
        while levels.is_empty and time.monotonic() < deadline:
            time.sleep(0.002)
            levels = engine.levels

        assert not levels.is_empty
        # A constant 0.5 signal at unity gain: peak and RMS are both exactly it.
        assert levels.peak == pytest.approx((0.5, 0.5))
        assert levels.rms == pytest.approx((0.5, 0.5))
    finally:
        engine.shutdown()
