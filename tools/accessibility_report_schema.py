"""Shared schema for host-native screen-reader walkthrough reports.

The canonical example is ``.agent_workspace/round3/accessibility-report.json``.
Every host harness emits exactly these top-level fields so reports can be
compared or merged without mistaking a prerequisite gate for assistive-
technology evidence.

``status`` is ``pass`` only when a live screen-reader session passed, ``fail``
when a live session ran but failed a check, and ``not-run`` when the required
host or assistive technology was unavailable.  Likewise, only platform rows
with ``status == "pass"`` and ``session == "live"`` contribute to
``screen_reader_platforms_passed``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPORT_SCHEMA: dict[str, type] = {
    "artifact": str,
    "checklist_item": str,
    "generated_by": str,
    "generated_at": str,
    "status": str,
    "wcag_2_2_aa": str,
    "wcag_evidence": dict,
    "screen_reader_platforms_passed": int,
    "platforms": list,
    "methodology": str,
    "environment": dict,
    "checks": dict,
    "limitations": str,
    "headless_proxy_companion": str,
    "unit_suite": str,
}

PLATFORM_SCHEMA: dict[str, type | tuple[type, ...]] = {
    "platform": str,
    "screen_reader": str,
    "session": (str, type(None)),
    "status": str,
}

PLATFORM_READERS = {
    "linux": "orca",
    "windows": "nvda",
    "macos": "voiceover",
}


def validate_report_schema(report: dict[str, Any]) -> None:
    """Raise ``TypeError``/``ValueError`` for an invalid shared report shape."""
    expected = set(REPORT_SCHEMA)
    actual = set(report)
    if actual != expected:
        raise ValueError(
            f"top-level fields differ: missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )

    for field, expected_type in REPORT_SCHEMA.items():
        value = report[field]
        if field == "screen_reader_platforms_passed" and isinstance(value, bool):
            raise TypeError(f"{field} must be an integer, not bool")
        if not isinstance(value, expected_type):
            raise TypeError(
                f"{field} must be {expected_type.__name__}, got {type(value).__name__}"
            )

    if report["artifact"] != "accessibility-report":
        raise ValueError("artifact must be accessibility-report")
    if report["checklist_item"] != "D4":
        raise ValueError("checklist_item must be D4")
    if report["status"] not in {"pass", "fail", "not-run"}:
        raise ValueError("status must be pass, fail or not-run")
    if report["wcag_2_2_aa"] not in {"pass", "fail", "not-run"}:
        raise ValueError("wcag_2_2_aa must be pass, fail or not-run")
    if not all(isinstance(value, bool) for value in report["checks"].values()):
        raise ValueError("every checks value must be boolean")

    rows = report["platforms"]
    if len(rows) != len(PLATFORM_READERS):
        raise ValueError("platforms must contain Linux, Windows and macOS rows")
    by_platform: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise TypeError("every platform row must be an object")
        for field, expected_type in PLATFORM_SCHEMA.items():
            if field not in row or not isinstance(row[field], expected_type):
                raise TypeError(f"platform row has invalid {field}")
        platform_name = row["platform"]
        if platform_name in by_platform:
            raise ValueError(f"duplicate platform row: {platform_name}")
        by_platform[platform_name] = row
        if row["status"] not in {"pass", "fail", "not-run"}:
            raise ValueError(f"invalid platform status: {row['status']}")
        if row["status"] == "pass" and row["session"] != "live":
            raise ValueError(f"{platform_name} pass must represent a live session")
        if row["status"] == "not-run" and not row.get("reason"):
            raise ValueError(f"{platform_name} not-run row needs a reason")

    if set(by_platform) != set(PLATFORM_READERS):
        raise ValueError("platform rows must be Linux, Windows and macOS")
    for platform_name, screen_reader in PLATFORM_READERS.items():
        if by_platform[platform_name]["screen_reader"] != screen_reader:
            raise ValueError(f"{platform_name} row must identify {screen_reader}")

    passed = sum(row["status"] == "pass" for row in rows)
    if report["screen_reader_platforms_passed"] != passed:
        raise ValueError("screen_reader_platforms_passed does not match platform rows")


def _not_run_wcag_evidence() -> dict[str, Any]:
    """Return the canonical WCAG evidence fields without inventing a result."""
    return {
        "audit": "not run; this report stopped at a host or assistive-technology gate",
        "contrast_pass": None,
        "failing_pairs": [],
        "text_pair_ratios": {},
        "minimum_text_ratio": None,
        "graphic_pair_ratios": {},
        "minimum_graphic_ratio": None,
        "color_safe_colormap": None,
        "success_criteria": {},
        "unit_suites": [],
    }


def build_platform_report(
    *,
    generated_by: str,
    target_platform: str,
    status: str,
    session: str | None,
    reason: str,
    methodology: str,
    environment: dict[str, Any],
    checks: dict[str, bool],
    limitations: str,
    evidence: dict[str, Any] | None = None,
    screen_reader_version: str | None = None,
    wcag_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one host result without attributing unrun platforms as evidence."""
    if target_platform not in PLATFORM_READERS:
        raise ValueError(f"unsupported target platform: {target_platform}")
    if status not in {"pass", "fail", "not-run"}:
        raise ValueError(f"unsupported result status: {status}")

    platform_rows: list[dict[str, Any]] = []
    for platform_name, screen_reader in PLATFORM_READERS.items():
        row: dict[str, Any] = {
            "platform": platform_name,
            "screen_reader": screen_reader,
            "session": None,
            "status": "not-run",
            "reason": f"{screen_reader} is outside this {target_platform} host run",
        }
        if platform_name == target_platform:
            row.update(
                {
                    "screen_reader_version": screen_reader_version,
                    "session": session,
                    "status": status,
                    "reason": reason,
                }
            )
            if evidence is not None:
                row["evidence"] = evidence
        platform_rows.append(row)

    measured_wcag = wcag_evidence or _not_run_wcag_evidence()
    contrast_passed = (
        measured_wcag.get("contrast_pass") is True
        and measured_wcag.get("color_safe_colormap") is True
    )
    report_status = status
    if status == "pass" and not contrast_passed:
        report_status = "fail"

    report = {
        "artifact": "accessibility-report",
        "checklist_item": "D4",
        "generated_by": generated_by,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": report_status,
        "wcag_2_2_aa": (
            "pass" if contrast_passed else "not-run" if wcag_evidence is None else "fail"
        ),
        "wcag_evidence": measured_wcag,
        "screen_reader_platforms_passed": sum(
            row["status"] == "pass" for row in platform_rows
        ),
        "platforms": platform_rows,
        "methodology": methodology,
        "environment": environment,
        "checks": checks,
        "limitations": limitations,
        "headless_proxy_companion": ".agent_workspace/v1.0/screen-reader-evidence.json",
        "unit_suite": "tests/test_accessibility_report.py",
    }
    validate_report_schema(report)
    return report


def write_report(report: dict[str, Any], output: Path) -> None:
    """Validate and atomically replace a report file."""
    validate_report_schema(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)
