"""Shared JSON/YAML codec helpers for :mod:`openfemlab.io`."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from enum import Enum
from os import PathLike
from pathlib import Path
from typing import Any, TextIO

import numpy as np
import yaml

SUPPORTED_FORMATS = ("json", "yaml")
SUPPORTED_EXTENSIONS = (".json", ".yaml", ".yml")


class FormatError(ValueError):
    """A native OpenFEMLab file is malformed or uses an unsupported format."""


def _format_name(source: str | PathLike[str] | TextIO, format: str | None) -> str:
    candidate = format
    if candidate is None:
        if isinstance(source, (str, PathLike)):
            candidate = Path(source).suffix
        else:
            candidate = Path(getattr(source, "name", "")).suffix
    normalized = str(candidate or "").lower().lstrip(".")
    if normalized == "yml":
        normalized = "yaml"
    if normalized not in SUPPORTED_FORMATS:
        expected = ", ".join(SUPPORTED_EXTENSIONS)
        raise FormatError(
            f"cannot determine a supported format (expected one of {expected}); "
            "pass format='json' or format='yaml'"
        )
    return normalized


def read_data(
    source: str | PathLike[str] | TextIO,
    *,
    format: str | None = None,
) -> Any:
    """Read a JSON/YAML document using safe, non-object-constructing loaders.

    Unlike the typed readers, this function intentionally returns ordinary
    Python mappings/lists.  It is useful for benchmark and test fixtures whose
    schema is not an OpenFEMLab persistence object.
    """

    format_name = _format_name(source, format)
    if isinstance(source, (str, PathLike)):
        with Path(source).open(encoding="utf-8") as stream:
            return _load_stream(stream, format_name)
    return _load_stream(source, format_name)


def _load_stream(stream: TextIO, format_name: str) -> Any:
    try:
        if format_name == "json":
            value = json.load(stream)
        else:
            value = yaml.safe_load(stream)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        name = getattr(stream, "name", "<stream>")
        raise FormatError(f"invalid {format_name.upper()} in {name}: {exc}") from exc
    if value is None:
        raise FormatError(f"{getattr(stream, 'name', '<stream>')} is empty")
    return value


def write_data(
    data: Any,
    destination: str | PathLike[str] | TextIO,
    *,
    format: str | None = None,
) -> None:
    """Write JSON-compatible data as deterministic UTF-8 JSON or safe YAML."""

    format_name = _format_name(destination, format)
    value = _to_builtin(data)
    if isinstance(destination, (str, PathLike)):
        with Path(destination).open("w", encoding="utf-8", newline="\n") as stream:
            _dump_stream(value, stream, format_name)
        return
    _dump_stream(value, destination, format_name)


def _dump_stream(data: Any, stream: TextIO, format_name: str) -> None:
    try:
        if format_name == "json":
            json.dump(data, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
        else:
            yaml.safe_dump(data, stream, sort_keys=False, allow_unicode=True)
    except (TypeError, ValueError, yaml.YAMLError) as exc:
        raise FormatError(f"data cannot be represented as {format_name.upper()}: {exc}") from exc


def require_mapping(value: Any, description: str = "document") -> Mapping[str, Any]:
    """Return ``value`` as a mapping or raise a format-oriented error."""

    if not isinstance(value, Mapping):
        raise FormatError(f"{description} must be a mapping, got {type(value).__name__}")
    return value


def encode_array(value: Any) -> Any:
    """Encode an array, preserving complex values in JSON/YAML-safe form."""

    array = np.asarray(value)
    if np.iscomplexobj(array):
        return {
            "real": _to_builtin(array.real),
            "imag": _to_builtin(array.imag),
        }
    return _to_builtin(array)


def decode_array(value: Any, *, dtype: Any | None = None, name: str = "array") -> np.ndarray:
    """Decode a real array or a ``{"real": ..., "imag": ...}`` complex array."""

    try:
        if isinstance(value, Mapping) and "real" in value:
            real = np.asarray(value["real"], dtype=np.float64)
            imaginary = np.asarray(value.get("imag", np.zeros_like(real)), dtype=np.float64)
            if real.shape != imaginary.shape:
                raise FormatError(
                    f"{name} real and imaginary parts have different shapes "
                    f"{real.shape} and {imaginary.shape}"
                )
            array = real + 1j * imaginary
        else:
            array = np.asarray(value, dtype=dtype)
    except (TypeError, ValueError) as exc:
        raise FormatError(f"{name} is not a valid numeric array: {exc}") from exc
    if dtype is not None and not np.iscomplexobj(array):
        array = array.astype(dtype, copy=False)
    return array


def _to_builtin(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return [_to_builtin(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return _to_builtin(value.item())
    if isinstance(value, Enum):
        return _to_builtin(value.value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _to_builtin(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_builtin(item) for item in value]
    if isinstance(value, complex):
        return {"real": value.real, "imag": value.imag}
    if isinstance(value, float) and not math.isfinite(value):
        # YAML supports these values, but rejecting them keeps JSON and YAML
        # documents interchangeable and avoids implementation-specific tokens.
        raise FormatError("non-finite floating-point values are not supported")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise FormatError(f"unsupported value of type {type(value).__name__}")
