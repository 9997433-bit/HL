"""Element library: springs, bars/trusses, planar and spatial beams, QUAD4, TET4, HEX8.

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
    "BeamElement3D",
    "Quad4Element",
    "Tet4Element",
    "Hex8Element",
    "PLANE_STATES",
    "gauss_legendre_2d",
    "gauss_legendre_3d",
    "plane_constitutive_matrix",
    "solid_constitutive_matrix",
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


def _bending_stiffness_block(rigidity: float, length: float) -> np.ndarray:
    """Euler-Bernoulli bending stiffness for ``(v1, theta1, v2, theta2)``."""
    b1 = 12.0 * rigidity / length**3
    b2 = 6.0 * rigidity / length**2
    b3 = 4.0 * rigidity / length
    b4 = 2.0 * rigidity / length
    return np.array(
        [
            [b1, b2, -b1, b2],
            [b2, b3, -b2, b4],
            [-b1, -b2, b1, -b2],
            [b2, b4, -b2, b3],
        ],
        dtype=float,
    )


def _bending_mass_block(total_mass: float, length: float) -> np.ndarray:
    """Consistent bending mass for ``(v1, theta1, v2, theta2)``, rotary inertia neglected."""
    L = length
    return (total_mass / 420.0) * np.array(
        [
            [156.0, 22.0 * L, 54.0, -13.0 * L],
            [22.0 * L, 4.0 * L**2, 13.0 * L, -3.0 * L**2],
            [54.0, 13.0 * L, 156.0, -22.0 * L],
            [-13.0 * L, -3.0 * L**2, -22.0 * L, 4.0 * L**2],
        ],
        dtype=float,
    )


#: Local DOF positions of the two bending planes in the 12-DOF beam ordering.
_BEAM3D_XY_PLANE = [1, 5, 7, 11]
_BEAM3D_XZ_PLANE = [2, 4, 8, 10]

#: Bending in the local x-z plane uses ``dw/dx = -theta_y``, so the rotational
#: rows and columns of the x-y blocks flip sign.
_BEAM3D_PLANE_SIGNS = np.diag([1.0, -1.0, 1.0, -1.0])

#: Candidate orientation references when the caller supplies none.
_BEAM3D_DEFAULT_REFERENCES = (
    np.array([0.0, 1.0, 0.0]),
    np.array([0.0, 0.0, 1.0]),
)


class BeamElement3D(Element):
    """2-node spatial Euler-Bernoulli beam, the CBAR-like frame member.

    Six DOFs per node (``UX``, ``UY``, ``UZ``, ``RX``, ``RY``, ``RZ``) carry
    axial extension, St Venant torsion and uncoupled bending in the two
    principal planes::

        k_local = diag_blocks(EA/L, GJ/L, bending(E Iz), bending(E Iy))

    with ``bending(EI)`` the classical 4x4 Hermitian block. Bending in the local
    x-y plane (deflection along local ``y``) is governed by
    :attr:`~openfemlab.core.model.Section.inertia_z`, bending in the local x-z
    plane by ``inertia_y``, and torsion by ``torsion_constant`` times the
    material shear modulus; all three must be positive.

    The local frame follows the Nastran CBAR convention: local ``x`` runs from
    the first to the second node and the *orientation vector* ``v`` fixes the
    roll by placing local ``y`` in the ``x``-``v`` plane, on the ``v`` side::

        e_x = (x2 - x1) / L      e_z = e_x x v / |e_x x v|      e_y = e_z x e_x

    ``orientation=None`` picks whichever of global ``Y`` and ``Z`` is least
    aligned with the member, so a beam along global ``X`` reproduces the planar
    :class:`BeamElement2D` frame (local ``y`` = global ``Y``). An explicit
    orientation parallel to the member is rejected rather than silently
    replaced.

    The consistent mass matrix adds the torsional rotary inertia
    ``rho (Iy + Iz) L`` on the twist DOFs -- without it the mass matrix is
    singular in torsion -- but neglects bending rotary inertia and shear
    deformation, consistent with the Euler-Bernoulli assumption. Warping,
    shear-centre offsets and rigid end offsets are not modelled, so the element
    matches CBAR only for members whose shear centre coincides with the
    centroid. ``lumped_mass`` row-lumps translation and twist and leaves the
    bending rotations massless, as :class:`BeamElement2D` does.
    """

    expected_nodes = 2

    #: An orientation vector this close to the member axis (in sine) is rejected.
    parallel_tolerance = 1e-8

    def __init__(
        self,
        node_ids: Sequence[Hashable],
        material: Material,
        section: Section,
        *,
        orientation: Sequence[float] | None = None,
        lumped_mass: bool = False,
        eid: Hashable | None = None,
    ) -> None:
        super().__init__(node_ids, eid=eid)
        for label in ("inertia_z", "inertia_y", "torsion_constant"):
            if getattr(section, label) <= 0.0:
                raise ElementError(f"BeamElement3D requires a positive section.{label}")
        self.material = material
        self.section = section
        self.orientation = None if orientation is None else self._unit_vector(orientation)
        self.lumped_mass = bool(lumped_mass)

    def _unit_vector(self, value: Sequence[float]) -> np.ndarray:
        vector = np.asarray(value, dtype=float).reshape(-1)
        if vector.size != 3:
            raise ElementError(
                f"BeamElement3D orientation needs three components, got {vector.size}"
            )
        norm = float(np.linalg.norm(vector))
        if norm == 0.0:
            raise ElementError("BeamElement3D orientation vector must be non-zero")
        return vector / norm

    def required_dofs(self, available: tuple[DOF, ...]) -> tuple[DOF, ...]:
        return (DOF.UX, DOF.UY, DOF.UZ, DOF.RX, DOF.RY, DOF.RZ)

    # ------------------------------------------------------------- geometry

    def length(self, coords: np.ndarray) -> float:
        return _axial_geometry(coords, (0, 1, 2), self)[0]

    def _reference_vector(self, axis: np.ndarray) -> np.ndarray:
        if self.orientation is not None:
            return self.orientation
        return min(_BEAM3D_DEFAULT_REFERENCES, key=lambda v: abs(float(axis @ v)))

    def local_axes(self, coords: np.ndarray) -> np.ndarray:
        """Rows ``[e_x, e_y, e_z]`` of the local frame, expressed in global axes."""
        _, e_x = _axial_geometry(coords, (0, 1, 2), self)
        e_z = np.cross(e_x, self._reference_vector(e_x))
        norm = float(np.linalg.norm(e_z))
        if norm <= self.parallel_tolerance:
            raise ElementError(
                f"BeamElement3D {self.node_ids} has an orientation vector parallel to the "
                "member axis; pick a vector spanning the local x-y plane"
            )
        e_z = e_z / norm
        return np.array([e_x, np.cross(e_z, e_x), e_z], dtype=float)

    def transformation_matrix(self, coords: np.ndarray) -> np.ndarray:
        """Global-to-local rotation of the 12 element DOFs."""
        rotation = self.local_axes(coords)
        transform = np.zeros((12, 12), dtype=float)
        for block in range(4):
            offset = 3 * block
            transform[offset : offset + 3, offset : offset + 3] = rotation
        return transform

    # --------------------------------------------------------------- physics

    def total_mass(self, coords: np.ndarray) -> float:
        return self.material.density * self.section.area * self.length(coords)

    def local_stiffness_matrix(self, length: float) -> np.ndarray:
        """The 12x12 stiffness in local axes for a member of ``length``."""
        E, G = self.material.E, self.material.shear_modulus
        axial = E * self.section.area / length
        torsion = G * self.section.torsion_constant / length
        k = np.zeros((12, 12), dtype=float)
        k[np.ix_([0, 6], [0, 6])] = axial * np.array([[1.0, -1.0], [-1.0, 1.0]])
        k[np.ix_([3, 9], [3, 9])] = torsion * np.array([[1.0, -1.0], [-1.0, 1.0]])
        xy = _bending_stiffness_block(E * self.section.inertia_z, length)
        k[np.ix_(_BEAM3D_XY_PLANE, _BEAM3D_XY_PLANE)] = xy
        xz = _bending_stiffness_block(E * self.section.inertia_y, length)
        k[np.ix_(_BEAM3D_XZ_PLANE, _BEAM3D_XZ_PLANE)] = (
            _BEAM3D_PLANE_SIGNS @ xz @ _BEAM3D_PLANE_SIGNS
        )
        return k

    def local_mass_matrix(self, length: float) -> np.ndarray:
        """The 12x12 mass in local axes for a member of ``length``."""
        total = self.material.density * self.section.area * length
        if total == 0.0:
            return np.zeros((12, 12), dtype=float)
        polar = self.material.density * (self.section.inertia_y + self.section.inertia_z) * length
        if self.lumped_mass:
            half, twist = 0.5 * total, 0.5 * polar
            return np.diag([half, half, half, twist, 0.0, 0.0] * 2)
        m = np.zeros((12, 12), dtype=float)
        m[np.ix_([0, 6], [0, 6])] = (total / 6.0) * np.array([[2.0, 1.0], [1.0, 2.0]])
        m[np.ix_([3, 9], [3, 9])] = (polar / 6.0) * np.array([[2.0, 1.0], [1.0, 2.0]])
        bending = _bending_mass_block(total, length)
        m[np.ix_(_BEAM3D_XY_PLANE, _BEAM3D_XY_PLANE)] = bending
        m[np.ix_(_BEAM3D_XZ_PLANE, _BEAM3D_XZ_PLANE)] = (
            _BEAM3D_PLANE_SIGNS @ bending @ _BEAM3D_PLANE_SIGNS
        )
        return m

    def stiffness_matrix(self, coords: np.ndarray) -> np.ndarray:
        transform = self.transformation_matrix(coords)
        return transform.T @ self.local_stiffness_matrix(self.length(coords)) @ transform

    def mass_matrix(self, coords: np.ndarray) -> np.ndarray:
        transform = self.transformation_matrix(coords)
        return transform.T @ self.local_mass_matrix(self.length(coords)) @ transform

    # ------------------------------------------------------------- recovery

    def end_forces(self, coords: np.ndarray, displacements: np.ndarray) -> np.ndarray:
        """Local end forces ``[N, Vy, Vz, T, My, Mz]`` per node, node-major.

        Sign convention: the entries are the forces the *nodes* apply to the
        element, so a member in tension reports a negative axial force at its
        first node and a positive one at its second.
        """
        values = np.asarray(displacements, dtype=float).reshape(-1)
        if values.size != 12:
            raise ElementError(f"expected 12 nodal displacements, got {values.size}")
        transform = self.transformation_matrix(coords)
        return self.local_stiffness_matrix(self.length(coords)) @ (transform @ values)


#: Two-dimensional idealizations supported by :class:`Quad4Element`.
PLANE_STATES: tuple[str, ...] = ("stress", "strain")

#: Natural coordinates of the QUAD4 corner nodes, counter-clockwise from (-1, -1).
_QUAD4_NATURAL = np.array([[-1.0, -1.0], [1.0, -1.0], [1.0, 1.0], [-1.0, 1.0]], dtype=float)


def _gauss_legendre_1d(order: int) -> tuple[np.ndarray, np.ndarray]:
    """Validated 1D Gauss-Legendre nodes and weights on ``[-1, 1]``."""
    if not 1 <= int(order) <= 4:
        raise ElementError(f"integration order must lie in [1, 4], got {order}")
    return np.polynomial.legendre.leggauss(int(order))


def gauss_legendre_2d(order: int = 2) -> tuple[np.ndarray, np.ndarray]:
    """Tensor-product Gauss-Legendre rule on ``[-1, 1]^2``.

    Returns ``(points, weights)`` with ``points`` of shape ``(order**2, 2)``. A
    rule of ``order`` points per direction integrates polynomials of degree
    ``2*order - 1`` per direction exactly.
    """
    nodes, weights = _gauss_legendre_1d(order)
    xi, eta = np.meshgrid(nodes, nodes, indexing="ij")
    wxi, weta = np.meshgrid(weights, weights, indexing="ij")
    return np.column_stack((xi.ravel(), eta.ravel())), (wxi * weta).ravel()


def gauss_legendre_3d(order: int = 2) -> tuple[np.ndarray, np.ndarray]:
    """Tensor-product Gauss-Legendre rule on ``[-1, 1]^3``.

    Returns ``(points, weights)`` with ``points`` of shape ``(order**3, 3)``,
    the three-dimensional counterpart of :func:`gauss_legendre_2d`.
    """
    nodes, weights = _gauss_legendre_1d(order)
    xi, eta, zeta = np.meshgrid(nodes, nodes, nodes, indexing="ij")
    wxi, weta, wzeta = np.meshgrid(weights, weights, weights, indexing="ij")
    return (
        np.column_stack((xi.ravel(), eta.ravel(), zeta.ravel())),
        (wxi * weta * wzeta).ravel(),
    )


def plane_constitutive_matrix(material: Material, plane: str = "stress") -> np.ndarray:
    """Isotropic 2D elasticity matrix relating ``[sxx, syy, sxy]`` to ``[exx, eyy, gxy]``.

    Plane stress (thin sheet loaded in its plane, ``szz = 0``)::

        D = E / (1 - nu^2) * [[1, nu, 0], [nu, 1, 0], [0, 0, (1 - nu) / 2]]

    Plane strain (long prismatic body, ``ezz = 0``)::

        D = E / ((1 + nu) (1 - 2 nu))
            * [[1 - nu, nu, 0], [nu, 1 - nu, 0], [0, 0, (1 - 2 nu) / 2]]
    """
    if plane not in PLANE_STATES:
        raise ElementError(f"unknown plane state {plane!r}; expected one of {list(PLANE_STATES)}")
    E, nu = float(material.E), float(material.nu)
    if plane == "stress":
        factor = E / (1.0 - nu**2)
        return factor * np.array(
            [[1.0, nu, 0.0], [nu, 1.0, 0.0], [0.0, 0.0, 0.5 * (1.0 - nu)]], dtype=float
        )
    factor = E / ((1.0 + nu) * (1.0 - 2.0 * nu))
    return factor * np.array(
        [
            [1.0 - nu, nu, 0.0],
            [nu, 1.0 - nu, 0.0],
            [0.0, 0.0, 0.5 * (1.0 - 2.0 * nu)],
        ],
        dtype=float,
    )


class Quad4Element(Element):
    """4-node isoparametric bilinear quadrilateral in the XY plane (DOFs ``UX``, ``UY``).

    Nodes are given counter-clockwise; the element is mapped from the reference
    square by the bilinear shape functions

    ``N_i(xi, eta) = (1 + xi xi_i) (1 + eta eta_i) / 4``

    so that geometry and displacement share the same interpolation. With
    ``B`` the strain-displacement operator and ``D`` the plane constitutive
    matrix (:func:`plane_constitutive_matrix`),

    ``K = t * int B^T D B dA``  and  ``M = rho t * int N^T N dA``

    are evaluated by a tensor-product Gauss rule (2x2 by default, which
    integrates both exactly for any non-degenerate quadrilateral). Full
    integration means the element has exactly three zero-energy modes -- the
    planar rigid-body motions -- and no hourglass modes; ``integration_order=1``
    is available for comparison studies but is rank deficient.

    Because the displacement field is bilinear the element reproduces any
    constant strain state exactly (it passes the patch test) but represents
    bending through shear, so it locks on coarse, high-aspect-ratio bending
    meshes. Refine, or use it where membrane action dominates.

    Parameters
    ----------
    material:
        Isotropic linear elastic material; ``density`` may be zero.
    thickness:
        Out-of-plane thickness ``t``.
    plane:
        ``"stress"`` (default) or ``"strain"``.
    lumped_mass:
        Diagonalize the consistent mass matrix by row summing, which preserves
        the total translational mass for any element shape.
    integration_order:
        Gauss points per direction.
    """

    expected_nodes = 4

    def __init__(
        self,
        node_ids: Sequence[Hashable],
        material: Material,
        *,
        thickness: float = 1.0,
        plane: str = "stress",
        lumped_mass: bool = False,
        integration_order: int = 2,
        eid: Hashable | None = None,
    ) -> None:
        super().__init__(node_ids, eid=eid)
        if thickness <= 0.0:
            raise ElementError(f"Quad4Element thickness must be positive, got {thickness}")
        if plane not in PLANE_STATES:
            raise ElementError(
                f"unknown plane state {plane!r}; expected one of {list(PLANE_STATES)}"
            )
        self.material = material
        self.thickness = float(thickness)
        self.plane = plane
        self.lumped_mass = bool(lumped_mass)
        self.integration_order = int(integration_order)
        self._points, self._weights = gauss_legendre_2d(self.integration_order)

    def required_dofs(self, available: tuple[DOF, ...]) -> tuple[DOF, ...]:
        return (DOF.UX, DOF.UY)

    # ------------------------------------------------------------- kinematics

    @staticmethod
    def shape_functions(xi: float, eta: float) -> np.ndarray:
        """Bilinear shape functions ``N`` at a natural point, shape ``(4,)``."""
        signs = _QUAD4_NATURAL
        return 0.25 * (1.0 + signs[:, 0] * xi) * (1.0 + signs[:, 1] * eta)

    @staticmethod
    def shape_function_derivatives(xi: float, eta: float) -> np.ndarray:
        """``dN/d(xi, eta)`` at a natural point, shape ``(2, 4)``."""
        signs = _QUAD4_NATURAL
        return 0.25 * np.array(
            [
                signs[:, 0] * (1.0 + signs[:, 1] * eta),
                signs[:, 1] * (1.0 + signs[:, 0] * xi),
            ],
            dtype=float,
        )

    def _planar_coords(self, coords: np.ndarray) -> np.ndarray:
        """The ``(4, 2)`` in-plane coordinates, rejecting out-of-plane geometry."""
        points = np.asarray(coords, dtype=float).reshape(4, -1)
        if points.shape[1] > 2:
            spread = float(np.ptp(points[:, 2]))
            scale = float(np.max(np.abs(points[:, :2]))) or 1.0
            if spread > 1e-9 * scale:
                raise ElementError(
                    f"Quad4Element {self.node_ids} is a planar XY element but its nodes "
                    f"span {spread:g} in Z"
                )
        return points[:, :2]

    def jacobian(self, coords: np.ndarray, xi: float, eta: float) -> tuple[np.ndarray, float]:
        """``(dN/dx, det J)`` at a natural point; ``dN/dx`` has shape ``(2, 4)``."""
        points = self._planar_coords(coords)
        natural = self.shape_function_derivatives(xi, eta)
        jac = natural @ points
        det = float(jac[0, 0] * jac[1, 1] - jac[0, 1] * jac[1, 0])
        if det <= 0.0:
            raise ElementError(
                f"Quad4Element {self.node_ids} has a non-positive Jacobian ({det:g}) at "
                f"(xi, eta) = ({xi:g}, {eta:g}); the element is degenerate, inverted or "
                "its nodes are not ordered counter-clockwise"
            )
        inverse = np.array([[jac[1, 1], -jac[0, 1]], [-jac[1, 0], jac[0, 0]]], dtype=float) / det
        return inverse @ natural, det

    def strain_displacement_matrix(
        self, coords: np.ndarray, xi: float, eta: float
    ) -> tuple[np.ndarray, float]:
        """``(B, det J)`` with ``B`` of shape ``(3, 8)`` in node-major DOF order."""
        gradient, det = self.jacobian(coords, xi, eta)
        b = np.zeros((3, 8), dtype=float)
        b[0, 0::2] = gradient[0]
        b[1, 1::2] = gradient[1]
        b[2, 0::2] = gradient[1]
        b[2, 1::2] = gradient[0]
        return b, det

    # --------------------------------------------------------------- physics

    @property
    def constitutive_matrix(self) -> np.ndarray:
        """Plane elasticity matrix ``D`` for the element's material and plane state."""
        return plane_constitutive_matrix(self.material, self.plane)

    def area(self, coords: np.ndarray) -> float:
        """Element area, integrated with the element's own quadrature rule."""
        return float(
            sum(
                weight * self.jacobian(coords, *point)[1]
                for point, weight in zip(self._points, self._weights, strict=True)
            )
        )

    def stiffness_matrix(self, coords: np.ndarray) -> np.ndarray:
        D = self.constitutive_matrix
        k = np.zeros((8, 8), dtype=float)
        for point, weight in zip(self._points, self._weights, strict=True):
            b, det = self.strain_displacement_matrix(coords, *point)
            k += (weight * det * self.thickness) * (b.T @ D @ b)
        return k

    def consistent_mass_matrix(self, coords: np.ndarray) -> np.ndarray:
        """``rho t int N^T N dA`` regardless of the ``lumped_mass`` setting."""
        density = float(self.material.density)
        m = np.zeros((8, 8), dtype=float)
        if density == 0.0:
            return m
        for point, weight in zip(self._points, self._weights, strict=True):
            shape = self.shape_functions(*point)
            _, det = self.jacobian(coords, *point)
            block = np.outer(shape, shape)
            factor = weight * det * self.thickness * density
            m[0::2, 0::2] += factor * block
            m[1::2, 1::2] += factor * block
        return m

    def mass_matrix(self, coords: np.ndarray) -> np.ndarray:
        consistent = self.consistent_mass_matrix(coords)
        if not self.lumped_mass:
            return consistent
        return np.diag(consistent.sum(axis=1))

    def total_mass(self, coords: np.ndarray) -> float:
        return float(self.material.density) * self.thickness * self.area(coords)

    # ------------------------------------------------------------ recovery

    def strain(
        self, coords: np.ndarray, displacements: np.ndarray, xi: float = 0.0, eta: float = 0.0
    ) -> np.ndarray:
        """Strain ``[exx, eyy, gxy]`` at a natural point from the 8 nodal displacements."""
        values = np.asarray(displacements, dtype=float).reshape(-1)
        if values.size != 8:
            raise ElementError(f"expected 8 nodal displacements, got {values.size}")
        b, _ = self.strain_displacement_matrix(coords, xi, eta)
        return b @ values

    def stress(
        self, coords: np.ndarray, displacements: np.ndarray, xi: float = 0.0, eta: float = 0.0
    ) -> np.ndarray:
        """Stress ``[sxx, syy, sxy]`` at a natural point from the 8 nodal displacements."""
        return self.constitutive_matrix @ self.strain(coords, displacements, xi, eta)


