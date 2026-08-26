#!/usr/bin/env python3
"""Run Round 2 SLO/compliance tests and write the machine-readable report."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from benchmarks.slo import run_slo_suite
from tools.ebu_r128 import integrated_loudness, loudness_range
from tools.ebu_vectors import (
    SAMPLE_RATE,
    TECH_3341_VECTORS,
    TECH_3342_VECTORS,
    synthesize_segments,
)

DEFAULT_OUTPUT = (
    REPOSITORY_ROOT / ".agent_workspace" / "round2" / "slo-compliance-report.json"
)
NEW_TEST_PATHS = (
    "benchmarks/slo",
    "tests/compliance",
    "tests/golden",
)


def _run_pytest() -> dict[str, Any]:
    command = [sys.executable, "-m", "pytest", "-q", *NEW_TEST_PATHS]
    completed = subprocess.run(
        command,
        cwd=REPOSITORY_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "command": command,
        "return_code": completed.returncode,
        "status": "pass" if completed.returncode == 0 else "fail",
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _compliance_measurements() -> dict[str, Any]:
    tech_3341: list[dict[str, Any]] = []
    for vector in TECH_3341_VECTORS:
        audio = synthesize_segments(vector.segments)
        measured = integrated_loudness(audio, SAMPLE_RATE)
        error = measured - vector.expected_integrated_lufs
        tech_3341.append(
            {
                "case_id": vector.case_id,
                "expected_lufs": vector.expected_integrated_lufs,
                "measured_lufs": round(measured, 6),
                "error_lu": round(error, 6),
                "tolerance_lu": 0.1,
                "status": "pass" if abs(error) <= 0.1 else "fail",
            }
        )

    lra_vector = TECH_3342_VECTORS[0]
    lra_audio = synthesize_segments(lra_vector.segments)
    measured_lra = loudness_range(lra_audio, SAMPLE_RATE)
    lra_error = measured_lra - lra_vector.expected_lra_lu
    tech_3342 = [
        {
            "case_id": lra_vector.case_id,
            "expected_lra_lu": lra_vector.expected_lra_lu,
            "measured_lra_lu": round(measured_lra, 6),
            "error_lu": round(lra_error, 6),
            "tolerance_lu": 1.0,
            "status": "pass" if abs(lra_error) <= 1.0 else "fail",
        }
    ]
    return {
        "oracle": "tools.ebu_r128 (independent test oracle)",
        "product_meter_status": "not-available",
        "product_compliance_claimed": False,
        "tech_3341": tech_3341,
        "tech_3342": tech_3342,
    }


def build_report(work_dir: Path) -> dict[str, Any]:
    pytest_result = _run_pytest()
    with tempfile.TemporaryDirectory(prefix="slo-round2-", dir=work_dir) as temporary:
        slo = run_slo_suite(Path(temporary), quick=False)
    compliance = _compliance_measurements()
    compliance_passed = all(
        case["status"] == "pass"
        for standard in ("tech_3341", "tech_3342")
        for case in compliance[standard]
    )
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "round": 2,
        "scope": "SLO and EBU/golden validation infrastructure",
        "validation_status": (
            "pass" if pytest_result["return_code"] == 0 and compliance_passed else "fail"
        ),
        "pytest": pytest_result,
        "slo": slo,
        "compliance": compliance,
        "golden": {
            "status": "covered-by-pytest",
            "formats": ["PCM_16", "PCM_24", "FLOAT"],
            "comparison": "WAV fmt fields and SHA-256 of encoded sample payload",
        },
        "caveats": [
            "Cloud results are headless proxies, not audio-device or UI SLO certification.",
            "EBU values validate the independent oracle; no production loudness meter exists.",
            "Tech 3342 uses its normative ±1 LU tolerance.",
        ],
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    report = build_report(output.parent)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"Wrote {output}", file=sys.stderr)
    return 0 if report["validation_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
