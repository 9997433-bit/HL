"""HEX8 trilinear brick: formulation, patch tests and modal checks.

The element is verified in three layers, mirroring ``tests/test_quad4.py`` and
``tests/test_tet4.py``:

* kernel level -- shape functions, the 3D Gauss rule, geometry;
* element/patch level -- rigid-body invariance, zero-energy mode count, exact
  reproduction of constant strain states on a distorted multi-element patch;
* model level -- structured blocks, mass bookkeeping and modal accuracy against
  the closed-form axial bar spectrum, plus the bending behaviour that separates
  the brick from the constant-strain tetrahedron.
"""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.core.assembly import assemble_stiffness, assemble_system
from openfemlab.core.elements import (
    Hex8Element,
    gauss_legendre_3d,
    solid_constitutive_matrix,
)
from openfemlab.core.model import DOF, Material, Model
from openfemlab.exceptions import ElementError, ModelError
from openfemlab.mesh.simple import hex_block_mesh, tet_block_mesh
from openfemlab.solver.modal import ModalSolver

STEEL = Material(E=2.1e11, density=7850.0, nu=0.3)
PATCH_MATERIAL = Material(E=1.0e6, density=1.0, nu=0.25)

SOLID_DOFS = (DOF.UX, DOF.UY, DOF.UZ)

