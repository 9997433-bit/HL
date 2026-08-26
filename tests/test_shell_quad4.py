"""Flat shell QUAD4 facet: facet frame, MITC4 plate, patch tests and modal checks.

The element is verified in the same three layers as the other continuum slices:

* kernel level -- facet frame, projected coordinates, curvature and assumed
  shear operators, and the reuse of the plane-stress QUAD4 membrane;
* element/patch level -- rigid-body invariance, the exact zero-energy mode
  count, and exact reproduction of both a constant membrane strain and a
  constant curvature on a distorted quadrilateral;
* model level -- assembly, mass bookkeeping, and modal accuracy against the
  Navier plate spectrum, the Euler-Bernoulli cantilever strip and a folded
  two-facet shell.

Moment and stress resultants are reported in each element's own facet frame,
which is *not* the global frame for a distorted element, so the resultant
checks compare the frame-independent tensor invariants.
"""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.core.assembly import assemble_stiffness, assemble_system
from openfemlab.core.elements import Quad4Element, ShellQuad4Element
from openfemlab.core.model import DOF, Material, Model
from openfemlab.exceptions import ElementError, ModelError
from openfemlab.mesh.simple import MeshBuilder, quad_plate_mesh, shell_plate_mesh
from openfemlab.solver.modal import ModalSolver

STEEL = Material(E=2.1e11, density=7850.0, nu=0.3)
PATCH_MATERIAL = Material(E=1.0e6, density=1.0, nu=0.25)

SHELL_DOFS = (DOF.UX, DOF.UY, DOF.UZ, DOF.RX, DOF.RY, DOF.RZ)

UNIT_SQUARE = np.array(
    [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]], dtype=float
)

