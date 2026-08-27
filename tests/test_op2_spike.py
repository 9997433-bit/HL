"""Contracts of the OP2 reader, phase by phase.

Three kinds of test live here.  The first pins the decisions the GAP-03 spike
took, so a later change cannot leak the reader into the public
:mod:`openfemlab.io` namespace before it has been held against real solver
output.  The second exercises the phases that are implemented — the record
framing (Phase 1) and the normal modes (Phase 2) — against files
:mod:`tests._op2` writes, since an OP2 cannot be produced without a Nastran
licence.  The third is still skipped, and states the contract each remaining
phase (MODULE_SPEC MS-9.6) has to satisfy — including the corpus test that is
the reason the reader stays unexported.
"""

from __future__ import annotations

import io
import struct

import numpy as np
import pytest

import openfemlab.io as openfemlab_io
from openfemlab.core.neutral import ElementType
from openfemlab.io import FormatError
from openfemlab.io.nastran import _ELEMENT_CARDS, read_bdf
from openfemlab.io.op2 import (
    GEOM2_ELEMENT_LAYOUTS,
    GEOM2_ELEMENT_RECORDS,
    MPT_MATERIAL_RECORDS,
    OP2_GEOMETRY_TABLES,
    OP2_MODE_TABLES,
    list_op2_tables,
    read_op2,
    read_op2_modes,
)

from . import _op2

#: The grids of the fixture model, deliberately not numbered from 1 so that a
#: reader that renumbers them instead of carrying the labels is caught.
GRID_LABELS = (11, 22, 33)

#: The entry points that read a file, with an argument that is a plausible OP2
#: source, so a guard can prove where the refusal comes from.
READING_ENTRY_POINTS = [
    pytest.param(read_op2_modes, id="read_op2_modes"),
    pytest.param(read_op2, id="read_op2"),
    pytest.param(list_op2_tables, id="list_op2_tables"),
]


def chain_modes() -> list[_op2.Mode]:
    """Two bending modes of a three-grid chain, in exact binary fractions.

    A 32-bit OP2 stores single-precision floats, so a fixture built from values
    a float32 holds exactly lets the assertions be about the reader rather than
    about rounding.
    """

    return [
        _op2.Mode(
            number=1,
            frequency_hz=12.5,
            shape={
                11: (0.0, 0.0, 0.25, 0.0, 0.125, 0.0),
                22: (0.0, 0.0, 0.75, 0.0, 0.0625, 0.0),
                33: (0.0, 0.0, 1.0, 0.0, -0.125, 0.0),
            },
        ),
        _op2.Mode(
            number=2,
            frequency_hz=41.25,
            shape={
                11: (0.0, 0.0, -1.0, 0.0, -0.5, 0.0),
                22: (0.0, 0.0, 0.5, 0.0, 0.25, 0.0),
                33: (0.0, 0.0, -0.25, 0.0, 0.5, 0.0),
            },
        ),
    ]


def basic_grids(cd: int = 0, cp: int = 0) -> list[_op2.Grid]:
    """The fixture's ``GRID`` cards, in the basic frame unless asked otherwise."""

    return [
        _op2.Grid(id=label, xyz=(float(index), 0.0, 0.0), cp=cp, cd=cd)
        for index, label in enumerate(GRID_LABELS)
    ]


def expected_shape(mode: _op2.Mode) -> np.ndarray:
    """The mode as the ``DofMap`` orders it: six components, grid by grid."""

    return np.concatenate([np.asarray(mode.shape[label]) for label in GRID_LABELS])


# ------------------------------------------------------------------ guards


@pytest.mark.parametrize("entry_point", READING_ENTRY_POINTS)
def test_every_entry_point_reports_a_truncated_file_as_a_format_error(entry_point):
    """Four bytes that frame nothing are a format error from every phase."""

    with pytest.raises(FormatError):
        entry_point(io.BytesIO(b"\x04\x00\x00\x00"))


@pytest.mark.parametrize("entry_point", READING_ENTRY_POINTS)
def test_the_implemented_phases_report_a_missing_file_as_a_format_error(
    entry_point, tmp_path
):
    """An unreadable source is an IO failure of this reader, not a stub."""

    missing = tmp_path / "absent.op2"

    with pytest.raises(FormatError, match="absent.op2"):
        entry_point(missing)


