"""Reader for the UNV geometry datasets 2411 (nodes) and 2412 (elements).

UNV files are the geometry half of the same ASCII container
:mod:`openfemlab.io.uff` reads test data from, so a single file exported by a
test system can carry a mesh (2411/2412), its mode shapes (55) and its
measured functions (58) at once.  This module reads the mesh half into a
:class:`~openfemlab.core.neutral.NeutralModel`; datasets it does not know are
skipped, exactly as the UFF reader skips geometry.

Element records are mapped to :class:`~openfemlab.core.neutral.ElementType`
through the explicit :data:`FE_DESCRIPTOR_TO_ELEMENT` table.  Descriptors
outside that table — higher-order cells, rigid elements, anything the solver
has no formulation for — are skipped with a warning and counted in
``NeutralModel.meta["skipped_fe_descriptors"]``, mirroring the policy of the
Nastran and meshio readers: import the supported subset rather than refuse to
open the file.

A UNV mesh names its property and material tables by number but does not
define them (datasets 1710/1716 and friends do, and are outside this subset),
so ``NeutralModel.properties`` and ``materials`` come back empty; the numbers
survive as ``element_property_ids`` and ``meta["element_material_ids"]``.
"""

from __future__ import annotations

import warnings
from os import PathLike
from typing import Any, TextIO

import numpy as np

from openfemlab.core.neutral import ElementType, NeutralModel

from ._common import FormatError
from ._uff_records import dataset_blocks, integer, numbers, read_text

__all__ = [
    "BEAM_FE_DESCRIPTORS",
    "ELEMENT_NODE_COUNTS",
    "FE_DESCRIPTOR_TO_ELEMENT",
    "UNV_ELEMENT_DATASET",
    "UNV_NODE_DATASET",
    "read_unv",
]

#: Dataset number of the double-precision node table.
UNV_NODE_DATASET = 2411

#: Dataset number of the element table.
UNV_ELEMENT_DATASET = 2412

#: UNV FE descriptor id → neutral element type.  Only descriptors whose node
#: count and ordering match a formulation the solver has are listed; the
#: parabolic and higher-order relatives of these cells are deliberately absent
#: rather than silently truncated to their corner nodes.
FE_DESCRIPTOR_TO_ELEMENT: dict[int, ElementType] = {
    11: ElementType.ROD2,       # rod
    21: ElementType.BEAM2,      # linear beam
    22: ElementType.BEAM2,      # tapered beam
    41: ElementType.TRI3,       # plane stress linear triangle
    91: ElementType.TRI3,       # thin shell linear triangle
    44: ElementType.QUAD4,      # plane stress linear quadrilateral
    94: ElementType.QUAD4,      # thin shell linear quadrilateral
    111: ElementType.TET4,      # solid linear tetrahedron
    115: ElementType.HEX8,      # solid linear brick
    136: ElementType.SPRING2,   # node-to-node translational spring
    137: ElementType.SPRING2,   # node-to-node rotational spring
    161: ElementType.MASS1,     # lumped mass
}

#: Nodes per element for every type :data:`FE_DESCRIPTOR_TO_ELEMENT` produces.
#: The count a record declares is checked against this, so a file that labels a
#: quadrilateral as a triangle fails instead of importing a wrong element.
ELEMENT_NODE_COUNTS: dict[ElementType, int] = {
    ElementType.MASS1: 1,
    ElementType.ROD2: 2,
    ElementType.BEAM2: 2,
    ElementType.SPRING2: 2,
    ElementType.TRI3: 3,
    ElementType.QUAD4: 4,
    ElementType.TET4: 4,
    ElementType.HEX8: 8,
}

#: Descriptors whose element record carries the extra beam line (orientation
#: node plus fore-end and aft-end cross-section numbers) before connectivity.
#: The curved (23) and parabolic (24) beams are unmapped but still have it, so
#: they have to be listed here to keep the record scan in step.
BEAM_FE_DESCRIPTORS = frozenset({11, 21, 22, 23, 24})

_SUPPORTED_DATASETS = frozenset({UNV_NODE_DATASET, UNV_ELEMENT_DATASET})


