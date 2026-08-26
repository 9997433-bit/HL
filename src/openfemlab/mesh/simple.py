"""Mesh generation helpers for 1D structures and lumped-parameter systems.

:class:`MeshBuilder` is the general entry point (add nodes and members by hand or
seed a straight line of elements); the module-level functions wrap the common
verification models used throughout the test suite.
"""

from __future__ import annotations

from collections.abc import Hashable, Sequence

import numpy as np

from ..core.elements import BeamElement2D, Quad4Element, SpringElement, TrussElement
from ..core.model import DOF, Material, Model, Section
from ..exceptions import ModelError

__all__ = [
    "MeshBuilder",
    "spring_mass_chain",
    "bar_mesh",
    "beam_mesh",
    "quad_plate_mesh",
    "truss_from_arrays",
]


class MeshBuilder:
    """Incremental node/element builder around a :class:`~openfemlab.core.model.Model`.

    Examples
    --------
    >>> mesh = MeshBuilder(dofs=("UX", "UY"))
    >>> mesh.add_node("a", 0.0, 0.0); mesh.add_node("b", 1.0, 0.0)   # doctest: +ELLIPSIS
    Node(...)
    Node(...)
    >>> _ = mesh.add_truss("a", "b", Material(2.1e11, 7850.0), Section(1e-4))
    >>> model = mesh.model
    """

    def __init__(self, dofs=(DOF.UX, DOF.UY, DOF.UZ), name: str = "mesh") -> None:
        self.model = Model(dofs=dofs, name=name)
        self._auto_node = 0

    # ----------------------------------------------------------------- nodes

    def add_node(self, node_id: Hashable | None = None, *coords):
        if node_id is None:
            node_id = self._next_id()
        return self.model.add_node(node_id, *coords)

    def _next_id(self) -> int:
        while self._auto_node in self.model._nodes:  # noqa: SLF001 - same package
            self._auto_node += 1
        node_id = self._auto_node
        self._auto_node += 1
        return node_id

    def line_nodes(
        self,
        start: Sequence[float],
        end: Sequence[float],
        num_elements: int,
        *,
        ids: Sequence[Hashable] | None = None,
    ) -> list[Hashable]:
        """Create ``num_elements + 1`` equally spaced nodes between two points."""
        if num_elements < 1:
            raise ModelError(f"num_elements must be >= 1, got {num_elements}")
        p0 = _as_point(start)
        p1 = _as_point(end)
        node_ids: list[Hashable] = []
        for i in range(num_elements + 1):
            fraction = i / num_elements
            point = p0 + fraction * (p1 - p0)
            node_id = None if ids is None else ids[i]
            node_ids.append(self.add_node(node_id, point).id)
        return node_ids

    # -------------------------------------------------------------- members

    def add_truss(self, node_a, node_b, material: Material, section: Section, **kwargs):
        return self.model.add_element(TrussElement((node_a, node_b), material, section, **kwargs))

    def add_beam(self, node_a, node_b, material: Material, section: Section, **kwargs):
        return self.model.add_element(BeamElement2D((node_a, node_b), material, section, **kwargs))

    def add_quad4(self, node_ids: Sequence[Hashable], material: Material, **kwargs):
        return self.model.add_element(Quad4Element(node_ids, material, **kwargs))

    def add_spring(self, node_a, node_b, stiffness: float, dof=DOF.UX):
        return self.model.add_element(SpringElement((node_a, node_b), stiffness, dof=dof))

    def add_grounded_spring(self, node_id, stiffness: float, dof=DOF.UX):
        return self.model.add_element(SpringElement((node_id,), stiffness, dof=dof))

    def chain(
        self,
        node_ids: Sequence[Hashable],
        factory,
    ) -> list:
        """Connect consecutive nodes with ``factory(node_a, node_b)`` elements."""
        return [factory(a, b) for a, b in zip(node_ids[:-1], node_ids[1:], strict=False)]

    # --------------------------------------------------------------- passthrough

    def fix(self, node_id, dofs=None) -> None:
        self.model.fix(node_id, dofs)

    def add_point_mass(self, node_id, mass: float, dofs=None) -> None:
        self.model.add_point_mass(node_id, mass, dofs)

    def build(self) -> Model:
        return self.model


def _as_point(value) -> np.ndarray:
    point = np.asarray(value, dtype=float).reshape(-1)
    if point.size > 3:
        raise ModelError(f"expected at most 3 coordinates, got {point.size}")
    padded = np.zeros(3, dtype=float)
    padded[: point.size] = point
    return padded


