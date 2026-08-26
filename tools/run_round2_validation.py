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
for search_path in (REPOSITORY_ROOT, REPOSITORY_ROOT / "audio-studio"):
    if str(search_path) not in sys.path:
        sys.path.insert(0, str(search_path))

from benchmarks.slo import run_slo_suite
from tools.ebu_r128 import integrated_loudness, loudness_range
from tools.ebu_vectors import (
    SAMPLE_RATE,
    TECH_3341_VECTORS,
    TECH_3342_VECTORS,
    synthesize_segments,
)

try:  # The product meter is measured alongside the oracle when it is importable.
    from audio_studio.dsp.loudness import LoudnessMeter
except ImportError:  # pragma: no cover - reported in the JSON rather than raised
    LoudnessMeter = None

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


def _product_integrated(audio: Any) -> float | None:
    if LoudnessMeter is None:
        return None
    return LoudnessMeter(SAMPLE_RATE).integrated(audio, channels_last=True)


def _product_lra(audio: Any) -> float | None:
    if LoudnessMeter is None:
        return None
    return LoudnessMeter(SAMPLE_RATE).loudness_range(audio, channels_last=True)


def _case(
    case_id: str,
    expected: float,
    tolerance: float,
    oracle: float,
    product: float | None,
    expected_key: str,
) -> dict[str, Any]:
    """One vector's result for both meters, plus the verdict for each."""
    entry: dict[str, Any] = {
        "case_id": case_id,
        expected_key: expected,
        "tolerance_lu": tolerance,
        "oracle_lu": round(oracle, 6),
        "oracle_error_lu": round(oracle - expected, 6),
        "oracle_status": "pass" if abs(oracle - expected) <= tolerance else "fail",
    }
    if product is None:
        entry["product_status"] = "not-measured"
        return entry
    entry["product_lu"] = round(product, 6)
    entry["product_error_lu"] = round(product - expected, 6)
    entry["product_status"] = "pass" if abs(product - expected) <= tolerance else "fail"
    return entry


def _compliance_measurements() -> dict[str, Any]:
    tech_3341 = []
    for vector in TECH_3341_VECTORS:
        audio = synthesize_segments(vector.segments)
        tech_3341.append(
            _case(
                vector.case_id,
                vector.expected_integrated_lufs,
                vector.tolerance_lu,
                integrated_loudness(audio, SAMPLE_RATE),
                _product_integrated(audio),
                "expected_lufs",
            )
        )

    tech_3342 = []
    for vector in TECH_3342_VECTORS:
        audio = synthesize_segments(vector.segments)
        tech_3342.append(
            _case(
                vector.case_id,
                vector.expected_lra_lu,
                vector.tolerance_lu,
                loudness_range(audio, SAMPLE_RATE),
                _product_lra(audio),
                "expected_lra_lu",
            )
        )

    statuses = [
        case[key]
        for cases in (tech_3341, tech_3342)
        for case in cases
        for key in ("oracle_status", "product_status")
    ]
    return {
        "oracle": "tools.ebu_r128 (independent test oracle)",
        "product_meter_status": (
            "not-importable"
            if LoudnessMeter is None
            else "audio_studio.dsp.loudness.LoudnessMeter"
        ),
        "product_compliance_claimed": LoudnessMeter is not None
        and all(status == "pass" for status in statuses),
        "tech_3341": tech_3341,
        "tech_3342": tech_3342,
    }


def build_report(work_dir: Path) -> dict[str, Any]:
    pytest_result = _run_pytest()
    with tempfile.TemporaryDirectory(prefix="slo-round2-", dir=work_dir) as temporary:
        slo = run_slo_suite(Path(temporary), quick=False)
    compliance = _compliance_measurements()
    compliance_passed = all(
        case[key] in ("pass", "not-measured")
        for standard in ("tech_3341", "tech_3342")
        for case in compliance[standard]
        for key in ("oracle_status", "product_status")
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
            (
                "EBU values are measured twice: by the independent oracle and by "
                "the product meter. A vector only one of them passes is a defect."
            ),
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
