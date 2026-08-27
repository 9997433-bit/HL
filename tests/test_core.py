"""Unit tests for the model container, element library and matrix assembly."""

from __future__ import annotations

import math

import numpy as np
import pytest

from openfemlab import (
    DOF,
    BeamElement2D,
    ElementError,
    Material,
    Model,
    ModelError,
    Section,
    SpringElement,
    TrussElement,
    assemble_mass,
    assemble_stiffness,
)
from openfemlab.mesh.simple import MeshBuilder, bar_mesh, spring_mass_chain, truss_from_arrays

STEEL = Material(E=2.1e11, density=7850.0)
SQUARE = Section(area=1e-4, inertia_z=1e-4**2 / 12.0)


# ------------------------------------------------------------------- model


def test_dof_parsing_and_numbering():
    model = Model(dofs=("ux", "UY", DOF.RZ), name="frame")
    model.add_node("a", 0.0, 0.0)
    model.add_node("b", 1.0, 0.0)

    assert model.ndof_per_node == 3
    assert model.num_dofs == 6
    assert model.dof_index("a", "UY") == 1
    assert model.dof_index("b", DOF.RZ) == 5
    assert model.describe_dof(4) == ("b", DOF.UY)
    np.testing.assert_array_equal(model.dof_indices("b"), [3, 4, 5])
    assert model.translational_dofs == (DOF.UX, DOF.UY)
    assert model.rotational_dofs == (DOF.RZ,)
    assert model.dof_labels[:2] == ["a:UX", "a:UY"]
    np.testing.assert_array_equal(model.dof_types, [0, 1, 5, 0, 1, 5])


def test_model_input_validation():
    model = Model(dofs=(DOF.UX,))
    model.add_node(1, 0.0)
    with pytest.raises(ModelError, match="duplicate node id"):
        model.add_node(1, 1.0)
    with pytest.raises(ModelError, match="unknown node id"):
        model.dof_index(99, DOF.UX)
    with pytest.raises(ModelError, match="not active"):
        model.dof_index(1, DOF.UZ)
    with pytest.raises(ModelError, match="unknown DOF name"):
        DOF.parse("torsion")
    with pytest.raises(ModelError, match="at least one active DOF"):
        Model(dofs=())
    with pytest.raises(ModelError, match="Young's modulus"):
        Material(E=-1.0)
    with pytest.raises(ModelError, match="section area"):
        Section(area=0.0)


def test_boundary_conditions_partition_dofs():
    model = Model(dofs=(DOF.UX, DOF.UY))
    model.add_nodes([(0, 0.0, 0.0), (1, 1.0, 0.0), (2, 2.0, 0.0)])
    model.fix(0)
    model.fix(2, (DOF.UY,))

    np.testing.assert_array_equal(model.constrained_dofs, [0, 1, 5])
    np.testing.assert_array_equal(model.free_dofs, [2, 3, 4])
    assert model.is_constrained(2, DOF.UY)
    model.release(2, (DOF.UY,))
    assert not model.is_constrained(2, DOF.UY)
    model.fix_dof_globally(DOF.UY)
    np.testing.assert_array_equal(model.constrained_dofs, [0, 1, 3, 5])


def test_point_masses_accumulate_per_dof():
    model = Model(dofs=(DOF.UX, DOF.UY, DOF.RZ))
    model.add_node(0, 0.0, 0.0)
    model.add_point_mass(0, 3.0)
    model.add_point_mass(0, 1.5, dofs=(DOF.UX,))
    model.add_rotary_inertia(0, 0.25)

    np.testing.assert_allclose(model.point_mass_vector(), [4.5, 3.0, 0.25])
    with pytest.raises(ModelError, match="non-negative"):
        model.add_point_mass(0, -1.0)


# ----------------------------------------------------------------- elements


def test_truss_stiffness_and_mass_matrices():
    element = TrussElement((0, 1), STEEL, SQUARE)
    element.bind((DOF.UX, DOF.UY))
    coords = np.array([[0.0, 0.0, 0.0], [3.0, 4.0, 0.0]])  # length 5, c = (0.6, 0.8)

    k = element.stiffness_matrix(coords)
    ea_over_l = STEEL.E * SQUARE.area / 5.0
    c = np.array([0.6, 0.8])
    block = np.outer(c, c) * ea_over_l
    np.testing.assert_allclose(k[:2, :2], block)
    np.testing.assert_allclose(k[:2, 2:], -block)
    np.testing.assert_allclose(k, k.T)
    np.testing.assert_allclose(k @ np.tile(c, 2), 0.0, atol=1e-6)  # rigid translation

    m = element.mass_matrix(coords)
    total = STEEL.density * SQUARE.area * 5.0
    assert m.sum() == pytest.approx(2.0 * total)  # two translational directions
    np.testing.assert_allclose(m, m.T)
    assert np.all(np.linalg.eigvalsh(m) > 0.0)

    lumped = TrussElement((0, 1), STEEL, SQUARE, lumped_mass=True)
    lumped.bind((DOF.UX, DOF.UY))
    np.testing.assert_allclose(lumped.mass_matrix(coords), np.eye(4) * total / 2.0)


