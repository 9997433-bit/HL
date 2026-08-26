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
HEX8) through the shared ``ELEMENT_CASES`` table, so a new formulation is
covered by adding one row rather than a new test. The developer suites
``tests/test_quad4.py``, ``tests/test_tet4.py`` and ``tests/test_hex8.py`` go
deeper per element; what this file gates is the property the *library* must
hold uniformly.

The oracles are the exact linear displacement field (patch) and the continuum
bar frequency ``c/(4L)``, ``c = sqrt(E/rho)`` (convergence), so no gate is
measured against a previous run of the code under test.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import numpy as np
import pytest

from openfemlab.core.assembly import assemble_stiffness
from openfemlab.core.elements import (
    Element,
    Hex8Element,
    Quad4Element,
    Tet4Element,
    plane_constitutive_matrix,
    solid_constitutive_matrix,
)
from openfemlab.core.model import DOF, Material, Model
from openfemlab.mesh.simple import _KUHN_TETRAHEDRA, hex_block_mesh, quad_plate_mesh, tet_block_mesh
from openfemlab.solver.modal import ModalSolver

from ._support import criterion

#: Gate of AC-ELEM-001: "exact to machine precision", relative to the largest
#: prescribed displacement. The measured defect is ~1e-16 on every family.
PATCH_TOLERANCE = 1e-12

#: Gate of AC-ELEM-001 for the recovered stress, which passes through ``D``.
STRESS_TOLERANCE = 1e-9

#: Gate of AC-ELEM-002, relative to ``max|K| * ||d||^2``.
RIGID_TOLERANCE = 1e-10

#: Gates of AC-ELEM-003: error ratio per halving (4 for a quadratic rate) and
#: the absolute error the finest mesh must reach.
CONVERGENCE_RATIO = 3.6
CONVERGENCE_ERROR = 1e-3

#: Patch material: soft and compressible, so no gate hides behind stiffness.
PATCH_MATERIAL = Material(E=1.0e6, density=1.0, nu=0.25)

#: Convergence material: ``nu = 0`` decouples the axial direction, which is what
#: makes the 1D continuum bar the exact oracle for a 2D/3D mesh.
BAR_MATERIAL = Material(E=2.1e11, density=7850.0, nu=0.0)
BAR_LENGTH = 1.0

#: Extent of the patch box and the linear field prescribed on its boundary.
PATCH_SPAN = np.array([0.24, 0.12, 0.18])
PATCH_GRADIENT = 1e-3 * np.array([[1.0, 0.4, -0.2], [0.3, -0.5, 0.5], [-0.1, 0.2, 0.8]])

#: How far interior patch nodes are pulled off the regular grid, as a fraction
#: of the cell size. The offsets are deterministic (a criterion only counts if
#: its test is deterministic) and large enough that no element stays a
#: parallelogram or parallelepiped.
PATCH_DISTORTION = 0.2

#: HEX8 corner order as indices into the ``di + 2 dj + 4 dk`` cell numbering.
_HEX8_CORNERS = (0, 1, 3, 2, 4, 5, 7, 6)


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


def _patch_nodes(model: Model, cells: Sequence[int], ndim: int) -> dict[int, np.ndarray]:
    """Fill ``model`` with a distorted structured grid; only interior nodes move."""
    node_id = _grid_ids(cells)
    cell = PATCH_SPAN[:ndim] / np.array(cells, dtype=float)
    coordinates: dict[int, np.ndarray] = {}
    interior = 0
    for index in np.ndindex(*[n + 1 for n in reversed(cells)]):
        position = tuple(reversed(index))
        point = np.array(position, dtype=float) * cell
        if all(0 < value < count for value, count in zip(position, cells, strict=True)):
            point = point + PATCH_DISTORTION * cell * _interior_offset(interior)[:ndim]
            interior += 1
        identifier = node_id(*position)
        coordinates[identifier] = point
        model.add_node(identifier, *point)
    return coordinates


def _quad_patch() -> tuple[Model, dict[int, np.ndarray]]:
    cells = (3, 3)
    model = Model(dofs=(DOF.UX, DOF.UY), name="quad4 patch")
    coordinates = _patch_nodes(model, cells, 2)
    node_id = _grid_ids(cells)
    for j in range(cells[1]):
        for i in range(cells[0]):
            model.add_element(
                Quad4Element(
                    (
                        node_id(i, j),
                        node_id(i + 1, j),
                        node_id(i + 1, j + 1),
                        node_id(i, j + 1),
                    ),
                    PATCH_MATERIAL,
                    thickness=0.001,
                )
            )
    return model, coordinates