#: A symmetric trapezoid: distorted, yet its averaged ``xi`` direction is global
#: X, so the facet frame coincides with the global one and resultants can be
#: compared component by component.
TRAPEZOID = np.array(
    [[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [1.6, 1.1, 0.0], [0.4, 1.1, 0.0]], dtype=float
)

#: A deliberately non-rectangular, non-parallelogram element.
DISTORTED = np.array(
    [[0.0, 0.0, 0.0], [2.0, -0.3, 0.0], [2.4, 1.6, 0.0], [0.5, 1.1, 0.0]], dtype=float
)


def rotation_matrix(axis, angle: float) -> np.ndarray:
    """Rodrigues rotation about ``axis`` by ``angle``."""
    unit = np.asarray(axis, dtype=float) / np.linalg.norm(axis)
    cross = np.array(
        [[0.0, -unit[2], unit[1]], [unit[2], 0.0, -unit[0]], [-unit[1], unit[0], 0.0]]
    )
    return np.eye(3) + np.sin(angle) * cross + (1.0 - np.cos(angle)) * (cross @ cross)


ROTATION = rotation_matrix([0.3, -0.7, 0.5], 0.9)
TILTED = DISTORTED @ ROTATION.T + np.array([1.5, -0.4, 2.0])


def bound_shell(coords: np.ndarray = DISTORTED, **kwargs) -> ShellQuad4Element:
    """A shell facet bound to a six-DOF model holding ``coords``."""
    options = {"thickness": 0.01, **kwargs}
    model = Model(dofs=SHELL_DOFS, name="single facet")
    for index, point in enumerate(np.asarray(coords, dtype=float)):
        model.add_node(index, point)
    return model.add_element(ShellQuad4Element(range(4), STEEL, **options))


def shoelace_area(coords: np.ndarray) -> float:
    xy = np.asarray(coords, dtype=float)[:, :2]
    rolled = np.roll(xy, -1, axis=0)
    return 0.5 * float(np.sum(xy[:, 0] * rolled[:, 1] - rolled[:, 0] * xy[:, 1]))


def membrane_field(coords: np.ndarray, strain: np.ndarray) -> np.ndarray:
    """Nodal DOFs of a constant in-plane strain state, in node-major shell order."""
    xy = np.asarray(coords, dtype=float)[:, :2]
    exx, eyy, gxy = strain
    values = np.zeros(6 * xy.shape[0], dtype=float)
    values[0::6] = exx * xy[:, 0] + 0.5 * gxy * xy[:, 1]
    values[1::6] = eyy * xy[:, 1] + 0.5 * gxy * xy[:, 0]
    return values


def bending_field(coords: np.ndarray, curvature: np.ndarray) -> np.ndarray:
    """Nodal DOFs of the constant-curvature state ``w = -(kxx x^2 + kyy y^2 + kxy x y) / 2``.

    Zero transverse shear ties the rotations to the slope,
    ``theta_x = dw/dy`` and ``theta_y = -dw/dx``.
    """
    xy = np.asarray(coords, dtype=float)[:, :2]
    x, y = xy[:, 0], xy[:, 1]
    kxx, kyy, kxy = curvature
    values = np.zeros(6 * xy.shape[0], dtype=float)
    values[2::6] = -0.5 * (kxx * x**2 + kyy * y**2 + kxy * x * y)
    values[3::6] = -(kyy * y + 0.5 * kxy * x)
    values[4::6] = kxx * x + 0.5 * kxy * y
    return values


def tensor_invariants(voigt: np.ndarray) -> tuple[float, float]:
    """Trace and determinant of a symmetric 2D tensor given as ``[xx, yy, xy]``."""
    xx, yy, xy = voigt
    return float(xx + yy), float(xx * yy - xy**2)


# ------------------------------------------------------------------ facet frame


def test_facet_frame_of_an_axis_aligned_element_is_the_global_frame():
    _, rotation = bound_shell(TRAPEZOID).local_frame(TRAPEZOID)
    np.testing.assert_allclose(rotation, np.eye(3), atol=1e-15)


def test_facet_frame_is_orthonormal_and_right_handed():
    origin, rotation = bound_shell(TILTED).local_frame(TILTED)
    np.testing.assert_allclose(rotation @ rotation.T, np.eye(3), atol=1e-14)
    assert float(np.linalg.det(rotation)) == pytest.approx(1.0, abs=1e-14)
    np.testing.assert_allclose(origin, TILTED.mean(axis=0), atol=1e-14)


def test_facet_normal_follows_the_counter_clockwise_node_order():
    normal = bound_shell(UNIT_SQUARE).local_frame(UNIT_SQUARE)[1][2]
    np.testing.assert_allclose(normal, [0.0, 0.0, 1.0], atol=1e-15)
    flipped = bound_shell(UNIT_SQUARE[::-1]).local_frame(UNIT_SQUARE[::-1])[1][2]
    np.testing.assert_allclose(flipped, [0.0, 0.0, -1.0], atol=1e-15)


def test_local_coords_are_the_rigidly_moved_in_plane_coordinates():
    """A tilted facet projects onto the same in-plane shape as its flat twin."""
    flat = bound_shell(DISTORTED).local_coords(DISTORTED)
    tilted = bound_shell(TILTED).local_coords(TILTED)
    np.testing.assert_allclose(tilted, flat, atol=1e-13)


def test_area_matches_the_shoelace_formula():
    for coords in (UNIT_SQUARE, TRAPEZOID, DISTORTED):
        element = bound_shell(coords)
        assert element.area(coords) == pytest.approx(shoelace_area(coords), rel=1e-13)
    assert bound_shell(TILTED).area(TILTED) == pytest.approx(shoelace_area(DISTORTED), rel=1e-13)


def test_total_mass_is_density_times_thickness_times_area():
    element = bound_shell(DISTORTED, thickness=0.02)
    expected = STEEL.density * 0.02 * shoelace_area(DISTORTED)
    assert element.total_mass(DISTORTED) == pytest.approx(expected, rel=1e-13)


# -------------------------------------------------------------------- validation


def test_a_warped_facet_is_rejected():
    warped = UNIT_SQUARE.copy()
    warped[2, 2] = 0.05
    with pytest.raises(ElementError, match="out of plane"):
        bound_shell(UNIT_SQUARE).stiffness_matrix(warped)


def test_a_facet_flat_to_round_off_is_accepted():
    nearly = UNIT_SQUARE.copy()
    nearly[2, 2] = 1e-12
    element = bound_shell(UNIT_SQUARE)
    reference = element.stiffness_matrix(UNIT_SQUARE)
    np.testing.assert_allclose(
        element.stiffness_matrix(nearly), reference, atol=1e-9 * np.abs(reference).max()
    )


def test_a_re_entrant_facet_is_rejected():
    """The facet frame follows the node order, so a shell has no global
    orientation to violate; what still fails is an inverted mapping."""
    reentrant = np.array([[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [0.4, 0.3, 0.0], [0.0, 2.0, 0.0]])
    with pytest.raises(ElementError, match="non-positive Jacobian"):
        bound_shell(UNIT_SQUARE).stiffness_matrix(reentrant)


def test_a_collapsed_facet_is_rejected():
    collapsed = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0], [3.0, 0.0, 0.0]])
    with pytest.raises(ElementError, match="degenerate"):
        bound_shell(UNIT_SQUARE).stiffness_matrix(collapsed)


def test_wrong_node_count_is_rejected():
    with pytest.raises(ElementError, match="expects 4 nodes"):
        ShellQuad4Element((1, 2, 3), STEEL, thickness=0.01)


def test_non_positive_thickness_is_rejected():
    with pytest.raises(ElementError, match="thickness must be positive"):
        ShellQuad4Element(range(4), STEEL, thickness=0.0)


def test_negative_drilling_factor_is_rejected():
    with pytest.raises(ElementError, match="drilling_factor"):
        ShellQuad4Element(range(4), STEEL, thickness=0.01, drilling_factor=-1.0)


def test_the_element_requires_all_six_nodal_dofs():
    model = Model(dofs=(DOF.UX, DOF.UY, DOF.UZ), name="translations only")
    for index, point in enumerate(UNIT_SQUARE):
        model.add_node(index, point)
    with pytest.raises(ElementError, match="RX"):
        model.add_element(ShellQuad4Element(range(4), STEEL, thickness=0.01))


def test_recovery_rejects_a_wrong_displacement_count():
    element = bound_shell(UNIT_SQUARE)
    with pytest.raises(ElementError, match="expected 24 nodal displacements"):
        element.curvature(UNIT_SQUARE, np.zeros(12))


# --------------------------------------------------------------------- stiffness


def test_stiffness_is_symmetric_and_positive_semidefinite():
    k = bound_shell(TILTED).stiffness_matrix(TILTED)
    assert k.shape == (24, 24)
    np.testing.assert_allclose(k, k.T, rtol=0, atol=1e-9 * np.abs(k).max())
    eigenvalues = np.linalg.eigvalsh(k)
    assert eigenvalues.min() > -1e-8 * eigenvalues.max()


