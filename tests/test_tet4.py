"""TET4 constant-strain tetrahedron: formulation, patch tests and modal checks.

The element is verified in three layers, mirroring ``tests/test_quad4.py``:

* kernel level -- shape functions, the 3D constitutive matrix, geometry;
* element/patch level -- rigid-body invariance, zero-energy mode count, exact
  reproduction of constant strain states on a distorted multi-element patch;
* model level -- Kuhn-subdivided blocks, mass bookkeeping and modal accuracy
  against the closed-form axial bar spectrum, plus the bending locking the
  element is known for.
"""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.core.assembly import assemble_stiffness, assemble_system
from openfemlab.core.elements import Tet4Element, solid_constitutive_matrix
from openfemlab.core.model import DOF, Material, Model
from openfemlab.exceptions import ElementError, ModelError
from openfemlab.mesh.simple import _KUHN_TETRAHEDRA, tet_block_mesh
from openfemlab.solver.modal import ModalSolver

STEEL = Material(E=2.1e11, density=7850.0, nu=0.3)
PATCH_MATERIAL = Material(E=1.0e6, density=1.0, nu=0.25)

SOLID_DOFS = (DOF.UX, DOF.UY, DOF.UZ)

#: The unit corner tetrahedron: natural and physical coordinates coincide.
REFERENCE = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])

#: A deliberately irregular tetrahedron with no axis-aligned edge.
DISTORTED = np.array(
    [[0.1, -0.2, 0.05], [1.3, 0.1, -0.15], [0.4, 1.1, 0.2], [0.2, 0.3, 0.9]]
)

#: Displacement gradient of the patch field; the three normal strains differ and
#: none of the resulting stress components vanishes.
PATCH_GRADIENT = 1e-3 * np.array([[1.0, 0.4, -0.2], [0.3, -0.5, 0.5], [-0.1, 0.2, 0.8]])


def bound_tet(coords: np.ndarray = DISTORTED, **kwargs) -> Tet4Element:
    """A TET4 bound to a three-DOF solid model holding ``coords``."""
    model = Model(dofs=SOLID_DOFS, name="single tet")
    for index, point in enumerate(np.asarray(coords, dtype=float)):
        model.add_node(index, point)
    return model.add_element(Tet4Element(range(4), STEEL, **kwargs))


def determinant_volume(coords: np.ndarray) -> float:
    """Signed volume from the 4x4 determinant, independent of the element code."""
    matrix = np.column_stack((np.ones(4), np.asarray(coords, dtype=float)))
    return float(np.linalg.det(matrix)) / 6.0


def linear_field(coords: np.ndarray, gradient: np.ndarray) -> np.ndarray:
    """Nodal displacements of ``u = G x``, in node-major DOF order."""
    return (np.asarray(coords, dtype=float) @ np.asarray(gradient, dtype=float).T).reshape(-1)


def voigt_strain(gradient: np.ndarray) -> np.ndarray:
    """Engineering strain ``[exx, eyy, ezz, gxy, gyz, gzx]`` of a displacement gradient."""
    g = np.asarray(gradient, dtype=float)
    return np.array(
        [g[0, 0], g[1, 1], g[2, 2], g[0, 1] + g[1, 0], g[1, 2] + g[2, 1], g[0, 2] + g[2, 0]]
    )


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
    for point in [(0.0, 0.0, 0.0), (0.25, 0.25, 0.25), (0.6, 0.1, 0.2), (1.0, 0.0, 0.0)]:
        assert Tet4Element.shape_functions(*point).sum() == pytest.approx(1.0, abs=1e-15)


def test_shape_functions_are_nodal_kronecker_deltas():
    natural = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]
    for index, point in enumerate(natural):
        np.testing.assert_allclose(Tet4Element.shape_functions(*point), np.eye(4)[index])


