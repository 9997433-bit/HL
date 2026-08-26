"""Minimal ASCII UFF/UNV reader for modal data.

The reader intentionally covers the two test-data datasets needed by the
modal workflow:

* dataset 55: normal-mode shapes at nodes;
* dataset 58: functions at nodal degrees of freedom (typically FRFs).

Other datasets are ignored so that files containing geometry or provenance
records can still be opened. Binary dataset 58 (``58b``) is not supported.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from typing import TextIO

import numpy as np
import numpy.typing as npt

from ._common import FormatError

_NUMBER = re.compile(
    r"[+-]?(?:(?:\d+(?:\.\d*)?)|(?:\.\d+))(?:[EeDd][+-]?\d+)?"
)


@dataclass(frozen=True, slots=True)
class UFFMode:
    """One dataset-55 normal mode."""

    frequency_hz: float
    mode_number: int
    node_ids: npt.NDArray[np.int64]
    values: npt.NDArray[np.float64] | npt.NDArray[np.complex128]
    load_case: int
    modal_mass: float
    viscous_damping: float
    hysteretic_damping: float
    data_characteristic: int
    specific_data_type: int
    id_lines: tuple[str, ...]

    @property
    def mode_shape(self) -> npt.NDArray[np.float64] | npt.NDArray[np.complex128]:
        """Mode-shape values with layout ``(nodes, values_per_node)``."""

        return self.values


@dataclass(frozen=True, slots=True)
class UFFFunction:
    """One dataset-58 function sampled on a frequency abscissa."""

    frequencies_hz: npt.NDArray[np.float64]
    values: npt.NDArray[np.float64] | npt.NDArray[np.complex128]
    function_type: int
    function_id: int
    version_number: int
    load_case: int
    response_entity: str
    response_node: int
    response_direction: int
    reference_entity: str
    reference_node: int
    reference_direction: int
    abscissa_label: str
    abscissa_units: str
    id_lines: tuple[str, ...]

    @property
    def data(self) -> npt.NDArray[np.float64] | npt.NDArray[np.complex128]:
        """Alias used by common UFF tooling."""

        return self.values

    @property
    def x(self) -> npt.NDArray[np.float64]:
        """Alias for the frequency abscissa."""

        return self.frequencies_hz


UFFDataset = UFFMode | UFFFunction


def read_uff(source: str | PathLike[str] | TextIO) -> list[UFFDataset]:
    """Read supported datasets from an ASCII UFF/UNV file.

    Unsupported dataset numbers are skipped. Malformed supported datasets
    raise :class:`~openfemlab.io.FormatError`.
    """

    text = _read_text(source)
    datasets: list[UFFDataset] = []
    for dataset_number, payload in _dataset_blocks(text):
        try:
            if dataset_number == 55:
                datasets.append(_parse_55(payload))
            else:
                datasets.append(_parse_58(payload))
        except FormatError as exc:
            raise FormatError(f"invalid UFF dataset {dataset_number}: {exc}") from exc
    return datasets


def read_uff_modes(source: str | PathLike[str] | TextIO) -> list[UFFMode]:
    """Read all dataset-55 normal modes from ``source``."""

    return [dataset for dataset in read_uff(source) if isinstance(dataset, UFFMode)]


def read_uff_functions(source: str | PathLike[str] | TextIO) -> list[UFFFunction]:
    """Read all dataset-58 functions from ``source``."""

    return [dataset for dataset in read_uff(source) if isinstance(dataset, UFFFunction)]


def _read_text(source: str | PathLike[str] | TextIO) -> str:
    if isinstance(source, (str, PathLike)):
        try:
            return Path(source).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise FormatError(f"cannot read UFF file {source!s}: {exc}") from exc
    try:
        value = source.read()
    except (OSError, UnicodeError) as exc:
        raise FormatError(f"cannot read UFF stream: {exc}") from exc
    if not isinstance(value, str):
        raise FormatError("UFF reader requires an ASCII text stream")
    return value


def _dataset_blocks(text: str) -> list[tuple[int, list[str]]]:
    lines = text.splitlines()
    blocks: list[tuple[int, list[str]]] = []
    index = 0
    while index < len(lines) - 1:
        if lines[index].strip() != "-1":
            index += 1
            continue
        marker = lines[index + 1].strip().lower()
        if marker.startswith("58b"):
            raise FormatError("binary UFF dataset 58b is not supported")
        if marker not in {"55", "58"}:
            index += 1
            continue
        dataset_number = int(marker)
        end = index + 2
        while end < len(lines) and lines[end].strip() != "-1":
            end += 1
        if end == len(lines):
            raise FormatError(f"UFF dataset {dataset_number} has no closing -1 delimiter")
        blocks.append((dataset_number, lines[index + 2 : end]))
        index = end
    return blocks


def _parse_55(lines: list[str]) -> UFFMode:
    if len(lines) < 10:
        raise FormatError("dataset 55 is shorter than its eight-record header")

    definition = _numbers(lines[5])
    if len(definition) < 6:
        raise FormatError("record 6 requires six integer fields")
    analysis_type = _integer(definition[1], "analysis type")
    if analysis_type != 2:
        raise FormatError(
            f"only normal-mode analysis type 2 is supported, found {analysis_type}"
        )
    data_characteristic = _integer(definition[2], "data characteristic")
    specific_data_type = _integer(definition[3], "specific data type")
    data_type = _integer(definition[4], "data type")
    values_per_node = _integer(definition[5], "values per node")
    if data_type not in {2, 5}:
        raise FormatError(f"data type must be 2 (real) or 5 (complex), found {data_type}")
    if values_per_node <= 0:
        raise FormatError("values per node must be positive")

    integer_parameters = _numbers(lines[6])
    if len(integer_parameters) < 4:
        raise FormatError("record 7 requires load-case and mode-number fields")
    load_case = _integer(integer_parameters[2], "load case")
    mode_number = _integer(integer_parameters[3], "mode number")

    real_parameters = _numbers(lines[7])
    if len(real_parameters) < 4:
        raise FormatError("record 8 requires frequency, mass, and damping fields")
    frequency_hz, modal_mass, viscous_damping, hysteretic_damping = real_parameters[:4]
    if not np.isfinite(frequency_hz) or frequency_hz < 0.0:
        raise FormatError("frequency must be finite and non-negative")

    raw_values_per_node = values_per_node * (2 if data_type == 5 else 1)
    node_ids: list[int] = []
    rows: list[list[float]] = []
    index = 8
    while index < len(lines):
        if not lines[index].strip():
            index += 1
            continue
        node_fields = _numbers(lines[index])
        if len(node_fields) != 1:
            raise FormatError(f"expected one node number in record {index + 1}")
        node_ids.append(_integer(node_fields[0], "node number"))
        index += 1

        raw_row: list[float] = []
        while len(raw_row) < raw_values_per_node and index < len(lines):
            raw_row.extend(_numbers(lines[index]))
            index += 1
        if len(raw_row) != raw_values_per_node:
            raise FormatError(
                f"node {node_ids[-1]} requires {raw_values_per_node} numeric values, "
                f"found {len(raw_row)}"
            )
        rows.append(raw_row)

    if not rows:
        raise FormatError("dataset 55 contains no nodal values")
    if len(set(node_ids)) != len(node_ids):
        raise FormatError("dataset 55 contains duplicate node numbers")

    raw = np.asarray(rows, dtype=np.float64)
    values: np.ndarray
    if data_type == 5:
        values = raw[:, 0::2] + 1j * raw[:, 1::2]
    else:
        values = raw
    return UFFMode(
        frequency_hz=float(frequency_hz),
        mode_number=mode_number,
        node_ids=np.asarray(node_ids, dtype=np.int64),
        values=values,
        load_case=load_case,
        modal_mass=float(modal_mass),
        viscous_damping=float(viscous_damping),
        hysteretic_damping=float(hysteretic_damping),
        data_characteristic=data_characteristic,
        specific_data_type=specific_data_type,
        id_lines=tuple(line.rstrip() for line in lines[:5]),
    )


def _parse_58(lines: list[str]) -> UFFFunction:
    if len(lines) < 12:
        raise FormatError("dataset 58 is shorter than its eleven-record header")

    (
        function_type,
        function_id,
        version_number,
        load_case,
        response_entity,
        response_node,
        response_direction,
        reference_entity,
        reference_node,
        reference_direction,
    ) = _function_identification(lines[5])

    data_form = _numbers(lines[6])
    if len(data_form) < 6:
        raise FormatError("record 7 requires six data-form fields")
    ordinate_type = _integer(data_form[0], "ordinate data type")
    number_of_points = _integer(data_form[1], "number of points")
    spacing = _integer(data_form[2], "abscissa spacing")
    abscissa_minimum = data_form[3]
    abscissa_increment = data_form[4]
    if ordinate_type not in {2, 4, 5, 6}:
        raise FormatError(f"unsupported ordinate data type {ordinate_type}")
    if number_of_points < 0:
        raise FormatError("number of points must be non-negative")
    if spacing not in {0, 1}:
        raise FormatError("abscissa spacing must be 0 (uneven) or 1 (even)")

    complex_values = ordinate_type in {5, 6}
    fields_per_point = (2 if complex_values else 1) + (0 if spacing else 1)
    expected_fields = number_of_points * fields_per_point
    raw_values = [value for line in lines[11:] for value in _numbers(line)]
    if len(raw_values) != expected_fields:
        raise FormatError(
            f"record 12 requires {expected_fields} numeric values for {number_of_points} "
            f"points, found {len(raw_values)}"
        )
    raw = np.asarray(raw_values, dtype=np.float64)

    if spacing:
        frequencies = abscissa_minimum + np.arange(number_of_points) * abscissa_increment
        if complex_values:
            values = raw[0::2] + 1j * raw[1::2]
        else:
            values = raw
    elif complex_values:
        frequencies = raw[0::3].copy()
        values = raw[1::3] + 1j * raw[2::3]
    else:
        frequencies = raw[0::2].copy()
        values = raw[1::2].copy()

    if not np.all(np.isfinite(frequencies)):
        raise FormatError("frequency abscissa contains non-finite values")
    label, units = _axis_labels(lines[7])
    return UFFFunction(
        frequencies_hz=np.asarray(frequencies, dtype=np.float64),
        values=values,
        function_type=function_type,
        function_id=function_id,
        version_number=version_number,
        load_case=load_case,
        response_entity=response_entity,
        response_node=response_node,
        response_direction=response_direction,
        reference_entity=reference_entity,
        reference_node=reference_node,
        reference_direction=reference_direction,
        abscissa_label=label,
        abscissa_units=units,
        id_lines=tuple(line.rstrip() for line in lines[:5]),
    )


def _function_identification(
    line: str,
) -> tuple[int, int, int, int, str, int, int, str, int, int]:
    if len(line) >= 80:
        fields = (
            line[0:5],
            line[5:15],
            line[15:20],
            line[20:30],
            line[31:41],
            line[41:51],
            line[51:55],
            line[56:66],
            line[66:76],
            line[76:80],
        )
    else:
        split = line.split()
        if len(split) != 10:
            raise FormatError("record 6 requires ten function-identification fields")
        fields = tuple(split)
    try:
        return (
            int(fields[0]),
            int(fields[1]),
            int(fields[2]),
            int(fields[3]),
            fields[4].strip(),
            int(fields[5]),
            int(fields[6]),
            fields[7].strip(),
            int(fields[8]),
            int(fields[9]),
        )
    except ValueError as exc:
        raise FormatError(f"record 6 contains an invalid integer: {exc}") from exc


def _axis_labels(line: str) -> tuple[str, str]:
    if len(line) < 26:
        return "", ""
    return line[26:46].strip(), line[47:67].strip()


def _numbers(line: str) -> list[float]:
    values: list[float] = []
    for token in _NUMBER.findall(line):
        try:
            values.append(float(token.replace("D", "E").replace("d", "e")))
        except ValueError as exc:  # pragma: no cover - guarded by the numeric expression
            raise FormatError(f"invalid numeric field {token!r}") from exc
    return values


def _integer(value: float, name: str) -> int:
    integer = int(value)
    if float(integer) != value:
        raise FormatError(f"{name} must be an integer, found {value}")
    return integer


__all__ = [
    "UFFDataset",
    "UFFFunction",
    "UFFMode",
    "read_uff",
    "read_uff_functions",
    "read_uff_modes",
]