def test_the_facet_leaves_exactly_six_zero_energy_modes():
    eigenvalues = np.linalg.eigvalsh(bound_shell(DISTORTED).stiffness_matrix(DISTORTED))
    zeros = int(np.sum(np.abs(eigenvalues) < 1e-8 * eigenvalues.max()))
    assert zeros == 6


def test_reduced_integration_is_rank_deficient():
    """The assumed shear field fixes locking, not under-integration: sampling the
    curvature at one point alone still empties the element out."""
    element = bound_shell(DISTORTED, integration_order=1)
    eigenvalues = np.linalg.eigvalsh(element.stiffness_matrix(DISTORTED))
    zeros = int(np.sum(np.abs(eigenvalues) < 1e-8 * eigenvalues.max()))
    assert zeros == 12  # six rigid-body modes, two membrane and four plate hourglass modes


def test_without_a_drilling_penalty_the_four_drilling_dofs_are_free():
    element = bound_shell(DISTORTED, drilling_factor=0.0)
    eigenvalues = np.linalg.eigvalsh(element.stiffness_matrix(DISTORTED))
    zeros = int(np.sum(np.abs(eigenvalues) < 1e-8 * eigenvalues.max()))
    assert zeros == 10


def test_the_drilling_penalty_scales_with_its_factor():
    plate = bound_shell(DISTORTED).plate_stiffness_matrix(
        bound_shell(DISTORTED).local_coords(DISTORTED)
    )
    weak = bound_shell(DISTORTED, drilling_factor=1e-3).drilling_stiffness(plate)
    strong = bound_shell(DISTORTED, drilling_factor=1e-2).drilling_stiffness(plate)
    assert strong == pytest.approx(10.0 * weak, rel=1e-13)
    assert 0.0 < weak < np.abs(np.diag(plate)).max()


@pytest.mark.parametrize("axis", range(3))
def test_rigid_body_translation_produces_no_nodal_force(axis):
    element = bound_shell(TILTED)
    k = element.stiffness_matrix(TILTED)
    motion = np.zeros(24)
    motion[axis::6] = 1.0
    np.testing.assert_allclose(k @ motion, np.zeros(24), atol=1e-12 * np.abs(k).max())


@pytest.mark.parametrize("axis", range(3))
def test_rigid_body_rotation_produces_no_strain_energy(axis):
    """A rigid rotation of the facet about a global axis, with the nodal
    rotations carried along; the drilling DOFs stay out of it because the
    drilling stiffness is a penalty, not a rotation field."""
    element = bound_shell(TILTED)
    k = element.stiffness_matrix(TILTED)
    _, frame = element.local_frame(TILTED)
    omega = np.eye(3)[axis]
    motion = np.zeros(24)
    for node, point in enumerate(TILTED - TILTED.mean(axis=0)):
        motion[6 * node : 6 * node + 3] = np.cross(omega, point)
        # Only the two bending rotations of the facet frame are physical here.
        motion[6 * node + 3 : 6 * node + 6] = (frame @ omega) * np.array([1.0, 1.0, 0.0]) @ frame
    energy = float(motion @ k @ motion)
    assert energy == pytest.approx(0.0, abs=1e-12 * np.abs(k).max() * (motion @ motion))


def test_the_three_rigidities_scale_with_their_own_power_of_the_thickness():
    """Membrane goes as ``t``, bending as ``t^3`` and transverse shear as ``t``;
    the last two share the rotational DOFs, which is why the plate block itself
    obeys no single power law."""
    thin = bound_shell(DISTORTED, thickness=0.01)
    thick = bound_shell(DISTORTED, thickness=0.03)
    membrane = [6 * n + a for n in range(4) for a in (0, 1)]
    np.testing.assert_allclose(
        thick.local_stiffness_matrix(DISTORTED)[np.ix_(membrane, membrane)],
        3.0 * thin.local_stiffness_matrix(DISTORTED)[np.ix_(membrane, membrane)],
        rtol=1e-13,
    )
    np.testing.assert_allclose(
        thick.bending_constitutive_matrix, 27.0 * thin.bending_constitutive_matrix, rtol=1e-13
    )
    assert thick.shear_rigidity == pytest.approx(3.0 * thin.shear_rigidity, rel=1e-13)


def test_stiffness_rotates_with_the_geometry():
    element = bound_shell(DISTORTED)
    tilted = bound_shell(TILTED)
    transform = np.kron(np.eye(8), ROTATION)
    np.testing.assert_allclose(
        tilted.stiffness_matrix(TILTED),
        transform @ element.stiffness_matrix(DISTORTED) @ transform.T,
        rtol=1e-9,
        atol=1e-6,
    )


# ------------------------------------------------------------- membrane reuse


def test_the_membrane_block_is_the_plane_stress_quad4_kernel():
    element = bound_shell(DISTORTED, thickness=0.004)
    quad = Quad4Element(range(4), STEEL, thickness=0.004, plane="stress")
    membrane = [6 * n + a for n in range(4) for a in (0, 1)]
    k = element.stiffness_matrix(DISTORTED)[np.ix_(membrane, membrane)]
    reference = quad.stiffness_matrix(DISTORTED)
    np.testing.assert_allclose(k, reference, atol=1e-9 * np.abs(reference).max())


