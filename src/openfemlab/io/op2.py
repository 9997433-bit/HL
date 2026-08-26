"""Planned reader for the Nastran OP2 binary result file — **not implemented**.

OP2 is the binary companion of the ASCII bulk data :mod:`openfemlab.io.nastran`
reads: one file that can carry the analysed model *and* its normal-mode
solution, which is exactly the pair the correlation and updating modules need
from an industrial solver.  Reaching it means writing a binary parser, and a
binary parser without a test corpus is a liability, so this module is a
deliberately empty seam: it holds the format knowledge the spike established
(GAP-03 extension, MODULE_SPEC MS-9.6) and the API the reader will expose, and
every entry point raises :class:`NotImplementedError`.

Nothing here is re-exported from :mod:`openfemlab.io`.  A name in that
namespace advertises a working reader, so ``read_op2`` stays reachable only as
``openfemlab.io.op2.read_op2`` until it reads a file.

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

**Phase 1 — framing.**  The record layer only: word size and byte-order
detection, the key/continuation walk, block name and trailer, and a directory
of ``(name, offset)`` for the whole file.  This phase reads no engineering
data, which is what makes it cheap to test exhaustively — truncated records,
mismatched trailing byte counts, a 64-bit file, a byte-swapped file.  It also
delivers something useful on its own: ``list_op2_tables`` tells a user why
their file has no modes in it.

**Phase 2 — modes.**  ``LAMA`` and ``OUGV1`` into a ``ModalResult`` whose
``DofMap`` carries the file's grid labels, so an imported eigenvector aligns
against a test set through the existing MS-4 label matching.  Restricted to
real normal modes in SORT1: complex eigenvectors, SORT2 and random output all
raise rather than being guessed at.

**Phase 3 — geometry.**  ``GEOM1``/``GEOM2``/``EPT``/``MPT`` into a
``NeutralModel``, reusing the element and property vocabulary
:mod:`openfemlab.io.nastran` already established for the same cards in ASCII,
so a BDF and its OP2 import to equal models.  Unknown records are skipped and
counted in ``meta``, the partial-import policy of MS-9.3.

**Phase 4 — coordinate systems.**  ``CORD1R``/``CORD2R`` and the ``CP``/``CD``
fields, which Phases 2 and 3 must reject rather than ignore (see below).

Why this is not started yet
---------------------------
Three risks decide the shape of the work, and none of them is about the
parsing:

*No corpus.* Producing an OP2 needs a Nastran licence, so the test files
cannot be generated in CI the way UFF and BDF fixtures are.  The way out is a
test-only writer: emit the framing and record layouts documented above from a
known model, then assert the reader recovers it.  That validates every byte
layout this module claims and runs offline, but it validates them against *our
reading of the spec*, not against Nastran — so it must be paired with an
opt-in corpus test over real files (an environment variable pointing at a
directory, skipped when unset) before the reader may be called supported.

*Dialects.* The record keys are stable, the record *contents* are not.
``CQUAD4`` is the standing example: NX writes 14 words and MSC writes 15, under
the same key ``(2958, 51, 177)``, distinguishable only by dividing the record
length.  Every phase must therefore validate that a record length is a
multiple of the layout it assumes and name the block and key when it is not,
rather than reading past the end of an entry.

*Coordinate systems.* ``GRID`` carries a ``CP`` (definition) and ``CD``
(output) frame, and OP2 eigenvectors are written in ``CD``.  A model with any
non-zero ``CP``/``CD`` and no ``CORD`` transform would import with silently
wrong coordinates and shapes, so Phases 2 and 3 must raise on it — the same
line :func:`~openfemlab.io.nastran.read_bdf` already draws for ``GRID`` and
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
pyNastran 1.4.1 (``op2/tables/geom/``) and pyYeti's ``nastran.op2`` format
notes; both are independent implementations of the MSC DMAP documentation.
"""

from __future__ import annotations

from os import PathLike
from typing import BinaryIO

from openfemlab.core.neutral import ElementType, NeutralModel
from openfemlab.core.results import ModalResult

__all__ = [
    "GEOM2_ELEMENT_RECORDS",
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

_ROADMAP = (
    "reading it is planned as the GAP-03 extension (docs/MODULE_SPEC.md MS-9.6); "
    "the format subset and the phases are documented in openfemlab.io.op2"
)

_ALTERNATIVES = (
    "export the model as bulk data and read it with openfemlab.io.read_bdf, or "
    "the modes as UFF dataset 55 and read them with openfemlab.io.read_uff_modes"
)


def read_op2(source: str | PathLike[str] | BinaryIO) -> NeutralModel:
    """Read the geometry of an OP2 file into a ``NeutralModel`` — Phase 3.

    Will read ``GRID`` from ``GEOM1``, the connectivity of
    :data:`GEOM2_ELEMENT_RECORDS` from ``GEOM2``, and the ``PSHELL``/``PSOLID``/
    ``PROD`` and ``MAT1`` tables from ``EPT`` and ``MPT``, producing the same
    model :func:`~openfemlab.io.nastran.read_bdf` produces from the bulk data
    the run started from.

    Raises
    ------
    NotImplementedError
        Always.
    """

    raise NotImplementedError(
        f"OP2 geometry import is not implemented: {_ROADMAP}. In the meantime, {_ALTERNATIVES}."
    )


def read_op2_modes(source: str | PathLike[str] | BinaryIO) -> ModalResult:
    """Read the normal modes of an OP2 file into a ``ModalResult`` — Phase 2.

    Will pair the ``LAMA`` eigenvalue table with the ``OUGV1`` eigenvectors and
    return a :class:`~openfemlab.core.results.ModalResult` whose ``DofMap``
    carries the file's grid labels, so the modes align against a test set
    without a separate node mapping.  Real normal modes in SORT1 only.

    Raises
    ------
    NotImplementedError
        Always.
    """

    raise NotImplementedError(
        f"OP2 mode import is not implemented: {_ROADMAP}. In the meantime, {_ALTERNATIVES}."
    )


def list_op2_tables(source: str | PathLike[str] | BinaryIO) -> list[str]:
    """List the data blocks an OP2 file contains, in file order — Phase 1.

    The diagnostic the framing layer delivers before any engineering data is
    parsed: it answers "does this file even contain modes?", which is the
    question a user hits first when a run wrote the wrong ``PARAM,POST``.

    Raises
    ------
    NotImplementedError
        Always.
    """

    raise NotImplementedError(
        f"OP2 reading is not implemented: {_ROADMAP}."
    )
