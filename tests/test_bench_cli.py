"""CLI bench command tests."""

from __future__ import annotations

from openfemlab.cli.main import main


def test_bench_modal_runs():
    assert main(["--no-color", "bench", "modal", "--sizes", "20", "--repeats", "1"]) == 0