def test_shape_functions_interpolate_the_geometry():
    for point in [(0.25, 0.25, 0.25), (0.5, 0.2, 0.1)]:
        shape = Tet4Element.shape_functions(*point)
        # The reference tetrahedron maps natural to physical coordinates identically.
        np.testing.assert_allclose(shape @ REFERENCE, point, atol=1e-15)


def test_shape_function_derivatives_match_finite_differences():
    base = np.array([0.2, 0.3, 0.15])
    step = 1e-6
    analytic = Tet4Element.shape_function_derivatives()
    for axis in range(3):
        offset = np.zeros(3)
        offset[axis] = step
        numeric = (
            Tet4Element.shape_functions(*(base + offset))
            - Tet4Element.shape_functions(*(base - offset))
        ) / (2 * step)
        np.testing.assert_allclose(analytic[axis], numeric, atol=1e-9)


def test_physical_shape_gradients_sum_to_zero():
    """A constant displacement produces no strain, which is exactly this identity."""
    gradient, _ = bound_tet().jacobian(DISTORTED)
    np.testing.assert_allclose(gradient.sum(axis=1), np.zeros(3), atol=1e-13)


def test_physical_shape_gradients_reproduce_the_coordinate_derivatives():
    gradient, _ = bound_tet().jacobian(DISTORTED)
    np.testing.assert_allclose(gradient @ DISTORTED, np.eye(3), atol=1e-13)


# ------------------------------------------------------------------ constitutive


def test_solid_matrix_matches_the_lame_closed_form():
    material = Material(E=200.0, density=1.0, nu=0.25)
    lam, mu = 80.0, 80.0
    expected = np.diag([2.0 * mu, 2.0 * mu, 2.0 * mu, mu, mu, mu])
    expected[:3, :3] += lam
    np.testing.assert_allclose(solid_constitutive_matrix(material), expected, rtol=1e-14)


def test_solid_matrix_is_symmetric_and_positive_definite():
    D = solid_constitutive_matrix(STEEL)
    np.testing.assert_allclose(D, D.T, rtol=1e-15)
    assert np.linalg.eigvalsh(D).min() > 0.0


def test_hydrostatic_strain_gives_the_bulk_modulus():
    strain = np.array([1.0, 1.0, 1.0, 0.0, 0.0, 0.0])
    bulk = STEEL.E / (3.0 * (1.0 - 2.0 * STEEL.nu))
    stress = solid_constitutive_matrix(STEEL) @ strain
    np.testing.assert_allclose(stress[:3], 3.0 * bulk, rtol=1e-13)
    np.testing.assert_allclose(stress[3:], np.zeros(3), atol=1e-9)


def test_shear_block_is_the_shear_modulus():
    D = solid_constitutive_matrix(STEEL)
    np.testing.assert_allclose(D[3:, 3:], STEEL.shear_modulus * np.eye(3), rtol=1e-14)
    np.testing.assert_allclose(D[:3, 3:], np.zeros((3, 3)), atol=1e-9)


def test_a_vanishing_poisson_ratio_decouples_the_normal_directions():
    material = Material(E=1.0, density=0.0, nu=0.0)
    np.testing.assert_allclose(
        solid_constitutive_matrix(material), np.diag([1.0, 1.0, 1.0, 0.5, 0.5, 0.5]), atol=1e-15
    )


def test_the_material_stiffens_as_it_approaches_incompressibility():
    soft = solid_constitutive_matrix(Material(E=1.0, density=0.0, nu=0.1))
    stiff = solid_constitutive_matrix(Material(E=1.0, density=0.0, nu=0.45))
    assert stiff[0, 0] > soft[0, 0]
    # Only the volumetric part grows; the shear modulus falls with 1 / (1 + nu).
    assert stiff[3, 3] < soft[3, 3]


# --------------------------------------------------------------------- geometry


@pytest.mark.parametrize("coords", [REFERENCE, DISTORTED])
def test_volume_matches_the_determinant_formula(coords):
    element = bound_tet(coords)
    assert element.volume(coords) == pytest.approx(determinant_volume(coords), rel=1e-14)


