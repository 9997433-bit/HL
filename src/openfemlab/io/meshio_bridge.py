"""Bridge between ``meshio`` meshes and the neutral model contract.

``meshio`` is an optional dependency (the ``[io]`` extra) and, per the
ARCHITECTURE P7 policy, it is never imported at module import time: only the
file-level entry points :func:`read_meshio` / :func:`write_meshio` and the
:func:`to_meshio` exporter need the package, and each of them raises
:class:`~openfemlab.exceptions.MissingDependencyError` with an install hint
when it is absent.  :func:`from_meshio` deliberately needs nothing beyond
NumPy: it accepts any object exposing meshio's ``points`` / ``cells``
attributes, so an importer that already holds a mesh can convert it in an
installation without the extra.

Cell blocks are mapped to :class:`~openfemlab.core.neutral.ElementType`
through the explicit :data:`CELL_TYPE_TO_ELEMENT` table.  Cell types outside
that table are skipped with a warning and recorded in
``NeutralModel.meta["skipped_cell_types"]``, mirroring the Nastran reader's
policy of importing the supported subset rather than failing on the first
unknown record.

A meshio file carries geometry and connectivity but no material or section
data, so ``NeutralModel.materials`` and ``NeutralModel.properties`` come back
empty; only the property *ids* survive, from cell data when the file has it.
"""

from __future__ import annotations

import warnings
from collections.abc import Sequence
from importlib import import_module
from os import PathLike
from types import ModuleType
from typing import Any

import numpy as np
import numpy.typing as npt

from openfemlab.core.neutral import ElementType, NeutralModel
from openfemlab.exceptions import MissingDependencyError

from ._common import FormatError

__all__ = [
    "CELL_TYPE_TO_ELEMENT",
    "ELEMENT_TO_CELL_TYPE",
    "ELEMENT_ID_KEY",
    "NODE_ID_KEY",
    "PROPERTY_ID_KEYS",
    "from_meshio",
    "read_meshio",
    "require_meshio",
    "to_meshio",
    "write_meshio",
]

#: meshio cell type → neutral element type.  The table is one-to-one so that a
#: ``NeutralModel`` exported through :func:`to_meshio` reads back unchanged.
#: ``beam2`` and ``spring2`` are absent by construction: meshio's ``line`` cell
#: has no attribute that would distinguish them from ``rod2``.
CELL_TYPE_TO_ELEMENT: dict[str, ElementType] = {
    "vertex": ElementType.MASS1,
    "line": ElementType.ROD2,
    "triangle": ElementType.TRI3,
    "quad": ElementType.QUAD4,
    "tetra": ElementType.TET4,
    "hexahedron": ElementType.HEX8,
}

ELEMENT_TO_CELL_TYPE: dict[ElementType, str] = {
    element: cell_type for cell_type, element in CELL_TYPE_TO_ELEMENT.items()
}

#: Point-data array holding external node labels, written by :func:`to_meshio`.
NODE_ID_KEY = "node_ids"

#: Cell-data array holding external element labels, written by :func:`to_meshio`.
ELEMENT_ID_KEY = "element_ids"

#: Cell-data arrays read as property ids, in order of preference.  The mesher
#: tags (``gmsh:physical``, ``medit:ref``) are the closest thing most formats
#: have to a property assignment.
PROPERTY_ID_KEYS = ("property_ids", "gmsh:physical", "medit:ref")

_MESHIO_EXTRA = "openfemlab[io]"


def require_meshio() -> ModuleType:
    """Import and return :mod:`meshio`, or raise a typed install hint."""

    try:
        return import_module("meshio")
    except ImportError as exc:
        raise MissingDependencyError(
            "meshio is required for mesh interchange; install it with "
            f'pip install "{_MESHIO_EXTRA}"'
        ) from exc


