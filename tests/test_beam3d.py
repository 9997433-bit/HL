"""Spatial Euler-Bernoulli beam (CBAR-like): local frame, matrices and models.

The element is verified in three layers, mirroring ``tests/test_quad4.py`` and
``tests/test_tet4.py``:

* kernel level -- the local frame convention, the local 12x12 matrices and
  their agreement with the planar :class:`BeamElement2D` in the shared plane;
* element level -- rigid-body invariance, zero-energy mode count and the
  invariance of the assembled matrices under a rigid rotation of the model;
* model level -- closed-form cantilever statics (exact for a point load),
  the cantilever bending and torsion spectra, and free-free rigid-body counts.
"""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.core.assembly import assemble_stiffness, assemble_system
from openfemlab.core.elements import BeamElement2D, BeamElement3D
from openfemlab.core.model import DOF, Material, Model, Section
from openfemlab.exceptions import ElementError
from openfemlab.mesh.simple import MeshBuilder, beam_mesh
from openfemlab.solver.modal import ModalSolver

STEEL = Material(E=2.1e11, density=7850.0, nu=0.3)

#: Deliberately unequal principal inertias so the two bending planes never mix up.
SECTION = Section(
    area=6.0e-4,
    inertia_z=2.0e-8,
    inertia_y=4.5e-8,
    torsion_constant=1.0e-8,
    name="rectangle",
)

FRAME_DOFS = (DOF.UX, DOF.UY, DOF.UZ, DOF.RX, DOF.RY, DOF.RZ)

#: A member along global X, the orientation the default reference reproduces.
ALONG_X = np.array([[0.0, 0.0, 0.0], [1.5, 0.0, 0.0]])

#: Cantilever roots for the closed-form spectra.
BEAM_LENGTH = 1.0

#: Euler-Bernoulli cantilever eigenvalues ``beta_i L``.
CANTILEVER_BETA = (1.8751040687, 4.6940911330, 7.8547574382)


def bound_beam(coords: np.ndarray = ALONG_X, **kwargs) -> BeamElement3D:
    """A spatial beam bound to a six-DOF frame model holding ``coords``."""
    model = Model(dofs=FRAME_DOFS, name="single beam")
    for index, point in enumerate(np.asarray(coords, dtype=float)):
        model.add_node(index, point)
    return model.add_element(BeamElement3D((0, 1), STEEL, SECTION, **kwargs))


def cantilever(
    num_elements: int = 1,
    *,
    length: float = BEAM_LENGTH,
    direction: tuple[float, float, float] = (1.0, 0.0, 0.0),
    section: Section = SECTION,
    **kwargs,
) -> tuple[Model, list]:
    """Clamped-free spatial beam of ``num_elements`` members, plus its node ids."""
    mesh = MeshBuilder(dofs=FRAME_DOFS, name="cantilever")
    axis = np.asarray(direction, dtype=float)
    axis = axis / np.linalg.norm(axis)
    nodes = mesh.line_nodes((0.0, 0.0, 0.0), axis * length, num_elements)
    mesh.chain(nodes, lambda a, b: mesh.add_beam3d(a, b, STEEL, section, **kwargs))
    mesh.fix(nodes[0])
    return mesh.build(), nodes


def solve_static(model: Model, loads: dict[int, float]) -> np.ndarray:
    """Displacements under ``{global dof index: force}``, zero on constrained DOFs."""
    system = assemble_system(model)
    free = system.free_dofs
    forces = np.zeros(system.num_dofs, dtype=float)
    for index, value in loads.items():
        forces[index] += value
    stiffness = system.K.toarray()
    displacements = np.zeros(system.num_dofs, dtype=float)
    displacements[free] = np.linalg.solve(
        stiffness[np.ix_(free, free)], forces[free]
    )
    return displacements


