"""QUAD4 plane-stress/plane-strain element: formulation, patch tests and modal checks.

The element is verified in three layers:

* kernel level -- shape functions, quadrature, constitutive matrices, geometry;
* element/patch level -- rigid-body invariance, zero-energy mode count, exact
  reproduction of constant strain states (the MacNeal-Harder patch);
* model level -- assembly, mass bookkeeping and modal accuracy against the
  closed-form axial bar and Euler-Bernoulli cantilever spectra.
"""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.core.assembly import assemble_stiffness, assemble_system
from openfemlab.core.elements import (
    Quad4Element,
    gauss_legendre_2d,
    plane_constitutive_matrix,
)
from openfemlab.core.model import DOF, Material, Model, Section
from openfemlab.exceptions import ElementError, ModelError
from openfemlab.mesh.simple import bar_mesh, quad_plate_mesh
from openfemlab.solver.modal import ModalSolver

STEEL = Material(E=2.1e11, density=7850.0, nu=0.3)
PATCH_MATERIAL = Material(E=1.0e6, density=1.0, nu=0.25)

#: A deliberately non-rectangular, non-parallelogram element.
DISTORTED = np.array(
    [[0.0, 0.0, 0.0], [2.0, -0.3, 0.0], [2.4, 1.6, 0.0], [0.5, 1.1, 0.0]], dtype=float
)
UNIT_SQUARE = np.array(
    [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]], dtype=float
)


def bound_quad(coords: np.ndarray = DISTORTED, **kwargs) -> Quad4Element:
    """A QUAD4 bound to a two-DOF planar model holding ``coords``."""
    model = Model(dofs=(DOF.UX, DOF.UY), name="single quad")
    for index, point in enumerate(np.asarray(coords, dtype=float)):
        model.add_node(index, point)
    return model.add_element(Quad4Element(range(4), STEEL, **kwargs))


def shoelace_area(coords: np.ndarray) -> float:
    xy = np.asarray(coords, dtype=float)[:, :2]
    rolled = np.roll(xy, -1, axis=0)
    return 0.5 * float(np.sum(xy[:, 0] * rolled[:, 1] - rolled[:, 0] * xy[:, 1]))


def linear_field(coords: np.ndarray, strain: np.ndarray) -> np.ndarray:
    """Nodal displacements of a constant-strain field, in node-major DOF order."""
    xy = np.asarray(coords, dtype=float)[:, :2]
    exx, eyy, gxy = strain
    values = np.zeros(2 * xy.shape[0], dtype=float)
    values[0::2] = exx * xy[:, 0] + 0.5 * gxy * xy[:, 1]
    values[1::2] = eyy * xy[:, 1] + 0.5 * gxy * xy[:, 0]
    return values


# --------------------------------------------------------------- shape functions


def test_shape_functions_are_a_partition_of_unity():
    for xi, eta in [(0.0, 0.0), (-0.4, 0.9), (1.0, -1.0), (0.6, 0.6)]:
        assert Quad4Element.shape_functions(xi, eta).sum() == pytest.approx(1.0, abs=1e-15)


def test_shape_functions_are_nodal_kronecker_deltas():
    natural = [(-1.0, -1.0), (1.0, -1.0), (1.0, 1.0), (-1.0, 1.0)]
    for index, (xi, eta) in enumerate(natural):
        np.testing.assert_allclose(
            Quad4Element.shape_functions(xi, eta), np.eye(4)[index], atol=1e-15
        )


def test_shape_functions_interpolate_the_geometry():
    xi, eta = 0.31, -0.72
    shape = Quad4Element.shape_functions(xi, eta)
    element = bound_quad()
    gradient, _ = element.jacobian(DISTORTED, xi, eta)
    # The mapped point must be consistent with the mapped gradients: the
    # bilinear map reproduces x and y exactly, so dN/dx @ x = [1, 0].
    np.testing.assert_allclose(gradient @ DISTORTED[:, 0], [1.0, 0.0], atol=1e-13)
    np.testing.assert_allclose(gradient @ DISTORTED[:, 1], [0.0, 1.0], atol=1e-13)
    assert shape @ DISTORTED[:, :2] == pytest.approx(
        Quad4Element.shape_functions(xi, eta) @ DISTORTED[:, :2]
    )


