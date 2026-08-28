"""Tests for SIMP topology optimization."""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.core.elements import Hex8Element, Quad4Element, Tet4Element
from openfemlab.core.model import DOF, Material, Model
from openfemlab.exceptions import OptimizationError
from openfemlab.mesh.simple import hex_block_mesh, tet_block_mesh
from openfemlab.optimization.topology import (
    apply_density_filter,
    build_density_filter,
    effective_heaviside_beta,
    element_centroids,
    element_volumes,
    filter_sensitivities,
    heaviside_projection,
    heaviside_projection_derivative,
    run_simp_topology,
)


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


def _mini_tet_block():
    steel = Material(E=2.1e11, density=0.0, nu=0.3)
    model = tet_block_mesh(
        1.0,
        0.5,
        0.5,
        1,
        1,
        1,
        steel,
        support="cantilever",
        name="mini tet block",
    )
    tip = max(model.nodes, key=lambda node: node.coords[0])
    model.add_nodal_load(tip.id, -500.0, dof=DOF.UY)
    return model


def _mini_hex_block():
    steel = Material(E=2.1e11, density=0.0, nu=0.3)
    model = hex_block_mesh(
        1.0,
        0.5,
        0.5,
        1,
        1,
        1,
        steel,
        support="cantilever",
        name="mini hex block",
    )
    tip = max(model.nodes, key=lambda node: node.coords[0])
    model.add_nodal_load(tip.id, -500.0, dof=DOF.UY)
    return model


def test_simp_topology_reduces_compliance():
    model = _mini_plate()
    result = run_simp_topology(model, vol_frac=0.5, max_iter=20, move=0.2, tol=1e-2)
    assert result.densities.shape == (2,)
    assert 0.0 < result.mean_density <= 1.0
    assert len(result.compliance_history) >= 2
    assert result.compliance_history[-1] <= result.compliance_history[0]


def test_element_volumes_tet4():
    steel = Material(E=2.1e11, density=0.0, nu=0.3)
    model = Model(dofs=(DOF.UX, DOF.UY, DOF.UZ))
    model.add_nodes(
        [
            (1, 0.0, 0.0, 0.0),
            (2, 1.0, 0.0, 0.0),
            (3, 0.0, 1.0, 0.0),
            (4, 0.0, 0.0, 1.0),
        ]
    )
    model.add_element(Tet4Element((1, 2, 3, 4), steel))
    volumes = element_volumes(model)
    assert volumes.shape == (1,)
    np.testing.assert_allclose(volumes[0], 1.0 / 6.0, rtol=1e-12)


def test_element_volumes_hex8():
    steel = Material(E=2.1e11, density=0.0, nu=0.3)
    model = Model(dofs=(DOF.UX, DOF.UY, DOF.UZ))
    model.add_nodes(
        [
            (1, 0.0, 0.0, 0.0),
            (2, 1.0, 0.0, 0.0),
            (3, 1.0, 1.0, 0.0),
            (4, 0.0, 1.0, 0.0),
            (5, 0.0, 0.0, 1.0),
            (6, 1.0, 0.0, 1.0),
            (7, 1.0, 1.0, 1.0),
            (8, 0.0, 1.0, 1.0),
        ]
    )
    model.add_element(Hex8Element(tuple(range(1, 9)), steel))
    volumes = element_volumes(model)
    assert volumes.shape == (1,)
    np.testing.assert_allclose(volumes[0], 1.0, rtol=1e-12)


def test_simp_topology_3d_tet4():
    model = _mini_tet_block()
    result = run_simp_topology(model, vol_frac=0.5, max_iter=15, move=0.2, tol=1e-2)
    assert result.densities.size == model.num_elements
    assert result.densities.size == 6
    assert len(result.compliance_history) >= 2
    assert result.compliance_history[-1] <= result.compliance_history[0]


def test_simp_topology_3d_hex8():
    model = _mini_hex_block()
    result = run_simp_topology(model, vol_frac=0.5, max_iter=15, move=0.2, tol=1e-2)
    assert result.densities.size == 1
    assert len(result.compliance_history) >= 1
    assert 0.0 < result.mean_density <= 1.0


def test_density_filter_smooths_checkerboard():
    model = _mini_plate()
    volumes = element_volumes(model)
    filter_matrix, row_sums = build_density_filter(model, radius=0.75, volumes=volumes)
    checkerboard = np.array([1.0, 0.001], dtype=float)
    filtered = apply_density_filter(checkerboard, filter_matrix, row_sums)
    assert filtered.min() > checkerboard.min()
    assert filtered.max() < checkerboard.max()
    assert np.std(filtered) < np.std(checkerboard)


def test_density_filter_sensitivity_chain_rule():
    model = _mini_plate()
    filter_matrix, row_sums = build_density_filter(model, radius=0.75)
    dc_design = np.array([-2.0, -8.0], dtype=float)
    dc_physical = filter_sensitivities(dc_design, filter_matrix, row_sums)
    assert dc_physical.shape == (2,)
    assert np.all(np.isfinite(dc_physical))


def test_simp_topology_with_density_filter():
    model = _mini_plate()
    result = run_simp_topology(
        model,
        vol_frac=0.5,
        max_iter=20,
        move=0.2,
        tol=1e-2,
        filter_radius=0.75,
    )
    assert result.meta["filter_radius"] == 0.75
    assert result.densities.shape == (2,)
    assert len(result.compliance_history) >= 2
    assert result.compliance_history[-1] <= result.compliance_history[0]


def test_element_centroids_dimension():
    model = _mini_plate()
    centroids = element_centroids(model)
    assert centroids.shape == (2, 3)
    np.testing.assert_allclose(centroids[:, 2], 0.0)
    model_3d = _mini_tet_block()
    centroids_3d = element_centroids(model_3d)
    assert centroids_3d.shape == (model_3d.num_elements, 3)


def test_heaviside_projection_sharpens_extremes():
    rho = np.array([0.0, 0.5, 1.0], dtype=float)
    soft = heaviside_projection(rho, beta=1.0, eta=0.5)
    sharp = heaviside_projection(rho, beta=64.0, eta=0.5)
    assert sharp[0] < soft[0] + 0.05
    assert sharp[2] > soft[2] - 0.05
    assert sharp[1] == pytest.approx(0.5, abs=0.05)


def test_heaviside_projection_derivative_is_positive():
    rho = np.linspace(0.0, 1.0, 5)
    deriv = heaviside_projection_derivative(rho, beta=16.0, eta=0.5)
    assert np.all(deriv > 0.0)


def test_effective_heaviside_beta_continuation():
    assert effective_heaviside_beta(0, 10, beta_max=32.0) == pytest.approx(1.0)
    assert effective_heaviside_beta(9, 10, beta_max=32.0) == pytest.approx(32.0, rel=1e-6)
    assert effective_heaviside_beta(5, 10, beta_max=32.0, continuation=False) == 32.0


def test_heaviside_requires_density_filter():
    model = _mini_plate()
    with pytest.raises(OptimizationError, match="filter"):
        run_simp_topology(model, vol_frac=0.5, max_iter=5, heaviside_beta=8.0)


def test_simp_topology_with_heaviside_projection():
    model = _mini_plate()
    result = run_simp_topology(
        model,
        vol_frac=0.5,
        max_iter=20,
        move=0.2,
        tol=1e-2,
        filter_radius=0.75,
        heaviside_beta=16.0,
    )
    assert result.projected_densities is not None
    assert result.meta["heaviside_beta"] == 16.0
    assert result.densities.shape == result.projected_densities.shape
    assert len(result.compliance_history) >= 2
