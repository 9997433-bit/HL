"""Sizing optimization hook (spec MS-5.3): model + responses -> vector problem.

The lowering pipeline::

    ParametricModel + Parameters        (same contracts as openfemlab.updating)
        |  ModalDesignEvaluator          one modal solve per design point,
        |                                MAC mode tracking, analytic df/dp
        v                                when matrix derivatives exist
    Objective / Constraints              physical-space values & gradients
        |  compile_sizing_problem        chain rule to design space,
        v                                tracked-FD gradient fallback
    OptimizationProblem                  plain bound-constrained NLP
        |  problem.solve(backend)
        v
    OptimizationResult                   termination report

The *model* contract is the one :class:`~openfemlab.updating.updater.
ModelUpdater` already uses — a callable mapping ``{parameter name: value}`` to
anything :func:`~openfemlab.updating.sensitivity.as_modal_data` understands —
so :class:`~openfemlab.updating.scaling_model.ScalingModel` and any updater
model work here unchanged.  Models additionally exposing ``eigen`` /
``assemble`` / ``derivatives`` (the :class:`~openfemlab.optimization.gradients.
MatrixDerivativeProvider` shape, which ``ScalingModel`` satisfies) unlock the
analytic Fox-Kapoor gradient route and the total-mass objective.
"""

from __future__ import annotations

import warnings
from collections.abc import Callable, Mapping, Sequence

import numpy as np

from ..exceptions import OptimizationError
from ..updating.parameters import ParameterSet, UpdatableParameter
from ..updating.sensitivity import ModalData, as_modal_data, track_modes
from ..updating.updater import ModelUpdater
from .geometry import (
    assemble_shape_stiffness_derivatives,
    elements_support_geometric_derivatives,
)
from .gradients import (
    finite_difference_gradient,
    mass_gradients,
    modal_frequency_gradients,
    translational_mass,
)
from .problem import OptimizationProblem, OptimizationResult, VectorConstraint
from .responses import Constraint, DesignState, Objective, Response
from .variables import DesignSpace

__all__ = [
    "ModalDesignEvaluator",
    "MorphingGeometryModel",
    "compile_sizing_problem",
    "minimize_sizing",
    "problem_from_updater",
]

ModelCallable = Callable[[Mapping[str, float]], object]

#: Design-point cache size of the evaluator (covers one central-difference
#: jacobian sweep of a few dozen variables plus the current iterate).
_CACHE_LIMIT = 64


