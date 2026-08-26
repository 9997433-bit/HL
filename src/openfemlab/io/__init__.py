"""Open, text-based import/export for FE models and modal data.

The native schema is versioned and available in both JSON and YAML.  Generic
``read_data`` also reads repository fixtures without constructing arbitrary
Python objects (YAML uses :func:`yaml.safe_load`).
"""

from __future__ import annotations

from typing import Any

from ._common import (
    SUPPORTED_EXTENSIONS,
    SUPPORTED_FORMATS,
    FormatError,
    read_data,
    write_data,
)
from ._native import (
    SCHEMA_VERSION,
    dof_map_from_dict,
    dof_map_from_labels,
    dof_map_to_dict,
    modal_result_from_dict,
    modal_result_to_dict,
    model_from_dict,
    model_to_dict,
    read,
    read_modal_result,
    read_model,
    read_test_data,
    test_data_from_dict,
    test_data_to_dict,
    write,
    write_modal_result,
    write_model,
    write_test_data,
)

# Familiar persistence aliases for script-oriented workflows.
load = read
dump = write
load_model = read_model
save_model = write_model
load_modal_result = read_modal_result
save_modal_result = write_modal_result
load_test_data = read_test_data
save_test_data = write_test_data


def read_yaml(source):
    """Read an arbitrary YAML document with the safe loader."""

    return read_data(source, format="yaml")


def read_json(source):
    """Read an arbitrary JSON document."""

    return read_data(source, format="json")


def from_meshio(mesh: Any) -> Any:
    """Convert a ``meshio.Mesh`` to a model (planned optional adapter)."""

    try:
        import meshio  # noqa: F401
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "meshio is required for this reader: pip install openfemlab[io]"
        ) from exc
    raise NotImplementedError("meshio bridge is not implemented yet")

__all__ = [
    "SCHEMA_VERSION",
    "SUPPORTED_FORMATS",
    "SUPPORTED_EXTENSIONS",
    "FormatError",
    "read",
    "write",
    "load",
    "dump",
    "read_data",
    "write_data",
    "read_yaml",
    "read_json",
    "read_model",
    "write_model",
    "load_model",
    "save_model",
    "model_to_dict",
    "model_from_dict",
    "read_modal_result",
    "write_modal_result",
    "load_modal_result",
    "save_modal_result",
    "modal_result_to_dict",
    "modal_result_from_dict",
    "read_test_data",
    "write_test_data",
    "load_test_data",
    "save_test_data",
    "test_data_to_dict",
    "test_data_from_dict",
    "dof_map_to_dict",
    "dof_map_from_dict",
    "dof_map_from_labels",
    "from_meshio",
]
