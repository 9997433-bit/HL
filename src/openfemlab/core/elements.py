"""Element library: scalar springs, 2-node bars/trusses and a planar beam.

Every element exposes the same contract used by :mod:`openfemlab.core.assembly`:

* :attr:`Element.node_ids` -- connectivity, in local node order;
* :meth:`Element.bind` -- resolves the element DOF signature against the model;
* :meth:`Element.stiffness_matrix` / :meth:`Element.mass_matrix` -- dense local
  matrices in *global* axes, ordered node-major with the element DOF signature.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Hashable, Sequence

import numpy as np

from ..exceptions import ElementError
from .model import DOF, TRANSLATIONAL_DOFS, Material, Section

__all__ = [
    "Element",
    "SpringElement",
    "TrussElement",
    "BarElement",
    "BeamElement2D",
]


class Element(ABC):
    """Abstract 1D structural element."""

    #: Number of nodes the concrete element expects, ``None`` when variable.
    expected_nodes: int | None = None

    def __init__(self, node_ids: Sequence[Hashable], *, eid: Hashable | None = None) -> None:
        self.node_ids: tuple[Hashable, ...] = tuple(node_ids)
        if self.expected_nodes is not None and len(self.node_ids) != self.expected_nodes:
            raise ElementError(
                f"{type(self).__name__} expects {self.expected_nodes} nodes, "
                f"got {len(self.node_ids)}"
            )
        if len(set(self.node_ids)) != len(self.node_ids):
            raise ElementError(f"{type(self).__name__} has repeated nodes: {self.node_ids}")
        self.id = eid
        self._dofs: tuple[DOF, ...] | None = None

    # ------------------------------------------------------------- DOF setup

    @abstractmethod
    def required_dofs(self, available: tuple[DOF, ...]) -> tuple[DOF, ...]:
        """DOFs (per node) the element wants, given the model's active DOFs."""

    def bind(self, available: tuple[DOF, ...]) -> tuple[DOF, ...]:
        """Freeze the element DOF signature; called when the element joins a model."""
        required = tuple(self.required_dofs(tuple(available)))
        missing = [d.name for d in required if d not in available]
        if missing:
            raise ElementError(
                f"{type(self).__name__} {self.node_ids} requires DOFs {missing} which are "
                f"not active in the model (active: {[d.name for d in available]})"
            )
        if not required:
            raise ElementError(
                f"{type(self).__name__} {self.node_ids} has no usable DOF in this model"
            )
        self._dofs = required
        return required

    @property
    def dofs(self) -> tuple[DOF, ...]:
        if self._dofs is None:
            raise ElementError(
                f"{type(self).__name__} {self.node_ids} is not bound to a model yet; "
                "add it via Model.add_element()"
            )
        return self._dofs

    @property
    def num_nodes(self) -> int:
        return len(self.node_ids)

    @property
    def num_dofs(self) -> int:
        return self.num_nodes * len(self.dofs)

    def global_dofs(self, model) -> np.ndarray:
        """Global equation numbers matching the local matrix ordering."""
        return np.array(
            [model.dof_index(nid, dof) for nid in self.node_ids for dof in self.dofs],
            dtype=int,
        )

    # --------------------------------------------------------------- physics

    @abstractmethod
    def stiffness_matrix(self, coords: np.ndarray) -> np.ndarray:
        """Local stiffness matrix in global axes for nodal ``coords`` (n_nodes x 3)."""

    @abstractmethod
    def mass_matrix(self, coords: np.ndarray) -> np.ndarray:
        """Local mass matrix in global axes for nodal ``coords`` (n_nodes x 3)."""

    def total_mass(self, coords: np.ndarray) -> float:
        """Structural mass carried by the element (0 for massless elements)."""
        return 0.0

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"{type(self).__name__}(nodes={self.node_ids})"


def _axial_geometry(coords: np.ndarray, axes: Sequence[int], element: Element):
    """Length and unit direction cosines of a 2-node element in the active axes."""
    delta = np.asarray(coords, dtype=float)[1, list(axes)] - np.asarray(coords, dtype=float)[
        0, list(axes)
    ]
    length = float(np.linalg.norm(delta))
    if length <= 0.0:
        raise ElementError(
            f"{type(element).__name__} {element.node_ids} has zero length in the active axes"
        )
    return length, delta / length


