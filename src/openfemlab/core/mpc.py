"""Multi-point constraints for Nastran RBE2 / RBE3 kinematic ties.

An :class:`RBE2Tie` couples dependent (slave) nodal DOFs to an independent
(master) node through exact rigid-body kinematics.  An :class:`RBE3Tie`
expresses a dependent reference node as a weighted average of independent
grid DOFs (the common industrial load-distribution form).

Both are applied by a sparse transformation ``u = T u_r`` so that

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
    "RBE3Group",
    "RBE3Tie",
    "build_mpc_reduction",
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
    """Parse a Nastran ``CM`` / ``REFC`` / ``C`` field such as ``123456``."""

    text = str(cm).strip()
    if not text.isdigit():
        raise ModelError(f"Nastran component field {cm!r} must be a digit string such as '123456'")
    seen: list[DOF] = []
    used: set[DOF] = set()
    for char in text:
        digit = int(char)
        if digit not in _NastranComponentMap:
            raise ModelError(f"Nastran component digit {digit} is outside the 1..6 range")
        dof = _NastranComponentMap[digit]
        if dof not in used:
            seen.append(dof)
            used.add(dof)
    if not seen:
        raise ModelError("Nastran component field is empty")
    return tuple(seen)


@dataclass(frozen=True)
class RBE2Tie:
    """One Nastran-style RBE2 rigid link (master → slaves)."""

    master: Hashable
    slaves: tuple[Hashable, ...]
    components: tuple[DOF, ...]
    eid: Hashable | None = None


@dataclass(frozen=True)
class RBE3Group:
    """One independent weight / component / grid list inside an RBE3."""

    weight: float
    components: tuple[DOF, ...]
    independents: tuple[Hashable, ...]


@dataclass(frozen=True)
class RBE3Tie:
    """One Nastran-style RBE3 interpolation element (independents → dependent)."""

    dependent: Hashable
    dependent_components: tuple[DOF, ...]
    groups: tuple[RBE3Group, ...]
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
    """Build the RBE2-only transformation; prefer :func:`build_mpc_reduction`."""

    return build_mpc_reduction(model, rbe2_ties=ties, rbe3_ties=())


def build_mpc_reduction(
    model,
    *,
    rbe2_ties: Sequence[RBE2Tie] = (),
    rbe3_ties: Sequence[RBE3Tie] = (),
) -> MpcReduction | None:
    """Build the combined RBE2/RBE3 transformation; ``None`` when both are empty."""

    if not rbe2_ties and not rbe3_ties:
        return None

    num_dofs = model.num_dofs
    constrained = set(int(i) for i in model.constrained_dofs)
    dependent_rows: dict[int, dict[int, float]] = {}

    for tie in rbe2_ties:
        _register_rbe2(model, tie, constrained, dependent_rows)
    for tie in rbe3_ties:
        _register_rbe3(model, tie, constrained, dependent_rows)

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
                    "chained MPC ties are not supported: a retained DOF is itself dependent"
                )
            try:
                column = retained_map[int(master_dof)]
            except KeyError as exc:
                raise ModelError(
                    f"MPC references DOF index {master_dof}, which was eliminated"
                ) from exc
            rows.append(int(dep))
            cols.append(column)
            data.append(float(weight))

    transform = sp.coo_matrix((data, (rows, cols)), shape=(num_dofs, retained.size)).tocsr()
    return MpcReduction(T=transform, retained=retained)


def mpc_free_dofs(model, reduction: MpcReduction) -> np.ndarray:
    """Free retained-DOF indices after MPC elimination and explicit constraints."""

    constrained = set(int(i) for i in model.constrained_dofs)
    free = [column for column, full in enumerate(reduction.retained) if full not in constrained]
    return np.asarray(free, dtype=int)


def _register_rbe2(
    model,
    tie: RBE2Tie,
    constrained: set[int],
    dependent_rows: dict[int, dict[int, float]],
) -> None:
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
            _claim_dependent(model, dep, component, constrained, dependent_rows, kind="RBE2")
            dependent_rows[dep] = _rbe2_row(model, tie.master, slave, component)


def _register_rbe3(
    model,
    tie: RBE3Tie,
    constrained: set[int],
    dependent_rows: dict[int, dict[int, float]],
) -> None:
    if tie.dependent not in model._nodes:
        raise ModelError(f"RBE3 dependent node {tie.dependent!r} is not in the model")
    if not tie.groups:
        raise ModelError(f"RBE3 {tie.eid or ''} has no independent groups")

    for group in tie.groups:
        if group.weight <= 0.0:
            raise ModelError(f"RBE3 {tie.eid or ''}: weight must be positive")
        if not group.independents:
            raise ModelError(f"RBE3 {tie.eid or ''}: an independent group is empty")
        for node_id in group.independents:
            if node_id not in model._nodes:
                raise ModelError(f"RBE3 independent node {node_id!r} is not in the model")
            if node_id == tie.dependent:
                raise ModelError(
                    f"RBE3 {tie.eid or ''}: dependent and independent nodes cannot coincide"
                )

    for component in tie.dependent_components:
        if not model.has_dof(component):
            continue
        dep = model.dof_index(tie.dependent, component)
        _claim_dependent(model, dep, component, constrained, dependent_rows, kind="RBE3")
        coefficients: dict[int, float] = {}
        total_weight = 0.0
        for group in tie.groups:
            if component not in group.components:
                continue
            if not model.has_dof(component):
                continue
            for node_id in group.independents:
                index = model.dof_index(node_id, component)
                coefficients[index] = coefficients.get(index, 0.0) + float(group.weight)
                total_weight += float(group.weight)
        if total_weight <= 0.0:
            raise ModelError(
                f"RBE3 {tie.eid or ''}: dependent {component.name} has no matching "
                "independent components"
            )
        dependent_rows[dep] = {
            index: weight / total_weight for index, weight in coefficients.items()
        }


def _claim_dependent(
    model,
    dep: int,
    component: DOF,
    constrained: set[int],
    dependent_rows: dict[int, dict[int, float]],
    *,
    kind: str,
) -> None:
    if dep in constrained:
        raise ModelError(
            f"{kind} ties DOF {model.describe_dof(dep)[0]!r}:{component.name} "
            "but that DOF is already constrained"
        )
    if dep in dependent_rows:
        raise ModelError(
            f"DOF {model.describe_dof(dep)[0]!r}:{component.name} is tied by more than one MPC"
        )


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
