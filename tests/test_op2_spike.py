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
from openfemlab.io.nastran import _ELEMENT_CARDS
from openfemlab.io.op2 import (
    GEOM2_ELEMENT_RECORDS,
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


def test_the_unimplemented_phase_refuses_with_a_roadmap_pointer():
    """A stub that raises without saying what to do instead is a dead end."""

    with pytest.raises(NotImplementedError) as excinfo:
        read_op2(io.BytesIO(b"\x04\x00\x00\x00"))

    message = str(excinfo.value)
    assert "not implemented" in message
    assert "MS-9.6" in message


def test_the_unimplemented_phase_refuses_before_reading(tmp_path):
    """Phase 3 must not open, seek or consume its source to say no."""

    missing = tmp_path / "absent.op2"

    with pytest.raises(NotImplementedError):
        read_op2(missing)

    assert not missing.exists()


@pytest.mark.parametrize("entry_point", READING_ENTRY_POINTS)
def test_the_implemented_phases_report_a_missing_file_as_a_format_error(
    entry_point, tmp_path
):
    """An unreadable source is an IO failure of this reader, not a stub."""

    missing = tmp_path / "absent.op2"

    with pytest.raises(FormatError, match="absent.op2"):
        entry_point(missing)


def test_the_reader_is_not_advertised_by_the_io_package():
    """An exported name promises a *supported* reader; this one is not one yet.

    Phases 1 and 2 work, but only against the files ``tests/_op2.py`` writes —
    that is, against our own reading of the format.  MS-9.6 makes the opt-in
    corpus test over real MSC and NX output the condition for calling the
    reader supported, so until it runs the entry points stay reachable only as
    ``openfemlab.io.op2.read_op2_modes``.
    """

    for name in ("read_op2", "read_op2_modes", "list_op2_tables"):
        assert name not in openfemlab_io.__all__
        assert not hasattr(openfemlab_io, name)


def test_element_records_cover_the_bdf_reader_element_set():
    """The two Nastran doors must agree on which elements they let through.

    A model that imports from bulk data but not from the OP2 of the same run
    would be the worst version of this feature, so the planned ``GEOM2`` subset
    is pinned against the cards :mod:`openfemlab.io.nastran` already reads.
    """

    ascii_blocks = {element_type for element_type, _ in _ELEMENT_CARDS.values()}
    assert set(GEOM2_ELEMENT_RECORDS.values()) == ascii_blocks
    assert GEOM2_ELEMENT_RECORDS[(2958, 51, 177)] is ElementType.QUAD4


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
def test_phase2_rejects_non_basic_grid_coordinate_systems(frame):
    """``CP``/``CD`` are wrong coordinates, not missing metadata.

    OP2 eigenvectors are written in each grid's ``CD`` frame, so until Phase 4
    reads the ``CORD`` cards a non-zero frame must raise — the line
    ``read_bdf`` already draws for ``GRID``.
    """

    content = _op2.modes_file(chain_modes(), grids=basic_grids(**frame))

    with pytest.raises(FormatError, match="non-basic coordinate system"):
        read_op2_modes(io.BytesIO(content))


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


# ------------------------------------------------- skipped phase contracts

_NOT_IMPLEMENTED = (
    "OP2 geometry import not implemented (GAP-03 extension, MODULE_SPEC MS-9.6 "
    "Phase 3); these state the contract of each remaining roadmap phase"
)


@pytest.mark.skip(reason=_NOT_IMPLEMENTED)
def test_phase3_geometry_matches_the_bdf_of_the_same_model():
    """Phase 3: the acceptance shape of the geometry work.

    Reading a model's bulk data and reading the OP2 of the run it produced must
    give equal ``NeutralModel``s — same labels, same blocks, same properties.
    Any divergence is a bug in one of the two readers, and this is the only
    test that can tell us which.
    """

    raise NotImplementedError


@pytest.mark.skip(reason=_NOT_IMPLEMENTED)
def test_phase3_rejects_non_basic_grid_coordinate_systems():
    """Phase 3: ``CP``/``CD`` are wrong coordinates, not missing metadata.

    Until Phase 4 reads the ``CORD`` cards, a non-zero frame must raise, the
    line ``read_bdf`` already draws for ``GRID`` — as Phase 2 already does for
    the eigenvectors written in ``CD``.
    """

    raise NotImplementedError


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
