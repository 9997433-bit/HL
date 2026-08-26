"""Headless coverage for recording lifecycle, accumulation, and WAV output."""

from __future__ import annotations

import numpy as np
import pytest

from audio_studio.core.engine import AudioEngine
from audio_studio.core.loader import load_audio
from audio_studio.core.output import NullOutput
from audio_studio.core.recorder import (
    NullRecorder,
    RecorderDeviceError,
    create_recorder,
)
from audio_studio.ui.main_window import MainWindow


def test_manual_null_recorder_accumulates_float32_frames() -> None:
    recorder = NullRecorder(realtime=False)
    recorder.open(16000, 2, block_size=32)
    recorder.start()

    first = recorder.pump()
    second = recorder.pump(17)
    captured = recorder.stop()

    assert first.shape == (32, 2)
    assert second.shape == (17, 2)
    assert captured.data.dtype == np.float32
    assert captured.data.shape == (49, 2)
    assert np.count_nonzero(captured.data) == 0
    assert recorder.frame_count == 49
    assert recorder.frames_recorded == 49
    assert recorder.sample_rate == 16000
    assert recorder.duration == pytest.approx(49 / 16000)


def test_synthetic_tone_is_phase_continuous_across_blocks() -> None:
    recorder = NullRecorder(
        realtime=False,
        tone_frequency=1000.0,
        amplitude=0.25,
    )
    recorder.open(8000, 1, block_size=5)
    recorder.start()

    recorder.pump()
    recorder.pump()
    captured = recorder.stop()

    frames = np.arange(10, dtype=np.float64)
    expected = 0.25 * np.sin(2.0 * np.pi * 1000.0 * frames / 8000)
    np.testing.assert_allclose(captured.data[:, 0], expected, atol=1e-6)


def test_stop_flushes_recording_to_wav(tmp_path) -> None:
    target = tmp_path / "capture.wav"
    recorder = NullRecorder(
        realtime=False,
        tone_frequency=440.0,
        amplitude=0.2,
    )
    recorder.open(24000, 2, block_size=128, target_path=target)
    recorder.start()
    recorder.pump()

    captured = recorder.stop()
    loaded = load_audio(target)

    assert target.exists()
    assert loaded.buffer.sample_rate == 24000
    assert loaded.buffer.data.shape == (128, 2)
    np.testing.assert_allclose(loaded.buffer.data, captured.data, atol=1e-6)


def test_start_and_stop_are_idempotent_and_post_stop_pumps_are_ignored() -> None:
    recorder = NullRecorder(realtime=False)
    recorder.open(48000, 1, block_size=16)

    recorder.start()
    recorder.start()
    recorder.pump()
    first = recorder.stop()
    second = recorder.stop()
    recorder.pump()

    assert first.n_frames == second.n_frames == 16
    assert recorder.frame_count == 16
    assert not recorder.is_running


def test_open_resets_previous_recording() -> None:
    recorder = NullRecorder(realtime=False)
    recorder.open(8000, 1, block_size=8)
    recorder.start()
    recorder.pump()
    recorder.stop()

    recorder.open(44100, 2, block_size=4)

    assert recorder.frame_count == 0
    assert recorder.buffer.data.shape == (0, 2)
    assert recorder.sample_rate == 44100


def test_invalid_format_and_start_before_open_are_rejected() -> None:
    recorder = NullRecorder(realtime=False)

    with pytest.raises(RecorderDeviceError, match="before open"):
        recorder.start()
    with pytest.raises(RecorderDeviceError, match="invalid stream format"):
        recorder.open(0, 2)


def test_factory_can_force_the_headless_backend() -> None:
    recorder = create_recorder(prefer_null=True)
    assert isinstance(recorder, NullRecorder)


def test_main_window_toggles_recording_and_opens_the_result(qapp) -> None:
    recorder = NullRecorder(realtime=False, tone_frequency=220.0)
    main = MainWindow(
        AudioEngine(NullOutput(realtime=False)),
        recorder=recorder,
    )
    try:
        main._on_record()  # noqa: SLF001 - exercise the transport slot

        assert recorder.is_running
        assert main.transport_bar.record_button.isChecked()
        assert not main.transport_bar.play_button.isEnabled()
        assert "Recording" in main.status_recording.text()

        recorder.pump(64)
        main._on_record()  # noqa: SLF001

        assert not recorder.is_running
        assert not main.transport_bar.record_button.isChecked()
        assert main.engine.n_frames == 64
        assert main.engine.sample_rate == 48000
        assert main.transport_bar.play_button.isEnabled()
    finally:
        main.close()
