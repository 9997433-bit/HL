"""Tests for linear static analysis."""

from __future__ import annotations

import pytest

from openfemlab.core.elements import TrussElement
from openfemlab.core.model import DOF, Material, Model, Section
from openfemlab.io import read_bdf
from openfemlab.io.neutral_convert import neutral_to_model
from openfemlab.solver.static import StaticSolver


def test_cantilever_truss_static():
    steel = Material(E=2.0e11, density=0.0)
    section = Section(area=1e-4)
    model = Model(dofs=(DOF.UX,))
    model.add_nodes([(0, 0.0), (1, 1.0)])
    model.add_element(TrussElement((0, 1), steel, section))
    model.fix(0)
    model.add_nodal_load(1, 1000.0)
    result = StaticSolver(model).solve()
    expected = 1000.0 / (steel.E * section.area) * 1.0
    assert result.displacements[-1] == pytest.approx(expected, rel=1e-6)


def test_bdf_force_import(tmp_path):
    bdf = tmp_path / "force.bdf"
    bdf.write_text(
        "\n".join(
            [
                "GRID,1,,0.,0.,0.",
                "GRID,2,,1.,0.,0.",
                "MAT1,1,2.1e11,,0.3,7850.",
                "PROD,1,1,1.e-4",
                "CROD,1,1,1,2",
                "FORCE,1,2,,1000.,1.,0.,0.",
            ]
        )
    )
    imported = neutral_to_model(read_bdf(bdf), material=Material(2.1e11, 7850.0))
    assert imported.nodal_loads
    assert any(abs(value) > 0.0 for value in imported.nodal_loads.values())
