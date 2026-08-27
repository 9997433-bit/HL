"""Assembly of the global stiffness and mass matrices.

Element contributions are accumulated in COO triplet form and converted to CSR
once, which is O(nnz) and avoids the quadratic cost of incremental sparse writes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp

from ..exceptions import ModelError
from .mpc import MpcReduction, build_rbe2_reduction, mpc_free_dofs

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
    mpc: MpcReduction | None = None

    @property
    def num_dofs(self) -> int:
        return self.K.shape[0]

    @property
    def num_full_dofs(self) -> int:
        if self.mpc is None:
            return self.num_dofs
        return int(self.mpc.T.shape[0])

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
        if self.mpc is None:
            if values.ndim == 1:
                full = np.zeros(self.num_dofs, dtype=float)
                full[self.free_dofs] = values
                return full
            full = np.zeros((self.num_dofs, values.shape[1]), dtype=float)
            full[self.free_dofs, :] = values
            return full

        if values.ndim == 1:
            retained = np.zeros(self.num_dofs, dtype=float)
            retained[self.free_dofs] = values
            return self.mpc.to_full(retained)
        retained = np.zeros((self.num_dofs, values.shape[1]), dtype=float)
        retained[self.free_dofs, :] = values
        return np.asarray(self.mpc.T @ retained, dtype=float)

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


def _assemble_elements(
    model,
    *,
    stiffness: bool,
    mass: bool,
) -> tuple[sp.csr_matrix | None, sp.csr_matrix | None]:
    """Assemble requested element matrices in one topology traversal.

    The triplet buffers are allocated once from the bound element DOF counts.
    When both matrices are requested, row/column indices, coordinates and global
    DOF maps are shared by ``K`` and ``M``.  This avoids the list-of-small-arrays
    and duplicate element traversal costs that dominate assembly for large meshes
    of low-order elements.
    """
    if stiffness:
        from ..accel.assembly_rust import assemble_truss_stiffness_rust, use_rust_assembly

        if use_rust_assembly() and not getattr(model, "rbe2_ties", ()):
            rust_stiffness = assemble_truss_stiffness_rust(model)
            if rust_stiffness is not None:
                if not mass:
                    return rust_stiffness, None
                _, mass_matrix = _assemble_elements(model, stiffness=False, mass=True)
                return rust_stiffness, mass_matrix

    elements = model.elements
    counts = np.fromiter(
        (element.num_dofs**2 for element in elements),
        dtype=np.intp,
        count=len(elements),
    )
    offsets = np.empty(len(elements) + 1, dtype=np.intp)
    offsets[0] = 0
    np.cumsum(counts, out=offsets[1:])

    rows = np.empty(int(offsets[-1]), dtype=np.intp)
    cols = np.empty_like(rows)
    stiffness_data = np.empty(rows.size, dtype=float) if stiffness else None
    mass_data = np.empty(rows.size, dtype=float) if mass else None

    for index, element in enumerate(elements):
        dofs = element.global_dofs(model)
        coords = model.node_coords(element.node_ids)
        start, stop = int(offsets[index]), int(offsets[index + 1])
        expected = (dofs.size, dofs.size)
        rows[start:stop] = np.repeat(dofs, dofs.size)
        cols[start:stop] = np.tile(dofs, dofs.size)

        if stiffness_data is not None:
            local_stiffness = np.asarray(element.stiffness_matrix(coords), dtype=float)
            if local_stiffness.shape != expected:
                raise ModelError(
                    f"{type(element).__name__} {element.node_ids} returned a "
                    f"{local_stiffness.shape} stiffness matrix but maps {dofs.size} DOFs"
                )
            stiffness_data[start:stop] = local_stiffness.reshape(-1)

        if mass_data is not None:
            local_mass = np.asarray(element.mass_matrix(coords), dtype=float)
            if local_mass.shape != expected:
                raise ModelError(
                    f"{type(element).__name__} {element.node_ids} returned a "
                    f"{local_mass.shape} mass matrix but maps {dofs.size} DOFs"
                )
            mass_data[start:stop] = local_mass.reshape(-1)

    shape = (model.num_dofs, model.num_dofs)

    def to_csr(data: np.ndarray | None) -> sp.csr_matrix | None:
        if data is None:
            return None
        if not np.any(data):
            return sp.csr_matrix(shape, dtype=float)
        matrix = sp.coo_matrix((data, (rows, cols)), shape=shape).tocsr()
        matrix.eliminate_zeros()
        return matrix

    return to_csr(stiffness_data), to_csr(mass_data)


def assemble_stiffness(model) -> sp.csr_matrix:
    """Assemble the global stiffness matrix ``K`` over all model DOFs."""
    matrix, _ = _assemble_elements(model, stiffness=True, mass=False)
    assert matrix is not None
    return matrix


def assemble_mass(model, *, include_point_masses: bool = True) -> sp.csr_matrix:
    """Assemble the global mass matrix ``M``, including concentrated masses."""
    _, matrix = _assemble_elements(model, stiffness=False, mass=True)
    assert matrix is not None
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

    K, M = _assemble_elements(model, stiffness=True, mass=True)
    assert K is not None and M is not None
    if include_point_masses:
        diagonal = model.point_mass_vector()
        if diagonal.any():
            M = (M + sp.diags(diagonal, format="csr")).tocsr()
    K = ((K + K.T) * 0.5).tocsr()
    M = ((M + M.T) * 0.5).tocsr()
    K.eliminate_zeros()
    M.eliminate_zeros()

    mpc = build_rbe2_reduction(model, model.rbe2_ties)
    if mpc is not None:
        K = mpc.reduce(K)
        M = mpc.reduce(M)
        free_dofs = mpc_free_dofs(model, mpc)
        constrained_dofs = np.setdiff1d(np.arange(K.shape[0], dtype=int), free_dofs)
    else:
        free_dofs = model.free_dofs
        constrained_dofs = model.constrained_dofs

    return AssembledSystem(
        K=K,
        M=M,
        free_dofs=free_dofs,
        constrained_dofs=constrained_dofs,
        dof_labels=model.dof_labels,
        dof_types=model.dof_types,
        model=model,
        mpc=mpc,
    )