class MorphingGeometryModel:
    """Parametric FE model whose design variables remesh nodal coordinates.

    Implements :class:`~openfemlab.optimization.gradients.MatrixDerivativeProvider`
    for truss/bar meshes that expose ``stiffness_coord_derivatives``.  Mass
    derivatives are taken as zero (consistent with density-less morph checks);
    frequency changes then come from geometric stiffness alone — exact for
    length-independent mass idealizations and a close approximation when
    remeshing is dominated by stiffness change.
    """

    def __init__(self, model, space: DesignSpace, *, num_modes: int = 6) -> None:
        if not elements_support_geometric_derivatives(model):
            raise OptimizationError(
                "MorphingGeometryModel requires every element to expose "
                "stiffness_coord_derivatives (truss/bar today)"
            )
        if space.n_shape == 0:
            raise OptimizationError("MorphingGeometryModel needs at least one shape variable")
        self.model = model
        self.space = space
        self.num_modes = int(num_modes)
        self._x0 = np.asarray(model.coordinates, dtype=float).copy()
        self.parameter_names = list(space.names)

    def _apply(self, values: Mapping[str, float] | Sequence[float] | np.ndarray) -> None:
        if isinstance(values, Mapping):
            x = self.space.x0().copy()
            for index, name in enumerate(self.space.names):
                if name in values:
                    x[index] = float(values[name])
        else:
            x = np.asarray(values, dtype=float).ravel()
            if x.size != self.space.n_variables:
                x = self.space.x0().copy()
        self.model.set_node_coordinates(self.space.apply_to_coordinates(self._x0, x))

    def __call__(self, values: Mapping[str, float]) -> object:
        from ..solver.modal import ModalSolver

        self._apply(values)
        return ModalSolver(self.model).solve(num_modes=self.num_modes)

    def assemble(self, values: Mapping[str, float] | Sequence[float] | np.ndarray):
        from ..core.assembly import assemble_system

        self._apply(values)
        system = assemble_system(self.model)
        return system.reduced()

    def derivatives(self, names: Sequence[str] | None = None):
        names = list(self.parameter_names if names is None else names)
        bases = []
        for name in names:
            for variable in self.space.shape:
                if variable.name == name:
                    bases.append(variable.basis)
                    break
            else:
                bases.append(None)
        active = [basis for basis in bases if basis is not None]
        derived = (
            assemble_shape_stiffness_derivatives(self.model, active) if active else []
        )
        derived_iter = iter(derived)
        free = self.model.free_dofs
        dK: list = []
        dM: list = []
        for basis in bases:
            if basis is None:
                dK.append(None)
                dM.append(None)
                continue
            full = next(derived_iter)
            dK.append(full[free, :][:, free].tocsr())
            dM.append(None)
        return dK, dM

    def eigen(self, values: Mapping[str, float] | Sequence[float] | np.ndarray):
        from ..solver.modal import ModalSolver

        self._apply(values)
        result = ModalSolver(self.model).solve(num_modes=self.num_modes)
        free = self.model.free_dofs
        return result.eigenvalues, result.mode_shapes[free, :]