def rodrigues(axis: np.ndarray, angle: float) -> np.ndarray:
    """Rotation matrix of ``angle`` radians about ``axis``."""
    unit = np.asarray(axis, dtype=float) / np.linalg.norm(axis)
    cross = np.array(
        [
            [0.0, -unit[2], unit[1]],
            [unit[2], 0.0, -unit[0]],
            [-unit[1], unit[0], 0.0],
        ]
    )
    return np.eye(3) + np.sin(angle) * cross + (1.0 - np.cos(angle)) * (cross @ cross)


def cantilever_frequency(index: int, inertia: float, length: float = BEAM_LENGTH) -> float:
    """Closed-form Euler-Bernoulli cantilever frequency [Hz]."""
    beta = CANTILEVER_BETA[index] / length
    return (
        beta**2
        / (2.0 * np.pi)
        * np.sqrt(STEEL.E * inertia / (STEEL.density * SECTION.area))
    )


def torsion_frequency(length: float = BEAM_LENGTH) -> float:
    """First fixed-free torsional frequency ``c / (4 L)`` [Hz]."""
    polar = SECTION.inertia_y + SECTION.inertia_z
    speed = np.sqrt(STEEL.shear_modulus * SECTION.torsion_constant / (STEEL.density * polar))
    return speed / (4.0 * length)


# ------------------------------------------------------------------ local frame


def test_the_default_frame_of_a_member_along_x_is_the_global_frame():
    np.testing.assert_allclose(bound_beam().local_axes(ALONG_X), np.eye(3), atol=1e-15)


def test_the_default_reference_avoids_a_member_parallel_to_it():
    """A member along global Y cannot use global Y as its reference vector."""
    coords = np.array([[0.0, 0.0, 0.0], [0.0, 2.0, 0.0]])
    axes = bound_beam(coords).local_axes(coords)
    np.testing.assert_allclose(axes[0], [0.0, 1.0, 0.0], atol=1e-15)
    np.testing.assert_allclose(axes[1], [0.0, 0.0, 1.0], atol=1e-15)


@pytest.mark.parametrize(
    "coords",
    [
        ALONG_X,
        np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 3.0]]),
        np.array([[0.2, -0.4, 0.1], [1.1, 0.9, -0.6]]),
    ],
)
def test_the_local_frame_is_orthonormal_and_right_handed(coords):
    axes = bound_beam(coords).local_axes(coords)
    np.testing.assert_allclose(axes @ axes.T, np.eye(3), atol=1e-14)
    assert np.linalg.det(axes) == pytest.approx(1.0, abs=1e-14)


def test_the_orientation_vector_places_the_local_y_axis():
    coords = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    axes = bound_beam(coords, orientation=(0.0, 1.0, 1.0)).local_axes(coords)
    np.testing.assert_allclose(axes[1], [0.0, 2.0**-0.5, 2.0**-0.5], atol=1e-14)
    np.testing.assert_allclose(axes[2], [0.0, -(2.0**-0.5), 2.0**-0.5], atol=1e-14)


def test_the_orientation_vector_is_normalized_on_input():
    element = bound_beam(orientation=(0.0, 0.0, 7.0))
    np.testing.assert_allclose(element.orientation, [0.0, 0.0, 1.0], atol=1e-15)


def test_an_orientation_parallel_to_the_member_is_rejected():
    with pytest.raises(ElementError, match="parallel to the member axis"):
        bound_beam(orientation=(1.0, 0.0, 0.0)).local_axes(ALONG_X)


@pytest.mark.parametrize(
    ("orientation", "match"),
    [
        ((0.0, 0.0, 0.0), "must be non-zero"),
        ((1.0, 0.0), "three components"),
    ],
)
def test_malformed_orientation_vectors_are_rejected(orientation, match):
    with pytest.raises(ElementError, match=match):
        BeamElement3D((0, 1), STEEL, SECTION, orientation=orientation)


