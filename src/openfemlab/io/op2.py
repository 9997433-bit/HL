"""Reader for the Nastran OP2 binary result file — framing and normal modes.

OP2 is the binary companion of the ASCII bulk data :mod:`openfemlab.io.nastran`
reads: one file that can carry the analysed model *and* its normal-mode
solution, which is exactly the pair the correlation and updating modules need
from an industrial solver.  Reaching it means writing a binary parser, and a
binary parser without a test corpus is a liability, so the reader is landed in
phases (GAP-03 extension, MODULE_SPEC MS-9.6), each with its own tests:
Phase 1 (the record framing), Phase 2 (the normal modes) and the first
increment of Phase 3 (``GRID`` geometry, ``CROD`` connectivity and ``MAT1``
materials) are implemented here.

Nothing here is re-exported from :mod:`openfemlab.io`.  A name in that
namespace advertises a *supported* reader, and this one is validated only
against files this repository's own test writer produces (``tests/_op2.py``) —
that is, against our reading of the format rather than against Nastran.  The
break in the MS-9.5 rule ends when the opt-in corpus test over real MSC and NX
output has run; until then the reader is reachable as
``openfemlab.io.op2.read_op2_modes`` and no shorter.

What the format looks like
--------------------------
An OP2 is a Fortran unformatted sequential file: every physical record is
``[reclen, payload, reclen]`` with a 32-bit byte count on both ends.  Above
that framing sit two more layers.

*Words.* Records are read as 4-byte words, but a 64-bit OP2 uses 8-byte words
throughout, and either width may be big- or little-endian.  Both are settled
from the first four bytes of the file, which are the byte count of the opening
record and must decode to 4 or 8; the value picks the word size and the byte
order that made it decode.

*Keys and data blocks.* A logical record is a *key* triplet giving a word
count, followed by that many words of payload, optionally continued by further
``[key, payload]`` pairs; a key of 0 ends the record, and a second 0 ends the
data block.  Blocks are self-describing: a block opens with its 8-character
name (``GEOM1``, ``OUGV1``, ``LAMA``, ...) and a trailer, so a reader can
identify a block and skip the ones it does not want by walking keys, without
understanding their contents.  That property is what makes a *subset* reader
honest rather than fragile — every table below can be skipped structurally.
:mod:`openfemlab.io.op2_framing` is that layer, and only that layer.

*The file header.* The opening marker distinguishes the two ways Nastran is
asked to write an OP2: ``3`` for ``PARAM,POST,-1``, which is followed by the
date record and the ``NASTRAN FORT TAPE ID CODE - `` label plus a version
string, and ``2`` for ``PARAM,POST,-2``, which has no header at all.  The
version string is the only in-band signal of the writing solver, and MSC, NX,
Simcenter, OptiStruct and Autodesk all differ somewhere below.

The subset worth reading
------------------------
Geometry lands in ``NeutralModel`` and modes in ``ModalResult``, matching what
every other reader in MS-9 produces:

===============  ==========================================================
Data block       What the subset takes from it
===============  ==========================================================
``GEOM1``        ``GRID`` — node labels and coordinates
``GEOM2``        the connectivity cards of :data:`GEOM2_ELEMENT_RECORDS`
``EPT``          ``PSHELL`` thickness, ``PSOLID``, ``PROD`` area
``MPT``          ``MAT1`` — E, G, nu, rho
``LAMA``         the eigenvalue table: mode number, frequency, modal mass
``OUGV1``        eigenvectors at grid points, one record per mode
===============  ==========================================================

Everything else is skipped by construction: ``GEOM3``/``GEOM4`` (loads and
constraints, which MS-9.4 states are outside the interchange contract),
``OES``/``OEF`` (element stresses and forces, which no module consumes),
``DYNAMIC``, ``DIT``, ``EDT``, and the matrix blocks ``KAA``/``MAA``.

Inside a geometry block, records are addressed by a three-integer key rather
than by position, so a subset reader dispatches on the key and skips the rest —
see :data:`GEOM2_ELEMENT_RECORDS`.  Result blocks are laid out differently: a
146-word ``IDENT`` record describes the case, then one data record holds the
values.  For normal modes ``IDENT`` word 1 is ``device_code + 10 *
analysis_code`` with analysis code 2, word 2 is the table code (7 =
eigenvector), word 5 is the mode number, word 6 the eigenvalue, word 7 the
frequency in radians, and word 10 the number of words per entry.  A real
eigenvector entry is 8 of those words — ``grid_id * 10 + device_code``, a grid
type flag, then T1, T2, T3, R1, R2, R3 — while a scalar point carries one
value in place of six.

Roadmap
-------
Each phase is independently landable and independently testable, and no phase
ships without the tests named in it.

**Phase 1 — framing.**  *Implemented* in :mod:`openfemlab.io.op2_framing`.  The
record layer only: word size and byte-order detection, the key/continuation
walk, block name and trailer, and a directory of ``(name, offset)`` for the
whole file.  This phase reads no engineering data, which is what makes it cheap
to test exhaustively — truncated records, mismatched trailing byte counts, a
64-bit file, a byte-swapped file.  It also delivers something useful on its
own: :func:`list_op2_tables` tells a user why their file has no modes in it.

**Phase 2 — modes.**  *Implemented*: :func:`read_op2_modes` pairs ``LAMA`` with
the eigenvectors of ``BOUGV1``/``OUGV1``/``OUG1`` into a ``ModalResult`` whose
``DofMap`` carries the file's grid labels, so an imported eigenvector aligns
against a test set through the existing MS-4 label matching.  Restricted to
real normal modes in SORT1: complex eigenvectors, SORT2 and random output all
raise rather than being guessed at.

**Phase 3 — geometry.**  ``GEOM1``/``GEOM2``/``EPT``/``MPT`` into a
``NeutralModel``, reusing the element and property vocabulary
:mod:`openfemlab.io.nastran` already established for the same cards in ASCII,
so a BDF and its OP2 import to equal models.  Unknown records are skipped and
counted in ``meta``, the partial-import policy of MS-9.3.  *Partly
implemented*: :func:`read_op2` reads ``GRID`` from ``GEOM1``, ``CROD`` from
``GEOM2`` and ``MAT1`` from ``MPT``.  Each further card is one entry in
:data:`GEOM2_ELEMENT_LAYOUTS` or :data:`MPT_MATERIAL_RECORDS` plus the tests
that pin its word layout, and until a card has both, a record carrying it is
*refused* rather than dropped — a model quietly missing its elements is worse
than one that did not import.  The ``EPT`` property tables are the remaining
increment.

**Phase 4 — coordinate systems.**  ``CORD1R``/``CORD2R`` and the ``CP``/``CD``
fields, which Phases 2 and 3 must reject rather than ignore (see below).

What still stands between this and "supported"
----------------------------------------------
Three risks decided the shape of the work, and none of them is about the
parsing:

*No corpus.* Producing an OP2 needs a Nastran licence, so the test files
cannot be generated in CI the way UFF and BDF fixtures are.  The way out taken
here is a test-only writer (``tests/_op2.py``): it emits the framing and record
layouts documented above from a known model, and the tests assert the reader
recovers it.  That validates every byte layout this module claims and runs
offline, but it validates them against *our reading of the spec*, not against
Nastran — so it must be paired with an opt-in corpus test over real files (an
environment variable pointing at a directory, skipped when unset) before the
reader may be called supported.  That test is still outstanding, which is why
nothing here is exported.

*Dialects.* The record keys are stable, the record *contents* are not.
``CQUAD4`` is the standing example: NX writes 14 words and MSC writes 15, under
the same key ``(2958, 51, 177)``, distinguishable only by dividing the record
length.  Every phase must therefore validate that a record length is a
multiple of the layout it assumes and name the block and key when it is not,
rather than reading past the end of an entry.

*Coordinate systems.* ``GRID`` carries a ``CP`` (definition) and ``CD``
(output) frame, and OP2 eigenvectors are written in ``CD``.  A model with any
non-zero ``CP``/``CD`` and no ``CORD`` transform would import with silently
wrong coordinates and shapes, so Phases 2 and 3 raise on it — the same line
:func:`~openfemlab.io.nastran.read_bdf` already draws for ``GRID`` and
:mod:`openfemlab.io.unv` draws for dataset 2420.

An optional dependency on `pyNastran <https://github.com/SteveDoyle2/pyNastran>`_
(BSD-3) would cover all of this today, behind the MS-9.3 seam that already
holds ``meshio``.  The spike recommends against making that the *only* path:
OP2 is the format an FE-correlation tool is judged on, and the Phase 1-2 subset
is a few hundred lines over a stable framing.  pyNastran earns its place on the
other side, as the dev-only oracle that says whether our reading of a real file
matches a mature one.

References
----------
The record keys and word layouts recorded here were cross-checked against
pyNastran 1.4.1 (``op2/tables/geom/``, ``op2/op2_interface/op2_reader.py``) and
pyYeti's ``nastran.op2`` format notes; both are independent implementations of
the MSC DMAP documentation.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from typing import BinaryIO, NamedTuple

import numpy as np

from openfemlab.core.dofs import DofMap, DofType
from openfemlab.core.neutral import ElementType, NeutralMaterial, NeutralModel
from openfemlab.core.results import ModalResult

from ._common import FormatError
from .op2_coordinates import (
    GEOM1_CORD2R_RECORD,
    RectangularSystem,
    read_cord2r_systems,
    require_defined_frames,
    resolve_rectangular_systems,
    transform_point_to_basic,
    transform_six_dof_to_basic,
)
from .op2_framing import OP2Block, OP2Format, read_op2_blocks

__all__ = [
    "GEOM1_CORD2R_RECORD",
    "GEOM1_GRID_RECORDS",
    "GEOM2_ELEMENT_LAYOUTS",
    "GEOM2_ELEMENT_RECORDS",
    "MPT_MATERIAL_RECORDS",
    "OP2_GEOMETRY_TABLES",
    "OP2_MODE_TABLES",
    "list_op2_tables",
    "read_op2",
    "read_op2_modes",
]

#: Data blocks Phase 3 reads geometry from, in the order a reader meets them.
OP2_GEOMETRY_TABLES: tuple[str, ...] = ("GEOM1", "GEOM2", "EPT", "MPT")

#: Data blocks Phase 2 reads modes from.  ``LAMA`` holds the eigenvalue table
#: and the ``OUG`` family the eigenvectors; ``BOUGV1`` is the same content in
#: the basic frame, which is why it is the preferred one when a file has both.
OP2_MODE_TABLES: tuple[str, ...] = ("LAMA", "BOUGV1", "OUGV1", "OUG1")

#: ``GEOM2`` record key → the neutral block that record fills, for the element
#: types :mod:`openfemlab.core.elements` has a formulation for.  Keys are the
#: three-integer record header Nastran writes ahead of each card's data and are
#: stable across MSC and NX; the *word layouts* behind them are not, so a
#: reader must check the record length against the entry size it assumes
#: before unpacking (``CQUAD4`` is 14 words in NX and 15 in MSC).
#:
#: Solid cards are shared with their higher-order relatives — ``CTETRA`` writes
#: 12 words whether or not the trailing 6 mid-side grids are zero — so, as in
#: the ASCII reader, a record with mid-side nodes must be rejected rather than
#: truncated to its corners.
GEOM2_ELEMENT_RECORDS: dict[tuple[int, int, int], ElementType] = {
    (3001, 30, 48): ElementType.ROD2,     # CROD
    (2408, 24, 180): ElementType.BEAM2,   # CBAR
    (2958, 51, 177): ElementType.QUAD4,   # CQUAD4
    (5508, 55, 217): ElementType.TET4,    # CTETRA
    (7308, 73, 253): ElementType.HEX8,    # CHEXA
}

#: Order the connectivity blocks are emitted in, so two files declaring the
#: same elements in a different order still import to identical models.  It is
#: the declaration order of :data:`GEOM2_ELEMENT_RECORDS`, which is the card
#: order :mod:`openfemlab.io.nastran` uses for the same blocks.
_BLOCK_ORDER: tuple[ElementType, ...] = tuple(dict.fromkeys(GEOM2_ELEMENT_RECORDS.values()))

#: ``GEOM2`` record key → ``(words per entry, the words holding its grids)``,
#: the layout Phase 3 unpacks the record with.  Word 0 of an entry is always
#: the element id and word 1 its property id, so the grid words are the only
#: thing a card has to declare here.
#:
#: A key in :data:`GEOM2_ELEMENT_RECORDS` and missing from this table names a
#: card the solver has a formulation for and this phase cannot unpack yet.
#: :func:`read_op2` refuses such a record instead of skipping it: the element
#: block would otherwise be absent from a model that looks complete.
GEOM2_ELEMENT_LAYOUTS: dict[tuple[int, int, int], tuple[int, tuple[int, ...]]] = {
    (3001, 30, 48): (4, (2, 3)),  # CROD: EID, PID, G1, G2
}

#: ``MPT`` record key → words per entry, for the material cards Phase 3 reads.
#: A ``MAT1`` entry is ``MID``, then ``E``, ``G``, ``NU``, ``RHO``, the thermal
#: expansion coefficient, the reference temperature, the structural damping and
#: the three allowables, then the ``MCSID`` frame.
MPT_MATERIAL_RECORDS: dict[tuple[int, int, int], int] = {
    (103, 1, 77): 12,  # MAT1
}

#: The words of a ``MAT1`` entry :class:`~openfemlab.core.neutral.NeutralMaterial`
#: has a home for; the rest are thermal and allowable data no module consumes.
_MAT1_MODULUS_WORD = 1
_MAT1_POISSON_WORD = 3
_MAT1_DENSITY_WORD = 4

#: ``GEOM1`` record key → ``(words per GRID entry, CP word, CD word)``, the
#: three dialects of the ``GRID`` card.  Phase 2 reads these only to *refuse* a
#: model whose grids are not in the basic frame; Phase 3 reads the coordinates
#: through the same table.  The 11-word form writes the location in double
#: precision, which moves ``CD`` — the reason this is a table and not a
#: constant — and which Phase 3 refuses rather than read two words as one.
GEOM1_GRID_RECORDS: dict[tuple[int, int, int], tuple[int, int, int]] = {
    (4501, 45, 1): (8, 1, 5),
    (4501, 45, 810001): (8, 1, 5),
    (4501, 45, 1120001): (11, 1, 8),
}

#: Words of the single-precision ``GRID`` entry — ``ID, CP, X1, X2, X3, CD,
#: PS, SEID`` — and the word its location starts at.
_GRID_BASIC_ENTRY_WORDS = 8
_GRID_LOCATION_WORD = 2

#: Words in the ``IDENT`` record that opens every result subtable.
_IDENT_WORDS = 146

#: Words per entry of the ``LAMA`` eigenvalue table: mode number, extraction
#: order, eigenvalue, radians, cycles, generalized mass and stiffness.
_LAMA_ENTRY_WORDS = 7

#: Words per entry of a real eigenvector: the coded grid id, the grid type and
#: the six components.
_REAL_EIGENVECTOR_WORDS = 8

#: ``IDENT`` analysis code of a real normal-modes run, and of the complex
#: eigenvalue runs this subset refuses.
_REAL_MODES_ANALYSIS_CODE = 2
_COMPLEX_MODES_ANALYSIS_CODE = 9

#: ``IDENT`` table code of an eigenvector, and format code of a real one.
_EIGENVECTOR_TABLE_CODE = 7
_REAL_FORMAT_CODE = 1

#: Grid type of a geometric grid point; scalar and extra points differ.
_GRID_POINT_TYPE = 1

#: Sort codes that mean SORT2 (one record per point, all times inside).
_SORT2_CODES = frozenset({2, 3, 6})

#: The six components of a real eigenvector entry, in file order.
_MODE_DOFS = (DofType.UX, DofType.UY, DofType.UZ, DofType.RX, DofType.RY, DofType.RZ)


@dataclass(frozen=True)
class _Geom1Context:
    """Coordinate systems and ``GRID`` data read from ``GEOM1``."""

    systems: dict[int, RectangularSystem]
    grid_cp: dict[int, int]
    grid_cd: dict[int, int]
    grids: dict[int, tuple[float, float, float]]
    skipped: int


def read_op2(source: str | PathLike[str] | BinaryIO) -> NeutralModel:
    """Read the geometry of an OP2 file into a ``NeutralModel`` — Phase 3.

    Reads ``GRID`` from ``GEOM1``, the connectivity records of
    :data:`GEOM2_ELEMENT_LAYOUTS` from ``GEOM2`` and the material records of
    :data:`MPT_MATERIAL_RECORDS` from ``MPT``, producing the model
    :func:`~openfemlab.io.nastran.read_bdf` produces from the bulk data the run
    started from — same labels, same blocks, same materials.

    Records outside that subset are stepped over and counted per block in
    ``meta["skipped_records"]``, the partial-import policy of MS-9.3.  The one
    record that is refused instead of skipped is a ``GEOM2`` record whose card
    *is* in :data:`GEOM2_ELEMENT_RECORDS` but whose word layout this increment
    does not unpack: dropping it would return a model that looks complete and
    has lost its elements.  ``EPT`` is not read at all yet, so a rod's ``PROD``
    survives only as the property id on the element — which is also all the
    ASCII reader keeps of it.

    Parameters
    ----------
    source:
        Path to an OP2 file, or an open binary stream positioned at its start.

    Raises
    ------
    ~openfemlab.io.FormatError
        If the file is not an OP2 or its framing is inconsistent; if it holds
        no ``GEOM1`` table, or no ``GRID`` inside it; if a record length is not
        a whole number of the entries its layout declares; if a ``GRID`` or
        element id is defined twice; if connectivity names a grid the file does
        not define; or if any ``GRID`` names a non-basic ``CP``/``CD`` frame,
        which Phase 4 will transform and this phase must not silently ignore.
    """

    op2_format, blocks = read_op2_blocks(source, keep=set(OP2_GEOMETRY_TABLES))
    source_name = _source_name(source)
    names = [block.name for block in blocks]
    if "GEOM1" not in names:
        raise FormatError(
            f"{_where(source_name)} has no GEOM1 table, so it holds no geometry; its "
            f"data blocks are {', '.join(names) or '(none)'}"
        )

    # Grids and coordinate systems first: a dialect this phase cannot unpack
    # has to be named as such, rather than reported as the unreadable record
    # length it also is.
    geom1, geom1_skipped = _read_geom1(blocks, op2_format, source_name)
    grids = geom1.grids
    if not grids:
        raise FormatError(
            f"{_where(source_name)}: the GEOM1 table holds no GRID records, so the "
            "model has no nodes"
        )
    connectivity, property_ids, element_ids, geom2_skipped = _read_elements(
        blocks, op2_format, source_name
    )
    materials, mpt_skipped = _read_materials(blocks, op2_format, source_name)

    referenced = {grid for rows in connectivity.values() for row in rows for grid in row}
    unknown = sorted(referenced - grids.keys())
    if unknown:
        listed = ", ".join(str(grid) for grid in unknown)
        raise FormatError(
            f"{_where(source_name)}: GEOM2 connectivity references GRID ids the GEOM1 "
            f"table does not define: {listed}"
        )

    elements = {
        element_type: np.asarray(connectivity[element_type], dtype=np.int64)
        for element_type in _BLOCK_ORDER
        if connectivity.get(element_type)
    }
    skipped = {
        name: count
        for name, count in (
            ("GEOM1", geom1_skipped),
            ("GEOM2", geom2_skipped),
            # The property tables are the remaining Phase 3 increment, so every
            # record of an EPT block is a record this reader did not read.
            ("EPT", sum(_countable_records(block) for block in blocks if block.name == "EPT")),
            ("MPT", mpt_skipped),
        )
        if count
    }

    meta: dict[str, object] = {
        "format": "nastran-op2",
        "tables": tuple(names),
        "word_size": op2_format.word_size,
        "byte_order": op2_format.byte_order,
        "element_ids": {
            element_type.value: element_ids[element_type] for element_type in elements
        },
        "skipped_records": skipped,
    }
    if op2_format.version:
        meta["solver_version"] = op2_format.version
    if source_name is not None:
        meta["source"] = source_name

    return NeutralModel(
        nodes=np.asarray(list(grids.values()), dtype=np.float64).reshape((-1, 3)),
        node_ids=np.fromiter(grids, dtype=np.int64, count=len(grids)),
        elements=elements,
        element_property_ids={
            element_type: np.asarray(property_ids[element_type], dtype=np.int64)
            for element_type in elements
        },
        materials=materials,
        meta=meta,
    )


def read_op2_modes(source: str | PathLike[str] | BinaryIO) -> ModalResult:
    """Read the normal modes of an OP2 file into a ``ModalResult`` — Phase 2.

    Pairs the ``LAMA`` eigenvalue table with the eigenvectors of the first
    ``OUG`` block the file carries (``BOUGV1`` first, since it is written in
    the basic frame) and returns a
    :class:`~openfemlab.core.results.ModalResult` whose ``DofMap`` carries the
    file's grid labels, so the modes align against a test set without a
    separate node mapping.  Modes come back ordered by mode number, with the
    frequencies of the ``LAMA`` table and the generalized masses in ``meta``.

    Parameters
    ----------
    source:
        Path to an OP2 file, or an open binary stream positioned at its start.

    Raises
    ------
    ~openfemlab.io.FormatError
        If the file is not an OP2 or its framing is inconsistent; if it holds
        no eigenvalue or eigenvector table; if the output is anything other
        than real normal modes in SORT1 at grid points; or if any ``GRID`` in
        the file names a non-basic ``CP``/``CD`` frame, which Phase 4 will
        transform and this phase must not silently ignore.
    """

    wanted = {*OP2_MODE_TABLES, "GEOM1"}
    op2_format, blocks = read_op2_blocks(source, keep=wanted)
    source_name = _source_name(source)
    names = [block.name for block in blocks]

    eigenvalue_table = _first_block(blocks, ("LAMA",))
    if eigenvalue_table is None:
        raise FormatError(
            f"{_where(source_name)} has no LAMA eigenvalue table, so it holds no normal "
            f"modes; its data blocks are {', '.join(names) or '(none)'}"
        )
    displacements = _first_block(blocks, OP2_MODE_TABLES[1:])
    if displacements is None:
        raise FormatError(
            f"{_where(source_name)} has a LAMA table but none of the eigenvector tables "
            f"{', '.join(OP2_MODE_TABLES[1:])}; its data blocks are {', '.join(names)}"
        )

    geom1 = _read_geom1(blocks, op2_format, source_name)[0]

    table = _read_lama(eigenvalue_table, op2_format, source_name)
    grids, shapes_by_mode, subcases = _read_eigenvectors(
        displacements, op2_format, source_name, geom1
    )
    if len(subcases) > 1:
        listed = ", ".join(str(subcase) for subcase in sorted(subcases))
        raise FormatError(
            f"{_where(source_name)} holds eigenvectors of several subcases ({listed}); "
            "reading more than one modal subcase from a file is outside the MS-9.6 subset"
        )

    mode_numbers = sorted(shapes_by_mode)
    missing = [number for number in mode_numbers if number not in table]
    if missing:
        listed = ", ".join(str(number) for number in missing)
        raise FormatError(
            f"{_where(source_name)}: {displacements.name} holds modes {listed} that the "
            "LAMA eigenvalue table does not, so their frequencies are unknown"
        )

    frequencies = np.array(
        [table[number].frequency_hz for number in mode_numbers], dtype=np.float64
    )
    generalized_masses = np.array(
        [table[number].generalized_mass for number in mode_numbers], dtype=np.float64
    )
    shapes = np.column_stack([shapes_by_mode[number] for number in mode_numbers])
    dof_map = DofMap.regular(grids, _MODE_DOFS)

    meta: dict[str, object] = {
        "format": "nastran-op2",
        "tables": tuple(names),
        "eigenvector_table": displacements.name,
        "word_size": op2_format.word_size,
        "byte_order": op2_format.byte_order,
        "mode_numbers": tuple(mode_numbers),
        "generalized_masses": generalized_masses.tolist(),
        "generalized_stiffnesses": [
            table[number].generalized_stiffness for number in mode_numbers
        ],
    }
    if op2_format.version:
        meta["solver_version"] = op2_format.version
    if subcases:
        meta["subcase"] = int(next(iter(subcases)))
    if source_name is not None:
        meta["source"] = source_name

    normalized = bool(np.allclose(generalized_masses, 1.0, rtol=0.0, atol=1e-6))
    try:
        return ModalResult(
            frequencies=frequencies,
            shapes=shapes,
            dof_map=dof_map,
            meta=meta,
            normalization="mass" if normalized else "none",
        )
    except ValueError as exc:  # pragma: no cover - guarded by the checks above
        raise FormatError(f"{_where(source_name)} holds an inconsistent mode set: {exc}") from exc


def list_op2_tables(source: str | PathLike[str] | BinaryIO) -> list[str]:
    """List the data blocks an OP2 file contains, in file order — Phase 1.

    The diagnostic the framing layer delivers before any engineering data is
    parsed: it answers "does this file even contain modes?", which is the
    question a user hits first when a run wrote the wrong ``PARAM,POST``.  No
    record contents are read, so a block this module knows nothing about is
    named all the same.

    Raises
    ------
    ~openfemlab.io.FormatError
        If the file is not an OP2 or its record framing is inconsistent.
    """

    _format, blocks = read_op2_blocks(source)
    return [block.name for block in blocks]


# ---------------------------------------------------------------- internals


def _source_name(source: str | PathLike[str] | BinaryIO) -> str | None:
    if isinstance(source, (str, PathLike)):
        return str(Path(source))
    name = getattr(source, "name", None)
    return str(name) if name is not None else None


def _where(source_name: str | None) -> str:
    return f"OP2 file {source_name}" if source_name else "OP2 stream"


def _first_block(blocks: list[OP2Block], names: tuple[str, ...]) -> OP2Block | None:
    """The file's first block named by ``names``, preferring the earlier name."""

    for name in names:
        for block in blocks:
            if block.name == name:
                return block
    return None


