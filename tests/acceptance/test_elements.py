"""M7 element-library acceptance suite (``docs/ACCEPTANCE_CRITERIA.md`` section 8).

Implemented here
----------------
- **AC-ELEM-001** (oracle, MS-8.3) — the patch test: a multi-element patch with
  displaced interior nodes, driven on its boundary by a linear displacement
  field, reproduces that field in the interior and the corresponding constant
  stress in every element, to machine precision.
- **AC-ELEM-002** (property, MS-8.3) — rigid-body motions produce no nodal force,
  no strain and no strain energy on a distorted element, and a free structure
  shows exactly the expected number of zero-energy modes and no spurious one.
- **AC-ELEM-003** (property, MS-8.4) — the discretization error of the first
  natural frequency falls quadratically under uniform refinement against the
  closed-form axial spectrum of a continuum bar.

Each criterion is checked on **every** element family of MS-8.2 (QUAD4, TET4,
HEX8, SHELL4) through the shared ``ELEMENT_CASES`` table, so a new formulation
is covered by adding one row rather than a new test. The developer suites
``tests/test_quad4.py``, ``tests/test_tet4.py``, ``tests/test_hex8.py`` and
``tests/test_shell_quad4.py`` go deeper per element; what this file gates is
the property the *library* must hold uniformly.

What the shell row changes, and why the table had to widen for it
-----------------------------------------------------------------
``ShellQuad4Element`` is the first formulation whose nodes carry rotations, so
three things that were constants of the suite became properties of the row:

- **The state.** A continuum row prescribes one linear displacement field; the
  shell row prescribes a constant membrane strain *and* a constant curvature at
  once, because a facet that reproduced only the first would still be an
  inadmissible plate. Its recovered quantities are correspondingly the membrane
  stress and the bending moment, plus the transverse shear, which the exact
  state leaves at zero.
- **The frame.** A facet reports its resultants in its own geometry-derived
  frame, which is not the frame the field is written in. The shell patch is
  therefore laid on a plane that is neither global nor axis-aligned — so the
  facet frames, the node-block rotation and the assembly are all exercised
  rather than collapsing to the identity — and every expected resultant is
  rotated into the reporting facet's frame before it is compared.
- **The rigid-body set.** Rotation about the facet normal is not part of the
  shell's kinematics: the director does not turn with it, and the drilling
  stiffness that keeps the local matrix non-singular is a penalty on a
  fictitious DOF, not a physical rotation field (MS-8.2). The six rigid-body
  motions of the shell row therefore carry the director rotation with its
  normal component projected out, which is what an unsupported shell assembly
  actually moves along — and AC-ELEM-002's free-assembly count confirms it.

The oracles are the exact linear displacement field and constant-curvature bowl
(patch), the continuum bar frequency ``c/(4L)``, ``c = sqrt(E/rho)``, and the
Reissner-Mindlin Navier plate spectrum (convergence), so no gate is measured
against a previous run of the code under test.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field

import numpy as np
import pytest

from openfemlab.core.assembly import assemble_stiffness
from openfemlab.core.elements import (
    Element,
    Hex8Element,
    Quad4Element,
    ShellQuad4Element,
    Tet4Element,
    plane_constitutive_matrix,
    solid_constitutive_matrix,
)
from openfemlab.core.model import DOF, Material, Model
from openfemlab.mesh.simple import (
    _KUHN_TETRAHEDRA,
    hex_block_mesh,
    quad_plate_mesh,
    shell_plate_mesh,
    tet_block_mesh,
)
from openfemlab.solver.modal import ModalSolver

from ._support import criterion

#: Gate of AC-ELEM-001: "exact to machine precision", relative to the largest
#: prescribed displacement. The measured defect is ~1e-16 on every continuum
#: family; see ``ShellElementCase.patch_tolerance`` for the shell.
PATCH_TOLERANCE = 1e-12

#: Gate of AC-ELEM-001 for the recovered stress, which passes through ``D``.
STRESS_TOLERANCE = 1e-9

#: Gate of AC-ELEM-002, relative to ``max|K| * ||d||^2``.
RIGID_TOLERANCE = 1e-10

#: Where AC-ELEM-002 puts the floor of the elastic spectrum, relative to the
#: largest eigenvalue: below it a mode counts as zero energy. The continuum
#: families leave the rigid-body zeros at ~1e-16 of the largest eigenvalue and
#: their first elastic mode above 5e-2 of it, so any cut in between would do;
#: see ``ShellElementCase.elastic_floor`` for the row that has an opinion.
ELASTIC_FLOOR = 1e-3

#: Gates of AC-ELEM-003: error ratio per halving (4 for a quadratic rate) and
#: the absolute error the finest mesh must reach.
CONVERGENCE_RATIO = 3.6
CONVERGENCE_ERROR = 1e-3

#: A recovered constant state only gates a formulation if every one of its
#: components is genuinely loaded. The floor is relative to the state's own
#: largest component, which is what lets one guard serve states as far apart in
#: magnitude as a membrane stress and a thin-shell moment resultant; ``0.05``
#: admits the smallest component of the spatial patch stress (``sigma_yy``, 9 %
#: of ``sigma_xx``) while still rejecting a trivially zero one.
STATE_FLOOR = 0.05

#: Patch material: soft and compressible, so no gate hides behind stiffness.
PATCH_MATERIAL = Material(E=1.0e6, density=1.0, nu=0.25)

#: Convergence material: ``nu = 0`` decouples the axial direction, which is what
#: makes the 1D continuum bar the exact oracle for a 2D/3D mesh.
BAR_MATERIAL = Material(E=2.1e11, density=7850.0, nu=0.0)
BAR_LENGTH = 1.0

#: Extent of the patch box and the linear field prescribed on its boundary.
PATCH_SPAN = np.array([0.24, 0.12, 0.18])
PATCH_GRADIENT = 1e-3 * np.array([[1.0, 0.4, -0.2], [0.3, -0.5, 0.5], [-0.1, 0.2, 0.8]])

#: Cells per axis of the patch: 9 planar or 27 spatial cells.
PATCH_CELLS = 3

#: How far interior patch nodes are pulled off the regular grid, as a fraction
#: of the cell size. The offsets are deterministic (a criterion only counts if
#: its test is deterministic) and large enough that no element stays a
#: parallelogram or parallelepiped.
PATCH_DISTORTION = 0.2

#: HEX8 corner order as indices into the ``di + 2 dj + 4 dk`` cell numbering.
_HEX8_CORNERS = (0, 1, 3, 2, 4, 5, 7, 6)

#: The six nodal DOFs of a shell facet, in the order the element expects them.
SHELL_DOFS = (DOF.UX, DOF.UY, DOF.UZ, DOF.RX, DOF.RY, DOF.RZ)

#: Thickness of the shell rows. Shared with the QUAD4 row so the membrane half
#: of the shell patch is the QUAD4 patch, on the same material and thickness.
SHELL_THICKNESS = 0.001

#: Constant curvature the shell rows prescribe beside ``PATCH_GRADIENT``: large
#: enough that the bowl's rise over the patch is comparable with the in-plane
#: displacement, so neither state can hide behind the other.
PATCH_CURVATURE = np.array([2.0e-2, -1.0e-2, 6.0e-3])

#: Local DOF positions of the membrane inside the node-major 24-DOF ordering.
_SHELL_MEMBRANE_DOFS = [6 * node + axis for node in range(4) for axis in (0, 1)]


def _rotation(axis: Sequence[float], angle: float) -> np.ndarray:
    """Rodrigues rotation about ``axis`` by ``angle``."""
    unit = np.asarray(axis, dtype=float) / np.linalg.norm(axis)
    cross = np.array(
        [[0.0, -unit[2], unit[1]], [unit[2], 0.0, -unit[0]], [-unit[1], unit[0], 0.0]]
    )
    return np.eye(3) + np.sin(angle) * cross + (1.0 - np.cos(angle)) * (cross @ cross)


#: Where the shell fixtures are placed: the rows ``[e_x, e_y, e_z]`` of a plane
#: that shares no axis with the global frame, and an origin away from it. A
#: shell laid in the global XY plane would leave every facet rotation an
#: identity and gate none of the machinery that makes the element a shell.
SHELL_FRAME = _rotation([0.3, -0.7, 0.5], 0.9)
SHELL_ORIGIN = np.array([1.5, -0.4, 2.0])

#: Simply supported plate of the AC-ELEM-003 bending row, and its refinement
#: ladder. The mesh is square so the ``(1, 1)`` mode is the fundamental one.
PLATE_MATERIAL = Material(E=2.1e11, density=7850.0, nu=0.3)
PLATE_SIDE = 1.0
PLATE_THICKNESS = 0.005
PLATE_COUNTS = (4, 8, 16)

#: Absolute gate of the bending row's finest mesh. The plate oracle's error
#: constant is an order of magnitude above the bar's -- 4.3e-3 at 16 elements
#: per side against the bar's 4.0e-4 at 16 elements -- so the finest-mesh gate
#: is the one AC-ELEM-003 number that a bending row cannot share; the rate
#: gates (``CONVERGENCE_RATIO``, and the observed order) are unchanged.
PLATE_CONVERGENCE_ERROR = 6e-3


def _interior_offset(index: int) -> np.ndarray:
    """Deterministic, irrational-looking displacement of interior patch node ``index``."""
    return np.array(
        [
            np.sin(1.3 * index + 0.4),
            np.cos(2.1 * index + 1.1),
            np.sin(0.7 * index + 2.3),
        ]
    )


def _voigt_strain(gradient: np.ndarray, ndim: int) -> np.ndarray:
    """Engineering strain of a displacement gradient, in the family's Voigt order."""
    g = np.asarray(gradient, dtype=float)
    if ndim == 2:
        return np.array([g[0, 0], g[1, 1], g[0, 1] + g[1, 0]])
    return np.array(
        [g[0, 0], g[1, 1], g[2, 2], g[0, 1] + g[1, 0], g[1, 2] + g[2, 1], g[0, 2] + g[2, 0]]
    )