@pytest.mark.parametrize("label", ["inertia_z", "inertia_y", "torsion_constant"])
def test_a_missing_section_property_is_rejected(label):
    properties = {"inertia_z": 1e-8, "inertia_y": 1e-8, "torsion_constant": 1e-8}
    properties[label] = 0.0
    with pytest.raises(ElementError, match=f"positive section.{label}"):
        BeamElement3D((0, 1), STEEL, Section(area=1e-4, **properties))


def test_a_zero_length_member_is_rejected():
    coincident = np.zeros((2, 3))
    with pytest.raises(ElementError, match="zero length"):
        bound_beam(coincident).stiffness_matrix(coincident)


def test_the_element_needs_the_rotational_dofs():
    model = Model(dofs=(DOF.UX, DOF.UY, DOF.UZ), name="solid dofs only")
    model.add_node(0, 0.0, 0.0, 0.0)
    model.add_node(1, 1.0, 0.0, 0.0)
    with pytest.raises(ElementError, match="RX"):
        model.add_element(BeamElement3D((0, 1), STEEL, SECTION))


# -------------------------------------------------------------- local matrices


def test_the_local_stiffness_is_symmetric_with_six_zero_energy_modes():
    k = bound_beam().local_stiffness_matrix(1.5)
    np.testing.assert_allclose(k, k.T, atol=1e-9)
    eigenvalues = np.linalg.eigvalsh(k)
    assert np.sum(eigenvalues < 1e-6 * eigenvalues.max()) == 6


def test_the_local_planar_block_matches_the_planar_beam():
    """The (u, v, theta_z) DOFs must reproduce ``BeamElement2D`` exactly."""
    length = 1.7
    planar = BeamElement2D((0, 1), STEEL, SECTION)
    spatial = bound_beam()
    rows = [0, 1, 5, 6, 7, 11]
    np.testing.assert_allclose(
        spatial.local_stiffness_matrix(length)[np.ix_(rows, rows)],
        planar.local_stiffness_matrix(length),
        rtol=1e-14,
    )
    np.testing.assert_allclose(
        spatial.local_mass_matrix(length)[np.ix_(rows, rows)],
        planar.local_mass_matrix(length),
        rtol=1e-14,
    )


def test_the_two_bending_planes_carry_their_own_inertia():
    length = 1.3
    k = bound_beam().local_stiffness_matrix(length)
    assert k[1, 1] == pytest.approx(12.0 * STEEL.E * SECTION.inertia_z / length**3, rel=1e-14)
    assert k[2, 2] == pytest.approx(12.0 * STEEL.E * SECTION.inertia_y / length**3, rel=1e-14)
    # ``dw/dx = -theta_y`` flips the sign of the shear-moment coupling in x-z.
    assert k[1, 5] > 0.0
    assert k[2, 4] < 0.0


def test_the_axial_and_torsional_blocks_are_the_bar_stiffnesses():
    length = 2.4
    k = bound_beam().local_stiffness_matrix(length)
    assert k[0, 0] == pytest.approx(STEEL.E * SECTION.area / length, rel=1e-14)
    torsion = STEEL.shear_modulus * SECTION.torsion_constant / length
    assert k[3, 3] == pytest.approx(torsion, rel=1e-14)
    assert k[3, 9] == pytest.approx(-torsion, rel=1e-14)


def test_the_consistent_mass_conserves_the_member_mass_per_direction():
    length = 1.9
    m = bound_beam().local_mass_matrix(length)
    total = STEEL.density * SECTION.area * length
    for direction in (0, 1, 2):
        rows = [direction, direction + 6]
        assert m[np.ix_(rows, rows)].sum() == pytest.approx(total, rel=1e-14)
    polar = STEEL.density * (SECTION.inertia_y + SECTION.inertia_z) * length
    assert m[np.ix_([3, 9], [3, 9])].sum() == pytest.approx(polar, rel=1e-14)