def test_the_in_plane_spectrum_reproduces_the_membrane_only_plate():
    """With the shell's out-of-plane DOFs suppressed the model *is* the QUAD4 plate."""
    arguments = {"thickness": 0.006, "support": "cantilever"}
    shell = shell_plate_mesh(0.4, 0.25, 5, 4, STEEL, **arguments)
    shell.fix_dof_globally((DOF.UZ, DOF.RX, DOF.RY, DOF.RZ))
    membrane = quad_plate_mesh(0.4, 0.25, 5, 4, STEEL, **arguments)
    np.testing.assert_allclose(
        ModalSolver(shell).solve(num_modes=4).frequencies,
        ModalSolver(membrane).solve(num_modes=4).frequencies,
        rtol=1e-10,
    )


# ------------------------------------------------------------ MITC4 kinematics


def test_the_curvature_operator_matches_finite_differences_of_the_rotations():
    element = bound_shell(TRAPEZOID)
    local_xy = element.local_coords(TRAPEZOID)
    b_k, _ = element.curvature_matrix(local_xy, 0.2, -0.35)
    gradient, _ = element.membrane.jacobian(local_xy, 0.2, -0.35)
    # kxx reads d(theta_y)/dx, kyy reads -d(theta_x)/dy.
    np.testing.assert_allclose(b_k[0, 2::3], gradient[0], atol=1e-15)
    np.testing.assert_allclose(b_k[1, 1::3], -gradient[1], atol=1e-15)
    np.testing.assert_allclose(b_k[0, 0::3], np.zeros(4), atol=1e-15)


def test_the_assumed_shear_is_exact_at_its_own_tying_points():
    element = bound_shell(DISTORTED)
    local_xy = element.local_coords(DISTORTED)
    rows = element.tying_rows(local_xy)
    for index, (point, direction) in enumerate(
        (((0.0, -1.0), 0), ((0.0, 1.0), 0), ((1.0, 0.0), 1), ((-1.0, 0.0), 1))
    ):
        b_s, _ = element.shear_strain_matrix(local_xy, *point)
        jac = Quad4Element.shape_function_derivatives(*point) @ local_xy
        np.testing.assert_allclose(jac[direction] @ b_s, rows[index], atol=1e-12)


def test_a_pure_bending_state_carries_no_transverse_shear():
    element = bound_shell(DISTORTED)
    field = bending_field(DISTORTED, np.array([3e-3, -1.5e-3, 8e-4]))
    for xi, eta in [(0.0, 0.0), (-0.9, 0.3), (0.8, -0.6), (1.0, 1.0)]:
        np.testing.assert_allclose(
            element.transverse_shear(DISTORTED, field, xi, eta), np.zeros(2), atol=1e-15
        )


def test_a_transverse_shear_state_is_resisted():
    """Sliding the plate through the thickness -- ``w`` linear, rotations zero --
    is pure shear and must cost energy, which is what tells shear locking from
    a genuinely soft element."""
    element = bound_shell(UNIT_SQUARE, thickness=0.01)
    field = np.zeros(24)
    field[2::6] = UNIT_SQUARE[:, 0]
    k = element.stiffness_matrix(UNIT_SQUARE)
    expected = element.shear_rigidity * element.area(UNIT_SQUARE)
    assert float(field @ k @ field) == pytest.approx(expected, rel=1e-12)


# -------------------------------------------------------------------- patch tests


@pytest.mark.parametrize(
    "strain", [np.array([1e-3, 0.0, 0.0]), np.array([4e-4, -2e-4, 7e-4])]
)
def test_one_facet_reproduces_a_constant_membrane_strain_exactly(strain):
    element = bound_shell(TRAPEZOID)
    field = membrane_field(TRAPEZOID, strain)
    expected = element.membrane.constitutive_matrix @ strain
    for xi, eta in [(0.0, 0.0), (-0.9, 0.3), (0.8, -0.6), (1.0, 1.0)]:
        np.testing.assert_allclose(
            element.membrane_stress(TRAPEZOID, field, xi, eta),
            expected,
            rtol=1e-12,
            atol=1e-12 * np.abs(expected).max(),
        )


@pytest.mark.parametrize(
    "curvature", [np.array([1e-2, 0.0, 0.0]), np.array([3e-3, -1.5e-3, 8e-4])]
)
def test_one_facet_reproduces_a_constant_curvature_exactly(curvature):
    element = bound_shell(TRAPEZOID, thickness=0.05)
    field = bending_field(TRAPEZOID, curvature)
    expected = element.bending_constitutive_matrix @ curvature
    for xi, eta in [(0.0, 0.0), (-0.9, 0.3), (0.8, -0.6), (1.0, 1.0)]:
        np.testing.assert_allclose(
            element.curvature(TRAPEZOID, field, xi, eta), curvature, rtol=1e-12, atol=1e-16
        )
        np.testing.assert_allclose(
            element.bending_moment(TRAPEZOID, field, xi, eta),
            expected,
            rtol=1e-12,
            atol=1e-12 * np.abs(expected).max(),
        )