def test_shape_function_derivatives_match_finite_differences():
    xi, eta = 0.23, -0.61
    step = 1e-6
    analytic = Quad4Element.shape_function_derivatives(xi, eta)
    d_xi = (
        Quad4Element.shape_functions(xi + step, eta) - Quad4Element.shape_functions(xi - step, eta)
    ) / (2 * step)
    d_eta = (
        Quad4Element.shape_functions(xi, eta + step) - Quad4Element.shape_functions(xi, eta - step)
    ) / (2 * step)
    np.testing.assert_allclose(analytic[0], d_xi, atol=1e-10)
    np.testing.assert_allclose(analytic[1], d_eta, atol=1e-10)


# -------------------------------------------------------------------- quadrature


@pytest.mark.parametrize("order", [1, 2, 3, 4])
def test_gauss_rule_integrates_polynomials_of_its_degree_exactly(order):
    points, weights = gauss_legendre_2d(order)
    assert points.shape == (order**2, 2)
    assert weights.sum() == pytest.approx(4.0)
    degree = 2 * order - 1
    for p in range(degree + 1):
        for q in range(degree + 1):
            exact = (0.0 if p % 2 else 2.0 / (p + 1)) * (0.0 if q % 2 else 2.0 / (q + 1))
            numeric = float(np.sum(weights * points[:, 0] ** p * points[:, 1] ** q))
            assert numeric == pytest.approx(exact, abs=1e-14)


@pytest.mark.parametrize("order", [0, 5, -1])
def test_gauss_rule_rejects_unsupported_order(order):
    with pytest.raises(ElementError, match="integration order"):
        gauss_legendre_2d(order)


# ------------------------------------------------------------------ constitutive


def test_plane_stress_matrix_matches_the_closed_form():
    material = Material(E=200.0, density=1.0, nu=0.25)
    expected = (200.0 / (1.0 - 0.0625)) * np.array(
        [[1.0, 0.25, 0.0], [0.25, 1.0, 0.0], [0.0, 0.0, 0.375]]
    )
    np.testing.assert_allclose(plane_constitutive_matrix(material, "stress"), expected, rtol=1e-14)


def test_plane_strain_matrix_matches_the_closed_form():
    material = Material(E=200.0, density=1.0, nu=0.25)
    factor = 200.0 / (1.25 * 0.5)
    expected = factor * np.array([[0.75, 0.25, 0.0], [0.25, 0.75, 0.0], [0.0, 0.0, 0.25]])
    np.testing.assert_allclose(plane_constitutive_matrix(material, "strain"), expected, rtol=1e-14)


def test_plane_strain_is_stiffer_than_plane_stress():
    stress = plane_constitutive_matrix(STEEL, "stress")
    strain = plane_constitutive_matrix(STEEL, "strain")
    assert strain[0, 0] > stress[0, 0]
    # Transverse shear is unaffected by the out-of-plane condition.
    assert strain[2, 2] == pytest.approx(stress[2, 2], rel=1e-14)


def test_plane_states_agree_when_poisson_ratio_vanishes():
    material = Material(E=1.0, density=0.0, nu=0.0)
    np.testing.assert_allclose(
        plane_constitutive_matrix(material, "stress"),
        plane_constitutive_matrix(material, "strain"),
        atol=1e-15,
    )


def test_unknown_plane_state_is_rejected():
    with pytest.raises(ElementError, match="unknown plane state"):
        plane_constitutive_matrix(STEEL, "shell")
    with pytest.raises(ElementError, match="unknown plane state"):
        Quad4Element(range(4), STEEL, plane="axisymmetric")


# --------------------------------------------------------------------- geometry


@pytest.mark.parametrize("coords", [UNIT_SQUARE, DISTORTED])
def test_area_matches_the_shoelace_formula(coords):
    element = bound_quad(coords)
    assert element.area(coords) == pytest.approx(shoelace_area(coords), rel=1e-14)


