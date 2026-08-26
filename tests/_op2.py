"""Binary Nastran OP2 records for the test suite.

An OP2 cannot be produced without a Nastran licence, so the reader's fixtures
have to be written here — the plan MODULE_SPEC MS-9.6 records as the way out of
the corpus problem, and the binary sibling of :mod:`tests._uff58`.  This module
emits the framing and the record layouts :mod:`openfemlab.io.op2` documents:
Fortran ``[reclen, payload, reclen]`` records, key triplets and marker groups,
a named data block per table, the ``LAMA`` eigenvalue table and the ``OUGV1``
eigenvectors of a known model.

Everything a real writer varies is a parameter here, because the point of the
fixture is to exercise the variation: 4- and 8-byte words, either byte order,
``PARAM,POST,-1`` (with the date/version header) and ``-2`` (without), and the
``IDENT`` codes that say complex, SORT2 or scalar-point output so the reader
can be held to refusing them.

What it does *not* do is validate the layouts against Nastran.  The 32-bit
files it writes are read back correctly by pyNastran 1.4.1 — mode numbers,
eigenvalues, grid ids and shapes all round-trip through an independent
implementation, and the same holds for the 64-bit ones except ``LAMA``, whose
entry size pyNastran hard-codes at 4-byte words — but a second reading of the
same documentation is not the solver.  Only the opt-in corpus test over real
MSC and NX output can settle that, which is why the reader stays unexported
until it runs.
"""

from __future__ import annotations

import math
import struct
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

#: One word of a record: an integer, a real, or 4 characters per word.
Token = tuple[str, object]

#: The label record of a ``PARAM,POST,-1`` header, 28 characters / 7 words.
TAPE_ID_LABEL = "NASTRAN FORT TAPE ID CODE - "

#: Words in the ``IDENT`` record that opens a result subtable: 50 of codes and
#: case parameters, then title, subtitle and label at 128 characters each.
IDENT_WORDS = 146
IDENT_CODE_WORDS = 50

#: Words per ``LAMA`` entry and per real eigenvector entry.
LAMA_ENTRY_WORDS = 7
EIGENVECTOR_ENTRY_WORDS = 8

#: ``GEOM1`` record key of the ``GRID`` card and its word layout.
GRID_RECORD_KEY = (4501, 45, 1)


# ------------------------------------------------------------------- words


def integers(*values: int) -> list[Token]:
    """Integer words."""
    return [("i", int(value)) for value in values]


def reals(*values: float) -> list[Token]:
    """Floating-point words."""
    return [("f", float(value)) for value in values]


def characters(value: str, *, words: int) -> list[Token]:
    """``words`` words of text, blank-padded or truncated to fit."""
    return [("s", value.ljust(4 * words)[: 4 * words])]


# ------------------------------------------------------------------ blocks


@dataclass(frozen=True)
class DataBlock:
    """One named OP2 data block and the logical records inside it."""

    name: str
    records: tuple[Sequence[Token], ...] = ()
    trailer: tuple[int, ...] = (0, 0, 0, 0, 0, 0, 0)
    subtable_name: str | None = None


@dataclass(frozen=True)
class Grid:
    """A ``GRID`` card as ``GEOM1`` writes it."""

    id: int
    xyz: tuple[float, float, float] = (0.0, 0.0, 0.0)
    cp: int = 0
    cd: int = 0
    ps: int = 0
    seid: int = 0


@dataclass(frozen=True)
class Mode:
    """One normal mode: its number, frequency and shape at the grids."""

    number: int
    frequency_hz: float
    shape: Mapping[int, Sequence[float]] = field(default_factory=dict)
    generalized_mass: float = 1.0

    @property
    def eigenvalue(self) -> float:
        """``omega**2``, the eigenvalue ``LAMA`` and ``IDENT`` both carry."""
        return (2.0 * math.pi * self.frequency_hz) ** 2

    @property
    def radians(self) -> float:
        return 2.0 * math.pi * self.frequency_hz


def geom1_block(grids: Iterable[Grid], *, key: tuple[int, int, int] = GRID_RECORD_KEY) -> DataBlock:
    """``GEOM1`` holding one ``GRID`` record: ``(ID, CP, X, Y, Z, CD, PS, SEID)``."""

    record: list[Token] = list(integers(*key))
    for grid in grids:
        record += integers(grid.id, grid.cp)
        record += reals(*grid.xyz)
        record += integers(grid.cd, grid.ps, grid.seid)
    return DataBlock(name="GEOM1", records=(record,), subtable_name="GEOM1S")


