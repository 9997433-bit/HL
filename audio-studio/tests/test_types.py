"""Value-type invariants: buffers, ranges, dB conversion and timecode."""

from __future__ import annotations

import numpy as np
import pytest

from audio_studio.core.types import (
    AudioBuffer,
    AudioFormat,
    TimeRange,
    TransportState,
    amplitude_to_db,
    db_to_amplitude,
    format_timecode,
)


def test_mono_input_is_promoted_and_converted_to_float32() -> None:
    buffer = AudioBuffer(np.array([0.0, 0.5, -0.5], dtype=np.float64), 8000)

    assert buffer.data.shape == (3, 1)
    assert buffer.data.dtype == np.float32
    assert buffer.n_channels == 1
    assert buffer.duration == pytest.approx(3 / 8000)


def test_buffer_rejects_a_non_positive_sample_rate() -> None:
    with pytest.raises(ValueError, match="sample_rate must be positive"):
        AudioBuffer(np.zeros((4, 1), dtype=np.float32), 0)


def test_peak_rms_and_downmix() -> None:
    data = np.array([[1.0, -1.0], [0.5, 0.5]], dtype=np.float32)
    buffer = AudioBuffer(data, 44100)

    assert buffer.peak() == pytest.approx(1.0)
    assert buffer.rms() == pytest.approx(np.sqrt(np.mean(data**2)), abs=1e-6)
    assert np.allclose(buffer.to_mono(), [0.0, 0.5])


def test_slice_is_clamped_to_the_buffer() -> None:
    buffer = AudioBuffer(np.ones((100, 2), dtype=np.float32), 44100)

    assert buffer.slice(TimeRange(90, 500)).n_frames == 10
    assert buffer.slice(TimeRange(200, 300)).n_frames == 0


def test_time_range_validation_and_conversion() -> None:
    rng = TimeRange.from_seconds(1.5, 0.5, 1000)

    assert rng == TimeRange(500, 1500)
    assert rng.length == 1000
    assert rng.to_seconds(1000) == (0.5, 1.5)
    assert rng.clamped(800) == TimeRange(500, 800)
    assert TimeRange(5, 5).is_empty

    with pytest.raises(ValueError, match="end precedes start"):
        TimeRange(10, 5)


def test_transport_state_activity_flag() -> None:
    assert TransportState.PLAYING.is_active
    assert not TransportState.PAUSED.is_active
    assert not TransportState.STOPPED.is_active


@pytest.mark.parametrize(
    ("amplitude", "expected_db"),
    [(1.0, 0.0), (0.5, -6.0206), (0.1, -20.0), (0.0, -120.0)],
)
def test_amplitude_to_db(amplitude: float, expected_db: float) -> None:
    assert amplitude_to_db(amplitude) == pytest.approx(expected_db, abs=1e-3)


def test_db_conversion_round_trips() -> None:
    for db in (-48.0, -12.0, -3.0, 0.0):
        assert amplitude_to_db(db_to_amplitude(db)) == pytest.approx(db, abs=1e-6)


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0.0, "00:00.000"),
        (1.5, "00:01.500"),
        (61.25, "01:01.250"),
        (3661.0, "1:01:01.000"),
        (-2.5, "-00:02.500"),
    ],
)
def test_format_timecode(seconds: float, expected: str) -> None:
    assert format_timecode(seconds) == expected


def test_audio_format_describe_reports_depth_and_layout() -> None:
    described = AudioFormat(48000, 2, "PCM_24", "FLAC").describe()

    assert "48 kHz" in described
    assert "24-bit" in described
    assert "Stereo" in described