def _countable_records(block: OP2Block) -> int:
    """Records of a geometry block that carry a card, i.e. all but the name."""

    return max(len(block.records) - 1, 0)


def _geometry_records(
    block: OP2Block, op2_format: OP2Format
) -> Iterator[tuple[tuple[int, int, int], np.ndarray, np.ndarray]]:
    """Yield ``(key, integer words, float words)`` per record of a geometry block.

    Records in a geometry block are addressed by the three-integer key they
    open with rather than by their position, and their entries mix integers and
    reals word by word, so both readings of the same body are handed out and
    each field is taken from the one it is written in.  The block's leading
    subtable-name record carries no key and is stepped over.
    """

    for record in block.records[1:]:
        integers = op2_format.ints(record)
        if integers.size < 3:
            continue
        key = (int(integers[0]), int(integers[1]), int(integers[2]))
        yield key, integers[3:], op2_format.floats(record)[3:]


def _entries(
    key: tuple[int, int, int],
    block_name: str,
    integers: np.ndarray,
    reals: np.ndarray,
    entry_words: int,
    source_name: str | None,
) -> tuple[np.ndarray, np.ndarray]:
    """The record body reshaped to one row per entry, or a named refusal.

    MS-9.6: record keys are stable across dialects and record *contents* are
    not, so a body that is not a whole number of entries has to name the block
    and the key rather than be unpacked past the end of an entry.
    """

    if integers.size % entry_words:
        raise FormatError(
            f"{_where(source_name)}: {block_name} record {key} holds {integers.size} "
            f"words, which is not a multiple of the {entry_words}-word entry its "
            "layout declares"
        )
    return integers.reshape(-1, entry_words), reals.reshape(-1, entry_words)