def test_a_constant_curvature_state_stores_exactly_its_analytic_energy():
    element = bound_shell(TRAPEZOID, thickness=0.05)
    curvature = np.array([3e-3, -1.5e-3, 8e-4])
    field = bending_field(TRAPEZOID, curvature)
    expected = (
        curvature @ element.bending_constitutive_matrix @ curvature * element.area(TRAPEZOID)
    )
    assert float(field @ element.stiffness_matrix(TRAPEZOID) @ field) == pytest.approx(
        expected, rel=1e-10
    )


#: The MacNeal-Harder distorted patch, reused for the shell so the membrane
#: evidence is directly comparable with ``tests/test_quad4.py``.
PATCH_COORDS = {
    1: (0.00, 0.00),
    2: (0.24, 0.00),
    3: (0.24, 0.12),
    4: (0.00, 0.12),
    5: (0.04, 0.02),
    6: (0.18, 0.03),
    7: (0.16, 0.08),
    8: (0.08, 0.08),
}
PATCH_CONNECTIVITY = [(1, 2, 6, 5), (2, 3, 7, 6), (3, 4, 8, 7), (4, 1, 5, 8), (5, 6, 7, 8)]


def shell_patch():
    model = Model(dofs=SHELL_DOFS, name="shell patch")
    for node_id, (x, y) in PATCH_COORDS.items():
        model.add_node(node_id, x, y, 0.0)
    elements = [
        model.add_element(ShellQuad4Element(nodes, PATCH_MATERIAL, thickness=0.001))
        for nodes in PATCH_CONNECTIVITY
    ]
    return model, elements


def solve_patch(model, exact: np.ndarray):
    """Prescribe every DOF of the outer nodes and solve for the interior ones."""
    K = assemble_stiffness(model).toarray()
    prescribed = np.array(
        [model.dof_index(n, d) for n in (1, 2, 3, 4) for d in SHELL_DOFS], dtype=int
    )
    interior = np.setdiff1d(np.arange(model.num_dofs), prescribed)
    solution = np.linalg.solve(
        K[np.ix_(interior, interior)], -K[np.ix_(interior, prescribed)] @ exact[prescribed]
    )
    computed = exact.copy()
    computed[interior] = solution
    return computed, interior


def patch_field(model, builder, state: np.ndarray) -> np.ndarray:
    exact = np.zeros(model.num_dofs, dtype=float)
    for node_id, (x, y) in PATCH_COORDS.items():
        nodal = builder(np.array([[x, y, 0.0]]), state)
        for offset, dof in enumerate(SHELL_DOFS):
            exact[model.dof_index(node_id, dof)] = nodal[offset]
    return exact


def test_the_membrane_patch_recovers_the_interior_displacements():
    model, _ = shell_patch()
    exact = patch_field(model, membrane_field, np.array([1e-3, 5e-4, 1e-3]))
    computed, interior = solve_patch(model, exact)
    assert np.abs(computed[interior] - exact[interior]).max() < 1e-12 * np.abs(exact).max()


def test_the_membrane_patch_yields_the_exact_constant_stress():
    model, elements = shell_patch()
    strain = np.array([1e-3, 5e-4, 1e-3])
    exact = patch_field(model, membrane_field, strain)
    computed, _ = solve_patch(model, exact)
    reference = tensor_invariants(elements[0].membrane.constitutive_matrix @ strain)
    for element in elements:
        coords = model.node_coords(element.node_ids)
        displacements = computed[element.global_dofs(model)]
        for xi, eta in [(-0.7, 0.2), (0.0, 0.0), (0.5, -0.9)]:
            stress = element.membrane_stress(coords, displacements, xi, eta)
            np.testing.assert_allclose(tensor_invariants(stress), reference, rtol=1e-9)


def test_the_bending_patch_recovers_the_interior_displacements():
    model, _ = shell_patch()
    exact = patch_field(model, bending_field, np.array([2e-2, -1e-2, 6e-3]))
    computed, interior = solve_patch(model, exact)
    error = np.abs(computed[interior] - exact[interior]).max()
    assert error < 1e-9 * np.abs(exact[interior]).max()


def test_the_bending_patch_yields_the_exact_constant_moment():
    model, elements = shell_patch()
    curvature = np.array([2e-2, -1e-2, 6e-3])
    exact = patch_field(model, bending_field, curvature)
    computed, _ = solve_patch(model, exact)
    reference = tensor_invariants(elements[0].bending_constitutive_matrix @ curvature)
    for element in elements:
        coords = model.node_coords(element.node_ids)
        displacements = computed[element.global_dofs(model)]
        for xi, eta in [(-0.7, 0.2), (0.0, 0.0), (0.5, -0.9)]:
            moment = element.bending_moment(coords, displacements, xi, eta)
            np.testing.assert_allclose(tensor_invariants(moment), reference, rtol=1e-6)
            np.testing.assert_allclose(
                element.transverse_shear(coords, displacements, xi, eta),
                np.zeros(2),
                atol=1e-12,
            )


def test_the_coplanar_patch_leaves_the_drilling_dofs_at_rest():
    model, _ = shell_patch()
    exact = patch_field(model, bending_field, np.array([2e-2, -1e-2, 6e-3]))
    computed, _ = solve_patch(model, exact)
    drilling = [model.dof_index(n, DOF.RZ) for n in PATCH_COORDS]
    np.testing.assert_allclose(computed[drilling], np.zeros(len(drilling)), atol=1e-18)


# --------------------------------------------------------------------------- mass