def from_meshio(
    mesh: Any,
    *,
    node_ids: Sequence[int] | npt.NDArray[np.integer] | None = None,
    default_property_id: int = 1,
    source: str | None = None,
) -> NeutralModel:
    """Convert a ``meshio.Mesh`` (or a duck-typed equivalent) to a neutral model.

    Parameters
    ----------
    mesh:
        Any object with meshio's ``points`` array and ``cells`` blocks; the
        optional ``point_data`` / ``cell_data`` mappings are honoured when
        present.
    node_ids:
        External node labels, one per point.  Overrides a ``node_ids`` point
        data array; when neither is given, points are labelled ``1..n_nodes``.
    default_property_id:
        Property id assigned to cell blocks whose file carries no property tag.
    source:
        Provenance string recorded in ``meta["source"]``.

    Notes
    -----
    Connectivity is stored as **node ids**, per the ``NeutralModel``
    contract, not as the zero-based point indices meshio uses.
    """

    points = _points(mesh)
    labels = _node_ids(mesh, points.shape[0], node_ids)
    blocks = _cell_blocks(mesh)
    cell_data = _mapping(getattr(mesh, "cell_data", None), "cell_data")

    connectivity: dict[ElementType, list[npt.NDArray[np.int64]]] = {}
    property_ids: dict[ElementType, list[npt.NDArray[np.int64]]] = {}
    element_ids: dict[ElementType, list[int]] = {}
    skipped: dict[str, int] = {}
    next_element_id = 1

    for index, (cell_type, cells) in enumerate(blocks):
        element_type = CELL_TYPE_TO_ELEMENT.get(cell_type)
        if element_type is None:
            skipped[cell_type] = skipped.get(cell_type, 0) + int(cells.shape[0])
            continue
        if cells.size and (cells.min() < 0 or cells.max() >= points.shape[0]):
            raise FormatError(
                f"{cell_type} block {index} references point indices outside "
                f"0..{points.shape[0] - 1}"
            )
        connectivity.setdefault(element_type, []).append(labels[cells])
        property_ids.setdefault(element_type, []).append(
            _block_data(
                cell_data, PROPERTY_ID_KEYS, index, cells.shape[0], default_property_id
            )
        )
        block_ids = _block_data(
            cell_data, (ELEMENT_ID_KEY,), index, cells.shape[0], None
        )
        if block_ids is None:
            block_ids = np.arange(
                next_element_id, next_element_id + cells.shape[0], dtype=np.int64
            )
        next_element_id = max(next_element_id + cells.shape[0], int(block_ids.max(initial=0)) + 1)
        element_ids.setdefault(element_type, []).extend(int(value) for value in block_ids)

    if skipped:
        joined = ", ".join(f"{name} ({count})" for name, count in sorted(skipped.items()))
        warnings.warn(
            f"skipped unsupported meshio cell types: {joined}",
            stacklevel=2,
        )

    meta: dict[str, Any] = {
        "format": "meshio",
        "element_ids": {
            element_type.value: element_ids[element_type] for element_type in connectivity
        },
    }
    if skipped:
        meta["skipped_cell_types"] = dict(sorted(skipped.items()))
    if source is not None:
        meta["source"] = source

    return NeutralModel(
        nodes=points,
        node_ids=labels,
        elements={
            element_type: np.concatenate(parts, axis=0)
            for element_type, parts in connectivity.items()
        },
        element_property_ids={
            element_type: np.concatenate(parts, axis=0)
            for element_type, parts in property_ids.items()
        },
        meta=meta,
    )


