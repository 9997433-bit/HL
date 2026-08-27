"""Coverage for the UNV 2411/2412 geometry reader.

The committed fixture ``fixtures/unv_plate_model.unv`` is a complete small UNV
file — units header, nodes, elements and a mode shape — read from disk the way
a user would.  Everything else is synthesized here so that a case is readable
next to the assertion it drives.
"""

from __future__ import annotations

import warnings
from collections.abc import Iterable, Iterator, Mapping, Sequence
from io import BytesIO, StringIO
from pathlib import Path

import numpy as np
import pytest

from openfemlab.core.elements import Hex8Element
from openfemlab.core.model import DOF, Material, Section
from openfemlab.core.neutral import ElementType
from openfemlab.io import FormatError, neutral_to_model, read_uff_modes, read_unv
from openfemlab.io.unv import (
    BEAM_FE_DESCRIPTORS,
    FE_DESCRIPTOR_TO_ELEMENT,
    UNV_ELEMENT_DATASET,
    UNV_NODE_DATASET,
)
from openfemlab.solver.modal import ModalSolver

FIXTURES = Path(__file__).parent / "fixtures"
PLATE = FIXTURES / "unv_plate_model.unv"

STEEL = Material(E=2.1e11, density=7850.0, nu=0.3)


# --------------------------------------------------------------- synthesis


def block(number: int, records: Iterable[str]) -> str:
    """Wrap ``records`` in the ``-1`` delimiters of one UNV dataset."""

    return "\n".join(["    -1", f"{number:6d}", *records, "    -1", ""])


def node_records(
    nodes: Mapping[int, Sequence[float]], *, system: int = 1
) -> Iterator[str]:
    for label, point in nodes.items():
        yield f"{label:10d}{system:10d}{system:10d}{11:10d}"
        yield "".join(f"{value:25.16E}".replace("E", "D") for value in point)


def element_records(
    label: int,
    descriptor: int,
    nodes: Sequence[int],
    *,
    property_id: int = 1,
    material_id: int = 1,
    orientation: int = 0,
    declared_nodes: int | None = None,
) -> Iterator[str]:
    count = len(nodes) if declared_nodes is None else declared_nodes
    yield f"{label:10d}{descriptor:10d}{property_id:10d}{material_id:10d}{7:10d}{count:10d}"
    if descriptor in BEAM_FE_DESCRIPTORS:
        yield f"{orientation:10d}{0:10d}{0:10d}"
    for start in range(0, len(nodes), 8):
        yield "".join(f"{node:10d}" for node in nodes[start : start + 8])


def unv(nodes: Mapping[int, Sequence[float]], *element_blocks: Iterable[str]) -> str:
    """A file with one 2411 dataset and one 2412 dataset."""

    elements = [record for records in element_blocks for record in records]
    text = block(UNV_NODE_DATASET, node_records(nodes))
    if elements:
        text += block(UNV_ELEMENT_DATASET, elements)
    return text


LINE_NODES = {1: (0.0, 0.0, 0.0), 2: (1.0, 0.0, 0.0), 3: (2.0, 0.0, 0.0)}

