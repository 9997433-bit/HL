"""Optimization layer (L3): gradient-based design optimization on validated models.

Structural sizing/shape optimization (spec module M5) reusing the platform's
existing machinery instead of duplicating it:

- **M1 modal solves** — one eigensolve per design point, shared by the
  objective and every constraint through a cached design state.
- **M3 sensitivity kernel** — analytic Fox-Kapoor frequency and mass gradients
  whenever the parametric model exposes assembled matrix derivatives
  (:class:`~openfemlab.updating.scaling_model.ScalingModel` does), with a
  mode-tracked central finite-difference fallback otherwise.
- **M2 mode tracking** — MAC-based tracking keeps "a constraint on mode i"
  attached to the physical mode branch across crossings.

Two levels of API:

- the structural layer (:func:`minimize_sizing`, :class:`Objective`,
  :class:`Constraint`, :class:`DesignSpace`) that speaks in models, parameters
  and responses; and
- the vector layer (:class:`OptimizationProblem`,
  :class:`~openfemlab.optimization.backends.ScipyBackend`) that backends
  consume, keeping the optimizer swappable.

Sizing variables are the same
:class:`~openfemlab.updating.parameters.UpdatableParameter` objects the model
updater uses, and :func:`problem_from_updater` lowers an updating run into the
same vector problem — calibration and design optimization share one problem
statement.  Design and staging: ``docs/OPTIMIZATION.md``.
"""

from __future__ import annotations

from .backends import (
    OptimizerBackend,
    ScipyBackend,
    available_backends,
    get_backend,
    kkt_residual,
)
from .doe import (
    DesignOfExperimentsResult,
    factorial_design_vectors,
    run_factorial_screen,
    run_lhs_screen,
)
from .gradients import (
    GradientCheck,
    MatrixDerivativeProvider,
    check_gradient,
    finite_difference_gradient,
    modal_frequency_gradients,
)
from .problem import (
    OptimizationIterate,
    OptimizationProblem,
    OptimizationResult,
    VectorConstraint,
)
from .responses import (
    Constraint,
    DesignState,
    NaturalFrequency,
    Objective,
    Response,
    TotalMass,
    frequency_floor,
)
from .rsm import QuadraticRSM, fit_quadratic_rsm
from .sizing import (
    ModalDesignEvaluator,
    MorphingGeometryModel,
    compile_sizing_problem,
    minimize_sizing,
    problem_from_updater,
)
from .topology import (
    TopologyResult,
    apply_density_filter,
    build_density_filter,
    effective_heaviside_beta,
    element_centroids,
    element_volumes,
    heaviside_projection,
    heaviside_projection_derivative,
    run_simp_topology,
)
from .variables import DesignSpace, ShapeVariable

__all__ = [
    "DesignOfExperimentsResult",
    "Constraint",
    "DesignSpace",
    "DesignState",
    "GradientCheck",
    "MatrixDerivativeProvider",
    "ModalDesignEvaluator",
    "MorphingGeometryModel",
    "NaturalFrequency",
    "Objective",
    "OptimizationIterate",
    "OptimizationProblem",
    "OptimizationResult",
    "OptimizerBackend",
    "Response",
    "ScipyBackend",
    "QuadraticRSM",
    "ShapeVariable",
    "TopologyResult",
    "TotalMass",
    "VectorConstraint",
    "apply_density_filter",
    "available_backends",
    "build_density_filter",
    "check_gradient",
    "compile_sizing_problem",
    "element_centroids",
    "element_volumes",
    "effective_heaviside_beta",
    "factorial_design_vectors",
    "finite_difference_gradient",
    "fit_quadratic_rsm",
    "frequency_floor",
    "get_backend",
    "heaviside_projection",
    "heaviside_projection_derivative",
    "run_factorial_screen",
    "run_lhs_screen",
    "run_simp_topology",
    "kkt_residual",
    "minimize_sizing",
    "modal_frequency_gradients",
    "problem_from_updater",
]
