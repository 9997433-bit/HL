"""Real-time discipline: what happens on which thread, and how fast.

The properties asserted here are all about the boundary between the GUI's
timescale and the device's:

* a fader move is spread over a few milliseconds instead of landing as a step,
  because a step in the waveform is a click;
* the playhead the UI draws is interpolated between device callbacks, so a
  30 Hz repaint does not show a 20 ms staircase;
* the effect rack runs on the feeder thread, ahead of the ring buffer, so a
  chain that runs long costs latency rather than a dropout.

The signal under test is DC — a constant 1.0 — because then the rendered value
*is* the gain that was applied to it, and a ramp can be read straight out of
the output block.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator

import numpy as np
import pytest

from audio_studio.core.engine import AudioEngine
from audio_studio.core.output import NullOutput
from audio_studio.core.sample_source import MemorySampleSource
from audio_studio.core.types import AudioBuffer, TransportState
from audio_studio.dsp.effects import Effect, EffectChain, GainEffect
from audio_studio.dsp.preview import EffectPreview

RATE = 48_000
BLOCK = 128
#: Block big enough (85 ms) that a sleep can be timed against it reliably.
SLOW_BLOCK = 4096
HALF_GAIN_DB = -6.0206


def dc_source(seconds: float = 1.0, channels: int = 1) -> MemorySampleSource:
    """A constant 1.0, so rendered amplitude reads back as applied gain."""
    frames = np.ones((int(RATE * seconds), channels), dtype=np.float32)
    return MemorySampleSource(AudioBuffer(frames, RATE))


def dc_engine(
    output: object | None = None, *, block_size: int = BLOCK, **kwargs: object
) -> AudioEngine:
    engine = AudioEngine(
        output if output is not None else NullOutput(realtime=False),
        block_size=block_size,
        ring_blocks=8,
        **kwargs,  # type: ignore[arg-type]
    )
    engine.set_source(dc_source())
    return engine


def wait_for_ring(engine: AudioEngine, frames: int, timeout: float = 2.0) -> None:
    """Block until the feeder has queued ``frames``, so a pull cannot underrun."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ring = engine._ring  # noqa: SLF001 - the test needs to see the buffering
        if ring is not None and ring.available_read >= frames:
            return
        time.sleep(0.001)
    raise AssertionError(f"the feeder never queued {frames} frames")


def pump(engine: AudioEngine, blocks: int = 1, *, size: int = BLOCK) -> np.ndarray:
    """Pull ``blocks`` device blocks and return them as one array."""
    # ``pump`` reaches the NullOutput either directly or through the preview
    # wrapper, which forwards anything it does not implement itself.
    device = engine.output
    rendered = []
    for _ in range(blocks):
        wait_for_ring(engine, size)
        rendered.append(device.pump(size))
    return np.vstack(rendered)


def ramp_frames(engine: AudioEngine) -> int:
    return int(round(engine.volume_ramp_ms * engine.sample_rate / 1000.0))


@pytest.fixture()
def dc() -> Iterator[AudioEngine]:
    engine = dc_engine()
    yield engine
    engine.shutdown()