def to_meshio(model: NeutralModel) -> Any:
    """Convert a :class:`NeutralModel` to a ``meshio.Mesh``.

    Node and element labels travel as the ``node_ids`` point-data and
    ``element_ids`` cell-data arrays so that :func:`from_meshio` recovers them.
    Element types with no one-to-one meshio cell type raise
    :class:`~openfemlab.io.FormatError` rather than silently collapsing onto a
    cell type that would read back as a different element.
    """

    meshio = require_meshio()

    index_of = {int(node_id): index for index, node_id in enumerate(model.node_ids)}
    cells: list[tuple[str, npt.NDArray[np.int64]]] = []
    property_blocks: list[npt.NDArray[np.int64]] = []
    element_id_blocks: list[npt.NDArray[np.int64]] = []
    meta_ids = model.meta.get("element_ids", {}) if isinstance(model.meta, dict) else {}

    for element_type, block in model.elements.items():
        cell_type = ELEMENT_TO_CELL_TYPE.get(element_type)
        if cell_type is None:
            supported = ", ".join(sorted(element.value for element in ELEMENT_TO_CELL_TYPE))
            raise FormatError(
                f"element type {element_type.value!r} has no meshio cell type "
                f"(exportable types: {supported})"
            )
        connectivity = np.asarray(block, dtype=np.int64).reshape((block.shape[0], -1))
        try:
            indices = np.asarray(
                [[index_of[int(node_id)] for node_id in row] for row in connectivity],
                dtype=np.int64,
            ).reshape(connectivity.shape)
        except KeyError as exc:
            raise FormatError(
                f"{element_type.value} connectivity references unknown node id {exc.args[0]}"
            ) from exc
        cells.append((cell_type, indices))
        property_blocks.append(
            _element_property_ids(model, element_type, connectivity.shape[0])
        )
        element_id_blocks.append(
            _element_labels(meta_ids.get(element_type.value), connectivity.shape[0])
        )

    return meshio.Mesh(
        points=np.asarray(model.nodes, dtype=np.float64),
        cells=cells,
        point_data={NODE_ID_KEY: np.asarray(model.node_ids, dtype=np.int64)},
        cell_data={
            PROPERTY_ID_KEYS[0]: property_blocks,
            ELEMENT_ID_KEY: element_id_blocks,
        },
    )


def read_meshio(
    source: str | PathLike[str],
    *,
    file_format: str | None = None,
    default_property_id: int = 1,
) -> NeutralModel:
    """Read any meshio-supported mesh file into a :class:`NeutralModel`."""

    meshio = require_meshio()
    try:
        mesh = meshio.read(source, file_format)
    except (OSError, UnicodeError, ValueError, KeyError, meshio.ReadError) as exc:
        raise FormatError(f"cannot read mesh file {source!s}: {exc}") from exc
    return from_meshio(mesh, default_property_id=default_property_id, source=str(source))


def write_meshio(
    model: NeutralModel,
    destination: str | PathLike[str],
    *,
    file_format: str | None = None,
) -> None:
    """Write a :class:`NeutralModel` to any meshio-supported mesh file."""

    meshio = require_meshio()
    try:
        meshio.write(destination, to_meshio(model), file_format)
    except (
        OSError,
        UnicodeError,
        ValueError,
        KeyError,
        meshio.ReadError,  # raised when the writer cannot deduce the format
        meshio.WriteError,
    ) as exc:
        raise FormatError(f"cannot write mesh file {destination!s}: {exc}") from exc