def _linear_field(coords: np.ndarray, ndim: int) -> np.ndarray:
    """Nodal values of ``u = PATCH_GRADIENT x``, node-major, ``ndim`` per node."""
    points = np.asarray(coords, dtype=float)[:, :ndim]
    gradient = PATCH_GRADIENT[:ndim, :ndim]
    return (points @ gradient.T).reshape(-1)


def _rotate_planar(voigt: np.ndarray, rotation: np.ndarray) -> np.ndarray:
    """A symmetric 2D tensor ``[xx, yy, xy]`` seen from a frame turned by ``rotation``."""
    xx, yy, xy = voigt
    turned = rotation @ np.array([[xx, xy], [xy, yy]], dtype=float) @ rotation.T
    return np.array([turned[0, 0], turned[1, 1], turned[0, 1]])


def _plane_field(points: np.ndarray) -> np.ndarray:
    """Nodal shell DOFs of the combined constant membrane and curvature state.

    ``points`` are in-plane coordinates and the result is ``(n, 6)`` in the same
    frame. The in-plane displacements follow ``u = G x`` with the planar block of
    :data:`PATCH_GRADIENT`; the transverse displacement is the constant-curvature
    bowl ``w = -(kxx x^2 + kyy y^2 + kxy x y) / 2`` and the rotations are tied to
    its slope, ``theta_x = dw/dy`` and ``theta_y = -dw/dx``, so the state carries
    no transverse shear anywhere. The drilling component is zero: rotation about
    the facet normal is not part of the shell kinematics, only of the penalty
    that regularizes it.
    """
    xy = np.asarray(points, dtype=float)[:, :2]
    x, y = xy[:, 0], xy[:, 1]
    kxx, kyy, kxy = PATCH_CURVATURE
    values = np.zeros((xy.shape[0], 6), dtype=float)
    values[:, :2] = xy @ PATCH_GRADIENT[:2, :2].T
    values[:, 2] = -0.5 * (kxx * x**2 + kyy * y**2 + kxy * x * y)
    values[:, 3] = -(kyy * y + 0.5 * kxy * x)
    values[:, 4] = kxx * x + 0.5 * kxy * y
    return values


