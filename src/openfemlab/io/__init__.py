"""Open, text-based import/export for FE models and modal data.

The native schema is versioned and available in both JSON and YAML.  Generic
``read_data`` also reads repository fixtures without constructing arbitrary
Python objects (YAML uses :func:`yaml.safe_load`).

Foreign formats arrive through dedicated readers: :func:`read_bdf` for the
Nastran bulk-data subset, :func:`read_uff` for UFF/UNV test data, and the
:mod:`~openfemlab.io.meshio_bridge` adapter for everything ``meshio`` can
open.  The meshio functions re-exported here import the optional package
lazily, so this module stays importable without the ``[io]`` extra.

Every one of those readers returns a :class:`~openfemlab.core.neutral.NeutralModel`;
:func:`neutral_to_model` converts it into the internal
:class:`~openfemlab.core.model.Model` so an imported mesh can be re-analyzed.
"""

from __future__ import annotations

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
from .meshio_bridge import from_meshio, read_meshio, to_meshio, write_meshio
from .nastran import read_bdf, read_nastran
from .neutral_convert import (
    SUPPORTED_ELEMENT_TYPES,
    infer_dofs,
    material_from_neutral,
    neutral_to_model,
    section_from_values,
)
from .uff import (
    UFFDataset,
    UFFFunction,
    UFFMode,
    read_uff,
    read_uff_functions,
    read_uff_modes,
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
    "to_meshio",
    "read_meshio",
    "write_meshio",
    "read_bdf",
    "read_nastran",
    "SUPPORTED_ELEMENT_TYPES",
    "neutral_to_model",
    "infer_dofs",
    "material_from_neutral",
    "section_from_values",
    "UFFDataset",
    "UFFFunction",
    "UFFMode",
    "read_uff",
    "read_uff_functions",
    "read_uff_modes",
]
