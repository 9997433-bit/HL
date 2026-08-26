"""Mesh generation helpers for 1D structures and lumped-parameter systems.

:class:`MeshBuilder` is the general entry point (add nodes and members by hand or
seed a straight line of elements); the module-level functions wrap the common
verification models used throughout the test suite.
"""

from __future__ import annotations

from collections.abc import Hashable, Sequence

import numpy as np

from ..core.elements import (
    BeamElement2D,
    BeamElement3D,
    Hex8Element,
    Quad4Element,
    ShellQuad4Element,
    SpringElement,
    Tet4Element,
    TrussElement,
)
from ..core.model import DOF, Material, Model, Section
from ..exceptions import ModelError

__all__ = [
    "MeshBuilder",
    "spring_mass_chain",
    "bar_mesh",
    "beam_mesh",
    "quad_plate_mesh",
    "shell_plate_mesh",
    "tet_block_mesh",
    "hex_block_mesh",
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

    def add_beam3d(self, node_a, node_b, material: Material, section: Section, **kwargs):
        return self.model.add_element(BeamElement3D((node_a, node_b), material, section, **kwargs))

    def add_quad4(self, node_ids: Sequence[Hashable], material: Material, **kwargs):
        return self.model.add_element(Quad4Element(node_ids, material, **kwargs))

    def add_shell_quad4(self, node_ids: Sequence[Hashable], material: Material, **kwargs):
        return self.model.add_element(ShellQuad4Element(node_ids, material, **kwargs))

    def add_tet4(self, node_ids: Sequence[Hashable], material: Material, **kwargs):
        return self.model.add_element(Tet4Element(node_ids, material, **kwargs))

    def add_hex8(self, node_ids: Sequence[Hashable], material: Material, **kwargs):
        return self.model.add_element(Hex8Element(node_ids, material, **kwargs))

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


def shell_plate_mesh(
    length: float,
    width: float,
    num_x: int,
    num_y: int,
    material: Material,
    *,
    thickness: float,
    support: str = "cantilever",
    origin: Sequence[float] = (0.0, 0.0, 0.0),
    lumped_mass: bool = False,
    rotary_inertia: bool = False,
    integration_order: int = 2,
    drilling_factor: float = 1e-3,
    name: str = "shell plate",
) -> Model:
    """Structured ``num_x x num_y`` grid of flat shell facets in the XY plane.

    Nodes are numbered row major (``id = row * (num_x + 1) + column``, with the
    row index running along Y) exactly as in :func:`quad_plate_mesh`, so the
    membrane-only and shell discretizations of the same rectangle share a node
    set; the model carries all six DOFs.

    ``support`` selects the boundary conditions: ``"cantilever"`` clamps the
    ``x = origin_x`` edge in all six DOFs, ``"free"`` leaves the plate
    unsupported (six rigid-body modes), ``"simply-supported"`` holds all four
    edges immovable in translation and blocks the edge rotation that ``w = 0``
    along an edge already implies -- the *hard* simple support whose thin-plate
    limit is the Navier solution.
    """
    supports = {"cantilever", "free", "simply-supported"}
    if support not in supports:
        raise ModelError(f"unknown support {support!r}; expected one of {sorted(supports)}")
    if length <= 0.0 or width <= 0.0:
        raise ModelError(f"length and width must be positive, got {length} and {width}")
    if num_x < 1 or num_y < 1:
        raise ModelError(f"num_x and num_y must be >= 1, got {num_x} and {num_y}")

    start = _as_point(origin)
    model = Model(dofs=(DOF.UX, DOF.UY, DOF.UZ, DOF.RX, DOF.RY, DOF.RZ), name=name)

    def node_id(column: int, row: int) -> int:
        return row * (num_x + 1) + column

    for row in range(num_y + 1):
        for column in range(num_x + 1):
            model.add_node(
                node_id(column, row),
                start[0] + length * column / num_x,
                start[1] + width * row / num_y,
                start[2],
            )

    for row in range(num_y):
        for column in range(num_x):
            model.add_element(
                ShellQuad4Element(
                    (
                        node_id(column, row),
                        node_id(column + 1, row),
                        node_id(column + 1, row + 1),
                        node_id(column, row + 1),
                    ),
                    material,
                    thickness=thickness,
                    lumped_mass=lumped_mass,
                    rotary_inertia=rotary_inertia,
                    integration_order=integration_order,
                    drilling_factor=drilling_factor,
                )
            )

    if support == "cantilever":
        model.fix_nodes([node_id(0, row) for row in range(num_y + 1)])
    elif support == "simply-supported":
        x_edges = [node_id(column, row) for column in (0, num_x) for row in range(num_y + 1)]
        y_edges = [node_id(column, row) for row in (0, num_y) for column in range(num_x + 1)]
        model.fix_nodes(x_edges + y_edges, (DOF.UX, DOF.UY, DOF.UZ))
        model.fix_nodes(x_edges, (DOF.RX,))
        model.fix_nodes(y_edges, (DOF.RY,))
    return model


def _box_grid(
    model: Model,
    length: float,
    width: float,
    height: float,
    num_x: int,
    num_y: int,
    num_z: int,
    origin: Sequence[float],
    support: str,
    supports: set[str],
):
    """Validate a structured box, fill ``model`` with its nodes, return ``node_id``.

    Nodes are numbered ``id = (k (num_y + 1) + j) (num_x + 1) + i`` with ``i``
    running along X, so ``0`` sits at ``origin`` and the last id at the far
    corner. Shared by the tetrahedral and hexahedral block generators so both
    number their grids identically.
    """
    if support not in supports:
        raise ModelError(f"unknown support {support!r}; expected one of {sorted(supports)}")
    for label, value in (("length", length), ("width", width), ("height", height)):
        if value <= 0.0:
            raise ModelError(f"{label} must be positive, got {value}")
    for label, value in (("num_x", num_x), ("num_y", num_y), ("num_z", num_z)):
        if value < 1:
            raise ModelError(f"{label} must be >= 1, got {value}")

    start = _as_point(origin)

    def node_id(i: int, j: int, k: int) -> int:
        return (k * (num_y + 1) + j) * (num_x + 1) + i

    for k in range(num_z + 1):
        for j in range(num_y + 1):
            for i in range(num_x + 1):
                model.add_node(
                    node_id(i, j, k),
                    start[0] + length * i / num_x,
                    start[1] + width * j / num_y,
                    start[2] + height * k / num_z,
                )
    return node_id


def _cell_corners(node_id, i: int, j: int, k: int) -> list[int]:
    """The eight node ids of cell ``(i, j, k)``, indexed by ``di + 2 dj + 4 dk``."""
    return [
        node_id(i + (c & 1), j + ((c >> 1) & 1), k + ((c >> 2) & 1)) for c in range(8)
    ]


#: Kuhn (Freudenthal) subdivision of a cell into six tetrahedra, as indices into
#: the eight corners numbered ``di + 2 dj + 4 dk``. Every tetrahedron is ordered
#: for a positive volume, and because the subdivision is identical in every cell
#: the face diagonals of neighbouring cells agree, so the mesh is conforming.
_KUHN_TETRAHEDRA: tuple[tuple[int, int, int, int], ...] = (
    (0, 1, 3, 7),
    (0, 1, 7, 5),
    (0, 2, 7, 3),
    (0, 2, 6, 7),
    (0, 4, 5, 7),
    (0, 4, 7, 6),
)


def tet_block_mesh(
    length: float,
    width: float,
    height: float,
    num_x: int,
    num_y: int,
    num_z: int,
    material: Material,
    *,
    support: str = "cantilever",
    origin: Sequence[float] = (0.0, 0.0, 0.0),
    lumped_mass: bool = False,
    name: str = "tet block",
) -> Model:
    """Structured ``num_x x num_y x num_z`` box of cells, each split into six TET4s.

    Nodes are numbered ``id = (k (num_y + 1) + j) (num_x + 1) + i`` with ``i``
    running along X, so ``0`` sits at ``origin`` and the last id at the far
    corner. Each cell is subdivided by the Kuhn triangulation, which yields six
    positive-volume tetrahedra and stays conforming across cell faces.

    ``support`` selects the boundary conditions: ``"cantilever"`` clamps the
    ``x = origin_x`` face, ``"free"`` leaves the block unsupported (six
    rigid-body modes).
    """
    model = Model(dofs=(DOF.UX, DOF.UY, DOF.UZ), name=name)
    node_id = _box_grid(
        model, length, width, height, num_x, num_y, num_z, origin, support,
        {"cantilever", "free"},
    )

    for k in range(num_z):
        for j in range(num_y):
            for i in range(num_x):
                corners = _cell_corners(node_id, i, j, k)
                for tet in _KUHN_TETRAHEDRA:
                    model.add_element(
                        Tet4Element([corners[c] for c in tet], material, lumped_mass=lumped_mass)
                    )

    if support == "cantilever":
        model.fix_nodes([node_id(0, j, k) for k in range(num_z + 1) for j in range(num_y + 1)])
    return model


#: The HEX8 corner order (``-zeta`` face counter-clockwise, then ``+zeta``) as
#: indices into the ``di + 2 dj + 4 dk`` corner numbering of a structured cell.
_HEX8_CORNERS: tuple[int, ...] = (0, 1, 3, 2, 4, 5, 7, 6)


def hex_block_mesh(
    length: float,
    width: float,
    height: float,
    num_x: int,
    num_y: int,
    num_z: int,
    material: Material,
    *,
    support: str = "cantilever",
    origin: Sequence[float] = (0.0, 0.0, 0.0),
    lumped_mass: bool = False,
    integration_order: int = 2,
    name: str = "hex block",
) -> Model:
    """Structured ``num_x x num_y x num_z`` grid of HEX8 bricks.

    Nodes are numbered exactly as in :func:`tet_block_mesh`
    (``id = (k (num_y + 1) + j) (num_x + 1) + i``), so the two generators
    produce interchangeable node sets for the same box and the same element
    can be compared against either discretization.

    ``support`` selects the boundary conditions: ``"cantilever"`` clamps the
    ``x = origin_x`` face, ``"free"`` leaves the block unsupported (six
    rigid-body modes), ``"simply-supported"`` restrains the two ``x`` faces
    transversally and one corner axially.
    """
    model = Model(dofs=(DOF.UX, DOF.UY, DOF.UZ), name=name)
    node_id = _box_grid(
        model, length, width, height, num_x, num_y, num_z, origin, support,
        {"cantilever", "free", "simply-supported"},
    )

    for k in range(num_z):
        for j in range(num_y):
            for i in range(num_x):
                corners = _cell_corners(node_id, i, j, k)
                model.add_element(
                    Hex8Element(
                        [corners[c] for c in _HEX8_CORNERS],
                        material,
                        lumped_mass=lumped_mass,
                        integration_order=integration_order,
                    )
                )

    root = [node_id(0, j, k) for k in range(num_z + 1) for j in range(num_y + 1)]
    tip = [node_id(num_x, j, k) for k in range(num_z + 1) for j in range(num_y + 1)]
    if support == "cantilever":
        model.fix_nodes(root)
    elif support == "simply-supported":
        model.fix_nodes(root + tip, (DOF.UY, DOF.UZ))
        model.fix(node_id(0, 0, 0), (DOF.UX,))
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