def _read_geom1(
    blocks: list[OP2Block], op2_format: OP2Format, source_name: str | None
) -> tuple[_Geom1Context, int]:
    """Read ``CORD2R`` and ``GRID`` records, returning basic-frame coordinates."""

    raw_systems: dict[int, RectangularSystem] = {}
    skipped = 0
    grid_rows: list[tuple[int, int, int, np.ndarray]] = []

    for block in blocks:
        if block.name != "GEOM1":
            continue
        for key, integers, reals in _geometry_records(block, op2_format):
            if key == GEOM1_CORD2R_RECORD:
                raw_systems.update(
                    read_cord2r_systems(integers, reals, source_name=source_name)
                )
                continue
            layout = GEOM1_GRID_RECORDS.get(key)
            if layout is None:
                skipped += 1
                continue
            entry_words, cp_word, cd_word = layout
            if entry_words != _GRID_BASIC_ENTRY_WORDS:
                raise FormatError(
                    f"{_where(source_name)}: GEOM1 record {key} writes the GRID location "
                    f"in double precision, {entry_words} words to the entry; reading "
                    "that dialect is outside the MS-9.6 Phase 3 subset"
                )
            labels, coordinates = _entries(
                key, "GEOM1", integers, reals, entry_words, source_name
            )
            for row in range(labels.shape[0]):
                label = int(labels[row, 0])
                cp = int(labels[row, cp_word])
                cd = int(labels[row, cd_word])
                location = coordinates[row, _GRID_LOCATION_WORD : _GRID_LOCATION_WORD + 3]
                grid_rows.append((label, cp, cd, np.asarray(location, dtype=float)))

    systems = resolve_rectangular_systems(raw_systems)
    if grid_rows:
        frames = np.array([[cp, cd] for _label, cp, cd, _loc in grid_rows], dtype=int)
        require_defined_frames(frames, raw_systems, source_name=source_name)

    grids: dict[int, tuple[float, float, float]] = {}
    grid_cp: dict[int, int] = {}
    grid_cd: dict[int, int] = {}
    for label, cp, cd, location in grid_rows:
        if label in grids:
            raise FormatError(f"{_where(source_name)}: duplicate GRID id {label}")
        grid_cp[label] = cp
        grid_cd[label] = cd
        basic = transform_point_to_basic(location, systems[cp])
        grids[label] = (float(basic[0]), float(basic[1]), float(basic[2]))

    context = _Geom1Context(
        systems=systems,
        grid_cp=grid_cp,
        grid_cd=grid_cd,
        grids=grids,
        skipped=skipped,
    )
    return context, skipped