#: The reference cube, in HEX8 node order: the ``z = 0`` face counter-clockwise,
#: then the ``z = 1`` face. Natural and physical coordinates differ by an offset
#: and a factor two only.
CUBE = np.array(
    [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [1.0, 1.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
        [1.0, 0.0, 1.0],
        [1.0, 1.0, 1.0],
        [0.0, 1.0, 1.0],
    ],
    dtype=float,
)

#: A brick with no planar face and no parallel edge pair -- the geometry every
#: exactness claim below is measured on.
DISTORTED = np.array(
    [
        [0.05, -0.10, 0.02],
        [1.20, 0.08, -0.15],
        [1.35, 1.10, 0.12],
        [-0.08, 0.95, -0.05],
        [0.02, -0.05, 1.05],
        [1.10, 0.12, 0.90],
        [1.25, 1.05, 1.20],
        [0.10, 1.15, 1.02],
    ],
    dtype=float,
)

#: Edge vectors of the sheared unit cell used where a closed form needs a
#: constant Jacobian.
SHEAR = np.array([[1.2, 0.0, 0.0], [0.3, 0.9, 0.0], [-0.2, 0.15, 1.4]], dtype=float)
PARALLELEPIPED = CUBE @ SHEAR

#: Displacement gradient of the patch field; the three normal strains differ and
#: none of the resulting stress components vanishes.
PATCH_GRADIENT = 1e-3 * np.array([[1.0, 0.4, -0.2], [0.3, -0.5, 0.5], [-0.1, 0.2, 0.8]])

#: Natural points the patch stress is sampled at -- centroid, a Gauss point, a
#: corner and an interior point, so the claim is "constant over the element".
SAMPLE_POINTS = ((0.0, 0.0, 0.0), (0.577, -0.577, 0.577), (1.0, 1.0, 1.0), (-1.0, 0.3, 0.8))


def bound_hex(coords: np.ndarray = DISTORTED, **kwargs) -> Hex8Element:
    """A HEX8 bound to a three-DOF solid model holding ``coords``."""
    model = Model(dofs=SOLID_DOFS, name="single hex")
    for index, point in enumerate(np.asarray(coords, dtype=float)):
        model.add_node(index, point)
    return model.add_element(Hex8Element(range(8), STEEL, **kwargs))


def linear_field(coords: np.ndarray, gradient: np.ndarray) -> np.ndarray:
    """Nodal displacements of ``u = G x``, in node-major DOF order."""
    return (np.asarray(coords, dtype=float) @ np.asarray(gradient, dtype=float).T).reshape(-1)


def voigt_strain(gradient: np.ndarray) -> np.ndarray:
    """Engineering strain ``[exx, eyy, ezz, gxy, gyz, gzx]`` of a displacement gradient."""
    g = np.asarray(gradient, dtype=float)
    return np.array(
        [g[0, 0], g[1, 1], g[2, 2], g[0, 1] + g[1, 0], g[1, 2] + g[2, 1], g[0, 2] + g[2, 0]]
    )


def cube_mass_pattern() -> np.ndarray:
    """``216/V * int N_i N_j dV`` on a parallelepiped: ``2**(shared coordinates)``."""
    pattern = np.zeros((8, 8), dtype=float)
    for i in range(8):
        for j in range(8):
            pattern[i, j] = 2.0 ** int(np.sum(np.isclose(CUBE[i], CUBE[j])))
    return pattern


def solve_prescribed(model: Model, prescribed: dict[int, float]) -> np.ndarray:
    """Static solution with the given DOF indices held at the given values."""
    K = assemble_stiffness(model).toarray()
    fixed = np.array(sorted(prescribed), dtype=int)
    free = np.setdiff1d(np.arange(model.num_dofs), fixed)
    values = np.zeros(model.num_dofs, dtype=float)
    values[fixed] = [prescribed[index] for index in fixed]
    values[free] = np.linalg.solve(
        K[np.ix_(free, free)], -K[np.ix_(free, fixed)] @ values[fixed]
    )
    return values


# --------------------------------------------------------------- shape functions


def test_shape_functions_are_a_partition_of_unity():
    for point in [(0.0, 0.0, 0.0), (-0.4, 0.9, 0.2), (1.0, -1.0, 1.0), (0.6, 0.6, -0.3)]:
        assert Hex8Element.shape_functions(*point).sum() == pytest.approx(1.0, abs=1e-15)


def test_shape_functions_are_nodal_kronecker_deltas():
    natural = 2.0 * CUBE - 1.0
    for index, point in enumerate(natural):
        np.testing.assert_allclose(
            Hex8Element.shape_functions(*point), np.eye(8)[index], atol=1e-15
        )


def test_shape_functions_interpolate_the_geometry():
    """The isoparametric map sends the reference cube onto the physical brick."""
    for point in [(0.0, 0.0, 0.0), (0.3, -0.7, 0.5)]:
        shape = Hex8Element.shape_functions(*point)
        expected = 0.5 * (np.array(point) + 1.0)  # CUBE is the unit-scaled reference
        np.testing.assert_allclose(shape @ CUBE, expected, atol=1e-15)


def test_shape_function_derivatives_match_finite_differences():
    base = np.array([0.23, -0.61, 0.44])
    step = 1e-6
    analytic = Hex8Element.shape_function_derivatives(*base)
    for axis in range(3):
        offset = np.zeros(3)
        offset[axis] = step
        numeric = (
            Hex8Element.shape_functions(*(base + offset))
            - Hex8Element.shape_functions(*(base - offset))
        ) / (2 * step)
        np.testing.assert_allclose(analytic[axis], numeric, atol=1e-9)


def test_physical_shape_gradients_sum_to_zero():
    """A constant displacement produces no strain, which is exactly this identity."""
    gradient, _ = bound_hex().jacobian(DISTORTED, 0.3, -0.2, 0.6)
    np.testing.assert_allclose(gradient.sum(axis=1), np.zeros(3), atol=1e-13)


def test_physical_shape_gradients_reproduce_the_coordinate_derivatives():
    gradient, _ = bound_hex().jacobian(DISTORTED, 0.3, -0.2, 0.6)
    np.testing.assert_allclose(gradient @ DISTORTED, np.eye(3), atol=1e-13)


# -------------------------------------------------------------------- quadrature


@pytest.mark.parametrize("order", [1, 2, 3, 4])
def test_gauss_rule_integrates_polynomials_of_its_degree_exactly(order):
    points, weights = gauss_legendre_3d(order)
    assert points.shape == (order**3, 3)
    assert weights.sum() == pytest.approx(8.0)
    degree = 2 * order - 1
    for p in range(degree + 1):
        for q in range(degree + 1):
            for r in range(degree + 1):
                exact = np.prod(
                    [0.0 if e % 2 else 2.0 / (e + 1) for e in (p, q, r)]
                )
                numeric = float(
                    np.sum(weights * points[:, 0] ** p * points[:, 1] ** q * points[:, 2] ** r)
                )
                assert numeric == pytest.approx(exact, abs=1e-14)


@pytest.mark.parametrize("order", [0, 5, -1])
def test_gauss_rule_rejects_unsupported_order(order):
    with pytest.raises(ElementError, match="integration order"):
        gauss_legendre_3d(order)


# --------------------------------------------------------------------- geometry


def test_the_reference_cube_has_unit_volume():
    assert bound_hex(CUBE).volume(CUBE) == pytest.approx(1.0, rel=1e-15)


def test_a_parallelepiped_has_the_determinant_volume():
    element = bound_hex(PARALLELEPIPED)
    expected = abs(float(np.linalg.det(SHEAR)))
    assert element.volume(PARALLELEPIPED) == pytest.approx(expected, rel=1e-14)


@pytest.mark.parametrize("order", [3, 4])
def test_the_default_rule_integrates_a_distorted_volume_exactly(order):
    """``det J`` stays within the 2-point rule's degree, so refining changes nothing."""
    coarse = bound_hex(DISTORTED).volume(DISTORTED)
    fine = bound_hex(DISTORTED, integration_order=order).volume(DISTORTED)
    assert coarse == pytest.approx(fine, rel=1e-14)


def test_total_mass_is_density_times_volume():
    element = bound_hex(DISTORTED)
    expected = STEEL.density * element.volume(DISTORTED)
    assert element.total_mass(DISTORTED) == pytest.approx(expected, rel=1e-14)


def test_inverted_node_order_is_rejected():
    inverted = CUBE[[4, 5, 6, 7, 0, 1, 2, 3]]
    element = bound_hex(CUBE)
    with pytest.raises(ElementError, match="non-positive Jacobian"):
        element.stiffness_matrix(inverted)


def test_a_collapsed_face_is_rejected():
    collapsed = CUBE.copy()
    collapsed[4:] = collapsed[:4]
    element = bound_hex(CUBE)
    with pytest.raises(ElementError, match="non-positive Jacobian"):
        element.stiffness_matrix(collapsed)


def test_planar_coordinates_are_rejected():
    element = bound_hex(CUBE)
    with pytest.raises(ElementError, match="three coordinates per node"):
        element.stiffness_matrix(CUBE[:, :2])


def test_a_rigid_translation_of_the_geometry_leaves_the_matrices_alone():
    shifted = DISTORTED + np.array([3.5, -2.0, 7.25])
    element = bound_hex(DISTORTED)
    np.testing.assert_allclose(
        element.stiffness_matrix(shifted), element.stiffness_matrix(DISTORTED), rtol=1e-12
    )


def test_wrong_node_count_is_rejected():
    with pytest.raises(ElementError, match="expects 8 nodes"):
        Hex8Element(range(7), STEEL)


def test_repeated_nodes_are_rejected():
    with pytest.raises(ElementError, match="repeated nodes"):
        Hex8Element((0, 1, 2, 3, 4, 5, 6, 6), STEEL)


def test_element_requires_all_three_translations():
    model = Model(dofs=(DOF.UX, DOF.UY), name="planar only")
    for index, point in enumerate(CUBE):
        model.add_node(index, point)
    with pytest.raises(ElementError, match="UZ"):
        model.add_element(Hex8Element(range(8), STEEL))


# -------------------------------------------------------------------- stiffness


def test_stiffness_is_symmetric_and_positive_semidefinite():
    k = bound_hex().stiffness_matrix(DISTORTED)
    assert k.shape == (24, 24)
    np.testing.assert_allclose(k, k.T, rtol=0, atol=1e-9 * np.abs(k).max())
    eigenvalues = np.linalg.eigvalsh(k)
    assert eigenvalues.min() > -1e-8 * eigenvalues.max()


@pytest.mark.parametrize("coords", [CUBE, DISTORTED])
def test_full_integration_leaves_exactly_six_zero_energy_modes(coords):
    eigenvalues = np.linalg.eigvalsh(bound_hex(coords).stiffness_matrix(coords))
    zeros = np.sum(np.abs(eigenvalues) < 1e-8 * eigenvalues.max())
    assert zeros == 6  # the six spatial rigid-body motions, no hourglassing


def test_reduced_integration_is_rank_deficient():
    element = bound_hex(DISTORTED, integration_order=1)
    eigenvalues = np.linalg.eigvalsh(element.stiffness_matrix(DISTORTED))
    zeros = np.sum(np.abs(eigenvalues) < 1e-8 * eigenvalues.max())
    assert zeros == 18  # six rigid-body modes plus the twelve hourglass modes


@pytest.mark.parametrize("axis", [0, 1, 2])
def test_rigid_body_translation_produces_no_nodal_force(axis):
    k = bound_hex().stiffness_matrix(DISTORTED)
    motion = np.tile(np.eye(3)[axis], 8)
    np.testing.assert_allclose(k @ motion, np.zeros(24), atol=1e-12 * np.abs(k).max())


@pytest.mark.parametrize("axis", [0, 1, 2])
def test_rigid_body_rotation_produces_no_strain_energy(axis):
    element = bound_hex()
    k = element.stiffness_matrix(DISTORTED)
    rotation = np.cross(np.eye(3)[axis], DISTORTED).reshape(-1)
    reference = float(np.abs(k).max() * rotation @ rotation)
    assert float(rotation @ k @ rotation) == pytest.approx(0.0, abs=1e-12 * reference)
    for point in SAMPLE_POINTS:
        np.testing.assert_allclose(
            element.strain(DISTORTED, rotation, *point), np.zeros(6), atol=1e-13
        )


def test_stiffness_scales_linearly_with_the_modulus():
    base = bound_hex(DISTORTED).stiffness_matrix(DISTORTED)
    model = Model(dofs=SOLID_DOFS)
    for index, point in enumerate(DISTORTED):
        model.add_node(index, point)
    stiffer = model.add_element(
        Hex8Element(range(8), Material(E=3 * STEEL.E, density=1.0, nu=STEEL.nu))
    )
    np.testing.assert_allclose(stiffer.stiffness_matrix(DISTORTED), 3.0 * base, rtol=1e-13)


def test_stiffness_is_invariant_under_a_spatial_rotation():
    angle = 0.7
    c, s = np.cos(angle), np.sin(angle)
    axis = np.ones(3) / np.sqrt(3.0)
    cross = np.array([[0.0, -axis[2], axis[1]], [axis[2], 0.0, -axis[0]], [-axis[1], axis[0], 0.0]])
    rotation = c * np.eye(3) + s * cross + (1.0 - c) * np.outer(axis, axis)

    element = bound_hex()
    transform = np.kron(np.eye(8), rotation)
    np.testing.assert_allclose(
        element.stiffness_matrix(DISTORTED @ rotation.T),
        transform @ element.stiffness_matrix(DISTORTED) @ transform.T,
        rtol=1e-10,
        atol=1e-6,
    )


def test_strain_energy_of_a_linear_field_matches_the_continuum_value():
    element = bound_hex(DISTORTED)
    displacements = linear_field(DISTORTED, PATCH_GRADIENT)
    strain = voigt_strain(PATCH_GRADIENT)
    expected = 0.5 * element.volume(DISTORTED) * float(
        strain @ element.constitutive_matrix @ strain
    )
    energy = 0.5 * float(displacements @ element.stiffness_matrix(DISTORTED) @ displacements)
    assert energy == pytest.approx(expected, rel=1e-12)


def test_the_brick_is_softer_than_a_tetrahedral_split_of_the_same_cell():
    """The six Kuhn tets spanning one cell are stiffer than the brick they fill."""
    hexahedral = ModalSolver(
        hex_block_mesh(0.4, 0.15, 0.1, 2, 1, 1, STEEL, support="cantilever")
    ).solve(num_modes=1)
    tetrahedral = ModalSolver(
        tet_block_mesh(0.4, 0.15, 0.1, 2, 1, 1, STEEL, support="cantilever")
    ).solve(num_modes=1)
    assert hexahedral.frequencies[0] < tetrahedral.frequencies[0]


# ------------------------------------------------------------------ patch tests


@pytest.mark.parametrize(
    "gradient",
    [
        1e-3 * np.eye(3),
        PATCH_GRADIENT,
        1e-3 * np.array([[0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 0.0]]),
    ],
)
def test_single_element_reproduces_constant_strain_exactly(gradient):
    element = bound_hex(DISTORTED)
    displacements = linear_field(DISTORTED, gradient)
    strain = voigt_strain(gradient)
    expected_stress = element.constitutive_matrix @ strain
    for point in SAMPLE_POINTS:
        np.testing.assert_allclose(
            element.strain(DISTORTED, displacements, *point), strain, rtol=1e-11, atol=1e-16
        )
        np.testing.assert_allclose(
            element.stress(DISTORTED, displacements, *point),
            expected_stress,
            rtol=1e-11,
            atol=1e-11 * np.abs(expected_stress).max(),
        )


def test_constant_strain_state_is_in_equilibrium_with_its_boundary_tractions():
    element = bound_hex(DISTORTED)
    forces = element.stiffness_matrix(DISTORTED) @ linear_field(DISTORTED, PATCH_GRADIENT)
    scale = np.abs(forces).max()
    for axis in range(3):
        assert abs(forces[axis::3].sum()) < 1e-9 * scale


def test_wrong_displacement_count_is_rejected():
    with pytest.raises(ElementError, match="expected 24 nodal displacements"):
        bound_hex().strain(DISTORTED, np.zeros(12))


#: Extent of the distorted patch box.
PATCH_SPAN = np.array([0.24, 0.12, 0.18])


def distorted_patch(cells: tuple[int, int, int] = (3, 3, 3)):
    """A structured hex box whose interior nodes are pulled off the regular grid.

    Returns ``(model, coordinates)``. Only interior nodes move, so the outer
    faces stay planar and can carry a prescribed linear displacement field --
    the three-dimensional MacNeal-Harder patch.
    """
    nx, ny, nz = cells
    cell = PATCH_SPAN / np.array(cells)
    model = Model(dofs=SOLID_DOFS, name="hex patch")
    coordinates: dict[int, np.ndarray] = {}

    def node_id(i: int, j: int, k: int) -> int:
        return (k * (ny + 1) + j) * (nx + 1) + i

    interior = 0
    for k in range(nz + 1):
        for j in range(ny + 1):
            for i in range(nx + 1):
                point = np.array([i, j, k], dtype=float) * cell
                if 0 < i < nx and 0 < j < ny and 0 < k < nz:
                    n = interior
                    offset = np.array(
                        [np.sin(1.3 * n + 0.4), np.cos(2.1 * n + 1.1), np.sin(0.7 * n + 2.3)]
                    )
                    point = point + 0.2 * cell * offset
                    interior += 1
                coordinates[node_id(i, j, k)] = point
                model.add_node(node_id(i, j, k), point)

    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                corners = [
                    node_id(i + (c & 1), j + ((c >> 1) & 1), k + ((c >> 2) & 1))
                    for c in range(8)
                ]
                model.add_element(
                    Hex8Element([corners[c] for c in (0, 1, 3, 2, 4, 5, 7, 6)], PATCH_MATERIAL)
                )

    return model, coordinates


def patch_boundary_problem(model: Model, coordinates: dict[int, np.ndarray]):
    """Prescribe ``u = PATCH_GRADIENT x`` on every boundary node of the patch."""
    exact = np.zeros(model.num_dofs, dtype=float)
    prescribed: dict[int, float] = {}
    for node_id, point in coordinates.items():
        displacement = PATCH_GRADIENT @ point
        on_boundary = bool(
            np.any(np.isclose(point, 0.0)) or np.any(np.isclose(point, PATCH_SPAN))
        )
        for dof, value in zip(SOLID_DOFS, displacement, strict=True):
            index = model.dof_index(node_id, dof)
            exact[index] = value
            if on_boundary:
                prescribed[index] = value
    return prescribed, exact


def test_the_distorted_patch_is_a_valid_mesh():
    model, _ = distorted_patch()
    assert model.num_nodes == 4**3
    assert model.num_elements == 27
    volumes = [element.volume(model.node_coords(element.node_ids)) for element in model.elements]
    assert min(volumes) > 0.0
    assert sum(volumes) == pytest.approx(float(np.prod(PATCH_SPAN)), rel=1e-12)


def test_the_distorted_patch_recovers_the_interior_displacements():
    model, coordinates = distorted_patch()
    prescribed, exact = patch_boundary_problem(model, coordinates)
    computed = solve_prescribed(model, prescribed)
    interior = np.setdiff1d(np.arange(model.num_dofs), np.array(sorted(prescribed), dtype=int))
    assert interior.size == 3 * 8
    assert np.abs(computed[interior] - exact[interior]).max() < 1e-14 * np.abs(exact).max()


def test_the_distorted_patch_yields_the_exact_constant_stress():
    model, coordinates = distorted_patch()
    prescribed, _ = patch_boundary_problem(model, coordinates)
    computed = solve_prescribed(model, prescribed)
    expected = solid_constitutive_matrix(PATCH_MATERIAL) @ voigt_strain(PATCH_GRADIENT)
    assert np.abs(expected).min() > 1.0  # no component is trivially zero
    for element in model.elements:
        coords = model.node_coords(element.node_ids)
        values = computed[element.global_dofs(model)]
        for point in SAMPLE_POINTS:
            np.testing.assert_allclose(element.stress(coords, values, *point), expected, rtol=1e-9)


def test_a_roller_supported_block_recovers_the_modulus_and_poisson_ratio():
    """Uniaxial extension is a constant strain state, so the mesh must be exact."""
    length, width, height = 0.4, 0.15, 0.1
    stretch = 1e-4
    model = hex_block_mesh(length, width, height, 2, 2, 2, PATCH_MATERIAL, support="free")

    prescribed: dict[int, float] = {}
    for node in model.nodes:
        for axis, dof in enumerate(SOLID_DOFS):
            if np.isclose(node.coords[axis], 0.0):
                prescribed[model.dof_index(node.id, dof)] = 0.0
        if np.isclose(node.x, length):
            prescribed[model.dof_index(node.id, DOF.UX)] = stretch * length
    computed = solve_prescribed(model, prescribed)

    expected = np.array([PATCH_MATERIAL.E * stretch, 0.0, 0.0, 0.0, 0.0, 0.0])
    scale = PATCH_MATERIAL.E * stretch
    for element in model.elements:
        stress = element.stress(
            model.node_coords(element.node_ids), computed[element.global_dofs(model)]
        )
        np.testing.assert_allclose(stress, expected, atol=1e-9 * scale)

    corner = next(
        node for node in model.nodes if np.allclose(node.coords, [length, width, height])
    )
    assert computed[model.dof_index(corner.id, DOF.UY)] == pytest.approx(
        -PATCH_MATERIAL.nu * stretch * width, rel=1e-10
    )
    assert computed[model.dof_index(corner.id, DOF.UZ)] == pytest.approx(
        -PATCH_MATERIAL.nu * stretch * height, rel=1e-10
    )


# ------------------------------------------------------------------------ mass


@pytest.mark.parametrize("coords", [CUBE, PARALLELEPIPED])
def test_consistent_mass_matches_the_closed_form_on_a_parallelepiped(coords):
    """``int N_i N_j dV = V 2^s / 216`` with ``s`` the shared natural coordinates."""
    element = bound_hex(coords)
    expected = np.kron(cube_mass_pattern(), np.eye(3)) * (
        STEEL.density * element.volume(coords) / 216.0
    )
    np.testing.assert_allclose(element.mass_matrix(coords), expected, rtol=1e-13)


def test_consistent_mass_is_symmetric_and_positive_definite():
    m = bound_hex(DISTORTED).mass_matrix(DISTORTED)
    np.testing.assert_allclose(m, m.T, atol=1e-18)
    assert np.linalg.eigvalsh(m).min() > 0.0


def test_consistent_mass_reproduces_the_total_mass_in_each_direction():
    element = bound_hex(DISTORTED)
    m = element.mass_matrix(DISTORTED)
    total = element.total_mass(DISTORTED)
    for axis in range(3):
        assert m[axis::3, axis::3].sum() == pytest.approx(total, rel=1e-13)
    assert m[0::3, 1::3].sum() == pytest.approx(0.0, abs=1e-18)


def test_rigid_translation_kinetic_energy_equals_the_total_mass():
    element = bound_hex(DISTORTED)
    m = element.mass_matrix(DISTORTED)
    velocity = np.tile([1.0, 0.0, 0.0], 8)
    assert float(velocity @ m @ velocity) == pytest.approx(element.total_mass(DISTORTED), rel=1e-13)


def test_the_mass_row_sums_are_quadrature_exact_on_a_distorted_brick():
    """Refining the rule changes the consistent mass but not the lumped one."""
    coarse = bound_hex(DISTORTED)
    fine = bound_hex(DISTORTED, integration_order=3)
    np.testing.assert_allclose(
        coarse.consistent_mass_matrix(DISTORTED).sum(axis=1),
        fine.consistent_mass_matrix(DISTORTED).sum(axis=1),
        rtol=1e-13,
    )
    difference = np.abs(
        coarse.consistent_mass_matrix(DISTORTED) - fine.consistent_mass_matrix(DISTORTED)
    ).max()
    assert difference > 0.0  # the off-diagonal terms genuinely are approximated


def test_lumped_mass_is_diagonal_and_conserves_the_total_mass():
    element = bound_hex(DISTORTED, lumped_mass=True)
    m = element.mass_matrix(DISTORTED)
    np.testing.assert_allclose(m - np.diag(np.diag(m)), np.zeros((24, 24)), atol=1e-18)
    for axis in range(3):
        assert np.diag(m)[axis::3].sum() == pytest.approx(
            element.total_mass(DISTORTED), rel=1e-13
        )


def test_lumped_mass_is_the_row_sum_of_the_consistent_mass():
    element = bound_hex(DISTORTED, lumped_mass=True)
    consistent = element.consistent_mass_matrix(DISTORTED)
    np.testing.assert_allclose(np.diag(element.mass_matrix(DISTORTED)), consistent.sum(axis=1))


def test_lumped_mass_of_the_cube_is_an_eighth_per_node():
    element = bound_hex(CUBE, lumped_mass=True)
    np.testing.assert_allclose(
        np.diag(element.mass_matrix(CUBE)), element.total_mass(CUBE) / 8.0, rtol=1e-13
    )


def test_a_massless_material_gives_a_zero_mass_matrix():
    model = Model(dofs=SOLID_DOFS)
    for index, point in enumerate(CUBE):
        model.add_node(index, point)
    element = model.add_element(Hex8Element(range(8), Material(E=1.0e9, density=0.0, nu=0.3)))
    np.testing.assert_array_equal(element.mass_matrix(CUBE), np.zeros((24, 24)))
    assert element.total_mass(CUBE) == 0.0


# ------------------------------------------------------------------ mesh & model


def test_hex_block_mesh_builds_the_expected_grid():
    model = hex_block_mesh(0.3, 0.2, 0.1, 3, 2, 2, STEEL, support="free")
    assert model.num_nodes == 4 * 3 * 3
    assert model.num_elements == 3 * 2 * 2
    assert model.dofs == SOLID_DOFS
    assert model.constrained_dofs.size == 0
    corner = model.node(model.num_nodes - 1)
    assert (corner.x, corner.y, corner.z) == pytest.approx((0.3, 0.2, 0.1))


def test_hex_block_mesh_fills_the_box_with_positive_volumes():
    model = hex_block_mesh(0.3, 0.2, 0.1, 3, 2, 2, STEEL, support="free")
    volumes = [element.volume(model.node_coords(element.node_ids)) for element in model.elements]
    assert min(volumes) > 0.0
    assert sum(volumes) == pytest.approx(0.3 * 0.2 * 0.1, rel=1e-12)


def test_hex_and_tet_blocks_number_their_nodes_identically():
    """The two generators are interchangeable discretizations of the same box."""
    hexahedral = hex_block_mesh(0.3, 0.2, 0.1, 3, 2, 2, STEEL, support="free")
    tetrahedral = tet_block_mesh(0.3, 0.2, 0.1, 3, 2, 2, STEEL, support="free")
    assert hexahedral.num_nodes == tetrahedral.num_nodes
    for a, b in zip(hexahedral.nodes, tetrahedral.nodes, strict=True):
        assert a.id == b.id
        np.testing.assert_allclose(a.coords, b.coords, atol=1e-15)


def test_hex_block_mesh_clamps_the_cantilever_root():
    model = hex_block_mesh(1.0, 0.1, 0.1, 4, 2, 2, STEEL, support="cantilever")
    root = [node.id for node in model.nodes if np.isclose(node.x, 0.0)]
    assert len(root) == 3 * 3
    assert model.constrained_dofs.size == 3 * len(root)
    for node_id in root:
        for dof in SOLID_DOFS:
            assert model.is_constrained(node_id, dof)


def test_hex_block_mesh_supports_a_simply_supported_span():
    model = hex_block_mesh(1.0, 0.1, 0.1, 4, 1, 1, STEEL, support="simply-supported")
    ends = [node for node in model.nodes if np.isclose(node.x, 0.0) or np.isclose(node.x, 1.0)]
    for node in ends:
        assert model.is_constrained(node.id, DOF.UY)
        assert model.is_constrained(node.id, DOF.UZ)
    axial = [node.id for node in model.nodes if model.is_constrained(node.id, DOF.UX)]
    assert axial == [0]


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"support": "pinned"}, "unknown support"),
        ({"num_x": 0}, "num_x must be >= 1"),
        ({"num_z": -2}, "num_z must be >= 1"),
        ({"length": -1.0}, "length must be positive"),
        ({"height": 0.0}, "height must be positive"),
    ],
)
def test_hex_block_mesh_validates_its_arguments(kwargs, match):
    arguments = {
        "length": 1.0,
        "width": 0.1,
        "height": 0.1,
        "num_x": 4,
        "num_y": 1,
        "num_z": 1,
        "material": STEEL,
    }
    arguments.update(kwargs)
    with pytest.raises(ModelError, match=match):
        hex_block_mesh(**arguments)


