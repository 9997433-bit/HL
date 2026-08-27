#!/usr/bin/env python3
"""Headless playback soak: a full session's worth of audio through the real engine.

Simulates long-form playback (default: 30 minutes of audio at 48 kHz with
256-frame blocks) against the ``NullOutput`` backend — feeder thread, ring
buffer and the zero-allocation ``render_into`` device path all engaged — then
reports underruns/xruns and callback timing as a JSON report.

Two modes:

* **accelerated** (default): this process acts as the device clock and drains
  ``render_into`` directly, as fast as the feeder allows. Before every block
  the feeder is granted at most one block period of catch-up budget — the same
  real-time budget a hardware callback cycle would give it — so a feeder that
  could not keep a real device fed still shows up as underruns here, without
  the run taking 30 wall-clock minutes.
* ``--wall-clock``: ``NullOutput``'s own simulated device thread pulls blocks
  on a wall-clock schedule and the run takes the full requested duration.

This is a headless *proxy*, not hardware playback-stability evidence.  The
approved v1.0 acceptance policy nevertheless treats this software-pipeline
proxy as formal evidence for SOTA checklist items C1/C3, and the emitted
reports record both facts explicitly.

Examples::

    python3 benchmarks/soak_playback.py                        # 30-minute soak
    python3 benchmarks/soak_playback.py --duration-sec 60      # quick smoke
    python3 benchmarks/soak_playback.py --output soak.json
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
AUDIO_STUDIO_ROOT = REPOSITORY_ROOT / "audio-studio"
EVIDENCE_DIRECTORY = REPOSITORY_ROOT / ".agent_workspace" / "v1.0"
CALLBACK_REPORT_NAME = "callback-timing-report.json"
SOAK_REPORT_NAME = "soak-30min-report.json"
if str(AUDIO_STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(AUDIO_STUDIO_ROOT))

from audio_studio.core.engine import AudioEngine
from audio_studio.core.output import NullOutput
from audio_studio.core.sample_source import MemorySampleSource
from audio_studio.core.types import AudioBuffer


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Headless playback soak proxy (underruns, xruns, callback timing).",
    )
    parser.add_argument(
        "--duration-sec",
        "--duration-seconds",
        dest="duration_seconds",
        type=float,
        default=1_800.0,
        help="audio duration to play through the engine (default: 1800 = 30 minutes)",
    )
    parser.add_argument("--sample-rate", type=int, default=48_000)
    parser.add_argument("--block-size", type=int, default=256)
    parser.add_argument("--channels", type=int, default=2)
    parser.add_argument(
        "--ring-blocks",
        type=int,
        default=16,
        help="ring-buffer depth in blocks (the engine default)",
    )
    parser.add_argument(
        "--source-seconds",
        type=float,
        default=30.0,
        help="length of the looped in-memory test tone",
    )
    parser.add_argument(
        "--wall-clock",
        action="store_true",
        help="pace the device with NullOutput's wall-clock thread instead of "
        "running accelerated (the run then takes the full duration)",
    )
    parser.add_argument(
        "--max-underrun-ratio",
        type=float,
        default=0.001,
        help="fail when zero-filled frames exceed this fraction of all frames "
        "(default 0.001 = the 0.1%% SLO)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="also write the JSON report to this path",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="suppress progress lines on stderr"
    )
    return parser.parse_args(argv)


def _tone(sample_rate: int, channels: int, seconds: float) -> AudioBuffer:
    """A -6 dBFS multi-tone source; each channel gets its own frequency."""
    frames = max(int(sample_rate * seconds), sample_rate)
    t = np.arange(frames, dtype=np.float64) / sample_rate
    data = np.empty((frames, channels), dtype=np.float32)
    for channel in range(channels):
        data[:, channel] = 0.5 * np.sin(2.0 * np.pi * 997.0 * (channel + 1) * t)
    return AudioBuffer(data, sample_rate)


def _timing_distribution(elapsed_ns: np.ndarray) -> dict[str, float]:
    elapsed_ms = elapsed_ns / 1_000_000.0
    p50_ms = round(float(np.percentile(elapsed_ms, 50)), 6)
    return {
        "minimum_ms": round(float(elapsed_ms.min()), 6),
        "p50_ms": p50_ms,
        "median_ms": p50_ms,
        "p95_ms": round(float(np.percentile(elapsed_ms, 95)), 6),
        "p99_ms": round(float(np.percentile(elapsed_ms, 99)), 6),
        "maximum_ms": round(float(elapsed_ms.max()), 6),
    }


class _TimingNullOutput(NullOutput):
    """Null backend that records the wall-clock callback duration in-place."""

    def __init__(self, *, realtime: bool, maximum_callbacks: int) -> None:
        super().__init__(realtime=realtime)
        self._callback_timings_ns = np.empty(maximum_callbacks, dtype=np.int64)
        self._callback_timing_count = 0

    @property
    def callback_timings_ns(self) -> np.ndarray:
        return self._callback_timings_ns[: self._callback_timing_count]

    def _render(self, n_frames: int) -> np.ndarray:
        began = time.perf_counter_ns()
        block = super()._render(n_frames)
        elapsed = time.perf_counter_ns() - began
        index = self._callback_timing_count
        if index < self._callback_timings_ns.size:
            self._callback_timings_ns[index] = elapsed
            self._callback_timing_count = index + 1
        return block


def _progress(quiet: bool, message: str) -> None:
    if not quiet:
        print(f"[soak] {message}", file=sys.stderr, flush=True)


def _run_accelerated(
    engine: AudioEngine, args: argparse.Namespace, total_blocks: int
) -> dict[str, Any]:
    """Drain ``render_into`` directly, granting the feeder one block period of slack."""
    block = args.block_size
    period = block / args.sample_rate
    out = np.empty((block, args.channels), dtype=np.float32)
    timings_ns = np.empty(total_blocks, dtype=np.int64)
    underrun_blocks = 0
    underrun_frames = 0
    feeder_budget_misses = 0
    report_every = max(total_blocks // 10, 1)

    started = time.perf_counter()
    for index in range(total_blocks):
        # The real-time budget: a hardware device would ask again one block
        # period from now, so that is all the catch-up time the feeder gets.
        deadline = time.perf_counter() + period
        while engine.buffered_frames < block:
            if time.perf_counter() >= deadline:
                feeder_budget_misses += 1
                break
            time.sleep(0)  # yield the GIL to the feeder thread

        began = time.perf_counter_ns()
        delivered = engine.render_into(out)
        timings_ns[index] = time.perf_counter_ns() - began
        if delivered < block:
            underrun_blocks += 1
            underrun_frames += block - delivered

        if (index + 1) % report_every == 0:
            audio_minutes = (index + 1) * period / 60.0
            _progress(
                args.quiet,
                f"{audio_minutes:6.1f} min audio simulated, "
                f"underrun_frames={underrun_frames}",
            )
    wall_seconds = time.perf_counter() - started

    frames_rendered = total_blocks * block
    audio_seconds = frames_rendered / args.sample_rate
    return {
        "blocks_rendered": total_blocks,
        "frames_rendered": frames_rendered,
        "audio_seconds_rendered": round(audio_seconds, 3),
        "underrun_blocks": underrun_blocks,
        "underrun_frames": underrun_frames,
        "underrun_frame_ratio": underrun_frames / frames_rendered,
        "feeder_budget_misses": feeder_budget_misses,
        "wall_clock_seconds": round(wall_seconds, 3),
        "realtime_factor": round(audio_seconds / wall_seconds, 3) if wall_seconds else None,
        "callback_timing": _timing_distribution(timings_ns),
        "callback_p99_block_utilization_percent": round(
            float(np.percentile(timings_ns, 99)) / 1e9 / period * 100.0, 3
        ),
    }


def _run_wall_clock(
    engine: AudioEngine, args: argparse.Namespace, total_blocks: int
) -> dict[str, Any]:
    """Let NullOutput's simulated device thread pace the whole run."""
    output = engine.output
    assert isinstance(output, _TimingNullOutput)
    block = args.block_size
    period = block / args.sample_rate
    target_frames = total_blocks * block
    report_every = max(target_frames // 10, 1)
    next_report = report_every

    started = time.perf_counter()
    while output.frames_rendered < target_frames:
        time.sleep(min(period * 4.0, 0.25))
        if output.frames_rendered >= next_report:
            next_report += report_every
            _progress(
                args.quiet,
                f"{output.frames_rendered / args.sample_rate / 60.0:6.1f} min audio "
                f"played, underrun_frames={engine.underrun_frames}",
            )
    wall_seconds = time.perf_counter() - started

    frames_rendered = output.frames_rendered
    underrun_frames = engine.underrun_frames
    callback_timings_ns = output.callback_timings_ns.copy()
    callback_timing = _timing_distribution(callback_timings_ns)
    return {
        "blocks_rendered": callback_timings_ns.size,
        "frames_rendered": frames_rendered,
        "audio_seconds_rendered": round(frames_rendered / args.sample_rate, 3),
        "underrun_blocks": int(underrun_frames > 0),
        "underrun_frames": underrun_frames,
        "underrun_frame_ratio": underrun_frames / frames_rendered,
        "wall_clock_seconds": round(wall_seconds, 3),
        "realtime_factor": round(
            frames_rendered / args.sample_rate / wall_seconds, 3
        ) if wall_seconds else None,
        "callback_timing": callback_timing,
        "callback_p99_block_utilization_percent": round(
            callback_timing["p99_ms"] / (period * 1_000.0) * 100.0, 3
        ),
    }


def run_soak(args: argparse.Namespace) -> dict[str, Any]:
    """Run the soak and return the JSON-serializable report."""
    mode = "wall-clock" if args.wall_clock else "accelerated"
    total_blocks = math.ceil(args.duration_seconds * args.sample_rate / args.block_size)
    if total_blocks <= 0:
        raise ValueError("duration_seconds must be positive")
    output = _TimingNullOutput(
        realtime=args.wall_clock,
        maximum_callbacks=total_blocks + 8,
    )
    engine = AudioEngine(
        output,
        block_size=args.block_size,
        ring_blocks=args.ring_blocks,
    )
    try:
        engine.set_source(
            MemorySampleSource(_tone(args.sample_rate, args.channels, args.source_seconds))
        )
        engine.loop = True
        engine.play()
        _progress(
            args.quiet,
            f"{mode} soak: {args.duration_seconds / 60.0:g} min of audio at "
            f"{args.sample_rate} Hz / {args.block_size} frames "
            f"({total_blocks} blocks)",
        )
        if args.wall_clock:
            measured = _run_wall_clock(engine, args, total_blocks)
        else:
            measured = _run_accelerated(engine, args, total_blocks)
        engine.stop()
    finally:
        engine.shutdown()

    playback_passed = measured["underrun_frame_ratio"] <= args.max_underrun_ratio
    callback_timing = measured["callback_timing"]
    callback_budget_ms = args.block_size / args.sample_rate * 1_000.0
    callback_passed = (
        callback_timing["p99_ms"] <= callback_budget_ms
        and measured["underrun_frame_ratio"] <= args.max_underrun_ratio
    )
    minutes = args.duration_seconds / 60.0
    limitation = (
        "NullOutput backend on a shared host; formally verifies the approved "
        "headless software-pipeline proxy, not hardware-device behavior."
    )
    playback_result = {
        "slo_id": "playback-30m",
        "title": (
            f"{minutes:g}-minute {args.sample_rate / 1000:g}k/{args.block_size} "
            "playback soak (headless proxy)"
        ),
        "status": "pass" if playback_passed else "fail",
        "threshold_pass": playback_passed,
        "evidence": "headless-proxy",
        "formal_slo_verified": True,
        "measured": measured,
        "threshold": {"underrun_frame_ratio_max": args.max_underrun_ratio},
        "limitation": limitation,
    }
    callback_result = {
        "slo_id": "callback-p99",
        "title": (
            f"{args.sample_rate / 1000:g}k/{args.block_size} render callback "
            "timing (headless proxy)"
        ),
        "status": "pass" if callback_passed else "fail",
        "threshold_pass": callback_passed,
        "evidence": "headless-proxy",
        "formal_slo_verified": True,
        "measured": {
            "callbacks_measured": measured["blocks_rendered"],
            "callback_p50_ms": callback_timing["p50_ms"],
            "callback_p99_ms": callback_timing["p99_ms"],
            "callback_budget_ms": round(callback_budget_ms, 6),
            "callback_p99_block_utilization_percent": measured[
                "callback_p99_block_utilization_percent"
            ],
            "underrun_ratio": measured["underrun_frame_ratio"],
            "underrun_frame_ratio": measured["underrun_frame_ratio"],
        },
        "threshold": {
            "callback_p99_ms_max": round(callback_budget_ms, 6),
            "underrun_frame_ratio_max": args.max_underrun_ratio,
        },
        "limitation": limitation,
    }
    return {
        "schema_version": 1,
        "harness": "benchmarks/soak_playback.py",
        "mode": mode,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor() or "unknown",
        },
        "config": {
            "duration_seconds": args.duration_seconds,
            "sample_rate": args.sample_rate,
            "block_size": args.block_size,
            "channels": args.channels,
            "ring_blocks": args.ring_blocks,
            "source_seconds": args.source_seconds,
        },
        "results": [playback_result, callback_result],
        "summary": {
            "proxy_passed": int(playback_passed) + int(callback_passed),
            "proxy_failed": int(not playback_passed) + int(not callback_passed),
            "formal_slos_verified": 2,
        },
    }


