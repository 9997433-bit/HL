"""M8 model-interchange acceptance suite (``docs/ACCEPTANCE_CRITERIA.md`` section 9).

Implemented here
----------------
- **AC-IO-001** (contract, MS-9.2) — every native object survives the JSON and
  the YAML round trip with its arrays bitwise intact, and the two encodings of
  one object are the same document rather than two schemas.
- **AC-IO-002** (contract, MS-9.3) — a neutral model written through the meshio
  bridge and read back keeps its coordinates, blocks, labels and property ids
  in every format that carries data arrays; the format that carries none
  degrades in the documented way instead of silently.
- **AC-IO-003** (contract, MS-9.4) — a mesh file written by meshio itself
  becomes a solver-ready model: ``read_meshio`` → ``neutral_to_model`` →
  ``assemble_system`` reproduces, to the bit, the assembly of the model
  ``openfemlab.mesh.simple`` builds from the same nodes and elements.

The reference of AC-IO-003 is that hand-built model rather than a stored
matrix, so the gate measures what the conversion *adds* — nothing — instead of
comparing the code against a previous run of itself. The continuum bar
frequency ``c/(4L)``, ``c = sqrt(E/rho)``, is the independent oracle on top of
it: identical matrices would be worthless if both models were wrong.

``meshio`` is the optional ``[io]`` extra. AC-IO-001 does not need it, so the
skip is taken inside the tests that do rather than for the whole module.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from openfemlab.core.assembly import assemble_system
from openfemlab.core.dofs import DofMap, DofType
from openfemlab.core.model import DOF, TRANSLATIONAL_DOFS, Material, Model, Section
from openfemlab.core.neutral import ElementType, NeutralMaterial, NeutralModel, NeutralProperty
from openfemlab.core.results import ModalResult
from openfemlab.core.results import TestData as ModalTestData  # 'Test*' would be collected
from openfemlab.io import (
    SCHEMA_VERSION,
    FormatError,
    from_meshio,
    neutral_to_model,
    read,
    read_data,
    read_meshio,
    read_modal_result,
    read_model,
    read_test_data,
    to_meshio,
    write,
    write_meshio,
    write_modal_result,
    write_model,
    write_test_data,
)
from openfemlab.mesh.simple import bar_mesh, hex_block_mesh, quad_plate_mesh, tet_block_mesh
from openfemlab.solver.modal import ModalSolver

from ._support import criterion, fixture_matrices, load_fixture

#: Gate of AC-IO-003 on the modal spectrum. The matrices come back bitwise
#: identical, so this only leaves room for the eigensolver itself.
SPECTRUM_TOLERANCE = 1e-12

#: Gate of AC-IO-003 against the continuum bar; the discretizations below land
#: at ~0.16 %.
ORACLE_TOLERANCE = 1e-2

#: Import-path material: ``nu = 0`` decouples the lateral directions, which is
#: what makes the 1D bar the exact oracle for a 2D or 3D mesh (as in MS-8.4).
BAR_MATERIAL = Material(E=2.1e11, density=7850.0, nu=0.0)
BAR_LENGTH = 1.0
BAR_SECTION = Section(area=1e-2)


def require_meshio() -> Any:
    """Import ``meshio`` or skip; AC-IO-002/003 exercise the ``[io]`` extra."""
    return pytest.importorskip("meshio", reason="requires the optional [io] extra")


def assert_identical(actual: Any, expected: Any, what: str) -> None:
    """Bitwise array equality — the round-trip gates admit no tolerance."""
    np.testing.assert_array_equal(np.asarray(actual), np.asarray(expected), err_msg=what)


# ---------------------------------------------------------------------------
# AC-IO-001 — the native JSON/YAML schema
# ---------------------------------------------------------------------------


def sample_neutral_model() -> NeutralModel:
    """Two blocks, both tables, a DOF map and nested metadata."""
    return NeutralModel(
        nodes=np.array(
            [[0.0, 0.0, 0.0], [1.5, 0.0, 0.0], [1.5, 0.75, 0.0], [0.0, 0.75, 0.0]]
        ),
        node_ids=np.array([11, 12, 13, 14]),
        elements={
            ElementType.ROD2: np.array([[11, 12], [12, 13]]),
            ElementType.QUAD4: np.array([[11, 12, 13, 14]]),
        },
        element_property_ids={
            ElementType.ROD2: np.array([7, 7]),
            ElementType.QUAD4: np.array([8]),
        },
        materials={
            2: NeutralMaterial(id=2, E=2.1e11, nu=0.3, rho=7850.0, name="steel"),
            3: NeutralMaterial(id=3, E=7.0e10, nu=0.33, rho=2700.0, name="aluminium"),
        },
        properties={
            7: NeutralProperty(id=7, material_id=2, values={"A": 3.7e-4}, name="rod"),
            8: NeutralProperty(id=8, material_id=3, values={"t": 2.5e-3}, name="skin"),
        },
        dof_map=DofMap.regular(np.array([11, 12, 13, 14]), (DofType.UX, DofType.UY)),
        meta={"units": "SI", "source": "acceptance", "tags": ["mixed", "round-trip"]},
    )


def sample_modal_result() -> ModalResult:
    """Irrational frequencies, so a truncating writer cannot pass by luck."""
    return ModalResult(
        frequencies=np.array([math.pi, 10.0 * math.e, 123.456789012345]),
        shapes=np.array(
            [
                [1.0, 0.5, -0.25],
                [-1.0 / 3.0, 2.0 / 7.0, 1.0],
                [0.125, -1.0, 1.0 / 9.0],
                [1.0e-12, 3.5, -2.5],
            ]
        ),
        dof_map=DofMap.regular(np.array([21, 22]), (DofType.UX, DofType.RZ)),
        meta={"solver": "external", "normalization": "mass"},
    )


def sample_test_data() -> ModalTestData:
    """Complex shapes: JSON has no complex type, so the schema must carry one."""
    return ModalTestData(
        frequencies=np.array([9.75, 41.5]),
        shapes=np.array(
            [[1.0 + 0.25j, -0.5], [0.5 - 1.0 / 3.0j, 2.0j], [0.0, 1.0 / 7.0 + 1.0j]]
        ),
        dof_map=DofMap([31, 32, 33], [DofType.UX, DofType.UY, DofType.UZ]),
        damping=np.array([0.012, 0.0035]),
        geometry=np.array([[0.0, 0.0, 0.0], [0.4, 0.0, 0.0], [0.8, 0.1, 0.0]]),
        meta={"campaign": "roving hammer"},
    )


def assert_model_restored(restored: NeutralModel, original: NeutralModel) -> None:
    assert_identical(restored.nodes, original.nodes, "nodes")
    assert_identical(restored.node_ids, original.node_ids, "node ids")
    assert set(restored.elements) == set(original.elements)
    for element_type, block in original.elements.items():
        name = element_type.value
        assert_identical(restored.elements[element_type], block, f"{name} connectivity")
        assert_identical(
            restored.element_property_ids[element_type],
            original.element_property_ids[element_type],
            f"{name} property ids",
        )
    assert restored.materials == original.materials
    assert restored.properties == original.properties
    assert restored.meta == original.meta
    assert_dof_map_restored(restored.dof_map, original.dof_map)


def assert_dof_map_restored(restored: DofMap, original: DofMap) -> None:
    assert_identical(restored.node_ids, original.node_ids, "dof map node ids")
    assert_identical(restored.dof_types, original.dof_types, "dof map dof types")


def assert_modal_result_restored(restored: ModalResult, original: ModalResult) -> None:
    assert_identical(restored.frequencies, original.frequencies, "frequencies")
    assert_identical(restored.shapes, original.shapes, "mode shapes")
    assert restored.meta == original.meta
    assert_dof_map_restored(restored.dof_map, original.dof_map)


def assert_test_data_restored(restored: ModalTestData, original: ModalTestData) -> None:
    assert_identical(restored.frequencies, original.frequencies, "frequencies")
    assert_identical(restored.shapes, original.shapes, "mode shapes")
    assert_identical(restored.damping, original.damping, "damping ratios")
    assert_identical(restored.geometry, original.geometry, "sensor geometry")
    assert restored.meta == original.meta
    assert_dof_map_restored(restored.dof_map, original.dof_map)


#: ``object_type`` → builder, writer, reader, comparison. The keys are the
#: ``object_type`` values the schema emits, which the header test relies on.
NATIVE_CASES: dict[str, tuple[Callable[[], Any], Callable[..., None], Callable[..., Any], Any]] = {
    "model": (sample_neutral_model, write_model, read_model, assert_model_restored),
    "modal_result": (
        sample_modal_result,
        write_modal_result,
        read_modal_result,
        assert_modal_result_restored,
    ),
    "test_data": (sample_test_data, write_test_data, read_test_data, assert_test_data_restored),
}


@criterion("AC-IO-001")
@pytest.mark.parametrize("encoding", ["json", "yaml"])
@pytest.mark.parametrize("object_type", sorted(NATIVE_CASES))
def test_native_object_survives_the_round_trip(
    tmp_path: Path, object_type: str, encoding: str
) -> None:
    build, writer, reader, compare = NATIVE_CASES[object_type]
    original = build()
    path = tmp_path / f"{object_type}.{encoding}"

    writer(original, path)
    compare(reader(path), original)

    # The untyped entry point recognizes the document by its own header.
    assert type(read(path)) is type(original)


@criterion("AC-IO-001")
@pytest.mark.parametrize("object_type", sorted(NATIVE_CASES))
def test_json_and_yaml_are_two_encodings_of_one_document(
    tmp_path: Path, object_type: str
) -> None:
    build, writer, _, _ = NATIVE_CASES[object_type]
    original = build()

    writer(original, tmp_path / "document.json")
    writer(original, tmp_path / "document.yaml")

    assert read_data(tmp_path / "document.json") == read_data(tmp_path / "document.yaml")


@criterion("AC-IO-001")
@pytest.mark.parametrize("object_type", sorted(NATIVE_CASES))
def test_native_document_carries_the_schema_header(tmp_path: Path, object_type: str) -> None:
    build, writer, _, _ = NATIVE_CASES[object_type]
    path = tmp_path / "document.json"

    writer(build(), path)

    document = read_data(path)
    assert document["format"] == "openfemlab"
    assert document["schema_version"] == SCHEMA_VERSION
    assert document["object_type"] == object_type


@criterion("AC-IO-001")
@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_non_finite_values_are_rejected_rather_than_written(tmp_path: Path, value: float) -> None:
    """JSON and YAML spell these differently, so the schema admits neither."""
    path = tmp_path / "broken.json"

    with pytest.raises(FormatError, match="non-finite"):
        write({"object_type": "raw", "reading": value}, path)

    assert not path.exists(), "a rejected document must not leave a partial file behind"


# ---------------------------------------------------------------------------
# AC-IO-002 — the meshio bridge
# ---------------------------------------------------------------------------


def mixed_neutral_model() -> NeutralModel:
    """Three blocks, non-contiguous node labels, explicit property and element ids."""
    return NeutralModel(
        nodes=np.array(
            [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [1.0, 1.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
                [1.0, 0.0, 1.0],
                [1.0, 1.0, 1.0],
                [0.0, 1.0, 1.0],
                [2.5, 0.0, 0.0],
                [2.5, 1.0, 0.0],
            ]
        ),
        node_ids=np.array([101, 102, 103, 104, 105, 106, 107, 108, 109, 110]),
        elements={
            ElementType.ROD2: np.array([[109, 110]]),
            ElementType.QUAD4: np.array([[101, 102, 103, 104], [102, 109, 110, 103]]),
            ElementType.HEX8: np.array([[101, 102, 103, 104, 105, 106, 107, 108]]),
        },
        element_property_ids={
            ElementType.ROD2: np.array([6]),
            ElementType.QUAD4: np.array([3, 4]),
            ElementType.HEX8: np.array([5]),
        },
        meta={"element_ids": {"rod2": [31], "quad4": [11, 12], "hex8": [21]}},
    )


def single_block_neutral_model() -> NeutralModel:
    """Two tetrahedra — what a format that cannot mix cell types can hold."""
    return NeutralModel(
        nodes=np.array(
            [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [1.0, 1.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.5, 0.5, 1.0],
            ]
        ),
        node_ids=np.array([7, 8, 9, 10, 11]),
        elements={ElementType.TET4: np.array([[7, 8, 9, 11], [8, 9, 10, 11]])},
        element_property_ids={ElementType.TET4: np.array([2, 3])},
        meta={"element_ids": {"tet4": [41, 42]}},
    )


#: Mesh formats that carry point and cell data, so the labels survive. Gmsh
#: needs entity information before it will write more than one cell type, so
#: it is exercised on the single-block model rather than dropped.
MESH_FILE_CASES: dict[str, tuple[str, str | None, Callable[[], NeutralModel]]] = {
    "vtu": ("mesh.vtu", None, mixed_neutral_model),
    "vtk": ("mesh.vtk", None, mixed_neutral_model),
    "gmsh": ("mesh.msh", "gmsh", single_block_neutral_model),
}


def assert_neutral_models_match(restored: NeutralModel, original: NeutralModel) -> None:
    """Everything the bridge promises to carry: geometry, topology and labels."""
    assert_identical(restored.nodes, original.nodes, "coordinates")
    assert_identical(restored.node_ids, original.node_ids, "node ids")
    assert set(restored.elements) == set(original.elements)
    for element_type, block in original.elements.items():
        name = element_type.value
        assert_identical(restored.elements[element_type], block, f"{name} connectivity")
        assert_identical(
            restored.element_property_ids[element_type],
            original.element_property_ids[element_type],
            f"{name} property ids",
        )
        assert restored.meta["element_ids"][name] == original.meta["element_ids"][name]


@criterion("AC-IO-002")
def test_neutral_model_survives_the_in_memory_meshio_round_trip() -> None:
    require_meshio()
    original = mixed_neutral_model()

    assert_neutral_models_match(from_meshio(to_meshio(original)), original)


@criterion("AC-IO-002")
@pytest.mark.parametrize("format_name", sorted(MESH_FILE_CASES))
def test_neutral_model_survives_the_meshio_file_round_trip(
    tmp_path: Path, format_name: str
) -> None:
    require_meshio()
    filename, file_format, build = MESH_FILE_CASES[format_name]
    original = build()
    path = tmp_path / filename

    write_meshio(original, path, file_format=file_format)
    restored = read_meshio(path, file_format=file_format)

    assert_neutral_models_match(restored, original)


@criterion("AC-IO-002")
def test_format_without_data_arrays_keeps_geometry_and_renumbers_labels(tmp_path: Path) -> None:
    """Abaqus ``.inp`` carries no data arrays; the loss is documented, not silent."""
    require_meshio()
    original = single_block_neutral_model()
    path = tmp_path / "mesh.inp"

    write_meshio(original, path, file_format="abaqus")
    restored = read_meshio(path, file_format="abaqus")

    assert_identical(restored.nodes, original.nodes, "coordinates")
    assert_identical(
        restored.node_ids, np.arange(1, original.nodes.shape[0] + 1), "renumbered node ids"
    )
    position = {int(node_id): index for index, node_id in enumerate(original.node_ids)}
    relabelled = np.array(
        [[position[int(node_id)] + 1 for node_id in row] for row in original.elements[
            ElementType.TET4
        ]]
    )
    assert_identical(restored.elements[ElementType.TET4], relabelled, "topology by position")
    assert_identical(
        restored.element_property_ids[ElementType.TET4],
        np.ones(relabelled.shape[0], dtype=np.int64),
        "default property ids",
    )


@criterion("AC-IO-002")
def test_element_type_without_a_cell_type_is_rejected() -> None:
    """``beam2`` and ``line`` are not interchangeable, so the export refuses."""
    require_meshio()
    model = NeutralModel(
        nodes=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]),
        node_ids=np.array([1, 2]),
        elements={ElementType.BEAM2: np.array([[1, 2]])},
    )

    with pytest.raises(FormatError, match="no meshio cell type"):
        to_meshio(model)


@criterion("AC-IO-002")
def test_unmapped_cell_types_are_skipped_with_a_diagnostic() -> None:
    """The partial-import policy, exercised without the extra: ``from_meshio``
    accepts anything exposing ``points`` and ``cells``."""
    mesh = SimpleNamespace(
        points=np.zeros((6, 3)),
        cells=[
            ("triangle", np.array([[0, 1, 2]])),
            ("wedge", np.array([[0, 1, 2, 3, 4, 5]])),
        ],
    )

    with pytest.warns(UserWarning, match="skipped unsupported meshio cell types"):
        restored = from_meshio(mesh)

    assert set(restored.elements) == {ElementType.TRI3}
    assert restored.meta["skipped_cell_types"] == {"wedge": 1}


# ---------------------------------------------------------------------------
# AC-IO-003 — read_meshio -> neutral_to_model -> assemble
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ImportCase:
    """One element family of the import path and the reference it is judged by."""

    cell_type: str
    reference: Callable[[], Model]
    #: Fallbacks a geometry-only mesh file cannot supply.
    convert: dict[str, Any] = field(default_factory=dict)
    #: Directions the family carries no stiffness in — a truss chain has none
    #: transversally — suppressed on both models so the comparison is solvable.
    suppressed: tuple[DOF, ...] = ()


IMPORT_CASES: dict[str, ImportCase] = {
    "rod2": ImportCase(
        cell_type="line",
        reference=lambda: bar_mesh(
            BAR_LENGTH, 8, BAR_MATERIAL, BAR_SECTION, dofs=TRANSLATIONAL_DOFS
        ),
        convert={"section": BAR_SECTION},
        suppressed=(DOF.UY, DOF.UZ),
    ),
    "quad4": ImportCase(
        cell_type="quad",
        reference=lambda: quad_plate_mesh(BAR_LENGTH, 0.1, 8, 1, BAR_MATERIAL),
    ),
    "tet4": ImportCase(
        cell_type="tetra",
        reference=lambda: tet_block_mesh(BAR_LENGTH, 0.1, 0.1, 6, 1, 1, BAR_MATERIAL),
    ),
    "hex8": ImportCase(
        cell_type="hexahedron",
        reference=lambda: hex_block_mesh(BAR_LENGTH, 0.1, 0.1, 8, 1, 1, BAR_MATERIAL),
    ),
}


def write_mesh_file(model: Model, cell_type: str, path: Path) -> Path:
    """Write ``model``'s geometry with meshio itself.

    The file carries points and cells and nothing else: no ``node_ids``,
    ``element_ids`` or ``property_ids`` array this project would recognize, so
    the labels the reader hands back are entirely its own.
    """
    meshio = require_meshio()
    position = {node_id: index for index, node_id in enumerate(model.node_ids)}
    cells = np.array(
        [[position[node_id] for node_id in element.node_ids] for element in model.elements],
        dtype=np.int64,
    )
    meshio.write(path, meshio.Mesh(points=model.coordinates, cells=[(cell_type, cells)]))
    return path


def import_model(case: ImportCase, path: Path) -> Model:
    """``read_meshio`` → ``neutral_to_model``, clamped like the reference mesh."""
    imported = neutral_to_model(read_meshio(path), material=BAR_MATERIAL, **case.convert)
    for node_id, coords in zip(imported.node_ids, imported.coordinates, strict=True):
        if abs(float(coords[0])) < 1e-12:
            imported.fix(node_id)
    return imported


def prepared_pair(case: ImportCase, tmp_path: Path) -> tuple[Model, Model]:
    """The hand-built reference and its imported twin, constrained alike."""
    reference = case.reference()
    imported = import_model(case, write_mesh_file(reference, case.cell_type, tmp_path / "mesh.vtu"))
    for model in (reference, imported):
        if case.suppressed:
            model.fix_dof_globally(case.suppressed)
    return reference, imported


@criterion("AC-IO-003")
@pytest.mark.parametrize("family", sorted(IMPORT_CASES))
def test_imported_mesh_assembles_as_the_hand_built_model(tmp_path: Path, family: str) -> None:
    reference, imported = prepared_pair(IMPORT_CASES[family], tmp_path)

    expected = assemble_system(reference)
    actual = assemble_system(imported)

    assert imported.dofs == reference.dofs
    assert_identical(actual.K.toarray(), expected.K.toarray(), "stiffness matrix")
    assert_identical(actual.M.toarray(), expected.M.toarray(), "mass matrix")
    assert_identical(actual.free_dofs, expected.free_dofs, "free DOFs")
    assert_identical(actual.constrained_dofs, expected.constrained_dofs, "constrained DOFs")
    assert actual.total_mass == expected.total_mass


@criterion("AC-IO-003")
@pytest.mark.parametrize("family", sorted(IMPORT_CASES))
def test_imported_model_solves_to_the_reference_spectrum(tmp_path: Path, family: str) -> None:
    reference, imported = prepared_pair(IMPORT_CASES[family], tmp_path)

    expected = ModalSolver(reference).solve(3).frequencies
    actual = ModalSolver(imported).solve(3).frequencies

    assert np.all(expected > 0.0)
    np.testing.assert_allclose(actual, expected, rtol=SPECTRUM_TOLERANCE, atol=0.0)


@criterion("AC-IO-003")
def test_imported_bar_reaches_the_continuum_axial_frequency(tmp_path: Path) -> None:
    """The independent half of the gate: the imported model is also *right*."""
    case = IMPORT_CASES["hex8"]
    path = write_mesh_file(case.reference(), case.cell_type, tmp_path / "bar.vtu")
    imported = import_model(case, path)
    imported.fix_dof_globally([DOF.UY, DOF.UZ])

    first = float(ModalSolver(imported).solve(1).frequencies[0])

    oracle = math.sqrt(BAR_MATERIAL.E / BAR_MATERIAL.density) / (4.0 * BAR_LENGTH)
    assert abs(first - oracle) / oracle <= ORACLE_TOLERANCE


@criterion("AC-IO-004")
def test_ac_io_004_op2_geometry_matches_the_bdf_of_the_same_model() -> None:
    """OP2 ``GEOM1``/``GEOM2`` import agrees with the bulk-data reader."""
    import io

    from openfemlab.io.nastran import read_bdf
    from openfemlab.io.op2 import read_op2
    from tests import _op2

    grids = [
        _op2.Grid(id=11, xyz=(0.0, 0.0, 0.0)),
        _op2.Grid(id=22, xyz=(1.0, 0.0, 0.0)),
        _op2.Grid(id=33, xyz=(2.0, 0.0, 0.0)),
    ]
    rods = [
        _op2.Rod(id=100, property_id=40, grids=(11, 22)),
        _op2.Rod(id=200, property_id=40, grids=(22, 33)),
    ]
    content = _op2.geometry_file(grids, rods=rods)
    bdf_text = io.StringIO(
        "\n".join(
            [
                "GRID,11,,0.,0.,0.",
                "GRID,22,,1.,0.,0.",
                "GRID,33,,2.,0.,0.",
                "CROD,100,40,11,22",
                "CROD,200,40,22,33",
            ]
        )
        + "\n"
    )

    bdf_model = read_bdf(bdf_text)
    op2_model = read_op2(io.BytesIO(content))

    np.testing.assert_array_equal(bdf_model.node_ids, op2_model.node_ids)
    np.testing.assert_allclose(bdf_model.nodes, op2_model.nodes)
    for element_type in bdf_model.elements:
        np.testing.assert_array_equal(
            bdf_model.elements[element_type], op2_model.elements[element_type]
        )
        np.testing.assert_array_equal(
            bdf_model.element_property_ids[element_type],
            op2_model.element_property_ids[element_type],
        )


@criterion("AC-IO-006")
def test_ac_io_006_op2_reads_prod_properties() -> None:
    """``EPT`` ``PROD`` cards populate ``NeutralModel.properties``."""
    import io

    from openfemlab.io.op2 import read_op2
    from tests import _op2

    content = _op2.geometry_file(
        [
            _op2.Grid(id=11, xyz=(0.0, 0.0, 0.0)),
            _op2.Grid(id=22, xyz=(1.0, 0.0, 0.0)),
        ],
        [_op2.Rod(id=100, property_id=40, grids=(11, 22))],
        [_op2.Mat1(id=7, E=2.0e11, nu=0.3, rho=7800.0)],
        properties=[_op2.Prod(id=40, material_id=7, area=2.5e-4)],
    )

    model = read_op2(io.BytesIO(content))
    prop = model.properties[40]

    assert prop.name == "PROD"
    assert prop.material_id == 7
    assert prop.values["A"] == pytest.approx(2.5e-4)


@criterion("AC-IO-007")
def test_ac_io_007_op2_reads_pshell_and_psolid_properties() -> None:
    """``PSHELL`` thickness and ``PSOLID`` material id import from ``EPT``."""
    import io

    from openfemlab.io.nastran import read_bdf
    from openfemlab.io.op2 import read_op2
    from tests import _op2

    bdf_text = io.StringIO(
        "\n".join(
            [
                "GRID,11,,0.,0.,0.",
                "PSHELL,10,7,0.0025",
                "PSOLID,20,7",
            ]
        )
        + "\n"
    )
    content = _op2.write_op2(
        [
            _op2.geom1_block([_op2.Grid(id=11, xyz=(0.0, 0.0, 0.0))]),
            _op2.pshell_block([_op2.Pshell(id=10, material_id=7, thickness=0.0025)]),
            _op2.psolid_block([_op2.Psolid(id=20, material_id=7)]),
        ]
    )

    bdf_model = read_bdf(bdf_text)
    op2_model = read_op2(io.BytesIO(content))

    assert op2_model.properties[10].name == bdf_model.properties[10].name
    assert op2_model.properties[10].material_id == bdf_model.properties[10].material_id
    assert op2_model.properties[10].values["t"] == pytest.approx(
        bdf_model.properties[10].values["t"]
    )
    assert op2_model.properties[20] == bdf_model.properties[20]


@criterion("AC-IO-008")
def test_ac_io_008_bdf_export_round_trip_preserves_geometry(tmp_path) -> None:
    """``write_bdf`` followed by ``read_bdf`` recovers nodes and connectivity."""
    import io

    from openfemlab.io.nastran import read_bdf, write_bdf

    bdf_text = io.StringIO(
        "\n".join(
            [
                "GRID,11,,0.,0.,0.",
                "GRID,22,,1.,0.,0.",
                "GRID,33,,2.,0.,0.",
                "CROD,100,40,11,22",
                "CROD,200,40,22,33",
            ]
        )
        + "\n"
    )
    source = read_bdf(bdf_text)
    path = tmp_path / "exported.bdf"
    write_bdf(source, path)
    recovered = read_bdf(path)
    assert np.array_equal(recovered.node_ids, source.node_ids)
    assert np.allclose(recovered.nodes, source.nodes)
    for element_type, connectivity in source.elements.items():
        assert element_type in recovered.elements
        assert np.array_equal(recovered.elements[element_type], connectivity)


@criterion("AC-IO-009")
def test_ac_io_009_export_test_model_round_trips_uff_modes(tmp_path) -> None:
    """Reduced test models export to UFF-55 and recover frequencies and shapes."""
    from openfemlab import ModalSolver
    from openfemlab.core.dofs import DofMap, DofType
    from openfemlab.core.results import TestData
    from openfemlab.io.uff import read_uff_modes
    from openfemlab.pretest.export_test import export_test_model

    stiffness, mass = fixture_matrices(load_fixture("ten_dof_chain"))
    result = ModalSolver.from_matrices(stiffness, mass).solve(num_modes=3, sparse=False)
    shapes = np.asarray(result.mode_shapes, dtype=float)
    frequencies = np.asarray(result.frequencies, dtype=float)
    dof_map = DofMap(
        node_ids=np.arange(shapes.shape[0], dtype=np.int64) + 100,
        dof_types=np.full(shapes.shape[0], DofType.UY, dtype=np.int64),
    )
    transform = {
        "rotation_euler_xyz_deg": [1.0, -2.0, 3.5],
        "translation": [0.01, 0.02, -0.03],
        "rotation_matrix": np.eye(3).tolist(),
    }
    test_data = TestData(
        frequencies=frequencies,
        shapes=shapes,
        dof_map=dof_map,
        meta={"rigid_transform": transform},
    )
    path = tmp_path / "test_model.unv"
    export_test_model(test_data, path)
    recovered = read_uff_modes(path)
    assert len(recovered) == frequencies.size
    for index, mode in enumerate(recovered):
        assert mode.frequency_hz == pytest.approx(frequencies[index], abs=1e-6)
        assert mode.values.shape == (shapes.shape[0], 1)
        assert mode.values[:, 0] == pytest.approx(shapes[:, index], abs=1e-5)
    assert "EulerXYZdeg=" in recovered[-1].id_lines[1]


@criterion("AC-IO-010")
def test_ac_io_010_write_bdf_applies_material_scales(tmp_path) -> None:
    """Updated material scalings appear in exported MAT1 cards."""
    import io

    from openfemlab.io.nastran import read_bdf, write_bdf

    bdf_text = io.StringIO(
        "\n".join(
            [
                "MAT1,40,400.,7800.,,0.3",
                "PSHELL,10,40,0.02",
                "GRID,11,,0.,0.,0.",
                "GRID,22,,1.,0.,0.",
                "CROD,100,10,11,22",
            ]
        )
        + "\n"
    )
    source = read_bdf(bdf_text)
    path = tmp_path / "scaled.bdf"
    write_bdf(source, path, material_scales={40: 1.25}, property_scales={10: 0.9})
    recovered = read_bdf(path)
    assert recovered.materials[40].E == pytest.approx(400.0 * 1.25)
    assert recovered.properties[10].values["t"] == pytest.approx(0.02 * 0.9)


@criterion("AC-IO-011")
def test_ac_io_011_ansys_driver_reports_missing_executable(tmp_path, monkeypatch) -> None:
    from openfemlab.io import FormatError
    from openfemlab.io.drivers import ansys as ansys_driver

    for key in ("OPENFEMLAB_ANSYS_EXE", "ANSYS_EXE", "ANSYS242", "ANSYS"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(ansys_driver.shutil, "which", lambda _name: None)
    deck = tmp_path / "model.inp"
    deck.write_text("*HEADING\n", encoding="utf-8")
    assert ansys_driver.resolve_ansys_executable("/nonexistent/ansys") == "/nonexistent/ansys"
    with pytest.raises(FormatError, match="no Ansys executable"):
        ansys_driver.run_ansys(deck, executable=None)


@criterion("AC-IO-012")
def test_ac_io_012_abaqus_driver_reports_missing_executable(tmp_path, monkeypatch) -> None:
    from openfemlab.io import FormatError
    from openfemlab.io.drivers import abaqus as abaqus_driver

    for key in ("OPENFEMLAB_ABAQUS_EXE", "ABAQUS_EXE", "ABAQUS"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(abaqus_driver.shutil, "which", lambda _name: None)
    deck = tmp_path / "model.inp"
    deck.write_text("*HEADING\n", encoding="utf-8")
    assert abaqus_driver.resolve_abaqus_executable("/opt/abaqus") == "/opt/abaqus"
    with pytest.raises(FormatError, match="no Abaqus executable"):
        abaqus_driver.run_abaqus(deck, executable=None)


@criterion("AC-IO-013")
def test_ac_io_013_op2_cbar_geometry_matches_the_bdf_of_the_same_model() -> None:
    """OP2 ``CBAR`` ``GEOM2`` import agrees with the bulk-data reader."""
    import io

    from openfemlab.core.neutral import ElementType
    from openfemlab.io.nastran import read_bdf
    from openfemlab.io.op2 import read_op2
    from tests import _op2

    grids = [
        _op2.Grid(id=11, xyz=(0.0, 0.0, 0.0)),
        _op2.Grid(id=22, xyz=(1.0, 0.0, 0.0)),
        _op2.Grid(id=33, xyz=(2.0, 0.5, 0.0)),
    ]
    cbars = [
        _op2.CBar(id=300, property_id=50, grids=(11, 22), orientation=(0.0, 0.0, 1.0)),
        _op2.CBar(id=400, property_id=50, grids=(22, 33), orientation=(0.0, 1.0, 0.0)),
    ]
    content = _op2.geometry_file(grids, cbars=cbars)
    bdf_text = io.StringIO(
        "\n".join(
            [
                "GRID,11,,0.,0.,0.",
                "GRID,22,,1.,0.,0.",
                "GRID,33,,2.,0.5,0.",
                "CBAR,300,50,11,22,0.,0.,1.",
                "CBAR,400,50,22,33,0.,1.,0.",
            ]
        )
        + "\n"
    )

    bdf_model = read_bdf(bdf_text)
    op2_model = read_op2(io.BytesIO(content))

    np.testing.assert_array_equal(bdf_model.node_ids, op2_model.node_ids)
    np.testing.assert_allclose(bdf_model.nodes, op2_model.nodes)
    assert ElementType.BEAM2 in bdf_model.elements
    for element_type in bdf_model.elements:
        np.testing.assert_array_equal(
            bdf_model.elements[element_type], op2_model.elements[element_type]
        )
        np.testing.assert_array_equal(
            bdf_model.element_property_ids[element_type],
            op2_model.element_property_ids[element_type],
        )


@criterion("AC-IO-014")
def test_ac_io_014_corpus_sidecar_bdf_matches_op2_geometry(tmp_path) -> None:
    """When a corpus OP2 has a sidecar BDF, geometry import agrees with bulk data."""
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "scripts"))
    from generate_op2_corpus import build_corpus  # noqa: E402

    from openfemlab.io.nastran import read_bdf
    from openfemlab.io.op2 import read_op2

    corpus_dir = tmp_path / "corpus"
    build_corpus(corpus_dir)
    geometry_files = sorted(corpus_dir.rglob("*_geometry.op2"))
    assert geometry_files, "synthetic corpus must ship geometry sidecars"

    for op2_path in geometry_files:
        bdf_path = op2_path.with_suffix(".bdf")
        assert bdf_path.is_file(), f"missing sidecar for {op2_path.name}"
        bdf_model = read_bdf(bdf_path)
        op2_model = read_op2(op2_path)
        np.testing.assert_array_equal(bdf_model.node_ids, op2_model.node_ids)
        np.testing.assert_allclose(bdf_model.nodes, op2_model.nodes)
        assert list(bdf_model.elements) == list(op2_model.elements)
        for element_type in bdf_model.elements:
            np.testing.assert_array_equal(
                bdf_model.elements[element_type], op2_model.elements[element_type]
            )
            np.testing.assert_array_equal(
                bdf_model.element_property_ids[element_type],
                op2_model.element_property_ids[element_type],
            )


@criterion("AC-IO-015")
def test_ac_io_015_nastran_driver_reports_missing_executable(tmp_path, monkeypatch) -> None:
    from openfemlab.io import FormatError
    from openfemlab.io.drivers import nastran as nastran_driver

    for key in ("OPENFEMLAB_NASTRAN_EXE", "NASTRAN_EXE", "NASTRAN"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(nastran_driver.shutil, "which", lambda _name: None)
    deck = tmp_path / "model.bdf"
    deck.write_text("GRID,11,,0.,0.,0.\n", encoding="utf-8")
    assert nastran_driver.resolve_nastran_executable("/opt/nastran") == "/opt/nastran"
    with pytest.raises(FormatError, match="no Nastran executable"):
        nastran_driver.run_nastran(deck, executable=None)


@criterion("AC-IO-016")
def test_ac_io_016_op2_corpus_manifest_declares_msc_and_nx_vendor_trees(tmp_path) -> None:
    """Generated corpus carries manifest.json with MSC/NX vendor directories."""
    import json
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "scripts"))
    from generate_op2_corpus import build_corpus, corpus_manifest  # noqa: E402

    corpus_dir = tmp_path / "corpus"
    written = build_corpus(corpus_dir)
    manifest = corpus_manifest(corpus_dir)

    assert manifest["schema_version"] == "1.0"
    assert set(manifest["vendors"]) == {"synthetic/msc", "synthetic/nx"}
    for vendor in manifest["vendors"]:
        vendor_dir = corpus_dir / vendor
        assert vendor_dir.is_dir()
        op2_files = sorted(vendor_dir.glob("*.op2"))
        assert op2_files, f"{vendor} must contain OP2 samples"
        assert sorted(manifest["vendors"][vendor]["samples"]) == sorted(
            path.name for path in op2_files
        )

    assert sorted(path.relative_to(corpus_dir).as_posix() for path in written) == sorted(
        f"{vendor}/{sample}"
        for vendor, samples in {
            "synthetic/msc": (
                "rod_geometry.op2",
                "rotated_grid.op2",
                "cbar_geometry.op2",
            ),
            "synthetic/nx": (
                "rod_modes.op2",
                "shell_properties.op2",
                "quad4_geometry.op2",
            ),
        }.items()
        for sample in samples
    )
    assert json.loads((corpus_dir / "manifest.json").read_text(encoding="utf-8")) == manifest