def _solid_patch(factory: Callable[[list[int]], Sequence[Element]]):
    cells = (3, 3, 3)
    model = Model(dofs=(DOF.UX, DOF.UY, DOF.UZ), name="solid patch")
    coordinates = _patch_nodes(model, cells, 3)
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


#: A distorted single element per family: no parallel edges, no planar symmetry.
_QUAD_COORDS = np.array(
    [[0.0, 0.0, 0.0], [2.0, -0.3, 0.0], [2.4, 1.6, 0.0], [0.5, 1.1, 0.0]], dtype=float
)
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
    #: Natural coordinates the recovered stress is sampled at; empty for the
    #: constant-strain tetrahedron, whose recovery takes no point argument.
    sample_points: tuple[tuple[float, ...], ...] = ()
    kwargs: dict = field(default_factory=dict)

    @property
    def dofs(self) -> tuple[DOF, ...]:
        return (DOF.UX, DOF.UY) if self.ndim == 2 else (DOF.UX, DOF.UY, DOF.UZ)

    @property
    def rigid_modes(self) -> int:
        return 3 if self.ndim == 2 else 6

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


ELEMENT_CASES: tuple[ElementCase, ...] = (
    ElementCase(
        "QUAD4", 2, Quad4Element, _QUAD_COORDS, _quad_patch, _quad_bar,
        sample_points=((0.0, 0.0), (-0.9, 0.3), (0.8, -0.6)),
        kwargs={"thickness": 0.001},
    ),
    ElementCase("TET4", 3, Tet4Element, _TET_COORDS, _tet_patch, _tet_bar),
    ElementCase(
        "HEX8", 3, Hex8Element, _HEX_COORDS, _hex_patch, _hex_bar,
        sample_points=((0.0, 0.0, 0.0), (0.577, -0.577, 0.577), (-1.0, 0.3, 0.8)),
    ),
)

CASE_IDS = tuple(case.label for case in ELEMENT_CASES)


def _rigid_body_motions(coords: np.ndarray, ndim: int) -> dict[str, np.ndarray]:
    """The ``3`` planar or ``6`` spatial rigid-body motions as nodal vectors."""
    points = np.asarray(coords, dtype=float)[:, :ndim]
    motions: dict[str, np.ndarray] = {}
    for axis in range(ndim):
        motions[f"translation {axis}"] = np.tile(np.eye(ndim)[axis], points.shape[0])
    if ndim == 2:
        rotation = np.empty_like(points)
        rotation[:, 0] = -points[:, 1]
        rotation[:, 1] = points[:, 0]
        motions["rotation z"] = rotation.reshape(-1)
    else:
        for axis in range(3):
            motions[f"rotation {axis}"] = np.cross(np.eye(3)[axis], points).reshape(-1)
    return motions


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


def _patch_problem(case: ElementCase):
    """``(model, prescribed, exact)`` of the boundary-driven linear-field patch."""
    model, coordinates = case.patch()
    span = PATCH_SPAN[: case.ndim]
    exact = np.zeros(model.num_dofs, dtype=float)
    prescribed: dict[int, float] = {}
    for node_id, point in coordinates.items():
        displacement = PATCH_GRADIENT[: case.ndim, : case.ndim] @ point[: case.ndim]
        on_boundary = bool(np.any(np.isclose(point, 0.0)) or np.any(np.isclose(point, span)))
        for dof, value in zip(case.dofs, displacement, strict=True):
            index = model.dof_index(node_id, dof)
            exact[index] = value
            if on_boundary:
                prescribed[index] = value
    return model, prescribed, exact


def _element_stresses(model: Model, case: ElementCase, values: np.ndarray):
    """Every recovered stress vector of the patch, at every sampled point."""
    for element in model.elements:
        coords = model.node_coords(element.node_ids)
        local = values[element.global_dofs(model)]
        points = case.sample_points or ((),)
        for point in points:
            yield element.stress(coords, local, *point)


# ---------------------------------------------------------------- AC-ELEM-001


