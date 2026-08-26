#!/usr/bin/env python3
"""Compare an audio benchmark JSON file with the checked-in Round 1 baseline."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

Direction = Literal["higher", "lower"]


@dataclass(frozen=True)
class Metric:
    """A benchmark value and the direction considered better."""

    path: str
    label: str
    direction: Direction
    unit: str


METRICS = (
    Metric(
        "file_loading.aggregate.median_of_file_medians_ms",
        "Median file-load time",
        "lower",
        "ms",
    ),
    Metric(
        "file_loading.aggregate.sum_of_file_medians_ms",
        "Aggregate file-load time",
        "lower",
        "ms",
    ),
    Metric("fft.elapsed_seconds", "FFT elapsed time", "lower", "s"),
    Metric(
        "fft.transforms_per_second",
        "FFT throughput",
        "higher",
        "transforms/s",
    ),
    Metric(
        "fft.samples_per_second",
        "FFT sample throughput",
        "higher",
        "samples/s",
    ),
    Metric("memory.python_peak_bytes", "Python peak allocation", "lower", "bytes"),
    Metric("memory.process_peak_rss_bytes", "Process peak RSS", "lower", "bytes"),
)

CONFIGURATION_KEYS = (
    "buffer_frames",
    "fft_iterations",
    "fft_size",
    "load_repetitions",
)


def load_report(path: Path) -> dict[str, Any]:
    """Load and minimally validate a benchmark report."""
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"cannot read {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"{path} is not valid JSON: {error}") from error
    if not isinstance(report, dict):
        raise ValueError(f"{path} must contain a JSON object")
    if report.get("schema_version") != 1:
        raise ValueError(f"{path} has unsupported schema_version")
    return report


def nested_number(report: dict[str, Any], dotted_path: str) -> float:
    """Return a finite numeric value addressed by a dotted object path."""
    value: Any = report
    for component in dotted_path.split("."):
        if not isinstance(value, dict) or component not in value:
            raise ValueError(f"missing benchmark metric: {dotted_path}")
        value = value[component]
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValueError(f"benchmark metric is not numeric: {dotted_path}")
    return float(value)


def metric_delta(
    metric: Metric,
    baseline: dict[str, Any],
    current: dict[str, Any],
    threshold_percent: float,
) -> dict[str, Any]:
    """Build one direction-aware delta record."""
    before = nested_number(baseline, metric.path)
    after = nested_number(current, metric.path)
    delta = after - before
    delta_percent = (delta / before * 100.0) if before else None
    adverse_percent = (
        delta_percent
        if metric.direction == "lower"
        else -delta_percent
        if delta_percent is not None
        else None
    )

    if adverse_percent is None:
        status = "incomparable"
    elif adverse_percent > threshold_percent:
        status = "regression"
    elif adverse_percent < -threshold_percent:
        status = "improvement"
    else:
        status = "stable"

    return {
        "path": metric.path,
        "label": metric.label,
        "unit": metric.unit,
        "better": metric.direction,
        "baseline": before,
        "current": after,
        "delta": delta,
        "delta_percent": delta_percent,
        "adverse_delta_percent": adverse_percent,
        "status": status,
    }


def latency_metrics(report: dict[str, Any]) -> dict[int, float]:
    """Index playback-startup estimates by sample rate."""
    section = report.get("playback_latency_estimate", {})
    estimates = section.get("estimates", []) if isinstance(section, dict) else []
    indexed: dict[int, float] = {}
    for estimate in estimates:
        if not isinstance(estimate, dict):
            continue
        rate = estimate.get("sample_rate_hz")
        latency = estimate.get("estimated_startup_ms")
        if (
            isinstance(rate, int)
            and isinstance(latency, int | float)
            and not isinstance(latency, bool)
        ):
            indexed[rate] = float(latency)
    return indexed


def latency_deltas(
    baseline: dict[str, Any],
    current: dict[str, Any],
    threshold_percent: float,
) -> list[dict[str, Any]]:
    """Compare startup-latency estimates common to both reports."""
    before = latency_metrics(baseline)
    after = latency_metrics(current)
    comparisons = []
    for sample_rate in sorted(before.keys() & after.keys()):
        path = (
            "playback_latency_estimate.estimates"
            f"[sample_rate_hz={sample_rate}].estimated_startup_ms"
        )
        synthetic_baseline = {"value": before[sample_rate]}
        synthetic_current = {"value": after[sample_rate]}
        comparison = metric_delta(
            Metric(path="value", label=f"Startup latency @ {sample_rate} Hz", direction="lower", unit="ms"),
            synthetic_baseline,
            synthetic_current,
            threshold_percent,
        )
        comparison["path"] = path
        comparisons.append(comparison)
    return comparisons


def selected_configuration(report: dict[str, Any]) -> dict[str, Any]:
    """Return workload settings that must match for a meaningful delta."""
    configuration = report.get("configuration", {})
    if not isinstance(configuration, dict):
        return {}
    return {key: configuration.get(key) for key in CONFIGURATION_KEYS}


def environment_summary(report: dict[str, Any]) -> dict[str, Any]:
    """Return the host fields useful for judging cross-run comparability."""
    environment = report.get("environment", {})
    if not isinstance(environment, dict):
        return {}
    return {
        key: environment.get(key)
        for key in ("platform", "processor", "python")
    }


def build_delta_report(
    baseline: dict[str, Any],
    current: dict[str, Any],
    *,
    baseline_path: Path,
    current_path: Path,
    threshold_percent: float,
) -> dict[str, Any]:
    """Compare benchmark reports and return a machine-readable delta report."""
    comparisons = [
        metric_delta(metric, baseline, current, threshold_percent)
        for metric in METRICS
    ]
    comparisons.extend(latency_deltas(baseline, current, threshold_percent))
    baseline_configuration = selected_configuration(baseline)
    current_configuration = selected_configuration(current)
    baseline_environment = environment_summary(baseline)
    current_environment = environment_summary(current)
    configuration_matches = baseline_configuration == current_configuration
    environment_matches = baseline_environment == current_environment

    counts = {
        status: sum(item["status"] == status for item in comparisons)
        for status in ("regression", "improvement", "stable", "incomparable")
    }
    warnings = []
    if not configuration_matches:
        warnings.append("Benchmark workload configuration differs from the baseline.")
    if not environment_matches:
        warnings.append(
            "Host or Python environment differs; timing and RSS deltas are informational."
        )

    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "baseline_path": baseline_path.as_posix(),
        "current_path": current_path.as_posix(),
        "regression_threshold_percent": threshold_percent,
        "comparison_valid": configuration_matches and environment_matches,
        "configuration": {
            "matches": configuration_matches,
            "baseline": baseline_configuration,
            "current": current_configuration,
        },
        "environment": {
            "matches": environment_matches,
            "baseline": baseline_environment,
            "current": current_environment,
        },
        "summary": {
            **counts,
            "rust_escape_hatch_evaluated": False,
            "note": "Use tools/monitor-realtime.py for realtime Rust thresholds.",
        },
        "warnings": warnings,
        "metrics": comparisons,
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    repository_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("current", type=Path, help="Current benchmark JSON report.")
    parser.add_argument(
        "--baseline",
        type=Path,
        default=repository_root / ".agent_workspace/round1/benchmark-baseline.json",
        help="Baseline JSON (default: checked-in Round 1 report).",
    )
    parser.add_argument("--output", type=Path, help="Optional JSON output path.")
    parser.add_argument(
        "--threshold-percent",
        type=float,
        default=10.0,
        help="Adverse percentage delta classified as a regression (default: 10).",
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit 1 when at least one metric regresses beyond the threshold.",
    )
    return parser.parse_args()


def main() -> int:
    """Run the comparison CLI."""
    args = parse_args()
    if args.threshold_percent < 0:
        print("--threshold-percent must be non-negative", file=sys.stderr)
        return 2
    try:
        baseline = load_report(args.baseline)
        current = load_report(args.current)
        report = build_delta_report(
            baseline,
            current,
            baseline_path=args.baseline,
            current_path=args.current,
            threshold_percent=args.threshold_percent,
        )
    except ValueError as error:
        print(f"perf-regression: {error}", file=sys.stderr)
        return 2

    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    has_regression = report["summary"]["regression"] > 0
    return int(args.fail_on_regression and has_regression)


if __name__ == "__main__":
    raise SystemExit(main())