def test_the_consistent_mass_carries_the_total_mass_in_each_direction():
    element = bound_shell(DISTORTED, thickness=0.02)
    m = element.mass_matrix(DISTORTED)
    total = element.total_mass(DISTORTED)
    for axis in range(3):
        velocity = np.zeros(24)
        velocity[axis::6] = 1.0
        assert float(velocity @ m @ velocity) == pytest.approx(total, rel=1e-12)


def test_the_bending_rotations_are_massless_by_default():
    m = bound_shell(DISTORTED, thickness=0.02).mass_matrix(DISTORTED)
    rotations = [6 * node + axis for node in range(4) for axis in (3, 4, 5)]
    np.testing.assert_allclose(m[rotations], np.zeros((12, 24)), atol=1e-18)


def test_rotary_inertia_adds_the_thickness_squared_over_twelve_term():
    plain = bound_shell(TRAPEZOID, thickness=0.02)
    heavy = bound_shell(TRAPEZOID, thickness=0.02, rotary_inertia=True)
    translation = [6 * node + 2 for node in range(4)]
    rotation = [6 * node + 3 for node in range(4)]
    m_plain = plain.mass_matrix(TRAPEZOID)
    m_heavy = heavy.mass_matrix(TRAPEZOID)
    np.testing.assert_allclose(
        m_heavy[np.ix_(translation, translation)], m_plain[np.ix_(translation, translation)]
    )
    np.testing.assert_allclose(
        m_heavy[np.ix_(rotation, rotation)],
        m_plain[np.ix_(translation, translation)] * (0.02**2 / 12.0),
        rtol=1e-13,
    )


def test_the_drilling_dofs_are_massless_even_with_rotary_inertia():
    m = bound_shell(DISTORTED, thickness=0.02, rotary_inertia=True).mass_matrix(DISTORTED)
    drilling = [6 * node + 5 for node in range(4)]
    np.testing.assert_allclose(m[drilling], np.zeros((4, 24)), atol=1e-18)


def test_lumped_mass_is_diagonal_and_preserves_the_total_mass():
    element = bound_shell(UNIT_SQUARE, thickness=0.02, lumped_mass=True, rotary_inertia=True)
    m = element.mass_matrix(UNIT_SQUARE)
    np.testing.assert_allclose(m - np.diag(np.diag(m)), np.zeros((24, 24)), atol=1e-18)
    assert np.diag(m)[0::6].sum() == pytest.approx(element.total_mass(UNIT_SQUARE), rel=1e-13)


def test_a_massless_material_gives_a_zero_mass_matrix():
    model = Model(dofs=SHELL_DOFS)
    for index, point in enumerate(UNIT_SQUARE):
        model.add_node(index, point)
    element = model.add_element(
        ShellQuad4Element(range(4), Material(E=1.0e9, density=0.0, nu=0.3), thickness=0.01)
    )
    np.testing.assert_array_equal(element.mass_matrix(UNIT_SQUARE), np.zeros((24, 24)))
    assert element.total_mass(UNIT_SQUARE) == 0.0


def test_mass_rotates_with_the_geometry():
    flat = bound_shell(DISTORTED, thickness=0.02, rotary_inertia=True)
    tilted = bound_shell(TILTED, thickness=0.02, rotary_inertia=True)
    transform = np.kron(np.eye(8), ROTATION)
    reference = transform @ flat.mass_matrix(DISTORTED) @ transform.T
    np.testing.assert_allclose(
        tilted.mass_matrix(TILTED), reference, atol=1e-12 * np.abs(reference).max()
    )


# ----------------------------------------------------------------- mesh & model


def test_the_mesh_builder_exposes_the_shell_seam():
    mesh = MeshBuilder(dofs=SHELL_DOFS)
    for point in UNIT_SQUARE:
        mesh.add_node(None, point)
    element = mesh.add_shell_quad4(range(4), STEEL, thickness=0.01)
    assert isinstance(element, ShellQuad4Element)
    assert element.dofs == SHELL_DOFS


def test_shell_plate_mesh_builds_the_expected_grid():
    model = shell_plate_mesh(0.3, 0.2, 3, 2, STEEL, thickness=0.01, support="free")
    assert model.num_nodes == 4 * 3
    assert model.num_elements == 6
    assert model.dofs == SHELL_DOFS
    assert model.constrained_dofs.size == 0
    corner = model.node(model.num_nodes - 1)
    assert (corner.x, corner.y) == pytest.approx((0.3, 0.2))


def test_shell_plate_mesh_shares_the_quad_plate_node_numbering():
    arguments = {"length": 0.3, "width": 0.2, "num_x": 3, "num_y": 2, "material": STEEL}
    shell = shell_plate_mesh(**arguments, thickness=0.01, support="free")
    membrane = quad_plate_mesh(
        arguments["length"],
        arguments["width"],
        arguments["num_x"],
        arguments["num_y"],
        STEEL,
        thickness=0.01,
        support="free",
    )
    for node_id in range(shell.num_nodes):
        np.testing.assert_allclose(shell.node(node_id).coords, membrane.node(node_id).coords)


def test_shell_plate_mesh_clamps_the_cantilever_root():
    model = shell_plate_mesh(1.0, 0.1, 4, 2, STEEL, thickness=0.01, support="cantilever")
    root = [0, 5, 10]
    assert model.constrained_dofs.size == 6 * len(root)
    for node_id in root:
        assert all(model.is_constrained(node_id, dof) for dof in SHELL_DOFS)