def test_the_reader_is_advertised_by_the_io_package():
    """Round 6 exports the OP2 subset from ``openfemlab.io`` (AC-IO-005).

    Real Nastran corpus validation remains opt-in via ``OPENFEMLAB_OP2_CORPUS``;
    the export marks the API as supported for the synthetic-fixture subset.
    """

    for name in ("read_op2", "read_op2_modes", "list_op2_tables"):
        assert name in openfemlab_io.__all__
        assert hasattr(openfemlab_io, name)


def test_element_records_cover_the_bdf_reader_element_set():
    """The two Nastran doors must agree on which elements they let through.

    A model that imports from bulk data but not from the OP2 of the same run
    would be the worst version of this feature, so the planned ``GEOM2`` subset
    is pinned against the cards :mod:`openfemlab.io.nastran` already reads.
    """

    ascii_blocks = {element_type for element_type, _ in _ELEMENT_CARDS.values()}
    assert set(GEOM2_ELEMENT_RECORDS.values()) == ascii_blocks
    assert GEOM2_ELEMENT_RECORDS[(2958, 51, 177)] is ElementType.QUAD4


def test_every_readable_layout_belongs_to_a_known_element_card():
    """The layout table refines the key table; it may not disagree with it.

    :data:`GEOM2_ELEMENT_LAYOUTS` says how to unpack the records
    :data:`GEOM2_ELEMENT_RECORDS` names, so a key in the first and not the
    second would be connectivity read into no block at all.  Every entry also
    has to place its grids inside the entry it declares, since the reader
    indexes the words it is given without a second bound to check them against.
    """

    assert set(GEOM2_ELEMENT_LAYOUTS) <= set(GEOM2_ELEMENT_RECORDS)
    for entry_words, grid_words in GEOM2_ELEMENT_LAYOUTS.values():
        assert len(set(grid_words)) == len(grid_words)
        assert all(2 <= word < entry_words for word in grid_words)
    assert GEOM2_ELEMENT_LAYOUTS[(3001, 30, 48)] == (4, (2, 3))
    assert MPT_MATERIAL_RECORDS[(103, 1, 77)] == 12


def test_element_records_are_distinct_three_integer_keys():
    """Two cards sharing a key would make the planned dispatch ambiguous."""

    assert len(set(GEOM2_ELEMENT_RECORDS)) == len(GEOM2_ELEMENT_RECORDS)
    for key in GEOM2_ELEMENT_RECORDS:
        assert len(key) == 3
        assert all(isinstance(word, int) and word > 0 for word in key)


def test_the_planned_table_sets_are_disjoint_and_named():
    """Geometry and mode blocks are read by different phases, so they differ."""

    assert not set(OP2_GEOMETRY_TABLES) & set(OP2_MODE_TABLES)
    assert "GEOM1" in OP2_GEOMETRY_TABLES
    assert "LAMA" in OP2_MODE_TABLES
    for name in (*OP2_GEOMETRY_TABLES, *OP2_MODE_TABLES):
        assert name.isupper() and 0 < len(name) <= 8


# --------------------------------------------------------- phase 1: framing


def test_phase1_lists_the_data_blocks_of_a_synthesized_file(tmp_path):
    """Phase 1: framing only, no engineering data.

    The fixture is written by a test-only OP2 writer rather than by Nastran:
    ``[reclen, payload, reclen]`` records, key triplets, and a block name and
    trailer per table.  That is what makes the layer testable offline, and it
    is also its limit — it checks the reader against our reading of the format,
    which is why the corpus test below has to exist alongside it.

    ``OES1X`` is in the file because listing a block the module knows nothing
    about is the whole claim of the framing layer: blocks are skipped by their
    keys, not by understanding them.
    """

    content = _op2.write_op2(
        [
            _op2.geom1_block(basic_grids()),
            _op2.lama_block(chain_modes()),
            _op2.eigenvector_block(chain_modes()),
            _op2.DataBlock(name="OES1X", records=(_op2.integers(5, 6, 7, 8),)),
        ]
    )

    assert list_op2_tables(io.BytesIO(content)) == ["GEOM1", "LAMA", "OUGV1", "OES1X"]

    path = tmp_path / "modes.op2"
    path.write_bytes(content)
    assert list_op2_tables(path) == ["GEOM1", "LAMA", "OUGV1", "OES1X"]


