"""Tests for Abaqus ODB NPZ reader."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from openfemlab.io.external_result import ExternalResult
from openfemlab.io.odb import read_odb_npz, sidecar_npz_path
from openfemlab.io.results_locator import read_solver_result


def test_read_odb_npz_fixture(tmp_path: Path):
    archive = tmp_path / "job.odb.openfemlab.npz"
    payload = ExternalResult(
        node_ids=np.array([1, 2], dtype=np.int64),
        coordinates=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]], dtype=float),
        displacements=np.array([[0.0, 0.0, 0.0], [0.0, -0.01, 0.0]], dtype=float),
        format="abaqus-odb",
        meta={"source": "synthetic"},
    )
    np.savez(archive, **payload.to_npz_dict())
    result = read_odb_npz(archive)
    assert result.num_nodes == 2
    assert result.displacements[1, 1] == pytest.approx(-0.01)


def test_sidecar_path_and_loader(tmp_path: Path):
    odb = tmp_path / "job.odb"
    odb.write_bytes(b"stub")
    cache = sidecar_npz_path(odb)
    payload = ExternalResult(
        node_ids=np.array([1], dtype=np.int64),
        coordinates=np.array([[0.0, 0.0, 0.0]], dtype=float),
        displacements=np.array([[0.001, 0.0, 0.0]], dtype=float),
        format="abaqus-odb",
        meta={},
    )
    np.savez(cache, **payload.to_npz_dict())
    loaded = read_solver_result(cache)
    assert loaded.displacements[0, 0] == pytest.approx(0.001)