def _read_elements(
    blocks: list[OP2Block], op2_format: OP2Format, source_name: str | None
) -> tuple[
    dict[ElementType, list[tuple[int, ...]]],
    dict[ElementType, list[int]],
    dict[ElementType, list[int]],
    int,
]:
    """The ``GEOM2`` connectivity, property ids and element ids, per block."""

    connectivity: dict[ElementType, list[tuple[int, ...]]] = {}
    property_ids: dict[ElementType, list[int]] = {}
    element_ids: dict[ElementType, list[int]] = {}
    defined: dict[int, ElementType] = {}
    skipped = 0

    for block in blocks:
        if block.name != "GEOM2":
            continue
        for key, integers, reals in _geometry_records(block, op2_format):
            layout = GEOM2_ELEMENT_LAYOUTS.get(key)
            if layout is None:
                element_type = GEOM2_ELEMENT_RECORDS.get(key)
                if element_type is not None:
                    raise FormatError(
                        f"{_where(source_name)}: GEOM2 record {key} carries "
                        f"{element_type.value} elements, whose word layout MS-9.6 Phase 3 "
                        "does not unpack yet; importing the file without them would hide "
                        "the elements rather than report them"
                    )
                skipped += 1
                continue
            element_type = GEOM2_ELEMENT_RECORDS[key]
            entry_words, grid_words = layout
            rows, _ = _entries(key, "GEOM2", integers, reals, entry_words, source_name)
            for row in range(rows.shape[0]):
                element_id = int(rows[row, 0])
                previous = defined.get(element_id)
                if previous is not None:
                    raise FormatError(
                        f"{_where(source_name)}: duplicate element id {element_id}, "
                        f"already defined as a {previous.value}"
                    )
                defined[element_id] = element_type
                connectivity.setdefault(element_type, []).append(
                    tuple(int(rows[row, word]) for word in grid_words)
                )
                property_ids.setdefault(element_type, []).append(int(rows[row, 1]))
                element_ids.setdefault(element_type, []).append(element_id)
    return connectivity, property_ids, element_ids, skipped