CUBE_NODES = {
    index + 1: point
    for index, point in enumerate(
        [
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (1.0, 1.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
            (1.0, 0.0, 1.0),
            (1.0, 1.0, 1.0),
            (0.0, 1.0, 1.0),
        ]
    )
}


# ------------------------------------------------------- the plate fixture


class TestPlateFixture:
    def test_nodes_carry_their_labels_and_coordinates(self) -> None:
        model = read_unv(PLATE)

        assert model.n_nodes == 6
        np.testing.assert_array_equal(model.node_ids, [1, 2, 3, 4, 5, 6])
        np.testing.assert_allclose(
            model.nodes,
            [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [2.0, 0.0, 0.0],
                [0.0, 0.5, 0.0],
                [1.0, 0.5, 0.0],
                [2.0, 0.5, 0.0],
            ],
        )

    def test_the_three_element_families_land_in_their_blocks(self) -> None:
        model = read_unv(PLATE)

        assert model.n_elements == 4
        assert set(model.elements) == {
            ElementType.QUAD4,
            ElementType.ROD2,
            ElementType.MASS1,
        }
        np.testing.assert_array_equal(
            model.elements[ElementType.QUAD4], [[1, 2, 5, 4], [2, 3, 6, 5]]
        )
        np.testing.assert_array_equal(model.elements[ElementType.ROD2], [[3, 6]])
        np.testing.assert_array_equal(model.elements[ElementType.MASS1], [[6]])

    def test_property_material_and_element_labels_survive(self) -> None:
        model = read_unv(PLATE)

        np.testing.assert_array_equal(
            model.element_property_ids[ElementType.QUAD4], [1, 1]
        )
        np.testing.assert_array_equal(model.element_property_ids[ElementType.ROD2], [2])
        assert model.meta["element_ids"] == {"quad4": [1, 2], "rod2": [10], "mass1": [20]}
        assert model.meta["element_material_ids"] == {
            "quad4": [1, 1],
            "rod2": [1],
            "mass1": [0],
        }

    def test_the_beam_orientation_node_of_the_rod_is_kept(self) -> None:
        assert read_unv(PLATE).meta["beam_orientation_nodes"] == {10: 1}

    def test_provenance_and_coordinate_systems_are_recorded(self) -> None:
        model = read_unv(PLATE)

        assert model.meta["format"] == "unv"
        assert model.meta["source"] == str(PLATE)
        assert model.meta["export_coordinate_systems"] == [1]
        assert "skipped_fe_descriptors" not in model.meta

    def test_the_mesh_carries_no_material_or_property_table(self) -> None:
        model = read_unv(PLATE)

        assert model.materials == {}
        assert model.properties == {}

    def test_the_same_file_yields_its_mode_through_the_uff_reader(self) -> None:
        model = read_unv(PLATE)
        modes = read_uff_modes(PLATE)

        assert len(modes) == 1
        assert modes[0].frequency_hz == pytest.approx(12.5)
        np.testing.assert_array_equal(modes[0].node_ids, model.node_ids)
        np.testing.assert_allclose(modes[0].mode_shape[:, 2], [0.0, 0.5, 1.0] * 2)

    def test_reading_the_fixture_warns_about_nothing(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            read_unv(PLATE)


# ------------------------------------------------------------- 2411 nodes


class TestNodeDataset:
    def test_a_stream_has_no_source_provenance(self) -> None:
        model = read_unv(StringIO(unv(LINE_NODES)))

        assert model.n_nodes == 3
        assert "source" not in model.meta
        assert model.elements == {}

    def test_coordinates_use_the_fortran_d_exponent(self) -> None:
        text = block(
            UNV_NODE_DATASET,
            [
                f"{1:10d}{1:10d}{1:10d}{11:10d}",
                "   1.2500000000000000D-03  -4.0000000000000000D+00"
                "   6.2500000000000000D+02",
            ],
        )

        np.testing.assert_allclose(read_unv(StringIO(text)).nodes, [[1.25e-3, -4.0, 625.0]])

    def test_several_node_datasets_are_merged_in_file_order(self) -> None:
        text = block(UNV_NODE_DATASET, node_records({1: (0.0, 0.0, 0.0)})) + block(
            UNV_NODE_DATASET, node_records({7: (1.0, 0.0, 0.0)})
        )

        np.testing.assert_array_equal(read_unv(StringIO(text)).node_ids, [1, 7])

    def test_mixed_export_coordinate_systems_warn_and_are_recorded(self) -> None:
        text = block(UNV_NODE_DATASET, node_records({1: (0.0, 0.0, 0.0)})) + block(
            UNV_NODE_DATASET, node_records({2: (1.0, 0.0, 0.0)}, system=4)
        )

        with pytest.warns(UserWarning, match="more than one export coordinate system"):
            model = read_unv(StringIO(text))

        assert model.meta["export_coordinate_systems"] == [1, 4]

    def test_a_duplicate_node_label_is_rejected(self) -> None:
        text = block(
            UNV_NODE_DATASET,
            [*node_records({1: (0.0, 0.0, 0.0)}), *node_records({1: (1.0, 0.0, 0.0)})],
        )

        with pytest.raises(FormatError, match="duplicate node label 1"):
            read_unv(StringIO(text))

    def test_a_non_positive_node_label_is_rejected(self) -> None:
        text = block(
            UNV_NODE_DATASET,
            [f"{0:10d}{1:10d}{1:10d}{11:10d}", *list(node_records({1: (0.0, 0.0, 0.0)}))[1:]],
        )

        with pytest.raises(FormatError, match="node label must be positive"):
            read_unv(StringIO(text))

    def test_a_truncated_coordinate_record_is_rejected(self) -> None:
        text = block(
            UNV_NODE_DATASET,
            [f"{1:10d}{1:10d}{1:10d}{11:10d}", "   0.0000000000000000D+00"],
        )

        with pytest.raises(FormatError, match="coordinates of node 1 requires 3"):
            read_unv(StringIO(text))

    def test_a_missing_coordinate_record_is_rejected(self) -> None:
        text = block(UNV_NODE_DATASET, [f"{1:10d}{1:10d}{1:10d}{11:10d}"])

        with pytest.raises(FormatError, match="file ends where the coordinates of node 1"):
            read_unv(StringIO(text))

    def test_a_non_finite_coordinate_is_rejected(self) -> None:
        text = block(
            UNV_NODE_DATASET,
            [
                f"{1:10d}{1:10d}{1:10d}{11:10d}",
                "   1.0000000000000000D+400   0.0000000000000000D+00"
                "   0.0000000000000000D+00",
            ],
        )

        with pytest.raises(FormatError, match="node 1 has non-finite coordinates"):
            read_unv(StringIO(text))


# ---------------------------------------------------------- 2412 elements


class TestElementDataset:
    @pytest.mark.parametrize(
        ("descriptor", "element_type", "nodes"),
        [
            (11, ElementType.ROD2, (1, 2)),
            (21, ElementType.BEAM2, (1, 2)),
            (22, ElementType.BEAM2, (1, 2)),
            (41, ElementType.TRI3, (1, 2, 3)),
            (91, ElementType.TRI3, (1, 2, 3)),
            (44, ElementType.QUAD4, (1, 2, 3, 4)),
            (94, ElementType.QUAD4, (1, 2, 3, 4)),
            (111, ElementType.TET4, (1, 2, 3, 5)),
            (115, ElementType.HEX8, (1, 2, 3, 4, 5, 6, 7, 8)),
            (136, ElementType.SPRING2, (1, 2)),
            (137, ElementType.SPRING2, (1, 2)),
            (161, ElementType.MASS1, (1,)),
        ],
    )
    def test_every_mapped_descriptor_lands_in_its_block(
        self, descriptor: int, element_type: ElementType, nodes: tuple[int, ...]
    ) -> None:
        text = unv(CUBE_NODES, element_records(3, descriptor, nodes))

        model = read_unv(StringIO(text))

        assert set(model.elements) == {element_type}
        np.testing.assert_array_equal(model.elements[element_type], [list(nodes)])
        assert model.meta["element_ids"] == {element_type.value: [3]}

    def test_the_descriptor_table_agrees_with_the_public_mapping(self) -> None:
        assert FE_DESCRIPTOR_TO_ELEMENT[115] is ElementType.HEX8
        assert set(FE_DESCRIPTOR_TO_ELEMENT.values()) == set(ElementType)

    def test_connectivity_wrapping_across_lines_is_reassembled(self) -> None:
        records = [
            f"{5:10d}{115:10d}{1:10d}{1:10d}{7:10d}{8:10d}",
            "".join(f"{node:10d}" for node in (1, 2, 3, 4, 5)),
            "".join(f"{node:10d}" for node in (6, 7, 8)),
        ]
        text = block(UNV_NODE_DATASET, node_records(CUBE_NODES)) + block(
            UNV_ELEMENT_DATASET, records
        )

        model = read_unv(StringIO(text))

        np.testing.assert_array_equal(
            model.elements[ElementType.HEX8], [[1, 2, 3, 4, 5, 6, 7, 8]]
        )

    def test_elements_of_one_type_keep_their_file_order(self) -> None:
        text = unv(
            CUBE_NODES,
            element_records(30, 44, (1, 2, 3, 4)),
            element_records(10, 44, (5, 6, 7, 8), property_id=9),
        )

        model = read_unv(StringIO(text))

        np.testing.assert_array_equal(
            model.elements[ElementType.QUAD4], [[1, 2, 3, 4], [5, 6, 7, 8]]
        )
        assert model.meta["element_ids"]["quad4"] == [30, 10]
        np.testing.assert_array_equal(
            model.element_property_ids[ElementType.QUAD4], [1, 9]
        )

    def test_an_unmapped_descriptor_is_skipped_with_a_warning(self) -> None:
        text = unv(
            CUBE_NODES,
            element_records(1, 44, (1, 2, 3, 4)),
            element_records(2, 45, (1, 2, 3, 4, 5, 6, 7, 8)),
            element_records(3, 24, (1, 2, 3)),
        )

        with pytest.warns(UserWarning, match="unsupported FE descriptor ids: 24 \\(1\\), 45"):
            model = read_unv(StringIO(text))

        assert set(model.elements) == {ElementType.QUAD4}
        assert model.meta["skipped_fe_descriptors"] == {24: 1, 45: 1}

    def test_an_unmapped_beam_descriptor_keeps_the_record_scan_in_step(self) -> None:
        text = unv(
            CUBE_NODES,
            element_records(1, 23, (1, 2, 3)),
            element_records(2, 44, (1, 2, 3, 4)),
        )

        with pytest.warns(UserWarning, match="descriptor ids: 23"):
            model = read_unv(StringIO(text))

        np.testing.assert_array_equal(model.elements[ElementType.QUAD4], [[1, 2, 3, 4]])

    def test_a_node_count_that_contradicts_the_descriptor_is_rejected(self) -> None:
        text = unv(CUBE_NODES, element_records(4, 44, (1, 2, 3), declared_nodes=3))

        with pytest.raises(FormatError, match="element 4 maps to quad4 but declares 3"):
            read_unv(StringIO(text))

    def test_a_repeated_node_within_an_element_is_rejected(self) -> None:
        text = unv(CUBE_NODES, element_records(4, 44, (1, 2, 2, 4)))

        with pytest.raises(FormatError, match="element 4 repeats a node label"):
            read_unv(StringIO(text))

    def test_a_duplicate_element_label_is_rejected(self) -> None:
        text = unv(
            CUBE_NODES,
            element_records(7, 44, (1, 2, 3, 4)),
            element_records(7, 111, (1, 2, 3, 5)),
        )

        with pytest.raises(FormatError, match="duplicate element label 7"):
            read_unv(StringIO(text))

    def test_connectivity_into_an_undefined_node_is_rejected(self) -> None:
        text = unv(LINE_NODES, element_records(1, 44, (1, 2, 3, 9)))

        with pytest.raises(FormatError, match="unknown node labels: 9"):
            read_unv(StringIO(text))

    def test_a_truncated_element_header_is_rejected(self) -> None:
        text = block(UNV_NODE_DATASET, node_records(LINE_NODES)) + block(
            UNV_ELEMENT_DATASET, [f"{1:10d}{11:10d}{1:10d}"]
        )

        with pytest.raises(FormatError, match="an element record requires 6"):
            read_unv(StringIO(text))

    def test_a_truncated_connectivity_record_is_rejected(self) -> None:
        text = unv(
            CUBE_NODES, element_records(4, 115, (1, 2, 3, 4, 5, 6, 7), declared_nodes=8)
        )

        with pytest.raises(
            FormatError, match="the connectivity of element 4 requires 8 numeric fields"
        ):
            read_unv(StringIO(text))

    def test_a_zero_node_count_is_rejected(self) -> None:
        text = block(UNV_NODE_DATASET, node_records(LINE_NODES)) + block(
            UNV_ELEMENT_DATASET, [f"{1:10d}{44:10d}{1:10d}{1:10d}{7:10d}{0:10d}"]
        )

        with pytest.raises(FormatError, match="element 1 declares 0 nodes"):
            read_unv(StringIO(text))

    def test_the_dataset_number_is_named_in_the_error(self) -> None:
        text = unv(CUBE_NODES, element_records(4, 44, (1, 2, 2, 4)))

        with pytest.raises(FormatError, match=f"invalid UNV dataset {UNV_ELEMENT_DATASET}"):
            read_unv(StringIO(text))


# ------------------------------------------------------------- containers


class TestContainer:
    def test_a_file_without_a_node_dataset_is_not_a_mesh(self) -> None:
        with pytest.raises(FormatError, match="no dataset 2411"):
            read_unv(StringIO(block(58, ["not a mesh"])))

    def test_an_unterminated_node_dataset_is_rejected(self) -> None:
        text = "    -1\n  2411\n" + "\n".join(node_records({1: (0.0, 0.0, 0.0)})) + "\n"

        with pytest.raises(FormatError, match="no closing -1 delimiter"):
            read_unv(StringIO(text))

    def test_unknown_datasets_between_the_geometry_are_skipped(self) -> None:
        text = (
            block(151, ["model header", "-with a dash"])
            + block(UNV_NODE_DATASET, node_records(LINE_NODES))
            + block(2420, ["coordinate systems this reader does not apply"])
            + block(UNV_ELEMENT_DATASET, element_records(1, 11, (1, 2)))
        )

        model = read_unv(StringIO(text))

        assert model.n_nodes == 3
        np.testing.assert_array_equal(model.elements[ElementType.ROD2], [[1, 2]])

    def test_a_missing_file_is_reported_as_a_format_error(self, tmp_path: Path) -> None:
        with pytest.raises(FormatError, match="cannot read UNV file"):
            read_unv(tmp_path / "absent.unv")

    def test_a_binary_stream_is_rejected(self) -> None:
        with pytest.raises(FormatError, match="requires an ASCII text stream"):
            read_unv(BytesIO(b"    -1\n  2411\n"))

    def test_a_path_round_trips_through_the_filesystem(self, tmp_path: Path) -> None:
        path = tmp_path / "bar.unv"
        path.write_text(unv(LINE_NODES, element_records(1, 11, (1, 2))), encoding="utf-8")

        model = read_unv(path)

        assert model.meta["source"] == str(path)
        assert model.n_elements == 1


# ------------------------------------------------------------ re-analysis


class TestReanalysis:
    def test_an_imported_rod_chain_solves_through_the_modal_pipeline(self) -> None:
        length, count = 2.0, 16
        nodes = {
            index + 1: (length * index / count, 0.0, 0.0) for index in range(count + 1)
        }
        elements = [
            record
            for index in range(count)
            for record in element_records(index + 1, 11, (index + 1, index + 2))
        ]
        neutral = read_unv(StringIO(unv(nodes, elements)))

        model = neutral_to_model(
            neutral,
            dofs=(DOF.UX,),
            material=STEEL,
            section=Section(area=1e-4),
        )
        model.fix(1, (DOF.UX,))
        first = ModalSolver(model).solve(num_modes=1).frequencies[0]

        wave_speed = np.sqrt(STEEL.E / STEEL.density)
        assert first == pytest.approx(wave_speed / (4.0 * length), rel=5e-3)

    def test_an_imported_brick_keeps_the_hexahedron_node_order(self) -> None:
        neutral = read_unv(
            StringIO(unv(CUBE_NODES, element_records(1, 115, tuple(range(1, 9)))))
        )

        model = neutral_to_model(neutral, material=STEEL)

        assert model.num_elements == 1
        element = model.elements[0]
        assert isinstance(element, Hex8Element)
        assert element.node_ids == tuple(range(1, 9))
        assert element.volume(np.asarray([CUBE_NODES[node] for node in element.node_ids])) == (
            pytest.approx(1.0)
        )