def spring_mass_chain(
    num_masses: int,
    stiffness: float | Sequence[float],
    mass: float | Sequence[float],
    *,
    fixed_start: bool = True,
    fixed_end: bool = False,
    spacing: float = 1.0,
    name: str = "spring-mass chain",
) -> Model:
    """Build a 1D chain of ``num_masses`` point masses linked by scalar springs.

    Node ``0`` is the (optionally fixed) ground node; masses live on nodes
    ``1..num_masses``. When ``fixed_end`` is true a closing spring ties the last
    mass to an extra fixed node, giving the classical fixed-fixed chain.

    Analytic frequencies for uniform ``k``/``m``:

    * fixed-free  ``omega_i = 2 sqrt(k/m) sin((2i-1) pi / (2 (2N+1)))``
    * fixed-fixed ``omega_i = 2 sqrt(k/m) sin(i pi / (2 (N+1)))``
    """
    if num_masses < 1:
        raise ModelError(f"num_masses must be >= 1, got {num_masses}")
    num_springs = num_masses + (1 if fixed_end else 0)
    stiffnesses = _broadcast(stiffness, num_springs, "stiffness")
    masses = _broadcast(mass, num_masses, "mass")

    model = Model(dofs=(DOF.UX,), name=name)
    num_nodes = num_masses + 1 + (1 if fixed_end else 0)
    for i in range(num_nodes):
        model.add_node(i, i * spacing, 0.0, 0.0)

    for i in range(num_springs):
        model.add_element(SpringElement((i, i + 1), stiffnesses[i], dof=DOF.UX))
    for i, value in enumerate(masses, start=1):
        model.add_point_mass(i, value, dofs=(DOF.UX,))

    if fixed_start:
        model.fix(0, (DOF.UX,))
    if fixed_end:
        model.fix(num_nodes - 1, (DOF.UX,))
    return model


def bar_mesh(
    length: float,
    num_elements: int,
    material: Material,
    section: Section,
    *,
    dofs=(DOF.UX,),
    fixed_start: bool = True,
    fixed_end: bool = False,
    direction: Sequence[float] = (1.0, 0.0, 0.0),
    origin: Sequence[float] = (0.0, 0.0, 0.0),
    lumped_mass: bool = False,
    tip_mass: float | None = None,
    name: str = "bar",
) -> Model:
    """Uniform axial bar discretized with ``num_elements`` truss elements.

    Continuum reference (wave speed ``c = sqrt(E/rho)``):

    * fixed-free  ``f_i = (2i-1) c / (4 L)``
    * fixed-fixed / free-free ``f_i = i c / (2 L)``
    """
    if length <= 0.0:
        raise ModelError(f"length must be positive, got {length}")
    axis = _as_point(direction)
    norm = float(np.linalg.norm(axis))
    if norm == 0.0:
        raise ModelError("direction vector must be non-zero")
    axis /= norm
    start = _as_point(origin)

    mesh = MeshBuilder(dofs=dofs, name=name)
    node_ids = mesh.line_nodes(start, start + axis * length, num_elements)
    mesh.chain(
        node_ids,
        lambda a, b: mesh.add_truss(a, b, material, section, lumped_mass=lumped_mass),
    )
    if fixed_start:
        mesh.fix(node_ids[0])
    if fixed_end:
        mesh.fix(node_ids[-1])
    if tip_mass:
        mesh.add_point_mass(node_ids[-1], tip_mass)
    return mesh.build()


def beam_mesh(
    length: float,
    num_elements: int,
    material: Material,
    section: Section,
    *,
    support: str = "cantilever",
    origin: Sequence[float] = (0.0, 0.0, 0.0),
    lumped_mass: bool = False,
    tip_mass: float | None = None,
    name: str = "beam",
) -> Model:
    """Uniform planar Euler-Bernoulli beam.

    ``support`` selects the boundary conditions: ``"cantilever"`` (clamped-free),
    ``"simply-supported"`` (pinned-pinned) or ``"free"``.

    Cantilever reference: ``f_i = beta_i^2 / (2 pi) sqrt(E I / (rho A L^4))``
    with ``beta_i L = 1.875104, 4.694091, 7.854757, ...``
    """
    supports = {"cantilever", "simply-supported", "free"}
    if support not in supports:
        raise ModelError(f"unknown support {support!r}; expected one of {sorted(supports)}")
    if length <= 0.0:
        raise ModelError(f"length must be positive, got {length}")

    mesh = MeshBuilder(dofs=(DOF.UX, DOF.UY, DOF.RZ), name=name)
    start = _as_point(origin)
    node_ids = mesh.line_nodes(start, start + np.array([length, 0.0, 0.0]), num_elements)
    mesh.chain(
        node_ids,
        lambda a, b: mesh.add_beam(a, b, material, section, lumped_mass=lumped_mass),
    )

    if support == "cantilever":
        mesh.fix(node_ids[0])
    elif support == "simply-supported":
        mesh.fix(node_ids[0], (DOF.UX, DOF.UY))
        mesh.fix(node_ids[-1], (DOF.UY,))
    if tip_mass:
        mesh.add_point_mass(node_ids[-1], tip_mass, dofs=(DOF.UY,))
    return mesh.build()