def _to_global(values: np.ndarray, frame: np.ndarray) -> np.ndarray:
    """Rotate per-node ``(translation, rotation)`` triples out of ``frame`` into global axes."""
    triples = np.asarray(values, dtype=float).reshape(-1, 2, 3)
    return (triples @ np.asarray(frame, dtype=float)).reshape(-1)


def _place(point: np.ndarray) -> np.ndarray:
    """A plane coordinate pair, placed in space on the shell fixtures' plane."""
    planar = np.zeros(3, dtype=float)
    planar[: len(point)] = point
    return SHELL_ORIGIN + planar @ SHELL_FRAME


def _grid_ids(cells: Sequence[int]):
    """Row-major node numbering of a structured grid of ``cells`` cells per axis."""
    counts = [n + 1 for n in cells]

    def node_id(*index: int) -> int:
        number = 0
        for value, count in zip(reversed(index), reversed(counts), strict=True):
            number = number * count + value
        # ``index`` runs (i, j[, k]) with i fastest, matching the mesh generators.
        return number

    return node_id


def _distorted_grid(cells: Sequence[int]) -> dict[int, np.ndarray]:
    """Node coordinates of a structured grid; only its interior nodes are moved."""
    node_id = _grid_ids(cells)
    cell = PATCH_SPAN[: len(cells)] / np.array(cells, dtype=float)
    coordinates: dict[int, np.ndarray] = {}
    interior = 0
    for index in np.ndindex(*[n + 1 for n in reversed(cells)]):
        position = tuple(reversed(index))
        point = np.array(position, dtype=float) * cell
        if all(0 < value < count for value, count in zip(position, cells, strict=True)):
            point = point + PATCH_DISTORTION * cell * _interior_offset(interior)[: len(cells)]
            interior += 1
        coordinates[node_id(*position)] = point
    return coordinates


def _on_patch_boundary(point: np.ndarray) -> bool:
    """Whether a grid node sits on the face of the patch box, and is thus driven."""
    span = PATCH_SPAN[: len(point)]
    return bool(np.any(np.isclose(point, 0.0)) or np.any(np.isclose(point, span)))


def _patch_nodes(model: Model, cells: Sequence[int]) -> dict[int, np.ndarray]:
    """Fill ``model`` with a distorted structured grid; only interior nodes move."""
    coordinates = _distorted_grid(cells)
    for identifier, point in coordinates.items():
        model.add_node(identifier, *point)
    return coordinates


def _quad_cells(cells: Sequence[int]):
    """Yield the four corner ids of every cell of a planar grid, counter-clockwise."""
    node_id = _grid_ids(cells)
    for j in range(cells[1]):
        for i in range(cells[0]):
            yield (
                node_id(i, j),
                node_id(i + 1, j),
                node_id(i + 1, j + 1),
                node_id(i, j + 1),
            )


def _quad_patch() -> tuple[Model, dict[int, np.ndarray]]:
    cells = (PATCH_CELLS, PATCH_CELLS)
    model = Model(dofs=(DOF.UX, DOF.UY), name="quad4 patch")
    coordinates = _patch_nodes(model, cells)
    for corners in _quad_cells(cells):
        model.add_element(Quad4Element(corners, PATCH_MATERIAL, thickness=SHELL_THICKNESS))
    return model, coordinates


def _shell_patch() -> tuple[Model, dict[int, np.ndarray]]:
    """The planar patch of :func:`_quad_patch`, laid on the tilted shell plane.

    The returned coordinates stay *in the plane*: they are what the prescribed
    field is written from, while the model holds their placement in space.
    """
    cells = (PATCH_CELLS, PATCH_CELLS)
    coordinates = _distorted_grid(cells)
    model = Model(dofs=SHELL_DOFS, name="shell facet patch")
    for identifier, point in coordinates.items():
        model.add_node(identifier, _place(point))
    for corners in _quad_cells(cells):
        model.add_element(
            ShellQuad4Element(corners, PATCH_MATERIAL, thickness=SHELL_THICKNESS)
        )
    return model, coordinates


def _solid_patch(factory: Callable[[list[int]], Sequence[Element]]):
    cells = (PATCH_CELLS, PATCH_CELLS, PATCH_CELLS)
    model = Model(dofs=(DOF.UX, DOF.UY, DOF.UZ), name="solid patch")
    coordinates = _patch_nodes(model, cells)
    node_id = _grid_ids(cells)
    for k in range(cells[2]):
        for j in range(cells[1]):
            for i in range(cells[0]):
                corners = [
                    node_id(i + (c & 1), j + ((c >> 1) & 1), k + ((c >> 2) & 1))
                    for c in range(8)
                ]
                for element in factory(corners):
                    model.add_element(element)
    return model, coordinates


