"""Fortran record framing for the Nastran OP2 — Phase 1 of MODULE_SPEC MS-9.6.

This is the layer below every engineering meaning: it turns the byte stream
into a list of named data blocks and their logical records, and it reads no
field it does not need to do that.  :mod:`openfemlab.io.op2` sits on top and
interprets the records; keeping the two apart is what makes the framing
testable on its own, which is the whole point of phasing the reader by risk.

The three nested layers, from the disk up:

*Physical records.*  ``[nbytes, payload, nbytes]`` with a **32-bit** byte count
on both ends — 32-bit even in a 64-bit OP2, where only the payload words widen
to 8 bytes.  The opening count is therefore the first four bytes of the file
and must decode to 4 or 8; that single value settles both the word size and the
byte order, since no other combination of the two decodes it.

*Logical records.*  A one-word record whose value is a positive word count is a
*key*: the record that follows it holds exactly that many words.  Further
``[key, payload]`` pairs continue the same logical record, and a non-positive
key ends it.  Blocks separate their records with the marker group ``[-n, 1,
0]``, ``n`` counting down from 2; the block ends when a lone ``0`` follows the
last group.

*Data blocks.*  A block opens with a key of 2 and its 8-character name, then
``[-1]`` and a trailer record, then its records.  Because the name comes first
and every record can be stepped over by its keys, a reader can name a block it
does not understand and skip it structurally — which is what lets this module
list ``OES1X`` without knowing a thing about element stresses.

Word layouts inside the records are the callers' business, with one exception
that belongs here: 64-bit files store an 8-character string in 16 bytes, and NX
writes it *interlaced* (``ABCD    EFGH    ``) where MSC writes it contiguous.
:meth:`OP2Format.text` reads both.
"""

from __future__ import annotations

from collections.abc import Container, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from io import BytesIO
from os import PathLike
from pathlib import Path
from typing import BinaryIO

import numpy as np

from ._common import FormatError

__all__ = [
    "OP2Block",
    "OP2Format",
    "read_op2_blocks",
]

#: Byte count of the first physical record → word size of the whole file.
_WORD_SIZES = (4, 8)

#: Opening marker of a ``PARAM,POST,-1`` file, the one that carries a header.
_HEADER_MARKER = 3

#: Opening marker of a ``PARAM,POST,-2`` file: the key of the first block name.
_NO_HEADER_MARKER = 2

#: Word count of the ``NASTRAN FORT TAPE ID CODE - `` label record.
_LABEL_WORDS = 7

#: A block name is 8 characters, so 2 words; some writers append a zero word.
_NAME_WORDS = (2, 3)


