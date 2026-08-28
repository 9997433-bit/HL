"""Tests for Round 18 CMS and stress-constrained topology."""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.core.elements import Quad4Element
from openfemlab.core.model import DOF, Material, Model
from openfemlab.optimization.stress import (
    element_von_mises_stresses,
    stress_p_norm,
)
from openfemlab.optimization.topology import run_simp_topology
from openfemlab.reduction import build_craig_bampton, reduced_craig_bampton_matrices


def test_craig_bampton_includes_fixed_interface_modes():
    stiffness = np.diag([2.0, 1.0, 1.0])
    mass = np.diag([1.0, 1.0, 1.0])
    basis = build_craig_bampton(stiffness, mass, interface_dofs=[0], num_modes=1)
    assert basis.n_constraint_modes == 1
    assert basis.n_fixed_interface_modes == 1
    assert basis.transformation.shape == (3, 2)
    assert basis.fixed_interface_frequencies_hz.size == 1
    k_red, m_red = reduced_craig_bampton_matrices(basis, stiffness, mass)
    assert k_red.shape == (2, 2)
    assert m_red.shape == (2, 2)


def test_stress_p_norm_is_zero_when_below_limit():
    stresses = np.array([1.0e6, 2.0e6], dtype=float)
    volumes = np.array([1.0, 1.0], dtype=float)
    measure = stress_p_norm(stresses, volumes, limit=5.0e6, exponent=4.0)
    assert measure < 0.0


def test_stress_constrained_topology_runs():
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
    result = run_simp_topology(
        model,
        vol_frac=0.5,
        max_iter=12,
        move=0.2,
        tol=1e-2,
        filter_radius=0.75,
        stress_limit=5.0e8,
        stress_p=4.0,
    )
    assert len(result.stress_history) == len(result.compliance_history)
    assert result.meta["stress_limit"] == 5.0e8


def test_element_von_mises_on_quad4():
    steel = Material(E=2.1e11, density=0.0, nu=0.3)
    model = Model(dofs=(DOF.UX, DOF.UY))
    model.add_nodes([(1, 0.0, 0.0), (2, 1.0, 0.0), (3, 1.0, 0.5), (4, 0.0, 0.5)])
    model.add_element(Quad4Element((1, 2, 3, 4), steel, thickness=0.01))
    model.fix(1)
    model.add_nodal_load(3, 1000.0, dof=DOF.UY)
    from openfemlab.solver.static import StaticSolver

    displacement = StaticSolver(model).solve().displacements
    vm = element_von_mises_stresses(model, displacement)
    assert vm.shape == (1,)
    assert vm[0] > 0.0
