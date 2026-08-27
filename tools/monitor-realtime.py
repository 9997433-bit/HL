#!/usr/bin/env python3
"""Measure or simulate callback timing and evaluate the Rust escape hatch."""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_SAMPLE_RATE = 48_000
DEFAULT_BUFFER_FRAMES = 128
DEFAULT_P99_THRESHOLD_MS = 1.33
DEFAULT_UNDERRUN_THRESHOLD_PERCENT = 0.1


def percentile(values: list[float], quantile: float) -> float:
    """Return a nearest-rank percentile."""
    if not values:
        raise ValueError("at least one callback duration is required")
    ordered = sorted(values)
    rank = max(1, math.ceil(quantile * len(ordered)))
    return ordered[rank - 1]


def simulate_callbacks(
    count: int,
    callback_budget_ms: float,
    *,
    target_load: float,
    jitter: float,
    underrun_rate_percent: float,
    seed: int,
) -> list[float]:
    """Generate deterministic callback durations for CI and threshold testing."""
    generator = random.Random(seed)
    center = callback_budget_ms * target_load
    deviation = callback_budget_ms * jitter
    durations = [
        max(0.001, generator.gauss(center, deviation))
        for _ in range(count)
    ]
    injected = round(count * underrun_rate_percent / 100.0)
    for index in generator.sample(range(count), min(injected, count)):
        durations[index] = callback_budget_ms * generator.uniform(1.01, 1.25)
    return durations


def synthetic_callback(
    frames: int,
    tracks: int,
    effects_per_track: int,
    phase: int,
) -> float:
    """Run a dependency-free approximation of a multitrack DSP hot loop."""
    checksum = 0.0
    for frame in range(frames):
        mixed = 0.0
        source = ((frame + phase) % 97 - 48) / 48.0
        for track in range(tracks):
            sample = source * (1.0 - track / (tracks * 2.0))
            for effect in range(effects_per_track):
                sample = sample * (0.999 - effect * 0.0001) + 0.00001
            mixed += sample
        checksum += mixed
    return checksum


def measure_callbacks(
    count: int,
    frames: int,
    tracks: int,
    effects_per_track: int,
) -> tuple[list[float], float]:
    """Time repeated synthetic callbacks without sleeping between blocks."""
    durations = []
    checksum = 0.0
    synthetic_callback(frames, tracks, effects_per_track, 0)
    for iteration in range(count):
        started = time.perf_counter_ns()
        checksum += synthetic_callback(
            frames,
            tracks,
            effects_per_track,
            iteration,
        )
        durations.append((time.perf_counter_ns() - started) / 1_000_000.0)
    return durations, checksum