class ModalDesignEvaluator:
    """Evaluates and caches one :class:`DesignState` per design point.

    Responsibilities:

    - **One solve per point** — objective and constraints share the cached
      state; ``n_modal_solves`` counts actual eigensolves for the termination
      report.
    - **Mode tracking (AC-OPT-004)** — modes of every new point are re-labeled
      by MAC against the running reference (the tracked view of the previously
      evaluated point), so mode-indexed responses follow physical branches
      across crossings.
    - **Analytic gradient bundle** — when the model satisfies
      :class:`~openfemlab.optimization.gradients.MatrixDerivativeProvider`
      *and* every design variable is one of its parameters, the state carries
      Fox-Kapoor ``df/dp`` (reference mode order) plus the total mass and its
      exact gradient.
    - **Shape morphing** — when ``geometry`` is a :class:`~openfemlab.core.model.Model`
      and the design space carries shape amplitudes, nodal coordinates are
      updated with ``X = X0 + Σ a_j V_j`` before each solve so finite-difference
      gradients see the remeshed mesh.
    """

    def __init__(
        self,
        model: ModelCallable,
        space: DesignSpace,
        *,
        geometry=None,
    ) -> None:
        self.model = model
        self.space = space
        self.n_modal_solves = 0
        self._cache: dict[bytes, DesignState] = {}
        self._reference: ModalData | None = None
        self._analytic = self._supports_analytic()
        self._geometry = geometry
        self._x0 = (
            None
            if geometry is None
            else np.asarray(geometry.coordinates, dtype=float).copy()
        )
        if self._geometry is not None and self.space.n_shape:
            n_nodes = int(self._x0.shape[0])
            for variable in self.space.shape:
                if variable.n_nodes != n_nodes:
                    raise OptimizationError(
                        f"shape variable {variable.name!r} has {variable.n_nodes} nodes "
                        f"but geometry has {n_nodes}"
                    )

    def _supports_analytic(self) -> bool:
        model = self.model
        if not (
            hasattr(model, "eigen")
            and hasattr(model, "assemble")
            and hasattr(model, "derivatives")
        ):
            return False
        known = getattr(model, "parameter_names", None)
        if known is None:
            return False
        # Shape amplitudes remesh geometry.  Analytic Fox-Kapoor is available
        # when the callable is a MorphingGeometryModel (truss geometric dK/da).
        if self.space.n_shape and not isinstance(model, MorphingGeometryModel):
            return False
        return all(name in known for name in self.space.names)

    @property
    def analytic(self) -> bool:
        """Whether the analytic (Fox-Kapoor) gradient route is available."""
        return self._analytic

    def state(self, x: Sequence[float] | np.ndarray) -> DesignState:
        """Evaluated design state at ``x`` (clipped to bounds, cached)."""
        x = self.space.clip(x)
        key = x.tobytes()
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        parameters = self.space.to_physical(x)
        if self._geometry is not None and self.space.n_shape:
            self._geometry.set_node_coordinates(
                self.space.apply_to_coordinates(self._x0, x)
            )
        state = DesignState(x=x, parameters=parameters)
        if self._analytic:
            self._evaluate_analytic(state)
        else:
            state.modal = as_modal_data(self.model(parameters))
        self.n_modal_solves += 1
        state.tracking = self._track(state.modal)
        if (
            state.gradients is not None
            and state.tracking is not None
            and np.all(state.tracking < state.gradients.shape[0])
        ):
            # Rows follow the reference mode labels, like tracked_frequency().
            state.gradients = state.gradients[state.tracking, :]

        if len(self._cache) >= _CACHE_LIMIT:
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = state
        return state

    def _evaluate_analytic(self, state: DesignState) -> None:
        eigenvalues, shapes = self.model.eigen(state.parameters)  # type: ignore[attr-defined]
        frequencies = np.sqrt(np.clip(eigenvalues, 0.0, None)) / (2.0 * np.pi)
        state.modal = ModalData(frequencies=frequencies, mode_shapes=shapes)
        state.gradients = modal_frequency_gradients(
            shapes, eigenvalues, self.model, self.space.names  # type: ignore[arg-type]
        )
        _, M = self.model.assemble(state.parameters)  # type: ignore[attr-defined]
        state.mass = translational_mass(M)
        state.mass_gradient = mass_gradients(self.model, self.space.names)  # type: ignore[arg-type]

    def _track(self, modal: ModalData | None) -> np.ndarray | None:
        if modal is None:
            return None
        if self._reference is None:
            self._reference = modal
            return np.arange(modal.n_modes)
        order = track_modes(self._reference, modal)
        if modal.mode_shapes is not None:
            self._reference = modal.select(order)
        return order


def _lower_scalar(
    evaluator: ModalDesignEvaluator,
    value_fn: Callable[[DesignState], float],
    gradient_fn: Callable[[DesignState], np.ndarray | None],
    label: str,
) -> tuple[Callable[[np.ndarray], float], Callable[[np.ndarray], np.ndarray]]:
    """Close one response over the evaluator: ``(f(x), df/dx(x))`` in design space."""

    def fun(x: np.ndarray) -> float:
        return float(value_fn(evaluator.state(x)))

    warned = [False]

    def jac(x: np.ndarray) -> np.ndarray:
        state = evaluator.state(x)
        physical = gradient_fn(state)
        if physical is not None:
            physical = np.asarray(physical, dtype=float).ravel()
            if physical.size != evaluator.space.n_variables:
                raise OptimizationError(
                    f"{label}: analytic gradient has {physical.size} entries for "
                    f"{evaluator.space.n_variables} design variables"
                )
            return physical * evaluator.space.chain(state.x)
        if not warned[0]:
            warned[0] = True
            warnings.warn(
                f"{label}: no analytic gradient available, falling back to tracked "
                "central finite differences (one modal solve per variable and side)",
                RuntimeWarning,
                stacklevel=2,
            )
        return finite_difference_gradient(fun, state.x, steps=evaluator.space.steps())

    return fun, jac