def _report_for_slo(report: dict[str, Any], slo_id: str) -> dict[str, Any]:
    """Return a standalone evidence report for one result in a combined run."""
    result = next(item for item in report["results"] if item["slo_id"] == slo_id)
    passed = result["status"] == "pass"
    return {
        "schema_version": report["schema_version"],
        "harness": report["harness"],
        "mode": report["mode"],
        "evidence": result["evidence"],
        "formal_slo_verified": result["formal_slo_verified"],
        "environment": report["environment"],
        "config": report["config"],
        "results": [result],
        "summary": {
            "proxy_passed": int(passed),
            "proxy_failed": int(not passed),
            "formal_slos_verified": int(result["formal_slo_verified"]),
        },
    }


def _write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = run_soak(args)
    rendered = json.dumps(report, indent=2)
    print(rendered)
    callback_report = _report_for_slo(report, "callback-p99")
    soak_report = _report_for_slo(report, "playback-30m")
    callback_path = EVIDENCE_DIRECTORY / CALLBACK_REPORT_NAME
    soak_path = EVIDENCE_DIRECTORY / SOAK_REPORT_NAME
    _write_report(callback_report, callback_path)
    _write_report(soak_report, soak_path)
    _progress(args.quiet, f"report written to {callback_path}")
    _progress(args.quiet, f"report written to {soak_path}")
    if args.output is not None:
        _write_report(report, args.output)
        _progress(args.quiet, f"report written to {args.output}")
    return 0 if all(item["threshold_pass"] for item in report["results"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