#: ``dN/d(xi, eta, zeta)`` of the TET4 shape functions -- constant, shape ``(3, 4)``.
_TET4_NATURAL_GRADIENT = np.array(
    [
        [-1.0, 1.0, 0.0, 0.0],
        [-1.0, 0.0, 1.0, 0.0],
        [-1.0, 0.0, 0.0, 1.0],
    ],
    dtype=float,
)

#: ``int N_i N_j dV / V`` over a tetrahedron: ``1/10`` on the diagonal, ``1/20`` elsewhere.
_TET4_MASS_PATTERN = (np.ones((4, 4), dtype=float) + np.eye(4)) / 20.0


def solid_constitutive_matrix(material: Material) -> np.ndarray:
    """Isotropic 3D elasticity matrix in Voigt notation.

    Relates ``[sxx, syy, szz, sxy, syz, szx]`` to the engineering strains
    ``[exx, eyy, ezz, gxy, gyz, gzx]`` through the Lame constants
    ``lambda = E nu / ((1 + nu) (1 - 2 nu))`` and ``mu = E / (2 (1 + nu))``::

        D = [[l + 2m,      l,      l,  0,  0,  0],
             [     l, l + 2m,      l,  0,  0,  0],
             [     l,      l, l + 2m,  0,  0,  0],
             [     0,      0,      0,  m,  0,  0],
             [     0,      0,      0,  0,  m,  0],
             [     0,      0,      0,  0,  0,  m]]

    :class:`~openfemlab.core.model.Material` keeps ``nu`` strictly below ``0.5``,
    so ``lambda`` stays finite; near-incompressible materials are representable
    but make constant-strain elements lock.
    """
    E, nu = float(material.E), float(material.nu)
    lam = E * nu / ((1.0 + nu) * (1.0 - 2.0 * nu))
    mu = E / (2.0 * (1.0 + nu))
    d = np.zeros((6, 6), dtype=float)
    d[:3, :3] = lam
    d[np.diag_indices(3)] += 2.0 * mu
    d[3:, 3:] = mu * np.eye(3)
    return d


