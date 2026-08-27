"""Run the Round 3 SOTA acceptance suite and emit a machine-readable report."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE_TEST = "tests/acceptance/test_sota_checklist.py"
CASE_NAME = re.compile(r"^test_sota_checklist_item\[(?P<case_id>[^\]]+)\]$")


def _git_revision() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def _binding_guard() -> dict:
    matches: list[str] = []
    for path in sorted((REPOSITORY_ROOT / "audio-studio").rglob("*.py")):
        if ".venv" in path.parts:
            continue
        if "PyQt6" in path.read_text(encoding="utf-8"):
            matches.append(str(path.relative_to(REPOSITORY_ROOT)))
    return {
        "command": "! grep -rn PyQt6 audio-studio/",
        "status": "pass" if not matches else "fail",
        "matches": matches,
    }


def _case_status(testcase: ET.Element) -> tuple[str, str | None]:
    for child_name, status in (("failure", "failed"), ("error", "error"), ("skipped", "skipped")):
        child = testcase.find(child_name)
        if child is None:
            continue
        message = child.get("message") or (child.text or "").strip() or None
        if child_name == "skipped" and (
            child.get("type") == "pytest.xfail" or (message and message.startswith("reason: "))
        ):
            return "xfail", message
        return status, message
    return "passed", None


def _parse_junit(path: Path) -> list[dict]:
    root = ET.parse(path).getroot()
    results: list[dict] = []
    for testcase in root.iter("testcase"):
        match = CASE_NAME.match(testcase.get("name", ""))
        if not match:
            continue
        status, detail = _case_status(testcase)
        result = {
            "case_id": match.group("case_id"),
            "status": status,
            "duration_seconds": round(float(testcase.get("time", "0")), 6),
        }
        if detail:
            result["detail"] = detail
        results.append(result)
    return sorted(results, key=lambda item: item["case_id"])


def run(output: Path) -> int:
    with tempfile.TemporaryDirectory(prefix="round3-acceptance-") as temporary:
        junit_path = Path(temporary) / "pytest.xml"
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            ACCEPTANCE_TEST,
            f"--junitxml={junit_path}",
        ]
        completed = subprocess.run(
            command,
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            check=False,
            text=True,
        )
        cases = _parse_junit(junit_path) if junit_path.is_file() else []

    summary = Counter(case["status"] for case in cases)
    binding_guard = _binding_guard()
    complete = len(cases) == 30
    validation_passed = completed.returncode == 0 and complete and binding_guard["status"] == "pass"
    report = {
        "schema_version": 1,
        "round": 3,
        "scope": "CI repair and fable SOTA checklist acceptance automation",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "git_revision": _git_revision(),
        "validation_status": "pass" if validation_passed else "fail",
        "sota_claimed": validation_passed and summary["xfail"] == 0,
        "checklist": {
            "source_top_level_bullets": 29,
            "automated_items": len(cases),
            "counting_note": (
                "The combined Tech 3341 loudness/true-peak bullet is split into "
                "two independent checks, yielding 30 automated items."
            ),
            "summary": {
                "passed": summary["passed"],
                "expected_gaps": summary["xfail"],
                "failed": summary["failed"],
                "errors": summary["error"],
                "skipped": summary["skipped"],
            },
            "cases": cases,
        },
        "binding_guard": binding_guard,
        "pytest": {
            "command": command,
            "return_code": completed.returncode,
            "status": "pass" if completed.returncode == 0 else "fail",
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        },
        "caveats": [
            "Xfails are audited product/evidence gaps, not acceptance passes.",
            "Cloud/headless checks do not certify hardware audio or manual UI requirements.",
            "sota_claimed remains false until every xfail is resolved and reviewed.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"Round 3 acceptance: {summary['passed']} passed, "
        f"{summary['xfail']} expected gaps, {summary['failed']} failed; report={output}"
    )
    return 0 if validation_passed else (completed.returncode or 1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT / ".agent_workspace/round3/ci-acceptance-report.json",
    )
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else REPOSITORY_ROOT / args.output
    return run(output)


if __name__ == "__main__":
    raise SystemExit(main())
