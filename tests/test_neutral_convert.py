"""Coverage for the NeutralModel -> Model conversion in ``io/neutral_convert.py``.

The conversion is what makes an imported mesh re-analyzable, so the tests are
written at three levels:

* bookkeeping -- DOF inference, node labels, element labels, property lookup
  and the fallbacks a geometry-only mesh file needs;
* equivalence -- a converted model assembles the *same* matrices as the model a
  user would have built by hand with the same elements, per element family;
* failure -- every malformed input reports a ``FormatError`` naming the block.
"""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.core.assembly import assemble_system
from openfemlab.core.elements import (
    BeamElement2D,
    BeamElement3D,
    Hex8Element,
    Quad4Element,
    ShellQuad4Element,
    Tet4Element,
    TrussElement,
)
from openfemlab.core.model import DOF, Material, Model, Section
from openfemlab.core.neutral import ElementType, NeutralMaterial, NeutralModel, NeutralProperty
from openfemlab.io import FormatError, neutral_to_model
from openfemlab.io.neutral_convert import (
    infer_dofs,
    material_from_neutral,
    section_from_values,
    to_model,
)
from openfemlab.mesh.simple import bar_mesh
from openfemlab.solver.modal import ModalSolver

STEEL = NeutralMaterial(id=1, E=2.1e11, nu=0.3, rho=7850.0, name="steel")
CORE_STEEL = Material(E=2.1e11, density=7850.0, nu=0.3, name="steel")

#: Section values of a 20 x 20 mm square bar, in the neutral spelling.
BAR_VALUES = {"A": 4.0e-4, "Iz": 1.3333e-8, "Iy": 1.3333e-8, "J": 2.2533e-8}
BAR_SECTION = Section(
    area=BAR_VALUES["A"],
    inertia_z=BAR_VALUES["Iz"],
    inertia_y=BAR_VALUES["Iy"],
    torsion_constant=BAR_VALUES["J"],
)

UNIT_SQUARE = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]])
UNIT_CUBE = np.vstack((UNIT_SQUARE, UNIT_SQUARE + np.array([0.0, 0.0, 1.0])))


def line_nodes(count: int, spacing: float = 0.25) -> np.ndarray:
    return np.column_stack(
        (np.arange(count, dtype=float) * spacing, np.zeros(count), np.zeros(count))
    )


def neutral(
    element_type: ElementType,
    nodes: np.ndarray,
    connectivity,
    *,
    node_ids=None,
    values: dict[str, float] | None = None,
    with_tables: bool = True,
    meta: dict | None = None,
) -> NeutralModel:
    """A single-block neutral model with one property and one material."""
    nodes = np.asarray(nodes, dtype=float)
    labels = np.arange(1, nodes.shape[0] + 1) if node_ids is None else np.asarray(node_ids)
    block = np.asarray(connectivity, dtype=np.int64)
    tables: dict = {}
    if with_tables:
        tables = {
            "materials": {STEEL.id: STEEL},
            "properties": {
                7: NeutralProperty(id=7, material_id=STEEL.id, values=dict(values or BAR_VALUES))
            },
        }
    return NeutralModel(
        nodes=nodes,
        node_ids=labels,
        elements={element_type: block},
        element_property_ids={element_type: np.full(block.shape[0], 7, dtype=np.int64)},
        meta=meta or {},
        **tables,
    )


def rod_chain(count: int = 5, spacing: float = 0.25, *, node_ids=None, **kwargs) -> NeutralModel:
    labels = list(range(1, count + 1)) if node_ids is None else list(node_ids)
    connectivity = list(zip(labels, labels[1:], strict=False))
    return neutral(
        ElementType.ROD2, line_nodes(count, spacing), connectivity, node_ids=labels, **kwargs
    )


def stiffness(model: Model) -> np.ndarray:
    return assemble_system(model).K.toarray()