class TestVolumeSmoothing:
    """A fader move must reach the target without a discontinuity on the way."""

    def test_a_change_is_walked_to_the_target_over_the_ramp(self, dc: AudioEngine) -> None:
        dc.play()
        assert np.allclose(pump(dc), 1.0)

        dc.volume = 0.25
        gains = pump(dc, blocks=6)[:, 0]

        ramp = ramp_frames(dc)
        assert 0.25 < gains[0] < 1.0, "the first sample after the change jumped"
        assert gains[0] > 0.99, "the ramp should start next to where it was"
        assert np.all(np.diff(gains[:ramp]) < 0.0), "the ramp is not monotonic"
        assert gains[ramp - 1] == pytest.approx(0.25, abs=1e-6)
        assert np.allclose(gains[ramp:], 0.25, atol=1e-6)

    def test_the_ramp_is_ten_milliseconds_long(self, dc: AudioEngine) -> None:
        assert dc.volume_ramp_ms == 10.0
        assert ramp_frames(dc) == 480

        dc.play()
        pump(dc)
        dc.volume = 0.0

        gains = pump(dc, blocks=6)[:, 0]
        reached = int(np.argmax(gains <= 0.0))
        assert reached == pytest.approx(ramp_frames(dc), abs=1)

    def test_no_step_between_consecutive_samples_is_audible(self, dc: AudioEngine) -> None:
        """The zipper-noise check: gain must never move faster than the ramp."""
        dc.play()
        pump(dc)
        dc.volume = 0.0
        quiet = pump(dc, blocks=6)[:, 0]
        dc.volume = 1.5
        loud = pump(dc, blocks=6)[:, 0]

        per_sample = 1.5 / ramp_frames(dc)
        assert np.max(np.abs(np.diff(quiet))) <= per_sample + 1e-6
        assert np.max(np.abs(np.diff(loud))) <= per_sample + 1e-6

    def test_muting_fades_out_rather_than_cutting(self, dc: AudioEngine) -> None:
        dc.play()
        pump(dc)

        dc.muted = True
        gains = pump(dc, blocks=6)[:, 0]

        ramp = ramp_frames(dc)
        assert gains[0] > 0.99
        assert np.all(gains[: ramp - 1] > 0.0), "the output was cut before the ramp ended"
        assert np.allclose(gains[ramp:], 0.0)

    def test_unmuting_fades_back_in(self, dc: AudioEngine) -> None:
        dc.play()
        dc.muted = True
        pump(dc, blocks=6)
        assert dc.applied_gain == 0.0

        dc.muted = False
        gains = pump(dc, blocks=6)[:, 0]

        assert gains[0] < 0.01, "unmuting jumped straight back to full level"
        assert np.all(np.diff(gains[: ramp_frames(dc)]) > 0.0)
        assert np.allclose(gains[ramp_frames(dc) :], 1.0, atol=1e-6)

    def test_a_change_mid_ramp_retargets_from_where_it_got_to(self, dc: AudioEngine) -> None:
        """Two slider moves in one gesture must not restart from the old value."""
        dc.play()
        pump(dc)
        dc.volume = 0.5
        pump(dc)  # part-way through the ramp
        midway = dc.applied_gain
        assert 0.5 < midway < 1.0

        dc.volume = 1.0
        gains = pump(dc, blocks=6)[:, 0]

        step = (1.0 - midway) / ramp_frames(dc)
        assert gains[0] == pytest.approx(midway + step, abs=1e-5)
        assert np.allclose(gains[ramp_frames(dc) :], 1.0, atol=1e-6)

    def test_playback_starts_at_the_fader_setting_without_a_ramp(self) -> None:
        """Only audio already in flight needs smoothing; a new pass does not."""
        engine = dc_engine()
        try:
            engine.volume = 0.5
            engine.play()

            assert np.allclose(pump(engine), 0.5, atol=1e-6)
            assert engine.applied_gain == 0.5
        finally:
            engine.shutdown()

    def test_the_ramp_length_is_configurable(self) -> None:
        engine = dc_engine(volume_ramp_ms=1.0)
        try:
            engine.play()
            pump(engine)
            engine.volume = 0.0

            gains = pump(engine, blocks=2)[:, 0]

            assert ramp_frames(engine) == 48
            assert np.allclose(gains[48:], 0.0)
            assert gains[0] > 0.9
        finally:
            engine.shutdown()

    def test_an_unchanged_fader_leaves_the_samples_alone(self, dc: AudioEngine) -> None:
        dc.play()
        assert np.array_equal(pump(dc, blocks=4), np.ones((4 * BLOCK, 1), dtype=np.float32))


class TestPlayheadInterpolation:
    """``position`` steps once per callback; the interpolated one must glide."""

    @pytest.fixture()
    def slow(self) -> Iterator[AudioEngine]:
        engine = dc_engine(block_size=SLOW_BLOCK)
        yield engine
        engine.shutdown()

    def test_a_stopped_transport_reports_its_position_exactly(self, dc: AudioEngine) -> None:
        assert dc.position_interpolated == 0.0

        dc.seek(12_345)

        assert dc.state is TransportState.STOPPED
        assert dc.position_interpolated == 12_345.0
        assert dc.position_seconds_interpolated == pytest.approx(12_345 / RATE)

    def test_it_trails_the_last_delivered_block(self, slow: AudioEngine) -> None:
        slow.play()
        pump(slow, blocks=2, size=SLOW_BLOCK)

        position = slow.position
        estimate = slow.position_interpolated

        assert position == 2 * SLOW_BLOCK
        assert position - SLOW_BLOCK <= estimate <= position
        # Read immediately after the pull, so almost none of the block has
        # been "played" yet — the slack is for a loaded machine, not for drift.
        assert estimate == pytest.approx(position - SLOW_BLOCK, abs=SLOW_BLOCK / 4)

    def test_it_advances_between_device_callbacks(self, slow: AudioEngine) -> None:
        slow.play()
        pump(slow, blocks=2, size=SLOW_BLOCK)

        before = slow.position_interpolated
        time.sleep(SLOW_BLOCK / RATE / 8.0)
        after = slow.position_interpolated

        assert after > before, "the playhead froze between callbacks"
        assert after <= slow.position, "the playhead ran past the audio delivered"

    def test_it_settles_on_the_real_position_instead_of_drifting(
        self, slow: AudioEngine
    ) -> None:
        """A device that stops pulling must not leave the playhead sliding on."""
        slow.play()
        pump(slow, blocks=2, size=SLOW_BLOCK)

        time.sleep(2.0 * SLOW_BLOCK / RATE)

        assert slow.position_interpolated == float(slow.position)

    def test_it_is_fractional_rather_than_frame_quantised(self, slow: AudioEngine) -> None:
        slow.play()
        pump(slow, blocks=2, size=SLOW_BLOCK)
        time.sleep(SLOW_BLOCK / RATE / 8.0)

        estimate = slow.position_interpolated

        assert isinstance(estimate, float)
        assert estimate % 1.0 != 0.0

    def test_frames_rendered_counts_what_the_device_took(self, dc: AudioEngine) -> None:
        dc.play()
        pump(dc, blocks=3)

        assert dc.frames_rendered == 3 * BLOCK
        assert dc.position == 3 * BLOCK

    def test_seeking_resets_the_render_history(self, dc: AudioEngine) -> None:
        dc.play()
        pump(dc, blocks=3)

        dc.seek(20_000)

        assert dc.frames_rendered == 0
        assert dc.position_interpolated == 20_000.0

    def test_pausing_parks_the_playhead_on_a_real_position(self, slow: AudioEngine) -> None:
        slow.play()
        pump(slow, blocks=2, size=SLOW_BLOCK)
        slow.pause()

        assert slow.position_interpolated == float(slow.position)

    def test_seconds_and_frames_agree(self, slow: AudioEngine) -> None:
        slow.play()
        pump(slow, blocks=2, size=SLOW_BLOCK)

        assert slow.position_seconds_interpolated == pytest.approx(
            slow.position_interpolated / RATE, abs=1e-3
        )