def test_total_mass_is_density_times_thickness_times_area():
    element = bound_quad(DISTORTED, thickness=0.02)
    expected = STEEL.density * 0.02 * shoelace_area(DISTORTED)
    assert element.total_mass(DISTORTED) == pytest.approx(expected, rel=1e-14)


def test_clockwise_node_order_is_rejected():
    element = bound_quad(UNIT_SQUARE)
    reversed_coords = UNIT_SQUARE[::-1]
    with pytest.raises(ElementError, match="non-positive Jacobian"):
        element.stiffness_matrix(reversed_coords)


def test_degenerate_element_is_rejected():
    collapsed = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 0.0], [0.0, 0.0]])
    element = bound_quad(UNIT_SQUARE)
    with pytest.raises(ElementError, match="non-positive Jacobian"):
        element.stiffness_matrix(collapsed)


def test_out_of_plane_nodes_are_rejected():
    warped = UNIT_SQUARE.copy()
    warped[2, 2] = 0.4
    element = bound_quad(UNIT_SQUARE)
    with pytest.raises(ElementError, match="span"):
        element.stiffness_matrix(warped)


def test_a_constant_z_offset_is_accepted():
    lifted = UNIT_SQUARE + np.array([0.0, 0.0, 3.5])
    element = bound_quad(UNIT_SQUARE)
    np.testing.assert_allclose(
        element.stiffness_matrix(lifted), element.stiffness_matrix(UNIT_SQUARE), rtol=1e-14
    )


def test_wrong_node_count_is_rejected():
    with pytest.raises(ElementError, match="expects 4 nodes"):
        Quad4Element((1, 2, 3), STEEL)


def test_repeated_nodes_are_rejected():
    with pytest.raises(ElementError, match="repeated nodes"):
        Quad4Element((1, 2, 2, 3), STEEL)


def test_non_positive_thickness_is_rejected():
    with pytest.raises(ElementError, match="thickness must be positive"):
        Quad4Element(range(4), STEEL, thickness=0.0)


def test_element_requires_both_planar_translations():
    model = Model(dofs=(DOF.UX,), name="axial only")
    for index, point in enumerate(UNIT_SQUARE):
        model.add_node(index, point)
    with pytest.raises(ElementError, match="UY"):
        model.add_element(Quad4Element(range(4), STEEL))


# -------------------------------------------------------------------- stiffness


def test_stiffness_is_symmetric_and_positive_semidefinite():
    k = bound_quad().stiffness_matrix(DISTORTED)
    assert k.shape == (8, 8)
    np.testing.assert_allclose(k, k.T, rtol=0, atol=1e-9 * np.abs(k).max())
    eigenvalues = np.linalg.eigvalsh(k)
    assert eigenvalues.min() > -1e-8 * eigenvalues.max()


def test_full_integration_leaves_exactly_three_zero_energy_modes():
    k = bound_quad(DISTORTED).stiffness_matrix(DISTORTED)
    eigenvalues = np.linalg.eigvalsh(k)
    zeros = np.sum(np.abs(eigenvalues) < 1e-8 * eigenvalues.max())
    assert zeros == 3


def test_reduced_integration_is_rank_deficient():
    element = bound_quad(DISTORTED, integration_order=1)
    eigenvalues = np.linalg.eigvalsh(element.stiffness_matrix(DISTORTED))
    zeros = np.sum(np.abs(eigenvalues) < 1e-8 * eigenvalues.max())
    assert zeros == 5  # three rigid-body modes plus two hourglass modes


def test_rigid_body_translation_produces_no_nodal_force():
    element = bound_quad()
    k = element.stiffness_matrix(DISTORTED)
    scale = np.abs(k).max()
    for offset in ([1.0, 0.0], [0.0, 1.0]):
        motion = np.tile(offset, 4)
        np.testing.assert_allclose(k @ motion, np.zeros(8), atol=1e-12 * scale)