def quad_plate_mesh(
    length: float,
    height: float,
    num_x: int,
    num_y: int,
    material: Material,
    *,
    thickness: float = 1.0,
    plane: str = "stress",
    support: str = "cantilever",
    origin: Sequence[float] = (0.0, 0.0, 0.0),
    lumped_mass: bool = False,
    integration_order: int = 2,
    name: str = "quad plate",
) -> Model:
    """Structured ``num_x x num_y`` grid of QUAD4 elements in the XY plane.

    Nodes are numbered row major (``id = row * (num_x + 1) + column``, with the
    row index running along Y), so ``0`` is the origin corner and
    ``(num_x + 1) * (num_y + 1) - 1`` the far corner. Element connectivity is
    counter-clockwise.

    ``support`` selects the boundary conditions: ``"cantilever"`` clamps the
    ``x = origin_x`` edge, ``"free"`` leaves the plate unsupported (three
    rigid-body modes), ``"simply-supported"`` pins the two vertical edges in Y
    and the lower-left node in X.
    """
    supports = {"cantilever", "free", "simply-supported"}
    if support not in supports:
        raise ModelError(f"unknown support {support!r}; expected one of {sorted(supports)}")
    if length <= 0.0 or height <= 0.0:
        raise ModelError(f"length and height must be positive, got {length} and {height}")
    if num_x < 1 or num_y < 1:
        raise ModelError(f"num_x and num_y must be >= 1, got {num_x} and {num_y}")

    start = _as_point(origin)
    model = Model(dofs=(DOF.UX, DOF.UY), name=name)

    def node_id(column: int, row: int) -> int:
        return row * (num_x + 1) + column

    for row in range(num_y + 1):
        for column in range(num_x + 1):
            model.add_node(
                node_id(column, row),
                start[0] + length * column / num_x,
                start[1] + height * row / num_y,
                start[2],
            )

    for row in range(num_y):
        for column in range(num_x):
            model.add_element(
                Quad4Element(
                    (
                        node_id(column, row),
                        node_id(column + 1, row),
                        node_id(column + 1, row + 1),
                        node_id(column, row + 1),
                    ),
                    material,
                    thickness=thickness,
                    plane=plane,
                    lumped_mass=lumped_mass,
                    integration_order=integration_order,
                )
            )

    if support == "cantilever":
        model.fix_nodes([node_id(0, row) for row in range(num_y + 1)])
    elif support == "simply-supported":
        model.fix_nodes([node_id(0, row) for row in range(num_y + 1)], (DOF.UY,))
        model.fix_nodes([node_id(num_x, row) for row in range(num_y + 1)], (DOF.UY,))
        model.fix(node_id(0, 0), (DOF.UX,))
    return model


def truss_from_arrays(
    coordinates,
    connectivity,
    material: Material,
    section: Section,
    *,
    dofs=(DOF.UX, DOF.UY, DOF.UZ),
    lumped_mass: bool = False,
    name: str = "truss",
) -> Model:
    """Build a truss from a ``(n_nodes, ndim)`` coordinate array and an
    ``(n_elements, 2)`` connectivity array of node indices."""
    coords = np.atleast_2d(np.asarray(coordinates, dtype=float))
    conn = np.atleast_2d(np.asarray(connectivity, dtype=int))
    if conn.shape[1] != 2:
        raise ModelError(f"connectivity must have two columns, got {conn.shape[1]}")
    if conn.size and (conn.min() < 0 or conn.max() >= coords.shape[0]):
        raise ModelError("connectivity references a node index outside the coordinate array")

    model = Model(dofs=dofs, name=name)
    for index, point in enumerate(coords):
        model.add_node(index, point)
    for a, b in conn:
        model.add_element(
            TrussElement((int(a), int(b)), material, section, lumped_mass=lumped_mass)
        )
    return model


def _broadcast(value, count: int, label: str) -> np.ndarray:
    array = np.atleast_1d(np.asarray(value, dtype=float))
    if array.size == 1:
        array = np.full(count, float(array[0]))
    if array.size != count:
        raise ModelError(f"expected 1 or {count} {label} values, got {array.size}")
    return array
