"""Round-trip and fixture coverage for the native JSON/YAML IO layer."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from openfemlab.core.dofs import DofMap, DofType
from openfemlab.core.neutral import ElementType
from openfemlab.core.neutral import NeutralMaterial as Material
from openfemlab.core.neutral import NeutralModel as Model
from openfemlab.core.neutral import NeutralProperty as Property
from openfemlab.core.results import ModalResult
from openfemlab.core.results import TestData as ModalTestData
from openfemlab.io import (
    FormatError,
    read,
    read_data,
    read_modal_result,
    read_model,
    read_test_data,
    write_modal_result,
    write_model,
    write_test_data,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize("fixture", sorted(FIXTURES.glob("*.yaml")))
def test_all_repository_yaml_fixtures_are_readable(fixture: Path) -> None:
    document = read_data(fixture)

    assert isinstance(document, dict)
    assert document["name"]


def test_modal_fixture_sections_convert_modes_by_dof_layout() -> None:
    fixture = FIXTURES / "test_modes.yaml"

    analytical = read_modal_result(fixture)
    experimental = read_test_data(fixture)

    np.testing.assert_allclose(analytical.frequencies, [10.0, 20.0, 30.0])
    np.testing.assert_allclose(experimental.frequencies, [10.1, 19.8, 30.6])
    assert analytical.shapes.shape == (4, 3)
    assert experimental.shapes.shape == (3, 3)
    np.testing.assert_array_equal(analytical.dof_map.node_ids, [1, 2, 3, 4])
    np.testing.assert_array_equal(
        analytical.dof_map.dof_types, np.full(4, int(DofType.UX))
    )
    assert analytical.meta["name"] == "synthetic_modal_correlation"
    assert analytical.meta["dof_labels"][1] == "node_2:x"


def _sample_model() -> Model:
    dof_map = DofMap.regular(np.array([10, 20]), (DofType.UX, DofType.UY))
    return Model(
        nodes=np.array([[0.0, 0.0, 0.0], [1.5, 0.0, 0.0]]),
        node_ids=np.array([10, 20]),
        elements={ElementType.SPRING2: np.array([[10, 20]])},
        element_property_ids={ElementType.SPRING2: np.array([7])},
        materials={2: Material(id=2, E=210.0e9, nu=0.3, rho=7850.0, name="steel")},
        properties={
            7: Property(id=7, material_id=2, values={"k": 1250.0}, name="spring")
        },
        dof_map=dof_map,
        meta={"units": "SI", "tags": ["fixture", "round-trip"]},
    )


@pytest.mark.parametrize("extension", [".json", ".yaml", ".yml"])
def test_model_round_trip_preserves_ids_blocks_and_metadata(
    tmp_path: Path, extension: str
) -> None:
    path = tmp_path / f"model{extension}"
    original = _sample_model()

    write_model(original, path)
    restored = read_model(path)

    np.testing.assert_allclose(restored.nodes, original.nodes)
    np.testing.assert_array_equal(restored.node_ids, original.node_ids)
    np.testing.assert_array_equal(
        restored.elements[ElementType.SPRING2],
        original.elements[ElementType.SPRING2],
    )
    np.testing.assert_array_equal(
        restored.element_property_ids[ElementType.SPRING2],
        original.element_property_ids[ElementType.SPRING2],
    )
    assert restored.materials == original.materials
    assert restored.properties == original.properties
    assert restored.meta == original.meta
    np.testing.assert_array_equal(restored.dof_map.node_ids, original.dof_map.node_ids)
    np.testing.assert_array_equal(restored.dof_map.dof_types, original.dof_map.dof_types)
    assert isinstance(read(path), Model)


@pytest.mark.parametrize("extension", [".json", ".yaml"])
def test_complex_modal_result_round_trip(extension: str, tmp_path: Path) -> None:
    path = tmp_path / f"modes{extension}"
    dof_map = DofMap([101, 102], [DofType.UX, DofType.UY])
    original = ModalResult(
        frequencies=np.array([5.25, 14.0]),
        shapes=np.array([[1.0 + 0.25j, 0.0], [0.5, -2.0j]]),
        dof_map=dof_map,
        meta={"solver": "external", "normalization": "arbitrary"},
    )

    write_modal_result(original, path)
    restored = read_modal_result(path)

    np.testing.assert_allclose(restored.frequencies, original.frequencies)
    np.testing.assert_allclose(restored.shapes, original.shapes)
    np.testing.assert_array_equal(restored.dof_map.node_ids, dof_map.node_ids)
    np.testing.assert_array_equal(restored.dof_map.dof_types, dof_map.dof_types)
    assert restored.meta == original.meta


@pytest.mark.parametrize("extension", [".json", ".yaml"])
def test_test_data_round_trip_preserves_optional_arrays(
    extension: str, tmp_path: Path
) -> None:
    path = tmp_path / f"test-data{extension}"
    original = ModalTestData(
        frequencies=np.array([8.0, 12.5]),
        shapes=np.array([[1.0, 0.2], [0.5, -1.0], [0.25, 0.8]]),
        dof_map=DofMap([1, 2, 3], [DofType.UX, DofType.UY, DofType.UZ]),
        damping=np.array([0.01, 0.015]),
        geometry=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]]),
        meta={"campaign": "hammer-01"},
    )

    write_test_data(original, path)
    restored = read_test_data(path)

    np.testing.assert_allclose(restored.frequencies, original.frequencies)
    np.testing.assert_allclose(restored.shapes, original.shapes)
    np.testing.assert_allclose(restored.damping, original.damping)
    np.testing.assert_allclose(restored.geometry, original.geometry)
    assert restored.meta == original.meta


def test_unknown_extension_requires_an_explicit_supported_format(tmp_path: Path) -> None:
    path = tmp_path / "model.txt"

    with pytest.raises(FormatError, match="supported format"):
        write_model(_sample_model(), path)


def test_model_reader_rejects_unknown_connectivity_node(tmp_path: Path) -> None:
    path = tmp_path / "invalid.yaml"
    path.write_text(
        """
object_type: model
node_ids: [1]
nodes: [[0, 0, 0]]
elements:
  spring2: [[1, 99]]
""",
        encoding="utf-8",
    )

    with pytest.raises(FormatError, match="unknown node ids.*99"):
        read_model(path)
