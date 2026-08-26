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
from .sizing import (
    ModalDesignEvaluator,
    compile_sizing_problem,
    minimize_sizing,
    problem_from_updater,
)
from .variables import DesignSpace, ShapeVariable

__all__ = [
    "Constraint",
    "DesignSpace",
    "DesignState",
    "GradientCheck",
    "MatrixDerivativeProvider",
    "ModalDesignEvaluator",
    "NaturalFrequency",
    "Objective",
    "OptimizationIterate",
    "OptimizationProblem",
    "OptimizationResult",
    "OptimizerBackend",
    "Response",
    "ScipyBackend",
    "ShapeVariable",
    "TotalMass",
    "VectorConstraint",
    "available_backends",
    "check_gradient",
    "compile_sizing_problem",
    "finite_difference_gradient",
    "frequency_floor",
    "get_backend",
    "kkt_residual",
    "minimize_sizing",
    "modal_frequency_gradients",
    "problem_from_updater",
]