@pytest.mark.parametrize("word_size", [4, 8])
@pytest.mark.parametrize("byte_order", ["<", ">"])
def test_phase1_detects_word_size_and_byte_order(word_size, byte_order):
    """Phase 1: all four framing variants decode to the same table list.

    Both are settled from the opening byte count, which must decode to 4 or 8;
    a file where it decodes to neither under either order is not an OP2 and
    must raise ``FormatError``.
    """

    content = _op2.modes_file(
        chain_modes(), grids=basic_grids(), word_size=word_size, byte_order=byte_order
    )

    assert list_op2_tables(io.BytesIO(content)) == ["GEOM1", "LAMA", "OUGV1"]

    result = read_op2_modes(io.BytesIO(content))
    assert result.frequencies == pytest.approx([12.5, 41.25])
    assert result.meta["word_size"] == word_size
    assert result.meta["byte_order"] == byte_order


def test_phase1_reads_a_file_written_without_a_header():
    """Phase 1: ``PARAM,POST,-2`` writes no date or version, only blocks."""

    content = _op2.modes_file(chain_modes(), grids=basic_grids(), post=-2)

    assert list_op2_tables(io.BytesIO(content)) == ["GEOM1", "LAMA", "OUGV1"]
    assert "solver_version" not in read_op2_modes(io.BytesIO(content)).meta


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(b"", id="empty"),
        pytest.param(b"not a nastran file at all", id="ascii"),
        pytest.param(struct.pack("<i", 12) + b"\x00" * 12, id="wrong-opening-count"),
    ],
)
def test_phase1_rejects_a_file_that_is_not_an_op2(content):
    """The opening byte count is the whole identification of the format."""

    with pytest.raises(FormatError):
        list_op2_tables(io.BytesIO(content))


def test_phase1_joins_the_continuation_blocks_of_a_long_record():
    """A logical record is one record however many blocks Nastran split it into.

    Real files split a record every 4096 bytes into further ``[key, payload]``
    pairs; the fixture splits every 8 words, which reaches the same path with
    a readable file.
    """

    modes = chain_modes()
    whole = _op2.modes_file(modes, grids=basic_grids())
    split = _op2.modes_file(modes, grids=basic_grids(), max_record_words=8)

    assert len(split) > len(whole)
    assert list_op2_tables(io.BytesIO(split)) == ["GEOM1", "LAMA", "OUGV1"]

    result = read_op2_modes(io.BytesIO(split))
    assert result.frequencies == pytest.approx([12.5, 41.25])
    assert result.shapes == pytest.approx(read_op2_modes(io.BytesIO(whole)).shapes)


def test_phase1_rejects_a_record_whose_byte_counts_disagree():
    """A record that closes with a different count than it opened with is junk."""

    content = bytearray(_op2.modes_file(chain_modes(), grids=basic_grids()))
    content[8:12] = struct.pack("<i", 5)  # the closing count of the first marker

    with pytest.raises(FormatError, match="closes with"):
        list_op2_tables(io.BytesIO(bytes(content)))


def test_phase1_rejects_a_truncated_file():
    """A walk may stop at a block boundary and nowhere else."""

    content = _op2.modes_file(chain_modes(), grids=basic_grids())

    with pytest.raises(FormatError, match="file ends"):
        list_op2_tables(io.BytesIO(content[:-4]))


# ----------------------------------------------------------- phase 2: modes


def test_phase2_reads_lama_and_ougv1_into_a_modal_result():
    """Phase 2: modes, with grid labels surviving into the ``DofMap``.

    Frequencies come from ``LAMA`` and shapes from the ``OUGV1`` records, one
    per mode; the ``IDENT`` mode number orders them, and the ``grid_id * 10 +
    device_code`` of each entry gives the label the ``DofMap`` is built on.
    """

    modes = chain_modes()
    content = _op2.modes_file(modes, grids=basic_grids())

    result = read_op2_modes(io.BytesIO(content))

    assert result.n_modes == 2
    assert result.frequencies == pytest.approx([12.5, 41.25])

    dof_map = result.dof_map
    assert dof_map is not None
    assert dof_map.ndof == 6 * len(GRID_LABELS)
    assert list(dof_map.node_ids) == [label for label in GRID_LABELS for _ in range(6)]

    for column, mode in enumerate(modes):
        assert result.shapes[:, column] == pytest.approx(expected_shape(mode))

    assert result.meta["format"] == "nastran-op2"
    assert result.meta["eigenvector_table"] == "OUGV1"
    assert result.meta["mode_numbers"] == (1, 2)
    assert result.meta["subcase"] == 1
    assert result.normalization == "mass"


