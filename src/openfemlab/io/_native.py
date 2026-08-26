"""Native, schema-versioned serialization of OpenFEMLab data contracts."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from os import PathLike
from typing import Any, TextIO

import numpy as np

from openfemlab.core.dofs import DofMap, DofType
from openfemlab.core.neutral import (
    ElementType,
    NeutralMaterial,
    NeutralModel,
    NeutralProperty,
)
from openfemlab.core.results import ModalResult, TestData

from ._common import (
    FormatError,
    decode_array,
    encode_array,
    read_data,
    require_mapping,
    write_data,
)

SCHEMA_VERSION = "1.0"
_HEADER = {"format": "openfemlab", "schema_version": SCHEMA_VERSION}
_DOF_ALIASES = {
    "X": DofType.UX,
    "Y": DofType.UY,
    "Z": DofType.UZ,
    "UX": DofType.UX,
    "UY": DofType.UY,
    "UZ": DofType.UZ,
    "RX": DofType.RX,
    "RY": DofType.RY,
    "RZ": DofType.RZ,
    "ROTX": DofType.RX,
    "ROTY": DofType.RY,
    "ROTZ": DofType.RZ,
}
_NODES_PER_ELEMENT = {
    ElementType.ROD2: 2,
    ElementType.BEAM2: 2,
    ElementType.TRI3: 3,
    ElementType.QUAD4: 4,
    ElementType.TET4: 4,
    ElementType.HEX8: 8,
    ElementType.MASS1: 1,
    ElementType.SPRING2: 2,
}


def dof_map_to_dict(dof_map: DofMap) -> dict[str, Any]:
    """Convert a :class:`DofMap` to its stable native representation."""

    return {
        "node_ids": dof_map.node_ids.tolist(),
        "dof_types": [DofType(int(value)).name for value in dof_map.dof_types],
    }


def dof_map_from_dict(value: Any) -> DofMap:
    """Construct a :class:`DofMap` from names, integer codes, or DOF labels."""

    data = require_mapping(value, "dof_map")
    if "labels" in data and "node_ids" not in data:
        return dof_map_from_labels(data["labels"])
    try:
        node_ids = np.asarray(data["node_ids"], dtype=np.int64)
        raw_types = data["dof_types"]
    except KeyError as exc:
        raise FormatError(f"dof_map is missing required field {exc.args[0]!r}") from exc
    dof_types = np.asarray([_parse_dof_type(item) for item in raw_types], dtype=np.int64)
    try:
        return DofMap(node_ids, dof_types)
    except ValueError as exc:
        raise FormatError(f"invalid dof_map: {exc}") from exc


def dof_map_from_labels(labels: Sequence[Any]) -> DofMap:
    """Parse labels such as ``node_12:x`` or ``sensor-3:RZ``.

    ``DofMap`` uses integer node IDs.  Numeric suffixes are retained when they
    are unique; otherwise stable 1-based IDs are assigned to distinct node
    labels in encounter order.
    """

    if isinstance(labels, (str, bytes)) or not isinstance(labels, Sequence):
        raise FormatError("dof_labels must be a sequence")
    node_labels: list[str] = []
    dof_types: list[DofType] = []
    for raw_label in labels:
        label = str(raw_label)
        if ":" not in label:
            raise FormatError(f"invalid DOF label {label!r}; expected '<node>:<dof>'")
        node_label, dof_label = label.rsplit(":", 1)
        if not node_label:
            raise FormatError(f"invalid DOF label {label!r}; node label is empty")
        node_labels.append(node_label)
        dof_types.append(_parse_dof_type(dof_label))

    unique_labels = list(dict.fromkeys(node_labels))
    suffixes: dict[str, int] = {}
    for node_label in unique_labels:
        match = re.search(r"(-?\d+)$", node_label)
        if match is not None:
            suffixes[node_label] = int(match.group(1))
    if len(suffixes) == len(unique_labels) and len(set(suffixes.values())) == len(unique_labels):
        node_lookup = suffixes
    else:
        node_lookup = {label: index for index, label in enumerate(unique_labels, start=1)}
    try:
        return DofMap(
            [node_lookup[label] for label in node_labels],
            [int(dof_type) for dof_type in dof_types],
        )
    except ValueError as exc:
        raise FormatError(f"invalid dof_labels: {exc}") from exc


def model_to_dict(model: NeutralModel) -> dict[str, Any]:
    """Return a JSON/YAML-safe, schema-versioned model mapping."""

    if not isinstance(model, NeutralModel):
        raise TypeError(f"expected NeutralModel, got {type(model).__name__}")
    document: dict[str, Any] = {
        **_HEADER,
        "object_type": "model",
        "node_ids": model.node_ids.tolist(),
        "nodes": encode_array(model.nodes),
        "elements": {
            element_type.value: np.asarray(connectivity, dtype=np.int64).tolist()
            for element_type, connectivity in model.elements.items()
        },
        "element_property_ids": {
            element_type.value: np.asarray(property_ids, dtype=np.int64).tolist()
            for element_type, property_ids in model.element_property_ids.items()
        },
        "materials": [
            {
                "id": material.id,
                "E": material.E,
                "nu": material.nu,
                "rho": material.rho,
                "name": material.name,
            }
            for _, material in sorted(model.materials.items())
        ],
        "properties": [
            {
                "id": prop.id,
                "material_id": prop.material_id,
                "values": prop.values,
                "name": prop.name,
            }
            for _, prop in sorted(model.properties.items())
        ],
        "meta": model.meta,
    }
    if model.dof_map is not None:
        document["dof_map"] = dof_map_to_dict(model.dof_map)
    return document


def model_from_dict(value: Any) -> NeutralModel:
    """Construct and validate a neutral :class:`Model` from a mapping."""

    root = require_mapping(value)
    data = _unwrap(root, "model")
    node_ids, nodes = _read_nodes(data)
    elements, property_ids = _read_elements(data)
    materials = _read_materials(data.get("materials", []))
    properties = _read_properties(data.get("properties", []))
    dof_map = dof_map_from_dict(data["dof_map"]) if data.get("dof_map") is not None else None
    meta = dict(require_mapping(data.get("meta", {}), "meta"))
    _validate_model_parts(
        node_ids,
        nodes,
        elements,
        property_ids,
        materials,
        properties,
        dof_map,
    )
    try:
        return NeutralModel(
            nodes=nodes,
            node_ids=node_ids,
            elements=elements,
            element_property_ids=property_ids,
            materials=materials,
            properties=properties,
            dof_map=dof_map,
            meta=meta,
        )
    except (TypeError, ValueError) as exc:
        raise FormatError(f"invalid model: {exc}") from exc


def read_model(source: str | PathLike[str] | TextIO, *, format: str | None = None) -> NeutralModel:
    """Read a neutral model from JSON or YAML."""

    return model_from_dict(read_data(source, format=format))


def write_model(
    model: NeutralModel,
    destination: str | PathLike[str] | TextIO,
    *,
    format: str | None = None,
) -> None:
    """Write a neutral model to JSON or YAML."""

    write_data(model_to_dict(model), destination, format=format)


def modal_result_to_dict(result: ModalResult) -> dict[str, Any]:
    """Return a native mapping for an analytical modal result."""

    if not isinstance(result, ModalResult):
        raise TypeError(f"expected ModalResult, got {type(result).__name__}")
    return {
        **_HEADER,
        "object_type": "modal_result",
        "frequencies_hz": result.frequencies.tolist(),
        "mode_shapes": encode_array(result.shapes),
        "mode_shape_layout": "dofs_by_mode",
        "dof_map": dof_map_to_dict(result.dof_map),
        "meta": result.meta,
    }


def modal_result_from_dict(value: Any, *, section: str | None = None) -> ModalResult:
    """Construct a modal result from native data or a repository modal fixture.

    Fixture mode shapes stored as ``modes_by_dof`` are transposed into the core
    contract's ``(ndof, nmodes)`` layout.
    """

    root = require_mapping(value)
    data = _select_modal_payload(root, section, default_section="analytical")
    frequencies = _read_frequencies(data, root)
    shapes = _read_mode_shapes(data, root)
    dof_map, labels = _read_result_dof_map(data, root)
    meta = _result_meta(root, data, labels)
    try:
        return ModalResult(
            frequencies=frequencies,
            shapes=shapes,
            dof_map=dof_map,
            meta=meta,
        )
    except ValueError as exc:
        raise FormatError(f"invalid modal result: {exc}") from exc


def read_modal_result(
    source: str | PathLike[str] | TextIO,
    *,
    format: str | None = None,
    section: str | None = None,
) -> ModalResult:
    """Read analytical modal data from JSON/YAML.

    ``section`` can select fixture sections such as ``"analytical"`` or
    ``"expected"``.
    """

    return modal_result_from_dict(read_data(source, format=format), section=section)


def write_modal_result(
    result: ModalResult,
    destination: str | PathLike[str] | TextIO,
    *,
    format: str | None = None,
) -> None:
    """Write analytical modal data to JSON or YAML."""

    write_data(modal_result_to_dict(result), destination, format=format)


def test_data_to_dict(test_data: TestData) -> dict[str, Any]:
    """Return a native mapping for experimental modal test data."""

    if not isinstance(test_data, TestData):
        raise TypeError(f"expected TestData, got {type(test_data).__name__}")
    document: dict[str, Any] = {
        **_HEADER,
        "object_type": "test_data",
        "frequencies_hz": test_data.frequencies.tolist(),
        "mode_shapes": encode_array(test_data.shapes),
        "mode_shape_layout": "dofs_by_mode",
        "dof_map": dof_map_to_dict(test_data.dof_map),
        "meta": test_data.meta,
    }
    if test_data.damping is not None:
        document["damping"] = np.asarray(test_data.damping, dtype=np.float64).tolist()
    if test_data.geometry is not None:
        document["geometry"] = encode_array(test_data.geometry)
    return document


def test_data_from_dict(value: Any, *, section: str | None = None) -> TestData:
    """Construct test data from native data or an ``experimental`` fixture section."""

    root = require_mapping(value)
    data = _select_modal_payload(root, section, default_section="experimental")
    frequencies = _read_frequencies(data, root)
    shapes = _read_mode_shapes(data, root)
    dof_map, labels = _read_result_dof_map(data, root)
    raw_damping = data.get("damping", data.get("damping_ratios"))
    damping = (
        None
        if raw_damping is None
        else decode_array(raw_damping, dtype=np.float64, name="damping")
    )
    geometry = (
        None
        if data.get("geometry") is None
        else decode_array(data["geometry"], dtype=np.float64, name="geometry")
    )
    if damping is not None and damping.shape != frequencies.shape:
        raise FormatError(
            f"damping must have shape {frequencies.shape}, got {damping.shape}"
        )
    if geometry is not None and (geometry.ndim != 2 or geometry.shape[1] != 3):
        raise FormatError(f"geometry must have shape (n, 3), got {geometry.shape}")
    meta = _result_meta(root, data, labels)
    try:
        return TestData(
            frequencies=frequencies,
            shapes=shapes,
            dof_map=dof_map,
            damping=damping,
            geometry=geometry,
            meta=meta,
        )
    except ValueError as exc:
        raise FormatError(f"invalid test data: {exc}") from exc


def read_test_data(
    source: str | PathLike[str] | TextIO,
    *,
    format: str | None = None,
    section: str | None = None,
) -> TestData:
    """Read experimental modal test data from JSON/YAML."""

    return test_data_from_dict(read_data(source, format=format), section=section)


def write_test_data(
    test_data: TestData,
    destination: str | PathLike[str] | TextIO,
    *,
    format: str | None = None,
) -> None:
    """Write experimental modal test data to JSON or YAML."""

    write_data(test_data_to_dict(test_data), destination, format=format)


def read(
    source: str | PathLike[str] | TextIO,
    *,
    format: str | None = None,
) -> NeutralModel | ModalResult | TestData | Any:
    """Read a native object, or return a plain mapping for an untyped fixture."""

    value = read_data(source, format=format)
    if not isinstance(value, Mapping):
        return value
    object_type = str(value.get("object_type", value.get("type", ""))).lower()
    if object_type == "model":
        return model_from_dict(value)
    if object_type in {"modal", "modal_result"}:
        return modal_result_from_dict(value)
    if object_type in {"test", "test_data"}:
        return test_data_from_dict(value)
    return value


def write(
    value: NeutralModel | ModalResult | TestData | Any,
    destination: str | PathLike[str] | TextIO,
    *,
    format: str | None = None,
) -> None:
    """Write a supported core object or an ordinary JSON-compatible value."""

    if isinstance(value, NeutralModel):
        document = model_to_dict(value)
    elif isinstance(value, ModalResult):
        document = modal_result_to_dict(value)
    elif isinstance(value, TestData):
        document = test_data_to_dict(value)
    else:
        document = value
    write_data(document, destination, format=format)


def _parse_dof_type(value: Any) -> DofType:
    if isinstance(value, str):
        normalized = value.strip().upper().replace("_", "")
        if normalized in _DOF_ALIASES:
            return _DOF_ALIASES[normalized]
        try:
            return DofType(int(normalized))
        except (ValueError, TypeError):
            pass
    else:
        try:
            return DofType(int(value))
        except (ValueError, TypeError):
            pass
    expected = ", ".join(dof.name for dof in DofType)
    raise FormatError(f"unknown DOF type {value!r}; expected one of {expected}")


def _unwrap(root: Mapping[str, Any], expected_type: str) -> Mapping[str, Any]:
    object_type = root.get("object_type", root.get("type"))
    if object_type is not None and str(object_type).lower() != expected_type:
        raise FormatError(f"expected {expected_type!r}, found object_type={object_type!r}")
    nested = root.get(expected_type)
    if isinstance(nested, Mapping):
        return nested
    return root


def _read_nodes(data: Mapping[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    raw_nodes = data.get("nodes", data.get("coordinates"))
    if raw_nodes is None:
        raise FormatError("model is missing required field 'nodes'")
    if (
        isinstance(raw_nodes, Sequence)
        and not isinstance(raw_nodes, (str, bytes))
        and raw_nodes
        and isinstance(raw_nodes[0], Mapping)
    ):
        entries = [require_mapping(item, "node") for item in raw_nodes]
        try:
            node_ids = np.asarray([entry["id"] for entry in entries], dtype=np.int64)
            coordinates = [
                entry.get("coordinates", entry.get("coords", entry.get("xyz")))
                for entry in entries
            ]
        except (KeyError, TypeError, ValueError) as exc:
            raise FormatError(f"invalid node table: {exc}") from exc
        if any(item is None for item in coordinates):
            raise FormatError("each node entry requires coordinates")
        nodes = decode_array(coordinates, dtype=np.float64, name="nodes")
    else:
        nodes = decode_array(raw_nodes, dtype=np.float64, name="nodes")
        if data.get("node_ids") is None:
            node_ids = np.arange(1, nodes.shape[0] + 1, dtype=np.int64)
        else:
            node_ids = decode_array(data["node_ids"], dtype=np.int64, name="node_ids")
    return node_ids, nodes


def _read_elements(
    data: Mapping[str, Any],
) -> tuple[dict[ElementType, np.ndarray], dict[ElementType, np.ndarray]]:
    raw_elements = data.get("elements", {})
    elements: dict[ElementType, np.ndarray] = {}
    property_ids: dict[ElementType, np.ndarray] = {}
    separate_property_ids = require_mapping(
        data.get("element_property_ids", {}), "element_property_ids"
    )
    if isinstance(raw_elements, Mapping):
        for raw_type, raw_block in raw_elements.items():
            element_type = _parse_element_type(raw_type)
            if isinstance(raw_block, Mapping):
                connectivity = raw_block.get("connectivity", raw_block.get("nodes"))
                block_property_ids = raw_block.get("property_ids")
            else:
                connectivity = raw_block
                block_property_ids = None
            if connectivity is None:
                raise FormatError(f"element block {raw_type!r} is missing connectivity")
            elements[element_type] = decode_array(
                connectivity, dtype=np.int64, name=f"{element_type.value} connectivity"
            )
            raw_ids = (
                block_property_ids
                if block_property_ids is not None
                else separate_property_ids.get(
                    element_type.value, separate_property_ids.get(element_type.name)
                )
            )
            if raw_ids is not None:
                property_ids[element_type] = decode_array(
                    raw_ids, dtype=np.int64, name=f"{element_type.value} property_ids"
                )
    elif isinstance(raw_elements, Sequence) and not isinstance(raw_elements, (str, bytes)):
        grouped_connectivity: dict[ElementType, list[Any]] = {}
        grouped_properties: dict[ElementType, list[int]] = {}
        for raw_entry in raw_elements:
            entry = require_mapping(raw_entry, "element")
            if "type" not in entry:
                raise FormatError("element entry is missing required field 'type'")
            element_type = _parse_element_type(entry["type"])
            connectivity = entry.get("connectivity", entry.get("nodes"))
            if connectivity is None:
                raise FormatError("element entry is missing connectivity")
            grouped_connectivity.setdefault(element_type, []).append(connectivity)
            if "property_id" in entry:
                grouped_properties.setdefault(element_type, []).append(int(entry["property_id"]))
        elements = {
            element_type: decode_array(
                connectivity, dtype=np.int64, name=f"{element_type.value} connectivity"
            )
            for element_type, connectivity in grouped_connectivity.items()
        }
        property_ids = {
            element_type: np.asarray(ids, dtype=np.int64)
            for element_type, ids in grouped_properties.items()
        }
    else:
        raise FormatError("elements must be a mapping of blocks or a sequence")
    return elements, property_ids


def _parse_element_type(value: Any) -> ElementType:
    normalized = str(value).lower()
    try:
        return ElementType(normalized)
    except ValueError:
        try:
            return ElementType[normalized.upper()]
        except KeyError as exc:
            expected = ", ".join(item.value for item in ElementType)
            raise FormatError(
                f"unknown element type {value!r}; expected one of {expected}"
            ) from exc


def _read_materials(value: Any) -> dict[int, NeutralMaterial]:
    entries = _table_entries(value, "materials")
    materials: dict[int, NeutralMaterial] = {}
    for entry in entries:
        try:
            material = NeutralMaterial(
                id=int(entry["id"]),
                E=float(entry["E"]),
                nu=float(entry["nu"]),
                rho=float(entry["rho"]),
                name=str(entry.get("name", "")),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise FormatError(f"invalid material: {exc}") from exc
        if material.id in materials:
            raise FormatError(f"duplicate material id {material.id}")
        materials[material.id] = material
    return materials


def _read_properties(value: Any) -> dict[int, NeutralProperty]:
    entries = _table_entries(value, "properties")
    properties: dict[int, NeutralProperty] = {}
    for entry in entries:
        try:
            raw_values = require_mapping(entry.get("values", {}), "property values")
            prop = NeutralProperty(
                id=int(entry["id"]),
                material_id=int(entry["material_id"]),
                values={str(key): float(item) for key, item in raw_values.items()},
                name=str(entry.get("name", "")),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise FormatError(f"invalid property: {exc}") from exc
        if prop.id in properties:
            raise FormatError(f"duplicate property id {prop.id}")
        properties[prop.id] = prop
    return properties


def _table_entries(value: Any, name: str) -> list[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        entries = []
        for raw_id, raw_entry in value.items():
            entry = dict(require_mapping(raw_entry, name[:-1]))
            entry.setdefault("id", raw_id)
            entries.append(entry)
        return entries
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [require_mapping(entry, name[:-1]) for entry in value]
    raise FormatError(f"{name} must be a mapping or sequence")


def _validate_model_parts(
    node_ids: np.ndarray,
    nodes: np.ndarray,
    elements: Mapping[ElementType, np.ndarray],
    property_ids: Mapping[ElementType, np.ndarray],
    materials: Mapping[int, NeutralMaterial],
    properties: Mapping[int, NeutralProperty],
    dof_map: DofMap | None,
) -> None:
    if nodes.ndim != 2 or nodes.shape[1] != 3:
        raise FormatError(f"nodes must have shape (n_nodes, 3), got {nodes.shape}")
    if node_ids.shape != (nodes.shape[0],):
        raise FormatError(f"node_ids must have shape ({nodes.shape[0]},), got {node_ids.shape}")
    if np.unique(node_ids).size != node_ids.size:
        raise FormatError("node_ids must be unique")
    known_nodes = set(int(item) for item in node_ids)
    for element_type, connectivity in elements.items():
        expected_columns = _NODES_PER_ELEMENT[element_type]
        if connectivity.ndim != 2 or connectivity.shape[1] != expected_columns:
            raise FormatError(
                f"{element_type.value} connectivity must have shape (n, {expected_columns}), "
                f"got {connectivity.shape}"
            )
        unknown = set(int(item) for item in connectivity.flat) - known_nodes
        if unknown:
            raise FormatError(
                f"{element_type.value} connectivity references unknown node ids {sorted(unknown)}"
            )
        if element_type in property_ids:
            ids = property_ids[element_type]
            if ids.shape != (connectivity.shape[0],):
                raise FormatError(
                    f"{element_type.value} property_ids must have shape "
                    f"({connectivity.shape[0]},), got {ids.shape}"
                )
            if properties:
                unknown_properties = set(int(item) for item in ids) - set(properties)
                if unknown_properties:
                    raise FormatError(
                        f"{element_type.value} references unknown property ids "
                        f"{sorted(unknown_properties)}"
                    )
    for prop in properties.values():
        if materials and prop.material_id not in materials:
            raise FormatError(
                f"property {prop.id} references unknown material id {prop.material_id}"
            )
    if dof_map is not None:
        unknown_dof_nodes = set(int(item) for item in dof_map.node_ids) - known_nodes
        if unknown_dof_nodes:
            raise FormatError(f"dof_map references unknown node ids {sorted(unknown_dof_nodes)}")


def _select_modal_payload(
    root: Mapping[str, Any],
    section: str | None,
    *,
    default_section: str,
) -> Mapping[str, Any]:
    if section is not None:
        selected = root.get(section)
        if not isinstance(selected, Mapping):
            raise FormatError(f"document has no mapping section {section!r}")
        return selected
    if default_section in root and isinstance(root[default_section], Mapping):
        return root[default_section]
    object_type = str(root.get("object_type", root.get("type", ""))).lower()
    expected = (
        {"modal", "modal_result"} if default_section == "analytical" else {"test", "test_data"}
    )
    if object_type and object_type not in expected:
        raise FormatError(f"unexpected object_type {object_type!r}")
    return root


def _read_frequencies(data: Mapping[str, Any], root: Mapping[str, Any]) -> np.ndarray:
    raw = data.get("frequencies_hz", data.get("frequencies"))
    if raw is None and data is not root:
        raw = root.get("frequencies_hz", root.get("frequencies"))
    if raw is None:
        raise FormatError("modal data is missing frequencies_hz")
    frequencies = decode_array(raw, dtype=np.float64, name="frequencies_hz")
    if frequencies.ndim != 1:
        raise FormatError(f"frequencies_hz must be one-dimensional, got {frequencies.shape}")
    if not np.all(np.isfinite(frequencies)) or np.any(frequencies < 0.0):
        raise FormatError("frequencies_hz must contain finite, non-negative values")
    return frequencies


def _read_mode_shapes(data: Mapping[str, Any], root: Mapping[str, Any]) -> np.ndarray:
    raw = data.get(
        "mode_shapes",
        data.get("shapes", data.get("mass_normalized_mode_shapes")),
    )
    if raw is None and data is not root:
        raw = root.get(
            "mode_shapes",
            root.get("shapes", root.get("mass_normalized_mode_shapes")),
        )
    if raw is None:
        raise FormatError("modal data is missing mode_shapes")
    shapes = decode_array(raw, name="mode_shapes")
    if shapes.ndim != 2:
        raise FormatError(f"mode_shapes must be two-dimensional, got {shapes.shape}")
    layout = str(
        data.get(
            "mode_shape_layout",
            data.get(
                "shape_layout",
                root.get("mode_shape_layout", root.get("shape_layout", "dofs_by_mode")),
            ),
        )
    ).lower()
    if layout in {"modes_by_dof", "modes_by_dofs", "modes_x_dofs"}:
        shapes = shapes.T
    elif layout not in {"dofs_by_mode", "dof_by_modes", "dofs_x_modes"}:
        raise FormatError(f"unknown mode_shape_layout {layout!r}")
    return shapes


def _read_result_dof_map(
    data: Mapping[str, Any], root: Mapping[str, Any]
) -> tuple[DofMap, list[str] | None]:
    raw_map = data.get("dof_map")
    if raw_map is None and data is not root:
        raw_map = root.get("dof_map")
    if raw_map is not None:
        return dof_map_from_dict(raw_map), None
    raw_labels = data.get("dof_labels")
    if raw_labels is None and data is not root:
        raw_labels = root.get("dof_labels")
    if raw_labels is None:
        raise FormatError("modal data requires dof_map or dof_labels")
    labels = [str(item) for item in raw_labels]
    return dof_map_from_labels(labels), labels


def _result_meta(
    root: Mapping[str, Any],
    data: Mapping[str, Any],
    labels: list[str] | None,
) -> dict[str, Any]:
    raw_meta = data.get("meta", {})
    meta = dict(require_mapping(raw_meta, "meta"))
    if data is not root:
        for field in ("name", "description", "units"):
            if field in root and field not in meta:
                meta[field] = root[field]
    if labels is not None and "dof_labels" not in meta:
        meta["dof_labels"] = labels
    return meta
