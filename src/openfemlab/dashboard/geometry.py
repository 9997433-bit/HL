"""Model geometry as the browser viewer consumes it.

The dashboard draws a mode shape by displacing the nodes of a wireframe, so it
needs three things the correlation JSON does not carry: nodal coordinates, the
element edges connecting them, and the DOF ordering that says which entry of a
mode-shape vector belongs to which node and direction.

:func:`geometry_payload` derives all three from a solver
:class:`~openfemlab.core.model.Model`; :func:`geometry_from_spec` builds that
model from a CLI model spec, which is the file a project already has on disk.
"""

from __future__ import annotations

from os import PathLike
from typing import Any

import numpy as np

from ..viz.plotting import element_edges

__all__ = ["geometry_payload", "geometry_from_spec"]

#: Version of the payload contract the static viewer reads.
GEOMETRY_SCHEMA_VERSION = "1.0"


def geometry_payload(model: Any) -> dict[str, Any]:
    """JSON-ready wireframe and DOF layout of ``model``.

    The ``edges`` are node *positions* (rows of ``nodes``), not node ids, so a
    viewer can index the coordinate array directly.  ``dof_map`` mirrors the
    native modal-result contract of :mod:`openfemlab.io`, which is what lets
    the viewer line a mode-shape vector up with the nodes.
    """
    nodes = list(model.nodes)
    if not nodes:
        raise ValueError("model has no nodes to draw")
    position = {node.id: index for index, node in enumerate(nodes)}

    edges: list[list[int]] = []
    seen: set[tuple[int, int]] = set()
    for element in model.elements:
        for start, end in element_edges(element):
            pair = (
                position[element.node_ids[start]],
                position[element.node_ids[end]],
            )
            key = (min(pair), max(pair))
            if key in seen:
                continue
            seen.add(key)
            edges.append([pair[0], pair[1]])

    coordinates = np.asarray(model.coordinates, dtype=float)
    dof_names = [dof.name for dof in model.dofs]
    return {
        "schema_version": GEOMETRY_SCHEMA_VERSION,
        "name": str(getattr(model, "name", "model")),
        "node_ids": [str(node.id) for node in nodes],
        "nodes": coordinates.tolist(),
        "edges": edges,
        "dofs": dof_names,
        "dof_map": {
            "node_ids": [str(node.id) for node in nodes for _ in dof_names],
            "dof_types": [name for _ in nodes for name in dof_names],
        },
        "dof_labels": list(model.dof_labels),
        "num_dofs": int(model.num_dofs),
        "constrained_dofs": [int(index) for index in model.constrained_dofs],
        "bounds": {
            "min": coordinates.min(axis=0).tolist(),
            "max": coordinates.max(axis=0).tolist(),
        },
    }


def geometry_from_spec(source: str | PathLike[str]) -> dict[str, Any]:
    """Build a model from a CLI model spec and return its geometry payload."""
    from ..cli.spec import build_model, load_spec

    return geometry_payload(build_model(load_spec(source)))
