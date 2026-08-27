"""Schema and honesty checks for the formal C2 recording-soak evidence."""

from __future__ import annotations

import json
import math
from pathlib import Path

REPORT_PATH = (
    Path(__file__).resolve().parents[1]
    / ".agent_workspace"
    / "round3"
    / "recording-stability-report.json"
)


def _load_report() -> dict:
    assert REPORT_PATH.is_file(), (
        "run `python3 benchmarks/recording_stability_soak.py --formal` "
        "to publish the C2 report"
    )
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def test_recording_stability_report_schema() -> None:
    report = _load_report()

    assert report["schema_version"] == 1
    assert report["harness"] == "benchmarks/recording_stability_soak.py"
    assert report["checklist_item"] == "C2"
    assert report["mode"] == "wall-clock"
    assert report["accelerated"] is False
    assert report["evidence"] == "direct-portaudio-pulseaudio"
    assert report["environment"]["backend"] == "SoundDeviceRecorder"
    assert report["environment"]["pulse_server_name"] == "pulseaudio"
    assert report["source"]["type"] == "pulseaudio-null-sink-monitor"
    assert report["source"]["monitor_source"].endswith(".monitor")

    results = report["results"]
    assert len(results) == 1
    result = results[0]
    assert result["slo_id"] == "recording-60m"
    assert result["status"] in {"pass", "fail"}
    assert isinstance(result["threshold_pass"], bool)
    assert isinstance(result["formal_slo_verified"], bool)
    assert result["evidence"] == report["evidence"]
    assert result["method"]
    assert result["limitation"]
    assert "No accelerated mode" in result["limitation"]


def test_formal_claim_requires_a_real_full_duration_callback_run() -> None:
    report = _load_report()
    result = report["results"][0]
    measured = result["measured"]
    config = report["config"]

    assert report["formal_slo_verified"] is result["formal_slo_verified"]
    if result["formal_slo_verified"]:
        assert config["formal_requested"] is True
        assert config["duration_seconds"] >= 3_600.0
        assert config["sample_rate"] == 48_000
        assert config["channels"] == 2
        assert measured["wall_clock_seconds"] >= 3_600.0
        assert measured["captured_frames"] >= 3_600 * 48_000
        assert measured["captured_duration_seconds"] >= 3_600.0
        assert measured["callback_count"] > 0
        assert measured["callback_errors"] == 0
        assert measured["xruns"] <= config["max_xruns"]
        assert measured["stream_aborted"] is False
        assert result["status"] == "pass"
        assert result["threshold_pass"] is True


def test_report_proves_the_complete_recording_and_bwf_paths() -> None:
    report = _load_report()
    result = report["results"][0]
    measured = result["measured"]
    signal = measured["source_signal"]

    assert measured["captured_frames"] == measured["output_file_frames"]
    assert measured["output_file_sample_rate"] == 48_000
    assert measured["output_file_channels"] == 2
    assert measured["output_file_subtype"] == "PCM_24"
    assert measured["output_file_bytes"] > measured["captured_frames"] * 2 * 3
    assert measured["output_file_allocated_bytes"] > 0
    assert measured["maximum_rss_mib"] > 0
    assert math.isfinite(measured["finalization_seconds"])
    assert measured["finalization_seconds"] >= 0.0

    assert signal["window_seconds"] > 0.0
    assert signal["first_window_peak"] > 0.01
    assert signal["first_window_rms"] > 0.001
    assert signal["last_window_peak"] > 0.01
    assert signal["last_window_rms"] > 0.001
