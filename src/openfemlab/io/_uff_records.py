"""Record-level scanning shared by the UFF and UNV readers.

UFF and UNV name the same ASCII container: a file is a sequence of datasets,
each opened and closed by a line holding ``-1`` and identified by the dataset
number on the line that follows.  :mod:`openfemlab.io.uff` reads the test-data
datasets (55 modes, 58 functions) and :mod:`openfemlab.io.unv` the geometry
datasets (2411 nodes, 2412 elements), so the delimiter scan and the numeric
field helpers they both need live here rather than in either of them.
"""

from __future__ import annotations

import re
from collections.abc import Container
from os import PathLike
from pathlib import Path
from typing import TextIO

from ._common import FormatError

__all__ = ["dataset_blocks", "integer", "numbers", "read_text"]

_NUMBER = re.compile(
    r"[+-]?(?:(?:\d+(?:\.\d*)?)|(?:\.\d+))(?:[EeDd][+-]?\d+)?"
)
_DELIMITER = "-1"


def read_text(
    source: str | PathLike[str] | TextIO, *, description: str
) -> tuple[str, str | None]:
    """Read ``source`` as text, returning it with a provenance name.

    ``description`` names the format in error messages (``"UFF"``, ``"UNV"``).
    The name is the path for a filesystem source and the stream's ``name``
    attribute when it has one; it is ``None`` for anonymous streams.
    """

    if isinstance(source, (str, PathLike)):
        path = Path(source)
        try:
            return path.read_text(encoding="utf-8"), str(path)
        except (OSError, UnicodeError) as exc:
            raise FormatError(f"cannot read {description} file {source!s}: {exc}") from exc
    try:
        value = source.read()
    except (OSError, UnicodeError) as exc:
        raise FormatError(f"cannot read {description} stream: {exc}") from exc
    if not isinstance(value, str):
        raise FormatError(f"{description} reader requires an ASCII text stream")
    name = getattr(source, "name", None)
    return value, str(name) if name is not None else None


def dataset_blocks(text: str, keep: Container[int]) -> list[tuple[int, list[str]]]:
    """Split ``text`` into the ``(dataset number, records)`` blocks in ``keep``.

    Datasets outside ``keep`` are skipped without being parsed, which is what
    lets a reader open a file whose other datasets it knows nothing about.  A
    kept dataset that is never closed is an error; an unkept one is not, since
    the scan never claimed to understand it.
    """

    lines = text.splitlines()
    blocks: list[tuple[int, list[str]]] = []
    index = 0
    while index < len(lines) - 1:
        if lines[index].strip() != _DELIMITER:
            index += 1
            continue
        marker = lines[index + 1].strip()
        if marker.lower().startswith("58b"):
            raise FormatError("binary UFF dataset 58b is not supported")
        number = _dataset_number(marker)
        if number is None or number not in keep:
            index += 1
            continue
        end = index + 2
        while end < len(lines) and lines[end].strip() != _DELIMITER:
            end += 1
        if end == len(lines):
            raise FormatError(f"UFF dataset {number} has no closing -1 delimiter")
        blocks.append((number, lines[index + 2 : end]))
        index = end
    return blocks


def numbers(line: str) -> list[float]:
    """Extract every numeric field on ``line``, accepting Fortran ``D`` exponents.

    Fields are matched rather than split so that the fixed-width records of a
    file whose columns have run together still read correctly.
    """

    values: list[float] = []
    for token in _NUMBER.findall(line):
        try:
            values.append(float(token.replace("D", "E").replace("d", "e")))
        except ValueError as exc:  # pragma: no cover - guarded by the numeric expression
            raise FormatError(f"invalid numeric field {token!r}") from exc
    return values


def integer(value: float, name: str) -> int:
    """Return ``value`` as an ``int``, rejecting a field that is not integral."""

    result = int(value)
    if float(result) != value:
        raise FormatError(f"{name} must be an integer, found {value}")
    return result


def _dataset_number(marker: str) -> int | None:
    if not marker.isdigit():
        return None
    return int(marker)