class TestInferDofs:
    def test_quad_only_mesh_stays_planar(self) -> None:
        model = neutral(ElementType.QUAD4, UNIT_SQUARE, [[1, 2, 3, 4]], values={"t": 0.01})

        assert infer_dofs(model) == (DOF.UX, DOF.UY)

    def test_quad_only_mesh_gets_six_dofs_when_bound_as_shell(self) -> None:
        model = neutral(ElementType.QUAD4, UNIT_SQUARE, [[1, 2, 3, 4]], values={"t": 0.01})

        assert infer_dofs(model, quad4_as="shell") == tuple(DOF)

    @pytest.mark.parametrize(
        "element_type, connectivity",
        [
            (ElementType.TET4, [[1, 2, 3, 5]]),
            (ElementType.HEX8, [[1, 2, 3, 4, 5, 6, 7, 8]]),
            (ElementType.ROD2, [[1, 2]]),
        ],
    )
    def test_translational_blocks_need_three_dofs(self, element_type, connectivity) -> None:
        model = neutral(element_type, UNIT_CUBE, connectivity)

        assert infer_dofs(model) == (DOF.UX, DOF.UY, DOF.UZ)

    def test_a_beam_block_pulls_in_the_rotations(self) -> None:
        model = neutral(ElementType.BEAM2, line_nodes(2), [[1, 2]])

        assert infer_dofs(model) == tuple(DOF)

    def test_mixed_blocks_take_the_union(self) -> None:
        model = neutral(ElementType.QUAD4, UNIT_CUBE, [[1, 2, 3, 4]], values={"t": 0.01})
        model.elements[ElementType.TET4] = np.array([[1, 2, 3, 5]], dtype=np.int64)

        assert infer_dofs(model) == (DOF.UX, DOF.UY, DOF.UZ)

    def test_empty_blocks_do_not_count(self) -> None:
        model = neutral(ElementType.QUAD4, UNIT_CUBE, [[1, 2, 3, 4]], values={"t": 0.01})
        model.elements[ElementType.BEAM2] = np.zeros((0, 2), dtype=np.int64)

        assert infer_dofs(model) == (DOF.UX, DOF.UY)

    def test_a_mesh_without_elements_falls_back_to_translations(self) -> None:
        model = NeutralModel(nodes=UNIT_SQUARE, node_ids=[1, 2, 3, 4])

        assert infer_dofs(model) == (DOF.UX, DOF.UY, DOF.UZ)


class TestNodesAndLabels:
    def test_node_labels_and_coordinates_survive(self) -> None:
        source = rod_chain(3, node_ids=[101, 102, 103])

        model = to_model(source)

        assert model.node_ids == [101, 102, 103]
        np.testing.assert_allclose(model.coordinates, source.nodes)
        assert model.dof_index(103, DOF.UX) == 6

    def test_element_labels_come_from_the_meta_block(self) -> None:
        source = rod_chain(3, meta={"element_ids": {"rod2": [11, 12]}})

        model = to_model(source)

        assert [element.id for element in model.elements] == [11, 12]

    def test_elements_are_labelled_one_upwards_without_meta(self) -> None:
        model = to_model(rod_chain(4))

        assert [element.id for element in model.elements] == [1, 2, 3]

    def test_the_model_name_comes_from_meta_then_the_argument(self) -> None:
        source = rod_chain(2, meta={"name": "imported"})

        assert to_model(source).name == "imported"
        assert to_model(source, name="explicit").name == "explicit"
        assert to_model(rod_chain(2)).name == "model"

    def test_duplicate_node_labels_are_rejected(self) -> None:
        source = rod_chain(3, node_ids=[1, 2, 1])

        with pytest.raises(FormatError, match="cannot add node 1"):
            to_model(source)