def test_the_reference_tetrahedron_has_the_textbook_volume():
    assert bound_tet(REFERENCE).volume(REFERENCE) == pytest.approx(1.0 / 6.0, rel=1e-15)


def test_total_mass_is_density_times_volume():
    element = bound_tet(DISTORTED)
    expected = STEEL.density * determinant_volume(DISTORTED)
    assert element.total_mass(DISTORTED) == pytest.approx(expected, rel=1e-14)


def test_inverted_node_order_is_rejected():
    inverted = REFERENCE[[0, 2, 1, 3]]
    element = bound_tet(REFERENCE)
    with pytest.raises(ElementError, match="non-positive Jacobian"):
        element.stiffness_matrix(inverted)


def test_coplanar_nodes_are_rejected():
    flat = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]])
    element = bound_tet(REFERENCE)
    with pytest.raises(ElementError, match="non-positive Jacobian"):
        element.stiffness_matrix(flat)


def test_planar_coordinates_are_rejected():
    element = bound_tet(REFERENCE)
    with pytest.raises(ElementError, match="three coordinates per node"):
        element.stiffness_matrix(REFERENCE[:, :2])


def test_a_rigid_translation_of_the_geometry_leaves_the_matrices_alone():
    shifted = DISTORTED + np.array([3.5, -2.0, 7.25])
    element = bound_tet(DISTORTED)
    np.testing.assert_allclose(
        element.stiffness_matrix(shifted), element.stiffness_matrix(DISTORTED), rtol=1e-12
    )


def test_wrong_node_count_is_rejected():
    with pytest.raises(ElementError, match="expects 4 nodes"):
        Tet4Element((1, 2, 3), STEEL)


def test_repeated_nodes_are_rejected():
    with pytest.raises(ElementError, match="repeated nodes"):
        Tet4Element((1, 2, 2, 3), STEEL)


def test_element_requires_all_three_translations():
    model = Model(dofs=(DOF.UX, DOF.UY), name="planar only")
    for index, point in enumerate(REFERENCE):
        model.add_node(index, point)
    with pytest.raises(ElementError, match="UZ"):
        model.add_element(Tet4Element(range(4), STEEL))


# -------------------------------------------------------------------- stiffness


def test_stiffness_is_symmetric_and_positive_semidefinite():
    k = bound_tet().stiffness_matrix(DISTORTED)
    assert k.shape == (12, 12)
    np.testing.assert_allclose(k, k.T, rtol=0, atol=1e-9 * np.abs(k).max())
    eigenvalues = np.linalg.eigvalsh(k)
    assert eigenvalues.min() > -1e-8 * eigenvalues.max()


def test_the_element_leaves_exactly_six_zero_energy_modes():
    eigenvalues = np.linalg.eigvalsh(bound_tet().stiffness_matrix(DISTORTED))
    zeros = np.sum(np.abs(eigenvalues) < 1e-8 * eigenvalues.max())
    assert zeros == 6  # the six spatial rigid-body motions, no hourglassing


@pytest.mark.parametrize("axis", [0, 1, 2])
def test_rigid_body_translation_produces_no_nodal_force(axis):
    k = bound_tet().stiffness_matrix(DISTORTED)
    motion = np.tile(np.eye(3)[axis], 4)
    np.testing.assert_allclose(k @ motion, np.zeros(12), atol=1e-12 * np.abs(k).max())


@pytest.mark.parametrize("axis", [0, 1, 2])
def test_rigid_body_rotation_produces_no_strain_energy(axis):
    element = bound_tet()
    k = element.stiffness_matrix(DISTORTED)
    rotation = np.cross(np.eye(3)[axis], DISTORTED).reshape(-1)
    reference = float(np.abs(k).max() * rotation @ rotation)
    assert float(rotation @ k @ rotation) == pytest.approx(0.0, abs=1e-12 * reference)
    np.testing.assert_allclose(element.strain(DISTORTED, rotation), np.zeros(6), atol=1e-13)


