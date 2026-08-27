"""Batch pipeline and CLI: glob discovery, operations, exports and exit codes."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from conftest import make_tone

from audio_studio.batch import cli
from audio_studio.batch.pipeline import (
    ApplyGain,
    BatchJob,
    Fade,
    NormalizeLoudness,
    run_batch,
)
from audio_studio.core.loader import load_audio, save_audio
from audio_studio.core.types import AudioBuffer
from audio_studio.dsp.loudness import integrated_loudness

#: Long enough for BS.1770 gating (>= 400 ms) while keeping the suite fast.
TONE_SECONDS = 2.0


@pytest.fixture()
def wav_dir(tmp_path: Path) -> Path:
    """Two float32 stereo tones at different levels, plus a decoy text file."""
    source = tmp_path / "in"
    source.mkdir()
    for name, frequency, amplitude in (
        ("loud.wav", 440.0, 0.5),
        ("quiet.wav", 330.0, 0.05),
    ):
        tone = make_tone(frequency, duration=TONE_SECONDS, amplitude=amplitude)
        save_audio(source / name, tone, subtype="FLOAT")
    (source / "notes.txt").write_text("not audio")
    return source


# ---------------------------------------------------------------------------
# pipeline
# ---------------------------------------------------------------------------


def test_glob_discovers_only_supported_audio(wav_dir: Path, tmp_path: Path) -> None:
    job = BatchJob(input_glob=str(wav_dir / "*"), output_dir=tmp_path / "out")
    names = [path.name for path in job.resolve_inputs()]
    assert names == ["loud.wav", "quiet.wav"]


def test_normalize_hits_target_lufs(wav_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    job = BatchJob(
        input_glob=str(wav_dir / "*.wav"),
        output_dir=out,
        operations=(NormalizeLoudness(-16.0),),
        subtype="FLOAT",
    )
    report = run_batch(job)
    assert report.all_ok and report.succeeded == 2

    for name in ("loud.wav", "quiet.wav"):
        rendered = load_audio(out / name).buffer
        measured = integrated_loudness(
            rendered.data, rendered.sample_rate, channels_last=True
        )
        assert measured == pytest.approx(-16.0, abs=0.1)


def test_normalize_respects_true_peak_ceiling(wav_dir: Path, tmp_path: Path) -> None:
    # Asking a 0.05-amplitude tone for -3 LUFS needs far more gain than a
    # -20 dBTP ceiling allows, so the ceiling must win.
    job = BatchJob(
        input_glob=str(wav_dir / "quiet.wav"),
        output_dir=tmp_path / "out",
        operations=(NormalizeLoudness(-3.0, max_true_peak_dbtp=-20.0),),
        subtype="FLOAT",
    )
    assert run_batch(job).all_ok
    rendered = load_audio(tmp_path / "out" / "quiet.wav").buffer
    peak_db = 20.0 * np.log10(float(np.max(np.abs(rendered.data))))
    assert peak_db <= -20.0 + 0.1


def test_normalize_passes_silence_through(tmp_path: Path) -> None:
    silent = AudioBuffer.silence(4800, 2, 48_000)
    assert NormalizeLoudness(-16.0).apply(silent) is silent


def test_gain_and_fade(wav_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    job = BatchJob(
        input_glob=str(wav_dir / "loud.wav"),
        output_dir=out,
        operations=(ApplyGain(-6.0), Fade(fade_in_s=0.1, fade_out_s=0.1)),
        subtype="FLOAT",
    )
    assert run_batch(job).all_ok

    rendered = load_audio(out / "loud.wav").buffer
    expected_peak = 0.5 * 10 ** (-6.0 / 20.0)
    assert float(np.max(np.abs(rendered.data))) == pytest.approx(expected_peak, rel=1e-3)
    assert np.allclose(rendered.data[0], 0.0, atol=1e-6)
    assert np.allclose(rendered.data[-1], 0.0, atol=1e-6)


def test_export_format_conversion(wav_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    job = BatchJob(
        input_glob=str(wav_dir / "*.wav"), output_dir=out, export_format="flac"
    )
    assert run_batch(job).all_ok

    original = load_audio(wav_dir / "loud.wav").buffer
    converted = load_audio(out / "loud.flac").buffer
    assert converted.n_frames == original.n_frames
    assert converted.sample_rate == original.sample_rate


def test_unknown_export_format_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsupported export format"):
        BatchJob(input_glob="*.wav", output_dir=tmp_path, export_format="xyz")


def test_refuses_to_overwrite_input(wav_dir: Path) -> None:
    job = BatchJob(input_glob=str(wav_dir / "*.wav"), output_dir=wav_dir)
    report = run_batch(job)
    assert report.failed == 2 and not report.all_ok
    assert all("overwrite" in result.error for result in report.results)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_normalizes_and_logs_progress(
    wav_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "out"
    code = cli.main(
        [
            "--input", str(wav_dir / "*.wav"),
            "--output", str(out),
            "--lufs", "-16",
            "--subtype", "FLOAT",
        ]
    )
    assert code == 0

    captured = capsys.readouterr().out
    assert "[1/2] loud.wav" in captured
    assert "[2/2] quiet.wav" in captured
    assert "2 succeeded, 0 failed" in captured

    rendered = load_audio(out / "quiet.wav").buffer
    measured = integrated_loudness(rendered.data, rendered.sample_rate, channels_last=True)
    assert measured == pytest.approx(-16.0, abs=0.1)


def test_cli_gain_fade_and_format(wav_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    code = cli.main(
        [
            "--input", str(wav_dir / "loud.wav"),
            "--output", str(out),
            "--gain-db", "-6",
            "--fade-in", "0.05",
            "--fade-out", "0.05",
            "--fade-shape", "cosine",
            "--format", "flac",
        ]
    )
    assert code == 0
    assert (out / "loud.flac").exists()
    assert not (out / "loud.wav").exists()


def test_cli_no_match_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = cli.main(
        ["--input", str(tmp_path / "nothing" / "*.wav"), "--output", str(tmp_path)]
    )
    assert code == 2
    assert "no supported audio files matched" in capsys.readouterr().err


def test_cli_bad_format_exits_2(
    wav_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = cli.main(
        [
            "--input", str(wav_dir / "*.wav"),
            "--output", str(tmp_path / "out"),
            "--format", "xyz",
        ]
    )
    assert code == 2
    assert "unsupported export format" in capsys.readouterr().err


def test_cli_failure_exits_1(wav_dir: Path) -> None:
    # Writing into the input directory is refused per file, so the run fails.
    code = cli.main(["--input", str(wav_dir / "*.wav"), "--output", str(wav_dir)])
    assert code == 1