@dataclass(frozen=True)
class OP2Format:
    """How the words of one OP2 file are laid out.

    Parameters
    ----------
    word_size:
        4 for a 32-bit file, 8 for a 64-bit one.
    byte_order:
        ``"<"`` or ``">"``, as a :mod:`struct` prefix.
    post:
        ``-1`` when the file opens with the date/version header, ``-2`` when it
        does not — the two values of ``PARAM,POST`` that produce an OP2.
    version:
        The writing solver's version string, ``""`` for a ``POST,-2`` file
        which has nowhere to put one.
    """

    word_size: int
    byte_order: str
    post: int
    version: str = ""

    @property
    def int_dtype(self) -> np.dtype:
        """NumPy integer type of one word."""
        return np.dtype(f"{self.byte_order}i{self.word_size}")

    @property
    def float_dtype(self) -> np.dtype:
        """NumPy floating type of one word."""
        return np.dtype(f"{self.byte_order}f{self.word_size}")

    def ints(self, payload: bytes) -> np.ndarray:
        """The payload read as signed integers, one per word."""
        return np.frombuffer(payload, dtype=self.int_dtype)

    def floats(self, payload: bytes) -> np.ndarray:
        """The payload read as floats, one per word."""
        return np.frombuffer(payload, dtype=self.float_dtype)

    def nwords(self, payload: bytes) -> int:
        """How many words the payload holds."""
        return len(payload) // self.word_size

    def text(self, payload: bytes) -> str:
        """The payload read as characters, un-padded.

        In a 64-bit file each 4-character group occupies a whole word, so the
        text is half padding: NX pads every group to 8 bytes (``ABCD    EFGH
        ``) and MSC writes the characters contiguously in the low half.  Both
        collapse to the same 32-bit string here, since a trailing blank group
        is padding under either reading.
        """

        if self.word_size == 8:
            groups = [payload[8 * i : 8 * i + 8] for i in range(len(payload) // 8)]
            if all(group[4:].strip() == b"" for group in groups):
                payload = b"".join(group[:4] for group in groups)
        return payload.decode("ascii", errors="replace").rstrip("\x00").strip()


@dataclass(frozen=True)
class OP2Block:
    """One named data block of an OP2 file.

    Parameters
    ----------
    name:
        The block's 8-character name, stripped (``GEOM1``, ``LAMA``, ...).
    offset:
        Byte offset of the block's name record, so a caller can report where a
        block it refused to read starts.
    trailer:
        The seven-ish word trailer that follows the name; its meaning is
        block-specific and this module does not interpret it.
    records:
        The block's logical records, in file order, starting with the subtable
        name record — empty when the block was skipped rather than read.
    """

    name: str
    offset: int
    trailer: tuple[int, ...]
    records: tuple[bytes, ...] = ()


def read_op2_blocks(
    source: str | PathLike[str] | BinaryIO,
    *,
    keep: Container[str] = frozenset(),
) -> tuple[OP2Format, list[OP2Block]]:
    """Walk an OP2 and return its format and its data blocks, in file order.

    Only the records of the blocks named in ``keep`` are materialized; every
    other block is stepped over by its keys, so listing the tables of a large
    result file costs a walk of its markers rather than its contents.

    Raises
    ------
    ~openfemlab.io.FormatError
        If the file is not an OP2, or its framing is inconsistent — a byte
        count that does not match its record, a key that overruns the file, a
        block that ends without its terminator.
    """

    with _open_binary(source) as (stream, name):
        walker = _Walker(stream, name)
        op2_format = walker.read_header()
        blocks: list[OP2Block] = []
        while True:
            marker = walker.peek_marker()
            if marker is None:
                break
            if marker == 0:
                # Some writers pad the end of the file with a bare terminator.
                walker.read_marker()
                continue
            blocks.append(walker.read_data_block(keep))
        return op2_format, blocks


@contextmanager
def _open_binary(
    source: str | PathLike[str] | BinaryIO,
) -> Iterator[tuple[BinaryIO, str]]:
    """Yield a seekable binary stream over ``source`` and a name for messages."""

    if isinstance(source, (str, PathLike)):
        path = Path(source)
        try:
            stream = path.open("rb")
        except OSError as exc:
            raise FormatError(f"cannot read OP2 file {path!s}: {exc}") from exc
        try:
            yield stream, str(path)
        finally:
            stream.close()
        return

    name = str(getattr(source, "name", "<stream>"))
    try:
        seekable = source.seekable()
    except (AttributeError, OSError):
        seekable = False
    if seekable:
        yield source, name
        return
    try:
        content = source.read()
    except OSError as exc:
        raise FormatError(f"cannot read OP2 stream {name}: {exc}") from exc
    if not isinstance(content, bytes):
        raise FormatError(f"OP2 reader requires a binary stream, got {name}")
    yield BytesIO(content), name


class _Walker:
    """Cursor over the physical, logical and block layers of one file."""

    def __init__(self, stream: BinaryIO, name: str) -> None:
        self._stream = stream
        self._name = name
        self.format = OP2Format(word_size=4, byte_order="<", post=-1)

    # ------------------------------------------------------ physical records

    def _error(self, message: str) -> FormatError:
        return FormatError(f"{self._name}: {message} (at byte {self._tell()})")

    def _tell(self) -> int:
        return int(self._stream.tell())

    def _read_exact(self, count: int, what: str) -> bytes:
        data = self._stream.read(count)
        if not isinstance(data, bytes):
            raise FormatError(f"OP2 reader requires a binary stream, got {self._name}")
        if len(data) != count:
            raise self._error(f"file ends inside {what}: wanted {count} bytes, got {len(data)}")
        return data

    def _read_count(self, what: str) -> int:
        raw = self._read_exact(4, what)
        return int(np.frombuffer(raw, dtype=np.dtype(f"{self.format.byte_order}i4"))[0])

    def _read_raw(self, *, keep: bool) -> tuple[bytes, int]:
        """Read one ``[nbytes, payload, nbytes]`` record.

        Returns the payload — empty when ``keep`` is false and the record was
        stepped over rather than read — and its length in bytes either way.
        """

        nbytes = self._read_count("a record byte count")
        if nbytes < 0:
            raise self._error(f"negative record byte count {nbytes}")
        if nbytes % self.format.word_size:
            raise self._error(
                f"record of {nbytes} bytes is not a whole number of "
                f"{self.format.word_size}-byte words"
            )
        if keep:
            payload = self._read_exact(nbytes, "a record payload")
        else:
            # The closing byte count below is read exactly, so a payload that
            # runs past the end of the file is caught there.
            self._stream.seek(nbytes, 1)
            payload = b""
        closing = self._read_count("a closing record byte count")
        if closing != nbytes:
            raise self._error(
                f"record opens with a byte count of {nbytes} and closes with {closing}"
            )
        return payload, nbytes

    # ------------------------------------------------------- logical records

    def peek_marker(self) -> int | None:
        """The value of the next record if it is a single word, else ``None``.

        ``None`` also means end of file, which is the only place a walk is
        allowed to stop; every other stop is a framing error.
        """

        position = self._tell()
        try:
            head = self._stream.read(4)
            if len(head) < 4:
                return None
            nbytes = int(np.frombuffer(head, dtype=np.dtype(f"{self.format.byte_order}i4"))[0])
            if nbytes != self.format.word_size:
                return None
            payload = self._stream.read(nbytes)
            if len(payload) < nbytes:
                return None
            return int(self.format.ints(payload)[0])
        finally:
            self._stream.seek(position)

    def read_marker(self, expected: int | None = None) -> int:
        """Read a one-word record, optionally checking its value."""

        payload, nbytes = self._read_raw(keep=True)
        if nbytes != self.format.word_size:
            raise self._error(
                f"expected a one-word marker, got {nbytes // self.format.word_size} words"
            )
        marker = int(self.format.ints(payload)[0])
        if expected is not None and marker != expected:
            raise self._error(f"expected marker {expected}, got {marker}")
        return marker

    def read_marker_group(self, expected: int) -> None:
        """Read a record separator: ``[-n]``, optionally followed by ``[1, 0]``."""

        self.read_marker(expected)
        if self.peek_marker() == 1:
            self.read_marker()
            if self.peek_marker() == 0:
                self.read_marker()

    def read_record(self, *, keep: bool) -> bytes:
        """Read one logical record: a key, its payload, and any continuations."""

        payload = self._read_keyed(keep=keep)
        chunks = [payload]
        while True:
            marker = self.peek_marker()
            if marker is None or marker <= 0:
                break
            chunks.append(self._read_keyed(keep=keep))
        return b"".join(chunks) if keep else b""

    def _read_keyed(self, *, keep: bool) -> bytes:
        key = self.read_marker()
        if key <= 0:
            raise self._error(f"expected a positive word count, got {key}")
        payload, nbytes = self._read_raw(keep=keep)
        if nbytes != key * self.format.word_size:
            raise self._error(
                f"key announces {key} words but the record holds "
                f"{nbytes // self.format.word_size}"
            )
        return payload

    # ------------------------------------------------------------ file layer

    def read_header(self) -> OP2Format:
        """Settle the word size and byte order, then step over the header."""

        head = self._stream.read(4)
        if len(head) < 4:
            raise FormatError(f"{self._name}: file is too short to be an OP2")
        self._stream.seek(0)
        word_size, byte_order = _detect_words(head, self._name)
        self.format = OP2Format(word_size=word_size, byte_order=byte_order, post=-1)

        marker = self.read_marker()
        if marker == _NO_HEADER_MARKER:
            # PARAM,POST,-2: no header at all, and the marker just read is the
            # key of the first block's name record.
            self._stream.seek(0)
            self.format = OP2Format(word_size=word_size, byte_order=byte_order, post=-2)
            return self.format
        if marker != _HEADER_MARKER:
            raise self._error(
                f"opening marker is {marker}; an OP2 opens with "
                f"{_HEADER_MARKER} (PARAM,POST,-1) or {_NO_HEADER_MARKER} (PARAM,POST,-2)"
            )

        self._read_raw(keep=False)  # the date the job ran
        self.read_marker(_LABEL_WORDS)
        self._read_raw(keep=False)  # 'NASTRAN FORT TAPE ID CODE - '
        version = self.format.text(self.read_record(keep=True))
        self.read_marker(-1)
        self.read_marker(0)
        self.format = OP2Format(
            word_size=word_size, byte_order=byte_order, post=-1, version=version
        )
        return self.format

    def read_data_block(self, keep: Container[str]) -> OP2Block:
        """Read one named data block, materializing its records only if wanted."""

        offset = self._tell()
        name_record = self.read_record(keep=True)
        if self.format.nwords(name_record) not in _NAME_WORDS:
            raise self._error(
                f"a data block opens with a {_NAME_WORDS[0]}-word name, got "
                f"{self.format.nwords(name_record)} words"
            )
        name = self.format.text(name_record[: 2 * self.format.word_size])
        if not name:
            raise self._error("data block has a blank name")

        self.read_marker_group(-1)
        trailer = tuple(int(word) for word in self.format.ints(self.read_record(keep=True)))

        wanted = name in keep
        records: list[bytes] = []
        index = -2
        while True:
            self.read_marker_group(index)
            marker = self.peek_marker()
            if marker is None:
                raise self._error(f"data block {name!r} ends without its terminating key")
            if marker == 0:
                self.read_marker()
                break
            record = self.read_record(keep=wanted)
            if wanted:
                records.append(record)
            index -= 1
        return OP2Block(name=name, offset=offset, trailer=trailer, records=tuple(records))


def _detect_words(head: bytes, name: str) -> tuple[int, str]:
    """Word size and byte order from the byte count of the opening record."""

    for byte_order, endian in (("<", "little"), (">", "big")):
        value = int.from_bytes(head, endian, signed=True)
        if value in _WORD_SIZES:
            return value, byte_order
    raise FormatError(
        f"{name} is not an OP2: it opens with {head!r}, which is a record byte "
        f"count of neither 4 (32-bit) nor 8 (64-bit) in either byte order"
    )