def test_the_assembled_block_reproduces_the_analytic_mass():
    length, width, height = 0.4, 0.25, 0.06
    model = hex_block_mesh(length, width, height, 3, 2, 2, STEEL, support="free")
    system = assemble_system(model)
    assert system.total_mass == pytest.approx(STEEL.density * length * width * height, rel=1e-12)


def test_the_assembled_block_matrices_are_symmetric():
    model = hex_block_mesh(0.4, 0.25, 0.06, 3, 2, 2, STEEL, support="free")
    system = assemble_system(model)
    for matrix in (system.K, system.M):
        assert abs(matrix - matrix.T).max() <= 1e-6 * abs(matrix).max()


def test_the_mesh_builder_can_add_a_brick():
    from openfemlab.mesh.simple import MeshBuilder

    mesh = MeshBuilder(dofs=SOLID_DOFS, name="one hex")
    for index, point in enumerate(CUBE):
        mesh.add_node(index, *point)
    element = mesh.add_hex8(range(8), STEEL)
    assert isinstance(element, Hex8Element)
    assert element.volume(CUBE) == pytest.approx(1.0)


# ---------------------------------------------------------------------- modal


def test_a_free_block_has_six_rigid_body_modes():
    model = hex_block_mesh(0.3, 0.2, 0.1, 3, 2, 2, STEEL, support="free")
    result = ModalSolver(model).solve(num_modes=8)
    assert int(np.sum(result.rigid_body_modes)) == 6
    np.testing.assert_allclose(result.frequencies[:6], np.zeros(6), atol=1e-2)
    assert result.frequencies[6] > 1.0e3


