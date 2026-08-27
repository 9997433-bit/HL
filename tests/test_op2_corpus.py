"""Opt-in OP2 corpus tests over real Nastran output."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from openfemlab.io import list_op2_tables, read_op2, read_op2_modes

CORPUS_ENV = "OPENFEMLAB_OP2_CORPUS"


def _corpus_files() -> list[Path]:
    root = os.environ.get(CORPUS_ENV)
    if not root:
        return []
    directory = Path(root)
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.rglob("*.op2") if path.is_file())


pytestmark = pytest.mark.skipif(
    not _corpus_files(),
    reason=f"{CORPUS_ENV} unset or contains no .op2 files",
)


@pytest.mark.parametrize("path", _corpus_files())
def test_corpus_op2_lists_tables(path: Path) -> None:
    tables = list_op2_tables(path)
    assert tables, f"{path} carries no OP2 tables"


@pytest.mark.parametrize("path", _corpus_files())
def test_corpus_op2_reads_modes_when_present(path: Path) -> None:
    names = set(list_op2_tables(path))
    if "LAMA" not in names:
        pytest.skip(f"{path.name} has no LAMA block")
    result = read_op2_modes(path)
    assert result.frequencies.size > 0


@pytest.mark.parametrize("path", _corpus_files())
def test_corpus_op2_reads_geometry_when_present(path: Path) -> None:
    names = set(list_op2_tables(path))
    if "GEOM1" not in names:
        pytest.skip(f"{path.name} has no GEOM1 block")
    model = read_op2(path)
    assert model.nodes.size > 0
