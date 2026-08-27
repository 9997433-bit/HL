"""Opt-in OP2 corpus tests over real Nastran output."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

from openfemlab.io import list_op2_tables, read_op2, read_op2_modes
from openfemlab.io.nastran import read_bdf

CORPUS_ENV = "OPENFEMLAB_OP2_CORPUS"


def _corpus_files() -> list[Path]:
    root = os.environ.get(CORPUS_ENV)
    if not root:
        return []
    directory = Path(root)
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.rglob("*.op2") if path.is_file())


def _assert_geometry_matches_bdf(op2_path: Path, bdf_path: Path) -> None:
    bdf_model = read_bdf(bdf_path)
    op2_model = read_op2(op2_path)

    np.testing.assert_array_equal(bdf_model.node_ids, op2_model.node_ids)
    np.testing.assert_allclose(bdf_model.nodes, op2_model.nodes)
    assert list(bdf_model.elements) == list(op2_model.elements)
    for element_type in bdf_model.elements:
        np.testing.assert_array_equal(
            bdf_model.elements[element_type], op2_model.elements[element_type]
        )
        np.testing.assert_array_equal(
            bdf_model.element_property_ids[element_type],
            op2_model.element_property_ids[element_type],
        )


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


@pytest.mark.parametrize("path", _corpus_files())
def test_corpus_op2_geometry_matches_sidecar_bdf_when_present(path: Path) -> None:
    sidecar = path.with_suffix(".bdf")
    if not sidecar.is_file():
        pytest.skip(f"{path.name} has no sidecar {sidecar.name}")
    names = set(list_op2_tables(path))
    if "GEOM1" not in names:
        pytest.skip(f"{path.name} has no GEOM1 block")
    _assert_geometry_matches_bdf(path, sidecar)