class Tet4Element(Element):
    """4-node linear tetrahedron -- the constant-strain solid (DOFs ``UX``, ``UY``, ``UZ``).

    The displacement field is linear in the volume coordinates,

    ``N = [1 - xi - eta - zeta, xi, eta, zeta]``,

    so ``B`` is constant over the element and one integration point is exact::

        K = V B^T D B      M = rho V / 20 * (1 + I) (x) I_3

    with ``V`` the signed volume and ``D`` from :func:`solid_constitutive_matrix`.
    The consistent mass follows from ``int N_i N_j dV = V (1 + delta_ij) / 20``;
    ``lumped_mass`` row-sums it to ``rho V / 4`` per node.

    Nodes are ordered so that the first three run counter-clockwise seen from the
    fourth, which makes the volume positive; any other ordering is rejected
    rather than silently sign-flipped.

    Being a constant-strain element it passes the patch test exactly but is the
    stiffest practical solid: bending is carried by a single constant strain per
    element, so it converges slowly and locks as ``nu`` approaches ``0.5``. Use
    it to fill geometry a structured mesher cannot, and refine.
    """

    expected_nodes = 4

    def __init__(
        self,
        node_ids: Sequence[Hashable],
        material: Material,
        *,
        lumped_mass: bool = False,
        eid: Hashable | None = None,
    ) -> None:
        super().__init__(node_ids, eid=eid)
        self.material = material
        self.lumped_mass = bool(lumped_mass)

    def required_dofs(self, available: tuple[DOF, ...]) -> tuple[DOF, ...]:
        return TRANSLATIONAL_DOFS

    # ------------------------------------------------------------- kinematics

    @staticmethod
    def shape_functions(xi: float, eta: float, zeta: float) -> np.ndarray:
        """Volume-coordinate shape functions ``N`` at a natural point, shape ``(4,)``."""
        return np.array([1.0 - xi - eta - zeta, xi, eta, zeta], dtype=float)

    @staticmethod
    def shape_function_derivatives() -> np.ndarray:
        """``dN/d(xi, eta, zeta)``, shape ``(3, 4)``; constant over the element."""
        return _TET4_NATURAL_GRADIENT.copy()

    def _solid_coords(self, coords: np.ndarray) -> np.ndarray:
        """The ``(4, 3)`` nodal coordinates."""
        points = np.asarray(coords, dtype=float).reshape(4, -1)
        if points.shape[1] != 3:
            raise ElementError(
                f"Tet4Element {self.node_ids} needs three coordinates per node, "
                f"got {points.shape[1]}"
            )
        return points

    def jacobian(self, coords: np.ndarray) -> tuple[np.ndarray, float]:
        """``(dN/dx, det J)`` with ``dN/dx`` of shape ``(3, 4)``; ``det J = 6 V``."""
        points = self._solid_coords(coords)
        jac = _TET4_NATURAL_GRADIENT @ points
        det = float(np.linalg.det(jac))
        if det <= 0.0:
            raise ElementError(
                f"Tet4Element {self.node_ids} has a non-positive Jacobian ({det:g}); the "
                "element is degenerate, inverted or its first three nodes do not run "
                "counter-clockwise seen from the fourth"
            )
        return np.linalg.solve(jac, _TET4_NATURAL_GRADIENT), det

    def strain_displacement_matrix(self, coords: np.ndarray) -> tuple[np.ndarray, float]:
        """``(B, det J)`` with ``B`` of shape ``(6, 12)`` in node-major DOF order."""
        gradient, det = self.jacobian(coords)
        b = np.zeros((6, 12), dtype=float)
        b[0, 0::3] = gradient[0]
        b[1, 1::3] = gradient[1]
        b[2, 2::3] = gradient[2]
        b[3, 0::3] = gradient[1]
        b[3, 1::3] = gradient[0]
        b[4, 1::3] = gradient[2]
        b[4, 2::3] = gradient[1]
        b[5, 0::3] = gradient[2]
        b[5, 2::3] = gradient[0]
        return b, det

    # --------------------------------------------------------------- physics

    @property
    def constitutive_matrix(self) -> np.ndarray:
        """3D elasticity matrix ``D`` for the element's material."""
        return solid_constitutive_matrix(self.material)

    def volume(self, coords: np.ndarray) -> float:
        """Volume ``det J / 6``, positive for a correctly ordered element."""
        return self.jacobian(coords)[1] / 6.0

    def stiffness_matrix(self, coords: np.ndarray) -> np.ndarray:
        b, det = self.strain_displacement_matrix(coords)
        return (det / 6.0) * (b.T @ self.constitutive_matrix @ b)

    def consistent_mass_matrix(self, coords: np.ndarray) -> np.ndarray:
        """``rho int N^T N dV`` regardless of the ``lumped_mass`` setting."""
        density = float(self.material.density)
        if density == 0.0:
            return np.zeros((12, 12), dtype=float)
        return np.kron(_TET4_MASS_PATTERN, np.eye(3)) * (density * self.volume(coords))

    def mass_matrix(self, coords: np.ndarray) -> np.ndarray:
        consistent = self.consistent_mass_matrix(coords)
        if not self.lumped_mass:
            return consistent
        return np.diag(consistent.sum(axis=1))

    def total_mass(self, coords: np.ndarray) -> float:
        return float(self.material.density) * self.volume(coords)

    # ------------------------------------------------------------ recovery

    def strain(self, coords: np.ndarray, displacements: np.ndarray) -> np.ndarray:
        """Strain ``[exx, eyy, ezz, gxy, gyz, gzx]``, constant over the element."""
        values = np.asarray(displacements, dtype=float).reshape(-1)
        if values.size != 12:
            raise ElementError(f"expected 12 nodal displacements, got {values.size}")
        b, _ = self.strain_displacement_matrix(coords)
        return b @ values

    def stress(self, coords: np.ndarray, displacements: np.ndarray) -> np.ndarray:
        """Stress ``[sxx, syy, szz, sxy, syz, szx]``, constant over the element."""
        return self.constitutive_matrix @ self.strain(coords, displacements)


