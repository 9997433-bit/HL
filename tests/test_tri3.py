"""TRI3 constant-strain triangle: kernel, patch test, and modal smoke checks."""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.core.elements import Tri3Element, plane_constitutive_matrix
from openfemlab.core.model import DOF, Material, Model
from openfemlab.exceptions import ElementError
from openfemlab.solver.modal import ModalSolver

STEEL = Material(E=2.1e11, density=7850.0, nu=0.3)
UNIT = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=float)


def bound_tri(coords: np.ndarray = UNIT, **kwargs) -> Tri3Element:
    model = Model(dofs=(DOF.UX, DOF.UY), name="tri")
    for index, point in enumerate(np.asarray(coords, dtype=float)):
        model.add_node(index, point)
    return model.add_element(Tri3Element(range(3), STEEL, **kwargs))


def test_tri3_area_and_mass():
    element = bound_tri()
    assert element.area(UNIT) == pytest.approx(0.5)
    assert element.total_mass(UNIT) == pytest.approx(STEEL.density * 1.0 * 0.5)


def test_tri3_rejects_inverted_winding():
    flipped = UNIT[[0, 2, 1]]
    element = bound_tri(flipped)
    with pytest.raises(ElementError, match="non-positive area"):
        element.stiffness_matrix(flipped)


def test_tri3_constant_strain_patch():
    element = bound_tri()
    strain = np.array([1.0e-3, -5.0e-4, 2.0e-4])
    xy = UNIT[:, :2]
    exx, eyy, gxy = strain
    displacements = np.zeros(6)
    displacements[0::2] = exx * xy[:, 0] + 0.5 * gxy * xy[:, 1]
    displacements[1::2] = eyy * xy[:, 1] + 0.5 * gxy * xy[:, 0]
    np.testing.assert_allclose(element.strain(UNIT, displacements), strain, atol=1e-12)
    stress = plane_constitutive_matrix(STEEL) @ strain
    np.testing.assert_allclose(element.stress(UNIT, displacements), stress, atol=1e-6)


def test_tri3_three_rigid_body_modes():
    element = bound_tri()
    k = element.stiffness_matrix(UNIT)
    values = np.linalg.eigvalsh(k)
    assert np.sum(np.abs(values) < 1e-8 * np.max(np.abs(values))) == 3


def test_tri3_modal_plate_smoke():
    model = Model(dofs=(DOF.UX, DOF.UY))
    model.add_nodes([(1, 0.0, 0.0), (2, 1.0, 0.0), (3, 0.0, 1.0), (4, 1.0, 1.0)])
    model.add_element(Tri3Element((1, 2, 4), STEEL, thickness=0.01))
    model.add_element(Tri3Element((1, 4, 3), STEEL, thickness=0.01))
    model.fix(1)
    model.fix(2, (DOF.UY,))
    result = ModalSolver(model).solve(num_modes=3)
    assert result.frequencies[0] > 0.0
    assert result.orthogonality_error() < 1e-8
