"""Optimizer backends: the swappable seam over ``scipy.optimize`` and friends.

A backend consumes a fully lowered :class:`~openfemlab.optimization.problem.
OptimizationProblem` (vectors and callables only) and returns an
:class:`~openfemlab.optimization.problem.OptimizationResult`.  The contract a
backend must honour:

- **Bounds are hard** (AC-OPT-003): never evaluate the objective or a
  constraint outside the box; record every accepted iterate in
  ``result.history`` so the bound audit is checkable after the fact.
- **No internal differentiation** (spec MS-5.2): the problem carries gradient
  callbacks (analytic or the compiler's tracked-FD fallback); a backend must
  pass them through and must not request its own numerical jacobians, because
  each hidden evaluation is a full modal solve.
- **Standardized constraints**: the problem states ``g(x) <= 0``; scipy's
  SLSQP convention is ``g(x) >= 0``, so the adapter negates both the function
  and its jacobian when mapping.

The mapping is documented per member in :class:`ScipyBackend` and in
``docs/OPTIMIZATION.md`` section 7, and is gated by AC-OPT-002 on the reference
spring-mass sizing problem and AC-OPT-003 on the iterate history.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

import numpy as np

from ..exceptions import OptimizationError
from .problem import (
    OptimizationIterate,
    OptimizationProblem,
    OptimizationResult,
    VectorConstraint,
)

__all__ = ["OptimizerBackend", "ScipyBackend", "get_backend", "available_backends"]

#: Bound-violation tolerance of the AC-OPT-003 audit.
BOUND_TOL = 1.0e-12

#: ``|g| <= ACTIVE_TOL`` marks a constraint active in the termination report;
#: matches the default of :meth:`~openfemlab.optimization.responses.Constraint.is_active`.
ACTIVE_TOL = 1.0e-6


@runtime_checkable
class OptimizerBackend(Protocol):
    """Anything that can minimize a lowered :class:`OptimizationProblem`."""

    def solve(self, problem: OptimizationProblem) -> OptimizationResult: ...


def _unique_names(constraints: Sequence[VectorConstraint]) -> list[str]:
    """Report keys for the constraints, disambiguating repeated names."""
    counts: dict[str, int] = {}
    names = []
    for constraint in constraints:
        seen = counts.get(constraint.name, 0)
        counts[constraint.name] = seen + 1
        names.append(constraint.name if seen == 0 else f"{constraint.name}#{seen + 1}")
    return names


def _require_jacobian(constraint: VectorConstraint) -> Any:
    if constraint.jac is None:
        raise OptimizationError(
            f"constraint {constraint.name!r} carries no jacobian; spec MS-5.2 "
            "forbids the backend from differentiating it numerically because "
            "every evaluation is a modal solve"
        )
    return constraint.jac


def _stationarity(
    problem: OptimizationProblem,
    x: np.ndarray,
    gradient: np.ndarray,
    active_jacobians: Sequence[np.ndarray],
) -> float:
    """First-order KKT residual at ``x``: ``max |grad f + sum_k mu_k a_k|``.

    The multipliers of everything active at ``x`` are recovered together by one
    non-negative least squares over the columns ``a_k``: the jacobian of each
    active inequality, and ``-e_i`` / ``+e_i`` for a variable sitting on its
    lower / upper bound.  Non-negativity is part of KKT, so an unsigned solve
    could report a spuriously small residual; and the bound directions have to
    enter the *same* fit rather than being projected out afterwards, because
    the constraint multipliers that best explain the free components are not
    the ones a fit over all components returns.  Projecting last leaves a
    residue in the free components of a bound-active solution, which is exactly
    where the measure has to be trustworthy.
    """
    from scipy.optimize import nnls

    residual = np.asarray(gradient, dtype=float).ravel()
    if residual.size == 0:
        return 0.0

    lower, upper = problem.bounds
    columns = [np.asarray(j, dtype=float).ravel() for j in active_jacobians]
    for index in np.flatnonzero(x <= lower + BOUND_TOL):
        direction = np.zeros(residual.size)
        direction[index] = -1.0
        columns.append(direction)
    for index in np.flatnonzero(x >= upper - BOUND_TOL):
        direction = np.zeros(residual.size)
        direction[index] = 1.0
        columns.append(direction)

    if columns:
        active = np.column_stack(columns)
        multipliers, _ = nnls(active, -residual)
        residual = residual + active @ multipliers
    return float(np.max(np.abs(residual)))


@dataclass
class ScipyBackend:
    """Adapter over :func:`scipy.optimize.minimize` (SLSQP / trust-constr).

    The lowering:

    - ``bounds`` -> ``scipy.optimize.Bounds(lo, hi)``; every design vector is
      additionally clipped before it reaches a callback, so backend round-off
      cannot push a *modal solve* outside the box (AC-OPT-003, tolerance
      1e-12).  What the backend proposed is preserved in
      :attr:`~openfemlab.optimization.problem.OptimizationIterate.in_bounds`,
      so clipping hides no excursion from the audit.
    - each :class:`~openfemlab.optimization.problem.VectorConstraint` ->
      ``{"type": "ineq", "fun": -g, "jac": -dg}`` for SLSQP, or a
      ``NonlinearConstraint(g, -inf, 0)`` for trust-constr.
    - ``jac`` always set from ``problem.gradient`` — scipy's 2-point fallback
      is explicitly disabled (spec MS-5.2); a problem without gradient
      callbacks is rejected rather than silently differentiated.
    - a callback records one
      :class:`~openfemlab.optimization.problem.OptimizationIterate` per
      accepted step, starting with the initial design.
    - termination maps ``result.success``/``message`` onto
      :class:`OptimizationResult`, with :func:`_stationarity` as the KKT
      measure.  It is computed the same way for both methods so the number is
      comparable across backends, rather than reporting trust-constr's
      ``optimality`` against SLSQP's raw gradient norm — the latter does not go
      to zero at a constrained optimum and would not be a convergence measure.

    Parameters
    ----------
    method:
        ``"slsqp"`` (default, spec MS-5.2) or ``"trust-constr"``.
    tol, max_iter, seed:
        Termination tolerance, iteration cap, and the seed forwarded to any
        stochastic multistart wrapper (the search itself is single-start and
        deterministic, so ``seed`` only records provenance today).
    """

    method: str = "slsqp"
    tol: float = 1.0e-8
    max_iter: int = 100
    seed: int = 0
    options: dict = field(default_factory=dict)

    _METHODS = ("slsqp", "trust-constr")

    def __post_init__(self) -> None:
        method = self.method.lower()
        if method not in self._METHODS:
            raise OptimizationError(
                f"unknown scipy method {self.method!r}; expected one of {self._METHODS}"
            )
        self.method = method
        if self.tol <= 0.0:
            raise OptimizationError("tolerance must be positive")
        if self.max_iter < 1:
            raise OptimizationError("max_iter must be at least 1")

    def solve(self, problem: OptimizationProblem) -> OptimizationResult:
        """Minimize ``problem`` and report the termination state (spec MS-5.2)."""
        import scipy.sparse as sp
        from scipy.optimize import Bounds, NonlinearConstraint, minimize

        if problem.gradient is None:
            raise OptimizationError(
                "the problem carries no gradient callback; spec MS-5.2 forbids "
                "the backend from differentiating numerically because every "
                "evaluation is a modal solve. compile_sizing_problem always "
                "supplies at least the tracked finite-difference route"
            )

        gradient = problem.gradient
        names = _unique_names(problem.constraints)
        evaluations = 0

        def objective(x: np.ndarray) -> float:
            nonlocal evaluations
            evaluations += 1
            return float(problem.objective(problem.clip(x)))

        def objective_jac(x: np.ndarray) -> np.ndarray:
            return np.asarray(gradient(problem.clip(x)), dtype=float).ravel()

        def value_of(constraint: VectorConstraint, x: np.ndarray) -> float:
            return float(constraint.fun(problem.clip(x)))

        def jac_of(constraint: VectorConstraint, x: np.ndarray) -> np.ndarray:
            jacobian = _require_jacobian(constraint)
            return np.asarray(jacobian(problem.clip(x)), dtype=float).ravel()

        history: list[OptimizationIterate] = []

        def record(xk: np.ndarray, *_: object) -> None:
            proposed = np.asarray(xk, dtype=float).ravel()
            x = problem.clip(proposed)
            history.append(
                OptimizationIterate(
                    iteration=len(history),
                    x=x,
                    # Not the counting wrapper: the evaluator caches this point.
                    objective=float(problem.objective(x)),
                    max_violation=max(
                        (value_of(c, x) for c in problem.constraints), default=0.0
                    ),
                    in_bounds=problem.feasible(proposed, BOUND_TOL),
                )
            )

        lower, upper = problem.bounds
        bounds = Bounds(lower, upper, keep_feasible=True)
        record(problem.x0)

        if self.method == "slsqp":
            # SLSQP states g(x) >= 0, the problem states g(x) <= 0.
            constraints: Any = [
                {
                    "type": "ineq",
                    "fun": lambda x, c=c: -value_of(c, x),
                    "jac": lambda x, c=c: -jac_of(c, x),
                }
                for c in problem.constraints
            ]
            options = {"maxiter": self.max_iter, "ftol": self.tol, **self.options}
        else:
            # Constraint curvature is neglected (the usual SQP approximation):
            # only the objective keeps a quasi-Newton Hessian.  scipy's default
            # is a per-constraint BFGS, which degenerates on a constraint with a
            # constant jacobian -- and the canonical sizing constraint, a mass
            # budget, is exactly linear.  Neglecting it costs step quality, not
            # correctness, since the gradients driving the KKT test are exact.
            zero_hessian = sp.csr_matrix((problem.n_variables, problem.n_variables))
            constraints = [
                NonlinearConstraint(
                    lambda x, c=c: value_of(c, x),
                    -np.inf,
                    0.0,
                    jac=lambda x, c=c: jac_of(c, x).reshape(1, -1),
                    hess=lambda x, v: zero_hessian,
                )
                for c in problem.constraints
            ]
            # Only ``gtol`` (the KKT optimality tolerance) is the counterpart of
            # SLSQP's ``ftol``.  ``xtol`` is a trust-radius floor, and tying it
            # to a tight ``tol`` makes the run exhaust ``maxiter`` instead of
            # terminating.
            options = {"maxiter": self.max_iter, "gtol": self.tol, **self.options}

        raw = minimize(
            objective,
            problem.x0,
            method="SLSQP" if self.method == "slsqp" else "trust-constr",
            jac=objective_jac,
            bounds=bounds,
            constraints=constraints,
            options=options,
            callback=record,
        )

        x = problem.clip(raw.x)
        values = {name: value_of(c, x) for name, c in zip(names, problem.constraints, strict=True)}
        active = [name for name, value in values.items() if abs(value) <= ACTIVE_TOL]
        if hasattr(raw, "optimality"):
            # trust-constr carries its own KKT measure (spec MS-5.2 asks for the
            # one the backend reports).  Preferring it also avoids misreading an
            # interior-point run, which stops strictly inside the feasible set
            # and so has no constraint the local reconstruction would call active.
            stationarity = float(raw.optimality)
        else:
            stationarity = _stationarity(
                problem,
                x,
                objective_jac(x),
                [
                    jac_of(c, x)
                    for name, c in zip(names, problem.constraints, strict=True)
                    if values[name] >= -ACTIVE_TOL
                ],
            )
        return OptimizationResult(
            converged=bool(raw.success),
            message=str(raw.message),
            x=x,
            objective=float(problem.objective(x)),
            constraint_values=values,
            active_set=active,
            stationarity=stationarity,
            n_iterations=int(getattr(raw, "nit", len(history))),
            n_evaluations=evaluations,
            history=history,
            variables=dict(zip(problem.names, x.tolist(), strict=True)),
        )


#: Registered backend factories, keyed by the name accepted by
#: :func:`get_backend` and :meth:`OptimizationProblem.solve`.
BACKENDS: dict[str, type] = {
    "slsqp": ScipyBackend,
    "trust-constr": ScipyBackend,
}


def available_backends() -> list[str]:
    """Names accepted by :func:`get_backend`."""
    return sorted(BACKENDS)


def get_backend(name: str = "slsqp", **options: object) -> OptimizerBackend:
    """Instantiate a registered backend by name.

    scipy method names double as backend names, so ``get_backend("slsqp")``
    and ``get_backend("trust-constr")`` configure :class:`ScipyBackend`
    accordingly.  External optimizers register a factory in :data:`BACKENDS`.
    """
    key = name.lower()
    try:
        factory = BACKENDS[key]
    except KeyError:
        raise OptimizationError(
            f"unknown optimization backend {name!r}; available: {available_backends()}"
        ) from None
    if factory is ScipyBackend:
        options.setdefault("method", key)
    backend = factory(**options)
    if not isinstance(backend, OptimizerBackend):
        raise OptimizationError(
            f"backend {name!r} does not implement solve(problem) -> OptimizationResult"
        )
    return backend
