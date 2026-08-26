"""Assembly of the global stiffness and mass matrices.

Element contributions are accumulated in COO triplet form and converted to CSR
once, which is O(nnz) and avoids the quadratic cost of incremental sparse writes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp

from ..exceptions import ModelError

__all__ = ["AssembledSystem", "assemble_system", "assemble_stiffness", "assemble_mass"]


@dataclass
class AssembledSystem:
    """Global matrices plus the DOF partition used by the solvers.

    Attributes
    ----------
    K, M:
        Symmetric CSR matrices of size ``num_dofs x num_dofs`` spanning *all* DOFs.
    free_dofs, constrained_dofs:
        Index arrays partitioning the equations.
    """

    K: sp.csr_matrix
    M: sp.csr_matrix
    free_dofs: np.ndarray
    constrained_dofs: np.ndarray
    dof_labels: list[str] = field(default_factory=list)
    dof_types: np.ndarray | None = None
    model: object | None = None

    @property
    def num_dofs(self) -> int:
        return self.K.shape[0]

    @property
    def num_free_dofs(self) -> int:
        return int(self.free_dofs.size)

    def reduced(self) -> tuple[sp.csr_matrix, sp.csr_matrix]:
        """``(K_ff, M_ff)`` restricted to the free DOFs."""
        free = self.free_dofs
        if free.size == self.num_dofs:
            return self.K, self.M
        return (
            self.K[free, :][:, free].tocsr(),
            self.M[free, :][:, free].tocsr(),
        )

    def expand(self, values: np.ndarray) -> np.ndarray:
        """Scatter a free-DOF vector (or column-wise matrix) into full DOF space."""
        values = np.asarray(values, dtype=float)
        if values.shape[0] != self.num_free_dofs:
            raise ModelError(
                f"expected {self.num_free_dofs} free-DOF rows, got {values.shape[0]}"
            )
        if values.ndim == 1:
            full = np.zeros(self.num_dofs, dtype=float)
            full[self.free_dofs] = values
            return full
        full = np.zeros((self.num_dofs, values.shape[1]), dtype=float)
        full[self.free_dofs, :] = values
        return full

    @property
    def total_mass(self) -> float:
        """Sum of all mass matrix entries divided by the number of translational
        directions, i.e. the rigid-body translational mass of the model."""
        model = self.model
        ntrans = len(getattr(model, "translational_dofs", ())) or 1
        if self.dof_types is None:
            return float(self.M.sum()) / ntrans
        mask = np.asarray(self.dof_types) < 3
        sub = self.M[mask, :][:, mask]
        return float(sub.sum()) / ntrans


def _accumulate(model, matrix_getter) -> sp.csr_matrix:
    ndof = model.num_dofs
    rows: list[np.ndarray] = []
    cols: list[np.ndarray] = []
    data: list[np.ndarray] = []

    for element in model.elements:
        coords = model.node_coords(element.node_ids)
        local = np.asarray(matrix_getter(element, coords), dtype=float)
        dofs = element.global_dofs(model)
        if local.shape != (dofs.size, dofs.size):
            raise ModelError(
                f"{type(element).__name__} {element.node_ids} returned a "
                f"{local.shape} matrix but maps {dofs.size} DOFs"
            )
        if not local.any():
            continue
        rows.append(np.repeat(dofs, dofs.size))
        cols.append(np.tile(dofs, dofs.size))
        data.append(local.reshape(-1))

    if rows:
        matrix = sp.coo_matrix(
            (np.concatenate(data), (np.concatenate(rows), np.concatenate(cols))),
            shape=(ndof, ndof),
        )
    else:
        matrix = sp.coo_matrix((ndof, ndof), dtype=float)
    return matrix.tocsr()


def assemble_stiffness(model) -> sp.csr_matrix:
    """Assemble the global stiffness matrix ``K`` over all model DOFs."""
    return _accumulate(model, lambda e, c: e.stiffness_matrix(c))


def assemble_mass(model, *, include_point_masses: bool = True) -> sp.csr_matrix:
    """Assemble the global mass matrix ``M``, including concentrated masses."""
    matrix = _accumulate(model, lambda e, c: e.mass_matrix(c))
    if include_point_masses:
        diagonal = model.point_mass_vector()
        if diagonal.any():
            matrix = (matrix + sp.diags(diagonal, format="csr")).tocsr()
    return matrix


def assemble_system(model, *, include_point_masses: bool = True) -> AssembledSystem:
    """Assemble ``K`` and ``M`` and capture the free/constrained DOF partition."""
    if model.num_nodes == 0:
        raise ModelError("cannot assemble an empty model")
    if model.num_elements == 0 and not model.point_masses:
        raise ModelError("model has neither elements nor point masses")

    K = assemble_stiffness(model)
    M = assemble_mass(model, include_point_masses=include_point_masses)
    K = ((K + K.T) * 0.5).tocsr()
    M = ((M + M.T) * 0.5).tocsr()
    K.eliminate_zeros()
    M.eliminate_zeros()

    return AssembledSystem(
        K=K,
        M=M,
        free_dofs=model.free_dofs,
        constrained_dofs=model.constrained_dofs,
        dof_labels=model.dof_labels,
        dof_types=model.dof_types,
        model=model,
    )
