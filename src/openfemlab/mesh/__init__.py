"""Mesh layer (L1): geometry generators and spatial queries.

Round 1 contract; implementations land in Round 2:

- ``make_line_mesh(length, n_elem)`` — 1-D beam/rod discretization.
- ``make_grid_mesh(lx, ly, nx, ny)`` — structured quad plate mesh.
- ``nearest_nodes(model_coords, points)`` — KD-tree sensor-to-node matching
  (``scipy.spatial.cKDTree``), used by correlation geometry alignment.

Anything beyond generation/queries (element formulations, DOF assignment)
belongs to ``solver``.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from .simple import MeshBuilder, bar_mesh, beam_mesh, spring_mass_chain, truss_from_arrays

__all__ = [
    "nearest_nodes",
    "MeshBuilder",
    "spring_mass_chain",
    "bar_mesh",
    "beam_mesh",
    "truss_from_arrays",
]


def nearest_nodes(
    coords: npt.NDArray[np.float64],
    points: npt.NDArray[np.float64],
) -> tuple[npt.NDArray[np.intp], npt.NDArray[np.float64]]:
    """Nearest model node for each query point.

    Parameters
    ----------
    coords:
        Model node coordinates, shape ``(n_nodes, 3)``.
    points:
        Query points (e.g. sensor locations), shape ``(n_pts, 3)``.

    Returns
    -------
    ``(indices, distances)`` — row indices into ``coords`` and Euclidean
    distances, both shape ``(n_pts,)``.
    """
    from scipy.spatial import cKDTree

    tree = cKDTree(np.asarray(coords, dtype=np.float64))
    distances, indices = tree.query(np.asarray(points, dtype=np.float64))
    return np.asarray(indices, dtype=np.intp), np.asarray(distances, dtype=np.float64)