class TestRodConversion:
    def test_a_chain_becomes_truss_elements_with_the_property_data(self) -> None:
        model = to_model(rod_chain(5))

        assert model.num_nodes == 5
        assert model.num_elements == 4
        assert all(isinstance(element, TrussElement) for element in model.elements)
        first = model.elements[0]
        assert first.material == CORE_STEEL
        assert first.section.area == pytest.approx(BAR_VALUES["A"])
        assert first.node_ids == (1, 2)

    def test_the_converted_chain_matches_the_hand_built_bar(self) -> None:
        converted = to_model(rod_chain(9), dofs=(DOF.UX,))
        converted.fix(1, (DOF.UX,))
        reference = bar_mesh(2.0, 8, CORE_STEEL, Section(area=BAR_VALUES["A"]))

        np.testing.assert_allclose(stiffness(converted), stiffness(reference))
        np.testing.assert_allclose(
            ModalSolver(converted).solve(num_modes=3).frequencies,
            ModalSolver(reference).solve(num_modes=3).frequencies,
        )

    def test_the_axial_spectrum_matches_the_continuum_bar(self) -> None:
        converted = to_model(rod_chain(33, 0.0625), dofs=(DOF.UX,))
        converted.fix(1, (DOF.UX,))

        wave_speed = np.sqrt(CORE_STEEL.E / CORE_STEEL.density)
        first = ModalSolver(converted).solve(num_modes=1).frequencies[0]

        assert first == pytest.approx(wave_speed / (4.0 * 2.0), rel=2e-3)

    def test_lumped_mass_is_passed_through(self) -> None:
        model = to_model(rod_chain(3), lumped_mass=True)

        assert all(element.lumped_mass for element in model.elements)


class TestBeamConversion:
    def test_a_beam_block_binds_the_spatial_element_by_default(self) -> None:
        model = to_model(neutral(ElementType.BEAM2, line_nodes(3), [[1, 2], [2, 3]]))

        assert model.dofs == tuple(DOF)
        assert all(isinstance(element, BeamElement3D) for element in model.elements)
        assert model.elements[0].section == BAR_SECTION

    def test_a_planar_signature_selects_the_planar_beam(self) -> None:
        source = neutral(ElementType.BEAM2, line_nodes(3), [[1, 2], [2, 3]])

        model = to_model(source, dofs=(DOF.UX, DOF.UY, DOF.RZ))

        assert all(isinstance(element, BeamElement2D) for element in model.elements)
        reference = Model(dofs=(DOF.UX, DOF.UY, DOF.RZ))
        for index, point in enumerate(source.nodes, start=1):
            reference.add_node(index, point)
        for pair in ((1, 2), (2, 3)):
            reference.add_element(BeamElement2D(pair, CORE_STEEL, BAR_SECTION))
        np.testing.assert_allclose(stiffness(model), stiffness(reference))

    def test_nastran_section_spellings_are_accepted(self) -> None:
        source = neutral(
            ElementType.BEAM2,
            line_nodes(2),
            [[1, 2]],
            values={"A": 4.0e-4, "I1": 1.0e-8, "I2": 2.0e-8, "J": 3.0e-8},
        )

        section = to_model(source).elements[0].section

        assert (section.inertia_z, section.inertia_y) == (1.0e-8, 2.0e-8)
        assert section.torsion_constant == 3.0e-8

    def test_the_orientation_vector_reaches_the_element(self) -> None:
        source = neutral(ElementType.BEAM2, line_nodes(2), [[1, 2]])

        model = to_model(source, beam_orientation=(0.0, 0.0, 1.0))

        np.testing.assert_allclose(model.elements[0].orientation, [0.0, 0.0, 1.0])

    def test_a_beam_needs_rotational_dofs(self) -> None:
        source = neutral(ElementType.BEAM2, line_nodes(2), [[1, 2]])

        with pytest.raises(FormatError, match="six spatial DOFs"):
            to_model(source, dofs=(DOF.UX, DOF.UY, DOF.UZ))

    def test_a_beam_without_bending_inertia_is_rejected(self) -> None:
        source = neutral(ElementType.BEAM2, line_nodes(2), [[1, 2]], values={"A": 1e-4})

        with pytest.raises(FormatError, match="positive section.inertia"):
            to_model(source)


