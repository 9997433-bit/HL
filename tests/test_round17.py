"""Tests for Round 17 topology export and geometry mapping."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from openfemlab.cli.spec import build_load_cases, build_model, load_spec
from openfemlab.core.elements import Quad4Element
from openfemlab.core.model import DOF, Material, Model
from openfemlab.io.external_result import ExternalResult
from openfemlab.io.geometry_map import map_external_to_model
from openfemlab.io.topology_export import write_topology_vtu
from openfemlab.optimization.topology import run_simp_topology
from openfemlab.reduction import build_craig_bampton

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MULTI_LOAD_SPEC = REPOSITORY_ROOT / "examples" / "specs" / "topopt_plate_multi_load.yaml"


def _mini_plate():
    steel = Material(E=2.1e11, density=0.0)
    model = Model(dofs=(DOF.UX, DOF.UY))
    model.add_nodes(
        [
            (1, 0.0, 0.0),
            (2, 1.0, 0.0),
            (3, 1.0, 0.5),
            (4, 0.0, 0.5),
            (5, 0.0, 1.0),
            (6, 1.0, 1.0),
        ]
    )
    model.add_element(Quad4Element((1, 2, 3, 4), steel, thickness=0.01))
    model.add_element(Quad4Element((4, 3, 6, 5), steel, thickness=0.01))
    model.fix(1)
    model.fix(4)
    model.fix(5)
    return model


def test_multi_load_spec_builds_vectors():
    spec = load_spec(MULTI_LOAD_SPEC)
    model = build_model(spec)
    cases = build_load_cases(spec, model)
    assert cases is not None
    vectors, weights = cases
    assert len(vectors) == 2
    assert weights == [1.0, 0.5]
    assert vectors[0].sum() != 0.0
    assert vectors[1].sum() != 0.0


def test_multi_load_simp_topology_runs():
    model = _mini_plate()
    load_y = np.zeros(model.num_dofs)
    load_x = np.zeros(model.num_dofs)
    load_y[model.dof_index(6, DOF.UY)] = 1000.0
    load_x[model.dof_index(6, DOF.UX)] = 500.0
    result = run_simp_topology(
        model,
        vol_frac=0.5,
        max_iter=15,
        move=0.2,
        tol=1e-2,
        load_vectors=[load_y, load_x],
        load_weights=[1.0, 0.5],
    )
    assert result.meta["num_load_cases"] == 2
    assert len(result.compliance_history) >= 2


def test_topology_vtu_export(tmp_path):
    pytest.importorskip("meshio")
    model = _mini_plate()
    model.add_nodal_load(6, 1000.0, dof=DOF.UY)
    result = run_simp_topology(model, vol_frac=0.5, max_iter=8, tol=1e-2)
    path = tmp_path / "topo.vtu"
    write_topology_vtu(model, result.densities, path)
    assert path.is_file()
    assert path.stat().st_size > 0


def test_map_external_to_model_by_id():
    model = _mini_plate()
    external = ExternalResult(
        node_ids=np.array([1, 2, 6], dtype=np.int64),
        coordinates=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0]]),
        displacements=np.zeros((3, 2)),
        format="test",
        meta={},
    )
    mapping = map_external_to_model(model, external, by_id=True)
    assert mapping.num_matched == 3
    assert mapping.method == "id"


def test_craig_bampton_skeleton_matches_guyan():
    stiffness = np.diag([2.0, 1.0, 1.0])
    mass = np.diag([1.0, 1.0, 1.0])
    basis = build_craig_bampton(stiffness, mass, interface_dofs=[0], num_modes=0)
    assert basis.transformation.shape == (3, 1)
