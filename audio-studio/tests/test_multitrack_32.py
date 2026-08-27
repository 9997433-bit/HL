"""SOTA B8: direct headless 32-track playback and automation evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from benchmarks.multitrack_32 import (  # noqa: E402
    AUTOMATION_DB_TOLERANCE,
    DEFAULT_REPORT_PATH,
    DEFAULT_TRACKS,
    MIX_ABS_TOLERANCE,
    build_session,
    run_benchmark,
    write_report,
)


@pytest.fixture(scope="module")
def b8_report() -> dict:
    return run_benchmark()


def test_b8_fixture_builds_32_clipped_and_automated_tracks() -> None:
    session, references = build_session()

    assert session.n_tracks == DEFAULT_TRACKS
    assert len(session.clips) == DEFAULT_TRACKS
    assert len(references) == DEFAULT_TRACKS
    assert all(track.n_clips == 1 for track in session.tracks)
    assert all(track.has_automation for track in session.tracks)
    assert all(len(track.automation.points) == 3 for track in session.tracks)


def test_b8_headless_playback_and_automation_meet_direct_thresholds(
    b8_report: dict,
) -> None:
    assert b8_report["checklist_item"] == "B8"
    result = b8_report["results"][0]
    measured = result["measured"]

    assert result["slo_id"] == "32-track"
    assert result["status"] == "pass"
    assert result["threshold_pass"] is True
    assert result["formal_slo_verified"] is True
    assert measured["backend"] == "null"
    assert measured["tracks_built"] == DEFAULT_TRACKS
    assert measured["automated_tracks"] == DEFAULT_TRACKS
    assert measured["frames_delivered"] == b8_report["config"]["frames"]
    assert measured["frames_pulled"] == b8_report["config"]["frames"]
    assert measured["underrun_frames"] == 0
    assert measured["automation_samples_checked"] >= DEFAULT_TRACKS * 10
    assert measured["automation_max_abs_error_db"] <= AUTOMATION_DB_TOLERANCE
    assert measured["mix_max_abs_error"] <= MIX_ABS_TOLERANCE


def test_b8_report_writer_preserves_the_acceptance_schema(
    b8_report: dict, tmp_path: Path
) -> None:
    report_path = tmp_path / "multitrack-report.json"

    write_report(b8_report, report_path)
    restored = json.loads(report_path.read_text(encoding="utf-8"))

    assert restored == b8_report
    assert {item["slo_id"] for item in restored["results"]} == {"32-track"}
    assert all(item["status"] == "pass" for item in restored["results"])
    assert all(item["formal_slo_verified"] is True for item in restored["results"])


def test_committed_b8_evidence_is_a_direct_pass() -> None:
    report = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
    result = report["results"][0]

    assert report["harness"] == "benchmarks/multitrack_32.py"
    assert result["slo_id"] == "32-track"
    assert result["evidence"] == "direct-headless"
    assert result["status"] == "pass"
    assert result["formal_slo_verified"] is True