def _tet_patch() -> tuple[Model, dict[int, np.ndarray]]:
    return _solid_patch(
        lambda corners: [
            Tet4Element([corners[c] for c in tet], PATCH_MATERIAL) for tet in _KUHN_TETRAHEDRA
        ]
    )


def _hex_patch() -> tuple[Model, dict[int, np.ndarray]]:
    return _solid_patch(
        lambda corners: [Hex8Element([corners[c] for c in _HEX8_CORNERS], PATCH_MATERIAL)]
    )


def _quad_bar(num_elements: int) -> Model:
    model = quad_plate_mesh(
        BAR_LENGTH, 0.1, num_elements, 1, BAR_MATERIAL, thickness=0.01, support="cantilever"
    )
    model.fix_dof_globally((DOF.UY,))
    return model


def _shell_bar(num_elements: int) -> Model:
    """The bar of :func:`_quad_bar` as a shell strip, left with its axial DOF only.

    Suppressing the five non-axial DOFs is the same reduction the continuum rows
    make with ``UY``/``UZ``; what it leaves under the oracle is the facet's
    membrane, reached through the shell's own assembly and DOF bookkeeping.
    """
    model = shell_plate_mesh(
        BAR_LENGTH, 0.1, num_elements, 1, BAR_MATERIAL, thickness=0.01, support="cantilever"
    )
    model.fix_dof_globally((DOF.UY, DOF.UZ, DOF.RX, DOF.RY, DOF.RZ))
    return model


def _tet_bar(num_elements: int) -> Model:
    model = tet_block_mesh(
        BAR_LENGTH, 0.1, 0.1, num_elements, 1, 1, BAR_MATERIAL, support="cantilever"
    )
    model.fix_dof_globally((DOF.UY, DOF.UZ))
    return model


def _hex_bar(num_elements: int) -> Model:
    model = hex_block_mesh(
        BAR_LENGTH, 0.1, 0.1, num_elements, 1, 1, BAR_MATERIAL, support="cantilever"
    )
    model.fix_dof_globally((DOF.UY, DOF.UZ))
    return model


def _plate_mesh(num_elements: int) -> Model:
    return shell_plate_mesh(
        PLATE_SIDE,
        PLATE_SIDE,
        num_elements,
        num_elements,
        PLATE_MATERIAL,
        thickness=PLATE_THICKNESS,
        support="simply-supported",
    )


def _navier_mindlin_frequency(m: int = 1, n: int = 1) -> float:
    """``f_mn`` [Hz] of a hard simply supported Reissner-Mindlin plate, in Hz.

    The Kirchhoff Navier frequency ``omega_K^2 = D k^4 / (rho t)`` with
    ``k^2 = pi^2 (m^2 + n^2) / a^2`` is softened by the transverse shear the
    element carries, ``omega^2 = omega_K^2 / (1 + D k^2 / (kappa G t))``.
    Rotary inertia is absent from this closed form and from the element's
    default mass matrix alike (MS-8.2), so the two describe the same theory and
    the only error the gate sees is the discretization error -- which is what
    lets a *rate* be measured at all. Against the Kirchhoff form the error
    would instead stall at the plate's own shear correction.
    """
    rigidity = (
        PLATE_MATERIAL.E * PLATE_THICKNESS**3 / (12.0 * (1.0 - PLATE_MATERIAL.nu**2))
    )
    wavenumber = np.pi**2 * (m**2 + n**2) / PLATE_SIDE**2
    kirchhoff = np.sqrt(
        rigidity * wavenumber**2 / (PLATE_MATERIAL.density * PLATE_THICKNESS)
    )
    shear = ShellQuad4Element.shear_correction * PLATE_MATERIAL.shear_modulus * PLATE_THICKNESS
    return float(kirchhoff / np.sqrt(1.0 + rigidity * wavenumber / shear) / (2.0 * np.pi))


#: A distorted single element per family: no parallel edges, no planar symmetry.
_QUAD_COORDS = np.array(
    [[0.0, 0.0, 0.0], [2.0, -0.3, 0.0], [2.4, 1.6, 0.0], [0.5, 1.1, 0.0]], dtype=float
)
#: The same quadrilateral, placed off every global plane: a facet's whole point
#: is that it may sit at an arbitrary orientation in space.
_SHELL_COORDS = np.array([_place(point) for point in _QUAD_COORDS], dtype=float)
_TET_COORDS = np.array(
    [[0.1, -0.2, 0.05], [1.3, 0.1, -0.15], [0.4, 1.1, 0.2], [0.2, 0.3, 0.9]], dtype=float
)
_HEX_COORDS = np.array(
    [
        [0.05, -0.10, 0.02],
        [1.20, 0.08, -0.15],
        [1.35, 1.10, 0.12],
        [-0.08, 0.95, -0.05],
        [0.02, -0.05, 1.05],
        [1.10, 0.12, 0.90],
        [1.25, 1.05, 1.20],
        [0.10, 1.15, 1.02],
    ],
    dtype=float,
)