def test_truss_axial_stiffness_and_degenerate_geometry():
    element = TrussElement((0, 1), STEEL, SQUARE)
    with pytest.raises(ElementError, match="not bound"):
        element.stiffness_matrix(np.zeros((2, 3)))
    element.bind((DOF.UX,))
    assert element.axial_stiffness(np.array([[0.0, 0, 0], [2.0, 0, 0]])) == pytest.approx(
        STEEL.E * SQUARE.area / 2.0
    )
    with pytest.raises(ElementError, match="zero length"):
        element.stiffness_matrix(np.zeros((2, 3)))
    with pytest.raises(ElementError, match="repeated nodes"):
        TrussElement((5, 5), STEEL, SQUARE)
    with pytest.raises(ElementError, match="expects 2 nodes"):
        TrussElement((1, 2, 3), STEEL, SQUARE)


def test_element_requires_active_dofs():
    beam = BeamElement2D((0, 1), STEEL, SQUARE)
    with pytest.raises(ElementError, match="requires DOFs"):
        beam.bind((DOF.UX, DOF.UY))
    with pytest.raises(ElementError, match="inertia_z"):
        BeamElement2D((0, 1), STEEL, Section(area=1e-4))


def test_beam_matrices_are_symmetric_and_reproduce_tip_stiffness():
    beam = BeamElement2D((0, 1), STEEL, SQUARE)
    beam.bind((DOF.UX, DOF.UY, DOF.RZ))
    length = 2.0
    coords = np.array([[0.0, 0.0, 0.0], [length, 0.0, 0.0]])

    k = beam.stiffness_matrix(coords)
    np.testing.assert_allclose(k, k.T)
    free = k[3:, 3:]  # clamp node 0 -> cantilever tip stiffness
    tip = np.linalg.solve(free, np.array([0.0, 1.0, 0.0]))
    assert tip[1] == pytest.approx(length**3 / (3.0 * STEEL.E * SQUARE.inertia_z))

    m = beam.mass_matrix(coords)
    total = STEEL.density * SQUARE.area * length
    translational = [0, 1, 3, 4]
    assert m[np.ix_(translational, translational)].sum() == pytest.approx(2.0 * total)


def test_beam_rotation_preserves_eigenvalues():
    horizontal = BeamElement2D((0, 1), STEEL, SQUARE)
    horizontal.bind((DOF.UX, DOF.UY, DOF.RZ))
    vertical = BeamElement2D((0, 1), STEEL, SQUARE)
    vertical.bind((DOF.UX, DOF.UY, DOF.RZ))

    k_h = horizontal.stiffness_matrix(np.array([[0.0, 0, 0], [1.0, 0, 0]]))
    k_v = vertical.stiffness_matrix(np.array([[0.0, 0, 0], [0.0, 1.0, 0]]))
    np.testing.assert_allclose(
        np.linalg.eigvalsh(k_h), np.linalg.eigvalsh(k_v), rtol=1e-10, atol=1e-6
    )


def test_spring_element_matrices():
    spring = SpringElement((0, 1), 250.0, dof=DOF.UX)
    spring.bind((DOF.UX,))
    np.testing.assert_allclose(
        spring.stiffness_matrix(np.zeros((2, 3))), [[250.0, -250.0], [-250.0, 250.0]]
    )
    np.testing.assert_allclose(spring.mass_matrix(np.zeros((2, 3))), np.zeros((2, 2)))

    grounded = SpringElement((0,), 250.0)
    grounded.bind((DOF.UX,))
    np.testing.assert_allclose(grounded.stiffness_matrix(np.zeros((1, 3))), [[250.0]])

    with pytest.raises(ElementError, match="stiffness must be positive"):
        SpringElement((0, 1), -5.0)
    with pytest.raises(ElementError, match="one node .* or two nodes"):
        SpringElement((0, 1, 2), 5.0)


# ----------------------------------------------------------------- assembly


def test_assembled_matrices_are_symmetric_and_conserve_mass():
    length, n = 1.0, 8
    model = bar_mesh(length, n, STEEL, SQUARE, fixed_start=False)
    system = model.assemble()

    K, M = system.K.toarray(), system.M.toarray()
    np.testing.assert_allclose(K, K.T, atol=1e-6)
    np.testing.assert_allclose(M, M.T, atol=1e-12)
    assert system.total_mass == pytest.approx(STEEL.density * SQUARE.area * length)
    # unconstrained axial bar: rigid translation is a null vector of K
    np.testing.assert_allclose(K @ np.ones(n + 1), 0.0, atol=1e-6)
    assert system.num_dofs == n + 1
    assert system.num_free_dofs == n + 1


