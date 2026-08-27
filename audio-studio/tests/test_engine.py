"""Transport behaviour: state machine, seek accuracy, rendering and metering."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pytest

from audio_studio.core.engine import AudioEngine
from audio_studio.core.loader import LoadedAudio
from audio_studio.core.output import NullOutput
from audio_studio.core.types import TimeRange, TransportState


def pump(engine: AudioEngine, blocks: int = 1) -> np.ndarray:
    """Pull ``blocks`` device blocks, giving the feeder thread time to keep up."""
    output = engine.output
    assert isinstance(output, NullOutput)
    rendered = []
    for _ in range(blocks):
        for _ in range(50):
            if engine.output.block_size <= _ring_available(engine):
                break
            time.sleep(0.002)
        rendered.append(output.pump())
    return np.vstack(rendered)


def _ring_available(engine: AudioEngine) -> int:
    ring = engine._ring  # noqa: SLF001 - test needs to observe buffering directly
    return ring.available_read if ring is not None else 0


def test_initial_state_is_stopped_and_empty(engine: AudioEngine) -> None:
    assert engine.state is TransportState.STOPPED
    assert not engine.has_clip
    assert engine.position == 0
    assert engine.duration == 0.0
    assert engine.render(128).shape == (128, 1)


def test_load_populates_clip_metadata_and_pyramid(engine: AudioEngine, wav_path: Path) -> None:
    clip = engine.load(wav_path)

    assert engine.has_clip
    assert engine.sample_rate == clip.buffer.sample_rate
    assert engine.n_channels == 2
    assert engine.n_frames == clip.buffer.n_frames
    assert engine.pyramid is not None
    assert engine.pyramid.n_frames == clip.buffer.n_frames
    assert engine.state is TransportState.STOPPED


def test_play_pause_stop_state_transitions(engine: AudioEngine, loaded_clip: LoadedAudio) -> None:
    observed: list[TransportState] = []
    engine.add_state_listener(observed.append)
    engine.set_clip(loaded_clip)

    engine.play()
    assert engine.state is TransportState.PLAYING
    assert engine.is_playing

    engine.pause()
    assert engine.state is TransportState.PAUSED
    assert not engine.output.is_running

    engine.play()
    assert engine.state is TransportState.PLAYING

    engine.stop()
    assert engine.state is TransportState.STOPPED
    assert observed == [
        TransportState.PLAYING,
        TransportState.PAUSED,
        TransportState.PLAYING,
        TransportState.STOPPED,
    ]


def test_toggle_play_pause_alternates(engine: AudioEngine, loaded_clip: LoadedAudio) -> None:
    engine.set_clip(loaded_clip)

    engine.toggle_play_pause()
    assert engine.is_playing
    engine.toggle_play_pause()
    assert engine.state is TransportState.PAUSED


@pytest.mark.parametrize("seconds", [0.0, 0.25, 0.75, 1.25])
def test_seek_is_sample_accurate_while_stopped(
    engine: AudioEngine, loaded_clip: LoadedAudio, seconds: float
) -> None:
    engine.set_clip(loaded_clip)
    expected = int(round(seconds * loaded_clip.buffer.sample_rate))

    returned = engine.seek(expected)

    assert returned == expected
    assert engine.position == expected
    assert engine.position_seconds == pytest.approx(seconds, abs=1e-6)


def test_seek_clamps_to_the_clip_bounds(engine: AudioEngine, loaded_clip: LoadedAudio) -> None:
    engine.set_clip(loaded_clip)

    assert engine.seek(-500) == 0
    assert engine.seek(engine.n_frames + 10_000) == engine.n_frames


def test_seek_seconds_matches_frame_seek(engine: AudioEngine, loaded_clip: LoadedAudio) -> None:
    engine.set_clip(loaded_clip)

    assert engine.seek_seconds(0.5) == int(round(0.5 * engine.sample_rate))


def test_rendered_audio_matches_the_source_from_the_seek_point(
    engine: AudioEngine, loaded_clip: LoadedAudio
) -> None:
    engine.set_clip(loaded_clip)
    start = 10_000
    engine.seek(start)
    engine.play()

    block_size = engine.output.block_size
    rendered = pump(engine, blocks=4)
    expected = loaded_clip.buffer.data[start : start + 4 * block_size]

    assert rendered.shape == expected.shape
    assert np.allclose(rendered, expected, atol=1e-6)


def test_position_tracks_frames_actually_delivered(
    engine: AudioEngine, loaded_clip: LoadedAudio
) -> None:
    engine.set_clip(loaded_clip)
    engine.play()
    block_size = engine.output.block_size

    pump(engine, blocks=6)

    # The feeder runs ahead of the device; the reported playhead must not.
    assert engine.position == pytest.approx(6 * block_size, abs=block_size)
    assert engine.position <= engine.n_frames


def test_seek_during_playback_discards_stale_buffered_audio(
    engine: AudioEngine, loaded_clip: LoadedAudio
) -> None:
    engine.set_clip(loaded_clip)
    engine.play()
    pump(engine, blocks=2)

    target = 30_000
    engine.seek(target)
    rendered = pump(engine, blocks=1)

    expected = loaded_clip.buffer.data[target : target + engine.output.block_size]
    assert np.allclose(rendered, expected, atol=1e-6)


def test_volume_and_mute_scale_the_output(
    engine: AudioEngine, loaded_clip: LoadedAudio
) -> None:
    """Both land on their target; the ramp getting there is test_rt_discipline's."""
    engine.set_clip(loaded_clip)
    engine.play()
    reference = pump(engine, blocks=3)
    # A change is smoothed over a few milliseconds, so compare past the ramp.
    settled = int(engine.volume_ramp_ms * engine.sample_rate / 1000.0) + 1

    engine.seek(0)
    engine.volume = 0.5
    halved = pump(engine, blocks=3)
    assert np.allclose(halved[settled:], reference[settled:] * 0.5, atol=1e-6)

    engine.seek(0)
    engine.muted = True
    assert np.allclose(pump(engine, blocks=3)[settled:], 0.0)