@dataclass(frozen=True)
class ElementCase:
    """One MS-8.2 formulation and the fixtures the three criteria need from it."""

    label: str
    ndim: int
    element: type[Element]
    coords: np.ndarray
    patch: Callable[[], tuple[Model, dict[int, np.ndarray]]]
    bar: Callable[[int], Model]
    #: Natural coordinates the recovered state is sampled at; empty for the
    #: constant-strain tetrahedron, whose recovery takes no point argument.
    sample_points: tuple[tuple[float, ...], ...] = ()
    kwargs: dict = field(default_factory=dict)

    @property
    def dofs(self) -> tuple[DOF, ...]:
        return (DOF.UX, DOF.UY) if self.ndim == 2 else (DOF.UX, DOF.UY, DOF.UZ)

    @property
    def rigid_modes(self) -> int:
        return 3 if self.ndim == 2 else 6

    @property
    def translations(self) -> int:
        """How many independent translation directions the element resolves."""
        return self.ndim

    @property
    def patch_cells(self) -> tuple[int, ...]:
        """Cells per axis of the patch grid."""
        return (PATCH_CELLS,) * self.ndim

    @property
    def patch_interior_dofs(self) -> int:
        """Equations the patch solves for -- the DOFs of its displaced nodes."""
        return len(self.dofs) * (PATCH_CELLS - 1) ** len(self.patch_cells)

    @property
    def patch_tolerance(self) -> float:
        return PATCH_TOLERANCE

    @property
    def elastic_floor(self) -> float:
        return ELASTIC_FLOOR

    @property
    def strain_samples(self) -> int:
        """How many ``(measure, sample point)`` pairs :meth:`strain_measures` yields."""
        return max(len(self.sample_points), 1)

    @property
    def stress_samples(self) -> int:
        """How many pairs :meth:`patch_stress_measures` yields per element."""
        return max(len(self.sample_points), 1)

    def bound(self, material: Material = PATCH_MATERIAL) -> Element:
        """The distorted single element, bound to a model that holds its nodes."""
        model = Model(dofs=self.dofs, name=self.label)
        for index, point in enumerate(self.coords):
            model.add_node(index, point)
        return model.add_element(
            self.element(range(len(self.coords)), material, **self.kwargs)
        )

    def constitutive_matrix(self) -> np.ndarray:
        if self.ndim == 2:
            return plane_constitutive_matrix(PATCH_MATERIAL, "stress")
        return solid_constitutive_matrix(PATCH_MATERIAL)

    def free_model(self) -> Model:
        """A small unsupported assembly, for the zero-energy mode count."""
        if self.ndim == 2:
            return quad_plate_mesh(0.3, 0.2, 3, 2, PATCH_MATERIAL, thickness=0.01, support="free")
        if self.element is Tet4Element:
            return tet_block_mesh(0.3, 0.2, 0.1, 2, 2, 2, PATCH_MATERIAL, support="free")
        return hex_block_mesh(0.3, 0.2, 0.1, 2, 2, 2, PATCH_MATERIAL, support="free")

    def plate_convergence(self) -> tuple[Callable[[int], Model], float] | None:
        """Bending refinement ladder and its oracle; ``None`` without bending DOFs."""
        return None

    # ------------------------------------------------------- prescribed state

    def nodal_field(self, element: Element, coords: np.ndarray) -> np.ndarray:
        """The exact state of AC-ELEM-001 as nodal DOFs of a single element."""
        return _linear_field(coords, self.ndim)

    def rigid_body_motions(self, element: Element, coords: np.ndarray) -> dict[str, np.ndarray]:
        """The ``3`` planar or ``6`` spatial rigid-body motions as nodal vectors."""
        points = np.asarray(coords, dtype=float)[:, : self.ndim]
        motions: dict[str, np.ndarray] = {}
        for axis in range(self.ndim):
            motions[f"translation {axis}"] = np.tile(np.eye(self.ndim)[axis], points.shape[0])
        if self.ndim == 2:
            rotation = np.empty_like(points)
            rotation[:, 0] = -points[:, 1]
            rotation[:, 1] = points[:, 0]
            motions["rotation z"] = rotation.reshape(-1)
        else:
            for axis in range(3):
                motions[f"rotation {axis}"] = np.cross(np.eye(3)[axis], points).reshape(-1)
        return motions

    # ------------------------------------------------------------- recovery

    def strain_measures(
        self, element: Element, coords: np.ndarray, displacements: np.ndarray
    ) -> Iterator[tuple[str, np.ndarray, np.ndarray]]:
        """Yield ``(label, recovered, constant)`` per strain measure and sample point.

        ``constant`` is the value :meth:`nodal_field` gives that measure, so the
        same generator serves AC-ELEM-001 (recovered == constant on the exact
        field) and AC-ELEM-002 (recovered == 0 on a rigid-body motion).
        """
        expected = _voigt_strain(PATCH_GRADIENT, self.ndim)
        for point in self.sample_points or ((),):
            yield "strain", element.strain(coords, displacements, *point), expected

    def patch_problem(self) -> tuple[Model, dict[int, float], np.ndarray]:
        """``(model, prescribed, exact)`` of the boundary-driven patch."""
        model, coordinates = self.patch()
        exact = np.zeros(model.num_dofs, dtype=float)
        prescribed: dict[int, float] = {}
        for node_id, point in coordinates.items():
            displacement = PATCH_GRADIENT[: self.ndim, : self.ndim] @ point[: self.ndim]
            on_boundary = _on_patch_boundary(point)
            for dof, value in zip(self.dofs, displacement, strict=True):
                index = model.dof_index(node_id, dof)
                exact[index] = value
                if on_boundary:
                    prescribed[index] = value
        return model, prescribed, exact

    def patch_stress_measures(
        self, model: Model, values: np.ndarray
    ) -> Iterator[tuple[str, np.ndarray, np.ndarray]]:
        """Yield ``(label, recovered, expected)`` for every element of the patch."""
        expected = self.constitutive_matrix() @ _voigt_strain(PATCH_GRADIENT, self.ndim)
        for element in model.elements:
            coords = model.node_coords(element.node_ids)
            local = values[element.global_dofs(model)]
            for point in self.sample_points or ((),):
                yield "stress", element.stress(coords, local, *point), expected