def test_phase2_orders_the_modes_by_mode_number():
    """The file's record order is the solver's business, not the caller's."""

    modes = list(reversed(chain_modes()))
    content = _op2.modes_file(modes, grids=basic_grids())

    result = read_op2_modes(io.BytesIO(content))

    assert result.meta["mode_numbers"] == (1, 2)
    assert result.frequencies == pytest.approx([12.5, 41.25])
    assert result.shapes[:, 0] == pytest.approx(expected_shape(chain_modes()[0]))


def test_phase2_prefers_the_basic_frame_eigenvectors():
    """``BOUGV1`` is the same shapes in the basic frame, so it wins over ``OUGV1``."""

    modes = chain_modes()
    content = _op2.write_op2(
        [
            _op2.lama_block(modes),
            _op2.eigenvector_block(modes, name="OUGV1"),
            _op2.eigenvector_block(modes, name="BOUGV1"),
        ]
    )

    result = read_op2_modes(io.BytesIO(content))

    assert list_op2_tables(io.BytesIO(content)) == ["LAMA", "OUGV1", "BOUGV1"]
    assert result.meta["eigenvector_table"] == "BOUGV1"


@pytest.mark.parametrize(
    ("options", "message"),
    [
        pytest.param({"analysis_code": 9}, "complex", id="complex-eigenvectors"),
        pytest.param({"sort_code": 2}, "SORT2", id="sort2"),
        pytest.param({"format_code": 2}, "format code", id="real-imaginary"),
        pytest.param({"table_code": 1}, "table code", id="displacement"),
        pytest.param({"num_wide": 14}, "words per entry", id="unexpected-entry-size"),
        pytest.param({"grid_type": 2}, "grid type", id="scalar-points"),
    ],
)
def test_phase2_rejects_complex_and_sort2_output(options, message):
    """Phase 2: refuse what the subset does not cover, rather than guess.

    Complex eigenvectors (analysis code 9) and SORT2 ordering both change the
    entry layout, so an unchecked reader silently returns wrong shapes.  The
    same applies to every other ``IDENT`` code that redefines an entry.
    """

    content = _op2.modes_file(chain_modes(), grids=basic_grids(), **options)

    with pytest.raises(FormatError, match=message):
        read_op2_modes(io.BytesIO(content))


@pytest.mark.parametrize("frame", [{"cp": 3}, {"cd": 7}])
def test_phase2_rejects_undefined_grid_coordinate_systems(frame):
    """``CP``/``CD`` without a ``CORD2R`` definition must raise."""

    content = _op2.modes_file(chain_modes(), grids=basic_grids(**frame))

    with pytest.raises(FormatError, match="reference coordinate system"):
        read_op2_modes(io.BytesIO(content))


def test_phase4_reads_cord2r_transformed_grid_coordinates():
    """Phase 4 maps ``GRID`` locations written in ``CP`` into the basic frame."""
    cord = _op2.Cord2R(
        cid=1,
        origin=(0.0, 0.0, 0.0),
        z_point=(0.0, 0.0, 1.0),
        xz_point=(0.0, 1.0, 0.0),
    )
    grids = [
        _op2.Grid(id=11, xyz=(1.0, 0.0, 0.0), cp=1, cd=0),
        _op2.Grid(id=22, xyz=(2.0, 0.0, 0.0), cp=1, cd=0),
        _op2.Grid(id=33, xyz=(3.0, 0.0, 0.0), cp=1, cd=0),
    ]
    content = _op2.geometry_file(grids, cords=[cord])

    geometry = read_op2(io.BytesIO(content))
    assert geometry.node_ids.tolist() == list(GRID_LABELS)
    assert geometry.nodes[0] == pytest.approx([0.0, 1.0, 0.0])
    assert geometry.nodes[1] == pytest.approx([0.0, 2.0, 0.0])


