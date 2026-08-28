"""Tests for shell element geometric stiffness derivatives."""

from __future__ import annotations

import numpy as np

from openfemlab.core.elements import Quad4Element, Tri3Element
from openfemlab.core.model import DOF, Material, Model


def _check_derivatives(element, coords: np.ndarray, step: float = 1e-6) -> None:
    analytic = element.stiffness_coord_derivatives(coords)
    n_nodes, spatial = coords.shape
    for node in range(n_nodes):
        for axis in range(min(2, spatial)):
            plus = coords.copy()
            minus = coords.copy()
            plus[node, axis] += step
            minus[node, axis] -= step
            fd = (element.stiffness_matrix(plus) - element.stiffness_matrix(minus)) / (
                2 * step
            )
            np.testing.assert_allclose(
                analytic[:, :, node, axis], fd, rtol=5e-5, atol=1e-6
            )


def test_tri3_stiffness_coord_derivatives_match_fd():
    steel = Material(E=2.1e11, density=7850.0)
    model = Model(dofs=(DOF.UX, DOF.UY))
    model.add_nodes([(1, 0.0, 0.0), (2, 1.0, 0.0), (3, 0.0, 1.0)])
    element = model.add_element(Tri3Element((1, 2, 3), steel, thickness=0.01))
    coords = model.node_coords(element.node_ids)
    _check_derivatives(element, coords)


def test_quad4_stiffness_coord_derivatives_match_fd():
    steel = Material(E=2.1e11, density=7850.0)
    model = Model(dofs=(DOF.UX, DOF.UY))
    model.add_nodes([(1, 0.0, 0.0), (2, 1.0, 0.0), (3, 1.0, 1.0), (4, 0.0, 1.0)])
    element = model.add_element(Quad4Element((1, 2, 3, 4), steel, thickness=0.01))
    coords = model.node_coords(element.node_ids)
    _check_derivatives(element, coords)
