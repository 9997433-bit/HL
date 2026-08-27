"""Optional Rust-backed assembly kernels (GAP-13 spike)."""

from __future__ import annotations

import os

import numpy as np
import scipy.sparse as sp

from ..core.elements import TrussElement
from ..core.model import DOF

__all__ = [
    "assemble_truss_stiffness_rust",
    "rust_assembly_available",
    "use_rust_assembly",
]


def rust_assembly_available() -> bool:
    """Return whether the ``openfemlab_asm`` PyO3 extension is importable."""
    try:
        import openfemlab_asm  # noqa: F401
    except ImportError:
        return False
    return True


def use_rust_assembly() -> bool:
    """Return whether ``OPENFEMLAB_USE_RUST_ASM`` selects the Rust stiffness path."""
    value = os.environ.get("OPENFEMLAB_USE_RUST_ASM", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _is_all_truss_3d(model) -> bool:
    if model.num_elements == 0:
        return False
    if model.dofs != (DOF.UX, DOF.UY, DOF.UZ):
        return False
    return all(isinstance(element, TrussElement) for element in model.elements)


def assemble_truss_stiffness_rust(model) -> sp.csr_matrix | None:
    """Assemble ``K`` for an all-``TrussElement`` 3D model via ``openfemlab_asm``.

    Returns ``None`` when the extension is absent or the model is outside the
    supported subset.
    """
    if not rust_assembly_available() or not _is_all_truss_3d(model):
        return None

    import openfemlab_asm

    node_index = {node.id: node.index for node in model.nodes}
    connectivity = np.empty((model.num_elements, 2), dtype=np.int64)
    axial = np.empty((model.num_elements, 1), dtype=float)
    for index, element in enumerate(model.elements):
        connectivity[index, 0] = node_index[element.node_ids[0]]
        connectivity[index, 1] = node_index[element.node_ids[1]]
        axial[index, 0] = element.axial_rigidity

    dof_indices = np.empty((model.num_nodes, 3), dtype=np.int64)
    for node in model.nodes:
        dof_indices[node.index, 0] = model.dof_index(node.id, DOF.UX)
        dof_indices[node.index, 1] = model.dof_index(node.id, DOF.UY)
        dof_indices[node.index, 2] = model.dof_index(node.id, DOF.UZ)

    rows, cols, data = openfemlab_asm.assemble_rod2_stiffness(
        model.coordinates,
        connectivity,
        axial,
        dof_indices,
    )
    shape = (model.num_dofs, model.num_dofs)
    matrix = sp.coo_matrix((data, (rows, cols)), shape=shape).tocsr()
    matrix.eliminate_zeros()
    return ((matrix + matrix.T) * 0.5).tocsr()