def test_metering_reports_per_channel_peak_and_rms(
    engine: AudioEngine, loaded_clip: LoadedAudio
) -> None:
    engine.set_clip(loaded_clip)
    engine.play()
    pump(engine, blocks=8)

    # The device callback only captures the block; the feeder thread measures
    # and publishes it, so give that thread a tick to run.
    deadline = time.monotonic() + 2.0
    levels = engine.levels
    while levels.is_empty and time.monotonic() < deadline:
        time.sleep(0.002)
        levels = engine.levels

    assert len(levels.peak) == 2
    assert all(0.0 < value <= 1.0 for value in levels.peak)
    assert all(rms <= peak for rms, peak in zip(levels.rms, levels.peak, strict=True))


def test_selection_restricts_the_playback_region(
    engine: AudioEngine, loaded_clip: LoadedAudio
) -> None:
    engine.set_clip(loaded_clip)
    selection = TimeRange(5_000, 20_000)
    engine.set_selection(selection)

    assert engine.playback_region == selection

    engine.play_selection_only = False
    assert engine.playback_region == TimeRange(0, engine.n_frames)


def test_play_from_outside_the_selection_snaps_to_its_start(
    engine: AudioEngine, loaded_clip: LoadedAudio
) -> None:
    engine.set_clip(loaded_clip)
    engine.set_selection(TimeRange(8_000, 12_000))
    engine.seek(0)

    engine.play()
    rendered = pump(engine, blocks=1)

    expected = loaded_clip.buffer.data[8_000 : 8_000 + engine.output.block_size]
    assert np.allclose(rendered, expected, atol=1e-6)


def test_playback_stops_and_notifies_at_the_end_of_the_region(
    realtime_engine: AudioEngine, loaded_clip: LoadedAudio
) -> None:
    engine = realtime_engine
    finished: list[bool] = []
    engine.add_finished_listener(lambda: finished.append(True))
    engine.set_clip(loaded_clip)
    engine.set_selection(TimeRange(0, 4_000))

    engine.play()
    deadline = time.monotonic() + 5.0
    while engine.is_playing and time.monotonic() < deadline:
        time.sleep(0.01)

    assert not engine.is_playing
    assert engine.state is TransportState.STOPPED
    assert finished == [True]


def test_stop_rewinds_to_where_the_pass_started(
    engine: AudioEngine, loaded_clip: LoadedAudio
) -> None:
    engine.set_clip(loaded_clip)
    engine.seek(15_000)
    engine.play()
    pump(engine, blocks=2)

    engine.stop()

    assert engine.position == 15_000


def test_loading_a_new_clip_resets_the_transport(
    engine: AudioEngine, loaded_clip: LoadedAudio, wav_path: Path
) -> None:
    engine.set_clip(loaded_clip)
    engine.seek(9_000)
    engine.play()

    engine.load(wav_path)

    assert engine.state is TransportState.STOPPED
    assert engine.position == 0
    assert engine.selection is None