def read_unv(source: str | PathLike[str] | TextIO) -> NeutralModel:
    """Read the 2411/2412 geometry of an ASCII UNV file into a neutral model.

    Parameters
    ----------
    source:
        Path or open text stream.  Other datasets in the file, including the
        55/58 test data :func:`~openfemlab.io.uff.read_uff` reads, are ignored.

    Notes
    -----
    Coordinates are taken as written, in the export coordinate system each node
    record names.  Dataset 2420 (coordinate systems) is outside this subset, so
    no transformation is possible: the system labels are recorded in
    ``meta["export_coordinate_systems"]`` and a file mixing several of them
    warns, because its coordinates are then not all in one frame.
    """

    text, source_name = read_text(source, description="UNV")

    nodes: dict[int, tuple[float, float, float]] = {}
    coordinate_systems: list[int] = []
    connectivity: dict[ElementType, list[list[int]]] = {}
    property_ids: dict[ElementType, list[int]] = {}
    material_ids: dict[ElementType, list[int]] = {}
    element_ids: dict[ElementType, list[int]] = {}
    orientation_nodes: dict[int, int] = {}
    skipped: dict[int, int] = {}
    element_labels: set[int] = set()
    saw_nodes = False

    for dataset_number, payload in dataset_blocks(text, _SUPPORTED_DATASETS):
        records = _RecordReader(payload)
        try:
            if dataset_number == UNV_NODE_DATASET:
                saw_nodes = True
                _parse_nodes(records, nodes, coordinate_systems)
            else:
                _parse_elements(
                    records,
                    connectivity,
                    property_ids,
                    material_ids,
                    element_ids,
                    orientation_nodes,
                    skipped,
                    element_labels,
                )
        except FormatError as exc:
            raise FormatError(f"invalid UNV dataset {dataset_number}: {exc}") from exc

    if not saw_nodes:
        raise FormatError(
            f"file contains no dataset {UNV_NODE_DATASET} (nodes); it is not a UNV mesh"
        )

    referenced = {node_id for rows in connectivity.values() for row in rows for node_id in row}
    unknown = sorted(referenced - nodes.keys())
    if unknown:
        joined = ", ".join(str(node_id) for node_id in unknown)
        raise FormatError(
            f"dataset {UNV_ELEMENT_DATASET} connectivity references unknown node labels: "
            f"{joined}"
        )

    if skipped:
        joined = ", ".join(
            f"{descriptor} ({count})" for descriptor, count in sorted(skipped.items())
        )
        warnings.warn(
            f"skipped UNV elements with unsupported FE descriptor ids: {joined}",
            stacklevel=2,
        )
    distinct_systems = sorted(set(coordinate_systems))
    if len(distinct_systems) > 1:
        warnings.warn(
            "UNV nodes use more than one export coordinate system "
            f"({', '.join(str(system) for system in distinct_systems)}); dataset 2420 is "
            "not read, so coordinates are imported untransformed",
            stacklevel=2,
        )

    meta: dict[str, Any] = {
        "format": "unv",
        "element_ids": {
            element_type.value: element_ids[element_type] for element_type in connectivity
        },
        "element_material_ids": {
            element_type.value: material_ids[element_type] for element_type in connectivity
        },
        "export_coordinate_systems": distinct_systems,
    }
    if orientation_nodes:
        meta["beam_orientation_nodes"] = dict(sorted(orientation_nodes.items()))
    if skipped:
        meta["skipped_fe_descriptors"] = dict(sorted(skipped.items()))
    if source_name is not None:
        meta["source"] = source_name

    return NeutralModel(
        nodes=np.asarray(list(nodes.values()), dtype=np.float64).reshape((-1, 3)),
        node_ids=np.fromiter(nodes, dtype=np.int64, count=len(nodes)),
        elements={
            element_type: np.asarray(rows, dtype=np.int64).reshape(
                (len(rows), ELEMENT_NODE_COUNTS[element_type])
            )
            for element_type, rows in connectivity.items()
        },
        element_property_ids={
            element_type: np.asarray(property_ids[element_type], dtype=np.int64)
            for element_type in connectivity
        },
        meta=meta,
    )