def test_rigid_body_rotation_produces_no_strain_energy():
    element = bound_quad()
    k = element.stiffness_matrix(DISTORTED)
    xy = DISTORTED[:, :2]
    rotation = np.zeros(8)
    rotation[0::2] = -xy[:, 1]
    rotation[1::2] = xy[:, 0]
    reference = float(np.abs(k).max() * rotation @ rotation)
    assert float(rotation @ k @ rotation) == pytest.approx(0.0, abs=1e-12 * reference)
    np.testing.assert_allclose(
        element.strain(DISTORTED, rotation, 0.4, -0.2), np.zeros(3), atol=1e-14
    )


def test_stiffness_scales_linearly_with_thickness_and_modulus():
    base = bound_quad(DISTORTED, thickness=0.01).stiffness_matrix(DISTORTED)
    thicker = bound_quad(DISTORTED, thickness=0.03).stiffness_matrix(DISTORTED)
    np.testing.assert_allclose(thicker, 3.0 * base, rtol=1e-13)

    model = Model(dofs=(DOF.UX, DOF.UY))
    for index, point in enumerate(DISTORTED):
        model.add_node(index, point)
    stiffer = model.add_element(
        Quad4Element(range(4), Material(E=2 * STEEL.E, density=1.0, nu=STEEL.nu), thickness=0.01)
    )
    np.testing.assert_allclose(stiffer.stiffness_matrix(DISTORTED), 2.0 * base, rtol=1e-13)


def test_stiffness_is_invariant_under_in_plane_rotation():
    angle = 0.7
    c, s = np.cos(angle), np.sin(angle)
    rotation = np.array([[c, -s], [s, c]])
    rotated = DISTORTED.copy()
    rotated[:, :2] = DISTORTED[:, :2] @ rotation.T
    element = bound_quad()
    transform = np.kron(np.eye(4), rotation)
    np.testing.assert_allclose(
        element.stiffness_matrix(rotated),
        transform @ element.stiffness_matrix(DISTORTED) @ transform.T,
        atol=1e-6,
        rtol=1e-10,
    )


# ------------------------------------------------------------------ patch tests


@pytest.mark.parametrize("strain", [np.array([1e-3, 0.0, 0.0]), np.array([4e-4, -2e-4, 7e-4])])
def test_single_element_reproduces_constant_strain_exactly(strain):
    element = bound_quad(DISTORTED)
    displacements = linear_field(DISTORTED, strain)
    expected_stress = element.constitutive_matrix @ strain
    for xi, eta in [(0.0, 0.0), (-0.9, 0.3), (0.8, -0.6), (1.0, 1.0)]:
        np.testing.assert_allclose(
            element.strain(DISTORTED, displacements, xi, eta), strain, rtol=1e-12, atol=1e-16
        )
        np.testing.assert_allclose(
            element.stress(DISTORTED, displacements, xi, eta),
            expected_stress,
            rtol=1e-12,
            atol=1e-12 * np.abs(expected_stress).max(),
        )


def test_constant_strain_state_is_in_equilibrium_with_its_boundary_tractions():
    element = bound_quad(DISTORTED)
    displacements = linear_field(DISTORTED, np.array([4e-4, -2e-4, 7e-4]))
    forces = element.stiffness_matrix(DISTORTED) @ displacements
    # Consistent nodal forces of a constant stress field are self-equilibrated.
    assert abs(forces[0::2].sum()) < 1e-9 * np.abs(forces).max()
    assert abs(forces[1::2].sum()) < 1e-9 * np.abs(forces).max()


def macneal_harder_patch(**element_kwargs):
    """The MacNeal-Harder five-element distorted patch on a 0.24 x 0.12 rectangle."""
    coords = {
        1: (0.00, 0.00),
        2: (0.24, 0.00),
        3: (0.24, 0.12),
        4: (0.00, 0.12),
        5: (0.04, 0.02),
        6: (0.18, 0.03),
        7: (0.16, 0.08),
        8: (0.08, 0.08),
    }
    connectivity = [(1, 2, 6, 5), (2, 3, 7, 6), (3, 4, 8, 7), (4, 1, 5, 8), (5, 6, 7, 8)]
    model = Model(dofs=(DOF.UX, DOF.UY), name="patch")
    for node_id, (x, y) in coords.items():
        model.add_node(node_id, x, y, 0.0)
    elements = [
        model.add_element(
            Quad4Element(nodes, PATCH_MATERIAL, thickness=0.001, **element_kwargs)
        )
        for nodes in connectivity
    ]
    return model, elements, coords


