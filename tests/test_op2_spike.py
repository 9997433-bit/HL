"""Guards and contract placeholders for the unimplemented OP2 reader.

Two kinds of test live here.  The first kind runs: it pins the decisions the
GAP-03 spike took, so a later change cannot quietly turn the stub into a
half-reader or leak it into the public :mod:`openfemlab.io` namespace before it
reads a file.  The second kind is skipped, and states the contract each roadmap
phase (MODULE_SPEC MS-9.6) has to satisfy — including the fixture problem that
is the reason the reader does not exist yet.
"""

from __future__ import annotations

import io

import pytest

import openfemlab.io as openfemlab_io
from openfemlab.core.neutral import ElementType
from openfemlab.io.nastran import _ELEMENT_CARDS
from openfemlab.io.op2 import (
    GEOM2_ELEMENT_RECORDS,
    OP2_GEOMETRY_TABLES,
    OP2_MODE_TABLES,
    list_op2_tables,
    read_op2,
    read_op2_modes,
)

#: Every entry point, with an argument that is a plausible OP2 source, so the
#: guard below proves the refusal comes before any reading.
ENTRY_POINTS = [
    pytest.param(read_op2, id="read_op2"),
    pytest.param(read_op2_modes, id="read_op2_modes"),
    pytest.param(list_op2_tables, id="list_op2_tables"),
]


# ------------------------------------------------------------------ guards


@pytest.mark.parametrize("entry_point", ENTRY_POINTS)
def test_every_entry_point_refuses_with_a_roadmap_pointer(entry_point):
    """A stub that raises without saying what to do instead is a dead end."""

    with pytest.raises(NotImplementedError) as excinfo:
        entry_point(io.BytesIO(b"\x04\x00\x00\x00"))

    message = str(excinfo.value)
    assert "not implemented" in message
    assert "MS-9.6" in message


@pytest.mark.parametrize("entry_point", ENTRY_POINTS)
def test_refusal_precedes_reading(entry_point, tmp_path):
    """The stub must not open, seek or consume its source."""

    missing = tmp_path / "absent.op2"

    with pytest.raises(NotImplementedError):
        entry_point(missing)

    assert not missing.exists()


def test_the_stub_is_not_advertised_by_the_io_package():
    """An exported name promises a working reader; this one does not work.

    ``openfemlab.io.op2`` stays importable so the roadmap and its record tables
    are reachable, but the package namespace gains nothing until Phase 2 lands.
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


# ------------------------------------------------- skipped phase contracts

_NOT_IMPLEMENTED = (
    "OP2 reader not implemented (GAP-03 extension, MODULE_SPEC MS-9.6); "
    "these state the contract of each roadmap phase"
)


@pytest.mark.skip(reason=_NOT_IMPLEMENTED)
def test_phase1_lists_the_data_blocks_of_a_synthesized_file():
    """Phase 1: framing only, no engineering data.

    The fixture is written by a test-only OP2 writer rather than by Nastran:
    ``[reclen, payload, reclen]`` records, key triplets, and a block name and
    trailer per table.  That is what makes the layer testable offline, and it
    is also its limit — it checks the reader against our reading of the format,
    which is why the corpus test below has to exist alongside it.
    """

    raise NotImplementedError


@pytest.mark.skip(reason=_NOT_IMPLEMENTED)
@pytest.mark.parametrize("word_size", [4, 8])
@pytest.mark.parametrize("byte_order", ["<", ">"])
def test_phase1_detects_word_size_and_byte_order(word_size, byte_order):
    """Phase 1: all four framing variants decode to the same table list.

    Both are settled from the opening byte count, which must decode to 4 or 8;
    a file where it decodes to neither under either order is not an OP2 and
    must raise ``FormatError``.
    """

    raise NotImplementedError


@pytest.mark.skip(reason=_NOT_IMPLEMENTED)
def test_phase2_reads_lama_and_ougv1_into_a_modal_result():
    """Phase 2: modes, with grid labels surviving into the ``DofMap``.

    Frequencies come from ``LAMA`` and shapes from the ``OUGV1`` records, one
    per mode; the ``IDENT`` mode number orders them, and the ``grid_id * 10 +
    device_code`` of each entry gives the label the ``DofMap`` is built on.
    """

    raise NotImplementedError


@pytest.mark.skip(reason=_NOT_IMPLEMENTED)
def test_phase2_rejects_complex_and_sort2_output():
    """Phase 2: refuse what the subset does not cover, rather than guess.

    Complex eigenvectors (analysis code 9) and SORT2 ordering both change the
    entry layout, so an unchecked reader silently returns wrong shapes.
    """

    raise NotImplementedError


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
    line ``read_bdf`` already draws for ``GRID``.
    """

    raise NotImplementedError


@pytest.mark.skip(reason=_NOT_IMPLEMENTED)
def test_real_op2_corpus_round_trip():
    """The test the synthesized fixtures cannot replace.

    Opt-in over a directory of real solver output (``OPENFEMLAB_OP2_CORPUS``),
    skipped when it is unset, because OP2 files cannot be produced without a
    Nastran licence and none can be committed here.  Until this runs over MSC
    *and* NX output, the reader stays experimental however green the
    synthesized tests are.
    """

    raise NotImplementedError