def test_block_modes_are_mass_orthonormal():
    model = hex_block_mesh(0.4, 0.15, 0.1, 4, 2, 2, STEEL, support="cantilever")
    result = ModalSolver(model).solve(num_modes=6)
    assert result.orthogonality_error() < 1e-9


def test_axial_modes_converge_quadratically_to_the_continuum_bar():
    """With lateral motion suppressed and ``nu = 0`` the block is a 1D bar."""
    material = Material(E=2.1e11, density=7850.0, nu=0.0)
    length = 1.0
    exact = np.sqrt(material.E / material.density) / (4.0 * length)

    errors = []
    for num_x in (4, 8, 16):
        model = hex_block_mesh(length, 0.1, 0.1, num_x, 1, 1, material, support="cantilever")
        model.fix_dof_globally((DOF.UY, DOF.UZ))
        errors.append(ModalSolver(model).solve(num_modes=1).frequencies[0] / exact - 1.0)

    # A conforming displacement element with consistent mass converges from above.
    assert all(error > 0.0 for error in errors)
    assert errors[0] > errors[1] > errors[2]
    assert errors[-1] < 1e-3
    assert errors[0] / errors[1] > 3.0
    assert errors[1] / errors[2] > 3.0


def test_lumped_mass_block_is_not_stiffer_than_the_consistent_one():
    arguments = {"support": "cantilever"}
    consistent = ModalSolver(
        hex_block_mesh(0.4, 0.15, 0.1, 4, 2, 2, STEEL, **arguments)
    ).solve(num_modes=4)
    lumped = ModalSolver(
        hex_block_mesh(0.4, 0.15, 0.1, 4, 2, 2, STEEL, lumped_mass=True, **arguments)
    ).solve(num_modes=4)
    assert np.all(lumped.frequencies <= consistent.frequencies * (1.0 + 1e-12))
    np.testing.assert_allclose(lumped.frequencies, consistent.frequencies, rtol=0.2)