def solve_patch(model, coords):
    """Prescribe ``u = 1e-3 (x + y/2)``, ``v = 1e-3 (y + x/2)`` on the outer boundary."""
    exact = np.zeros(model.num_dofs, dtype=float)
    for node_id, (x, y) in coords.items():
        exact[model.dof_index(node_id, DOF.UX)] = 1e-3 * (x + 0.5 * y)
        exact[model.dof_index(node_id, DOF.UY)] = 1e-3 * (y + 0.5 * x)

    K = assemble_stiffness(model).toarray()
    prescribed = np.array(
        [model.dof_index(n, d) for n in (1, 2, 3, 4) for d in (DOF.UX, DOF.UY)], dtype=int
    )
    interior = np.setdiff1d(np.arange(model.num_dofs), prescribed)
    solution = np.linalg.solve(
        K[np.ix_(interior, interior)], -K[np.ix_(interior, prescribed)] @ exact[prescribed]
    )
    computed = exact.copy()
    computed[interior] = solution
    return computed, exact, interior


def test_macneal_harder_patch_recovers_the_interior_displacements():
    model, _, coords = macneal_harder_patch()
    computed, exact, interior = solve_patch(model, coords)
    error = np.abs(computed[interior] - exact[interior]).max()
    assert error < 1e-14 * np.abs(exact).max()


def test_macneal_harder_patch_yields_the_exact_constant_stress():
    model, elements, coords = macneal_harder_patch()
    computed, _, _ = solve_patch(model, coords)
    expected = np.array([1333.3333333333, 1333.3333333333, 400.0])
    for element in elements:
        element_coords = model.node_coords(element.node_ids)
        displacements = computed[element.global_dofs(model)]
        for xi, eta in [(-0.7, 0.2), (0.0, 0.0), (0.5, -0.9)]:
            np.testing.assert_allclose(
                element.stress(element_coords, displacements, xi, eta), expected, rtol=1e-9
            )


@pytest.mark.parametrize("order", [2, 3])
def test_patch_test_holds_for_any_full_integration_order(order):
    model, _, coords = macneal_harder_patch(integration_order=order)
    computed, exact, interior = solve_patch(model, coords)
    assert np.abs(computed[interior] - exact[interior]).max() < 1e-14 * np.abs(exact).max()


# ------------------------------------------------------------------------ mass


def test_consistent_mass_is_symmetric_and_positive_definite():
    m = bound_quad(DISTORTED).mass_matrix(DISTORTED)
    np.testing.assert_allclose(m, m.T, atol=1e-18)
    assert np.linalg.eigvalsh(m).min() > 0.0


def test_consistent_mass_reproduces_the_total_mass_in_each_direction():
    element = bound_quad(DISTORTED, thickness=0.02)
    m = element.mass_matrix(DISTORTED)
    total = element.total_mass(DISTORTED)
    assert m[0::2, 0::2].sum() == pytest.approx(total, rel=1e-13)
    assert m[1::2, 1::2].sum() == pytest.approx(total, rel=1e-13)
    assert m[0::2, 1::2].sum() == pytest.approx(0.0, abs=1e-18)


def test_rigid_translation_kinetic_energy_equals_the_total_mass():
    element = bound_quad(DISTORTED, thickness=0.02)
    m = element.mass_matrix(DISTORTED)
    velocity = np.zeros(8)
    velocity[0::2] = 1.0
    assert float(velocity @ m @ velocity) == pytest.approx(
        element.total_mass(DISTORTED), rel=1e-13
    )


def test_lumped_mass_is_diagonal_and_preserves_the_total_mass():
    element = bound_quad(DISTORTED, thickness=0.02, lumped_mass=True)
    m = element.mass_matrix(DISTORTED)
    np.testing.assert_allclose(m - np.diag(np.diag(m)), np.zeros((8, 8)), atol=1e-18)
    assert np.diag(m)[0::2].sum() == pytest.approx(element.total_mass(DISTORTED), rel=1e-13)
    assert np.all(np.diag(m) > 0.0)