def test_assembly_partitioning_and_expansion():
    model = spring_mass_chain(3, 1000.0, 2.0)
    system = model.assemble()

    np.testing.assert_array_equal(system.constrained_dofs, [0])
    np.testing.assert_array_equal(system.free_dofs, [1, 2, 3])
    K_ff, M_ff = system.reduced()
    assert K_ff.shape == (3, 3)
    np.testing.assert_allclose(M_ff.toarray(), np.eye(3) * 2.0)

    expanded = system.expand(np.array([1.0, 2.0, 3.0]))
    np.testing.assert_allclose(expanded, [0.0, 1.0, 2.0, 3.0])
    expanded_block = system.expand(np.ones((3, 2)))
    assert expanded_block.shape == (4, 2)
    with pytest.raises(ModelError, match="free-DOF rows"):
        system.expand(np.ones(2))


def test_point_masses_enter_the_mass_matrix():
    model = Model(dofs=(DOF.UX,))
    model.add_node(0, 0.0)
    model.add_node(1, 1.0)
    model.add_spring(0, 1, 100.0)
    model.add_point_mass(1, 7.0)

    K = assemble_stiffness(model).toarray()
    np.testing.assert_allclose(K, [[100.0, -100.0], [-100.0, 100.0]])
    np.testing.assert_allclose(assemble_mass(model).toarray(), [[0.0, 0.0], [0.0, 7.0]])
    np.testing.assert_allclose(
        assemble_mass(model, include_point_masses=False).toarray(), np.zeros((2, 2))
    )


def test_assembly_rejects_empty_models():
    with pytest.raises(ModelError, match="empty model"):
        Model(dofs=(DOF.UX,)).assemble()
    model = Model(dofs=(DOF.UX,))
    model.add_node(0, 0.0)
    with pytest.raises(ModelError, match="neither elements nor point masses"):
        model.assemble()


# --------------------------------------------------------------------- mesh


def test_mesh_builder_line_and_auto_ids():
    mesh = MeshBuilder(dofs=(DOF.UX, DOF.UY))
    ids = mesh.line_nodes((0.0, 0.0), (4.0, 0.0), 4)
    assert ids == [0, 1, 2, 3, 4]
    np.testing.assert_allclose(mesh.model.coordinates[:, 0], [0.0, 1.0, 2.0, 3.0, 4.0])
    mesh.chain(ids, lambda a, b: mesh.add_truss(a, b, STEEL, SQUARE))
    assert mesh.build().num_elements == 4
    with pytest.raises(ModelError, match="num_elements"):
        mesh.line_nodes((0.0, 0.0), (1.0, 0.0), 0)


def test_spring_mass_chain_layout():
    model = spring_mass_chain(4, [1.0, 2.0, 3.0, 4.0, 5.0], 5.0, fixed_end=True)
    assert model.num_nodes == 6
    assert model.num_elements == 5
    assert model.num_dofs == 6
    np.testing.assert_array_equal(model.constrained_dofs, [0, 5])
    np.testing.assert_allclose(model.point_mass_vector(), [0.0, 5.0, 5.0, 5.0, 5.0, 0.0])
    with pytest.raises(ModelError, match="expected 1 or 5"):
        spring_mass_chain(4, [1.0, 2.0], 5.0, fixed_end=True)
    with pytest.raises(ModelError, match="num_masses"):
        spring_mass_chain(0, 1.0, 1.0)


def test_bar_mesh_geometry_and_options():
    model = bar_mesh(2.0, 4, STEEL, SQUARE, direction=(0.0, 0.0, 1.0), dofs=(DOF.UZ,))
    np.testing.assert_allclose(model.coordinates[:, 2], [0.0, 0.5, 1.0, 1.5, 2.0])
    assert model.num_elements == 4
    np.testing.assert_array_equal(model.constrained_dofs, [0])
    with pytest.raises(ModelError, match="length must be positive"):
        bar_mesh(0.0, 2, STEEL, SQUARE)
    with pytest.raises(ModelError, match="direction vector"):
        bar_mesh(1.0, 2, STEEL, SQUARE, direction=(0.0, 0.0, 0.0))


def test_truss_from_arrays_validation():
    coords = [[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]]
    model = truss_from_arrays(
        coords, [(0, 1), (1, 2), (2, 0)], STEEL, SQUARE, dofs=(DOF.UX, DOF.UY)
    )
    assert model.num_nodes == 3 and model.num_elements == 3
    total = sum(e.total_mass(model.node_coords(e.node_ids)) for e in model.elements)
    perimeter = 1.0 + 2.0 * math.hypot(0.5, 1.0)
    assert total == pytest.approx(STEEL.density * SQUARE.area * perimeter)
    with pytest.raises(ModelError, match="two columns"):
        truss_from_arrays(coords, [(0, 1, 2)], STEEL, SQUARE)
    with pytest.raises(ModelError, match="outside the coordinate array"):
        truss_from_arrays(coords, [(0, 7)], STEEL, SQUARE)