#: Natural coordinates of the HEX8 corner nodes: the ``zeta = -1`` face
#: counter-clockwise from ``(-1, -1)``, then the ``zeta = +1`` face the same way.
#: This is the CHEXA / VTK / meshio corner ordering.
_HEX8_NATURAL = np.array(
    [
        [-1.0, -1.0, -1.0],
        [1.0, -1.0, -1.0],
        [1.0, 1.0, -1.0],
        [-1.0, 1.0, -1.0],
        [-1.0, -1.0, 1.0],
        [1.0, -1.0, 1.0],
        [1.0, 1.0, 1.0],
        [-1.0, 1.0, 1.0],
    ],
    dtype=float,
)


class Hex8Element(Element):
    """8-node isoparametric trilinear brick (DOFs ``UX``, ``UY``, ``UZ``).

    The solid counterpart of :class:`Quad4Element`: nodes are given as the
    ``zeta = -1`` face counter-clockwise seen from ``+zeta``, then the
    ``zeta = +1`` face in the same order, and the element is mapped from the
    reference cube by

    ``N_i(xi, eta, zeta) = (1 + xi xi_i) (1 + eta eta_i) (1 + zeta zeta_i) / 8``.

    With ``B`` the strain-displacement operator and ``D`` the 3D elasticity
    matrix (:func:`solid_constitutive_matrix`),

    ``K = int B^T D B dV``  and  ``M = rho int N^T N dV``

    are evaluated by a tensor-product Gauss rule (2x2x2 by default). Full
    integration leaves exactly six zero-energy modes -- the spatial rigid-body
    motions -- so the brick has no hourglass modes; ``integration_order=1``
    reproduces the classical rank deficiency (12 spurious modes) and exists for
    comparison studies only.

    The trilinear field reproduces any constant strain state exactly (it passes
    the patch test on distorted geometry) but, like QUAD4, carries bending
    through parasitic shear, so it locks on coarse, high-aspect-ratio bending
    meshes and stiffens further as ``nu`` approaches ``0.5``. It is still far
    softer than the constant-strain :class:`Tet4Element` at equal DOF count.

    The quadrature is exact for the volume and for the row sums of the mass
    matrix on any hexahedron (both integrands stay within the 2-point rule's
    degree), hence for the total and lumped mass; the off-diagonal consistent
    mass terms are exact for a parallelepiped and quadrature-approximated on a
    distorted element, which ``integration_order=3`` removes.

    Parameters
    ----------
    material:
        Isotropic linear elastic material; ``density`` may be zero.
    lumped_mass:
        Diagonalize the consistent mass matrix by row summing, which preserves
        the total translational mass for any element shape.
    integration_order:
        Gauss points per direction.
    """

    expected_nodes = 8

    def __init__(
        self,
        node_ids: Sequence[Hashable],
        material: Material,
        *,
        lumped_mass: bool = False,
        integration_order: int = 2,
        eid: Hashable | None = None,
    ) -> None:
        super().__init__(node_ids, eid=eid)
        self.material = material
        self.lumped_mass = bool(lumped_mass)
        self.integration_order = int(integration_order)
        self._points, self._weights = gauss_legendre_3d(self.integration_order)

    def required_dofs(self, available: tuple[DOF, ...]) -> tuple[DOF, ...]:
        return TRANSLATIONAL_DOFS

    # ------------------------------------------------------------- kinematics

    @staticmethod
    def shape_functions(xi: float, eta: float, zeta: float) -> np.ndarray:
        """Trilinear shape functions ``N`` at a natural point, shape ``(8,)``."""
        signs = _HEX8_NATURAL
        return 0.125 * (
            (1.0 + signs[:, 0] * xi)
            * (1.0 + signs[:, 1] * eta)
            * (1.0 + signs[:, 2] * zeta)
        )

    @staticmethod
    def shape_function_derivatives(xi: float, eta: float, zeta: float) -> np.ndarray:
        """``dN/d(xi, eta, zeta)`` at a natural point, shape ``(3, 8)``."""
        signs = _HEX8_NATURAL
        factors = 1.0 + signs * np.array([xi, eta, zeta], dtype=float)
        return 0.125 * np.array(
            [
                signs[:, 0] * factors[:, 1] * factors[:, 2],
                signs[:, 1] * factors[:, 0] * factors[:, 2],
                signs[:, 2] * factors[:, 0] * factors[:, 1],
            ],
            dtype=float,
        )

    def _solid_coords(self, coords: np.ndarray) -> np.ndarray:
        """The ``(8, 3)`` nodal coordinates."""
        points = np.asarray(coords, dtype=float).reshape(8, -1)
        if points.shape[1] != 3:
            raise ElementError(
                f"Hex8Element {self.node_ids} needs three coordinates per node, "
                f"got {points.shape[1]}"
            )
        return points

    def jacobian(
        self, coords: np.ndarray, xi: float, eta: float, zeta: float
    ) -> tuple[np.ndarray, float]:
        """``(dN/dx, det J)`` at a natural point; ``dN/dx`` has shape ``(3, 8)``."""
        points = self._solid_coords(coords)
        natural = self.shape_function_derivatives(xi, eta, zeta)
        jac = natural @ points
        det = float(np.linalg.det(jac))
        if det <= 0.0:
            raise ElementError(
                f"Hex8Element {self.node_ids} has a non-positive Jacobian ({det:g}) at "
                f"(xi, eta, zeta) = ({xi:g}, {eta:g}, {zeta:g}); the element is "
                "degenerate, inverted or its nodes are not in the face-by-face "
                "counter-clockwise order"
            )
        return np.linalg.solve(jac, natural), det

    def strain_displacement_matrix(
        self, coords: np.ndarray, xi: float, eta: float, zeta: float
    ) -> tuple[np.ndarray, float]:
        """``(B, det J)`` with ``B`` of shape ``(6, 24)`` in node-major DOF order."""
        gradient, det = self.jacobian(coords, xi, eta, zeta)
        b = np.zeros((6, 24), dtype=float)
        b[0, 0::3] = gradient[0]
        b[1, 1::3] = gradient[1]
        b[2, 2::3] = gradient[2]
        b[3, 0::3] = gradient[1]
        b[3, 1::3] = gradient[0]
        b[4, 1::3] = gradient[2]
        b[4, 2::3] = gradient[1]
        b[5, 0::3] = gradient[2]
        b[5, 2::3] = gradient[0]
        return b, det

    # --------------------------------------------------------------- physics

    @property
    def constitutive_matrix(self) -> np.ndarray:
        """3D elasticity matrix ``D`` for the element's material."""
        return solid_constitutive_matrix(self.material)

    def volume(self, coords: np.ndarray) -> float:
        """Element volume, integrated with the element's own quadrature rule."""
        return float(
            sum(
                weight * self.jacobian(coords, *point)[1]
                for point, weight in zip(self._points, self._weights, strict=True)
            )
        )

    def stiffness_matrix(self, coords: np.ndarray) -> np.ndarray:
        D = self.constitutive_matrix
        k = np.zeros((24, 24), dtype=float)
        for point, weight in zip(self._points, self._weights, strict=True):
            b, det = self.strain_displacement_matrix(coords, *point)
            k += (weight * det) * (b.T @ D @ b)
        return k

    def consistent_mass_matrix(self, coords: np.ndarray) -> np.ndarray:
        """``rho int N^T N dV`` regardless of the ``lumped_mass`` setting."""
        density = float(self.material.density)
        m = np.zeros((24, 24), dtype=float)
        if density == 0.0:
            return m
        for point, weight in zip(self._points, self._weights, strict=True):
            shape = self.shape_functions(*point)
            _, det = self.jacobian(coords, *point)
            block = np.outer(shape, shape) * (weight * det * density)
            for axis in range(3):
                m[axis::3, axis::3] += block
        return m

    def mass_matrix(self, coords: np.ndarray) -> np.ndarray:
        consistent = self.consistent_mass_matrix(coords)
        if not self.lumped_mass:
            return consistent
        return np.diag(consistent.sum(axis=1))

    def total_mass(self, coords: np.ndarray) -> float:
        return float(self.material.density) * self.volume(coords)

    # ------------------------------------------------------------ recovery

    def strain(
        self,
        coords: np.ndarray,
        displacements: np.ndarray,
        xi: float = 0.0,
        eta: float = 0.0,
        zeta: float = 0.0,
    ) -> np.ndarray:
        """Strain ``[exx, eyy, ezz, gxy, gyz, gzx]`` at a natural point.

        The centroid ``(0, 0, 0)`` is the default because it is the
        superconvergent point of the trilinear brick.
        """
        values = np.asarray(displacements, dtype=float).reshape(-1)
        if values.size != 24:
            raise ElementError(f"expected 24 nodal displacements, got {values.size}")
        b, _ = self.strain_displacement_matrix(coords, xi, eta, zeta)
        return b @ values

    def stress(
        self,
        coords: np.ndarray,
        displacements: np.ndarray,
        xi: float = 0.0,
        eta: float = 0.0,
        zeta: float = 0.0,
    ) -> np.ndarray:
        """Stress ``[sxx, syy, szz, sxy, syz, szx]`` at a natural point."""
        return self.constitutive_matrix @ self.strain(coords, displacements, xi, eta, zeta)
