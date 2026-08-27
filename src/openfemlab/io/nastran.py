"""Minimal dependency-free reader for ASCII Nastran bulk-data files.

The supported subset is one connectivity card per element block the solver
formulates, plus the grid, material and property cards those need: ``GRID``,
``CROD``, ``CBAR``, ``CQUAD4``, ``CTETRA``, ``CHEXA``, ``MAT1``, ``PSHELL``
and ``PSOLID``.  Cards may be written in free field or in small fixed field
and may run onto continuation lines; unsupported cards are skipped, together
with their continuations.  ``GRID`` coordinates must use the basic coordinate
system because coordinate-system cards are outside this subset.

Only the linear form of each connectivity card is read.  A ``CTETRA`` or
``CHEXA`` carrying mid-side grid points is rejected rather than silently
truncated to its corner nodes, because dropping them would change the mesh.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from os import PathLike
from pathlib import Path
from typing import TextIO

import numpy as np

from openfemlab.core.neutral import (
    ElementType,
    NeutralMaterial,
    NeutralModel,
    NeutralProperty,
)

from ._common import FormatError

#: Connectivity cards, each mapped to the block it fills and the number of
#: grid points read from it.  Nastran numbers the grids of all four of these
#: the way :mod:`openfemlab.core.elements` expects -- a ``CQUAD4`` runs
#: counter-clockwise, a ``CTETRA`` puts its first three counter-clockwise seen
#: from the fourth, and a ``CHEXA`` gives one face then the opposite face in
#: the same order -- so connectivity passes through unpermuted.
_ELEMENT_CARDS: dict[str, tuple[ElementType, int]] = {
    "CROD": (ElementType.ROD2, 2),
    "CBAR": (ElementType.BEAM2, 2),
    "CQUAD4": (ElementType.QUAD4, 4),
    "CTETRA": (ElementType.TET4, 4),
    "CHEXA": (ElementType.HEX8, 8),
}

#: Cards whose grid list is the whole card, so a further grid field means a
#: higher-order element this reader cannot represent.  ``CBAR`` continues into
#: an orientation vector and ``CQUAD4`` into ``THETA``/``ZOFFS``, so neither
#: can be checked this way.
_HAS_FIXED_GRID_COUNT = frozenset({"CTETRA", "CHEXA"})

_PROPERTY_CARDS = frozenset({"PSHELL", "PSOLID"})
_SUPPORTED_CARDS = frozenset({"GRID", "MAT1"}) | set(_ELEMENT_CARDS) | _PROPERTY_CARDS

#: Block order of the emitted connectivity, so two files that declare the same
#: elements in a different order still produce identical models.
_BLOCK_ORDER: tuple[ElementType, ...] = tuple(
    dict.fromkeys(element_type for element_type, _ in _ELEMENT_CARDS.values())
)

_IMPLICIT_EXPONENT = re.compile(
    r"([+-]?(?:(?:\d+(?:\.\d*)?)|(?:\.\d+)))([+-]\d+)"
)


def read_bdf(source: str | PathLike[str] | TextIO) -> NeutralModel:
    """Read a minimal ASCII BDF model into a :class:`NeutralModel`.

    ``PSHELL`` and ``PSOLID`` land in ``properties``, the shell carrying its
    thickness as ``t`` so :func:`~openfemlab.io.neutral_convert.to_model` binds
    a ``CQUAD4`` at the thickness the file states.  The property ids of the
    other cards are still retained in ``element_property_ids``, but their
    definitions are absent: a rod's section comes from ``PROD`` and a bar's
    from ``PBAR``, both outside this reader's subset, so a ``CROD`` or ``CBAR``
    mesh needs ``section=`` when it is converted.
    """

    text, source_name = _read_text(source)
    nodes: dict[int, tuple[float, float, float]] = {}
    connectivity: dict[ElementType, list[tuple[int, ...]]] = {}
    property_ids: dict[ElementType, list[int]] = {}
    element_ids: dict[ElementType, list[int]] = {}
    element_cards: dict[int, str] = {}
    materials: dict[int, NeutralMaterial] = {}
    properties: dict[int, NeutralProperty] = {}

    for line_number, fields in _iter_cards(text):
        card = fields[0].upper()
        if card == "ENDDATA":
            break
        if card.endswith("*") and card[:-1] in _SUPPORTED_CARDS:
            raise FormatError(
                f"invalid BDF {card} card on line {line_number}: "
                "large-field cards are not supported"
            )
        if card not in _SUPPORTED_CARDS:
            continue

        try:
            if card == "GRID":
                node_id, coordinates = _parse_grid(fields)
                if node_id in nodes:
                    raise FormatError(f"duplicate GRID id {node_id}")
                nodes[node_id] = coordinates
            elif card in _ELEMENT_CARDS:
                element_type, node_count = _ELEMENT_CARDS[card]
                element_id, property_id, element_nodes = _parse_element(
                    card, fields, node_count
                )
                previous = element_cards.get(element_id)
                if previous is not None:
                    raise FormatError(
                        f"duplicate element id {element_id}, already defined by a "
                        f"{previous} card"
                    )
                element_cards[element_id] = card
                connectivity.setdefault(element_type, []).append(element_nodes)
                property_ids.setdefault(element_type, []).append(property_id)
                element_ids.setdefault(element_type, []).append(element_id)
            elif card in _PROPERTY_CARDS:
                property_ = _parse_pshell(fields) if card == "PSHELL" else _parse_psolid(fields)
                if property_.id in properties:
                    raise FormatError(f"duplicate property id {property_.id}")
                properties[property_.id] = property_
            else:
                material = _parse_mat1(fields)
                if material.id in materials:
                    raise FormatError(f"duplicate MAT1 id {material.id}")
                materials[material.id] = material
        except FormatError as exc:
            raise FormatError(
                f"invalid BDF {card} card on line {line_number}: {exc}"
            ) from exc

    referenced = {
        node_id for rows in connectivity.values() for row in rows for node_id in row
    }
    unknown_nodes = sorted(referenced - nodes.keys())
    if unknown_nodes:
        joined = ", ".join(str(node_id) for node_id in unknown_nodes)
        raise FormatError(f"element connectivity references unknown GRID ids: {joined}")

    node_ids = np.fromiter(nodes, dtype=np.int64, count=len(nodes))
    node_coordinates = np.asarray(list(nodes.values()), dtype=np.float64).reshape((-1, 3))
    elements: dict[ElementType, np.ndarray] = {}
    element_property_ids: dict[ElementType, np.ndarray] = {}
    for element_type in _BLOCK_ORDER:
        rows = connectivity.get(element_type)
        if not rows:
            continue
        elements[element_type] = np.asarray(rows, dtype=np.int64).reshape(
            (len(rows), len(rows[0]))
        )
        element_property_ids[element_type] = np.asarray(
            property_ids[element_type], dtype=np.int64
        )

    meta: dict[str, object] = {
        "format": "nastran-bdf",
        "element_ids": {
            element_type.value: element_ids[element_type] for element_type in elements
        },
    }
    if source_name is not None:
        meta["source"] = source_name
    return NeutralModel(
        nodes=node_coordinates,
        node_ids=node_ids,
        elements=elements,
        element_property_ids=element_property_ids,
        materials=materials,
        properties=properties,
        meta=meta,
    )


def _read_text(source: str | PathLike[str] | TextIO) -> tuple[str, str | None]:
    if isinstance(source, (str, PathLike)):
        try:
            path = Path(source)
            return path.read_text(encoding="utf-8"), str(path)
        except (OSError, UnicodeError) as exc:
            raise FormatError(f"cannot read BDF file {source!s}: {exc}") from exc

    try:
        value = source.read()
    except (OSError, UnicodeError) as exc:
        raise FormatError(f"cannot read BDF stream: {exc}") from exc
    if not isinstance(value, str):
        raise FormatError("BDF reader requires an ASCII text stream")
    name = getattr(source, "name", None)
    return value, str(name) if name is not None else None


def _iter_cards(text: str) -> Iterator[tuple[int, list[str]]]:
    """Yield ``(line_number, fields)`` per logical card, continuations merged.

    A continuation line -- one blank in field 1, or opening with ``+`` or a
    leading comma -- appends its data fields to the card above it, which is how
    a ``CHEXA`` reaches its eighth grid point.  One that follows no card at all
    is dropped, as is one that follows a card this reader skips.  The reported
    line number is always that of the card's first line.
    """

    pending: list[str] | None = None
    pending_line = 0
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.split("$", maxsplit=1)[0].rstrip()
        if not line.strip():
            continue
        if _is_continuation(line):
            if pending is not None:
                pending.extend(_continuation_fields(line))
            continue
        if pending is not None:
            yield pending_line, pending
            pending = None
        fields = _card_fields(line)
        if fields:
            pending, pending_line = fields, line_number
    if pending is not None:
        yield pending_line, pending


def _is_continuation(line: str) -> bool:
    if line[:1] in ("+", ","):
        return True
    return not line[:8].strip()


def _card_fields(line: str) -> list[str]:
    if "," in line:
        return _drop_continuation_marker([field.strip() for field in line.split(",")])

    card_field = line[:8].strip()
    if not card_field:
        return []
    columns = (
        None
        if any(character.isspace() for character in card_field)
        else _fixed_field_columns(line)
    )
    if columns is None:
        return _drop_continuation_marker(line.split())
    return [card_field, *columns]


def _continuation_fields(line: str) -> list[str]:
    if "," in line:
        return _drop_continuation_marker([field.strip() for field in line.split(",")][1:])

    columns = _fixed_field_columns(line)
    if columns is not None:
        return columns
    return _drop_continuation_marker(line.split()[1:] if line[:1] == "+" else line.split())


def _fixed_field_columns(line: str) -> list[str] | None:
    """Data fields of columns 9-72, or ``None`` when the line is not aligned.

    Column 73 onwards holds the continuation marker rather than data, so it is
    never returned.  A chunk containing whitespace between two tokens means the
    line is not on the eight-column grid at all and has to be split on
    whitespace instead.
    """

    columns = [line[start : start + 8].strip() for start in range(8, min(len(line), 72), 8)]
    if any(any(character.isspace() for character in column) for column in columns):
        return None
    return columns


def _drop_continuation_marker(fields: list[str]) -> list[str]:
    """Strip trailing blanks and a field-10 continuation marker from a card."""

    while fields and not fields[-1]:
        fields.pop()
    if fields and fields[-1].startswith("+"):
        fields.pop()
    return fields


def _parse_grid(fields: list[str]) -> tuple[int, tuple[float, float, float]]:
    node_id = _positive_integer(_required(fields, 1, "ID"), "GRID ID")
    coordinate_system = _integer(_field(fields, 2) or "0", "GRID CP")
    if coordinate_system != 0:
        raise FormatError(
            f"GRID {node_id} uses unsupported coordinate system CP={coordinate_system}"
        )
    coordinates = (
        _float(_field(fields, 3) or "0", "GRID X1"),
        _float(_field(fields, 4) or "0", "GRID X2"),
        _float(_field(fields, 5) or "0", "GRID X3"),
    )
    return node_id, coordinates


def _parse_element(
    card: str, fields: list[str], node_count: int
) -> tuple[int, int, tuple[int, ...]]:
    """``(EID, PID, grids)`` of one connectivity card.

    Fields past the grid list are ignored, which is what makes a ``CBAR``'s
    orientation vector and a ``CQUAD4``'s ``THETA`` harmless here.
    """

    element_id = _positive_integer(_required(fields, 1, "EID"), f"{card} EID")
    property_id = _positive_integer(_required(fields, 2, "PID"), f"{card} PID")
    element_nodes = tuple(
        _positive_integer(
            _required(fields, 3 + offset, f"G{offset + 1}"), f"{card} G{offset + 1}"
        )
        for offset in range(node_count)
    )
    if len(set(element_nodes)) != node_count:
        raise FormatError(f"{card} {element_id} must reference {node_count} distinct GRID ids")
    if card in _HAS_FIXED_GRID_COUNT and _field(fields, 3 + node_count):
        raise FormatError(
            f"{card} {element_id} has more than {node_count} grid points; only the "
            f"{node_count}-node form is supported"
        )
    return element_id, property_id, element_nodes


def _parse_pshell(fields: list[str]) -> NeutralProperty:
    property_id = _positive_integer(_required(fields, 1, "PID"), "PSHELL PID")
    material_id = _positive_integer(_required(fields, 2, "MID1"), "PSHELL MID1")
    thickness = _float(_required(fields, 3, "T"), "PSHELL T")
    if thickness <= 0.0:
        raise FormatError("PSHELL T must be positive")
    return NeutralProperty(
        id=property_id,
        material_id=material_id,
        values={"t": thickness},
        name="PSHELL",
    )


def _parse_psolid(fields: list[str]) -> NeutralProperty:
    """A solid property, which carries only the material the elements use.

    ``CORDM``, ``IN``, ``STRESS``, ``ISOP`` and ``FCTN`` describe integration
    and output choices that this reader's isotropic, fully integrated solids do
    not take from the file, so they are read past.
    """

    property_id = _positive_integer(_required(fields, 1, "PID"), "PSOLID PID")
    material_id = _positive_integer(_required(fields, 2, "MID"), "PSOLID MID")
    return NeutralProperty(id=property_id, material_id=material_id, name="PSOLID")


def _parse_mat1(fields: list[str]) -> NeutralMaterial:
    material_id = _positive_integer(_required(fields, 1, "MID"), "MAT1 MID")
    youngs_modulus = _optional_float(fields, 2, "MAT1 E")
    shear_modulus = _optional_float(fields, 3, "MAT1 G")
    poisson_ratio = _optional_float(fields, 4, "MAT1 NU")
    density = _float(_field(fields, 5) or "0", "MAT1 RHO")

    if youngs_modulus is None:
        if shear_modulus is None or poisson_ratio is None:
            raise FormatError("MAT1 requires at least two of E, G, and NU")
        youngs_modulus = 2.0 * shear_modulus * (1.0 + poisson_ratio)
    elif poisson_ratio is None:
        if shear_modulus is None:
            raise FormatError("MAT1 requires at least two of E, G, and NU")
        poisson_ratio = youngs_modulus / (2.0 * shear_modulus) - 1.0
    elif shear_modulus is None:
        shear_modulus = youngs_modulus / (2.0 * (1.0 + poisson_ratio))

    if youngs_modulus <= 0.0:
        raise FormatError("MAT1 E must be positive")
    if shear_modulus is not None and shear_modulus <= 0.0:
        raise FormatError("MAT1 G must be positive")
    if not -1.0 < poisson_ratio < 0.5:
        raise FormatError("MAT1 NU must be between -1 and 0.5")
    if density < 0.0:
        raise FormatError("MAT1 RHO must be non-negative")
    return NeutralMaterial(
        id=material_id,
        E=youngs_modulus,
        nu=poisson_ratio,
        rho=density,
    )


def _field(fields: list[str], index: int) -> str:
    return fields[index].strip() if index < len(fields) else ""


def _required(fields: list[str], index: int, name: str) -> str:
    value = _field(fields, index)
    if not value:
        raise FormatError(f"missing required {name} field")
    return value


def _optional_float(fields: list[str], index: int, name: str) -> float | None:
    token = _field(fields, index)
    return _float(token, name) if token else None


def _positive_integer(token: str, name: str) -> int:
    value = _integer(token, name)
    if value <= 0:
        raise FormatError(f"{name} must be positive")
    return value


def _integer(token: str, name: str) -> int:
    value = _float(token, name)
    integer = int(value)
    if float(integer) != value:
        raise FormatError(f"{name} must be an integer, found {token!r}")
    return integer


def _float(token: str, name: str) -> float:
    normalized = token.replace("D", "E").replace("d", "e")
    try:
        value = float(normalized)
    except ValueError:
        match = _IMPLICIT_EXPONENT.fullmatch(normalized)
        if match is None:
            raise FormatError(f"{name} is not a valid number: {token!r}") from None
        value = float(f"{match.group(1)}E{match.group(2)}")
    if not np.isfinite(value):
        raise FormatError(f"{name} must be finite")
    return value


read_nastran = read_bdf


def write_bdf(
    model: NeutralModel,
    destination: str | PathLike[str] | TextIO,
    *,
    title: str = "OpenFEMLab export",
) -> None:
    """Write a minimal ASCII BDF from a :class:`NeutralModel` (MS-9.6 export).

    Emits ``GRID``, ``MAT1``, ``PSHELL``/``PSOLID``, and connectivity cards
    present in the model.  Rods and bars without ``PROD``/``PBAR`` sections are
    still written with property ids so geometry round-trips; section data must
    be supplied again on import when converting to an internal model.
    """
    lines = [f"TITLE = {title}", "BEGIN BULK"]
    for material_id, material in sorted(model.materials.items()):
        lines.append(
            f"MAT1,{material_id},{material.E:g},{material.rho:g},,{material.nu:g}"
        )
    for property_id, property_ in sorted(model.properties.items()):
        thickness = property_.values.get("t")
        if thickness is not None:
            lines.append(
                f"PSHELL,{property_id},{property_.material_id},{thickness:g}"
            )
        else:
            lines.append(f"PSOLID,{property_id},{property_.material_id}")
    for index, node_id in enumerate(model.node_ids):
        x, y, z = model.nodes[index]
        lines.append(f"GRID,{int(node_id)},,{x:g},{y:g},{z:g}")
    element_id = 1
    card_map = {
        ElementType.ROD2: "CROD",
        ElementType.BEAM2: "CBAR",
        ElementType.QUAD4: "CQUAD4",
        ElementType.TET4: "CTETRA",
        ElementType.HEX8: "CHEXA",
    }
    for element_type in _BLOCK_ORDER:
        connectivity = model.elements.get(element_type)
        if connectivity is None or connectivity.size == 0:
            continue
        card = card_map.get(element_type)
        if card is None:
            continue
        property_ids = model.element_property_ids.get(element_type)
        for row_index, nodes in enumerate(np.asarray(connectivity, dtype=np.int64)):
            pid = int(property_ids[row_index]) if property_ids is not None else 1
            node_list = ",".join(str(int(node_id)) for node_id in nodes)
            lines.append(f"{card},{element_id},{pid},{node_list}")
            element_id += 1
    lines.append("ENDDATA")
    payload = "\n".join(lines) + "\n"
    if isinstance(destination, (str, PathLike)):
        Path(destination).write_text(payload, encoding="utf-8")
    else:
        destination.write(payload)


__all__ = ["read_bdf", "read_nastran", "write_bdf"]
