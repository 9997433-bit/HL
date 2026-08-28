"""Finite element model container: nodes, DOF bookkeeping, supports and point masses.

This is the *internal solver* model: it owns nodes, bound elements, constraints
and the global DOF numbering. The flat interchange representation used by the io
layer lives in :mod:`openfemlab.core.neutral`.

The DOF layout is *node major*: for a model whose DOF signature is
``(UX, UY, RZ)`` the global equation number of node ``i`` (insertion order) is

    dof_index = i * ndof_per_node + local_position_of_dof

which keeps the assembled matrices tightly banded for chain/line meshes.
"""

from __future__ import annotations

from collections.abc import Hashable, Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from enum import IntEnum

import numpy as np

from ..exceptions import ModelError

__all__ = [
    "DOF",
    "TRANSLATIONAL_DOFS",
    "ROTATIONAL_DOFS",
    "Material",
    "Section",
    "Node",
    "Model",
]


class DOF(IntEnum):
    """Nodal degree of freedom identifiers.

    The integer value of the three translational members doubles as the index of
    the associated Cartesian coordinate axis, which the elements rely on when
    they extract direction cosines from the nodal coordinates.
    """

    UX = 0
    UY = 1
    UZ = 2
    RX = 3
    RY = 4
    RZ = 5

    @classmethod
    def parse(cls, value: DOF | str | int) -> DOF:
        """Coerce ``value`` (enum member, name such as ``"ux"``, or index) to a :class:`DOF`."""
        if isinstance(value, DOF):
            return value
        if isinstance(value, str):
            try:
                return cls[value.strip().upper()]
            except KeyError as exc:
                raise ModelError(
                    f"unknown DOF name {value!r}; expected one of {[d.name for d in cls]}"
                ) from exc
        if isinstance(value, (int, np.integer)):
            try:
                return cls(int(value))
            except ValueError as exc:
                raise ModelError(f"unknown DOF index {value!r}") from exc
        raise ModelError(f"cannot interpret {value!r} as a DOF")

    @property
    def is_translational(self) -> bool:
        return self.value < 3

    @property
    def is_rotational(self) -> bool:
        return self.value >= 3


TRANSLATIONAL_DOFS: tuple[DOF, ...] = (DOF.UX, DOF.UY, DOF.UZ)
ROTATIONAL_DOFS: tuple[DOF, ...] = (DOF.RX, DOF.RY, DOF.RZ)


def _parse_dofs(dofs: Iterable[DOF | str | int] | DOF | str | int) -> tuple[DOF, ...]:
    if isinstance(dofs, (DOF, str, int, np.integer)):
        dofs = [dofs]
    parsed = tuple(DOF.parse(d) for d in dofs)
    if len(set(parsed)) != len(parsed):
        raise ModelError(f"duplicate DOF in {[d.name for d in parsed]}")
    return parsed


@dataclass(frozen=True)
class Material:
    """Linear elastic, isotropic material.

    Parameters
    ----------
    E:
        Young's modulus (consistent units, e.g. Pa).
    density:
        Mass density (e.g. kg/m^3). ``0`` yields a massless element, which is a
        legitimate modelling choice when all inertia is carried by point masses.
    nu:
        Poisson's ratio, used only to derive the shear modulus.
    """

    E: float
    density: float = 0.0
    nu: float = 0.3
    name: str = ""

    def __post_init__(self) -> None:
        if self.E <= 0.0:
            raise ModelError(f"Young's modulus must be positive, got {self.E}")
        if self.density < 0.0:
            raise ModelError(f"density must be non-negative, got {self.density}")
        if not -1.0 < self.nu < 0.5:
            raise ModelError(f"Poisson's ratio must lie in (-1, 0.5), got {self.nu}")

    @property
    def shear_modulus(self) -> float:
        return self.E / (2.0 * (1.0 + self.nu))


@dataclass(frozen=True)
class Section:
    """Beam/bar cross section properties."""

    area: float
    inertia_z: float = 0.0
    inertia_y: float = 0.0
    torsion_constant: float = 0.0
    name: str = ""

    def __post_init__(self) -> None:
        if self.area <= 0.0:
            raise ModelError(f"section area must be positive, got {self.area}")
        for label in ("inertia_z", "inertia_y", "torsion_constant"):
            if getattr(self, label) < 0.0:
                raise ModelError(f"section {label} must be non-negative")


