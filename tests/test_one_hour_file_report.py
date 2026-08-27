"""Schema and honesty checks for the SOTA B2 performance evidence."""

from __future__ import annotations

import json
import math
from pathlib import Path

REPORT_PATH = (
    Path(__file__).resolve().parents[1]
    / ".agent_workspace"
    / "round3"
    / "file-performance-report.json"
)
REQUIRED_SLOS = {
    "waveform-open",
    "spectrogram-first-frame",
    "offline-eq-normalize",
}


def _load_report() -> dict:
    assert REPORT_PATH.is_file(), (
        "run `python3 benchmarks/one_hour_file_perf.py --formal` "
        "to publish the B2 report"
    )
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def test_one_hour_file_report_schema() -> None:
    report = _load_report()

    assert report["schema_version"] == 1
    assert report["harness"] == "benchmarks/one_hour_file_perf.py"
    assert report["checklist_item"] == "B2"
    assert report["evidence"] in {"direct-headless", "headless-proxy"}
    assert isinstance(report["formal_slo_verified"], bool)
    assert {"python", "platform", "processor", "qt_platform", "clock"} <= set(
        report["environment"]
    )

    fixture = report["fixture"]
    assert fixture["n_frames"] > 0
    assert fixture["duration_seconds"] > 0
    assert fixture["sample_rate"] == 48_000
    assert fixture["channels"] == 2
    assert fixture["subtype"] == "PCM_16"
    assert fixture["file_size_bytes"] > 44
    assert 0.0 <= fixture["allocated_ratio"]
    assert fixture["peak_sidecar_bytes"] > 0

    results = report["results"]
    assert {item["slo_id"] for item in results} == REQUIRED_SLOS
    assert len(results) == len(REQUIRED_SLOS)
    for item in results:
        assert item["status"] in {"pass", "fail"}
        assert isinstance(item["threshold_pass"], bool)
        assert isinstance(item["formal_slo_verified"], bool)
        assert item["evidence"] in {"direct-headless", "headless-proxy"}
        assert item["title"]
        assert item["scope"]
        assert item["limitation"]
        elapsed = item["measured"]["elapsed_seconds"]
        ceiling = item["threshold"]["elapsed_seconds_max"]
        assert math.isfinite(elapsed) and elapsed >= 0.0
        assert math.isfinite(ceiling) and ceiling > 0.0
        assert item["threshold_pass"] is (elapsed < ceiling)
        assert item["status"] == ("pass" if item["threshold_pass"] else "fail")


def test_formal_claim_requires_full_allocated_run_and_passing_results() -> None:
    report = _load_report()
    results = report["results"]
    formal_results = [item for item in results if item["formal_slo_verified"]]

    assert report["formal_slo_verified"] is (
        len(formal_results) == len(REQUIRED_SLOS)
    )
    if formal_results:
        fixture = report["fixture"]
        assert fixture["duration_seconds"] >= 3_600.0
        assert fixture["n_frames"] >= 3_600 * fixture["sample_rate"]
        assert fixture["allocated_ratio"] >= 0.95
        assert report["evidence"] == "direct-headless"
        assert all(item["status"] == "pass" for item in formal_results)
        assert all(item["evidence"] == "direct-headless" for item in formal_results)


def test_report_proves_each_operation_consumed_real_source_data() -> None:
    report = _load_report()
    fixture_frames = report["fixture"]["n_frames"]
    by_id = {item["slo_id"]: item for item in report["results"]}

    waveform = by_id["waveform-open"]["measured"]
    assert waveform["source_frames"] == fixture_frames
    assert waveform["cached_waveform_frames"] == fixture_frames
    assert waveform["waveform_peak"] > 0.0
    assert waveform["offscreen_paint_completed"] is True

    spectrogram = by_id["spectrogram-first-frame"]["measured"]
    assert spectrogram["source_frames"] == fixture_frames
    assert 0 < spectrogram["viewport_frames"] <= fixture_frames
    assert spectrogram["spectrogram_columns"] > 0
    assert spectrogram["offscreen_paint_completed"] is True

    offline = by_id["offline-eq-normalize"]["measured"]
    assert offline["source_frames"] == fixture_frames
    assert offline["frames_eq_processed"] == fixture_frames
    assert offline["frames_normalized"] == fixture_frames
    assert offline["eq"]["type"] == "ThreeBandEQ"
    assert offline["normalize"]["type"] == "NormalizeEffect"
    assert offline["normalize"]["output_peak_dbfs"] == -1.0