def lama_block(modes: Sequence[Mode], *, name: str = "LAMA") -> DataBlock:
    """The eigenvalue table: one 7-word entry per mode."""

    entries: list[Token] = []
    for order, mode in enumerate(modes, start=1):
        entries += integers(mode.number, order)
        entries += reals(
            mode.eigenvalue,
            mode.radians,
            mode.frequency_hz,
            mode.generalized_mass,
            mode.eigenvalue * mode.generalized_mass,
        )
    ident = result_ident(
        analysis_code=2, table_code=2, mode=len(modes), num_wide=LAMA_ENTRY_WORDS
    )
    return DataBlock(name=name, records=(ident, entries), subtable_name=name)


def eigenvector_block(
    modes: Sequence[Mode],
    *,
    name: str = "OUGV1",
    device_code: int = 1,
    analysis_code: int = 2,
    table_code: int = 7,
    sort_code: int = 0,
    format_code: int = 1,
    num_wide: int = EIGENVECTOR_ENTRY_WORDS,
    grid_type: int = 1,
    subcase: int = 1,
) -> DataBlock:
    """Eigenvectors, one ``IDENT``/data pair per mode.

    The codes are arguments because the reader has to refuse most of their
    values: ``analysis_code=9`` is a complex eigenvector, ``sort_code=2`` is
    SORT2, ``format_code=2`` is real/imaginary, ``grid_type=2`` is a scalar
    point.
    """

    records: list[Sequence[Token]] = []
    for mode in modes:
        records.append(
            result_ident(
                analysis_code=analysis_code,
                device_code=device_code,
                table_code=table_code,
                sort_code=sort_code,
                subcase=subcase,
                mode=mode.number,
                eigenvalue=mode.eigenvalue,
                radians=mode.radians,
                format_code=format_code,
                num_wide=num_wide,
            )
        )
        data: list[Token] = []
        for grid, components in mode.shape.items():
            data += integers(grid * 10 + device_code, grid_type)
            data += reals(*components)
        records.append(data)
    return DataBlock(name=name, records=tuple(records), subtable_name="OUG1")


def result_ident(
    *,
    analysis_code: int = 2,
    device_code: int = 1,
    table_code: int = 7,
    sort_code: int = 0,
    subcase: int = 1,
    mode: int = 1,
    eigenvalue: float = 0.0,
    radians: float = 0.0,
    random_code: int = 0,
    format_code: int = 1,
    num_wide: int = EIGENVECTOR_ENTRY_WORDS,
    title: str = "OpenFEMLab test model",
    subtitle: str = "normal modes",
    label: str = "SUBCASE 1",
) -> list[Token]:
    """The 146-word record that opens a result subtable.

    Word 1 is ``device_code + 10 * analysis_code`` and word 2 the table code
    with the sort code above it; words 5 to 7 carry the mode number, its
    eigenvalue and its frequency in radians, word 9 the format code and word 10
    the words per entry.  The rest of the code block is zero, as it is for a
    normal-modes run, and the last 96 words are the three 128-character
    strings the case is labelled with.
    """

    words: list[Token] = []
    words += integers(device_code + 10 * analysis_code, sort_code * 1000 + table_code, 0, subcase)
    words += integers(mode)
    words += reals(eigenvalue, radians)
    words += integers(random_code, format_code, num_wide)
    words += integers(*([0] * (IDENT_CODE_WORDS - len(words))))
    words += characters(title, words=32)
    words += characters(subtitle, words=32)
    words += characters(label, words=32)
    return words


def modes_file(
    modes: Sequence[Mode],
    *,
    grids: Iterable[Grid] | None = None,
    eigenvector_table: str = "OUGV1",
    extra_blocks: Sequence[DataBlock] = (),
    **eigenvector_options: object,
) -> bytes:
    """A whole OP2 holding the modes of one model: ``GEOM1``, ``LAMA``, ``OUG``.

    ``eigenvector_options`` are passed to :func:`eigenvector_block`, and any
    keyword :func:`write_op2` accepts (``word_size``, ``byte_order``, ``post``)
    is split out of them first.
    """

    file_options = {
        key: eigenvector_options.pop(key)
        for key in ("word_size", "byte_order", "post", "version", "date")
        if key in eigenvector_options
    }
    blocks: list[DataBlock] = []
    if grids is not None:
        blocks.append(geom1_block(grids))
    blocks.append(lama_block(modes))
    blocks.append(
        eigenvector_block(modes, name=eigenvector_table, **eigenvector_options)  # type: ignore[arg-type]
    )
    blocks.extend(extra_blocks)
    return write_op2(blocks, **file_options)  # type: ignore[arg-type]


# ------------------------------------------------------------------ writing