def test_bending_converges_towards_euler_bernoulli_faster_than_the_tetrahedron():
    """Shear locking, pinned -- with the TET4 comparison that motivates the brick."""
    length, width, height = 1.0, 0.05, 0.05
    inertia = width * height**3 / 12.0
    reference = (1.875104**2 / (2 * np.pi)) * np.sqrt(
        STEEL.E * inertia / (STEEL.density * width * height * length**4)
    )

    errors = []
    for cells in [(8, 1, 1), (16, 2, 2), (32, 4, 4)]:
        model = hex_block_mesh(length, width, height, *cells, STEEL, support="cantilever")
        errors.append(ModalSolver(model).solve(num_modes=1).frequencies[0] / reference - 1.0)

    assert all(error > 0.0 for error in errors)
    assert errors[0] > errors[1] > errors[2]
    # One element through the thickness locks hard (+89 %); at 2475 DOF the brick
    # is inside 10 %, where TET4 on the same grid is still 25 % stiff.
    assert errors[0] > 0.5
    assert 0.03 < errors[-1] < 0.15

    tetrahedral = ModalSolver(
        tet_block_mesh(length, width, height, 32, 4, 4, STEEL, support="cantilever")
    ).solve(num_modes=1)
    assert tetrahedral.frequencies[0] / reference - 1.0 > 2.0 * errors[-1]
