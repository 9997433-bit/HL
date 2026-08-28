"""Tests for SIMP topology optimization."""

from __future__ import annotations

from openfemlab.core.elements import Quad4Element
from openfemlab.core.model import DOF, Material, Model
from openfemlab.optimization.topology import run_simp_topology


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


def test_simp_topology_reduces_compliance():
    model = _mini_plate()
    result = run_simp_topology(model, vol_frac=0.5, max_iter=20, move=0.2, tol=1e-2)
    assert result.densities.shape == (2,)
    assert 0.0 < result.mean_density <= 1.0
    assert len(result.compliance_history) >= 2
    assert result.compliance_history[-1] <= result.compliance_history[0]