class TestQuadConversion:
    def two_quads(self, **kwargs) -> NeutralModel:
        nodes = np.vstack((UNIT_SQUARE, [[2.0, 0.0, 0.0], [2.0, 1.0, 0.0]]))
        return neutral(
            ElementType.QUAD4, nodes, [[1, 2, 3, 4], [2, 5, 6, 3]], **kwargs
        )

    def test_the_thickness_comes_from_the_property(self) -> None:
        model = to_model(self.two_quads(values={"t": 0.004}))

        assert all(isinstance(element, Quad4Element) for element in model.elements)
        assert [element.thickness for element in model.elements] == [0.004, 0.004]

    def test_the_thickness_argument_covers_a_property_without_one(self) -> None:
        model = to_model(self.two_quads(values={"A": 1.0}), thickness=0.002)

        assert model.elements[0].thickness == pytest.approx(0.002)

    def test_the_plane_state_is_passed_through(self) -> None:
        model = to_model(self.two_quads(values={"t": 0.01}), plane="strain")

        assert model.elements[0].plane == "strain"

    def test_the_converted_plate_matches_the_hand_built_one(self) -> None:
        source = self.two_quads(values={"t": 0.01})

        converted = to_model(source)

        reference = Model(dofs=(DOF.UX, DOF.UY))
        for index, point in enumerate(source.nodes, start=1):
            reference.add_node(index, point)
        for corners in ((1, 2, 3, 4), (2, 5, 6, 3)):
            reference.add_element(Quad4Element(corners, CORE_STEEL, thickness=0.01))
        np.testing.assert_allclose(stiffness(converted), stiffness(reference))


class TestShellQuadConversion:
    def single_quad(self, **kwargs) -> NeutralModel:
        return neutral(ElementType.QUAD4, UNIT_SQUARE, [[1, 2, 3, 4]], **kwargs)

    def test_quad4_as_shell_binds_the_shell_element(self) -> None:
        model = to_model(self.single_quad(values={"t": 0.01}), quad4_as="shell")

        assert model.dofs == tuple(DOF)
        assert all(isinstance(element, ShellQuad4Element) for element in model.elements)

    def test_the_converted_shell_matches_the_hand_built_one(self) -> None:
        source = self.single_quad(values={"t": 0.01})

        converted = to_model(source, quad4_as="shell")

        reference = Model(dofs=tuple(DOF))
        for index, point in enumerate(source.nodes, start=1):
            reference.add_node(index, point)
        reference.add_element(ShellQuad4Element((1, 2, 3, 4), CORE_STEEL, thickness=0.01))
        np.testing.assert_allclose(stiffness(converted), stiffness(reference), rtol=0.0, atol=0.0)

    def test_membrane_binding_is_still_the_default(self) -> None:
        model = to_model(self.single_quad(values={"t": 0.01}))

        assert all(isinstance(element, Quad4Element) for element in model.elements)


