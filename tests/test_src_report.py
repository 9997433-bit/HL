"""Regression tests for the reproducible selectable SRC quality report."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from tools.src_report import measure_src_quality, write_report


@pytest.fixture(scope="module")
def src_report() -> dict[str, object]:
    return measure_src_quality(duration_seconds=0.5)


def test_src_report_measures_sweeps_against_mastering_thresholds(
    src_report: dict[str, object],
) -> None:
    implementation = src_report["implementation"]
    stimulus = src_report["stimulus"]
    checks = src_report["checks"]

    assert implementation["backend"] in {
        "scipy.signal.resample_poly",
        "soxr.resample",
    }
    assert src_report["src_paths"]["scipy"]["backend"] == "scipy.signal.resample_poly"
    if implementation["backend"] == "soxr.resample":
        assert src_report["src_paths"]["soxr"]["quality"] == "VHQ"
    assert stimulus["kind"] == "logarithmic sine sweep"
    assert src_report["source_sample_rate_hz"] == 96_000
    assert src_report["target_sample_rate_hz"] == 44_100
    for metric in (
        "passband_peak_deviation_db",
        "stopband_mirror_dbfs",
        "thd_plus_n_dbfs",
    ):
        assert math.isfinite(src_report[metric])

    assert set(checks) == {"passband", "stopband", "thd_plus_n"}
    expected_status = "pass" if all(checks.values()) else "fail"
    assert src_report["status"] == expected_status


def test_report_explains_selected_path_result(
    src_report: dict[str, object],
) -> None:
    backend = src_report["implementation"]["backend"]
    if backend == "scipy.signal.resample_poly":
        assert src_report["status"] == "fail"
        assert "soxr" in src_report["recommendation"]
    else:
        assert backend == "soxr.resample"
        assert src_report["status"] == "pass"
        assert "meets" in src_report["recommendation"]


def test_src_report_json_round_trip(
    tmp_path: Path,
    src_report: dict[str, object],
) -> None:
    target = tmp_path / "src-quality.json"

    assert write_report(src_report, target) == target
    assert json.loads(target.read_text(encoding="utf-8")) == src_report


def test_src_report_rejects_nonpositive_duration() -> None:
    with pytest.raises(ValueError, match="duration_seconds must be positive"):
        measure_src_quality(duration_seconds=0.0)
