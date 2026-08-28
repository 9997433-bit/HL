"""Map external solver nodes onto an OpenFEMLab :class:`~openfemlab.core.model.Model`."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..mesh import nearest_nodes
from .external_result import ExternalResult

__all__ = ["ExternalNodeMap", "map_external_to_model"]


@dataclass(frozen=True, slots=True)
class ExternalNodeMap:
    """Pairing between external result nodes and model node indices."""

    model_node_indices: np.ndarray
    external_indices: np.ndarray
    distances: np.ndarray
    unmatched_external: tuple[int, ...]
    unmatched_model: tuple[int, ...]
    method: str

    @property
    def num_matched(self) -> int:
        return int(self.external_indices.size)


def map_external_to_model(
    model,
    external: ExternalResult,
    *,
    by_id: bool = True,
    max_distance: float | None = None,
) -> ExternalNodeMap:
    """Map ``external`` nodes onto ``model`` nodes by label or nearest coordinate."""
    model_ids = np.array([node.id for node in model.nodes], dtype=np.int64)
    external_ids = np.asarray(external.node_ids, dtype=np.int64).reshape(-1)
    model_coords = np.asarray(model.coordinates, dtype=float)[:, :3]
    external_coords = np.asarray(external.coordinates, dtype=float)
    if external_coords.ndim == 1:
        external_coords = external_coords.reshape(-1, 1)
    if external_coords.shape[1] < 3:
        padded = np.zeros((external_coords.shape[0], 3), dtype=float)
        padded[:, : external_coords.shape[1]] = external_coords
        external_coords = padded

    if by_id:
        id_to_index = {int(node_id): index for index, node_id in enumerate(model_ids)}
        model_indices = np.full(external_ids.size, -1, dtype=np.intp)
        distances = np.zeros(external_ids.size, dtype=float)
        for index, node_id in enumerate(external_ids):
            mapped = id_to_index.get(int(node_id))
            if mapped is not None:
                model_indices[index] = mapped
                distances[index] = float(
                    np.linalg.norm(model_coords[mapped] - external_coords[index])
                )
        matched = model_indices >= 0
        if max_distance is not None:
            matched &= distances <= float(max_distance)
            model_indices[~matched] = -1
        external_indices = np.arange(external_ids.size, dtype=np.intp)[matched]
        model_node_indices = model_indices[matched]
        matched_distances = distances[matched]
        used_model = set(model_node_indices.tolist())
        unmatched_model = tuple(
            int(index) for index, node_id in enumerate(model_ids) if index not in used_model
        )
        unmatched_external = tuple(
            int(index) for index in range(external_ids.size) if index not in set(external_indices)
        )
        return ExternalNodeMap(
            model_node_indices=np.asarray(model_node_indices, dtype=np.intp),
            external_indices=np.asarray(external_indices, dtype=np.intp),
            distances=np.asarray(matched_distances, dtype=float),
            unmatched_external=unmatched_external,
            unmatched_model=unmatched_model,
            method="id",
        )

    nearest, distances = nearest_nodes(model_coords, external_coords)
    nearest = np.asarray(nearest, dtype=np.intp).reshape(-1)
    distances = np.asarray(distances, dtype=float).reshape(-1)
    if max_distance is not None:
        keep = distances <= float(max_distance)
        nearest = nearest[keep]
        distances = distances[keep]
        external_indices = np.nonzero(keep)[0].astype(np.intp)
    else:
        external_indices = np.arange(external_ids.size, dtype=np.intp)
    used_model = set(nearest.tolist())
    unmatched_model = tuple(
        int(index) for index in range(model_ids.size) if index not in used_model
    )
    matched_external = set(external_indices.tolist())
    unmatched_external = tuple(
        int(index) for index in range(external_ids.size) if index not in matched_external
    )
    return ExternalNodeMap(
        model_node_indices=nearest,
        external_indices=external_indices,
        distances=distances,
        unmatched_external=unmatched_external,
        unmatched_model=unmatched_model,
        method="nearest",
    )
