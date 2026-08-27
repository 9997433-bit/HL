"""Measure Audio Studio's selected sample-rate converter against mastering gates."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from itertools import pairwise
from pathlib import Path
from typing import Any

import numpy as np
import scipy

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
AUDIO_STUDIO_ROOT = REPOSITORY_ROOT / "audio-studio"
if str(AUDIO_STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(AUDIO_STUDIO_ROOT))

from audio_studio.core.resample import (  # noqa: E402
    resample_backend,
    resample_buffer,
    soxr_available,
)

SOURCE_RATE = 96_000
TARGET_RATE = 44_100
DEFAULT_DURATION_SECONDS = 2.0
DEFAULT_OUTPUT = Path(".agent_workspace/round3/src-quality-report.json")

MAX_PASSBAND_DEVIATION_DB = 0.01
MAX_STOPBAND_MIRROR_DBFS = -120.0
MAX_THD_PLUS_N_DBFS = -130.0


def _dbfs(value: float) -> float:
    return 20.0 * math.log10(max(float(value), np.finfo(np.float64).tiny))


def _convert(samples: np.ndarray) -> np.ndarray:
    return resample_buffer(samples, SOURCE_RATE, TARGET_RATE, quality="vhq")


def _package_version(distribution: str) -> str:
    try:
        return version(distribution)
    except PackageNotFoundError:  # pragma: no cover - import and metadata normally agree
        return "unknown"


def _src_paths() -> dict[str, dict[str, str]]:
    paths = {
        "scipy": {
            "backend": "scipy.signal.resample_poly",
            "scipy_version": scipy.__version__,
            "quality": "default Kaiser beta=5.0",
        }
    }
    if soxr_available():
        paths["soxr"] = {
            "backend": "soxr.resample",
            "soxr_version": _package_version("soxr"),
            "quality": "VHQ",
        }
    return paths


def _log_sweep(
    sample_rate: int,
    duration_seconds: float,
    start_hz: float,
    end_hz: float,
    *,
    amplitude: float = 0.9,
) -> np.ndarray:
    """Return a logarithmic sine sweep with phase defined in continuous time."""
    frame_count = round(sample_rate * duration_seconds)
    time = np.arange(frame_count, dtype=np.float64) / sample_rate
    log_ratio = math.log(end_hz / start_hz)
    phase = (
        2.0
        * np.pi
        * start_hz
        * duration_seconds
        / log_ratio
        * (np.exp(time * log_ratio / duration_seconds) - 1.0)
    )
    return amplitude * np.sin(phase)


def _trim_edges(samples: np.ndarray, sample_rate: int) -> np.ndarray:
    """Discard converter start/end transients while retaining short probes."""
    trim = min(round(0.05 * sample_rate), samples.size // 10)
    return samples[trim:-trim] if trim else samples


def _passband_deviation_db(duration_seconds: float) -> float:
    source = _log_sweep(SOURCE_RATE, duration_seconds, 20.0, 20_000.0)
    converted = _convert(source)
    reference = _log_sweep(TARGET_RATE, duration_seconds, 20.0, 20_000.0)
    usable = min(converted.size, reference.size)
    converted = converted[:usable]
    reference = reference[:usable]

    # Compare local RMS levels along the sweep. The direct target-rate sweep is
    # the continuous-time reference and cancels the chirp's changing crest/RMS.
    edge = min(round(0.05 * TARGET_RATE), usable // 10)
    starts = np.linspace(edge, usable - edge, 33, dtype=int)
    gains_db: list[float] = []
    for start, end in pairwise(starts):
        actual_rms = math.sqrt(float(np.mean(np.square(converted[start:end]))))
        reference_rms = math.sqrt(float(np.mean(np.square(reference[start:end]))))
        gains_db.append(_dbfs(actual_rms / reference_rms))
    return float(np.max(np.abs(gains_db)))


def _stopband_mirror_dbfs(duration_seconds: float) -> float:
    # Frequencies above the 44.1 kHz destination Nyquist limit may only appear
    # in the output as aliases. A sweep exposes the worst transition/stopband
    # mirror instead of testing one favorable frequency.
    source = _log_sweep(SOURCE_RATE, duration_seconds, 24_000.0, 46_000.0)
    converted = _trim_edges(
        _convert(source),
        TARGET_RATE,
    )
    windows = np.array_split(converted, 32)
    worst_rms = max(
        math.sqrt(float(np.mean(np.square(window))))
        for window in windows
        if window.size
    )
    return _dbfs(worst_rms)


def _thd_plus_n_dbfs(duration_seconds: float) -> float:
    duration_seconds = max(duration_seconds, 0.25)
    source_time = np.arange(
        round(SOURCE_RATE * duration_seconds),
        dtype=np.float64,
    ) / SOURCE_RATE
    source = 0.9 * np.sin(2.0 * np.pi * 1_000.0 * source_time)
    converted = _trim_edges(
        _convert(source),
        TARGET_RATE,
    )

    # Remove the best-fit fundamental (including any constant phase shift) and
    # report all remaining energy against digital full scale.
    time = np.arange(converted.size, dtype=np.float64) / TARGET_RATE
    basis = np.column_stack(
        (
            np.sin(2.0 * np.pi * 1_000.0 * time),
            np.cos(2.0 * np.pi * 1_000.0 * time),
            np.ones(converted.size, dtype=np.float64),
        )
    )
    coefficients, *_ = np.linalg.lstsq(basis, converted, rcond=None)
    residual = converted - basis @ coefficients
    return _dbfs(math.sqrt(float(np.mean(np.square(residual)))))


def measure_src_quality(
    *,
    duration_seconds: float = DEFAULT_DURATION_SECONDS,
) -> dict[str, Any]:
    """Measure the selected 96 kHz to 44.1 kHz conversion path."""
    if duration_seconds <= 0.0:
        raise ValueError("duration_seconds must be positive")

    backend = resample_backend()
    paths = _src_paths()
    passband_deviation = _passband_deviation_db(duration_seconds)
    stopband_mirror = _stopband_mirror_dbfs(duration_seconds)
    thd_plus_n = _thd_plus_n_dbfs(duration_seconds)
    checks = {
        "passband": passband_deviation <= MAX_PASSBAND_DEVIATION_DB,
        "stopband": stopband_mirror < MAX_STOPBAND_MIRROR_DBFS,
        "thd_plus_n": thd_plus_n < MAX_THD_PLUS_N_DBFS,
    }
    status = "pass" if all(checks.values()) else "fail"
    if status == "pass":
        recommendation = (
            f"Selected {backend} SRC meets the measured offline mastering thresholds."
        )
    elif backend == "scipy" and not soxr_available():
        recommendation = (
            "Selected SciPy SRC misses one or more offline mastering thresholds; "
            "install Audio Studio's mastering extra for the optional soxr backend."
        )
    elif backend == "scipy":
        recommendation = (
            "Selected SciPy SRC misses one or more offline mastering thresholds; "
            "unset AUDIO_STUDIO_SRC or set it to soxr to select the available VHQ path."
        )
    else:
        recommendation = (
            "Selected soxr VHQ SRC misses one or more offline mastering thresholds; "
            "keep the source sample rate for the final master and inspect this report."
        )

    return {
        "schema_version": 2,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "implementation": paths[backend],
        "src_paths": paths,
        "selection": os.environ.get("AUDIO_STUDIO_SRC", "automatic") or "automatic",
        "source_sample_rate_hz": SOURCE_RATE,
        "target_sample_rate_hz": TARGET_RATE,
        "stimulus": {
            "kind": "logarithmic sine sweep",
            "duration_seconds": duration_seconds,
            "passband_hz": [20.0, 20_000.0],
            "stopband_hz": [24_000.0, 46_000.0],
            "thd_plus_n_tone_hz": 1_000.0,
        },
        "passband_peak_deviation_db": passband_deviation,
        "stopband_mirror_dbfs": stopband_mirror,
        "thd_plus_n_dbfs": thd_plus_n,
        "thresholds": {
            "passband_peak_deviation_db_max": MAX_PASSBAND_DEVIATION_DB,
            "stopband_mirror_dbfs_max": MAX_STOPBAND_MIRROR_DBFS,
            "thd_plus_n_dbfs_max": MAX_THD_PLUS_N_DBFS,
        },
        "checks": checks,
        "status": status,
        "recommendation": recommendation,
    }


def write_report(report: dict[str, Any], output: Path) -> Path:
    """Write ``report`` as stable, human-readable JSON."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--duration",
        type=float,
        default=DEFAULT_DURATION_SECONDS,
        help="duration of each sine-sweep probe in seconds",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"JSON output path (default: {DEFAULT_OUTPUT})",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    report = measure_src_quality(duration_seconds=args.duration)
    write_report(report, args.output)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
