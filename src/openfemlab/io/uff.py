"""Minimal ASCII UFF/UNV reader and writer for modal data.

Both directions intentionally cover the two test-data datasets needed by the
modal workflow:

* dataset 55: normal-mode shapes at nodes;
* dataset 58: functions at nodal degrees of freedom (typically FRFs).

On read, other datasets are ignored so that files containing geometry or
provenance records can still be opened. Binary dataset 58 (``58b``) is not
supported in either direction.

:func:`write_uff` emits the same records the reader accepts, so
``read_uff(write_uff(...))`` returns the dataset it was given. Header records
keep the ``E13.5`` field the format prescribes, which rounds mode shapes and
modal parameters to six significant digits; dataset-58 ordinates are written
in the double-precision ``E20.12`` field instead, and an evenly spaced
abscissa falls back to explicit abscissa values when the six-digit header
cannot reproduce it.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
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
    """One dataset-55 normal mode.

    Every field the reader recovers from a file also has a write-side default,
    so a mode can be built from a solver result with the four fields that
    carry data and handed straight to :func:`write_uff`.
    """

    frequency_hz: float
    mode_number: int
    node_ids: npt.NDArray[np.int64]
    values: npt.NDArray[np.float64] | npt.NDArray[np.complex128]
    load_case: int = 0
    modal_mass: float = 0.0
    viscous_damping: float = 0.0
    hysteretic_damping: float = 0.0
    #: 2 = three-degree-of-freedom global translation vector.
    data_characteristic: int = 2
    #: 8 = displacement.
    specific_data_type: int = 8
    id_lines: tuple[str, ...] = ()

    @property
    def mode_shape(self) -> npt.NDArray[np.float64] | npt.NDArray[np.complex128]:
        """Mode-shape values with layout ``(nodes, values_per_node)``."""

        return self.values


@dataclass(frozen=True, slots=True)
class UFFFunction:
    """One dataset-58 function sampled on a frequency abscissa."""

    frequencies_hz: npt.NDArray[np.float64]
    values: npt.NDArray[np.float64] | npt.NDArray[np.complex128]
    #: 4 = frequency response function.
    function_type: int = 4
    function_id: int = 1
    version_number: int = 0
    load_case: int = 0
    response_entity: str = "NONE"
    response_node: int = 0
    response_direction: int = 0
    reference_entity: str = "NONE"
    reference_node: int = 0
    reference_direction: int = 0
    abscissa_label: str = "Frequency"
    abscissa_units: str = "Hz"
    ordinate_label: str = ""
    ordinate_units: str = ""
    id_lines: tuple[str, ...] = ()

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


def write_uff(
    datasets: UFFDataset | Iterable[UFFDataset],
    destination: str | PathLike[str] | TextIO,
) -> None:
    """Write datasets to an ASCII UFF/UNV file or text stream.

    ``datasets`` is a single :class:`UFFMode`/:class:`UFFFunction` or any
    iterable of them; the blocks are written in the order given. Datasets that
    cannot be represented raise :class:`~openfemlab.io.FormatError`.
    """

    text = format_uff(datasets)
    if isinstance(destination, (str, PathLike)):
        try:
            Path(destination).write_text(text, encoding="utf-8", newline="\n")
        except (OSError, UnicodeError) as exc:
            raise FormatError(f"cannot write UFF file {destination!s}: {exc}") from exc
        return
    try:
        destination.write(text)
    except (OSError, UnicodeError) as exc:
        raise FormatError(f"cannot write UFF stream: {exc}") from exc


def format_uff(datasets: UFFDataset | Iterable[UFFDataset]) -> str:
    """Return the ASCII UFF text for ``datasets`` without touching the disk."""

    if isinstance(datasets, (UFFMode, UFFFunction)):
        datasets = [datasets]
    lines: list[str] = []
    for position, dataset in enumerate(datasets):
        if isinstance(dataset, UFFMode):
            dataset_number, formatter = 55, _format_55
        elif isinstance(dataset, UFFFunction):
            dataset_number, formatter = 58, _format_58
        else:
            raise FormatError(
                f"cannot write {type(dataset).__name__} as a UFF dataset; "
                "expected a UFFMode or UFFFunction"
            )
        try:
            records = formatter(dataset)  # type: ignore[arg-type]
        except FormatError as exc:
            raise FormatError(
                f"invalid UFF dataset {dataset_number} at position {position}: {exc}"
            ) from exc
        lines.extend([_DELIMITER, f"{dataset_number:6d}", *records, _DELIMITER])
    return "".join(f"{line}\n" for line in lines)


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
    ordinate_label, ordinate_units = _axis_labels(lines[8])
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
        ordinate_label=ordinate_label,
        ordinate_units=ordinate_units,
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


_DELIMITER = "    -1"
_ID_LINE_COUNT = 5
_ID_LINE_WIDTH = 80
_ID_LINE_FILLER = "NONE"
_AXIS_FIELD_WIDTH = 20
_ENTITY_FIELD_WIDTH = 10
#: Specific data type 18 identifies a frequency abscissa.
_FREQUENCY_DATA_TYPE = 18


def _format_55(mode: UFFMode) -> list[str]:
    values = _values_array(mode.values, "mode-shape values")
    if values.ndim != 2:
        raise FormatError(f"mode-shape values must be two-dimensional, found {values.ndim}")
    node_count, values_per_node = values.shape
    if node_count == 0:
        raise FormatError("dataset 55 contains no nodal values")
    if values_per_node == 0:
        raise FormatError("values per node must be positive")

    node_ids = _node_ids(mode.node_ids, node_count)
    frequency = float(mode.frequency_hz)
    if not np.isfinite(frequency) or frequency < 0.0:
        raise FormatError("frequency must be finite and non-negative")

    data_type = 5 if np.iscomplexobj(values) else 2
    if data_type == 5:
        raw = np.empty((node_count, 2 * values_per_node), dtype=np.float64)
        raw[:, 0::2] = values.real
        raw[:, 1::2] = values.imag
    else:
        raw = values.astype(np.float64, copy=False)

    records = _id_records(mode.id_lines)
    records.append(
        _integer_record(
            [
                (1, 10, "model type"),
                (2, 10, "analysis type"),
                (mode.data_characteristic, 10, "data characteristic"),
                (mode.specific_data_type, 10, "specific data type"),
                (data_type, 10, "data type"),
                (values_per_node, 10, "values per node"),
            ]
        )
    )
    records.append(
        _integer_record(
            [
                (2, 10, "integer parameter count"),
                (4, 10, "real parameter count"),
                (mode.load_case, 10, "load case"),
                (mode.mode_number, 10, "mode number"),
            ]
        )
    )
    records.append(
        _real_record(
            [
                frequency,
                float(mode.modal_mass),
                float(mode.viscous_damping),
                float(mode.hysteretic_damping),
            ]
        )
    )
    for node_id, row in zip(node_ids, raw, strict=True):
        records.append(_integer_record([(node_id, 10, "node number")]))
        records.extend(_real_records(row, per_line=6))
    return records


def _format_58(function: UFFFunction) -> list[str]:
    values = _values_array(function.values, "function values")
    frequencies = _values_array(function.frequencies_hz, "frequency abscissa")
    if np.iscomplexobj(frequencies):
        raise FormatError("frequency abscissa must be real")
    frequencies = frequencies.astype(np.float64, copy=False)
    if values.ndim != 1 or frequencies.ndim != 1:
        raise FormatError("dataset 58 abscissa and ordinates must be one-dimensional")
    if frequencies.size != values.size:
        raise FormatError(
            f"{frequencies.size} abscissa values for {values.size} ordinate values"
        )
    if values.size == 0:
        # The reader needs an eleven-record header plus at least one data
        # record, so an empty function has no representation.
        raise FormatError("dataset 58 requires at least one data point")
    if np.any(frequencies < 0.0):
        raise FormatError("frequency abscissa must be non-negative")

    complex_values = np.iscomplexobj(values)
    ordinate_type = 6 if complex_values else 4
    even, minimum, increment = _abscissa_spacing(frequencies)

    records = _id_records(function.id_lines)
    records.append(_function_identification_record(function))
    records.append(
        _integer_record(
            [
                (ordinate_type, 10, "ordinate data type"),
                (values.size, 10, "number of points"),
                (1 if even else 0, 10, "abscissa spacing"),
            ]
        )
        + _real_record([minimum, increment, 0.0])
    )
    records.append(
        _axis_record(_FREQUENCY_DATA_TYPE, function.abscissa_label, function.abscissa_units)
    )
    records.append(_axis_record(0, function.ordinate_label, function.ordinate_units))
    records.append(_axis_record(0, "", ""))
    records.append(_axis_record(0, "", ""))

    if complex_values and even:
        fields = np.empty(2 * values.size, dtype=np.float64)
        fields[0::2] = values.real
        fields[1::2] = values.imag
        per_line = 4
    elif complex_values:
        fields = np.empty(3 * values.size, dtype=np.float64)
        fields[0::3] = frequencies
        fields[1::3] = values.real
        fields[2::3] = values.imag
        per_line = 3
    elif even:
        fields = values.astype(np.float64, copy=False)
        per_line = 4
    else:
        fields = np.empty(2 * values.size, dtype=np.float64)
        fields[0::2] = frequencies
        fields[1::2] = values.real
        per_line = 4
    records.extend(_double_records(fields, per_line=per_line))
    return records


def _abscissa_spacing(frequencies: npt.NDArray[np.float64]) -> tuple[bool, float, float]:
    """Decide between an even and an uneven abscissa.

    Even spacing stores only the first value and the increment, both in the
    six-significant-digit field record 7 prescribes. That is kept only when
    those two rounded numbers rebuild the abscissa to within a millionth of
    its span; otherwise every abscissa value is written out in full.
    """

    if frequencies.size == 1:
        return True, _rounded_real(frequencies[0]), 0.0
    minimum = _rounded_real(frequencies[0])
    increment = _rounded_real((frequencies[-1] - frequencies[0]) / (frequencies.size - 1))
    rebuilt = minimum + np.arange(frequencies.size) * increment
    span = float(np.max(np.abs(frequencies)))
    tolerance = 1e-6 * max(span, abs(increment))
    if np.all(np.abs(rebuilt - frequencies) <= tolerance):
        return True, minimum, increment
    return False, 0.0, 0.0


def _rounded_real(value: float) -> float:
    """Return ``value`` as the reader recovers it from an ``E13.5`` field."""

    return float(_real(value))


def _function_identification_record(function: UFFFunction) -> str:
    return (
        _integer_record(
            [
                (function.function_type, 5, "function type"),
                (function.function_id, 10, "function identification number"),
                (function.version_number, 5, "version number"),
                (function.load_case, 10, "load case"),
            ]
        )
        + " "
        + _entity_field(function.response_entity, "response entity")
        + _integer_record(
            [
                (function.response_node, 10, "response node"),
                (function.response_direction, 4, "response direction"),
            ]
        )
        + " "
        + _entity_field(function.reference_entity, "reference entity")
        + _integer_record(
            [
                (function.reference_node, 10, "reference node"),
                (function.reference_direction, 4, "reference direction"),
            ]
        )
    )


def _axis_record(specific_data_type: int, label: str, units: str) -> str:
    return (
        _integer_record(
            [
                (specific_data_type, 10, "specific data type"),
                (0, 5, "length units exponent"),
                (0, 5, "force units exponent"),
                (0, 5, "temperature units exponent"),
            ]
        )
        + f" {_axis_field(label, 'axis label')} {_axis_field(units, 'axis units')}"
    )


def _axis_field(text: str, name: str) -> str:
    value = str(text).strip()
    if len(value) > _AXIS_FIELD_WIDTH:
        raise FormatError(
            f"{name} {value!r} exceeds the {_AXIS_FIELD_WIDTH}-character field"
        )
    return f"{value:<{_AXIS_FIELD_WIDTH}}"


def _entity_field(name: str, description: str) -> str:
    value = str(name).strip()
    if len(value) > _ENTITY_FIELD_WIDTH:
        raise FormatError(
            f"{description} {value!r} exceeds the {_ENTITY_FIELD_WIDTH}-character field"
        )
    return f"{value:>{_ENTITY_FIELD_WIDTH}}"


def _id_records(id_lines: Sequence[str]) -> list[str]:
    records = [str(line).rstrip() for line in id_lines]
    if len(records) > _ID_LINE_COUNT:
        raise FormatError(
            f"dataset opens with {_ID_LINE_COUNT} free-text records, found {len(records)}"
        )
    for record in records:
        if len(record) > _ID_LINE_WIDTH:
            raise FormatError(f"free-text record {record!r} exceeds {_ID_LINE_WIDTH} columns")
        if record.strip() == "-1":
            raise FormatError("a free-text record cannot be the -1 block delimiter")
    records.extend([_ID_LINE_FILLER] * (_ID_LINE_COUNT - len(records)))
    return [record or _ID_LINE_FILLER for record in records]


def _node_ids(node_ids: npt.ArrayLike, node_count: int) -> list[int]:
    array = np.asarray(node_ids)
    if array.ndim != 1:
        raise FormatError("node numbers must be one-dimensional")
    if array.size != node_count:
        raise FormatError(f"{array.size} node numbers for {node_count} rows of values")
    identifiers: list[int] = []
    for value in array.tolist():
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise FormatError(f"node number {value!r} is not numeric")
        identifiers.append(_integer(float(value), "node number"))
    if len(set(identifiers)) != len(identifiers):
        raise FormatError("dataset 55 contains duplicate node numbers")
    if any(identifier <= 0 for identifier in identifiers):
        raise FormatError("node numbers must be positive")
    return identifiers


def _values_array(values: npt.ArrayLike, name: str) -> np.ndarray:
    try:
        array = np.asarray(values)
    except (TypeError, ValueError) as exc:  # pragma: no cover - numpy accepts most input
        raise FormatError(f"{name} are not a numeric array: {exc}") from exc
    if array.dtype.kind not in {"i", "u", "f", "c"}:
        raise FormatError(f"{name} are not a numeric array, found dtype {array.dtype}")
    if not np.all(np.isfinite(array)):
        raise FormatError(f"{name} contain non-finite entries")
    return array


def _integer_record(fields: Sequence[tuple[int, int, str]]) -> str:
    return "".join(_fixed_integer(value, width, name) for value, width, name in fields)


def _fixed_integer(value: int, width: int, name: str) -> str:
    integer = _integer(float(value), name)
    field = f"{integer:{width}d}"
    if len(field) > width:
        raise FormatError(f"{name} {integer} does not fit the {width}-column field")
    return field


def _real(value: float) -> str:
    return f"{float(value):13.5E}"


def _real_record(values: Iterable[float]) -> str:
    return "".join(_real(value) for value in values)


def _real_records(values: npt.NDArray[np.float64], *, per_line: int) -> list[str]:
    return [
        _real_record(values[start : start + per_line])
        for start in range(0, len(values), per_line)
    ]


def _double_records(values: npt.NDArray[np.float64], *, per_line: int) -> list[str]:
    return [
        "".join(f"{float(value):20.12E}" for value in values[start : start + per_line])
        for start in range(0, len(values), per_line)
    ]


__all__ = [
    "UFFDataset",
    "UFFFunction",
    "UFFMode",
    "format_uff",
    "read_uff",
    "read_uff_functions",
    "read_uff_modes",
    "write_uff",
]