def compile_sizing_problem(
    model: ModelCallable,
    params: ParameterSet | Sequence[UpdatableParameter] | DesignSpace,
    objective: Objective | Response,
    constraints: Sequence[Constraint] = (),
    *,
    geometry=None,
    **options: object,
) -> tuple[OptimizationProblem, ModalDesignEvaluator]:
    """Lower a structural sizing statement to a vector problem.

    Returns the problem together with its evaluator so callers can inspect
    gradient availability, modal-solve counts, and the cached states — and so
    AC-OPT-001 checks can run against the compiled callbacks directly.

    Pass ``geometry`` (a :class:`~openfemlab.core.model.Model`) when the design
    space includes shape amplitudes so each evaluation remeshes coordinates
    before the modal solve.
    """
    space = params if isinstance(params, DesignSpace) else DesignSpace(sizing=params)
    if isinstance(objective, Response):
        objective = Objective(objective)
    evaluator = ModalDesignEvaluator(model, space, geometry=geometry)

    fun, jac = _lower_scalar(
        evaluator, objective.value, objective.gradient, f"objective {objective.name!r}"
    )
    vector_constraints = [
        VectorConstraint(
            *_lower_scalar(
                evaluator,
                constraint.standardized,
                constraint.standardized_gradient,
                f"constraint {constraint.name!r}",
            ),
            name=constraint.name,
        )
        for constraint in constraints
    ]
    problem = OptimizationProblem(
        objective=fun,
        x0=space.x0(),
        bounds=space.bounds(),
        gradient=jac,
        constraints=vector_constraints,
        names=space.names,
        options=dict(options),
    )
    return problem, evaluator


def minimize_sizing(
    model: ModelCallable,
    params: ParameterSet | Sequence[UpdatableParameter] | DesignSpace,
    objective: Objective | Response,
    constraints: Sequence[Constraint] = (),
    *,
    backend: str = "slsqp",
    tol: float = 1.0e-8,
    max_iter: int = 100,
    seed: int = 0,
    geometry=None,
) -> OptimizationResult:
    """Gradient-based sizing optimization (spec MS-5.3 public API).

    Minimizes ``objective`` over the bounded design variables subject to the
    standardized inequality ``constraints``, reusing the modal solver (M1),
    the Fox-Kapoor sensitivity kernel (M3) and MAC mode tracking (M2).
    """
    problem, evaluator = compile_sizing_problem(
        model, params, objective, constraints, geometry=geometry
    )
    result = problem.solve(backend, tol=tol, max_iter=max_iter, seed=seed)
    result.n_modal_solves = evaluator.n_modal_solves
    return result


def problem_from_updater(updater: ModelUpdater) -> OptimizationProblem:
    """Re-express a model-updating run as a bound-constrained vector problem.

    The objective is the updater's own weighted least-squares cost
    ``f(x) = 1/2 ||r(x)||^2`` with the Gauss-Newton gradient ``J^T r`` built
    from the updater's residual and jacobian machinery (analytic Fox-Kapoor
    sensitivities when the updater has them, its mode-repairing finite
    differences otherwise).  This is the seam through which a generic
    bound-constrained backend (e.g. trust-constr) can drive updating instead of
    the built-in Levenberg-Marquardt loop, and through which updating and
    design studies share one problem statement.
    """

    def evaluate(x: np.ndarray) -> tuple[ModalData, list[tuple[int, int]], np.ndarray]:
        data = updater.evaluate(np.asarray(x, dtype=float))
        pairs = updater.pair(data)
        return data, pairs, updater.residual(data, pairs)

    def objective(x: np.ndarray) -> float:
        _, _, residual = evaluate(x)
        return updater.cost(residual)

    def gradient(x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=float)
        data, pairs, residual = evaluate(x)
        jacobian = updater.jacobian(x, pairs, residual, data)
        return jacobian.T @ residual

    return OptimizationProblem(
        objective=objective,
        x0=updater.parameters.design_values(),
        bounds=updater.parameters.design_bounds(),
        gradient=gradient,
        names=updater.parameters.free_names,
    )