class TestSolidConversion:
    def test_a_tetrahedron_carries_its_material_mass(self) -> None:
        source = neutral(ElementType.TET4, UNIT_CUBE, [[1, 2, 4, 5]], values={"A": 1.0})

        model = to_model(source)
        element = model.elements[0]

        assert isinstance(element, Tet4Element)
        coords = model.node_coords(element.node_ids)
        assert element.volume(coords) == pytest.approx(1.0 / 6.0)
        assert element.total_mass(coords) == pytest.approx(STEEL.rho / 6.0)

    def test_the_converted_brick_matches_the_hand_built_one(self) -> None:
        source = neutral(
            ElementType.HEX8, UNIT_CUBE, [[1, 2, 3, 4, 5, 6, 7, 8]], values={"A": 1.0}
        )

        converted = to_model(source)

        reference = Model(dofs=(DOF.UX, DOF.UY, DOF.UZ))
        for index, point in enumerate(UNIT_CUBE, start=1):
            reference.add_node(index, point)
        reference.add_element(Hex8Element(range(1, 9), CORE_STEEL))
        assert isinstance(converted.elements[0], Hex8Element)
        np.testing.assert_allclose(stiffness(converted), stiffness(reference))

    def test_a_free_brick_has_six_rigid_body_modes(self) -> None:
        source = neutral(
            ElementType.HEX8, UNIT_CUBE, [[1, 2, 3, 4, 5, 6, 7, 8]], values={"A": 1.0}
        )

        result = ModalSolver(to_model(source)).solve(num_modes=8)

        assert int(np.sum(result.rigid_body_modes)) == 6

    def test_the_integration_order_is_passed_through(self) -> None:
        source = neutral(
            ElementType.HEX8, UNIT_CUBE, [[1, 2, 3, 4, 5, 6, 7, 8]], values={"A": 1.0}
        )

        model = to_model(source, integration_order=3)

        assert model.elements[0].integration_order == 3


class TestGeometryOnlyMeshes:
    """A mesh file carries no material data; the fallbacks stand in for it."""

    def test_material_and_section_arguments_fill_an_empty_table(self) -> None:
        source = rod_chain(3, with_tables=False)

        model = to_model(
            source, material=CORE_STEEL, section=Section(area=1e-4, inertia_z=1e-9)
        )

        assert model.elements[0].material is CORE_STEEL
        assert model.elements[0].section.area == pytest.approx(1e-4)

    def test_a_missing_material_is_reported_with_the_remedy(self) -> None:
        with pytest.raises(FormatError, match="no material= fallback"):
            to_model(rod_chain(3, with_tables=False))

    def test_a_missing_section_is_reported_with_the_remedy(self) -> None:
        source = rod_chain(3, values={"t": 0.01})

        with pytest.raises(FormatError, match="no section= fallback"):
            to_model(source)

    def test_a_property_wins_over_the_fallback(self) -> None:
        model = to_model(
            rod_chain(3), material=Material(E=1.0, density=1.0), section=Section(area=1.0)
        )

        assert model.elements[0].material == CORE_STEEL
        assert model.elements[0].section.area == pytest.approx(BAR_VALUES["A"])

    def test_a_dangling_material_reference_falls_back(self) -> None:
        source = rod_chain(3)
        source.materials.clear()

        with pytest.raises(FormatError, match="references material 1"):
            to_model(source)
        assert to_model(source, material=CORE_STEEL).elements[0].material is CORE_STEEL


class TestUnsupportedBlocks:
    def mass_only(self) -> NeutralModel:
        return neutral(
            ElementType.MASS1, UNIT_SQUARE[:1], [[1]], values={"m": 1.0}
        )

    def test_a_block_without_a_formulation_is_rejected(self) -> None:
        with pytest.raises(FormatError, match="no formulation yet"):
            to_model(self.mass_only())

    def test_skip_unsupported_drops_the_block_with_a_warning(self) -> None:
        source = self.mass_only()
        source.elements[ElementType.ROD2] = np.array([[1, 2]], dtype=np.int64)
        source.element_property_ids[ElementType.ROD2] = np.array([7], dtype=np.int64)
        # MASS1 needs a second node for the rod; pad coordinates.
        source.nodes = np.vstack([source.nodes, [[1.0, 0.0, 0.0]]])
        source.node_ids = np.array([1, 2], dtype=np.int64)

        with pytest.warns(UserWarning, match="mass1 \\(1\\)"):
            model = to_model(source, skip_unsupported=True, section=BAR_SECTION)

        assert model.num_nodes == 2
        assert [type(element) for element in model.elements] == [TrussElement]

    def test_tri3_membrane_converts(self) -> None:
        source = neutral(
            ElementType.TRI3, UNIT_SQUARE[:3], [[1, 2, 3]], values={"t": 0.01}
        )
        model = to_model(source)
        assert model.num_elements == 1
        assert type(model.elements[0]).__name__ == "Tri3Element"


