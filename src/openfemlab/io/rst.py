"""Ansys MAPDL ``.rst`` reader via optional ``ansys-mapdl-reader``."""

from __future__ import annotations

from importlib import import_module
from os import PathLike
from pathlib import Path

import numpy as np

from openfemlab.exceptions import MissingDependencyError

from ._common import FormatError
from .external_result import ExternalResult

__all__ = ["RSTResult", "read_rst"]

RSTResult = ExternalResult


def read_rst(
    source: str | PathLike[str],
    *,
    step: int = -1,
) -> ExternalResult:
    """Read nodal displacements from an Ansys binary ``.rst`` file.

    Requires the optional ``ansys-mapdl-reader`` package (``pip install
    openfemlab[io-rst]``).  No live Ansys licence is needed to read the file.
    """
    path = Path(source).resolve()
    if not path.is_file():
        raise FormatError(f"RST file not found: {path}")
    reader = _require_mapdl_reader()
    try:
        result = reader.read_binary(str(path))
    except OSError as exc:
        raise FormatError(f"cannot read RST file {path}: {exc}") from exc
    step_index = int(step)
    if step_index < 0:
        step_index = int(result.nsets) - 1 if hasattr(result, "nsets") else 0
    try:
        node_ids, values = result.nodal_solution(step_index)
    except Exception as exc:
        raise FormatError(f"RST file {path} has no displacement at step {step_index}") from exc
    node_ids = np.asarray(node_ids, dtype=np.int64).reshape(-1)
    displacements = np.asarray(values, dtype=float)
    if displacements.ndim == 1:
        displacements = displacements.reshape(-1, 1)
    if displacements.shape[0] != node_ids.size:
        raise FormatError("RST displacement rows do not match node count")
    if displacements.shape[1] == 2:
        displacements = np.column_stack([displacements, np.zeros(node_ids.size)])
    elif displacements.shape[1] != 3:
        raise FormatError(
            f"RST displacement must have 2 or 3 components, got {displacements.shape[1]}"
        )
    coordinates = np.zeros((node_ids.size, 3), dtype=float)
    if hasattr(result, "nodes") and result.nodes is not None:
        try:
            mesh_nodes = np.asarray(result.nodes, dtype=float)
            if mesh_nodes.shape[0] == node_ids.size:
                coordinates[:, : mesh_nodes.shape[1]] = mesh_nodes[:, :3]
        except Exception:
            pass
    return ExternalResult(
        node_ids=node_ids,
        coordinates=coordinates,
        displacements=displacements,
        format="ansys-rst",
        meta={"source": str(path), "step": step_index},
    )


def _require_mapdl_reader():
    try:
        return import_module("ansys.mapdl.reader")
    except ImportError as exc:
        raise MissingDependencyError(
            "reading Ansys .rst files requires ansys-mapdl-reader; "
            "install with: pip install ansys-mapdl-reader"
        ) from exc