def test_stiffness_scales_linearly_with_the_modulus():
    base = bound_tet(DISTORTED).stiffness_matrix(DISTORTED)
    model = Model(dofs=SOLID_DOFS)
    for index, point in enumerate(DISTORTED):
        model.add_node(index, point)
    stiffer = model.add_element(
        Tet4Element(range(4), Material(E=3 * STEEL.E, density=1.0, nu=STEEL.nu))
    )
    np.testing.assert_allclose(stiffer.stiffness_matrix(DISTORTED), 3.0 * base, rtol=1e-13)


def test_stiffness_is_invariant_under_a_spatial_rotation():
    angle = 0.7
    c, s = np.cos(angle), np.sin(angle)
    # A rotation about (1, 1, 1) / sqrt(3), written out via Rodrigues' formula.
    axis = np.ones(3) / np.sqrt(3.0)
    cross = np.array([[0.0, -axis[2], axis[1]], [axis[2], 0.0, -axis[0]], [-axis[1], axis[0], 0.0]])
    rotation = c * np.eye(3) + s * cross + (1.0 - c) * np.outer(axis, axis)

    element = bound_tet()
    transform = np.kron(np.eye(4), rotation)
    np.testing.assert_allclose(
        element.stiffness_matrix(DISTORTED @ rotation.T),
        transform @ element.stiffness_matrix(DISTORTED) @ transform.T,
        rtol=1e-10,
        atol=1e-6,
    )


def test_strain_energy_of_a_linear_field_matches_the_continuum_value():
    element = bound_tet(DISTORTED)
    displacements = linear_field(DISTORTED, PATCH_GRADIENT)
    strain = voigt_strain(PATCH_GRADIENT)
    expected = 0.5 * element.volume(DISTORTED) * float(
        strain @ element.constitutive_matrix @ strain
    )
    energy = 0.5 * float(displacements @ element.stiffness_matrix(DISTORTED) @ displacements)
    assert energy == pytest.approx(expected, rel=1e-12)


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
    element = bound_tet(DISTORTED)
    displacements = linear_field(DISTORTED, gradient)
    strain = voigt_strain(gradient)
    np.testing.assert_allclose(
        element.strain(DISTORTED, displacements), strain, rtol=1e-11, atol=1e-16
    )
    expected_stress = element.constitutive_matrix @ strain
    np.testing.assert_allclose(
        element.stress(DISTORTED, displacements),
        expected_stress,
        rtol=1e-11,
        atol=1e-11 * np.abs(expected_stress).max(),
    )


def test_constant_strain_state_is_in_equilibrium_with_its_boundary_tractions():
    element = bound_tet(DISTORTED)
    forces = element.stiffness_matrix(DISTORTED) @ linear_field(DISTORTED, PATCH_GRADIENT)
    scale = np.abs(forces).max()
    for axis in range(3):
        assert abs(forces[axis::3].sum()) < 1e-9 * scale


def distorted_patch(cells: tuple[int, int, int] = (3, 3, 3)):
    """A Kuhn-subdivided box whose interior nodes are pulled off the regular grid.

    Returns ``(model, coordinates)``. Only interior nodes move, so the outer
    faces stay planar and can carry a prescribed linear displacement field.
    """
    span = np.array([0.24, 0.12, 0.18])
    nx, ny, nz = cells
    cell = span / np.array(cells)
    model = Model(dofs=SOLID_DOFS, name="tet patch")
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
                for tet in _KUHN_TETRAHEDRA:
                    model.add_element(Tet4Element([corners[c] for c in tet], PATCH_MATERIAL))

    return model, coordinates