def test_the_lumped_mass_halves_translation_and_twist():
    length = 1.1
    m = bound_beam(lumped_mass=True).local_mass_matrix(length)
    total = STEEL.density * SECTION.area * length
    polar = STEEL.density * (SECTION.inertia_y + SECTION.inertia_z) * length
    np.testing.assert_allclose(m, np.diag(np.diag(m)), atol=1e-18)
    np.testing.assert_allclose(np.diag(m)[:3], 0.5 * total, rtol=1e-14)
    assert np.diag(m)[3] == pytest.approx(0.5 * polar, rel=1e-14)
    # Bending rotations stay massless, exactly as the planar beam leaves them.
    np.testing.assert_array_equal(np.diag(m)[4:6], np.zeros(2))


def test_a_massless_material_gives_a_zero_mass_matrix():
    model = Model(dofs=FRAME_DOFS, name="massless")
    model.add_node(0, 0.0, 0.0, 0.0)
    model.add_node(1, 1.0, 0.0, 0.0)
    element = model.add_element(BeamElement3D((0, 1), Material(E=1.0), SECTION))
    np.testing.assert_array_equal(element.mass_matrix(ALONG_X), np.zeros((12, 12)))
    assert element.total_mass(ALONG_X) == 0.0


# -------------------------------------------------------------- global matrices


@pytest.mark.parametrize(
    "coords",
    [ALONG_X, np.array([[0.3, -0.2, 0.4], [1.4, 0.8, -0.5]])],
)
def test_rigid_body_motion_stores_no_energy(coords):
    element = bound_beam(coords)
    k = element.stiffness_matrix(coords)
    centre = coords.mean(axis=0)
    for translation in np.eye(3):
        motion = np.concatenate([np.concatenate([translation, np.zeros(3)])] * 2)
        np.testing.assert_allclose(k @ motion, np.zeros(12), atol=1e-6)
    for rotation in np.eye(3):
        motion = np.concatenate(
            [np.concatenate([np.cross(rotation, point - centre), rotation]) for point in coords]
        )
        assert motion @ k @ motion == pytest.approx(0.0, abs=1e-6 * abs(k).max())


def test_the_global_matrices_are_symmetric_with_the_expected_rank():
    coords = np.array([[0.3, -0.2, 0.4], [1.4, 0.8, -0.5]])
    element = bound_beam(coords)
    k = element.stiffness_matrix(coords)
    m = element.mass_matrix(coords)
    np.testing.assert_allclose(k, k.T, atol=1e-9)
    np.testing.assert_allclose(m, m.T, atol=1e-12)
    assert np.linalg.matrix_rank(k, tol=1e-6 * abs(k).max()) == 6
    assert np.linalg.eigvalsh(m).min() > 0.0


def test_the_element_mass_equals_the_member_mass():
    coords = np.array([[0.0, 0.0, 0.0], [0.6, 0.8, 0.0]])
    element = bound_beam(coords)
    assert element.length(coords) == pytest.approx(1.0, rel=1e-14)
    assert element.total_mass(coords) == pytest.approx(STEEL.density * SECTION.area, rel=1e-14)


def test_the_assembled_matrices_follow_a_rigid_rotation_of_the_model():
    rotation = rodrigues(np.array([1.0, 2.0, 3.0]), 0.7)
    straight, _ = cantilever(4)
    tilted, _ = cantilever(4, direction=rotation @ np.array([1.0, 0.0, 0.0]))
    assert ModalSolver(straight).solve(num_modes=6).frequencies == pytest.approx(
        ModalSolver(tilted).solve(num_modes=6).frequencies, rel=1e-9
    )


# -------------------------------------------------------------------- statics


def test_a_tip_load_gives_the_closed_form_cantilever_deflection():
    """A cubic Hermitian element is exact for an end load, even with one element."""
    load = 1.0e3
    for dof, inertia in ((DOF.UY, SECTION.inertia_z), (DOF.UZ, SECTION.inertia_y)):
        model, nodes = cantilever(1)
        tip = model.dof_index(nodes[-1], dof)
        displacements = solve_static(model, {tip: load})
        expected = load * BEAM_LENGTH**3 / (3.0 * STEEL.E * inertia)
        assert displacements[tip] == pytest.approx(expected, rel=1e-12)