def _read_materials(
    blocks: list[OP2Block], op2_format: OP2Format, source_name: str | None
) -> tuple[dict[int, NeutralMaterial], int]:
    """The ``MPT`` materials by id, and the records of that block left unread."""

    materials: dict[int, NeutralMaterial] = {}
    skipped = 0
    for block in blocks:
        if block.name != "MPT":
            continue
        for key, integers, reals in _geometry_records(block, op2_format):
            entry_words = MPT_MATERIAL_RECORDS.get(key)
            if entry_words is None:
                skipped += 1
                continue
            labels, values = _entries(key, "MPT", integers, reals, entry_words, source_name)
            for row in range(labels.shape[0]):
                material_id = int(labels[row, 0])
                if material_id in materials:
                    raise FormatError(
                        f"{_where(source_name)}: duplicate MAT1 id {material_id}"
                    )
                # The name is left empty, as the ASCII reader leaves it, so that
                # a model and the OP2 of its run compare equal card for card.
                materials[material_id] = NeutralMaterial(
                    id=material_id,
                    E=float(values[row, _MAT1_MODULUS_WORD]),
                    nu=float(values[row, _MAT1_POISSON_WORD]),
                    rho=float(values[row, _MAT1_DENSITY_WORD]),
                )
    return materials, skipped