def load_recorded_durations(path: Path) -> tuple[list[float], int | None]:
    """Load callback durations and an optional authoritative underrun count."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"cannot read {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"{path} is not valid JSON: {error}") from error

    underrun_count = None
    if isinstance(payload, list):
        raw_durations = payload
    elif isinstance(payload, dict):
        raw_durations = payload.get("durations_ms")
        raw_underruns = payload.get("underrun_count")
        if raw_underruns is not None:
            if not isinstance(raw_underruns, int) or raw_underruns < 0:
                raise ValueError("underrun_count must be a non-negative integer")
            underrun_count = raw_underruns
    else:
        raise ValueError(  # noqa: TRY004
            "duration input must be a JSON list or object"
        )

    if not isinstance(raw_durations, list) or not raw_durations:
        raise ValueError("durations_ms must be a non-empty JSON list")
    durations = []
    for value in raw_durations:
        if (
            not isinstance(value, int | float)
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError("every callback duration must be a finite non-negative number")
        durations.append(float(value))
    return durations, underrun_count


def build_report(
    durations_ms: list[float],
    *,
    source: str,
    sample_rate: int,
    buffer_frames: int,
    p99_threshold_ms: float,
    underrun_threshold_percent: float,
    recorded_underruns: int | None = None,
    workload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Summarize callback timing and apply the Round 1 migration thresholds."""
    callback_budget_ms = buffer_frames / sample_rate * 1_000.0
    deadline_misses = sum(duration > callback_budget_ms for duration in durations_ms)
    underrun_count = (
        recorded_underruns
        if recorded_underruns is not None
        else deadline_misses
    )
    if underrun_count > len(durations_ms):
        raise ValueError("underrun_count cannot exceed the callback count")

    p99_ms = percentile(durations_ms, 0.99)
    underrun_rate_percent = underrun_count / len(durations_ms) * 100.0
    p99_triggered = p99_ms > p99_threshold_ms
    underrun_triggered = underrun_rate_percent > underrun_threshold_percent
    migration_recommended = p99_triggered or underrun_triggered
    triggers = []
    if p99_triggered:
        triggers.append(
            f"callback p99 {p99_ms:.6f} ms exceeds {p99_threshold_ms:.6f} ms"
        )
    if underrun_triggered:
        triggers.append(
            "underrun rate "
            f"{underrun_rate_percent:.6f}% exceeds "
            f"{underrun_threshold_percent:.6f}%"
        )

    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source": source,
        "configuration": {
            "sample_rate_hz": sample_rate,
            "buffer_frames": buffer_frames,
            "callback_budget_ms": callback_budget_ms,
            "p99_threshold_ms": p99_threshold_ms,
            "underrun_threshold_percent": underrun_threshold_percent,
            "workload": workload,
        },
        "measurements": {
            "callback_count": len(durations_ms),
            "minimum_ms": min(durations_ms),
            "mean_ms": statistics.fmean(durations_ms),
            "median_ms": statistics.median(durations_ms),
            "p95_ms": percentile(durations_ms, 0.95),
            "p99_ms": p99_ms,
            "maximum_ms": max(durations_ms),
            "p99_budget_utilization_percent": p99_ms / callback_budget_ms * 100.0,
            "deadline_miss_count": deadline_misses,
            "underrun_count": underrun_count,
            "underrun_rate_percent": underrun_rate_percent,
        },
        "decision": {
            "p99_triggered": p99_triggered,
            "underrun_triggered": underrun_triggered,
            "rust_migration_recommended": migration_recommended,
            "triggers": triggers,
            "recommendation": (
                "Evaluate migration of the realtime inner loop to the Rust escape hatch."
                if migration_recommended
                else "Keep the Python path and continue representative hardware soak tests."
            ),
        },
        "limitations": [
            "Synthetic and imported timings do not validate an audio driver or hardware device.",
            "CI scheduling cannot substitute for the required 10-minute device underrun soak.",
        ],
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("simulate", "measure"), default="simulate")
    parser.add_argument("--durations-file", type=Path)
    parser.add_argument("--iterations", type=int, default=500)
    parser.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE)
    parser.add_argument("--buffer-frames", type=int, default=DEFAULT_BUFFER_FRAMES)
    parser.add_argument("--tracks", type=int, default=32)
    parser.add_argument("--effects-per-track", type=int, default=4)
    parser.add_argument("--target-load", type=float, default=0.30)
    parser.add_argument("--jitter", type=float, default=0.08)
    parser.add_argument("--simulated-underrun-rate-percent", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=6116)
    parser.add_argument(
        "--p99-threshold-ms",
        type=float,
        default=DEFAULT_P99_THRESHOLD_MS,
    )
    parser.add_argument(
        "--underrun-threshold-percent",
        type=float,
        default=DEFAULT_UNDERRUN_THRESHOLD_PERCENT,
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--fail-on-trigger",
        action="store_true",
        help="Exit 1 when the Rust migration threshold is triggered.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    """Reject invalid workload and threshold values."""
    positive = {
        "--iterations": args.iterations,
        "--sample-rate": args.sample_rate,
        "--buffer-frames": args.buffer_frames,
        "--tracks": args.tracks,
        "--effects-per-track": args.effects_per_track,
        "--p99-threshold-ms": args.p99_threshold_ms,
    }
    invalid = [name for name, value in positive.items() if value <= 0]
    if invalid:
        raise ValueError(f"{', '.join(invalid)} must be positive")
    non_negative = {
        "--target-load": args.target_load,
        "--jitter": args.jitter,
        "--simulated-underrun-rate-percent": args.simulated_underrun_rate_percent,
        "--underrun-threshold-percent": args.underrun_threshold_percent,
    }
    invalid = [name for name, value in non_negative.items() if value < 0]
    if invalid:
        raise ValueError(f"{', '.join(invalid)} must be non-negative")
    if args.simulated_underrun_rate_percent > 100:
        raise ValueError("--simulated-underrun-rate-percent cannot exceed 100")


def main() -> int:
    """Run the realtime monitoring CLI."""
    args = parse_args()
    try:
        validate_args(args)
        callback_budget_ms = args.buffer_frames / args.sample_rate * 1_000.0
        workload: dict[str, Any] | None = None
        if args.durations_file:
            durations, recorded_underruns = load_recorded_durations(args.durations_file)
            source = "recorded"
            workload = {"input": args.durations_file.as_posix()}
        elif args.mode == "measure":
            durations, checksum = measure_callbacks(
                args.iterations,
                args.buffer_frames,
                args.tracks,
                args.effects_per_track,
            )
            recorded_underruns = None
            source = "measured_synthetic_workload"
            workload = {
                "tracks": args.tracks,
                "effects_per_track": args.effects_per_track,
                "checksum": checksum,
            }
        else:
            durations = simulate_callbacks(
                args.iterations,
                callback_budget_ms,
                target_load=args.target_load,
                jitter=args.jitter,
                underrun_rate_percent=args.simulated_underrun_rate_percent,
                seed=args.seed,
            )
            recorded_underruns = None
            source = "simulated"
            workload = {
                "target_load": args.target_load,
                "jitter": args.jitter,
                "simulated_underrun_rate_percent": args.simulated_underrun_rate_percent,
                "seed": args.seed,
            }

        report = build_report(
            durations,
            source=source,
            sample_rate=args.sample_rate,
            buffer_frames=args.buffer_frames,
            p99_threshold_ms=args.p99_threshold_ms,
            underrun_threshold_percent=args.underrun_threshold_percent,
            recorded_underruns=recorded_underruns,
            workload=workload,
        )
    except ValueError as error:
        print(f"monitor-realtime: {error}", file=sys.stderr)
        return 2

    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    triggered = report["decision"]["rust_migration_recommended"]
    return int(args.fail_on_trigger and triggered)


if __name__ == "__main__":
    raise SystemExit(main())
