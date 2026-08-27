"""Contract tests for host-native screen-reader walkthrough harnesses."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import accessibility_walkthrough_macos as macos_harness
from tools import accessibility_walkthrough_windows as windows_harness
from tools.accessibility_report_schema import REPORT_SCHEMA, validate_report_schema

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
LINUX_REPORT_PATH = (
    REPOSITORY_ROOT / ".agent_workspace/round3/accessibility-report.json"
)


def test_host_harness_files_and_shared_schema_exist() -> None:
    expected = {
        REPOSITORY_ROOT / "tools/accessibility_report_schema.py",
        REPOSITORY_ROOT / "tools/accessibility_walkthrough_windows.py",
        REPOSITORY_ROOT / "tools/accessibility_walkthrough_macos.py",
    }
    assert all(path.is_file() for path in expected)
    assert windows_harness.REPORT_SCHEMA is REPORT_SCHEMA
    assert macos_harness.REPORT_SCHEMA is REPORT_SCHEMA


@pytest.mark.parametrize(
    ("harness", "platform_name", "required_phrase"),
    [
        (windows_harness, "windows", "requires Windows + NVDA"),
        (macos_harness, "macos", "requires macOS + VoiceOver"),
    ],
)
def test_host_gate_reports_match_the_canonical_top_level_schema(
    harness: object, platform_name: str, required_phrase: str
) -> None:
    report = harness.build_gated_report([required_phrase])

    validate_report_schema(report)
    assert set(report) == set(REPORT_SCHEMA)
    assert report["status"] == "not-run"
    assert report["wcag_2_2_aa"] == "not-run"
    assert report["screen_reader_platforms_passed"] == 0
    target = next(
        row for row in report["platforms"] if row["platform"] == platform_name
    )
    assert target["status"] == "not-run"
    assert target["session"] is None
    assert required_phrase in target["reason"]


def test_harness_documentation_names_real_apis_and_honest_limits() -> None:
    windows_source = (
        REPOSITORY_ROOT / "tools/accessibility_walkthrough_windows.py"
    ).read_text(encoding="utf-8")
    macos_source = (
        REPOSITORY_ROOT / "tools/accessibility_walkthrough_macos.py"
    ).read_text(encoding="utf-8")

    assert "pywinauto" in windows_source
    assert "UIA" in windows_source
    assert "NVDA Speech Viewer" in windows_source
    assert "requires Windows + NVDA" in windows_source
    assert "AXUIElementCreateApplication" in macos_source
    assert "kAXFocusedAttribute" in macos_source
    assert "no supported machine-readable speech transcript API" in macos_source
    assert "requires macOS + VoiceOver" in macos_source


def test_committed_linux_orca_report_still_validates() -> None:
    report = json.loads(LINUX_REPORT_PATH.read_text(encoding="utf-8"))

    validate_report_schema(report)
    assert set(report) == set(REPORT_SCHEMA)
    assert report["generated_by"] == "tools/accessibility_walkthrough.py"
    assert report["status"] == "pass"
    assert report["screen_reader_platforms_passed"] == 1
    orca = next(row for row in report["platforms"] if row["platform"] == "linux")
    assert orca["screen_reader"] == "orca"
    assert orca["session"] == "live"
    assert orca["status"] == "pass"
