"""CLI quickstart and report commands."""

from __future__ import annotations

import json
from pathlib import Path

from openfemlab.cli.main import main


def test_quickstart_runs_cleanly():
    assert main(["--no-color", "quickstart"]) == 0


def test_report_from_correlation_json(tmp_path: Path):
    payload = {
        "schema_version": "1.1",
        "summary": {
            "mean_mac": 0.95,
            "min_mac": 0.9,
            "max_abs_freq_error_pct": 1.0,
            "num_pairs": 1,
        },
        "pairs": [],
        "unpaired_test": [],
        "unpaired_fe": [],
        "pairing_method": "optimal",
        "mac_matrix": None,
        "comac": None,
        "dof_labels": None,
        "frf": None,
        "settings": {},
        "meta": {},
    }
    source = tmp_path / "corr.json"
    source.write_text(json.dumps(payload), encoding="utf-8")
    dest = tmp_path / "corr.html"
    assert main(["--no-color", "report", str(source), "-o", str(dest)]) == 0
    assert dest.is_file()
    assert "Modal correlation" in dest.read_text(encoding="utf-8")