@pytest.mark.parametrize(
    ("load_dof", "rotation_dof", "inertia", "sign"),
    [
        (DOF.UY, DOF.RZ, SECTION.inertia_z, 1.0),
        (DOF.UZ, DOF.RY, SECTION.inertia_y, -1.0),
    ],
)
def test_the_tip_rotation_matches_the_closed_form(load_dof, rotation_dof, inertia, sign):
    """``dw/dx = -theta_y`` makes the x-z plane rotation the mirror of the x-y one."""
    load = 1.0e3
    model, nodes = cantilever(1)
    tip = model.dof_index(nodes[-1], load_dof)
    displacements = solve_static(model, {tip: load})
    expected = sign * load * BEAM_LENGTH**2 / (2.0 * STEEL.E * inertia)
    assert displacements[model.dof_index(nodes[-1], rotation_dof)] == pytest.approx(
        expected, rel=1e-12
    )


def test_axial_and_torsional_compliance_match_the_bar_formulas():
    model, nodes = cantilever(1)
    force, torque = 5.0e4, 20.0
    axial = model.dof_index(nodes[-1], DOF.UX)
    twist = model.dof_index(nodes[-1], DOF.RX)
    displacements = solve_static(model, {axial: force, twist: torque})
    assert displacements[axial] == pytest.approx(
        force * BEAM_LENGTH / (STEEL.E * SECTION.area), rel=1e-12
    )
    assert displacements[twist] == pytest.approx(
        torque * BEAM_LENGTH / (STEEL.shear_modulus * SECTION.torsion_constant), rel=1e-12
    )


def test_the_orientation_vector_rolls_the_section():
    """Rolling the section by 90 degrees swaps which inertia resists a global load."""
    load = 1.0e3
    model, nodes = cantilever(1, orientation=(0.0, 0.0, 1.0))
    tip = model.dof_index(nodes[-1], DOF.UZ)
    displacements = solve_static(model, {tip: load})
    expected = load * BEAM_LENGTH**3 / (3.0 * STEEL.E * SECTION.inertia_z)
    assert displacements[tip] == pytest.approx(expected, rel=1e-12)


def test_end_forces_balance_the_applied_tip_load():
    load = 1.0e3
    model, nodes = cantilever(1)
    tip = model.dof_index(nodes[-1], DOF.UY)
    displacements = solve_static(model, {tip: load})
    element = model.elements[0]
    forces = element.end_forces(model.node_coords(element.node_ids), displacements)
    assert forces[1] == pytest.approx(-load, rel=1e-10)
    assert forces[7] == pytest.approx(load, rel=1e-10)
    assert forces[11] == pytest.approx(0.0, abs=1e-9 * load * BEAM_LENGTH)
    # Root moment carries the full lever arm.
    assert forces[5] == pytest.approx(-load * BEAM_LENGTH, rel=1e-10)


def test_end_forces_vanish_under_rigid_body_motion():
    coords = np.array([[0.3, -0.2, 0.4], [1.4, 0.8, -0.5]])
    element = bound_beam(coords)
    motion = np.concatenate([np.concatenate([[0.1, -0.3, 0.2], np.zeros(3)])] * 2)
    np.testing.assert_allclose(element.end_forces(coords, motion), np.zeros(12), atol=1e-6)


def test_end_forces_reject_a_wrong_sized_vector():
    with pytest.raises(ElementError, match="expected 12 nodal displacements"):
        bound_beam().end_forces(ALONG_X, np.zeros(6))


# ---------------------------------------------------------------------- modal


def test_the_cantilever_spectrum_matches_the_closed_form_in_both_planes():
    model, _ = cantilever(12)
    frequencies = ModalSolver(model).solve(num_modes=4).frequencies
    expected = sorted(
        cantilever_frequency(index, inertia)
        for index in (0, 1)
        for inertia in (SECTION.inertia_z, SECTION.inertia_y)
    )
    np.testing.assert_allclose(frequencies, expected, rtol=5e-3)


