"""Sensitivity-based FE model updating.

Three layers:

- :mod:`~openfemlab.updating.parameters` — bounded, dimensionless scaling
  factors and their mapping to the optimiser's design space.
- :mod:`~openfemlab.updating.sensitivity` — analytical (Fox & Kapoor)
  eigenvalue and eigenvector derivatives, plus solver-independent
  finite-difference sensitivities with MAC-based mode tracking.
- :mod:`~openfemlab.updating.updater` — the regularised Gauss-Newton /
  Levenberg-Marquardt loop minimising frequency and MAC residuals.

:class:`~openfemlab.updating.scaling_model.ScalingModel` ties them together for
the affine ``K(θ) = K_0 + Σ θ_j K_j`` substructuring parameterisation.
"""

from __future__ import annotations

from .parameters import Parameter, ParameterSet, ParameterType, UpdatableParameter
from .scaling_model import ScalingModel
from .sensitivity import (
    ModalData,
    SensitivityResult,
    as_modal_data,
    eigenvalue_sensitivity,
    eigenvalue_to_frequency_sensitivity,
    finite_difference_jacobian,
    frequency_sensitivity,
    mac_sensitivity,
    modal_sensitivity,
    mode_shape_sensitivity,
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
    "Parameter",
    "ParameterSet",
    "ParameterType",
    "ScalingModel",
    "SensitivityResult",
    "UpdatableParameter",
    "UpdatingOptions",
    "UpdatingResult",
    "as_modal_data",
    "eigenvalue_sensitivity",
    "eigenvalue_to_frequency_sensitivity",
    "finite_difference_jacobian",
    "frequency_sensitivity",
    "mac_sensitivity",
    "modal_sensitivity",
    "mode_shape_sensitivity",
    "relative_sensitivity",
    "track_modes",
    "update_model",
]
