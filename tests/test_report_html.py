"""Tests for HTML report generation."""

from __future__ import annotations

from pathlib import Path

from openfemlab.report.html import detect_report_kind, write_html_report


def test_detect_correlation_report():
    payload = {
        "schema_version": "1.1",
        "summary": {
            "mean_mac": 0.95,
            "min_mac": 0.9,
            "max_abs_freq_error_pct": 2.0,
            "num_pairs": 2,
        },
        "pairs": [{"test_index": 0, "fe_index": 0, "mac": 0.99, "freq_error_pct": 0.1}],
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
    assert detect_report_kind(payload) == "correlation"


def test_write_correlation_html(tmp_path: Path):
    payload = {
        "schema_version": "1.1",
        "summary": {
            "mean_mac": 0.95,
            "min_mac": 0.9,
            "max_abs_freq_error_pct": 2.0,
            "num_pairs": 1,
        },
        "pairs": [{"test_index": 0, "fe_index": 0, "mac": 0.99, "freq_error_pct": 0.1}],
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
    out = tmp_path / "corr.html"
    kind = write_html_report(payload, out)
    assert kind == "correlation"
    text = out.read_text(encoding="utf-8")
    assert "Modal correlation" in text
    assert "0.9" in text


def test_write_correction_html(tmp_path: Path):
    payload = {
        "schema_version": "1.0",
        "status": "PASS",
        "stages": [{"stage": "S1", "status": "completed"}],
        "baseline_correlation": {
            "schema_version": "1.1",
            "summary": {"min_mac": 0.5, "max_abs_freq_error_pct": 10.0},
            "pairs": [],
        },
        "final_correlation": {
            "schema_version": "1.1",
            "summary": {"min_mac": 0.99, "max_abs_freq_error_pct": 0.5},
            "pairs": [],
        },
        "parameters": [
            {
                "name": "k1",
                "kind": "stiffness",
                "initial": 1.0,
                "final": 0.9,
                "lower": 0.5,
                "upper": 1.5,
                "change_pct": -10.0,
                "selected": True,
            }
        ],
    }
    out = tmp_path / "fix.html"
    kind = write_html_report(payload, out)
    assert kind == "correction"
    assert "PASS" in out.read_text(encoding="utf-8")