class ThreadProbe(Effect):
    """Records which thread the chain was processed on."""

    name = "Thread probe"

    def __init__(self) -> None:
        super().__init__()
        self.threads: set[str] = set()

    def _process_planar(self, audio: np.ndarray, sample_rate: float) -> np.ndarray:
        self.threads.add(threading.current_thread().name)
        return audio


def half_preview(*, realtime: bool = False) -> EffectPreview:
    return EffectPreview(
        NullOutput(realtime=realtime),
        EffectChain([GainEffect(gain_db=HALF_GAIN_DB, ramp_ms=0.0)]),
    )


class TestEffectsRunAheadOfTheDevice:
    """DEV-19: the rack belongs on the feeder, not in the device callback."""

    def test_the_engine_takes_the_rack_off_the_device_thread(self) -> None:
        preview = half_preview()
        engine = dc_engine(preview)
        try:
            engine.play()

            assert preview.runs_on_feeder
            assert engine.stream_processor == preview.process_block
        finally:
            engine.shutdown()

        assert not preview.runs_on_feeder
        assert engine.stream_processor is None

    def test_the_ring_buffer_already_holds_processed_audio(self) -> None:
        """The proof that the callback only copies: the queue is wet."""
        preview = half_preview()
        engine = dc_engine(preview)
        try:
            engine.play()  # primes the ring before the device pulls anything

            queued = engine._ring.peek(BLOCK)  # noqa: SLF001 - the point of the test

            assert np.allclose(queued, 0.5, atol=1e-3)
            assert preview.processed_blocks > 0
        finally:
            engine.shutdown()

    def test_the_chain_never_runs_on_the_device_thread(self) -> None:
        probe = ThreadProbe()
        preview = EffectPreview(NullOutput(realtime=True), EffectChain([probe]))
        engine = AudioEngine(preview, block_size=512, ring_blocks=8)
        engine.set_source(dc_source())
        try:
            engine.play()
            time.sleep(0.25)
            engine.stop()
        finally:
            engine.shutdown()

        assert probe.threads, "the chain never ran"
        assert "NullOutput" not in probe.threads, "the rack ran in the device callback"
        assert "AudioFeeder" in probe.threads
        assert probe.threads <= {"AudioFeeder", threading.current_thread().name}

    def test_the_master_fader_is_applied_after_the_insert(self) -> None:
        preview = half_preview()
        engine = dc_engine(preview)
        try:
            engine.volume = 0.5
            engine.play()

            assert np.allclose(pump(engine), 0.25, atol=1e-3)
        finally:
            engine.shutdown()

    def test_a_backend_driven_by_hand_keeps_the_device_path(self) -> None:
        """Nothing to bind to, so the wrapper processes in its own render()."""
        preview = half_preview()
        preview.open(RATE, 1, lambda n: np.ones((n, 1), dtype=np.float32))
        preview.start()
        try:
            block = preview.pump(64)

            assert not preview.runs_on_feeder
            assert preview.processed_blocks == 1
            assert np.allclose(block, 0.5, atol=1e-3)
        finally:
            preview.close()

    def test_a_raising_effect_on_the_feeder_still_costs_one_block(self) -> None:
        class Boom(Effect):
            name = "Boom"

            def _process_planar(self, audio: np.ndarray, sample_rate: float) -> np.ndarray:
                raise ValueError("bad parameter")

        preview = EffectPreview(NullOutput(realtime=False), EffectChain([Boom()]))
        engine = dc_engine(preview)
        try:
            engine.play()
            rendered = pump(engine, blocks=2)

            assert preview.failed_blocks > 0
            assert isinstance(preview.last_error, ValueError)
            assert np.allclose(rendered, 1.0), "a failing effect must pass the dry block"
        finally:
            engine.shutdown()