def test_phase4_reads_cord2r_transformed_eigenvectors():
    """Phase 4 maps eigenvectors written in each grid's ``CD`` frame."""
    cord = _op2.Cord2R(
        cid=1,
        origin=(0.0, 0.0, 0.0),
        z_point=(0.0, 0.0, 1.0),
        xz_point=(0.0, 1.0, 0.0),
    )
    grids = [_op2.Grid(id=11, xyz=(0.0, 0.0, 0.0), cp=0, cd=1)]
    modes = [
        _op2.Mode(
            number=1,
            frequency_hz=10.0,
            shape={11: (1.0, 0.0, 0.0, 0.0, 0.0, 0.0)},
        )
    ]
    content = _op2.modes_file(modes, grids=grids, cords=[cord])
    result = read_op2_modes(io.BytesIO(content))
    assert result.shapes[:, 0] == pytest.approx([0.0, 1.0, 0.0, 0.0, 0.0, 0.0])


def test_phase2_names_the_tables_a_file_without_modes_does_have():
    """The diagnostic Phase 1 exists to deliver, raised from Phase 2."""

    modes = chain_modes()

    without_eigenvalues = _op2.write_op2([_op2.eigenvector_block(modes)])
    with pytest.raises(FormatError, match="no LAMA eigenvalue table"):
        read_op2_modes(io.BytesIO(without_eigenvalues))

    without_shapes = _op2.write_op2([_op2.lama_block(modes)])
    with pytest.raises(FormatError, match="none of the eigenvector tables"):
        read_op2_modes(io.BytesIO(without_shapes))


def test_phase2_rejects_a_record_that_does_not_divide_into_entries():
    """A record length that is not a whole number of entries is a dialect trap.

    MS-9.6: the record keys are stable and the record contents are not, so an
    unpack that does not divide has to name the table rather than read past the
    end of an entry.
    """

    modes = chain_modes()
    truncated = _op2.eigenvector_block(modes)
    records = list(truncated.records)
    records[1] = list(records[1])[:-3]
    content = _op2.write_op2(
        [_op2.lama_block(modes), _op2.DataBlock(name="OUGV1", records=tuple(records))]
    )

    with pytest.raises(FormatError, match="not a multiple of"):
        read_op2_modes(io.BytesIO(content))


# ------------------------------------------------------- phase 3: geometry
#
# The fixture model is the two-element rod chain below, written both as bulk
# data and as an OP2, so the two Nastran doors can be held against each other.
# Its coordinates and material constants are binary fractions, since a 32-bit
# OP2 stores single-precision reals and the assertions are about the reader.

ROD_PROPERTY_ID = 40

ROD_BDF = """\
GRID,11,,0.,0.,0.
GRID,22,,1.,0.,0.
GRID,33,,2.,0.5,0.
CROD,100,40,11,22
CROD,200,40,22,33
MAT1,7,2.5+8,,0.25,7.75+3
"""


def rod_grids(**frame: int) -> list[_op2.Grid]:
    """The fixture's three ``GRID`` cards, in the basic frame unless told not to."""

    return [
        _op2.Grid(id=11, xyz=(0.0, 0.0, 0.0), **frame),
        _op2.Grid(id=22, xyz=(1.0, 0.0, 0.0), **frame),
        _op2.Grid(id=33, xyz=(2.0, 0.5, 0.0), **frame),
    ]


def rod_elements() -> list[_op2.Rod]:
    """The fixture's two ``CROD`` cards, sharing one ``PROD`` they do not define."""

    return [
        _op2.Rod(id=100, property_id=ROD_PROPERTY_ID, grids=(11, 22)),
        _op2.Rod(id=200, property_id=ROD_PROPERTY_ID, grids=(22, 33)),
    ]


def rod_materials() -> list[_op2.Mat1]:
    """The fixture's single ``MAT1``, in constants a float32 holds exactly."""

    return [_op2.Mat1(id=7, E=2.5e8, G=1.0e8, nu=0.25, rho=7.75e3)]


def rod_properties() -> list[_op2.Prod]:
    """The fixture's ``PROD`` for the shared rod property id."""

    return [_op2.Prod(id=ROD_PROPERTY_ID, material_id=7, area=1.0e-4)]