def test_lumped_mass_is_the_row_sum_of_the_consistent_mass():
    element = bound_quad(DISTORTED, thickness=0.02, lumped_mass=True)
    consistent = element.consistent_mass_matrix(DISTORTED)
    np.testing.assert_allclose(np.diag(element.mass_matrix(DISTORTED)), consistent.sum(axis=1))


def test_a_massless_material_gives_a_zero_mass_matrix():
    model = Model(dofs=(DOF.UX, DOF.UY))
    for index, point in enumerate(UNIT_SQUARE):
        model.add_node(index, point)
    element = model.add_element(
        Quad4Element(range(4), Material(E=1.0e9, density=0.0, nu=0.3), thickness=0.01)
    )
    np.testing.assert_array_equal(element.mass_matrix(UNIT_SQUARE), np.zeros((8, 8)))
    assert element.total_mass(UNIT_SQUARE) == 0.0


# ------------------------------------------------------------------ mesh & model


def test_quad_plate_mesh_builds_the_expected_grid():
    model = quad_plate_mesh(0.3, 0.2, 3, 2, STEEL, thickness=0.01, support="free")
    assert model.num_nodes == 4 * 3
    assert model.num_elements == 6
    assert model.dofs == (DOF.UX, DOF.UY)
    assert model.constrained_dofs.size == 0
    corner = model.node(model.num_nodes - 1)
    assert (corner.x, corner.y) == pytest.approx((0.3, 0.2))
    for element in model.elements:
        assert element.area(model.node_coords(element.node_ids)) > 0.0


def test_quad_plate_mesh_clamps_the_cantilever_root():
    model = quad_plate_mesh(1.0, 0.1, 4, 2, STEEL, thickness=0.01, support="cantilever")
    root = [0, 5, 10]
    assert model.constrained_dofs.size == 2 * len(root)
    for node_id in root:
        assert model.is_constrained(node_id, DOF.UX)
        assert model.is_constrained(node_id, DOF.UY)


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"support": "clamped"}, "unknown support"),
        ({"num_x": 0}, "must be >= 1"),
        ({"length": -1.0}, "must be positive"),
    ],
)
def test_quad_plate_mesh_validates_its_arguments(kwargs, match):
    arguments = {"length": 1.0, "height": 0.1, "num_x": 4, "num_y": 2, "material": STEEL}
    arguments.update(kwargs)
    with pytest.raises(ModelError, match=match):
        quad_plate_mesh(**arguments)


def test_assembled_plate_reproduces_the_analytic_slab_mass():
    length, height, thickness = 0.4, 0.25, 0.006
    model = quad_plate_mesh(length, height, 5, 4, STEEL, thickness=thickness, support="free")
    system = assemble_system(model)
    expected = STEEL.density * thickness * length * height
    assert system.total_mass == pytest.approx(expected, rel=1e-12)


def test_assembled_plate_matrices_are_symmetric():
    model = quad_plate_mesh(0.4, 0.25, 4, 3, STEEL, thickness=0.006, support="free")
    system = assemble_system(model)
    for matrix in (system.K, system.M):
        assert abs(matrix - matrix.T).max() <= 1e-6 * abs(matrix).max()


# ---------------------------------------------------------------------- modal


def test_axial_modes_match_the_equivalent_bar_mesh():
    """With ``nu = 0`` the column-constant axial subspace of a rectangular QUAD4 strip
    is K- and M-invariant and coincides exactly with a linear bar discretization."""
    material = Material(E=2.1e11, density=7850.0, nu=0.0)
    length, height, thickness, num_x = 1.0, 0.1, 0.01, 20
    plate = quad_plate_mesh(
        length, height, num_x, 2, material, thickness=thickness, support="cantilever"
    )
    plate.fix_dof_globally((DOF.UY,))
    plate_modes = ModalSolver(plate).solve(num_modes=3).frequencies

    bar = bar_mesh(length, num_x, material, Section(area=thickness * height))
    bar_modes = ModalSolver(bar).solve(num_modes=3).frequencies

    np.testing.assert_allclose(plate_modes, bar_modes, rtol=1e-10)


