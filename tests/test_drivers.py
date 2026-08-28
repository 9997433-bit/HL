"""Licence-free driver contract tests (dry-run argv / cwd)."""

from __future__ import annotations

from pathlib import Path

import pytest

from openfemlab.io import FormatError
from openfemlab.io.drivers.abaqus import abaqus_command, run_abaqus
from openfemlab.io.drivers.ansys import ansys_command, run_ansys
from openfemlab.io.drivers.nastran import nastran_command, run_nastran


def test_nastran_dry_run_returns_planned_command(tmp_path: Path):
    deck = tmp_path / "rod.bdf"
    deck.write_text("ENDDATA\n", encoding="utf-8")
    result = run_nastran(deck, executable="/usr/bin/nastran", dry_run=True)
    assert result.exit_code == 0
    assert result.command == nastran_command(deck, executable="/usr/bin/nastran")
    assert result.command[-1] == "rod.bdf"
    assert result.work_dir == str(deck.parent.resolve())


def test_ansys_dry_run_returns_planned_command(tmp_path: Path):
    deck = tmp_path / "job.dat"
    deck.write_text("/EOF\n", encoding="utf-8")
    result = run_ansys(deck, executable="/usr/bin/ansys", dry_run=True)
    assert result.command == ansys_command(deck, executable="/usr/bin/ansys")
    assert "-b" in result.command
    assert result.command[-1] == "job.dat"


def test_abaqus_dry_run_returns_planned_command(tmp_path: Path):
    deck = tmp_path / "job.inp"
    deck.write_text("*HEADING\n", encoding="utf-8")
    result = run_abaqus(deck, executable="/usr/bin/abaqus", dry_run=True)
    assert result.command == abaqus_command(deck, executable="/usr/bin/abaqus")
    assert any(part.startswith("input=") for part in result.command)


def test_drivers_reject_missing_input(tmp_path: Path):
    missing = tmp_path / "missing.bdf"
    with pytest.raises(FormatError, match="not found"):
        run_nastran(missing, executable="/usr/bin/nastran", dry_run=True)