def test_phase3_reads_grids_elements_and_materials_into_a_neutral_model():
    """Phase 3: ``GEOM1`` grids, ``GEOM2`` connectivity and ``MPT`` materials.

    Labels are the point: a reader that renumbers the grids from 1, or that
    drops the element ids, breaks the MS-9.1 promise that an imported model
    aligns against a test set through the labels the solver used.
    """

    content = _op2.geometry_file(rod_grids(), rod_elements(), rod_materials())

    model = read_op2(io.BytesIO(content))

    assert list(model.node_ids) == [11, 22, 33]
    np.testing.assert_allclose(
        model.nodes, [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.5, 0.0]]
    )
    assert list(model.elements) == [ElementType.ROD2]
    np.testing.assert_array_equal(model.elements[ElementType.ROD2], [[11, 22], [22, 33]])
    np.testing.assert_array_equal(
        model.element_property_ids[ElementType.ROD2], [ROD_PROPERTY_ID] * 2
    )

    material = model.materials[7]
    assert (material.E, material.nu, material.rho) == (2.5e8, 0.25, 7.75e3)

    assert model.meta["format"] == "nastran-op2"
    assert model.meta["tables"] == ("GEOM1", "GEOM2", "MPT")
    assert model.meta["element_ids"] == {"rod2": [100, 200]}
    assert model.meta["skipped_records"] == {}


@pytest.mark.parametrize("word_size", [4, 8])
@pytest.mark.parametrize("byte_order", ["<", ">"])
def test_phase3_reads_the_same_model_from_every_framing_variant(word_size, byte_order):
    """The geometry records ride on Phase 1's framing, all four forms of it."""

    content = _op2.geometry_file(
        rod_grids(),
        rod_elements(),
        rod_materials(),
        word_size=word_size,
        byte_order=byte_order,
    )

    model = read_op2(io.BytesIO(content))

    assert list(model.node_ids) == [11, 22, 33]
    np.testing.assert_allclose(model.nodes[2], [2.0, 0.5, 0.0])
    np.testing.assert_array_equal(model.elements[ElementType.ROD2], [[11, 22], [22, 33]])
    assert model.materials[7].rho == 7.75e3
    assert model.meta["word_size"] == word_size
    assert model.meta["byte_order"] == byte_order


def test_phase3_geometry_matches_the_bdf_of_the_same_model():
    """Phase 3: the acceptance shape of the geometry work.

    Reading a model's bulk data and reading the OP2 of the run it produced must
    give equal ``NeutralModel``s — same labels, same blocks, same materials.
    Any divergence is a bug in one of the two readers, and this is the only
    test that can tell us which.  ``PROD`` is in neither subset, so the section
    survives both readings as the property id on the element and nothing more.
    """

    from_bdf = read_bdf(io.StringIO(ROD_BDF))
    from_op2 = read_op2(
        io.BytesIO(_op2.geometry_file(rod_grids(), rod_elements(), rod_materials()))
    )

    np.testing.assert_array_equal(from_op2.node_ids, from_bdf.node_ids)
    np.testing.assert_allclose(from_op2.nodes, from_bdf.nodes)
    assert list(from_op2.elements) == list(from_bdf.elements)
    for element_type, connectivity in from_bdf.elements.items():
        np.testing.assert_array_equal(from_op2.elements[element_type], connectivity)
        np.testing.assert_array_equal(
            from_op2.element_property_ids[element_type],
            from_bdf.element_property_ids[element_type],
        )
    assert from_op2.materials == from_bdf.materials
    assert from_op2.properties == from_bdf.properties == {}
    assert from_op2.meta["element_ids"] == from_bdf.meta["element_ids"]


@pytest.mark.parametrize("frame", [{"cp": 3}, {"cd": 7}])
def test_phase3_rejects_undefined_grid_coordinate_systems(frame):
    """Phase 3: ``CP``/``CD`` without ``CORD2R`` must raise."""

    content = _op2.geometry_file(rod_grids(**frame), rod_elements())

    with pytest.raises(FormatError, match="reference coordinate system"):
        read_op2(io.BytesIO(content))


def test_phase3_refuses_an_element_card_whose_layout_it_cannot_unpack():
    """A known card without a layout is a refusal, not a skip.

    ``GEOM2_ELEMENT_RECORDS`` promises the solver has a formulation for the
    card, so dropping its record would return a model that looks complete and
    has silently lost a whole element block.  The record here is four ``CROD``
    words written under the ``CQUAD4`` key, which is what a card outside the
    layout table looks like from the reader's side.
    """

    content = _op2.write_op2(
        [
            _op2.geom1_block(rod_grids()),
            _op2.geom2_block(rod_elements(), key=(2958, 51, 177)),
        ]
    )

    with pytest.raises(FormatError, match="quad4"):
        read_op2(io.BytesIO(content))