class SpringElement(Element):
    """Scalar spring acting along a single DOF direction.

    With two nodes it couples the same DOF of both nodes,
    ``k * [[1, -1], [-1, 1]]``. With one node it is a grounded spring, ``k * [[1]]``.
    Springs carry no mass; attach inertia with :meth:`Model.add_point_mass`.
    """

    def __init__(
        self,
        node_ids: Sequence[Hashable],
        stiffness: float,
        *,
        dof: DOF | str | int = DOF.UX,
        eid: Hashable | None = None,
    ) -> None:
        super().__init__(node_ids, eid=eid)
        if not 1 <= self.num_nodes <= 2:
            raise ElementError("SpringElement connects one node (to ground) or two nodes")
        if stiffness <= 0.0:
            raise ElementError(f"spring stiffness must be positive, got {stiffness}")
        self.stiffness = float(stiffness)
        self.dof = DOF.parse(dof)

    def required_dofs(self, available: tuple[DOF, ...]) -> tuple[DOF, ...]:
        return (self.dof,)

    def stiffness_matrix(self, coords: np.ndarray) -> np.ndarray:
        if self.num_nodes == 1:
            return np.array([[self.stiffness]], dtype=float)
        return self.stiffness * np.array([[1.0, -1.0], [-1.0, 1.0]], dtype=float)

    def mass_matrix(self, coords: np.ndarray) -> np.ndarray:
        return np.zeros((self.num_dofs, self.num_dofs), dtype=float)


class TrussElement(Element):
    """2-node bar carrying axial force only (pin-jointed truss member).

    Stiffness in global axes, with ``c`` the unit vector from node 1 to node 2::

        K = (E A / L) * [[ c c^T, -c c^T],
                         [-c c^T,  c c^T]]

    Consistent mass matrix (translating rod, valid in any direction)::

        M = (rho A L / 6) * [[2 I, 1 I],
                             [1 I, 2 I]]

    and, with ``lumped=True``, ``M = (rho A L / 2) * I``.
    """

    expected_nodes = 2

    def __init__(
        self,
        node_ids: Sequence[Hashable],
        material: Material,
        section: Section,
        *,
        lumped_mass: bool = False,
        eid: Hashable | None = None,
    ) -> None:
        super().__init__(node_ids, eid=eid)
        self.material = material
        self.section = section
        self.lumped_mass = bool(lumped_mass)

    # -- properties -------------------------------------------------------

    @property
    def axial_rigidity(self) -> float:
        return self.material.E * self.section.area

    @property
    def _axes(self) -> tuple[int, ...]:
        return tuple(int(d) for d in self.dofs)

    def required_dofs(self, available: tuple[DOF, ...]) -> tuple[DOF, ...]:
        return tuple(d for d in TRANSLATIONAL_DOFS if d in available)

    def length(self, coords: np.ndarray) -> float:
        return _axial_geometry(coords, self._axes, self)[0]

    def axial_stiffness(self, coords: np.ndarray) -> float:
        """Scalar spring constant ``EA/L`` of the member."""
        return self.axial_rigidity / self.length(coords)

    # -- matrices ---------------------------------------------------------

    def stiffness_matrix(self, coords: np.ndarray) -> np.ndarray:
        length, direction = _axial_geometry(coords, self._axes, self)
        block = np.outer(direction, direction) * (self.axial_rigidity / length)
        ndim = direction.size
        k = np.empty((2 * ndim, 2 * ndim), dtype=float)
        k[:ndim, :ndim] = block
        k[:ndim, ndim:] = -block
        k[ndim:, :ndim] = -block
        k[ndim:, ndim:] = block
        return k

    def mass_matrix(self, coords: np.ndarray) -> np.ndarray:
        length, direction = _axial_geometry(coords, self._axes, self)
        ndim = direction.size
        total = self.total_mass(coords)
        if total == 0.0:
            return np.zeros((2 * ndim, 2 * ndim), dtype=float)
        eye = np.eye(ndim)
        if self.lumped_mass:
            return 0.5 * total * np.eye(2 * ndim)
        m = np.empty((2 * ndim, 2 * ndim), dtype=float)
        factor = total / 6.0
        m[:ndim, :ndim] = 2.0 * factor * eye
        m[:ndim, ndim:] = factor * eye
        m[ndim:, :ndim] = factor * eye
        m[ndim:, ndim:] = 2.0 * factor * eye
        return m

    def total_mass(self, coords: np.ndarray) -> float:
        return self.material.density * self.section.area * self.length(coords)


#: A bar is a truss member; the alias keeps 1D axial models readable.
BarElement = TrussElement