def write_op2(
    blocks: Iterable[DataBlock],
    *,
    word_size: int = 4,
    byte_order: str = "<",
    post: int = -1,
    version: str = "NX12.0",
    date: tuple[int, int, int] = (8, 26, 26),
) -> bytes:
    """Serialize data blocks as an OP2 file.

    Parameters
    ----------
    word_size:
        4 for a 32-bit file, 8 for a 64-bit one.  Only the words widen: the
        Fortran byte counts stay 32-bit, as they do in a real 64-bit OP2.
    byte_order:
        ``"<"`` or ``">"``.
    post:
        ``-1`` writes the date and version header, ``-2`` writes none.
    """

    if word_size not in (4, 8):
        raise ValueError(f"an OP2 word is 4 or 8 bytes, not {word_size}")
    if byte_order not in ("<", ">"):
        raise ValueError(f"byte order is '<' or '>', not {byte_order!r}")

    out = bytearray()
    if post == -1:
        out += _marker(3, word_size, byte_order)
        out += _block(integers(*date), word_size, byte_order)
        out += _marker(7, word_size, byte_order)
        out += _block(characters(TAPE_ID_LABEL, words=7), word_size, byte_order)
        out += _keyed(characters(version, words=2), word_size, byte_order)
        out += _marker(-1, word_size, byte_order)
        out += _marker(0, word_size, byte_order)
    elif post != -2:
        raise ValueError(f"an OP2 is written by PARAM,POST,-1 or -2, not {post}")

    for block in blocks:
        out += _write_block(block, word_size, byte_order, date)
    out += _marker(0, word_size, byte_order)  # the trailing marker that ends a file
    return bytes(out)


def _write_block(
    block: DataBlock, word_size: int, byte_order: str, date: tuple[int, int, int]
) -> bytes:
    out = bytearray()
    out += _keyed(characters(block.name, words=2), word_size, byte_order)
    out += _marker(-1, word_size, byte_order)
    out += _keyed(integers(*block.trailer), word_size, byte_order)

    # The subtable name is followed by the run date in a 32-bit file; 64-bit
    # writers put the name on its own, which is what pyNastran expects to find
    # there and what this writer therefore emits.
    subtable = characters(block.subtable_name or block.name, words=2)
    if word_size == 4:
        subtable += integers(*date, 0, 1)
    records: list[Sequence[Token]] = [subtable, *block.records]

    index = -2
    for record in records:
        out += _marker_group(index, word_size, byte_order)
        out += _keyed(record, word_size, byte_order)
        index -= 1
    out += _marker_group(index, word_size, byte_order)
    out += _marker(0, word_size, byte_order)
    return bytes(out)


def _marker_group(index: int, word_size: int, byte_order: str) -> bytes:
    return b"".join(
        _marker(value, word_size, byte_order) for value in (index, 1, 0)
    )


def _marker(value: int, word_size: int, byte_order: str) -> bytes:
    return _block(integers(value), word_size, byte_order)


def _keyed(words: Sequence[Token], word_size: int, byte_order: str) -> bytes:
    """A key giving the word count, then the payload it announces."""

    payload = pack_words(words, word_size, byte_order)
    key = len(payload) // word_size
    return _marker(key, word_size, byte_order) + _raw(payload, byte_order)


def _block(words: Sequence[Token], word_size: int, byte_order: str) -> bytes:
    return _raw(pack_words(words, word_size, byte_order), byte_order)


def _raw(payload: bytes, byte_order: str) -> bytes:
    """One Fortran unformatted record: ``[nbytes, payload, nbytes]``."""

    count = struct.pack(f"{byte_order}i", len(payload))
    return count + payload + count


def pack_words(words: Sequence[Token], word_size: int, byte_order: str) -> bytes:
    """Pack tokens into words.

    A 64-bit OP2 stores text *interlaced*, one 4-character group per 8-byte
    word with the upper half blank, which is what NX writes and what the
    reader has to see through.
    """

    integer_format = f"{byte_order}{'i' if word_size == 4 else 'q'}"
    real_format = f"{byte_order}{'f' if word_size == 4 else 'd'}"
    out = bytearray()
    for kind, value in words:
        if kind == "i":
            out += struct.pack(integer_format, int(value))  # type: ignore[arg-type]
        elif kind == "f":
            out += struct.pack(real_format, float(value))  # type: ignore[arg-type]
        elif kind == "s":
            text = str(value)
            if len(text) % 4:
                text = text.ljust(4 * (len(text) // 4 + 1))
            encoded = text.encode("ascii")
            if word_size == 4:
                out += encoded
            else:
                out += b"".join(
                    encoded[4 * i : 4 * i + 4] + b"    " for i in range(len(encoded) // 4)
                )
        else:  # pragma: no cover - a typo in a fixture, not a tested path
            raise ValueError(f"unknown word kind {kind!r}")
    return bytes(out)
