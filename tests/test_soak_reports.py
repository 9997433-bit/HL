"""Schema coverage for the v1.0 playback-soak evidence reports."""

from __future__ import annotations

import json
import math

import pytest

from benchmarks import soak_playback


@pytest.fixture(scope="module")
def soak_reports(tmp_path_factory: pytest.TempPathFactory) -> dict[str, dict]:
    evidence_directory = tmp_path_factory.mktemp("soak-evidence")
    original_directory = soak_playback.EVIDENCE_DIRECTORY
    soak_playback.EVIDENCE_DIRECTORY = evidence_directory
    try:
        exit_code = soak_playback.main(
            ["--duration-sec", "0.05", "--source-seconds", "0.01", "--quiet"]
        )
    finally:
        soak_playback.EVIDENCE_DIRECTORY = original_directory

    assert exit_code == 0
    expected_paths = {
        "callback": evidence_directory / soak_playback.CALLBACK_REPORT_NAME,
        "soak": evidence_directory / soak_playback.SOAK_REPORT_NAME,
    }
    assert all(path.is_file() for path in expected_paths.values())
    return {
        name: json.loads(path.read_text(encoding="utf-8"))
        for name, path in expected_paths.items()
    }


def _assert_common_schema(report: dict, expected_slo_id: str) -> dict:
    assert report["schema_version"] == 1
    assert report["harness"] == "benchmarks/soak_playback.py"
    assert report["mode"] == "accelerated"
    assert report["evidence"] == "headless-proxy"
    assert report["formal_slo_verified"] is True

    config = report["config"]
    assert config["duration_seconds"] == pytest.approx(0.05)
    assert config["sample_rate"] == 48_000
    assert config["block_size"] == 256
    assert config["channels"] == 2

    assert len(report["results"]) == 1
    result = report["results"][0]
    assert result["slo_id"] == expected_slo_id
    assert result["status"] == "pass"
    assert result["threshold_pass"] is True
    assert result["evidence"] == "headless-proxy"
    assert result["formal_slo_verified"] is True
    assert report["summary"] == {
        "proxy_passed": 1,
        "proxy_failed": 0,
        "formal_slos_verified": 1,
    }
    return result


def test_callback_timing_report_schema(soak_reports: dict[str, dict]) -> None:
    result = _assert_common_schema(soak_reports["callback"], "callback-p99")
    measured = result["measured"]

    assert measured["callbacks_measured"] > 0
    assert math.isfinite(measured["callback_p50_ms"])
    assert math.isfinite(measured["callback_p99_ms"])
    assert 0.0 <= measured["callback_p50_ms"] <= measured["callback_p99_ms"]
    assert measured["callback_p99_ms"] <= result["threshold"]["callback_p99_ms_max"]
    assert measured["underrun_ratio"] == measured["underrun_frame_ratio"]
    assert 0.0 <= measured["underrun_ratio"] <= 1.0


def test_soak_30min_report_schema(soak_reports: dict[str, dict]) -> None:
    result = _assert_common_schema(soak_reports["soak"], "playback-30m")
    measured = result["measured"]

    assert measured["blocks_rendered"] > 0
    assert measured["frames_rendered"] > 0
    assert measured["audio_seconds_rendered"] >= 0.05
    assert 0.0 <= measured["underrun_frame_ratio"] <= 1.0
    callback_timing = measured["callback_timing"]
    assert 0.0 <= callback_timing["p50_ms"] <= callback_timing["p99_ms"]
    assert callback_timing["median_ms"] == callback_timing["p50_ms"]
