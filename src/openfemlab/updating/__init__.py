"""Sensitivity-based FE model updating."""

from __future__ import annotations

from .parameters import ParameterSet, ParameterType, UpdatableParameter
from .sensitivity import (
    ModalData,
    SensitivityResult,
    as_modal_data,
    eigenvalue_sensitivity,
    eigenvalue_to_frequency_sensitivity,
    finite_difference_jacobian,
    modal_sensitivity,
    relative_sensitivity,
    track_modes,
)
from .updater import (
    IterationRecord,
    ModelUpdater,
    UpdatingOptions,
    UpdatingResult,
    update_model,
)

__all__ = [
    "IterationRecord",
    "ModalData",
    "ModelUpdater",
    "ParameterSet",
    "ParameterType",
    "SensitivityResult",
    "UpdatableParameter",
    "UpdatingOptions",
    "UpdatingResult",
    "as_modal_data",
    "eigenvalue_sensitivity",
    "eigenvalue_to_frequency_sensitivity",
    "finite_difference_jacobian",
    "modal_sensitivity",
    "relative_sensitivity",
    "track_modes",
    "update_model",
]
