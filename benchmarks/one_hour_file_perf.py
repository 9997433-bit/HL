#!/usr/bin/env python3
"""Direct, headless performance evidence for SOTA checklist item B2.

B2 requires a one-hour, 48 kHz stereo file to:

* open with a rendered waveform in under three seconds;
* produce its first rendered spectrogram viewport in under two seconds; and
* complete offline EQ plus peak normalisation in under thirty seconds.

The default run creates a physically allocated PCM-16 WAV containing a
deterministic dual tone for the full hour.  Waveform and spectrogram timings
include real libsndfile reads and headless Qt paints.  The offline timing reads
every frame through ``StreamingSampleSource``, runs the production three-band
EQ block path, and runs the production ``NormalizeEffect`` over the complete
EQ render.

The fixture and its peak sidecar are setup inputs, so their creation is
reported but excluded from the open latency.  A run is marked formal only when
``--formal`` is explicitly requested, the fixture is at least one hour of
48 kHz stereo audio, its payload is physically allocated, and the measured
threshold passes.  Shortened runs are useful smoke proxies but cannot close B2.

Examples::

    python3 benchmarks/one_hour_file_perf.py --formal
    python3 benchmarks/one_hour_file_perf.py --duration-seconds 10
    python3 benchmarks/one_hour_file_perf.py --output /tmp/file-perf.json
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import sys
import tempfile
import time
import wave
from pathlib import Path
from typing import Any

import numpy as np

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
AUDIO_STUDIO_ROOT = REPOSITORY_ROOT / "audio-studio"
if str(AUDIO_STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(AUDIO_STUDIO_ROOT))

from audio_studio.core import peaks_cache
from audio_studio.core.peaks import BASE_DECIMATION, PeakPyramid, PyramidLevel
from audio_studio.core.sample_source import StreamingSampleSource
from audio_studio.dsp.effects import NormalizeEffect, NormalizeMode, ThreeBandEQ

SAMPLE_RATE = 48_000
CHANNELS = 2
FORMAL_DURATION_SECONDS = 3_600.0
FIXTURE_CHUNK_FRAMES = 65_536
DEFAULT_BLOCK_FRAMES = 1 << 20
DEFAULT_SPECTROGRAM_SECONDS = 30.0

WAVEFORM_OPEN_SECONDS_MAX = 3.0
SPECTROGRAM_FIRST_FRAME_SECONDS_MAX = 2.0
OFFLINE_EQ_NORMALIZE_SECONDS_MAX = 30.0

DEFAULT_REPORT_PATH = (
    REPOSITORY_ROOT / ".agent_workspace/round3/file-performance-report.json"
)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="One-hour file open, spectrogram, and offline-render benchmark.",
    )
    parser.add_argument(
        "--duration-seconds",
        type=float,
        default=FORMAL_DURATION_SECONDS,
        help="fixture duration (default: 3600; shorter runs are non-formal proxies)",
    )
    parser.add_argument(
        "--block-frames",
        type=int,
        default=DEFAULT_BLOCK_FRAMES,
        help="streaming EQ render block size",
    )
    parser.add_argument(
        "--spectrogram-seconds",
        type=float,
        default=DEFAULT_SPECTROGRAM_SECONDS,
        help="first visible viewport read from the one-hour source",
    )
    parser.add_argument(
        "--formal",
        action="store_true",
        help="request formal evidence; rejected unless the full allocated fixture is used",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=None,
        help="fixture/render scratch directory (default: temporary directory)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help=f"JSON report path (default: {DEFAULT_REPORT_PATH})",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress progress lines on stderr",
    )
    return parser.parse_args(argv)


def _progress(quiet: bool, message: str) -> None:
    if not quiet:
        print(f"[one-hour-file] {message}", file=sys.stderr, flush=True)


def _fixture_chunk() -> tuple[np.ndarray, bytes]:
    """Return one non-sparse periodic PCM chunk as float32 and PCM-16 bytes."""
    sample = np.arange(FIXTURE_CHUNK_FRAMES, dtype=np.float64)
    left = (
        0.20 * np.sin(2.0 * np.pi * 997.0 * sample / SAMPLE_RATE)
        + 0.04 * np.sin(2.0 * np.pi * 83.0 * sample / SAMPLE_RATE)
    )
    right = (
        0.18 * np.sin(2.0 * np.pi * 1_109.0 * sample / SAMPLE_RATE)
        + 0.05 * np.sin(2.0 * np.pi * 127.0 * sample / SAMPLE_RATE)
    )
    floating = np.ascontiguousarray(np.column_stack((left, right)), dtype=np.float32)
    pcm = np.clip(np.rint(floating * 32_767.0), -32_768, 32_767).astype("<i2")
    # libsndfile's PCM-16 decode scale is 1/32768, so derive the sidecar from
    # the exact samples the application will see rather than the pre-quantised tone.
    decoded = np.ascontiguousarray(pcm.astype(np.float32) / 32_768.0)
    return decoded, pcm.tobytes()


def _repeat_level0(samples: np.ndarray, n_frames: int) -> PeakPyramid:
    """Build the exact level-0 peak cache for a repeated aligned chunk."""
    repeats, tail = divmod(n_frames, FIXTURE_CHUNK_FRAMES)
    template = PeakPyramid(samples, base_decimation=BASE_DECIMATION).levels[0]
    tail_level = (
        PeakPyramid(samples[:tail], base_decimation=BASE_DECIMATION).levels[0]
        if tail
        else None
    )

    def repeated_2d(array: np.ndarray, tail_array: np.ndarray | None) -> np.ndarray:
        pieces: list[np.ndarray] = []
        if repeats:
            pieces.append(np.tile(array, (repeats, 1)))
        if tail_array is not None:
            pieces.append(tail_array)
        return np.ascontiguousarray(np.concatenate(pieces, axis=0))

    def repeated_1d(array: np.ndarray, tail_array: np.ndarray | None) -> np.ndarray:
        pieces: list[np.ndarray] = []
        if repeats:
            pieces.append(np.tile(array, repeats))
        if tail_array is not None:
            pieces.append(tail_array)
        return np.ascontiguousarray(np.concatenate(pieces))

    level = PyramidLevel(
        decimation=BASE_DECIMATION,
        minimum=repeated_2d(
            template.minimum,
            None if tail_level is None else tail_level.minimum,
        ),
        maximum=repeated_2d(
            template.maximum,
            None if tail_level is None else tail_level.maximum,
        ),
        sumsq=repeated_2d(
            template.sumsq,
            None if tail_level is None else tail_level.sumsq,
        ),
        counts=repeated_1d(
            template.counts,
            None if tail_level is None else tail_level.counts,
        ),
    )
    return PeakPyramid.from_levels(
        [level],
        n_frames=n_frames,
        n_channels=CHANNELS,
    )


def _write_fixture(path: Path, n_frames: int) -> dict[str, Any]:
    """Write a physically allocated WAV and its exact waveform sidecar."""
    samples, chunk_bytes = _fixture_chunk()
    repeats, tail = divmod(n_frames, FIXTURE_CHUNK_FRAMES)
    started = time.perf_counter()
    with wave.open(str(path), "wb") as output:
        output.setnchannels(CHANNELS)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        remaining = repeats
        while remaining:
            copies = min(remaining, 32)
            output.writeframesraw(chunk_bytes * copies)
            remaining -= copies
        if tail:
            output.writeframesraw(chunk_bytes[: tail * CHANNELS * 2])

    pyramid = _repeat_level0(samples, n_frames)
    sidecar = peaks_cache.write(path, pyramid)
    if sidecar is None:
        raise RuntimeError("failed to write waveform peak sidecar")
    setup_seconds = time.perf_counter() - started

    stat = path.stat()
    # st_blocks is unavailable on Windows.  Zero is recorded there, so a run
    # may be direct but cannot claim to have proved physical allocation.
    allocated_bytes = max(0, int(getattr(stat, "st_blocks", 0)) * 512)
    return {
        "path": str(path),
        "duration_seconds": n_frames / SAMPLE_RATE,
        "n_frames": n_frames,
        "sample_rate": SAMPLE_RATE,
        "channels": CHANNELS,
        "subtype": "PCM_16",
        "content": "deterministic allocated dual-tone PCM",
        "file_size_bytes": stat.st_size,
        "allocated_bytes": allocated_bytes,
        "allocated_ratio": round(allocated_bytes / stat.st_size, 6),
        "peak_sidecar_bytes": sidecar.stat().st_size,
        "setup_seconds_excluded_from_slos": round(setup_seconds, 6),
    }


def _qt_application():
    """Return a QApplication suitable for Xvfb or offscreen headless rendering."""
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication(["one-hour-file-perf"])


def _measure_waveform_open(
    fixture: Path,
    *,
    expected_frames: int,
    application: Any,
) -> tuple[dict[str, Any], bool]:
    """Open the stream, restore peaks, and force a real headless waveform paint."""
    from audio_studio.ui.waveform_view import WaveformView

    source: StreamingSampleSource | None = None
    view: Any = None
    started = time.perf_counter()
    try:
        source = StreamingSampleSource(fixture)
        pyramid = peaks_cache.read(fixture)
        if pyramid is None:
            raise RuntimeError("waveform sidecar did not load")
        view = WaveformView()
        view.resize(1_280, 480)
        view.set_clip(
            pyramid,
            sample_rate=source.sample_rate,
            sample_source=source,
            n_frames=source.n_frames,
        )
        application.processEvents()
        pixmap = view.grab()
        elapsed = time.perf_counter() - started
        envelope = pyramid.envelope(0, source.n_frames, 1_280)
        waveform_peak = float(np.max(np.abs(envelope.maximum)))
        rendered = not pixmap.isNull() and pixmap.width() >= 1_280 and pixmap.height() >= 480
        complete = (
            source.n_frames == expected_frames
            and pyramid.n_frames == expected_frames
            and waveform_peak > 0.0
            and rendered
        )
        measured = {
            "elapsed_seconds": round(elapsed, 6),
            "source_frames": source.n_frames,
            "cached_waveform_frames": pyramid.n_frames,
            "peak_cache_levels": pyramid.n_levels,
            "render_width_px": pixmap.width(),
            "render_height_px": pixmap.height(),
            "waveform_peak": round(waveform_peak, 8),
            "headless_paint_completed": rendered,
        }
        return measured, complete
    finally:
        if view is not None:
            view.close()
            view.deleteLater()
        if source is not None:
            source.close()


def _measure_spectrogram_first_frame(
    fixture: Path,
    *,
    expected_frames: int,
    viewport_seconds: float,
    application: Any,
) -> tuple[dict[str, Any], bool]:
    """Read, analyze, and paint the first visible viewport headlessly."""
    from audio_studio.ui.spectrum_panel import SpectrumPanel

    source: StreamingSampleSource | None = None
    panel: Any = None
    requested = min(expected_frames, max(2_048, math.ceil(viewport_seconds * SAMPLE_RATE)))
    started = time.perf_counter()
    try:
        source = StreamingSampleSource(fixture)
        audio = source.read(0, requested)
        panel = SpectrumPanel()
        panel.resize(1_280, 720)
        panel.analyze(audio, SAMPLE_RATE, channels_last=True)
        application.processEvents()
        pixmap = panel.grab()
        elapsed = time.perf_counter() - started
        rendered = not pixmap.isNull() and panel.has_data
        complete = (
            source.n_frames == expected_frames
            and audio.shape == (requested, CHANNELS)
            and rendered
        )
        measured = {
            "elapsed_seconds": round(elapsed, 6),
            "source_frames": source.n_frames,
            "viewport_frames": requested,
            "viewport_seconds": round(requested / SAMPLE_RATE, 6),
            "spectrogram_columns": panel.spectrogram._current_matrix().shape[0],
            "render_width_px": pixmap.width(),
            "render_height_px": pixmap.height(),
            "headless_paint_completed": rendered,
        }
        return measured, complete
    finally:
        if panel is not None:
            panel.close()
            panel.deleteLater()
        if source is not None:
            source.close()


def _measure_offline_eq_normalize(
    fixture: Path,
    *,
    expected_frames: int,
    block_frames: int,
    scratch: Path,
    quiet: bool,
) -> tuple[dict[str, Any], bool]:
    """Render every source frame through production EQ and normalisation paths."""
    source = StreamingSampleSource(fixture)
    rendered_path = scratch / "eq-render-f32-planar.dat"
    rendered = np.memmap(
        rendered_path,
        dtype=np.float32,
        mode="w+",
        shape=(CHANNELS, expected_frames),
    )
    eq = ThreeBandEQ(
        low_gain_db=1.5,
        mid_frequency=1_800.0,
        mid_gain_db=-2.0,
        high_gain_db=0.75,
    )
    progress_step = max(expected_frames // 10, 1)
    next_progress = progress_step
    position = 0
    normalized: np.ndarray | None = None
    started = time.perf_counter()
    try:
        while position < expected_frames:
            wanted = min(block_frames, expected_frames - position)
            block = source.read(position, wanted)
            if block.shape[0] == 0:
                break
            processed = eq.process_block(block, SAMPLE_RATE, channels_last=True)
            got = int(processed.shape[0])
            rendered[:, position : position + got] = processed.T
            position += got
            if position >= next_progress:
                _progress(
                    quiet,
                    f"offline render {position / expected_frames * 100.0:5.1f}%",
                )
                next_progress += progress_step
        rendered.flush()

        normalizer = NormalizeEffect(target_db=-1.0, mode=NormalizeMode.PEAK)
        normalized = normalizer.process(rendered, SAMPLE_RATE, channels_last=False)
        elapsed = time.perf_counter() - started
        output_peak = float(np.max(np.abs(normalized)))
        target_linear = 10.0 ** (-1.0 / 20.0)
        checksum_indices = np.linspace(
            0,
            max(expected_frames - 1, 0),
            min(4_096, expected_frames),
            dtype=np.int64,
        )
        checksum = float(np.sum(normalized[:, checksum_indices], dtype=np.float64))
        complete = (
            position == expected_frames
            and normalized.shape == (CHANNELS, expected_frames)
            and math.isclose(output_peak, target_linear, rel_tol=0.0, abs_tol=2e-4)
            and math.isfinite(checksum)
        )
        measured = {
            "elapsed_seconds": round(elapsed, 6),
            "source_frames": source.n_frames,
            "frames_eq_processed": position,
            "frames_normalized": int(normalized.shape[1]),
            "block_frames": block_frames,
            "eq": {
                "type": "ThreeBandEQ",
                "low_gain_db": 1.5,
                "mid_frequency_hz": 1_800.0,
                "mid_gain_db": -2.0,
                "high_gain_db": 0.75,
            },
            "normalize": {
                "type": "NormalizeEffect",
                "mode": "peak",
                "target_dbfs": -1.0,
                "applied_gain_db": round(normalizer.applied_gain_db[0], 6),
                "output_peak_dbfs": round(20.0 * math.log10(output_peak), 6),
            },
            "output_checksum": round(checksum, 8),
        }
        return measured, complete
    finally:
        source.close()
        del normalized
        del rendered
        try:
            rendered_path.unlink()
        except OSError:
            pass


def _result(
    *,
    slo_id: str,
    title: str,
    measured: dict[str, Any],
    seconds_max: float,
    operation_complete: bool,
    formal_eligible: bool,
    scope: str,
) -> dict[str, Any]:
    passed = operation_complete and measured["elapsed_seconds"] < seconds_max
    formal_verified = bool(formal_eligible and passed)
    return {
        "slo_id": slo_id,
        "title": title,
        "status": "pass" if passed else "fail",
        "threshold_pass": passed,
        "evidence": "direct-headless" if formal_eligible else "headless-proxy",
        "formal_slo_verified": formal_verified,
        "measured": measured,
        "threshold": {"elapsed_seconds_max": seconds_max},
        "scope": scope,
        "limitation": (
            "Headless Qt on a shared Linux host measures the complete software path, "
            "including paint, but excludes a physical display and monitor latency."
            if slo_id != "offline-eq-normalize"
            else (
                "The full file is decoded and processed, but the benchmark discards "
                "the rendered float buffer instead of timing final container encoding."
            )
        ),
    }


def run_benchmark(args: argparse.Namespace, scratch: Path) -> dict[str, Any]:
    if not math.isfinite(args.duration_seconds) or args.duration_seconds <= 0.0:
        raise ValueError("duration_seconds must be positive and finite")
    if args.block_frames <= 0:
        raise ValueError("block_frames must be positive")
    if not math.isfinite(args.spectrogram_seconds) or args.spectrogram_seconds <= 0.0:
        raise ValueError("spectrogram_seconds must be positive and finite")

    n_frames = round(args.duration_seconds * SAMPLE_RATE)
    fixture_path = scratch / "one-hour-48k-stereo-pcm16.wav"
    _progress(args.quiet, f"writing {n_frames:,}-frame allocated fixture")
    fixture = _write_fixture(fixture_path, n_frames)
    physically_allocated = fixture["allocated_ratio"] >= 0.95
    formal_shape = (
        fixture["duration_seconds"] >= FORMAL_DURATION_SECONDS
        and fixture["sample_rate"] == SAMPLE_RATE
        and fixture["channels"] == CHANNELS
        and physically_allocated
    )
    if args.formal and not formal_shape:
        raise ValueError(
            "--formal requires at least 3600 seconds of physically allocated "
            "48 kHz stereo PCM"
        )
    formal_eligible = bool(args.formal and formal_shape)

    application = _qt_application()
    _progress(args.quiet, "measuring waveform open and offscreen paint")
    waveform, waveform_complete = _measure_waveform_open(
        fixture_path,
        expected_frames=n_frames,
        application=application,
    )
    _progress(args.quiet, "measuring first spectrogram viewport and offscreen paint")
    spectrogram, spectrogram_complete = _measure_spectrogram_first_frame(
        fixture_path,
        expected_frames=n_frames,
        viewport_seconds=args.spectrogram_seconds,
        application=application,
    )
    _progress(args.quiet, "measuring full-file EQ and peak normalisation")
    offline, offline_complete = _measure_offline_eq_normalize(
        fixture_path,
        expected_frames=n_frames,
        block_frames=args.block_frames,
        scratch=scratch,
        quiet=args.quiet,
    )

    results = [
        _result(
            slo_id="waveform-open",
            title="Open one-hour WAV and render waveform",
            measured=waveform,
            seconds_max=WAVEFORM_OPEN_SECONDS_MAX,
            operation_complete=waveform_complete,
            formal_eligible=formal_eligible,
            scope="Streaming open, peak-sidecar restore, 1280×480 headless Qt paint",
        ),
        _result(
            slo_id="spectrogram-first-frame",
            title="Render first spectrogram viewport from one-hour WAV",
            measured=spectrogram,
            seconds_max=SPECTROGRAM_FIRST_FRAME_SECONDS_MAX,
            operation_complete=spectrogram_complete,
            formal_eligible=formal_eligible,
            scope=(
                f"Read/analyze first {spectrogram['viewport_seconds']:g}s viewport "
                "and complete a 1280×720 headless Qt paint"
            ),
        ),
        _result(
            slo_id="offline-eq-normalize",
            title="Offline EQ plus peak normalization over one-hour WAV",
            measured=offline,
            seconds_max=OFFLINE_EQ_NORMALIZE_SECONDS_MAX,
            operation_complete=offline_complete,
            formal_eligible=formal_eligible,
            scope=(
                "Every frame through StreamingSampleSource + ThreeBandEQ, then "
                "the complete render through NormalizeEffect"
            ),
        ),
    ]
    all_formal = all(item["formal_slo_verified"] for item in results)
    return {
        "schema_version": 1,
        "harness": "benchmarks/one_hour_file_perf.py",
        "checklist_item": "B2",
        "evidence": "direct-headless" if formal_eligible else "headless-proxy",
        "formal_slo_verified": all_formal,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor() or "unknown",
            "qt_platform": application.platformName(),
            "clock": "time.perf_counter",
        },
        "fixture": fixture,
        "results": results,
        "summary": {
            "passed": sum(item["status"] == "pass" for item in results),
            "failed": sum(item["status"] != "pass" for item in results),
            "formal_slos_verified": sum(
                item["formal_slo_verified"] for item in results
            ),
        },
    }


def _write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.work_dir is None:
        with tempfile.TemporaryDirectory(prefix="one-hour-file-perf-") as directory:
            report = run_benchmark(args, Path(directory))
    else:
        args.work_dir.mkdir(parents=True, exist_ok=True)
        report = run_benchmark(args, args.work_dir)

    rendered = json.dumps(report, indent=2)
    print(rendered)
    if args.output is not None:
        _write_report(report, args.output)
        _progress(args.quiet, f"report written to {args.output}")
    return 0 if all(item["threshold_pass"] for item in report["results"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
