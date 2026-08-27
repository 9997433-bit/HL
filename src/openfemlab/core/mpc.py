"""Multi-point constraints for rigid kinematic ties (Nastran RBE2).

An :class:`RBE2Tie` couples dependent (slave) nodal DOFs to an independent
(master) node through exact rigid-body kinematics.  The constraint is applied
by a sparse transformation ``u = T u_r`` so that

    K_r = T^T K T,    M_r = T^T M T

before the usual free/constrained DOF partition is taken.
"""

from __future__ import annotations

from collections.abc import Hashable, Sequence
from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp

from ..exceptions import ModelError
from .model import DOF

__all__ = [
    "MpcReduction",
    "RBE2Tie",
    "build_rbe2_reduction",
    "parse_nastran_components",
]


_NastranComponentMap: dict[int, DOF] = {
    1: DOF.UX,
    2: DOF.UY,
    3: DOF.UZ,
    4: DOF.RX,
    5: DOF.RY,
    6: DOF.RZ,
}


def parse_nastran_components(cm: str | int) -> tuple[DOF, ...]:
    """Parse a Nastran ``CM`` field such as ``123456`` into :class:`DOF` members."""

    text = str(cm).strip()
    if not text.isdigit():
        raise ModelError(f"RBE2 CM field {cm!r} must be a digit string such as '123456'")
    seen: list[DOF] = []
    used: set[DOF] = set()
    for char in text:
        digit = int(char)
        if digit not in _NastranComponentMap:
            raise ModelError(f"RBE2 CM digit {digit} is outside the 1..6 range")
        dof = _NastranComponentMap[digit]
        if dof not in used:
            seen.append(dof)
            used.add(dof)
    if not seen:
        raise ModelError("RBE2 CM field is empty")
    return tuple(seen)


@dataclass(frozen=True)
class RBE2Tie:
    """One Nastran-style RBE2 rigid link."""

    master: Hashable
    slaves: tuple[Hashable, ...]
    components: tuple[DOF, ...]
    eid: Hashable | None = None


@dataclass(frozen=True)
class MpcReduction:
    """Sparse kinematic map from retained DOFs back to the full model space."""

    T: sp.csr_matrix
    retained: np.ndarray

    @property
    def num_retained(self) -> int:
        return int(self.retained.size)

    def reduce(self, matrix: sp.csr_matrix) -> sp.csr_matrix:
        reduced = self.T.T @ matrix @ self.T
        reduced = ((reduced + reduced.T) * 0.5).tocsr()
        reduced.eliminate_zeros()
        return reduced

    def to_full(self, retained_values: np.ndarray) -> np.ndarray:
        vector = np.asarray(retained_values, dtype=float)
        if vector.ndim != 1:
            raise ModelError("MPC recovery expects a 1-D retained vector")
        if vector.size != self.num_retained:
            raise ModelError(
                f"expected {self.num_retained} retained DOFs, got {vector.size}"
            )
        return np.asarray(self.T @ vector, dtype=float).reshape(-1)


def build_rbe2_reduction(model, ties: Sequence[RBE2Tie]) -> MpcReduction | None:
    """Build the RBE2 transformation for ``model``; ``None`` when ``ties`` is empty."""

    if not ties:
        return None

    num_dofs = model.num_dofs
    constrained = set(int(i) for i in model.constrained_dofs)
    dependent_rows: dict[int, dict[int, float]] = {}

    for tie in ties:
        if tie.master not in model._nodes:
            raise ModelError(f"RBE2 master node {tie.master!r} is not in the model")
        for slave in tie.slaves:
            if slave not in model._nodes:
                raise ModelError(f"RBE2 slave node {slave!r} is not in the model")
            if slave == tie.master:
                raise ModelError(f"RBE2 {tie.eid or ''}: master and slave cannot coincide")
            for component in tie.components:
                if not model.has_dof(component):
                    continue
                dep = model.dof_index(slave, component)
                if dep in constrained:
                    raise ModelError(
                        f"RBE2 ties DOF {model.describe_dof(dep)[0]!r}:"
                        f"{component.name} but that DOF is already constrained"
                    )
                if dep in dependent_rows:
                    raise ModelError(
                        f"DOF {model.describe_dof(dep)[0]!r}:{component.name} is tied by "
                        "more than one RBE2"
                    )
                dependent_rows[dep] = _rbe2_row(model, tie.master, slave, component)

    retained = np.array(
        [index for index in range(num_dofs) if index not in dependent_rows],
        dtype=int,
    )
    retained_map = {int(full): column for column, full in enumerate(retained)}

    rows: list[int] = []
    cols: list[int] = []
    data: list[float] = []
    for column, full in enumerate(retained):
        rows.append(int(full))
        cols.append(column)
        data.append(1.0)

    for dep, coefficients in dependent_rows.items():
        for master_dof, weight in coefficients.items():
            if master_dof in dependent_rows:
                raise ModelError(
                    "chained RBE2 ties are not supported: a master DOF is itself dependent"
                )
            try:
                column = retained_map[int(master_dof)]
            except KeyError as exc:
                raise ModelError(
                    f"RBE2 references DOF index {master_dof}, which was eliminated"
                ) from exc
            rows.append(int(dep))
            cols.append(column)
            data.append(float(weight))

    transform = sp.coo_matrix((data, (rows, cols)), shape=(num_dofs, retained.size)).tocsr()
    return MpcReduction(T=transform, retained=retained)


def mpc_free_dofs(model, reduction: MpcReduction) -> np.ndarray:
    """Free retained-DOF indices after RBE2 elimination and explicit constraints."""

    constrained = set(int(i) for i in model.constrained_dofs)
    free = [column for column, full in enumerate(reduction.retained) if full not in constrained]
    return np.asarray(free, dtype=int)


def _rbe2_row(model, master_id: Hashable, slave_id: Hashable, component: DOF) -> dict[int, float]:
    """Coefficients ``u_slave,comp = sum alpha_i u_i`` in full-DOF indexing."""

    master = model.node(master_id)
    slave = model.node(slave_id)
    dx = slave.x - master.x
    dy = slave.y - master.y
    dz = slave.z - master.z

    coefficients: dict[int, float] = {}
    if component.is_rotational:
        coefficients[model.dof_index(master_id, component)] = 1.0
        return coefficients

    coefficients[model.dof_index(master_id, component)] = 1.0
    if component is DOF.UX:
        if model.has_dof(DOF.RY):
            coefficients[model.dof_index(master_id, DOF.RY)] = dz
        if model.has_dof(DOF.RZ):
            coefficients[model.dof_index(master_id, DOF.RZ)] = -dy
    elif component is DOF.UY:
        if model.has_dof(DOF.RX):
            coefficients[model.dof_index(master_id, DOF.RX)] = -dz
        if model.has_dof(DOF.RZ):
            coefficients[model.dof_index(master_id, DOF.RZ)] = dx
    elif component is DOF.UZ:
        if model.has_dof(DOF.RX):
            coefficients[model.dof_index(master_id, DOF.RX)] = dy
        if model.has_dof(DOF.RY):
            coefficients[model.dof_index(master_id, DOF.RY)] = -dx
    return coefficients