def test_phase3_skips_and_counts_the_records_outside_its_subset():
    """MS-9.3 partial import: what was not read is reported, not forgotten.

    A ``CBUSH`` record is a card no block of this model has, and ``EPT`` is the
    property table the next increment reads; both are stepped over, and both
    are counted so that a caller can tell a complete import from a partial one.
    """

    unknown_geom2 = _op2.geom2_block(rod_elements(), key=(2608, 26, 60))
    unknown_ept = _op2.DataBlock(
        name="EPT",
        records=(_op2.integers(1602, 16, 30, 40, 7, 0.1, 0.2),),
        subtable_name="EPTS",
    )
    content = _op2.write_op2(
        [
            _op2.geom1_block(rod_grids()),
            _op2.DataBlock(
                name="GEOM2",
                records=(*_op2.geom2_block(rod_elements()).records, *unknown_geom2.records),
                subtable_name="GEOM2S",
            ),
            unknown_ept,
            _op2.mpt_block(rod_materials()),
        ]
    )

    model = read_op2(io.BytesIO(content))

    assert model.meta["skipped_records"] == {"GEOM2": 1, "EPT": 1}
    np.testing.assert_array_equal(model.elements[ElementType.ROD2], [[11, 22], [22, 33]])
    assert model.properties == {}


def test_phase3_reads_prod_from_ept():
    """Phase 3: ``EPT`` ``PROD`` area lands in ``NeutralModel.properties``."""

    content = _op2.geometry_file(
        rod_grids(), rod_elements(), rod_materials(), properties=rod_properties()
    )

    model = read_op2(io.BytesIO(content))

    prop = model.properties[ROD_PROPERTY_ID]
    assert prop.name == "PROD"
    assert prop.material_id == 7
    assert prop.values["A"] == pytest.approx(1.0e-4)
    assert prop.values["area"] == pytest.approx(1.0e-4)
    assert model.meta["tables"] == ("GEOM1", "GEOM2", "EPT", "MPT")


def test_phase3_reads_pshell_and_psolid_from_ept():
    """Phase 3: ``PSHELL`` thickness and ``PSOLID`` material id import."""

    content = _op2.write_op2(
        [
            _op2.geom1_block([_op2.Grid(id=11, xyz=(0.0, 0.0, 0.0))]),
            _op2.pshell_block([_op2.Pshell(id=10, material_id=7, thickness=0.0025)]),
            _op2.psolid_block([_op2.Psolid(id=20, material_id=7)]),
            _op2.mpt_block(rod_materials()),
        ]
    )

    model = read_op2(io.BytesIO(content))

    shell = model.properties[10]
    assert shell.name == "PSHELL"
    assert shell.material_id == 7
    assert shell.values["t"] == pytest.approx(0.0025)

    solid = model.properties[20]
    assert solid.name == "PSOLID"
    assert solid.material_id == 7
    assert solid.values == {}


def test_phase3_pshell_matches_bdf_of_the_same_property():
    """Phase 3: ``PSHELL``/``PSOLID`` agree with the bulk-data reader."""

    bdf_text = """\
GRID,11,,0.,0.,0.
PSHELL,10,7,0.0025
PSOLID,20,7
MAT1,7,2.5+8,,0.25,7.75+3
"""
    content = _op2.write_op2(
        [
            _op2.geom1_block([_op2.Grid(id=11, xyz=(0.0, 0.0, 0.0))]),
            _op2.pshell_block([_op2.Pshell(id=10, material_id=7, thickness=0.0025)]),
            _op2.psolid_block([_op2.Psolid(id=20, material_id=7)]),
            _op2.mpt_block(rod_materials()),
        ]
    )

    from_bdf = read_bdf(io.StringIO(bdf_text))
    from_op2 = read_op2(io.BytesIO(content))

    assert from_op2.properties[10].name == from_bdf.properties[10].name
    assert from_op2.properties[10].material_id == from_bdf.properties[10].material_id
    assert from_op2.properties[10].values["t"] == pytest.approx(
        from_bdf.properties[10].values["t"]
    )
    assert from_op2.properties[20] == from_bdf.properties[20]


