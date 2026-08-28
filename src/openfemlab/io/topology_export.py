"""Export topology optimization densities to VTK/VTU via meshio."""

from __future__ import annotations

from os import PathLike

import numpy as np

from openfemlab.core.elements import Hex8Element, Quad4Element, Tet4Element, Tri3Element
from openfemlab.core.neutral import ElementType, NeutralMaterial, NeutralModel, NeutralProperty
from openfemlab.exceptions import OpenFEMLabError

from .meshio_bridge import require_meshio, to_meshio

__all__ = ["DENSITY_CELL_KEY", "model_to_neutral", "write_topology_vtu"]

DENSITY_CELL_KEY = "density"


def model_to_neutral(model) -> NeutralModel:
    """Build a minimal :class:`NeutralModel` from a solver :class:`Model`."""
    if model.num_nodes == 0:
        raise OpenFEMLabError("cannot export an empty model")
    node_ids = np.array([node.id for node in model.nodes], dtype=np.int64)
    nodes = np.asarray(model.coordinates, dtype=float)
    if nodes.shape[1] < 3:
        padded = np.zeros((nodes.shape[0], 3), dtype=float)
        padded[:, : nodes.shape[1]] = nodes
        nodes = padded
    blocks: dict[ElementType, list[list[int]]] = {}
    element_ids: dict[ElementType, list[int]] = {}
    property_ids: dict[ElementType, list[int]] = {}
    materials: dict[int, NeutralMaterial] = {}
    properties: dict[int, NeutralProperty] = {}
    property_counter = 1
    for index, element in enumerate(model.elements):
        if isinstance(element, Tet4Element):
            kind = ElementType.TET4
        elif isinstance(element, Hex8Element):
            kind = ElementType.HEX8
        elif isinstance(element, Quad4Element):
            kind = ElementType.QUAD4
        elif isinstance(element, Tri3Element):
            kind = ElementType.TRI3
        else:
            raise OpenFEMLabError(
                f"topology export does not support {type(element).__name__} yet"
            )
        material = getattr(element, "material", None)
        property_id = property_counter
        property_counter += 1
        youngs = float(getattr(material, "E", 1.0))
        density = float(getattr(material, "density", 0.0))
        nu = float(getattr(material, "nu", 0.3))
        materials[property_id] = NeutralMaterial(
            id=property_id, E=youngs, nu=nu, rho=density, name=f"mat_{property_id}"
        )
        thickness = float(getattr(element, "thickness", 1.0))
        properties[property_id] = NeutralProperty(
            id=property_id,
            material_id=property_id,
            values={"t": thickness},
            name=f"prop_{property_id}",
        )
        blocks.setdefault(kind, []).append([int(node_id) for node_id in element.node_ids])
        element_ids.setdefault(kind, []).append(index)
        property_ids.setdefault(kind, []).append(property_id)
    elements = {kind: np.asarray(rows, dtype=np.int64) for kind, rows in blocks.items()}
    element_property_ids = {
        kind: np.asarray(values, dtype=np.int64) for kind, values in property_ids.items()
    }
    meta = {
        "element_ids": {
            kind.value: np.asarray(values, dtype=np.int64)
            for kind, values in element_ids.items()
        }
    }
    return NeutralModel(
        nodes=nodes,
        node_ids=node_ids,
        elements=elements,
        element_property_ids=element_property_ids,
        materials=materials,
        properties=properties,
        meta=meta,
    )


def write_topology_vtu(
    model,
    densities: np.ndarray,
    destination: str | PathLike[str],
    *,
    use_projected: np.ndarray | None = None,
) -> None:
    """Write element densities as VTU/VTK cell data."""
    values = np.asarray(
        use_projected if use_projected is not None else densities, dtype=float
    ).reshape(-1)
    if values.size != model.num_elements:
        raise OpenFEMLabError(
            f"expected {model.num_elements} densities, got {values.size}"
        )
    neutral = model_to_neutral(model)
    meshio = require_meshio()
    mesh = to_meshio(neutral)
    density_blocks: list[np.ndarray] = []
    offset = 0
    for element_type in neutral.elements:
        count = int(neutral.elements[element_type].shape[0])
        density_blocks.append(values[offset : offset + count])
        offset += count
    cell_data = dict(mesh.cell_data)
    cell_data[DENSITY_CELL_KEY] = density_blocks
    mesh = meshio.Mesh(
        mesh.points,
        mesh.cells,
        point_data=dict(mesh.point_data),
        cell_data=cell_data,
    )
    meshio.write(destination, mesh)