@criterion("AC-ELEM-001")
@pytest.mark.parametrize("case", ELEMENT_CASES, ids=CASE_IDS)
def test_ac_elem_001_patch_reproduces_the_linear_field_exactly(case: ElementCase):
    """Interior displacements of a distorted patch match the prescribed field."""
    model, prescribed, exact = _patch_problem(case)
    computed = _solve_prescribed(model, prescribed)
    interior = np.setdiff1d(np.arange(model.num_dofs), np.array(sorted(prescribed), dtype=int))
    assert interior.size == case.ndim * (2 ** case.ndim)  # 4 / 8 displaced nodes
    error = np.abs(computed[interior] - exact[interior]).max() / np.abs(exact).max()
    assert error < PATCH_TOLERANCE, f"{case.label}: patch defect {error:.3e}"


@criterion("AC-ELEM-001")
@pytest.mark.parametrize("case", ELEMENT_CASES, ids=CASE_IDS)
def test_ac_elem_001_patch_yields_the_exact_constant_stress(case: ElementCase):
    """Every element of the patch reports the same constant stress ``D eps``."""
    model, prescribed, _ = _patch_problem(case)
    computed = _solve_prescribed(model, prescribed)
    expected = case.constitutive_matrix() @ _voigt_strain(PATCH_GRADIENT, case.ndim)
    assert np.abs(expected).min() > 1.0  # no component is trivially zero
    for stress in _element_stresses(model, case, computed):
        np.testing.assert_allclose(stress, expected, rtol=STRESS_TOLERANCE)


@criterion("AC-ELEM-001")
@pytest.mark.parametrize("case", ELEMENT_CASES, ids=CASE_IDS)
def test_ac_elem_001_single_element_is_exact_on_distorted_geometry(case: ElementCase):
    """The single-element form of the patch test: strain recovery on one element."""
    element = case.bound()
    displacements = _linear_field(case.coords, case.ndim)
    expected = _voigt_strain(PATCH_GRADIENT, case.ndim)
    for point in case.sample_points or ((),):
        np.testing.assert_allclose(
            element.strain(case.coords, displacements, *point),
            expected,
            rtol=1e-11,
            atol=1e-16,
        )


@criterion("AC-ELEM-001")
@pytest.mark.parametrize("case", ELEMENT_CASES, ids=CASE_IDS)
def test_ac_elem_001_constant_stress_is_self_equilibrated(case: ElementCase):
    """Consistent nodal forces of a constant stress state sum to zero per axis."""
    element = case.bound()
    forces = element.stiffness_matrix(case.coords) @ _linear_field(case.coords, case.ndim)
    scale = np.abs(forces).max()
    for axis in range(case.ndim):
        assert abs(forces[axis :: case.ndim].sum()) < STRESS_TOLERANCE * scale


# ---------------------------------------------------------------- AC-ELEM-002


@criterion("AC-ELEM-002")
@pytest.mark.parametrize("case", ELEMENT_CASES, ids=CASE_IDS)
def test_ac_elem_002_rigid_body_motions_are_stress_free(case: ElementCase):
    """No nodal force, no strain energy and no strain under any rigid motion."""
    element = case.bound()
    k = element.stiffness_matrix(case.coords)
    scale = float(np.abs(k).max())
    for name, motion in _rigid_body_motions(case.coords, case.ndim).items():
        residual = np.abs(k @ motion).max() / (scale * np.abs(motion).max())
        assert residual < RIGID_TOLERANCE, f"{case.label} {name}: force residual {residual:.3e}"
        energy = float(motion @ k @ motion) / (scale * float(motion @ motion))
        assert abs(energy) < RIGID_TOLERANCE, f"{case.label} {name}: energy {energy:.3e}"
        for point in case.sample_points or ((),):
            strain = element.strain(case.coords, motion, *point)
            assert np.abs(strain).max() < RIGID_TOLERANCE


@criterion("AC-ELEM-002")
@pytest.mark.parametrize("case", ELEMENT_CASES, ids=CASE_IDS)
def test_ac_elem_002_single_element_has_no_spurious_zero_energy_mode(case: ElementCase):
    """The element stiffness has exactly the rigid-body nullity -- no hourglassing."""
    eigenvalues = np.linalg.eigvalsh(case.bound().stiffness_matrix(case.coords))
    zeros = int(np.sum(np.abs(eigenvalues) < 1e-8 * eigenvalues.max()))
    assert zeros == case.rigid_modes, f"{case.label}: {zeros} zero-energy modes"


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
