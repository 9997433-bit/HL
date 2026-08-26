#!/usr/bin/env python3
"""Run numerical environment, stability, fixture, and boundary-test checks."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FIXTURES = (
    "two_dof_analytic.yaml",
    "ten_dof_chain.yaml",
    "test_modes.yaml",
)


def _check_fixtures() -> dict[str, Any]:
    fixture_dir = ROOT / "tests" / "fixtures"
    files = {
        name: {
            "path": str((fixture_dir / name).relative_to(ROOT)),
            "present": (fixture_dir / name).is_file(),
        }
        for name in REQUIRED_FIXTURES
    }
    return {
        "status": "pass" if all(item["present"] for item in files.values()) else "fail",
        "files": files,
    }


def _run_probe(script_name: str, arguments: Sequence[str] = ()) -> dict[str, Any]:
    command = [
        sys.executable,
        str(ROOT / "tests" / "probes" / script_name),
        "--json",
        *arguments,
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "status": "fail",
            "command": command,
            "error": f"{type(exc).__name__}: {exc}",
        }

    try:
        report: dict[str, Any] = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return {
            "status": "fail",
            "command": command,
            "returncode": completed.returncode,
            "error": f"probe returned invalid JSON: {exc}",
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    if completed.returncode != 0:
        report["status"] = "fail"
    if completed.stderr.strip():
        report["stderr"] = completed.stderr.strip()
    return report


def _run_boundary_tests() -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        str(ROOT / "tests" / "test_boundary.py"),
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "status": "fail",
            "command": command,
            "error": f"{type(exc).__name__}: {exc}",
        }
    return {
        "status": "pass" if completed.returncode == 0 else "fail",
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def run_validation(repeats: int = 25, run_tests: bool = True) -> dict[str, Any]:
    probes = {
        "environment": _run_probe("probe_environment.py"),
        "eigen_stability": _run_probe(
            "probe_eigen_stability.py", ("--repeats", str(repeats))
        ),
        "sensitivity_stability": _run_probe("probe_sensitivity_stability.py"),
    }
    report: dict[str, Any] = {
        "fixtures": _check_fixtures(),
        "probes": probes,
    }
    if run_tests:
        report["boundary_tests"] = _run_boundary_tests()

    statuses = [report["fixtures"]["status"]]
    statuses.extend(probe["status"] for probe in probes.values())
    if run_tests:
        statuses.append(report["boundary_tests"]["status"])
    report["status"] = "pass" if all(status == "pass" for status in statuses) else "fail"
    return report


def _print_human(report: dict[str, Any]) -> None:
    print(f"installation validation: {report['status'].upper()}")
    print(f"  fixtures: {report['fixtures']['status'].upper()}")
    for name, probe in report["probes"].items():
        print(f"  {name}: {probe['status'].upper()}")
        if "error" in probe:
            print(f"    {probe['error']}")
    if "boundary_tests" in report:
        boundary = report["boundary_tests"]
        print(f"  boundary_tests: {boundary['status'].upper()}")
        if boundary.get("stdout"):
            for line in boundary["stdout"].splitlines():
                print(f"    {line}")
        if boundary.get("stderr"):
            for line in boundary["stderr"].splitlines():
                print(f"    {line}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repeats",
        type=int,
        default=25,
        help="number of repeated generalized eigenvalue solves",
    )
    parser.add_argument(
        "--skip-boundary-tests",
        action="store_true",
        help="run only fixture and numerical probes",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    args = parser.parse_args(argv)
    if args.repeats < 2:
        parser.error("--repeats must be at least 2")

    report = run_validation(args.repeats, not args.skip_boundary_tests)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_human(report)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
