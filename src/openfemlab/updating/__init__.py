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
- :mod:`~openfemlab.updating.frf` — the MS-3.2 FRF residual provider driving
  the same loop from a measured frequency response instead of a mode table.
- :mod:`~openfemlab.updating.resolver` — binds declarative dotted parameter
  targets (``materials.steel.E``) to a solver model and builds the affine
  parameterisation from it.

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
from .force_id import identify_harmonic_forces
from .frf import (
    FRF_WEIGHTINGS,
    FRFResidual,
    FRFState,
    FRFUpdater,
    FRFUpdatingResult,
    update_model_frf,
)
from .mmu import MMUComponent, mmu_frequency_residual, update_model_mmu
from .parameters import Parameter, ParameterSet, ParameterType, UpdatableParameter
from .resolver import (
    NonAffineTargetError,
    ParameterTarget,
    ResolvedParameter,
    ScalingSpec,
    TargetError,
    parameters_from_mapping,
    parse_target,
    resolve_parameters,
    resolve_scaling_spec,
    scaling_model_from_spec,
)
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
    "FRF_WEIGHTINGS",
    "BayesianUpdater",
    "BayesianUpdatingResult",
    "FRFResidual",
    "FRFState",
    "FRFUpdater",
    "FRFUpdatingResult",
    "GaussianPrior",
    "IterationRecord",
    "ModalData",
    "ModelUpdater",
    "NonAffineTargetError",
    "Parameter",
    "ParameterSet",
    "ParameterTarget",
    "ParameterType",
    "PosteriorEstimate",
    "ResolvedParameter",
    "ScalingModel",
    "ScalingSpec",
    "SensitivityResult",
    "TargetError",
    "MMUComponent",
    "UpdatableParameter",
    "UpdatingOptions",
    "UpdatingResult",
    "as_modal_data",
    "covariance_matrix",
    "eigenvalue_sensitivity",
    "eigenvalue_to_frequency_sensitivity",
    "finite_difference_jacobian",
    "frequency_sensitivity",
    "identify_harmonic_forces",
    "mac_sensitivity",
    "map_step",
    "mmu_frequency_residual",
    "modal_sensitivity",
    "mode_shape_sensitivity",
    "parameters_from_mapping",
    "parse_target",
    "posterior_covariance",
    "posterior_sigma",
    "precision_matrix",
    "relative_sensitivity",
    "resolve_parameters",
    "resolve_scaling_spec",
    "scaling_model_from_spec",
    "track_modes",
    "update_model",
    "update_model_bayesian",
    "update_model_frf",
    "update_model_mmu",
]
