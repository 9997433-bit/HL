"""Tests for RBE2 multi-point constraints."""

from __future__ import annotations

from io import StringIO

import numpy as np
import pytest

from openfemlab.core.elements import TrussElement
from openfemlab.core.model import DOF, Material, Model, Section
from openfemlab.core.mpc import parse_nastran_components
from openfemlab.io.nastran import read_bdf
from openfemlab.io.neutral_convert import neutral_to_model
from openfemlab.solver.modal import ModalSolver

STEEL = Material(E=2.1e11, density=7850.0)
ROD = Section(area=1e-4)


def test_parse_nastran_components():
    assert parse_nastran_components("123456") == (
        DOF.UX,
        DOF.UY,
        DOF.UZ,
        DOF.RX,
        DOF.RY,
        DOF.RZ,
    )
    assert parse_nastran_components(123) == (DOF.UX, DOF.UY, DOF.UZ)


def test_rbe2_axial_tie_matches_single_bar():
    """A tied tip node adds no stiffness; only the master segment carries load."""

    ref = Model(dofs=(DOF.UX,), name="ref")
    ref.add_nodes([(1, 0.0), (2, 1.0)])
    ref.add_element(TrussElement((1, 2), STEEL, ROD))
    ref.fix(1)

    tied = Model(dofs=(DOF.UX,), name="tied")
    tied.add_nodes([(1, 0.0), (2, 1.0), (3, 2.0)])
    tied.add_element(TrussElement((1, 2), STEEL, ROD))
    tied.add_element(
        TrussElement((2, 3), Material(E=STEEL.E, density=0.0), ROD)
    )
    tied.fix(1)
    tied.tie_rbe2(2, [3], components=(DOF.UX,))

    f_ref = ModalSolver(ref).solve(num_modes=1).frequencies[0]
    f_tied = ModalSolver(tied).solve(num_modes=1).frequencies[0]
    assert f_tied == pytest.approx(f_ref, rel=1e-6)


def test_rbe2_planar_rotation_coupling():
    model = Model(dofs=(DOF.UX, DOF.UY, DOF.RZ))
    model.add_node(1, 0.0, 0.0)
    model.add_node(2, 1.0, 0.0)
    model.add_grounded_spring(1, 1.0, DOF.RZ)
    model.tie_rbe2(1, [2], components=(DOF.UX, DOF.UY))

    system = model.assemble()
    assert system.num_free_dofs == 4
    trial = np.zeros(system.num_free_dofs)
    trial[2] = 0.01  # master RZ in retained ordering
    full = system.expand(trial)

    assert full[model.dof_index(1, DOF.RZ)] == pytest.approx(0.01)
    assert full[model.dof_index(2, DOF.UY)] == pytest.approx(0.01)
    assert full[model.dof_index(2, DOF.UX)] == pytest.approx(0.0)


def test_bdf_rbe2_is_applied_in_neutral_to_model():
    source = StringIO(
        """BEGIN BULK
GRID,1,,0.,0.,0.
GRID,2,,1.,0.,0.
GRID,3,,2.,0.,0.
MAT1,1,2.1+11,,0.3,7850.
PROD,1,1,1.E-4
CROD,10,1,1,2
CROD,11,1,2,3
RBE2,100,2,1,3
ENDDATA
"""
    )
    neutral = read_bdf(source)
    model = neutral_to_model(
        neutral,
        material=STEEL,
        section=ROD,
        dofs=(DOF.UX,),
    )
    model.fix(1)
    assert len(model.rbe2_ties) == 1
    assert model.rbe2_ties[0].master == 2
    assert model.rbe2_ties[0].slaves == (3,)

    shape = ModalSolver(model).solve(num_modes=1).mode_shapes[:, 0]
    assert shape[model.dof_index(2, DOF.UX)] == pytest.approx(
        shape[model.dof_index(3, DOF.UX)]
    )


def test_rbe2_rejects_constrained_slave():
    model = Model(dofs=(DOF.UX,))
    model.add_nodes([(1, 0.0), (2, 1.0)])
    model.add_element(TrussElement((1, 2), STEEL, ROD))
    model.fix(2)
    model.tie_rbe2(1, [2], components=(DOF.UX,))
    with pytest.raises(Exception, match="already constrained"):
        model.assemble()


def test_rbe3_dependent_is_weighted_average():
    model = Model(dofs=(DOF.UX,))
    model.add_nodes([(1, 0.0), (2, 1.0), (3, 0.5)])
    model.add_element(TrussElement((1, 2), STEEL, ROD))
    model.fix(1)
    model.tie_rbe3(3, [1, 2], components=(DOF.UX,), weight=1.0)

    system = model.assemble()
    trial = np.ones(system.num_free_dofs)
    full = system.expand(trial)
    assert full[model.dof_index(1, DOF.UX)] == pytest.approx(0.0)
    assert full[model.dof_index(2, DOF.UX)] == pytest.approx(1.0)
    assert full[model.dof_index(3, DOF.UX)] == pytest.approx(0.5)


def test_bdf_rbe3_is_applied_in_neutral_to_model():
    source = StringIO(
        """BEGIN BULK
GRID,1,,0.,0.,0.
GRID,2,,1.,0.,0.
GRID,3,,0.5,0.,0.
MAT1,1,2.1+11,,0.3,7850.
PROD,1,1,1.E-4
CROD,10,1,1,2
RBE3,200,3,1,1.0,1,1,2
ENDDATA
"""
    )
    neutral = read_bdf(source)
    model = neutral_to_model(neutral, material=STEEL, section=ROD, dofs=(DOF.UX,))
    model.fix(1)
    assert len(model.rbe3_ties) == 1
    assert model.rbe3_ties[0].dependent == 3
    shape = ModalSolver(model).solve(num_modes=1).mode_shapes[:, 0]
    assert shape[model.dof_index(3, DOF.UX)] == pytest.approx(
        0.5 * (shape[model.dof_index(1, DOF.UX)] + shape[model.dof_index(2, DOF.UX)])
    )