def test_shell_plate_mesh_applies_a_hard_simple_support():
    model = shell_plate_mesh(1.0, 1.0, 2, 2, STEEL, thickness=0.01, support="simply-supported")
    assert model.is_constrained(1, DOF.UZ) and model.is_constrained(1, DOF.RY)
    assert not model.is_constrained(1, DOF.RX)
    assert model.is_constrained(3, DOF.UZ) and model.is_constrained(3, DOF.RX)
    assert not model.is_constrained(3, DOF.RY)
    assert not any(model.is_constrained(4, dof) for dof in SHELL_DOFS)


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"support": "clamped"}, "unknown support"),
        ({"num_y": 0}, "must be >= 1"),
        ({"width": -1.0}, "must be positive"),
    ],
)
def test_shell_plate_mesh_validates_its_arguments(kwargs, match):
    arguments = {
        "length": 1.0,
        "width": 0.1,
        "num_x": 4,
        "num_y": 2,
        "material": STEEL,
        "thickness": 0.01,
    }
    arguments.update(kwargs)
    with pytest.raises(ModelError, match=match):
        shell_plate_mesh(**arguments)


def test_the_assembled_plate_reproduces_the_analytic_slab_mass():
    length, width, thickness = 0.4, 0.25, 0.006
    model = shell_plate_mesh(length, width, 5, 4, STEEL, thickness=thickness, support="free")
    system = assemble_system(model)
    assert system.total_mass == pytest.approx(
        STEEL.density * thickness * length * width, rel=1e-12
    )


def test_the_assembled_plate_matrices_are_symmetric():
    model = shell_plate_mesh(0.4, 0.25, 4, 3, STEEL, thickness=0.006, support="free")
    system = assemble_system(model)
    for matrix in (system.K, system.M):
        assert abs(matrix - matrix.T).max() <= 1e-6 * abs(matrix).max()


# ------------------------------------------------------------------------ modal


def navier_frequency(m: int, n: int, side: float, thickness: float) -> float:
    """Kirchhoff simply-supported square plate, ``f_mn`` in Hz."""
    rigidity = STEEL.E * thickness**3 / (12.0 * (1.0 - STEEL.nu**2))
    return (
        0.5 * np.pi * (m**2 + n**2) / side**2 * np.sqrt(rigidity / (STEEL.density * thickness))
    )


def test_the_simply_supported_plate_converges_to_the_navier_spectrum():
    side, thickness = 1.0, 0.005
    reference = navier_frequency(1, 1, side, thickness)
    errors = []
    for num in (4, 8, 12):
        model = shell_plate_mesh(
            side, side, num, num, STEEL, thickness=thickness, support="simply-supported"
        )
        first = ModalSolver(model).solve(num_modes=1).frequencies[0]
        errors.append(first / reference - 1.0)

    # Displacement-based bending converges from above, quadratically in h.
    assert all(error > 0.0 for error in errors)
    assert errors[0] > errors[1] > errors[2]
    assert errors[-1] < 0.01
    assert errors[0] / errors[1] > 3.0


def test_the_simply_supported_plate_reproduces_the_higher_navier_modes():
    side, thickness = 1.0, 0.005
    model = shell_plate_mesh(
        side, side, 12, 12, STEEL, thickness=thickness, support="simply-supported"
    )
    frequencies = ModalSolver(model).solve(num_modes=4).frequencies
    modes = ((1, 1), (1, 2), (2, 1), (2, 2))
    expected = [navier_frequency(m, n, side, thickness) for m, n in modes]
    np.testing.assert_allclose(frequencies, expected, rtol=0.04)
    # The two half-wave modes of a square plate are a degenerate pair.
    assert frequencies[1] == pytest.approx(frequencies[2], rel=1e-6)


def test_the_free_plate_has_exactly_six_rigid_body_modes():
    model = shell_plate_mesh(0.4, 0.3, 5, 4, STEEL, thickness=0.004, support="free")
    result = ModalSolver(model).solve(num_modes=9)
    assert int(np.sum(result.rigid_body_modes)) == 6
    np.testing.assert_allclose(result.frequencies[:6], np.zeros(6), atol=1e-2)
    assert result.frequencies[6] > 1.0


def test_the_plate_modes_are_mass_orthonormal():
    model = shell_plate_mesh(0.4, 0.25, 5, 4, STEEL, thickness=0.006, support="cantilever")
    assert ModalSolver(model).solve(num_modes=6).orthogonality_error() < 1e-9


def test_the_cantilever_strip_converges_to_the_euler_bernoulli_beam():
    length, width, thickness = 1.0, 0.05, 0.005
    inertia = width * thickness**3 / 12.0
    area = width * thickness
    reference = (1.875104**2 / (2 * np.pi)) * np.sqrt(
        STEEL.E * inertia / (STEEL.density * area * length**4)
    )
    errors = []
    for num_x in (10, 20, 40):
        model = shell_plate_mesh(
            length, width, num_x, 1, STEEL, thickness=thickness, support="cantilever"
        )
        errors.append(ModalSolver(model).solve(num_modes=1).frequencies[0] / reference - 1.0)

    assert all(error > 0.0 for error in errors)
    assert errors[0] > errors[1] > errors[2]
    assert errors[-1] < 5e-3


