"""Minimal dependency-free reader for ASCII Nastran bulk-data files.

The supported subset is intentionally small: ``GRID``, ``CROD``, and
``MAT1`` cards in free-field or small fixed-field form.  Unsupported cards
are skipped.  ``GRID`` coordinates must use the basic coordinate system
because coordinate-system cards are outside this subset.
"""

from __future__ import annotations

import re
from os import PathLike
from pathlib import Path
from typing import TextIO

import numpy as np

from openfemlab.core.neutral import ElementType, NeutralMaterial, NeutralModel

from ._common import FormatError

_SUPPORTED_CARDS = frozenset({"GRID", "CROD", "MAT1"})
_IMPLICIT_EXPONENT = re.compile(
    r"([+-]?(?:(?:\d+(?:\.\d*)?)|(?:\.\d+)))([+-]\d+)"
)


def read_bdf(source: str | PathLike[str] | TextIO) -> NeutralModel:
    """Read a minimal ASCII BDF model into a :class:`NeutralModel`.

    ``CROD`` property ids are retained in ``element_property_ids``.  The
    corresponding property definitions are intentionally absent because a
    rod's material and section are defined by ``PROD``, which is outside this
    reader's minimal card subset.
    """

    text, source_name = _read_text(source)
    nodes: dict[int, tuple[float, float, float]] = {}
    rods: list[tuple[int, int]] = []
    rod_ids: list[int] = []
    rod_property_ids: list[int] = []
    materials: dict[int, NeutralMaterial] = {}

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.split("$", maxsplit=1)[0].rstrip()
        if not line.strip():
            continue

        fields = _card_fields(line)
        if not fields:
            continue
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
            elif card == "CROD":
                element_id, property_id, node_pair = _parse_crod(fields)
                if element_id in rod_ids:
                    raise FormatError(f"duplicate CROD id {element_id}")
                rod_ids.append(element_id)
                rod_property_ids.append(property_id)
                rods.append(node_pair)
            else:
                material = _parse_mat1(fields)
                if material.id in materials:
                    raise FormatError(f"duplicate MAT1 id {material.id}")
                materials[material.id] = material
        except FormatError as exc:
            raise FormatError(
                f"invalid BDF {card} card on line {line_number}: {exc}"
            ) from exc

    unknown_nodes = sorted({node_id for rod in rods for node_id in rod} - nodes.keys())
    if unknown_nodes:
        joined = ", ".join(str(node_id) for node_id in unknown_nodes)
        raise FormatError(f"CROD connectivity references unknown GRID ids: {joined}")

    node_ids = np.fromiter(nodes, dtype=np.int64, count=len(nodes))
    node_coordinates = np.asarray(list(nodes.values()), dtype=np.float64).reshape((-1, 3))
    elements: dict[ElementType, np.ndarray] = {}
    element_property_ids: dict[ElementType, np.ndarray] = {}
    if rods:
        elements[ElementType.ROD2] = np.asarray(rods, dtype=np.int64).reshape((-1, 2))
        element_property_ids[ElementType.ROD2] = np.asarray(
            rod_property_ids, dtype=np.int64
        )

    meta: dict[str, object] = {
        "format": "nastran-bdf",
        "element_ids": {ElementType.ROD2.value: rod_ids},
    }
    if source_name is not None:
        meta["source"] = source_name
    return NeutralModel(
        nodes=node_coordinates,
        node_ids=node_ids,
        elements=elements,
        element_property_ids=element_property_ids,
        materials=materials,
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


def _card_fields(line: str) -> list[str]:
    if "," in line:
        return [field.strip() for field in line.split(",")]

    card_field = line[:8].strip()
    if not card_field:
        return []
    if any(character.isspace() for character in card_field):
        return line.split()
    return [
        card_field,
        *(line[start : start + 8].strip() for start in range(8, len(line), 8)),
    ]


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


def _parse_crod(fields: list[str]) -> tuple[int, int, tuple[int, int]]:
    element_id = _positive_integer(_required(fields, 1, "EID"), "CROD EID")
    property_id = _positive_integer(_required(fields, 2, "PID"), "CROD PID")
    first_node = _positive_integer(_required(fields, 3, "G1"), "CROD G1")
    second_node = _positive_integer(_required(fields, 4, "G2"), "CROD G2")
    if first_node == second_node:
        raise FormatError(f"CROD {element_id} must reference two distinct GRID ids")
    return element_id, property_id, (first_node, second_node)


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

__all__ = ["read_bdf", "read_nastran"]
