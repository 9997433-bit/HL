"""Acceptance gates for IO export surface."""

from __future__ import annotations

from ._support import criterion


@criterion("AC-IO-005")
def test_op2_readers_are_exported_from_openfemlab_io() -> None:
    import openfemlab.io as io

    for name in ("list_op2_tables", "read_op2", "read_op2_modes"):
        assert hasattr(io, name)
        assert name in io.__all__