def test_axial_modes_converge_to_the_continuum_bar():
    material = Material(E=2.1e11, density=7850.0, nu=0.0)
    length, height, thickness = 1.0, 0.1, 0.01
    speed = np.sqrt(material.E / material.density)
    exact = speed / (4.0 * length)

    errors = []
    for num_x in (5, 10, 20):
        plate = quad_plate_mesh(
            length, height, num_x, 2, material, thickness=thickness, support="cantilever"
        )
        plate.fix_dof_globally((DOF.UY,))
        first = ModalSolver(plate).solve(num_modes=1).frequencies[0]
        errors.append(abs(first / exact - 1.0))

    assert errors[-1] < 1e-3
    # Consistent-mass discretization converges quadratically, from above.
    assert errors[0] > errors[1] > errors[2]
    assert errors[0] / errors[1] > 3.0
    assert errors[1] / errors[2] > 3.0


def test_cantilever_bending_converges_to_euler_bernoulli_from_above():
    length, height, thickness = 1.0, 0.05, 0.01
    inertia = thickness * height**3 / 12.0
    area = thickness * height
    reference = (1.875104**2 / (2 * np.pi)) * np.sqrt(
        STEEL.E * inertia / (STEEL.density * area * length**4)
    )

    errors = []
    for num_x, num_y in [(20, 2), (40, 4), (80, 8)]:
        model = quad_plate_mesh(
            length, height, num_x, num_y, STEEL, thickness=thickness, support="cantilever"
        )
        first = ModalSolver(model).solve(num_modes=1).frequencies[0]
        errors.append(first / reference - 1.0)

    # Bilinear elements represent bending through shear, so they lock from above.
    assert all(error > 0.0 for error in errors)
    assert errors[0] > errors[1] > errors[2]
    assert errors[-1] < 0.02
    assert errors[0] / errors[1] > 2.0


def test_free_plate_has_three_rigid_body_modes():
    model = quad_plate_mesh(0.3, 0.2, 4, 3, STEEL, thickness=0.006, support="free")
    result = ModalSolver(model).solve(num_modes=6)
    assert int(np.sum(result.rigid_body_modes)) == 3
    assert result.frequencies[3] > 1.0e3
    np.testing.assert_allclose(result.frequencies[:3], np.zeros(3), atol=1e-2)


def test_plate_modes_are_mass_orthonormal():
    model = quad_plate_mesh(0.4, 0.25, 5, 4, STEEL, thickness=0.006, support="cantilever")
    result = ModalSolver(model).solve(num_modes=6)
    assert result.orthogonality_error() < 1e-9


def test_lumped_mass_plate_is_not_stiffer_than_the_consistent_one():
    arguments = {"thickness": 0.006, "support": "cantilever"}
    consistent = ModalSolver(
        quad_plate_mesh(0.4, 0.25, 5, 4, STEEL, **arguments)
    ).solve(num_modes=4)
    lumped = ModalSolver(
        quad_plate_mesh(0.4, 0.25, 5, 4, STEEL, lumped_mass=True, **arguments)
    ).solve(num_modes=4)
    assert np.all(lumped.frequencies <= consistent.frequencies * (1.0 + 1e-12))
    np.testing.assert_allclose(lumped.frequencies, consistent.frequencies, rtol=0.15)


def test_plane_strain_plate_is_stiffer_than_plane_stress():
    arguments = {"thickness": 0.006, "support": "cantilever"}
    stress = ModalSolver(
        quad_plate_mesh(0.4, 0.25, 5, 4, STEEL, plane="stress", **arguments)
    ).solve(num_modes=3)
    strain = ModalSolver(
        quad_plate_mesh(0.4, 0.25, 5, 4, STEEL, plane="strain", **arguments)
    ).solve(num_modes=3)
    assert np.all(strain.frequencies > stress.frequencies)