def patch_boundary_problem(model: Model, coordinates: dict[int, np.ndarray]):
    """Prescribe ``u = PATCH_GRADIENT x`` on every boundary node of the patch."""
    span = np.array([0.24, 0.12, 0.18])
    exact = np.zeros(model.num_dofs, dtype=float)
    prescribed: dict[int, float] = {}
    for node_id, point in coordinates.items():
        displacement = PATCH_GRADIENT @ point
        on_boundary = bool(np.any(np.isclose(point, 0.0)) or np.any(np.isclose(point, span)))
        for dof, value in zip(SOLID_DOFS, displacement, strict=True):
            index = model.dof_index(node_id, dof)
            exact[index] = value
            if on_boundary:
                prescribed[index] = value
    return prescribed, exact


def test_the_distorted_patch_is_a_valid_mesh():
    model, _ = distorted_patch()
    assert model.num_nodes == 4**3
    assert model.num_elements == 27 * 6
    volumes = [element.volume(model.node_coords(element.node_ids)) for element in model.elements]
    assert min(volumes) > 0.0
    assert sum(volumes) == pytest.approx(0.24 * 0.12 * 0.18, rel=1e-12)


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
        stress = element.stress(
            model.node_coords(element.node_ids), computed[element.global_dofs(model)]
        )
        np.testing.assert_allclose(stress, expected, rtol=1e-9)


def test_a_roller_supported_block_recovers_the_modulus_and_poisson_ratio():
    """Uniaxial extension is a constant strain state, so the mesh must be exact."""
    length, width, height = 0.4, 0.15, 0.1
    stretch = 1e-4
    model = tet_block_mesh(length, width, height, 2, 2, 2, PATCH_MATERIAL, support="free")

    prescribed: dict[int, float] = {}
    for node in model.nodes:
        for axis, dof in enumerate(SOLID_DOFS):
            if np.isclose(node.coords[axis], 0.0):
                prescribed[model.dof_index(node.id, dof)] = 0.0
        if np.isclose(node.x, length):
            prescribed[model.dof_index(node.id, DOF.UX)] = stretch * length
    computed = solve_prescribed(model, prescribed)

    axial = stretch
    expected = np.array([PATCH_MATERIAL.E * axial, 0.0, 0.0, 0.0, 0.0, 0.0])
    scale = PATCH_MATERIAL.E * axial
    for element in model.elements:
        stress = element.stress(
            model.node_coords(element.node_ids), computed[element.global_dofs(model)]
        )
        np.testing.assert_allclose(stress, expected, atol=1e-9 * scale)

    corner = next(
        node
        for node in model.nodes
        if np.allclose(node.coords, [length, width, height])
    )
    assert computed[model.dof_index(corner.id, DOF.UY)] == pytest.approx(
        -PATCH_MATERIAL.nu * axial * width, rel=1e-10
    )
    assert computed[model.dof_index(corner.id, DOF.UZ)] == pytest.approx(
        -PATCH_MATERIAL.nu * axial * height, rel=1e-10
    )


# ------------------------------------------------------------------------ mass


def test_consistent_mass_matches_the_closed_form():
    element = bound_tet(DISTORTED)
    pattern = (np.ones((4, 4)) + np.eye(4)) / 20.0
    expected = np.kron(pattern, np.eye(3)) * (STEEL.density * element.volume(DISTORTED))
    np.testing.assert_allclose(element.mass_matrix(DISTORTED), expected, rtol=1e-14)


def test_consistent_mass_is_symmetric_and_positive_definite():
    m = bound_tet(DISTORTED).mass_matrix(DISTORTED)
    np.testing.assert_allclose(m, m.T, atol=1e-18)
    assert np.linalg.eigvalsh(m).min() > 0.0


def test_consistent_mass_reproduces_the_total_mass_in_each_direction():
    element = bound_tet(DISTORTED)
    m = element.mass_matrix(DISTORTED)
    total = element.total_mass(DISTORTED)
    for axis in range(3):
        assert m[axis::3, axis::3].sum() == pytest.approx(total, rel=1e-13)
    assert m[0::3, 1::3].sum() == pytest.approx(0.0, abs=1e-18)