class TestMalformedInput:
    def test_a_wrong_connectivity_width_is_rejected(self) -> None:
        source = neutral(ElementType.QUAD4, UNIT_SQUARE, [[1, 2, 3]], values={"t": 0.01})

        with pytest.raises(FormatError, match="4 nodes per element"):
            to_model(source)

    def test_a_one_dimensional_block_is_rejected(self) -> None:
        source = rod_chain(3)
        source.elements[ElementType.ROD2] = np.array([1, 2], dtype=np.int64)

        with pytest.raises(FormatError, match=r"shape \(n_elements, nodes_per_element\)"):
            to_model(source)

    def test_misaligned_property_ids_are_rejected(self) -> None:
        source = rod_chain(4)
        source.element_property_ids[ElementType.ROD2] = np.array([7], dtype=np.int64)

        with pytest.raises(FormatError, match=r"shape \(3,\)"):
            to_model(source)

    def test_misaligned_element_labels_are_rejected(self) -> None:
        source = rod_chain(4, meta={"element_ids": {"rod2": [1, 2]}})

        with pytest.raises(FormatError, match="2 labels for 3 elements"):
            to_model(source)

    def test_connectivity_pointing_at_an_unknown_node_is_rejected(self) -> None:
        source = rod_chain(3)
        source.elements[ElementType.ROD2] = np.array([[1, 2], [2, 99]], dtype=np.int64)

        with pytest.raises(FormatError, match="unknown node id 99"):
            to_model(source)

    def test_a_repeated_node_in_one_element_is_rejected(self) -> None:
        source = rod_chain(3)
        source.elements[ElementType.ROD2] = np.array([[1, 2], [2, 2]], dtype=np.int64)

        with pytest.raises(FormatError, match="repeated nodes"):
            to_model(source)

    def test_an_unusable_dof_signature_is_rejected(self) -> None:
        with pytest.raises(FormatError, match="invalid DOF signature"):
            to_model(rod_chain(3), dofs=("UX", "UX"))


class TestScalarConverters:
    def test_material_conversion_keeps_every_field(self) -> None:
        converted = material_from_neutral(STEEL)

        assert converted == CORE_STEEL

    def test_an_incompressible_material_is_rejected_with_its_id(self) -> None:
        with pytest.raises(FormatError, match="material 4 is not usable"):
            material_from_neutral(NeutralMaterial(id=4, E=1.0, nu=0.5, rho=1.0))

    def test_section_values_default_the_optional_fields_to_zero(self) -> None:
        section = section_from_values({"A": 2.0})

        assert section == Section(area=2.0)

    def test_section_values_are_matched_case_insensitively(self) -> None:
        section = section_from_values({"area": 2.0, "IZ": 3.0})

        assert (section.area, section.inertia_z) == (2.0, 3.0)

    def test_a_property_without_an_area_names_its_keys(self) -> None:
        with pytest.raises(FormatError, match="keys: t"):
            section_from_values({"t": 0.01})


class TestPackageSurface:
    def test_the_io_namespace_exports_the_converter(self) -> None:
        assert neutral_to_model is to_model

    def test_a_meshio_import_round_trips_into_an_analyzable_model(self) -> None:
        meshio = pytest.importorskip("meshio", reason="requires the optional [io] extra")
        from openfemlab.io import from_meshio

        mesh = meshio.Mesh(points=UNIT_CUBE, cells=[("hexahedron", np.arange(8).reshape(1, 8))])

        model = to_model(from_meshio(mesh), material=CORE_STEEL)
        system = assemble_system(model)

        assert model.num_dofs == 24
        assert system.M.sum() == pytest.approx(3.0 * STEEL.rho)