def test_phase3_rejects_a_record_that_does_not_divide_into_entries():
    """The dialect trap of MS-9.6, on the geometry side.

    A ``GEOM2`` record one word short of a whole number of entries is what a
    reader assuming the wrong dialect sees, and reading past the end of an
    entry is how it turns into wrong connectivity instead of an error.
    """

    rods = _op2.geom2_block(rod_elements())
    truncated = list(rods.records[0])[:-1]
    content = _op2.write_op2(
        [
            _op2.geom1_block(rod_grids()),
            _op2.DataBlock(name="GEOM2", records=(truncated,), subtable_name="GEOM2S"),
        ]
    )

    with pytest.raises(FormatError, match="not a multiple of"):
        read_op2(io.BytesIO(content))


def test_phase3_rejects_connectivity_that_names_a_grid_the_file_does_not_define():
    """An element hanging off a grid that is not there is an unusable model."""

    content = _op2.geometry_file(
        rod_grids()[:2],
        [*rod_elements(), _op2.Rod(id=300, property_id=ROD_PROPERTY_ID, grids=(33, 44))],
    )

    with pytest.raises(FormatError, match="33, 44"):
        read_op2(io.BytesIO(content))


@pytest.mark.parametrize(
    ("blocks", "message"),
    [
        pytest.param(
            lambda: [_op2.geom1_block([*rod_grids(), _op2.Grid(id=22, xyz=(9.0, 0.0, 0.0))])],
            "duplicate GRID id 22",
            id="duplicate-grid",
        ),
        pytest.param(
            lambda: [
                _op2.geom1_block(rod_grids()),
                _op2.geom2_block(
                    [*rod_elements(), _op2.Rod(id=100, property_id=1, grids=(11, 33))]
                ),
            ],
            "duplicate element id 100",
            id="duplicate-element",
        ),
        pytest.param(
            lambda: [
                _op2.geom1_block(rod_grids()),
                _op2.mpt_block([*rod_materials(), _op2.Mat1(id=7, E=1.0)]),
            ],
            "duplicate MAT1 id 7",
            id="duplicate-material",
        ),
    ],
)
def test_phase3_rejects_a_label_the_file_defines_twice(blocks, message):
    """Two cards under one label make the import order decide the model."""

    with pytest.raises(FormatError, match=message):
        read_op2(io.BytesIO(_op2.write_op2(blocks())))


def test_phase3_refuses_the_double_precision_grid_dialect():
    """The 11-word ``GRID`` writes its location in two words per coordinate.

    Reading it as the 8-word form would unpack half of an ``X1`` as a whole
    coordinate, so the dialect is named and refused until it is implemented.
    """

    content = _op2.write_op2(
        [_op2.geom1_block(rod_grids(), key=(4501, 45, 1120001))]
    )

    with pytest.raises(FormatError, match="double precision"):
        read_op2(io.BytesIO(content))


def test_phase3_names_the_tables_a_file_without_geometry_does_have():
    """The Phase 1 diagnostic again, raised from Phase 3.

    An OP2 written by a run that requested only results has no ``GEOM1`` in it,
    which is a wrong ``PARAM,POST`` rather than a broken file — so the answer
    is the list of blocks the file *does* carry.
    """

    content = _op2.write_op2([_op2.lama_block(chain_modes())])
    with pytest.raises(FormatError, match="no GEOM1 table"):
        read_op2(io.BytesIO(content))

    empty = _op2.write_op2([_op2.geom1_block([])])
    with pytest.raises(FormatError, match="no GRID records"):
        read_op2(io.BytesIO(empty))


# ------------------------------------------------- skipped phase contracts

_NOT_IMPLEMENTED = (
    "OP2 corpus import not implemented; this states the contract of the "
    "remaining roadmap phase"
)


@pytest.mark.skip(reason=_NOT_IMPLEMENTED)
def test_real_op2_corpus_round_trip():
    """The test the synthesized fixtures cannot replace.

    Opt-in over a directory of real solver output (``OPENFEMLAB_OP2_CORPUS``),
    skipped when it is unset, because OP2 files cannot be produced without a
    Nastran licence and none can be committed here.  Until this runs over MSC
    *and* NX output, the reader stays experimental — and unexported — however
    green the synthesized tests are.
    """

    raise NotImplementedError