def test_rigid_translation_kinetic_energy_equals_the_total_mass():
    element = bound_tet(DISTORTED)
    m = element.mass_matrix(DISTORTED)
    velocity = np.tile([1.0, 0.0, 0.0], 4)
    assert float(velocity @ m @ velocity) == pytest.approx(element.total_mass(DISTORTED), rel=1e-13)


def test_lumped_mass_is_diagonal_and_puts_a_quarter_on_each_node():
    element = bound_tet(DISTORTED, lumped_mass=True)
    m = element.mass_matrix(DISTORTED)
    np.testing.assert_allclose(m - np.diag(np.diag(m)), np.zeros((12, 12)), atol=1e-18)
    np.testing.assert_allclose(np.diag(m), 0.25 * element.total_mass(DISTORTED), rtol=1e-13)


def test_lumped_mass_is_the_row_sum_of_the_consistent_mass():
    element = bound_tet(DISTORTED, lumped_mass=True)
    consistent = element.consistent_mass_matrix(DISTORTED)
    np.testing.assert_allclose(np.diag(element.mass_matrix(DISTORTED)), consistent.sum(axis=1))


def test_a_massless_material_gives_a_zero_mass_matrix():
    model = Model(dofs=SOLID_DOFS)
    for index, point in enumerate(REFERENCE):
        model.add_node(index, point)
    element = model.add_element(
        Tet4Element(range(4), Material(E=1.0e9, density=0.0, nu=0.3))
    )
    np.testing.assert_array_equal(element.mass_matrix(REFERENCE), np.zeros((12, 12)))
    assert element.total_mass(REFERENCE) == 0.0


# ------------------------------------------------------------------ mesh & model


def test_tet_block_mesh_builds_the_expected_grid():
    model = tet_block_mesh(0.3, 0.2, 0.1, 3, 2, 2, STEEL, support="free")
    assert model.num_nodes == 4 * 3 * 3
    assert model.num_elements == 6 * 3 * 2 * 2
    assert model.dofs == SOLID_DOFS
    assert model.constrained_dofs.size == 0
    corner = model.node(model.num_nodes - 1)
    assert (corner.x, corner.y, corner.z) == pytest.approx((0.3, 0.2, 0.1))


def test_tet_block_mesh_fills_the_box_with_positive_volumes():
    model = tet_block_mesh(0.3, 0.2, 0.1, 3, 2, 2, STEEL, support="free")
    volumes = [element.volume(model.node_coords(element.node_ids)) for element in model.elements]
    assert min(volumes) > 0.0
    assert sum(volumes) == pytest.approx(0.3 * 0.2 * 0.1, rel=1e-12)


def test_the_kuhn_subdivision_is_conforming():
    """Every interior triangle is shared by exactly two tetrahedra."""
    num_x, num_y, num_z = 2, 2, 3
    model = tet_block_mesh(0.3, 0.2, 0.1, num_x, num_y, num_z, STEEL, support="free")
    faces: dict[frozenset, int] = {}
    for element in model.elements:
        nodes = element.node_ids
        for skipped in range(4):
            face = frozenset(nodes[:skipped] + nodes[skipped + 1 :])
            faces[face] = faces.get(face, 0) + 1
    assert set(faces.values()) == {1, 2}
    boundary = sum(1 for count in faces.values() if count == 1)
    expected = 4 * (num_x * num_y + num_y * num_z + num_z * num_x)
    assert boundary == expected


def test_tet_block_mesh_clamps_the_cantilever_root():
    model = tet_block_mesh(1.0, 0.1, 0.1, 4, 2, 2, STEEL, support="cantilever")
    root = [node.id for node in model.nodes if np.isclose(node.x, 0.0)]
    assert len(root) == 3 * 3
    assert model.constrained_dofs.size == 3 * len(root)
    for node_id in root:
        for dof in SOLID_DOFS:
            assert model.is_constrained(node_id, dof)


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
def test_tet_block_mesh_validates_its_arguments(kwargs, match):
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
        tet_block_mesh(**arguments)


