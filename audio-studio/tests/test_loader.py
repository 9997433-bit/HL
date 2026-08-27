"""Decoding, encoding and resampling."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from conftest import SAMPLE_RATE, make_tone

from audio_studio.core.loader import (
    AudioLoadError,
    file_dialog_filter,
    load_audio,
    probe,
    read_bext,
    resample,
    save_audio,
    supported_formats,
)
from audio_studio.core.types import AudioBuffer


def test_load_wav_preserves_shape_rate_and_samples(wav_path: Path, tone: AudioBuffer) -> None:
    clip = load_audio(wav_path)

    assert clip.buffer.sample_rate == SAMPLE_RATE
    assert clip.buffer.n_channels == tone.n_channels
    assert clip.buffer.n_frames == tone.n_frames
    assert clip.buffer.data.dtype == np.float32
    assert clip.duration == pytest.approx(tone.duration)
    # 16-bit quantisation is the only loss between write and read.
    assert np.max(np.abs(clip.buffer.data - tone.data)) < 2.0 / 32767.0


def test_load_flac_matches_wav(flac_path: Path, wav_path: Path) -> None:
    flac = load_audio(flac_path)
    wav = load_audio(wav_path)

    assert flac.audio_format.container.upper().startswith("FLAC")
    assert flac.buffer.n_frames == wav.buffer.n_frames
    assert np.allclose(flac.buffer.data, wav.buffer.data, atol=1e-4)


def test_load_mono_reports_single_channel_and_bit_depth(mono_path: Path) -> None:
    clip = load_audio(mono_path)

    assert clip.buffer.n_channels == 1
    assert clip.buffer.data.ndim == 2
    assert clip.audio_format.bit_depth == 24
    assert "Mono" in clip.audio_format.describe()


def test_probe_reads_metadata_without_decoding(wav_path: Path, tone: AudioBuffer) -> None:
    info = probe(wav_path)

    assert info.sample_rate == tone.sample_rate
    assert info.channels == tone.n_channels
    assert info.bit_depth == 16


def test_missing_file_raises_audio_load_error(tmp_path: Path) -> None:
    with pytest.raises(AudioLoadError, match="File not found"):
        load_audio(tmp_path / "does-not-exist.wav")


def test_round_trip_through_save_audio(tmp_path: Path) -> None:
    original = make_tone(330.0, duration=0.25, channels=1)
    target = tmp_path / "nested" / "round-trip.flac"

    save_audio(target, original, subtype="PCM_24")
    reloaded = load_audio(target)

    assert target.exists()
    assert reloaded.buffer.n_frames == original.n_frames
    assert np.allclose(reloaded.buffer.data, original.data, atol=1e-6)


@pytest.mark.parametrize("target_rate", [22050, 48000])
def test_resample_changes_rate_and_preserves_duration(target_rate: int) -> None:
    original = make_tone(1000.0, duration=0.5, channels=2)

    converted = resample(original, target_rate)

    assert converted.sample_rate == target_rate
    assert converted.duration == pytest.approx(original.duration, abs=1e-3)
    assert converted.n_channels == original.n_channels
    # A 1 kHz tone survives both conversions without gross amplitude error.
    assert converted.peak() == pytest.approx(original.peak(), abs=0.05)


def test_load_with_target_sample_rate_resamples(wav_path: Path) -> None:
    clip = load_audio(wav_path, target_sample_rate=24000)

    assert clip.buffer.sample_rate == 24000


def test_format_advertising_is_consistent() -> None:
    formats = supported_formats()

    assert formats[".wav"] and formats[".flac"]
    assert "*.mp3" in file_dialog_filter()


def _record_bwf(target: Path) -> None:
    """Produce a genuine Broadcast Wave file through the product recorder."""
    from audio_studio.core.recorder import NullRecorder

    recorder = NullRecorder(realtime=False, tone_frequency=440.0)
    recorder.open(
        48_000,
        1,
        target_path=target,
        description="bext round trip",
        originator="Audio Studio Tests",
        flush_interval=0,
    )
    recorder.start()
    recorder.pump(4_096)
    recorder.stop()
    recorder.close()


def test_load_captures_the_bext_chunk_of_a_broadcast_wave(tmp_path: Path) -> None:
    source = tmp_path / "take.wav"
    _record_bwf(source)

    clip = load_audio(source)

    assert clip.bext is not None
    assert clip.bext == read_bext(source)
    assert clip.bext[:256].rstrip(b"\0") == b"bext round trip"
    assert clip.bext[256:288].rstrip(b"\0") == b"Audio Studio Tests"


def test_bext_survives_a_generic_load_save_round_trip(tmp_path: Path) -> None:
    """M5: editing a BWF must not silently strip its broadcast extension."""
    source = tmp_path / "take.wav"
    _record_bwf(source)
    original = load_audio(source)

    exported = tmp_path / "edited.wav"
    save_audio(exported, original.buffer, subtype="PCM_24", dither=False, bext=original.bext)
    round_tripped = load_audio(exported)

    assert round_tripped.bext == original.bext, "bext payload must survive byte-for-byte"
    assert round_tripped.buffer.n_frames == original.buffer.n_frames
    assert np.allclose(round_tripped.buffer.data, original.buffer.data, atol=1e-6)


def test_files_without_bext_report_none_and_round_trip_cleanly(
    wav_path: Path, tmp_path: Path
) -> None:
    clip = load_audio(wav_path)
    assert clip.bext is None

    target = tmp_path / "plain.wav"
    save_audio(target, clip.buffer, subtype="PCM_16", bext=clip.bext)
    assert read_bext(target) is None


def test_bext_on_a_non_wav_target_is_refused_not_dropped(tmp_path: Path) -> None:
    tone = make_tone(330.0, duration=0.1, channels=1)

    with pytest.raises(ValueError, match="WAV target"):
        save_audio(tmp_path / "out.flac", tone, bext=b"\0" * 602)


def test_read_bext_rejects_non_riff_files(tmp_path: Path, flac_path: Path) -> None:
    assert read_bext(flac_path) is None
    missing = tmp_path / "missing.wav"
    assert read_bext(missing) is None