@dataclass(frozen=True)
class Node:
    """A mesh node with a stable insertion index used for DOF numbering."""

    id: Hashable
    coords: np.ndarray
    index: int

    def __post_init__(self) -> None:
        coords = np.asarray(self.coords, dtype=float).reshape(-1)
        if coords.size > 3:
            raise ModelError(f"node {self.id!r}: expected at most 3 coordinates, got {coords.size}")
        padded = np.zeros(3, dtype=float)
        padded[: coords.size] = coords
        object.__setattr__(self, "coords", padded)

    @property
    def x(self) -> float:
        return float(self.coords[0])

    @property
    def y(self) -> float:
        return float(self.coords[1])

    @property
    def z(self) -> float:
        return float(self.coords[2])


@dataclass
class Model:
    """Container for nodes, elements, supports and concentrated masses.

    Parameters
    ----------
    dofs:
        Active DOF signature applied to every node, e.g. ``("UX",)`` for an axial
        chain, ``("UX", "UY")`` for a planar truss or ``("UX", "UY", "RZ")`` for a
        planar frame.
    name:
        Free-form model label.
    """

    dofs: tuple[DOF, ...] = TRANSLATIONAL_DOFS
    name: str = "model"
    _nodes: dict[Hashable, Node] = field(default_factory=dict, init=False, repr=False)
    _elements: list = field(default_factory=list, init=False, repr=False)
    _constrained: set[int] = field(default_factory=set, init=False, repr=False)
    _point_masses: dict[int, float] = field(default_factory=dict, init=False, repr=False)
    _rbe2_ties: list = field(default_factory=list, init=False, repr=False)
    _rbe3_ties: list = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        self.dofs = _parse_dofs(self.dofs)
        if not self.dofs:
            raise ModelError("a model needs at least one active DOF")
        self._dof_position = {dof: i for i, dof in enumerate(self.dofs)}

    # ------------------------------------------------------------------ DOFs

    @property
    def ndof_per_node(self) -> int:
        return len(self.dofs)

    @property
    def num_nodes(self) -> int:
        return len(self._nodes)

    @property
    def num_elements(self) -> int:
        return len(self._elements)

    @property
    def num_dofs(self) -> int:
        return self.num_nodes * self.ndof_per_node

    @property
    def translational_dofs(self) -> tuple[DOF, ...]:
        return tuple(d for d in self.dofs if d.is_translational)

    @property
    def rotational_dofs(self) -> tuple[DOF, ...]:
        return tuple(d for d in self.dofs if d.is_rotational)

    def has_dof(self, dof: DOF | str | int) -> bool:
        return DOF.parse(dof) in self._dof_position

    def dof_index(self, node_id: Hashable, dof: DOF | str | int) -> int:
        """Global equation number of ``dof`` at ``node_id``."""
        node = self.node(node_id)
        parsed = DOF.parse(dof)
        try:
            offset = self._dof_position[parsed]
        except KeyError as exc:
            raise ModelError(
                f"DOF {parsed.name} is not active in model {self.name!r} "
                f"(active: {[d.name for d in self.dofs]})"
            ) from exc
        return node.index * self.ndof_per_node + offset

    def dof_indices(self, node_id: Hashable) -> np.ndarray:
        """All global equation numbers of ``node_id`` in model DOF order."""
        base = self.node(node_id).index * self.ndof_per_node
        return np.arange(base, base + self.ndof_per_node, dtype=int)

    @property
    def dof_types(self) -> np.ndarray:
        """Array of length ``num_dofs`` holding the :class:`DOF` code of each equation."""
        codes = np.array([int(d) for d in self.dofs], dtype=int)
        return np.tile(codes, self.num_nodes)

    @property
    def dof_labels(self) -> list[str]:
        return [f"{node.id}:{dof.name}" for node in self.nodes for dof in self.dofs]

    def describe_dof(self, index: int) -> tuple[Hashable, DOF]:
        """Inverse of :meth:`dof_index`: map an equation number to ``(node_id, dof)``."""
        if not 0 <= index < self.num_dofs:
            raise ModelError(f"DOF index {index} out of range [0, {self.num_dofs})")
        node_index, offset = divmod(int(index), self.ndof_per_node)
        return self.nodes[node_index].id, self.dofs[offset]

    # ----------------------------------------------------------------- nodes

    def add_node(self, node_id: Hashable, *coords) -> Node:
        """Register a node. Coordinates may be passed as scalars or one sequence."""
        if node_id in self._nodes:
            raise ModelError(f"duplicate node id {node_id!r}")
        if len(coords) == 1 and isinstance(coords[0], (Sequence, np.ndarray)):
            values = np.asarray(coords[0], dtype=float).reshape(-1)
        else:
            values = np.asarray(coords, dtype=float).reshape(-1)
        node = Node(id=node_id, coords=values, index=len(self._nodes))
        self._nodes[node_id] = node
        return node

    def add_nodes(self, items: Iterable[tuple]) -> list[Node]:
        """Bulk helper: ``add_nodes([(1, 0.0, 0.0), (2, 1.0, 0.0)])``."""
        return [self.add_node(item[0], *item[1:]) for item in items]

    def node(self, node_id: Hashable) -> Node:
        try:
            return self._nodes[node_id]
        except KeyError as exc:
            raise ModelError(f"unknown node id {node_id!r}") from exc

    @property
    def nodes(self) -> list[Node]:
        """Nodes in insertion (= DOF numbering) order."""
        return list(self._nodes.values())

    @property
    def node_ids(self) -> list[Hashable]:
        return list(self._nodes.keys())

    @property
    def coordinates(self) -> np.ndarray:
        """``(num_nodes, 3)`` array of nodal coordinates in DOF numbering order."""
        if not self._nodes:
            return np.zeros((0, 3), dtype=float)
        return np.vstack([node.coords for node in self._nodes.values()])

    def node_coords(self, node_ids: Sequence[Hashable]) -> np.ndarray:
        return np.vstack([self.node(nid).coords for nid in node_ids])

    # -------------------------------------------------------------- elements

    def add_element(self, element):
        """Attach an element, validating its nodes and resolving its DOF signature."""
        for node_id in element.node_ids:
            self.node(node_id)  # raises for unknown ids
        element.bind(self.dofs)
        self._elements.append(element)
        return element

    def add_elements(self, elements: Iterable) -> list:
        return [self.add_element(e) for e in elements]

    @property
    def elements(self) -> list:
        return list(self._elements)

    def __iter__(self) -> Iterator:
        return iter(self._elements)

    # ---------------------------------------------------- boundary conditions

    def fix(self, node_id: Hashable, dofs=None) -> None:
        """Constrain (set to zero) the given DOFs of ``node_id``; all of them by default."""
        targets = self.dofs if dofs is None else _parse_dofs(dofs)
        for dof in targets:
            self._constrained.add(self.dof_index(node_id, dof))

    def fix_nodes(self, node_ids: Iterable[Hashable], dofs=None) -> None:
        for node_id in node_ids:
            self.fix(node_id, dofs)

    def fix_dof_globally(self, dofs) -> None:
        """Constrain a DOF direction on every node (e.g. suppress out-of-plane motion)."""
        for node_id in self._nodes:
            self.fix(node_id, dofs)

    def release(self, node_id: Hashable, dofs=None) -> None:
        """Undo :meth:`fix` for the given DOFs."""
        targets = self.dofs if dofs is None else _parse_dofs(dofs)
        for dof in targets:
            self._constrained.discard(self.dof_index(node_id, dof))

    def is_constrained(self, node_id: Hashable, dof) -> bool:
        return self.dof_index(node_id, dof) in self._constrained

    @property
    def constrained_dofs(self) -> np.ndarray:
        return np.array(sorted(self._constrained), dtype=int)

    @property
    def free_dofs(self) -> np.ndarray:
        mask = np.ones(self.num_dofs, dtype=bool)
        if self._constrained:
            mask[self.constrained_dofs] = False
        return np.flatnonzero(mask)

    # ---------------------------------------------------------- MPC / RBE2

    @property
    def rbe2_ties(self) -> tuple:
        """Registered :class:`~openfemlab.core.mpc.RBE2Tie` instances."""
        return tuple(self._rbe2_ties)

    @property
    def rbe3_ties(self) -> tuple:
        """Registered :class:`~openfemlab.core.mpc.RBE3Tie` instances."""
        return tuple(self._rbe3_ties)

    def tie_rbe2(
        self,
        master: Hashable,
        slaves: Iterable[Hashable],
        *,
        components: Iterable[DOF | str | int] | None = None,
        eid: Hashable | None = None,
    ):
        """Register a Nastran-style RBE2 rigid link on ``master``."""
        from .mpc import RBE2Tie

        slave_tuple = tuple(slaves)
        if not slave_tuple:
            raise ModelError("RBE2 requires at least one slave node")
        if components is None:
            tied = self.dofs
        else:
            tied = _parse_dofs(components)
        tie = RBE2Tie(master=master, slaves=slave_tuple, components=tied, eid=eid)
        self._rbe2_ties.append(tie)
        return tie

    def tie_rbe3(
        self,
        dependent: Hashable,
        independents: Iterable[Hashable],
        *,
        components: Iterable[DOF | str | int] | None = None,
        weight: float = 1.0,
        independent_components: Iterable[DOF | str | int] | None = None,
        eid: Hashable | None = None,
    ):
        """Register a Nastran-style RBE3 weighted interpolation on ``dependent``.

        The single-group form expresses each dependent component as the average
        of the same component on ``independents`` (weight ``weight``).
        """
        from .mpc import RBE3Group, RBE3Tie

        independent_tuple = tuple(independents)
        if not independent_tuple:
            raise ModelError("RBE3 requires at least one independent node")
        if weight <= 0.0:
            raise ModelError("RBE3 weight must be positive")
        dependent_dofs = self.dofs if components is None else _parse_dofs(components)
        independent_dofs = (
            dependent_dofs
            if independent_components is None
            else _parse_dofs(independent_components)
        )
        tie = RBE3Tie(
            dependent=dependent,
            dependent_components=dependent_dofs,
            groups=(
                RBE3Group(
                    weight=float(weight),
                    components=independent_dofs,
                    independents=independent_tuple,
                ),
            ),
            eid=eid,
        )
        self._rbe3_ties.append(tie)
        return tie

    def set_node_coordinates(self, coordinates) -> None:
        """Replace nodal coordinates in DOF numbering order (shape morphing)."""
        coords = np.asarray(coordinates, dtype=float)
        nodes = self.nodes
        if coords.ndim != 2 or coords.shape[0] != len(nodes) or coords.shape[1] > 3:
            raise ModelError(
                f"coordinates must have shape ({len(nodes)}, <=3), got {coords.shape}"
            )
        for node, row in zip(nodes, coords, strict=True):
            padded = np.zeros(3, dtype=float)
            padded[: row.size] = row
            object.__setattr__(node, "coords", padded)

    # ----------------------------------------------------- concentrated mass

    def add_point_mass(self, node_id: Hashable, mass: float, dofs=None) -> None:
        """Add a concentrated translational mass at ``node_id``.

        By default the mass acts on every active translational DOF of the model;
        pass ``dofs`` to restrict it to selected directions.
        """
        if mass < 0.0:
            raise ModelError(f"point mass must be non-negative, got {mass}")
        targets = self.translational_dofs if dofs is None else _parse_dofs(dofs)
        if not targets:
            raise ModelError("no translational DOF available for the point mass")
        for dof in targets:
            index = self.dof_index(node_id, dof)
            self._point_masses[index] = self._point_masses.get(index, 0.0) + float(mass)

    def add_rotary_inertia(self, node_id: Hashable, inertia: float, dofs=None) -> None:
        """Add a concentrated rotary inertia at ``node_id`` (rotational DOFs)."""
        if inertia < 0.0:
            raise ModelError(f"rotary inertia must be non-negative, got {inertia}")
        targets = self.rotational_dofs if dofs is None else _parse_dofs(dofs)
        if not targets:
            raise ModelError("no rotational DOF available for the rotary inertia")
        for dof in targets:
            index = self.dof_index(node_id, dof)
            self._point_masses[index] = self._point_masses.get(index, 0.0) + float(inertia)

    @property
    def point_masses(self) -> dict[int, float]:
        """Mapping ``global dof index -> concentrated mass/inertia``."""
        return dict(self._point_masses)

    def point_mass_vector(self) -> np.ndarray:
        """Concentrated masses expanded to a diagonal-of-M contribution vector."""
        vector = np.zeros(self.num_dofs, dtype=float)
        for index, value in self._point_masses.items():
            vector[index] += value
        return vector

    # ---------------------------------------------------------------- extras

    def add_spring(self, node_a: Hashable, node_b: Hashable, stiffness: float, dof=DOF.UX):
        """Create a scalar :class:`~openfemlab.core.elements.SpringElement`."""
        from .elements import SpringElement

        return self.add_element(SpringElement((node_a, node_b), stiffness, dof=dof))

    def add_grounded_spring(self, node_id: Hashable, stiffness: float, dof=DOF.UX):
        """Scalar spring between ``node_id`` and ground."""
        from .elements import SpringElement

        return self.add_element(SpringElement((node_id,), stiffness, dof=dof))

    def assemble(self):
        """Assemble ``K`` and ``M``; see :func:`openfemlab.core.assembly.assemble_system`."""
        from .assembly import assemble_system

        return assemble_system(self)

    def summary(self) -> str:
        parts: list[str] = []
        if self._rbe2_ties:
            parts.append(f"{len(self._rbe2_ties)} RBE2")
        if self._rbe3_ties:
            parts.append(f"{len(self._rbe3_ties)} RBE3")
        mpc = f", {', '.join(parts)}" if parts else ""
        return (
            f"Model {self.name!r}: {self.num_nodes} nodes, {self.num_elements} elements, "
            f"{self.num_dofs} DOFs ({len(self._constrained)} constrained{mpc}), "
            f"DOF signature {[d.name for d in self.dofs]}"
        )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{self.summary()}>"
