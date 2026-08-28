"""Tests for Round 19 MMA topology and superelement export."""

from __future__ import annotations

import numpy as np

from openfemlab.core.elements import Quad4Element
from openfemlab.core.model import DOF, Material, Model
from openfemlab.io import read_bdf
from openfemlab.io.neutral_convert import neutral_to_model
from openfemlab.optimization.mma import create_mma_state, mma_update
from openfemlab.optimization.topology import run_simp_topology
from openfemlab.reduction import (
    build_craig_bampton,
    reduced_craig_bampton_matrices,
    write_superelement_npz,
)
from openfemlab.reduction.superelement import SuperelementBundle


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
    model.add_nodal_load(6, 1000.0, dof=DOF.UY)
    return model


def test_mma_update_respects_volume_constraint():
    x = np.full(4, 0.8, dtype=float)
    state = create_mma_state(x)
    xmin = np.full(4, 0.001)
    xmax = np.ones(4)
    volumes = np.ones(4)
    f0 = 10.0
    df0 = np.array([1.0, 2.0, 3.0, 4.0], dtype=float)
    constraint_value = float(np.mean(x) - 0.5)
    gradient = volumes / volumes.sum()
    xnew, _ = mma_update(
        x,
        xmin,
        xmax,
        state,
        f0=f0,
        df0dx=df0,
        constraints=[(constraint_value, gradient)],
        move=0.2,
    )
    assert np.all(xnew >= xmin - 1e-12)
    assert np.all(xnew <= xmax + 1e-12)
    assert float(np.mean(xnew)) < float(np.mean(x))


def test_mma_topology_runs():
    model = _mini_plate()
    result = run_simp_topology(
        model,
        vol_frac=0.5,
        max_iter=12,
        move=0.2,
        tol=1e-2,
        optimizer="mma",
    )
    assert result.meta["optimizer"] == "mma"
    assert len(result.compliance_history) >= 1
    assert 0.0 < result.mean_density <= 1.0


def test_mma_and_oc_both_reduce_compliance():
    model = _mini_plate()
    oc = run_simp_topology(
        model,
        vol_frac=0.5,
        max_iter=15,
        move=0.2,
        tol=1e-2,
        optimizer="oc",
    )
    mma = run_simp_topology(
        model,
        vol_frac=0.5,
        max_iter=15,
        move=0.2,
        tol=1e-2,
        optimizer="mma",
    )
    assert oc.compliance_history[-1] <= oc.compliance_history[0]
    assert mma.compliance_history[-1] <= mma.compliance_history[0]


def test_write_superelement_npz(tmp_path):
    stiffness = np.diag([2.0, 1.0, 1.0])
    mass = np.diag([1.0, 1.0, 1.0])
    basis = build_craig_bampton(stiffness, mass, interface_dofs=[0], num_modes=1)
    k_red, m_red = reduced_craig_bampton_matrices(basis, stiffness, mass)
    path = tmp_path / "superelement.npz"
    write_superelement_npz(
        path,
        basis,
        stiffness,
        mass,
        model_name="demo",
        source="test",
    )
    bundle = SuperelementBundle(path)
    assert bundle.kind == "craig_bampton_superelement"
    assert bundle.K_red.shape == k_red.shape
    assert bundle.M_red.shape == m_red.shape
    assert bundle.T.shape == basis.transformation.shape
    assert bundle.interface_dofs.tolist() == [0]


def test_bdf_moment_import(tmp_path):
    bdf = tmp_path / "moment.bdf"
    bdf.write_text(
        "\n".join(
            [
                "GRID,1,,0.,0.,0.",
                "GRID,2,,1.,0.,0.",
                "MAT1,1,2.1e11,,0.3,7850.",
                "PROD,1,1,1.e-4",
                "CROD,1,1,1,2",
                "MOMENT,1,2,,500.,0.,0.,1.",
            ]
        )
    )
    imported = neutral_to_model(
        read_bdf(bdf),
        material=Material(2.1e11, 7850.0),
        dofs=(DOF.UX, DOF.UY, DOF.UZ, DOF.RX, DOF.RY, DOF.RZ),
    )
    assert imported.nodal_loads
    assert any(abs(value) > 0.0 for value in imported.nodal_loads.values())
