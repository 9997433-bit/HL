"""Sensitivity-based FE model updating.

Three layers:

- :mod:`~openfemlab.updating.parameters` — bounded, dimensionless scaling
  factors and their mapping to the optimiser's design space.
- :mod:`~openfemlab.updating.sensitivity` — analytical (Fox & Kapoor)
  eigenvalue and eigenvector derivatives, plus solver-independent
  finite-difference sensitivities with MAC-based mode tracking.
- :mod:`~openfemlab.updating.updater` — the regularised Gauss-Newton /
  Levenberg-Marquardt loop minimising frequency and MAC residuals.
- :mod:`~openfemlab.updating.bayesian` — the MS-3.5 MAP variant of that loop:
  Gaussian prior, measurement-noise covariance, Laplace posterior covariance.

:class:`~openfemlab.updating.scaling_model.ScalingModel` ties them together for
the affine ``K(θ) = K_0 + Σ θ_j K_j`` substructuring parameterisation.
"""

from __future__ import annotations

from .bayesian import (
    BayesianUpdater,
    BayesianUpdatingResult,
    GaussianPrior,
    PosteriorEstimate,
    covariance_matrix,
    map_step,
    posterior_covariance,
    posterior_sigma,
    precision_matrix,
    update_model_bayesian,
)
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
    "BayesianUpdater",
    "BayesianUpdatingResult",
    "GaussianPrior",
    "IterationRecord",
    "ModalData",
    "ModelUpdater",
    "Parameter",
    "ParameterSet",
    "ParameterType",
    "PosteriorEstimate",
    "ScalingModel",
    "SensitivityResult",
    "UpdatableParameter",
    "UpdatingOptions",
    "UpdatingResult",
    "as_modal_data",
    "covariance_matrix",
    "eigenvalue_sensitivity",
    "eigenvalue_to_frequency_sensitivity",
    "finite_difference_jacobian",
    "frequency_sensitivity",
    "mac_sensitivity",
    "map_step",
    "modal_sensitivity",
    "mode_shape_sensitivity",
    "posterior_covariance",
    "posterior_sigma",
    "precision_matrix",
    "relative_sensitivity",
    "track_modes",
    "update_model",
    "update_model_bayesian",
]