def test_the_cantilever_strip_matches_the_beam_tip_deflection():
    length, width, thickness = 1.0, 0.05, 0.005
    num_x, num_y = 20, 2
    model = shell_plate_mesh(
        length, width, num_x, num_y, STEEL, thickness=thickness, support="cantilever"
    )
    tip = [num_x + row * (num_x + 1) for row in range(num_y + 1)]
    load = np.zeros(model.num_dofs)
    for node_id in tip:
        load[model.dof_index(node_id, DOF.UZ)] = 1.0 / len(tip)

    free = model.free_dofs
    K = assemble_stiffness(model).toarray()
    displacements = np.zeros(model.num_dofs)
    displacements[free] = np.linalg.solve(K[np.ix_(free, free)], load[free])

    inertia = width * thickness**3 / 12.0
    expected = length**3 / (3.0 * STEEL.E * inertia)
    tip_deflection = displacements[model.dof_index(tip[0], DOF.UZ)]
    # The plate is marginally stiffer than the beam: the clamp holds the
    # anticlastic curvature that a beam is free to develop.
    assert tip_deflection == pytest.approx(expected, rel=0.01)
    assert tip_deflection < expected


def test_a_lumped_mass_plate_is_not_stiffer_than_the_consistent_one():
    arguments = {"thickness": 0.005, "support": "cantilever"}
    consistent = ModalSolver(shell_plate_mesh(0.4, 0.25, 5, 4, STEEL, **arguments)).solve(
        num_modes=4
    )
    lumped = ModalSolver(
        shell_plate_mesh(0.4, 0.25, 5, 4, STEEL, lumped_mass=True, **arguments)
    ).solve(num_modes=4)
    assert np.all(lumped.frequencies <= consistent.frequencies * (1.0 + 1e-12))
    np.testing.assert_allclose(lumped.frequencies, consistent.frequencies, rtol=0.2)


def test_rotary_inertia_lowers_the_plate_spectrum_slightly():
    arguments = {"thickness": 0.005, "support": "simply-supported"}
    plain = ModalSolver(shell_plate_mesh(1.0, 1.0, 8, 8, STEEL, **arguments)).solve(
        num_modes=3, residual_tol=None
    )
    heavy = ModalSolver(
        shell_plate_mesh(1.0, 1.0, 8, 8, STEEL, rotary_inertia=True, **arguments)
    ).solve(num_modes=3, residual_tol=None)
    assert np.all(heavy.frequencies < plain.frequencies)
    np.testing.assert_allclose(heavy.frequencies, plain.frequencies, rtol=1e-3)


def test_a_tilted_plate_has_the_same_spectrum_as_the_flat_one():
    flat = shell_plate_mesh(0.4, 0.3, 4, 3, STEEL, thickness=0.004, support="cantilever")
    tilted = Model(dofs=SHELL_DOFS, name="tilted plate")
    for node_id in range(flat.num_nodes):
        tilted.add_node(node_id, ROTATION @ flat.node(node_id).coords)
    for element in flat.elements:
        tilted.add_element(ShellQuad4Element(element.node_ids, STEEL, thickness=0.004))
    for node_id in range(flat.num_nodes):
        for dof in SHELL_DOFS:
            if flat.is_constrained(node_id, dof):
                tilted.fix(node_id, (dof,))

    np.testing.assert_allclose(
        ModalSolver(tilted).solve(num_modes=5).frequencies,
        ModalSolver(flat).solve(num_modes=5).frequencies,
        rtol=1e-8,
    )


def folded_shell(num: int = 4, thickness: float = 0.004) -> Model:
    """Two square facets meeting at a right angle along ``x = 1``, clamped at ``x = 0``."""
    model = Model(dofs=SHELL_DOFS, name="folded shell")
    step = 1.0 / num
    flange: dict[tuple[int, int], int] = {}
    web: dict[tuple[int, int], int] = {}
    counter = 0
    for j in range(num + 1):
        for i in range(num + 1):
            model.add_node(counter, i * step, j * step, 0.0)
            flange[(i, j)] = counter
            counter += 1
    for j in range(num + 1):
        for i in range(1, num + 1):
            model.add_node(counter, 1.0, j * step, i * step)
            web[(i, j)] = counter
            counter += 1
    web.update({(0, j): flange[(num, j)] for j in range(num + 1)})

    for patch in (flange, web):
        for j in range(num):
            for i in range(num):
                corners = (
                    patch[(i, j)],
                    patch[(i + 1, j)],
                    patch[(i + 1, j + 1)],
                    patch[(i, j + 1)],
                )
                model.add_element(ShellQuad4Element(corners, STEEL, thickness=thickness))
    model.fix_nodes([flange[(0, j)] for j in range(num + 1)])
    return model


def test_the_folded_shell_has_no_mechanism_at_the_crease():
    """The drilling penalty is what keeps the fold from hinging: the rotation
    normal to one facet is a bending rotation of the other."""
    model = folded_shell()
    free = model.free_dofs
    eigenvalues = np.linalg.eigvalsh(assemble_stiffness(model).toarray()[np.ix_(free, free)])
    assert eigenvalues.min() > 1e-9 * eigenvalues.max()


def test_the_folded_shell_solves_and_stays_mass_orthonormal():
    model = folded_shell()
    result = ModalSolver(model).solve(num_modes=4)
    assert np.all(result.frequencies > 0.0)
    assert result.orthogonality_error() < 1e-9