def test_the_assembled_block_reproduces_the_analytic_mass():
    length, width, height = 0.4, 0.25, 0.06
    model = tet_block_mesh(length, width, height, 3, 2, 2, STEEL, support="free")
    system = assemble_system(model)
    assert system.total_mass == pytest.approx(STEEL.density * length * width * height, rel=1e-12)


def test_the_assembled_block_matrices_are_symmetric():
    model = tet_block_mesh(0.4, 0.25, 0.06, 3, 2, 2, STEEL, support="free")
    system = assemble_system(model)
    for matrix in (system.K, system.M):
        assert abs(matrix - matrix.T).max() <= 1e-6 * abs(matrix).max()


def test_the_mesh_builder_can_add_a_tetrahedron():
    from openfemlab.mesh.simple import MeshBuilder

    mesh = MeshBuilder(dofs=SOLID_DOFS, name="one tet")
    for index, point in enumerate(REFERENCE):
        mesh.add_node(index, *point)
    element = mesh.add_tet4(range(4), STEEL)
    assert isinstance(element, Tet4Element)
    assert element.volume(REFERENCE) == pytest.approx(1.0 / 6.0)


# ---------------------------------------------------------------------- modal


def test_a_free_block_has_six_rigid_body_modes():
    model = tet_block_mesh(0.3, 0.2, 0.1, 3, 2, 2, STEEL, support="free")
    result = ModalSolver(model).solve(num_modes=8)
    assert int(np.sum(result.rigid_body_modes)) == 6
    np.testing.assert_allclose(result.frequencies[:6], np.zeros(6), atol=1e-2)
    assert result.frequencies[6] > 1.0e3


def test_block_modes_are_mass_orthonormal():
    model = tet_block_mesh(0.4, 0.15, 0.1, 4, 2, 2, STEEL, support="cantilever")
    result = ModalSolver(model).solve(num_modes=6)
    assert result.orthogonality_error() < 1e-9


def test_axial_modes_converge_quadratically_to_the_continuum_bar():
    """With lateral motion suppressed and ``nu = 0`` the block is a 1D bar."""
    material = Material(E=2.1e11, density=7850.0, nu=0.0)
    length = 1.0
    exact = np.sqrt(material.E / material.density) / (4.0 * length)

    errors = []
    for num_x in (4, 8, 16):
        model = tet_block_mesh(length, 0.1, 0.1, num_x, 1, 1, material, support="cantilever")
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
        tet_block_mesh(0.4, 0.15, 0.1, 4, 2, 2, STEEL, **arguments)
    ).solve(num_modes=4)
    lumped = ModalSolver(
        tet_block_mesh(0.4, 0.15, 0.1, 4, 2, 2, STEEL, lumped_mass=True, **arguments)
    ).solve(num_modes=4)
    assert np.all(lumped.frequencies <= consistent.frequencies * (1.0 + 1e-12))
    np.testing.assert_allclose(lumped.frequencies, consistent.frequencies, rtol=0.2)


def test_bending_locks_and_only_slowly_relaxes_towards_euler_bernoulli():
    """The headline TET4 limitation, pinned so it cannot be forgotten."""
    length, width, height = 1.0, 0.05, 0.05
    inertia = width * height**3 / 12.0
    reference = (1.875104**2 / (2 * np.pi)) * np.sqrt(
        STEEL.E * inertia / (STEEL.density * width * height * length**4)
    )

    errors = []
    for cells in [(8, 1, 1), (16, 2, 2), (32, 4, 4)]:
        model = tet_block_mesh(length, width, height, *cells, STEEL, support="cantilever")
        errors.append(ModalSolver(model).solve(num_modes=1).frequencies[0] / reference - 1.0)

    assert all(error > 0.0 for error in errors)
    assert errors[0] > errors[1] > errors[2]
    # Refinement helps, but a constant-strain tetrahedron is still 25 % stiff at
    # 2475 DOF, where QUAD4 is inside 2 % with a fraction of the equations.
    assert errors[0] > 1.0
    assert 0.1 < errors[-1] < 0.3