@dataclass(frozen=True)
class ShellElementCase(ElementCase):
    """The MS-8.2 flat shell facet: six DOFs per node and two constant states.

    Everything the criteria ask of a continuum element they ask of this one; the
    overrides below only say it in the shell's own vocabulary -- see the module
    docstring for why the state, the reporting frame and the rigid-body set all
    had to move from the suite onto the row.
    """

    @property
    def dofs(self) -> tuple[DOF, ...]:
        return SHELL_DOFS

    @property
    def patch_cells(self) -> tuple[int, ...]:
        """A surface formulation meshes a plane, so the patch is the planar one."""
        return (PATCH_CELLS, PATCH_CELLS)

    @property
    def patch_tolerance(self) -> float:
        """Looser than the continuum rows, and for a conditioning reason only.

        The facet couples a membrane going as ``t``, a bending rigidity going as
        ``t^3``, a shear penalty going as ``t`` and a drilling penalty at 1e-3 of
        the plate diagonal, which puts ``cond(K)`` of this patch at ~1e7 against
        ~1e4 for the continuum ones. The defect measured on that system is
        ~1e-12 rather than the continuum families' ~1e-16, so the gate sits two
        decades above the measurement exactly as ``PATCH_TOLERANCE`` does.
        """
        return 1e-10

    @property
    def elastic_floor(self) -> float:
        """Far below the continuum rows', and that is the formulation talking.

        The smallest elastic mode of a facet is the drilling penalty, which is
        1e-3 of the plate's rotational diagonal while the largest is a membrane
        going as ``t`` -- on this facet, 2e-8 of it. A cut chosen for a continuum
        element would swallow the very mode that makes the facet non-singular
        and report ten zero-energy modes instead of six.
        """
        return 1e-9

    @property
    def strain_samples(self) -> int:
        """Membrane strain, curvature and transverse shear, at every sample point."""
        return 3 * len(self.sample_points)

    @property
    def stress_samples(self) -> int:
        """Membrane stress and bending moment, at every sample point."""
        return 2 * len(self.sample_points)

    def free_model(self) -> Model:
        return shell_plate_mesh(
            0.3, 0.2, 3, 2, PATCH_MATERIAL, thickness=0.01, support="free"
        )

    def plate_convergence(self) -> tuple[Callable[[int], Model], float] | None:
        return _plate_mesh, _navier_mindlin_frequency()

    # ------------------------------------------------------- prescribed state

    def nodal_field(self, element: Element, coords: np.ndarray) -> np.ndarray:
        """The membrane-plus-curvature state, written in the facet's own frame.

        Writing it there and rotating out is what lets the recovered resultants
        be compared against the unrotated constants: the single-element tests
        ask whether the facet reproduces the state, not where it reports it.
        """
        local = _plane_field(element.local_coords(coords))
        return _to_global(local, element.local_frame(coords)[1])

    def rigid_body_motions(self, element: Element, coords: np.ndarray) -> dict[str, np.ndarray]:
        points = np.asarray(coords, dtype=float).reshape(-1, 3)
        frame = element.local_frame(coords)[1]
        motions: dict[str, np.ndarray] = {}
        for axis in range(3):
            motion = np.zeros(6 * points.shape[0], dtype=float)
            motion[axis::6] = 1.0
            motions[f"translation {axis}"] = motion
        for axis in range(3):
            omega = np.eye(3)[axis]
            # The director turns with the body, but not about itself: the
            # drilling DOF is fictitious, so a rigid motion leaves it at rest.
            director = (frame @ omega) * np.array([1.0, 1.0, 0.0]) @ frame
            motion = np.zeros(6 * points.shape[0], dtype=float)
            for node, offset in enumerate(points - points.mean(axis=0)):
                motion[6 * node : 6 * node + 3] = np.cross(omega, offset)
                motion[6 * node + 3 : 6 * node + 6] = director
            motions[f"rotation {axis}"] = motion
        return motions

    # ------------------------------------------------------------- recovery

    def strain_measures(
        self, element: Element, coords: np.ndarray, displacements: np.ndarray
    ) -> Iterator[tuple[str, np.ndarray, np.ndarray]]:
        local_xy = element.local_coords(coords)
        local = element.local_displacements(coords, displacements)
        membrane = local[_SHELL_MEMBRANE_DOFS]
        for point in self.sample_points:
            yield (
                "membrane strain",
                element.membrane.strain(local_xy, membrane, *point),
                _voigt_strain(PATCH_GRADIENT, 2),
            )
            yield (
                "curvature",
                element.curvature(coords, displacements, *point),
                PATCH_CURVATURE,
            )
            yield (
                "transverse shear",
                element.transverse_shear(coords, displacements, *point),
                np.zeros(2),
            )

    def patch_problem(self) -> tuple[Model, dict[int, float], np.ndarray]:
        model, coordinates = self.patch()
        planar = _plane_field(np.array(list(coordinates.values()), dtype=float))
        exact = np.zeros(model.num_dofs, dtype=float)
        prescribed: dict[int, float] = {}
        for row, (node_id, point) in enumerate(coordinates.items()):
            on_boundary = _on_patch_boundary(point)
            for dof, value in zip(self.dofs, _to_global(planar[row], SHELL_FRAME), strict=True):
                index = model.dof_index(node_id, dof)
                exact[index] = value
                if on_boundary:
                    prescribed[index] = value
        return model, prescribed, exact

    def patch_stress_measures(
        self, model: Model, values: np.ndarray
    ) -> Iterator[tuple[str, np.ndarray, np.ndarray]]:
        membrane = plane_constitutive_matrix(PATCH_MATERIAL, "stress") @ _voigt_strain(
            PATCH_GRADIENT, 2
        )
        for element in model.elements:
            coords = model.node_coords(element.node_ids)
            local = values[element.global_dofs(model)]
            # A facet reports in a frame its own node order fixes, which differs
            # from the patch plane by an in-plane turn; rotate the constants
            # rather than compare them in the wrong axes.
            turn = (element.local_frame(coords)[1] @ SHELL_FRAME.T)[:2, :2]
            expected_stress = _rotate_planar(membrane, turn)
            expected_moment = _rotate_planar(
                element.bending_constitutive_matrix @ PATCH_CURVATURE, turn
            )
            for point in self.sample_points:
                yield (
                    "membrane stress",
                    element.membrane_stress(coords, local, *point),
                    expected_stress,
                )
                yield (
                    "bending moment",
                    element.bending_moment(coords, local, *point),
                    expected_moment,
                )