def test_the_bending_spectrum_converges_quadratically():
    coarse, _ = cantilever(2)
    fine, _ = cantilever(8)
    exact = cantilever_frequency(1, SECTION.inertia_z)
    errors = [
        abs(ModalSolver(model).solve(num_modes=3).frequencies[2] - exact) / exact
        for model in (coarse, fine)
    ]
    assert errors[1] < errors[0] / 10.0


def test_the_first_torsional_mode_matches_the_shaft_formula():
    model, nodes = cantilever(16)
    result = ModalSolver(model).solve(num_modes=12)
    exact = torsion_frequency()
    closest = int(np.argmin(np.abs(result.frequencies - exact)))
    assert result.frequencies[closest] == pytest.approx(exact, rel=5e-3)
    shape = result.shapes[:, closest]
    twist = abs(shape[model.dof_index(nodes[-1], DOF.RX)])
    assert twist == max(abs(shape[model.dof_index(nodes[-1], dof)]) for dof in FRAME_DOFS)


def test_the_spatial_beam_reproduces_the_planar_beam_spectrum():
    """Along global X the planes decouple, so every planar mode is a spatial mode."""
    planar = beam_mesh(BEAM_LENGTH, 6, STEEL, SECTION, support="cantilever")
    spatial, _ = cantilever(6)
    planar_frequencies = ModalSolver(planar).solve(num_modes=3).frequencies
    spatial_frequencies = ModalSolver(spatial).solve(num_modes=10).frequencies
    for frequency in planar_frequencies:
        assert np.min(np.abs(spatial_frequencies - frequency)) / frequency < 1e-8


def test_a_free_frame_has_six_rigid_body_modes():
    mesh = MeshBuilder(dofs=FRAME_DOFS, name="free frame")
    nodes = mesh.line_nodes((0.0, 0.0, 0.0), (BEAM_LENGTH, 0.0, 0.0), 6)
    mesh.chain(nodes, lambda a, b: mesh.add_beam3d(a, b, STEEL, SECTION))
    result = ModalSolver(mesh.build()).solve(num_modes=8)
    assert int(np.sum(result.rigid_body_modes)) == 6
    np.testing.assert_allclose(result.frequencies[:6], np.zeros(6), atol=1e-3)
    assert result.frequencies[6] > 10.0


def test_an_l_frame_assembles_and_solves():
    """Two non-collinear members exercise the transformation in assembly."""
    mesh = MeshBuilder(dofs=FRAME_DOFS, name="L frame")
    mesh.add_node(0, 0.0, 0.0, 0.0)
    mesh.add_node(1, 1.0, 0.0, 0.0)
    mesh.add_node(2, 1.0, 0.0, 0.8)
    mesh.add_beam3d(0, 1, STEEL, SECTION)
    mesh.add_beam3d(1, 2, STEEL, SECTION)
    mesh.fix(0)
    model = mesh.build()
    system = assemble_system(model)
    for matrix in (system.K, system.M):
        assert abs(matrix - matrix.T).max() <= 1e-6 * abs(matrix).max()
    assert system.total_mass == pytest.approx(STEEL.density * SECTION.area * 1.8, rel=1e-12)
    assert ModalSolver(model).solve(num_modes=4).frequencies.min() > 0.0


def test_the_mesh_builder_can_add_a_spatial_beam():
    mesh = MeshBuilder(dofs=FRAME_DOFS, name="one beam")
    mesh.add_node(0, 0.0, 0.0, 0.0)
    mesh.add_node(1, 1.5, 0.0, 0.0)
    element = mesh.add_beam3d(0, 1, STEEL, SECTION)
    assert isinstance(element, BeamElement3D)
    stiffness = assemble_stiffness(mesh.build())
    assert stiffness.shape == (12, 12)