class _RecordReader:
    """Sequential reader over the numeric records of one dataset block.

    UNV records are fixed-width Fortran output, but a record may also be
    continued across lines (connectivity wraps every eight nodes), so records
    are consumed by field count rather than by line.
    """

    def __init__(self, lines: list[str]) -> None:
        self._lines = lines
        self._index = 0

    def at_end(self) -> bool:
        while self._index < len(self._lines) and not self._lines[self._index].strip():
            self._index += 1
        return self._index >= len(self._lines)

    def record(self, count: int, description: str) -> list[float]:
        """Consume whole lines until exactly ``count`` numeric fields are read."""

        if self.at_end():
            raise FormatError(f"file ends where {description} was expected")
        values: list[float] = []
        while len(values) < count and self._index < len(self._lines):
            line = self._lines[self._index]
            self._index += 1
            if line.strip():
                values.extend(numbers(line))
        if len(values) != count:
            raise FormatError(
                f"{description} requires {count} numeric fields, found {len(values)}"
            )
        return values


def _parse_nodes(
    records: _RecordReader,
    nodes: dict[int, tuple[float, float, float]],
    coordinate_systems: list[int],
) -> None:
    while not records.at_end():
        header = records.record(4, "a node record")
        label = _label(header[0], "node label")
        coordinate_systems.append(integer(header[1], "export coordinate system"))
        coordinates = records.record(3, f"the coordinates of node {label}")
        if label in nodes:
            raise FormatError(f"duplicate node label {label}")
        if not all(np.isfinite(value) for value in coordinates):
            raise FormatError(f"node {label} has non-finite coordinates")
        nodes[label] = (coordinates[0], coordinates[1], coordinates[2])


def _parse_elements(
    records: _RecordReader,
    connectivity: dict[ElementType, list[list[int]]],
    property_ids: dict[ElementType, list[int]],
    material_ids: dict[ElementType, list[int]],
    element_ids: dict[ElementType, list[int]],
    orientation_nodes: dict[int, int],
    skipped: dict[int, int],
    element_labels: set[int],
) -> None:
    while not records.at_end():
        header = records.record(6, "an element record")
        label = _label(header[0], "element label")
        if label in element_labels:
            raise FormatError(f"duplicate element label {label}")
        element_labels.add(label)

        descriptor = integer(header[1], f"the FE descriptor id of element {label}")
        property_id = integer(header[2], f"the property table number of element {label}")
        material_id = integer(header[3], f"the material table number of element {label}")
        declared_nodes = integer(header[5], f"the node count of element {label}")
        if declared_nodes <= 0:
            raise FormatError(f"element {label} declares {declared_nodes} nodes")

        orientation: int | None = None
        if descriptor in BEAM_FE_DESCRIPTORS:
            beam = records.record(3, f"the beam record of element {label}")
            orientation = integer(beam[0], f"the orientation node of element {label}")
        nodes = [
            _label(value, f"a node label of element {label}")
            for value in records.record(declared_nodes, f"the connectivity of element {label}")
        ]

        element_type = FE_DESCRIPTOR_TO_ELEMENT.get(descriptor)
        if element_type is None:
            skipped[descriptor] = skipped.get(descriptor, 0) + 1
            continue
        expected_nodes = ELEMENT_NODE_COUNTS[element_type]
        if declared_nodes != expected_nodes:
            raise FormatError(
                f"element {label} maps to {element_type.value} but declares "
                f"{declared_nodes} nodes instead of {expected_nodes}"
            )
        if len(set(nodes)) != len(nodes):
            raise FormatError(f"element {label} repeats a node label")

        connectivity.setdefault(element_type, []).append(nodes)
        property_ids.setdefault(element_type, []).append(property_id)
        material_ids.setdefault(element_type, []).append(material_id)
        element_ids.setdefault(element_type, []).append(label)
        if orientation:
            orientation_nodes[label] = orientation


def _label(value: float, name: str) -> int:
    label = integer(value, name)
    if label <= 0:
        raise FormatError(f"{name} must be positive, found {label}")
    return label