ELEMENT_CASES: tuple[ElementCase, ...] = (
    ElementCase(
        "QUAD4", 2, Quad4Element, _QUAD_COORDS, _quad_patch, _quad_bar,
        sample_points=((0.0, 0.0), (-0.9, 0.3), (0.8, -0.6)),
        kwargs={"thickness": SHELL_THICKNESS},
    ),
    ElementCase("TET4", 3, Tet4Element, _TET_COORDS, _tet_patch, _tet_bar),
    ElementCase(
        "HEX8", 3, Hex8Element, _HEX_COORDS, _hex_patch, _hex_bar,
        sample_points=((0.0, 0.0, 0.0), (0.577, -0.577, 0.577), (-1.0, 0.3, 0.8)),
    ),
    ShellElementCase(
        "SHELL4", 3, ShellQuad4Element, _SHELL_COORDS, _shell_patch, _shell_bar,
        sample_points=((0.0, 0.0), (-0.9, 0.3), (0.8, -0.6), (1.0, 1.0)),
        kwargs={"thickness": SHELL_THICKNESS},
    ),
)

CASE_IDS = tuple(case.label for case in ELEMENT_CASES)

#: The rows whose formulation carries bending DOFs, and so has a plate oracle.
BENDING_CASES = tuple(case for case in ELEMENT_CASES if case.plate_convergence() is not None)
BENDING_IDS = tuple(case.label for case in BENDING_CASES)


def _solve_prescribed(model: Model, prescribed: dict[int, float]) -> np.ndarray:
    """Static solution with the given DOF indices held at the given values."""
    K = assemble_stiffness(model).toarray()
    fixed = np.array(sorted(prescribed), dtype=int)
    free = np.setdiff1d(np.arange(model.num_dofs), fixed)
    values = np.zeros(model.num_dofs, dtype=float)
    values[fixed] = [prescribed[index] for index in fixed]
    values[free] = np.linalg.solve(
        K[np.ix_(free, free)], -K[np.ix_(free, fixed)] @ values[fixed]
    )
    return values


# ---------------------------------------------------------------- AC-ELEM-001


@criterion("AC-ELEM-001")
@pytest.mark.parametrize("case", ELEMENT_CASES, ids=CASE_IDS)
def test_ac_elem_001_patch_reproduces_the_linear_field_exactly(case: ElementCase):
    """Interior displacements of a distorted patch match the prescribed field."""
    model, prescribed, exact = case.patch_problem()
    computed = _solve_prescribed(model, prescribed)
    interior = np.setdiff1d(np.arange(model.num_dofs), np.array(sorted(prescribed), dtype=int))
    assert interior.size == case.patch_interior_dofs
    error = np.abs(computed[interior] - exact[interior]).max() / np.abs(exact).max()
    assert error < case.patch_tolerance, f"{case.label}: patch defect {error:.3e}"


@criterion("AC-ELEM-001")
@pytest.mark.parametrize("case", ELEMENT_CASES, ids=CASE_IDS)
def test_ac_elem_001_patch_yields_the_exact_constant_stress(case: ElementCase):
    """Every element of the patch reports the same constant stress ``D eps``."""
    model, prescribed, _ = case.patch_problem()
    computed = _solve_prescribed(model, prescribed)
    checked = 0
    for label, recovered, expected in case.patch_stress_measures(model, computed):
        # No component of a gating state may be trivially zero.
        assert np.abs(expected).min() > STATE_FLOOR * np.abs(expected).max(), label
        np.testing.assert_allclose(
            recovered, expected, rtol=STRESS_TOLERANCE, err_msg=f"{case.label} {label}"
        )
        checked += 1
    assert checked == model.num_elements * case.stress_samples


@criterion("AC-ELEM-001")
@pytest.mark.parametrize("case", ELEMENT_CASES, ids=CASE_IDS)
def test_ac_elem_001_single_element_is_exact_on_distorted_geometry(case: ElementCase):
    """The single-element form of the patch test: strain recovery on one element."""
    element = case.bound()
    displacements = case.nodal_field(element, case.coords)
    checked = 0
    for label, recovered, expected in case.strain_measures(
        element, case.coords, displacements
    ):
        np.testing.assert_allclose(
            recovered, expected, rtol=1e-11, atol=1e-16, err_msg=f"{case.label} {label}"
        )
        checked += 1
    assert checked == case.strain_samples


@criterion("AC-ELEM-001")
@pytest.mark.parametrize("case", ELEMENT_CASES, ids=CASE_IDS)
def test_ac_elem_001_constant_stress_is_self_equilibrated(case: ElementCase):
    """Consistent nodal forces of a constant stress state sum to zero per axis."""
    element = case.bound()
    forces = element.stiffness_matrix(case.coords) @ case.nodal_field(element, case.coords)
    scale = np.abs(forces).max()
    stride = len(case.dofs)
    for axis in range(case.translations):
        assert abs(forces[axis::stride].sum()) < STRESS_TOLERANCE * scale


# ---------------------------------------------------------------- AC-ELEM-002