def _points(mesh: Any) -> npt.NDArray[np.float64]:
    raw = getattr(mesh, "points", None)
    if raw is None:
        raise FormatError("mesh has no points array")
    try:
        points = np.asarray(raw, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise FormatError(f"mesh points are not numeric: {exc}") from exc
    if points.ndim != 2 or not 1 <= points.shape[1] <= 3:
        raise FormatError(
            f"mesh points must have shape (n_points, 1..3), got {points.shape}"
        )
    if points.shape[1] == 3:
        return points
    # 2-D meshes arrive with the out-of-plane column dropped; the neutral
    # contract is always three-dimensional.
    padded = np.zeros((points.shape[0], 3), dtype=np.float64)
    padded[:, : points.shape[1]] = points
    return padded


def _node_ids(
    mesh: Any,
    n_points: int,
    override: Sequence[int] | npt.NDArray[np.integer] | None,
) -> npt.NDArray[np.int64]:
    point_data = _mapping(getattr(mesh, "point_data", None), "point_data")
    raw = override if override is not None else point_data.get(NODE_ID_KEY)
    if raw is None:
        return np.arange(1, n_points + 1, dtype=np.int64)
    ids = _integer_array(raw, "node_ids").reshape(-1)
    if ids.shape != (n_points,):
        raise FormatError(f"node_ids must have shape ({n_points},), got {ids.shape}")
    if np.unique(ids).size != ids.size:
        raise FormatError("node_ids must be unique")
    return ids


def _cell_blocks(mesh: Any) -> list[tuple[str, npt.NDArray[np.int64]]]:
    raw_blocks = getattr(mesh, "cells", None)
    if raw_blocks is None:
        raise FormatError("mesh has no cell blocks")
    blocks: list[tuple[str, npt.NDArray[np.int64]]] = []
    for index, block in enumerate(raw_blocks):
        cell_type = getattr(block, "type", None)
        data = getattr(block, "data", None)
        if cell_type is None:
            try:
                cell_type, data = block
            except (TypeError, ValueError) as exc:
                raise FormatError(
                    f"cell block {index} is neither a meshio CellBlock nor a "
                    "(type, data) pair"
                ) from exc
        cells = _integer_array(data, f"cell block {index}")
        if cells.ndim != 2:
            raise FormatError(
                f"cell block {index} must have shape (n_cells, nodes_per_cell), "
                f"got {cells.shape}"
            )
        blocks.append((str(cell_type), cells))
    return blocks


def _mapping(value: Any, description: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not hasattr(value, "get"):
        raise FormatError(f"{description} must be a mapping, got {type(value).__name__}")
    return dict(value)


def _block_data(
    cell_data: dict[str, Any],
    keys: Sequence[str],
    index: int,
    n_cells: int,
    default: int | None,
) -> npt.NDArray[np.int64] | None:
    for key in keys:
        blocks = cell_data.get(key)
        if blocks is None:
            continue
        if index >= len(blocks):
            raise FormatError(f"cell data {key!r} has no entry for cell block {index}")
        values = _integer_array(blocks[index], f"cell data {key!r}").reshape(-1)
        if values.shape != (n_cells,):
            raise FormatError(
                f"cell data {key!r} for block {index} must have shape ({n_cells},), "
                f"got {values.shape}"
            )
        return values
    if default is None:
        return None
    return np.full(n_cells, int(default), dtype=np.int64)


def _element_property_ids(
    model: NeutralModel, element_type: ElementType, n_elements: int
) -> npt.NDArray[np.int64]:
    values = model.element_property_ids.get(element_type)
    if values is None:
        return np.ones(n_elements, dtype=np.int64)
    ids = np.asarray(values, dtype=np.int64).reshape(-1)
    if ids.shape != (n_elements,):
        raise FormatError(
            f"{element_type.value} property ids must have shape ({n_elements},), "
            f"got {ids.shape}"
        )
    return ids


def _element_labels(values: Any, n_elements: int) -> npt.NDArray[np.int64]:
    if values is None:
        return np.arange(1, n_elements + 1, dtype=np.int64)
    labels = _integer_array(values, "element_ids").reshape(-1)
    if labels.shape != (n_elements,):
        raise FormatError(
            f"element_ids must have shape ({n_elements},), got {labels.shape}"
        )
    return labels


def _integer_array(value: Any, description: str) -> npt.NDArray[np.int64]:
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise FormatError(f"{description} is not an array: {exc}") from exc
    if array.dtype.kind == "f" and not np.all(array == np.floor(array)):
        raise FormatError(f"{description} must hold integers")
    if array.dtype.kind not in "iuf":
        raise FormatError(f"{description} must hold integers, got dtype {array.dtype}")
    return array.astype(np.int64, copy=False)