def _iter_subtables(
    block: OP2Block, op2_format: OP2Format
) -> Iterator[tuple[bytes, bytes]]:
    """Yield the ``(IDENT, data)`` record pairs of a result block.

    A result block interleaves a 146-word ``IDENT`` describing one case with
    the data record holding its values, ahead of which sits the subtable name
    record; pairing on the ``IDENT`` length skips that one without having to
    know what it says.
    """

    ident: bytes | None = None
    for record in block.records:
        if op2_format.nwords(record) == _IDENT_WORDS:
            ident = record
        elif ident is not None:
            yield ident, record
            ident = None


class _Eigenvalue(NamedTuple):
    """One row of the ``LAMA`` table, in the order the record writes it."""

    extraction_order: int
    eigenvalue: float
    frequency_hz: float
    generalized_mass: float
    generalized_stiffness: float


def _read_lama(
    block: OP2Block, op2_format: OP2Format, source_name: str | None
) -> dict[int, _Eigenvalue]:
    """The ``LAMA`` table as ``mode number → row``."""

    table: dict[int, _Eigenvalue] = {}
    for _ident, data in _iter_subtables(block, op2_format):
        nwords = op2_format.nwords(data)
        if nwords % _LAMA_ENTRY_WORDS:
            raise FormatError(
                f"{_where(source_name)}: a LAMA record holds {nwords} words, which is not "
                f"a multiple of the {_LAMA_ENTRY_WORDS}-word eigenvalue entry"
            )
        integers = op2_format.ints(data).reshape(-1, _LAMA_ENTRY_WORDS)
        reals = op2_format.floats(data).reshape(-1, _LAMA_ENTRY_WORDS)
        for row in range(integers.shape[0]):
            table[int(integers[row, 0])] = _Eigenvalue(
                extraction_order=int(integers[row, 1]),
                eigenvalue=float(reals[row, 2]),
                frequency_hz=float(reals[row, 4]),
                generalized_mass=float(reals[row, 5]),
                generalized_stiffness=float(reals[row, 6]),
            )
    if not table:
        raise FormatError(f"{_where(source_name)}: the LAMA table holds no eigenvalues")
    return table


