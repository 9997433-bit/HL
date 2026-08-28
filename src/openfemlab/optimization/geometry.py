"""Geometric (mesh-morph) stiffness derivatives for shape optimization."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import scipy.sparse as sp

from ..exceptions import OptimizationError

__all__ = [
    "assemble_shape_stiffness_derivatives",
    "elements_support_geometric_derivatives",
]


def elements_support_geometric_derivatives(model) -> bool:
    """True when every element exposes analytic ``stiffness_coord_derivatives``."""

    elements = list(getattr(model, "elements", ()))
    if not elements:
        return False
    return all(hasattr(element, "stiffness_coord_derivatives") for element in elements)


def assemble_shape_stiffness_derivatives(
    model,
    bases: Sequence[np.ndarray],
) -> list[sp.csr_matrix]:
    """Assemble full-DOF ``dK/da_j`` for morph bases ``V_j`` of shape ``(n_nodes, 3)``.

    Requires every element to implement ``stiffness_coord_derivatives(coords)``
    returning ``(ndof_e, ndof_e, n_nodes_e, ndim_local)``.  Only the model's
    active translational axes contribute; unused basis columns are ignored.
    """

    n_nodes = model.num_nodes
    n_dofs = model.num_dofs
    results: list[sp.csr_matrix] = []
    for basis in bases:
        field = np.asarray(basis, dtype=float)
        if field.shape != (n_nodes, 3):
            raise OptimizationError(
                f"shape basis has shape {field.shape}, expected ({n_nodes}, 3)"
            )
        rows: list[int] = []
        cols: list[int] = []
        data: list[float] = []
        for element in model.elements:
            coords = model.node_coords(element.node_ids)
            local = np.asarray(element.stiffness_coord_derivatives(coords), dtype=float)
            dofs = np.asarray(element.global_dofs(model), dtype=int)
            node_indices = [model.node(node_id).index for node_id in element.node_ids]
            ndim = local.shape[3]
            dK = np.zeros(local.shape[:2], dtype=float)
            for local_node, node_index in enumerate(node_indices):
                for axis in range(ndim):
                    velocity = float(field[node_index, axis])
                    if velocity == 0.0:
                        continue
                    dK += local[:, :, local_node, axis] * velocity
            flat = dK.reshape(-1)
            if not np.any(flat):
                continue
            rows.extend(np.repeat(dofs, dofs.size).tolist())
            cols.extend(np.tile(dofs, dofs.size).tolist())
            data.extend(flat.tolist())
        if not data:
            results.append(sp.csr_matrix((n_dofs, n_dofs), dtype=float))
            continue
        matrix = sp.coo_matrix((data, (rows, cols)), shape=(n_dofs, n_dofs)).tocsr()
        matrix = ((matrix + matrix.T) * 0.5).tocsr()
        matrix.eliminate_zeros()
        results.append(matrix)
    return results