class BeamElement2D(Element):
    """2-node Euler-Bernoulli beam in the XY plane (DOFs ``UX``, ``UY``, ``RZ``).

    Local stiffness (axial + bending, shear deformation neglected)::

        k_local = [[ EA/L,        0,       0, -EA/L,        0,       0],
                   [    0,  12EI/L^3, 6EI/L^2,     0, -12EI/L^3, 6EI/L^2],
                   [    0,   6EI/L^2,  4EI/L,      0,  -6EI/L^2, 2EI/L ],
                   [-EA/L,        0,       0,  EA/L,        0,       0],
                   [    0, -12EI/L^3,-6EI/L^2,     0,  12EI/L^3,-6EI/L^2],
                   [    0,   6EI/L^2,  2EI/L,      0,  -6EI/L^2, 4EI/L ]]

    with the classical consistent (translational) mass matrix ``rho A L / 420 * [...]``.
    Rotary inertia of the cross section is neglected, consistent with the
    Euler-Bernoulli assumption.
    """

    expected_nodes = 2

    def __init__(
        self,
        node_ids: Sequence[Hashable],
        material: Material,
        section: Section,
        *,
        lumped_mass: bool = False,
        eid: Hashable | None = None,
    ) -> None:
        super().__init__(node_ids, eid=eid)
        if section.inertia_z <= 0.0:
            raise ElementError("BeamElement2D requires a positive section.inertia_z")
        self.material = material
        self.section = section
        self.lumped_mass = bool(lumped_mass)

    def required_dofs(self, available: tuple[DOF, ...]) -> tuple[DOF, ...]:
        return (DOF.UX, DOF.UY, DOF.RZ)

    def length(self, coords: np.ndarray) -> float:
        return _axial_geometry(coords, (0, 1), self)[0]

    def total_mass(self, coords: np.ndarray) -> float:
        return self.material.density * self.section.area * self.length(coords)

    def _transformation(self, coords: np.ndarray) -> tuple[float, np.ndarray]:
        length, direction = _axial_geometry(coords, (0, 1), self)
        c, s = float(direction[0]), float(direction[1])
        rotation = np.array([[c, s, 0.0], [-s, c, 0.0], [0.0, 0.0, 1.0]], dtype=float)
        transform = np.zeros((6, 6), dtype=float)
        transform[:3, :3] = rotation
        transform[3:, 3:] = rotation
        return length, transform

    def local_stiffness_matrix(self, length: float) -> np.ndarray:
        E, A, inertia, L = (
            self.material.E,
            self.section.area,
            self.section.inertia_z,
            length,
        )
        ea = E * A / L
        b1 = 12.0 * E * inertia / L**3
        b2 = 6.0 * E * inertia / L**2
        b3 = 4.0 * E * inertia / L
        b4 = 2.0 * E * inertia / L
        return np.array(
            [
                [ea, 0.0, 0.0, -ea, 0.0, 0.0],
                [0.0, b1, b2, 0.0, -b1, b2],
                [0.0, b2, b3, 0.0, -b2, b4],
                [-ea, 0.0, 0.0, ea, 0.0, 0.0],
                [0.0, -b1, -b2, 0.0, b1, -b2],
                [0.0, b2, b4, 0.0, -b2, b3],
            ],
            dtype=float,
        )

    def local_mass_matrix(self, length: float) -> np.ndarray:
        total = self.material.density * self.section.area * length
        if total == 0.0:
            return np.zeros((6, 6), dtype=float)
        if self.lumped_mass:
            half = 0.5 * total
            return np.diag([half, half, 0.0, half, half, 0.0])
        L = length
        return (total / 420.0) * np.array(
            [
                [140.0, 0.0, 0.0, 70.0, 0.0, 0.0],
                [0.0, 156.0, 22.0 * L, 0.0, 54.0, -13.0 * L],
                [0.0, 22.0 * L, 4.0 * L**2, 0.0, 13.0 * L, -3.0 * L**2],
                [70.0, 0.0, 0.0, 140.0, 0.0, 0.0],
                [0.0, 54.0, 13.0 * L, 0.0, 156.0, -22.0 * L],
                [0.0, -13.0 * L, -3.0 * L**2, 0.0, -22.0 * L, 4.0 * L**2],
            ],
            dtype=float,
        )

    def stiffness_matrix(self, coords: np.ndarray) -> np.ndarray:
        length, transform = self._transformation(coords)
        return transform.T @ self.local_stiffness_matrix(length) @ transform

    def mass_matrix(self, coords: np.ndarray) -> np.ndarray:
        length, transform = self._transformation(coords)
        return transform.T @ self.local_mass_matrix(length) @ transform