def _read_eigenvectors(
    block: OP2Block,
    op2_format: OP2Format,
    source_name: str | None,
    geom1: _Geom1Context,
) -> tuple[list[int], dict[int, np.ndarray], set[int]]:
    """The grid labels, one flattened shape per mode, and the subcases seen."""

    grids: list[int] | None = None
    shapes: dict[int, np.ndarray] = {}
    subcases: set[int] = set()

    for ident, data in _iter_subtables(block, op2_format):
        header = op2_format.ints(ident)
        mode, device_code, num_wide = _check_ident(header, block.name, source_name)
        subcases.add(int(header[3]))

        nwords = op2_format.nwords(data)
        if nwords % num_wide:
            raise FormatError(
                f"{_where(source_name)}: a {block.name} record for mode {mode} holds "
                f"{nwords} words, which is not a multiple of the {num_wide} words per "
                "entry its IDENT declares"
            )
        integers = op2_format.ints(data).reshape(-1, num_wide)
        reals = op2_format.floats(data).reshape(-1, num_wide)

        grid_types = set(int(value) for value in integers[:, 1])
        if grid_types - {_GRID_POINT_TYPE}:
            other = ", ".join(str(value) for value in sorted(grid_types - {_GRID_POINT_TYPE}))
            raise FormatError(
                f"{_where(source_name)}: {block.name} mode {mode} carries points of grid "
                f"type {other}; scalar and extra points have no six-component shape and "
                "are outside the MS-9.6 subset"
            )
        coded = integers[:, 0]
        if np.any((coded - device_code) % 10):
            raise FormatError(
                f"{_where(source_name)}: {block.name} mode {mode} has entries whose grid "
                f"id is not written as grid * 10 + {device_code}"
            )
        labels = [int(value) for value in (coded - device_code) // 10]
        if grids is None:
            grids = labels
        elif labels != grids:
            raise FormatError(
                f"{_where(source_name)}: {block.name} mode {mode} is written on a "
                "different set of grids than the modes before it"
            )
        if mode in shapes:
            raise FormatError(
                f"{_where(source_name)}: {block.name} holds mode {mode} more than once"
            )
        raw_vectors = np.asarray(reals[:, 2:8], dtype=np.float64)
        transformed = []
        for row, grid_id in enumerate(labels):
            cd = geom1.grid_cd.get(grid_id, 0)
            transformed.append(
                transform_six_dof_to_basic(raw_vectors[row], geom1.systems[cd])
            )
        shapes[mode] = np.vstack(transformed).reshape(-1)

    if grids is None or not shapes:
        raise FormatError(
            f"{_where(source_name)}: the {block.name} table holds no eigenvectors"
        )
    return grids, shapes, subcases


def _check_ident(
    header: np.ndarray, table_name: str, source_name: str | None
) -> tuple[int, int, int]:
    """Validate one result ``IDENT`` and return ``(mode, device, num_wide)``."""

    approach_code = int(header[0])
    analysis_code, device_code = divmod(approach_code, 10)
    table_code = int(header[1]) % 1000
    sort_code = int(header[1]) // 1000
    mode = int(header[4])
    format_code = int(header[8])
    num_wide = int(header[9])

    if analysis_code == _COMPLEX_MODES_ANALYSIS_CODE:
        raise FormatError(
            f"{_where(source_name)}: {table_name} holds complex eigenvectors (analysis "
            f"code {_COMPLEX_MODES_ANALYSIS_CODE}); MS-9.6 Phase 2 reads real normal "
            f"modes (analysis code {_REAL_MODES_ANALYSIS_CODE}) only"
        )
    if analysis_code != _REAL_MODES_ANALYSIS_CODE:
        raise FormatError(
            f"{_where(source_name)}: {table_name} was written by analysis code "
            f"{analysis_code}, not the normal-modes code {_REAL_MODES_ANALYSIS_CODE}"
        )
    if sort_code in _SORT2_CODES:
        raise FormatError(
            f"{_where(source_name)}: {table_name} is written in SORT2 (sort code "
            f"{sort_code}), which orders the file by point rather than by mode; MS-9.6 "
            "Phase 2 reads SORT1 only"
        )
    if table_code != _EIGENVECTOR_TABLE_CODE:
        raise FormatError(
            f"{_where(source_name)}: {table_name} carries table code {table_code}, not "
            f"the eigenvector code {_EIGENVECTOR_TABLE_CODE}"
        )
    if format_code != _REAL_FORMAT_CODE:
        raise FormatError(
            f"{_where(source_name)}: {table_name} mode {mode} is written with format code "
            f"{format_code} (real/imaginary or magnitude/phase), not the real format code "
            f"{_REAL_FORMAT_CODE}"
        )
    if num_wide != _REAL_EIGENVECTOR_WORDS:
        raise FormatError(
            f"{_where(source_name)}: {table_name} mode {mode} declares {num_wide} words "
            f"per entry; a real eigenvector at a grid point is {_REAL_EIGENVECTOR_WORDS}"
        )
    return mode, device_code, num_wide
