"""Coverage for the optional meshio ↔ NeutralModel bridge.

The whole module is skipped when the ``[io]`` extra is not installed; the one
behaviour that must hold *without* meshio — a typed error carrying an install
hint — is exercised by monkeypatching the guarded import.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest

meshio = pytest.importorskip("meshio", reason="requires the optional [io] extra")

from openfemlab.core.neutral import ElementType, NeutralModel  # noqa: E402
from openfemlab.exceptions import MissingDependencyError  # noqa: E402
from openfemlab.io import (  # noqa: E402
    FormatError,
    meshio_bridge,
)
from openfemlab.io.meshio_bridge import (  # noqa: E402
    CELL_TYPE_TO_ELEMENT,
    ELEMENT_TO_CELL_TYPE,
    from_meshio,
    read_meshio,
    require_meshio,
    to_meshio,
    write_meshio,
)

_UNIT_SQUARE = np.array(
    [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [1.0, 1.0, 0.0],
        [0.0, 1.0, 0.0],
        [2.0, 0.0, 0.0],
        [2.0, 1.0, 0.0],
    ]
)


def _two_quads() -> Any:
    return meshio.Mesh(
        points=_UNIT_SQUARE,
        cells=[("quad", np.array([[0, 1, 2, 3], [1, 4, 5, 2]]))],
    )


def _unit_cube() -> Any:
    points = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
            [0.0, 1.0, 1.0],
        ]
    )
    return meshio.Mesh(
        points=points,
        cells=[("hexahedron", np.array([[0, 1, 2, 3, 4, 5, 6, 7]]))],
    )


class TestSimpleConversion:
    def test_quad_mesh_becomes_a_neutral_model(self) -> None:
        model = from_meshio(_two_quads())

        assert isinstance(model, NeutralModel)
        assert model.n_nodes == 6
        assert model.n_elements == 2
        np.testing.assert_allclose(model.nodes, _UNIT_SQUARE)
        np.testing.assert_array_equal(model.node_ids, [1, 2, 3, 4, 5, 6])
        assert list(model.elements) == [ElementType.QUAD4]
        np.testing.assert_array_equal(
            model.elements[ElementType.QUAD4], [[1, 2, 3, 4], [2, 5, 6, 3]]
        )

    def test_connectivity_stores_node_ids_not_point_indices(self) -> None:
        mesh = meshio.Mesh(
            points=_UNIT_SQUARE[:4],
            cells=[("quad", np.array([[0, 1, 2, 3]]))],
        )

        model = from_meshio(mesh, node_ids=[101, 102, 103, 104])

        np.testing.assert_array_equal(model.node_ids, [101, 102, 103, 104])
        np.testing.assert_array_equal(
            model.elements[ElementType.QUAD4], [[101, 102, 103, 104]]
        )

    def test_point_data_node_ids_are_honoured(self) -> None:
        mesh = meshio.Mesh(
            points=_UNIT_SQUARE[:4],
            cells=[("quad", np.array([[0, 1, 2, 3]]))],
            point_data={"node_ids": np.array([7, 8, 9, 10])},
        )

        np.testing.assert_array_equal(from_meshio(mesh).node_ids, [7, 8, 9, 10])

    def test_explicit_node_ids_override_point_data(self) -> None:
        mesh = meshio.Mesh(
            points=_UNIT_SQUARE[:4],
            cells=[("quad", np.array([[0, 1, 2, 3]]))],
            point_data={"node_ids": np.array([7, 8, 9, 10])},
        )

        model = from_meshio(mesh, node_ids=[1, 2, 3, 4])

        np.testing.assert_array_equal(model.node_ids, [1, 2, 3, 4])

    def test_hexahedron_mesh_maps_to_hex8(self) -> None:
        model = from_meshio(_unit_cube())

        np.testing.assert_array_equal(
            model.elements[ElementType.HEX8], [[1, 2, 3, 4, 5, 6, 7, 8]]
        )
        assert model.meta["element_ids"] == {"hex8": [1]}

    def test_two_dimensional_points_are_padded_to_three_columns(self) -> None:
        mesh = meshio.Mesh(
            points=np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]),
            cells=[("quad", np.array([[0, 1, 2, 3]]))],
        )

        model = from_meshio(mesh)

        assert model.nodes.shape == (4, 3)
        np.testing.assert_allclose(model.nodes[:, 2], 0.0)

    def test_mixed_blocks_land_in_separate_element_types(self) -> None:
        mesh = meshio.Mesh(
            points=_UNIT_SQUARE,
            cells=[
                ("triangle", np.array([[0, 1, 2]])),
                ("line", np.array([[0, 1]])),
                ("vertex", np.array([[4]])),
            ],
        )

        model = from_meshio(mesh)

        assert set(model.elements) == {
            ElementType.TRI3,
            ElementType.ROD2,
            ElementType.MASS1,
        }
        assert model.meta["element_ids"] == {"tri3": [1], "rod2": [2], "mass1": [3]}

    def test_repeated_blocks_of_one_type_are_concatenated(self) -> None:
        mesh = meshio.Mesh(
            points=_UNIT_SQUARE,
            cells=[
                ("quad", np.array([[0, 1, 2, 3]])),
                ("quad", np.array([[1, 4, 5, 2]])),
            ],
        )

        model = from_meshio(mesh)

        np.testing.assert_array_equal(
            model.elements[ElementType.QUAD4], [[1, 2, 3, 4], [2, 5, 6, 3]]
        )
        assert model.meta["element_ids"] == {"quad4": [1, 2]}

    def test_materials_and_properties_are_empty(self) -> None:
        model = from_meshio(_two_quads())

        assert model.materials == {}
        assert model.properties == {}
        assert model.dof_map is None
        assert model.meta["format"] == "meshio"

    def test_duck_typed_mesh_needs_no_meshio_types(self) -> None:
        class PlainMesh:
            points = _UNIT_SQUARE[:4]
            cells = [("quad", np.array([[0, 1, 2, 3]]))]

        model = from_meshio(PlainMesh())

        np.testing.assert_array_equal(model.elements[ElementType.QUAD4], [[1, 2, 3, 4]])


class TestPropertyAndElementIds:
    def test_property_ids_default_to_one(self) -> None:
        model = from_meshio(_two_quads())

        np.testing.assert_array_equal(
            model.element_property_ids[ElementType.QUAD4], [1, 1]
        )

    def test_default_property_id_is_configurable(self) -> None:
        model = from_meshio(_two_quads(), default_property_id=42)

        np.testing.assert_array_equal(
            model.element_property_ids[ElementType.QUAD4], [42, 42]
        )

    @pytest.mark.parametrize("key", ["property_ids", "gmsh:physical", "medit:ref"])
    def test_cell_data_tags_become_property_ids(self, key: str) -> None:
        mesh = meshio.Mesh(
            points=_UNIT_SQUARE,
            cells=[("quad", np.array([[0, 1, 2, 3], [1, 4, 5, 2]]))],
            cell_data={key: [np.array([3, 4])]},
        )

        model = from_meshio(mesh)

        np.testing.assert_array_equal(model.element_property_ids[ElementType.QUAD4], [3, 4])

    def test_cell_data_element_ids_are_preserved(self) -> None:
        mesh = meshio.Mesh(
            points=_UNIT_SQUARE,
            cells=[("quad", np.array([[0, 1, 2, 3], [1, 4, 5, 2]]))],
            cell_data={"element_ids": [np.array([500, 501])]},
        )

        model = from_meshio(mesh)

        assert model.meta["element_ids"] == {"quad4": [500, 501]}

    def test_generated_element_ids_continue_past_imported_ones(self) -> None:
        mesh = meshio.Mesh(
            points=_UNIT_SQUARE,
            cells=[
                ("quad", np.array([[0, 1, 2, 3]])),
                ("line", np.array([[0, 1]])),
            ],
            cell_data={"element_ids": [np.array([500]), np.array([501])]},
        )

        model = from_meshio(mesh)

        assert model.meta["element_ids"] == {"quad4": [500], "rod2": [501]}


class TestUnsupportedCells:
    def test_unmapped_cell_types_are_skipped_with_a_diagnostic(self) -> None:
        mesh = meshio.Mesh(
            points=_UNIT_SQUARE,
            cells=[
                ("quad", np.array([[0, 1, 2, 3]])),
                ("triangle6", np.array([[0, 1, 2, 3, 4, 5]])),
            ],
        )

        with pytest.warns(UserWarning, match="triangle6"):
            model = from_meshio(mesh)

        assert list(model.elements) == [ElementType.QUAD4]
        assert model.meta["skipped_cell_types"] == {"triangle6": 1}

    def test_fully_supported_mesh_records_no_skips_and_warns_nothing(self) -> None:
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            model = from_meshio(_two_quads())

        assert "skipped_cell_types" not in model.meta


class TestMalformedMeshes:
    def test_out_of_range_connectivity_is_rejected(self) -> None:
        mesh = meshio.Mesh(
            points=_UNIT_SQUARE[:4],
            cells=[("quad", np.array([[0, 1, 2, 9]]))],
        )

        with pytest.raises(FormatError, match="point indices outside"):
            from_meshio(mesh)

    def test_duplicate_node_ids_are_rejected(self) -> None:
        mesh = meshio.Mesh(
            points=_UNIT_SQUARE[:4],
            cells=[("quad", np.array([[0, 1, 2, 3]]))],
        )

        with pytest.raises(FormatError, match="unique"):
            from_meshio(mesh, node_ids=[1, 2, 2, 4])

    def test_node_ids_length_must_match_the_points(self) -> None:
        with pytest.raises(FormatError, match=r"must have shape \(8,\), got \(4,\)"):
            from_meshio(_unit_cube(), node_ids=[1, 2, 3, 4])

    def test_points_must_be_two_dimensional(self) -> None:
        class BadMesh:
            points = np.zeros(4)
            cells: list[tuple[str, np.ndarray]] = []

        with pytest.raises(FormatError, match="n_points"):
            from_meshio(BadMesh())

    def test_cell_blocks_must_be_recognisable(self) -> None:
        class BadMesh:
            points = _UNIT_SQUARE[:4]
            cells = ["quad"]

        with pytest.raises(FormatError, match="CellBlock"):
            from_meshio(BadMesh())

    def test_cell_data_must_cover_every_block(self) -> None:
        # meshio.Mesh validates this itself, so the short cell-data list has to
        # come from a duck-typed mesh to reach the bridge's own check.
        class ShortCellData:
            points = _UNIT_SQUARE
            cells = [
                ("quad", np.array([[0, 1, 2, 3]])),
                ("line", np.array([[0, 1]])),
            ]
            cell_data = {"property_ids": [np.array([3])]}

        with pytest.raises(FormatError, match="no entry for cell block 1"):
            from_meshio(ShortCellData())

    def test_cell_data_length_must_match_the_block(self) -> None:
        class WrongLength:
            points = _UNIT_SQUARE
            cells = [("quad", np.array([[0, 1, 2, 3]]))]
            cell_data = {"property_ids": [np.array([3, 4])]}

        with pytest.raises(FormatError, match=r"must have shape \(1,\)"):
            from_meshio(WrongLength())


class TestExport:
    def test_round_trip_preserves_nodes_blocks_and_ids(self) -> None:
        original = from_meshio(
            meshio.Mesh(
                points=_UNIT_SQUARE,
                cells=[("quad", np.array([[0, 1, 2, 3], [1, 4, 5, 2]]))],
                cell_data={"property_ids": [np.array([3, 4])]},
            ),
            node_ids=[11, 12, 13, 14, 15, 16],
        )

        restored = from_meshio(to_meshio(original))

        np.testing.assert_allclose(restored.nodes, original.nodes)
        np.testing.assert_array_equal(restored.node_ids, original.node_ids)
        assert list(restored.elements) == list(original.elements)
        np.testing.assert_array_equal(
            restored.elements[ElementType.QUAD4], original.elements[ElementType.QUAD4]
        )
        np.testing.assert_array_equal(
            restored.element_property_ids[ElementType.QUAD4],
            original.element_property_ids[ElementType.QUAD4],
        )
        assert restored.meta["element_ids"] == original.meta["element_ids"]

    def test_export_uses_zero_based_point_indices(self) -> None:
        model = from_meshio(_two_quads(), node_ids=[11, 12, 13, 14, 15, 16])

        mesh = to_meshio(model)

        np.testing.assert_array_equal(mesh.cells[0].data, [[0, 1, 2, 3], [1, 4, 5, 2]])
        np.testing.assert_array_equal(mesh.point_data["node_ids"], model.node_ids)

    def test_element_types_without_a_meshio_cell_type_are_rejected(self) -> None:
        model = NeutralModel(
            nodes=_UNIT_SQUARE[:2],
            node_ids=np.array([1, 2]),
            elements={ElementType.BEAM2: np.array([[1, 2]])},
        )

        with pytest.raises(FormatError, match="no meshio cell type"):
            to_meshio(model)

    def test_unknown_node_ids_in_connectivity_are_rejected(self) -> None:
        model = NeutralModel(
            nodes=_UNIT_SQUARE[:2],
            node_ids=np.array([1, 2]),
            elements={ElementType.ROD2: np.array([[1, 77]])},
        )

        with pytest.raises(FormatError, match="unknown node id 77"):
            to_meshio(model)


class TestFileRoundTrip:
    def test_write_then_read_recovers_the_model(self, tmp_path: Path) -> None:
        model = from_meshio(_unit_cube(), node_ids=[10, 20, 30, 40, 50, 60, 70, 80])
        path = tmp_path / "cube.vtu"

        write_meshio(model, path)
        restored = read_meshio(path)

        np.testing.assert_allclose(restored.nodes, model.nodes)
        np.testing.assert_array_equal(restored.node_ids, model.node_ids)
        np.testing.assert_array_equal(
            restored.elements[ElementType.HEX8], model.elements[ElementType.HEX8]
        )
        assert restored.meta["source"] == str(path)
        assert restored.meta["format"] == "meshio"

    def test_reading_a_missing_file_raises_a_format_error(self, tmp_path: Path) -> None:
        with pytest.raises(FormatError, match="cannot read mesh file"):
            read_meshio(tmp_path / "absent.vtu")

    def test_writing_an_unknown_format_raises_a_format_error(self, tmp_path: Path) -> None:
        model = from_meshio(_two_quads())

        with pytest.raises(FormatError, match="cannot write mesh file"):
            write_meshio(model, tmp_path / "quads.not-a-format")


class TestOptionalDependencySeam:
    def test_missing_meshio_raises_a_typed_install_hint(self, monkeypatch) -> None:
        def _refuse(name: str) -> None:
            raise ImportError(f"No module named {name!r}")

        monkeypatch.setattr(meshio_bridge, "import_module", _refuse)

        with pytest.raises(MissingDependencyError, match=r"openfemlab\[io\]"):
            require_meshio()

    def test_missing_dependency_error_is_an_import_error(self) -> None:
        assert issubclass(MissingDependencyError, ImportError)

    def test_conversion_does_not_need_the_optional_package(self, monkeypatch) -> None:
        def _refuse(name: str) -> None:
            raise ImportError(f"No module named {name!r}")

        monkeypatch.setattr(meshio_bridge, "import_module", _refuse)

        class PlainMesh:
            points = _UNIT_SQUARE[:4]
            cells = [("quad", np.array([[0, 1, 2, 3]]))]

        model = from_meshio(PlainMesh())

        assert model.n_elements == 1


class TestMappingTable:
    def test_the_cell_type_table_is_one_to_one(self) -> None:
        assert len(ELEMENT_TO_CELL_TYPE) == len(CELL_TYPE_TO_ELEMENT)
        for cell_type, element_type in CELL_TYPE_TO_ELEMENT.items():
            assert ELEMENT_TO_CELL_TYPE[element_type] == cell_type

    @pytest.mark.parametrize(
        ("cell_type", "element_type"),
        [
            ("vertex", ElementType.MASS1),
            ("line", ElementType.ROD2),
            ("triangle", ElementType.TRI3),
            ("quad", ElementType.QUAD4),
            ("tetra", ElementType.TET4),
            ("hexahedron", ElementType.HEX8),
        ],
    )
    def test_documented_pairs_are_registered(
        self, cell_type: str, element_type: ElementType
    ) -> None:
        assert CELL_TYPE_TO_ELEMENT[cell_type] is element_type

    def test_ambiguous_line_elements_stay_unmapped(self) -> None:
        assert ElementType.BEAM2 not in ELEMENT_TO_CELL_TYPE
        assert ElementType.SPRING2 not in ELEMENT_TO_CELL_TYPE