@criterion("AC-ELEM-002")
@pytest.mark.parametrize("case", ELEMENT_CASES, ids=CASE_IDS)
def test_ac_elem_002_rigid_body_motions_are_stress_free(case: ElementCase):
    """No nodal force, no strain energy and no strain under any rigid motion."""
    element = case.bound()
    k = element.stiffness_matrix(case.coords)
    scale = float(np.abs(k).max())
    motions = case.rigid_body_motions(element, case.coords)
    assert len(motions) == case.rigid_modes
    for name, motion in motions.items():
        residual = np.abs(k @ motion).max() / (scale * np.abs(motion).max())
        assert residual < RIGID_TOLERANCE, f"{case.label} {name}: force residual {residual:.3e}"
        energy = float(motion @ k @ motion) / (scale * float(motion @ motion))
        assert abs(energy) < RIGID_TOLERANCE, f"{case.label} {name}: energy {energy:.3e}"
        for label, recovered, _ in case.strain_measures(element, case.coords, motion):
            assert np.abs(recovered).max() < RIGID_TOLERANCE, f"{case.label} {name}: {label}"


@criterion("AC-ELEM-002")
@pytest.mark.parametrize("case", ELEMENT_CASES, ids=CASE_IDS)
def test_ac_elem_002_single_element_has_no_spurious_zero_energy_mode(case: ElementCase):
    """The element stiffness has exactly the rigid-body nullity -- no hourglassing.

    Stated as the two halves of "the nullity is exactly ``rigid_modes``" rather
    than as a count against one cut, because where that cut may sit is a
    property of the formulation: the shell's smallest elastic mode is a
    deliberate penalty six decades below its largest, so a cut that suits a
    continuum element would count it as a mechanism.
    """
    eigenvalues = np.linalg.eigvalsh(case.bound().stiffness_matrix(case.coords))
    largest = float(eigenvalues.max())
    rigid = float(np.abs(eigenvalues[: case.rigid_modes]).max())
    assert rigid < RIGID_TOLERANCE * largest, f"{case.label}: rigid mode carries {rigid:.3e}"
    elastic = float(eigenvalues[case.rigid_modes])
    assert elastic > case.elastic_floor * largest, (
        f"{case.label}: mode {case.rigid_modes} is at {elastic / largest:.3e} of the "
        "largest eigenvalue -- a spurious zero-energy mode"
    )


@criterion("AC-ELEM-002")
@pytest.mark.parametrize("case", ELEMENT_CASES, ids=CASE_IDS)
def test_ac_elem_002_free_assembly_shows_only_rigid_body_modes(case: ElementCase):
    """An unsupported mesh has exactly 3 (planar) or 6 (spatial) zero frequencies."""
    model = case.free_model()
    result = ModalSolver(model).solve(num_modes=case.rigid_modes + 2)
    assert int(np.sum(result.rigid_body_modes)) == case.rigid_modes
    np.testing.assert_allclose(
        result.frequencies[: case.rigid_modes], np.zeros(case.rigid_modes), atol=1e-2
    )
    assert result.frequencies[case.rigid_modes] > 1.0


# ---------------------------------------------------------------- AC-ELEM-003


@criterion("AC-ELEM-003")
@pytest.mark.parametrize("case", ELEMENT_CASES, ids=CASE_IDS)
def test_ac_elem_003_axial_modes_converge_quadratically(case: ElementCase):
    """Halving ``h`` quarters the frequency error against the continuum bar."""
    exact = np.sqrt(BAR_MATERIAL.E / BAR_MATERIAL.density) / (4.0 * BAR_LENGTH)
    errors = [
        ModalSolver(case.bar(num_elements)).solve(num_modes=1).frequencies[0] / exact - 1.0
        for num_elements in (4, 8, 16)
    ]

    # A conforming displacement field with consistent mass converges from above.
    assert all(error > 0.0 for error in errors), f"{case.label}: {errors}"
    assert errors[-1] < CONVERGENCE_ERROR, f"{case.label}: finest error {errors[-1]:.3e}"
    for coarse, fine in zip(errors[:-1], errors[1:], strict=True):
        ratio = coarse / fine
        assert ratio > CONVERGENCE_RATIO, f"{case.label}: error ratio {ratio:.3f}"
        assert 1.8 < np.log2(ratio) < 2.2, f"{case.label}: observed order {np.log2(ratio):.3f}"


@criterion("AC-ELEM-003")
@pytest.mark.parametrize("case", BENDING_CASES, ids=BENDING_IDS)
def test_ac_elem_003_bending_modes_converge_quadratically(case: ElementCase):
    """The same rate on the plate oracle, for a formulation that bends.

    The axial row above reaches a bending element only through its membrane, so
    it says nothing about the half of the formulation that carries curvature.
    This one refines a simply supported square plate against the Reissner-Mindlin
    Navier spectrum -- the theory the element discretizes, so the whole error is
    the discretization error.
    """
    mesh, exact = case.plate_convergence()
    errors = [
        ModalSolver(mesh(num_elements)).solve(num_modes=1, residual_tol=None).frequencies[0]
        / exact
        - 1.0
        for num_elements in PLATE_COUNTS
    ]

    assert all(error > 0.0 for error in errors), f"{case.label}: {errors}"
    assert errors[-1] < PLATE_CONVERGENCE_ERROR, f"{case.label}: finest {errors[-1]:.3e}"
    for coarse, fine in zip(errors[:-1], errors[1:], strict=True):
        ratio = coarse / fine
        assert ratio > CONVERGENCE_RATIO, f"{case.label}: error ratio {ratio:.3f}"
        assert 1.8 < np.log2(ratio) < 2.2, f"{case.label}: observed order {np.log2(ratio):.3f}"
