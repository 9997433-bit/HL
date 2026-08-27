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

``docs/OPTIMIZATION.md`` section 7 states the same mapping in prose.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

import numpy as np

from ..exceptions import OptimizationError
from .problem import OptimizationIterate, OptimizationProblem, OptimizationResult

__all__ = [
    "OptimizerBackend",
    "ScipyBackend",
    "kkt_residual",
    "get_backend",
    "available_backends",
]

#: Tolerance of the AC-OPT-003 bound audit; also the width of the projection
#: that absorbs a backend's round-off before an evaluation is requested.
BOUND_TOLERANCE = 1.0e-12


@runtime_checkable
class OptimizerBackend(Protocol):
    """Anything that can minimize a lowered :class:`OptimizationProblem`."""

    def solve(self, problem: OptimizationProblem) -> OptimizationResult: ...


def kkt_residual(
    objective_gradient: np.ndarray,
    constraint_gradients: dict[str, np.ndarray],
    x: np.ndarray,
    bounds: tuple[np.ndarray, np.ndarray],
    *,
    tolerance: float = 1.0e-9,
) -> float:
    """First-order stationarity measure at ``x``.

    Solves the non-negative least-squares problem for the multipliers of the
    active inequalities and the active bounds,

    ``min_{lambda, mu >= 0} || df/dx + sum_k lambda_k dg_k/dx + mu_bounds ||``,

    and returns the residual norm relative to the gradient scale.  Zero means
    the first-order KKT conditions hold to working precision.  SLSQP and
    trust-constr report incomparable diagnostics of their own, so the
    termination report uses this measure for both.

    ``constraint_gradients`` must contain only the constraints that are
    *active* at ``x``.  Complementary slackness (``lambda_k g_k = 0``) forbids
    a nonzero multiplier on a strictly satisfied constraint, so admitting one
    would hand the solve a column it may not use and could certify a point as
    stationary when it is not.
    """
    from scipy.optimize import nnls

    g = np.asarray(objective_gradient, dtype=float).ravel()
    lo, hi = bounds
    columns = [np.asarray(dg, dtype=float).ravel() for dg in constraint_gradients.values()]
    for i in range(g.size):
        unit = np.zeros(g.size)
        if x[i] >= hi[i] - tolerance:
            unit[i] = 1.0
        elif x[i] <= lo[i] + tolerance:
            unit[i] = -1.0
        else:
            continue
        columns.append(unit)

    scale = max(float(np.linalg.norm(g)), 1.0)
    if not columns:
        return float(np.linalg.norm(g)) / scale
    _, residual = nnls(np.column_stack(columns), -g)
    return float(residual) / scale


@dataclass
class ScipyBackend:
    """Adapter over :func:`scipy.optimize.minimize` (SLSQP / trust-constr).

    The lowering:

    - ``bounds`` -> ``scipy.optimize.Bounds(lo, hi, keep_feasible=True)``;
      every point is additionally clipped before it reaches the model, so
      round-off cannot escape the box (AC-OPT-003, tolerance 1e-12).
    - each :class:`~openfemlab.optimization.problem.VectorConstraint` ->
      ``{"type": "ineq", "fun": -g, "jac": -dg}`` for SLSQP, or a
      ``NonlinearConstraint(g, -inf, 0)`` for trust-constr.
    - ``jac`` always set from ``problem.gradient`` — scipy's 2-point fallback
      is explicitly disabled (spec MS-5.2).
    - a callback records :class:`~openfemlab.optimization.problem.
      OptimizationIterate` rows for the bound and convergence audit.
    - termination maps scipy's ``success``/``message`` onto
      :class:`OptimizationResult`, with :func:`kkt_residual` as the
      method-independent ``stationarity``.
    - under trust-constr, constraint curvature is neglected (the usual SQP
      approximation) because scipy's per-constraint BFGS default degenerates
      on the linear constraints that dominate sizing work.

    Parameters
    ----------
    method:
        ``"slsqp"`` (default, spec MS-5.2) or ``"trust-constr"``.
    tol, max_iter, seed:
        Termination tolerance, iteration cap, and the seed forwarded to any
        stochastic multistart wrapper (single-start today).
    active_tol:
        A constraint counts as active when ``|g| <= active_tol``.
    options:
        Extra options forwarded to ``scipy.optimize.minimize``.  Under
        trust-constr a ``"hess"`` entry is lifted out and passed as the
        *objective* Hessian — the escape hatch for a linear objective, where
        the exact Hessian is zero and a quasi-Newton approximation has nothing
        to learn from it.  SLSQP is first order and ignores it.
    """

    method: str = "slsqp"
    tol: float = 1.0e-8
    max_iter: int = 100
    seed: int = 0
    active_tol: float = 1.0e-6
    options: dict = field(default_factory=dict)

    _METHODS = ("slsqp", "trust-constr")
    _SCIPY_NAMES = {"slsqp": "SLSQP", "trust-constr": "trust-constr"}

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
        """Minimize ``problem`` and report the termination state."""
        from scipy import sparse
        from scipy.optimize import Bounds, NonlinearConstraint, minimize

        if problem.gradient is None:
            raise OptimizationError(
                "the problem carries no gradient callback; scipy would fall back to "
                "internal finite differences, which spec MS-5.2 forbids"
            )

        lo, hi = problem.bounds
        counters = {"evaluations": 0}
        cache: dict[bytes, float] = {}
        history: list[OptimizationIterate] = []

        def project(x: np.ndarray) -> np.ndarray:
            return np.clip(np.asarray(x, dtype=float).ravel(), lo, hi)

        def objective(x: np.ndarray) -> float:
            projected = project(x)
            counters["evaluations"] += 1
            value = float(problem.objective(projected))
            cache[projected.tobytes()] = value
            return value

        def objective_gradient(x: np.ndarray) -> np.ndarray:
            return np.asarray(problem.gradient(project(x)), dtype=float).ravel()

        def record(xk: np.ndarray, *_: object) -> None:
            raw = np.asarray(xk, dtype=float).ravel().copy()
            projected = project(raw)
            value = cache.get(projected.tobytes())
            if value is None:
                value = objective(projected)
            violations = [float(c.fun(projected)) for c in problem.constraints]
            history.append(
                OptimizationIterate(
                    iteration=len(history) + 1,
                    x=raw,
                    objective=value,
                    max_violation=max(violations) if violations else 0.0,
                    in_bounds=problem.feasible(raw, tolerance=BOUND_TOLERANCE),
                )
            )

        if self.method == "slsqp":
            constraints: Any = [
                {
                    "type": "ineq",
                    "fun": _negated(c.fun, project),
                    "jac": _negated_jac(c.jac, project),
                }
                for c in problem.constraints
            ]
        else:
            # Constraint curvature is neglected -- the usual SQP approximation.
            # scipy's default is a per-constraint BFGS, which degenerates when
            # the jacobian is constant, and the canonical sizing constraint (a
            # mass budget) is exactly linear in the sizing scalars: with the
            # default, the 2-variable payload-placement problem exhausts
            # maxiter while emitting a warning per evaluation, where a zero
            # constraint Hessian converges in under 30 iterations.  This costs
            # step quality, not correctness -- the gradients that drive the KKT
            # test are exact either way.
            zero_hessian = sparse.csr_matrix((problem.n_variables, problem.n_variables))
            constraints = [
                NonlinearConstraint(
                    _projected(c.fun, project),
                    -np.inf,
                    0.0,
                    jac=_projected_jac(c.jac, project),
                    hess=lambda x, v: zero_hessian,
                )
                for c in problem.constraints
            ]

        options = {"maxiter": self.max_iter, **self.options}
        # trust-constr also needs a Hessian for the objective and has no second
        # derivatives to work from, so it approximates one by quasi-Newton.  A
        # minimum-mass objective is linear, which scipy reports as
        # "delta_grad == 0.0"; the fix is the exact zero Hessian, and only the
        # caller can assert that.  SLSQP is first order and has no use for one.
        hessian = options.pop("hess", None)
        extra = (
            {"hess": hessian}
            if hessian is not None and self.method != "slsqp"
            else {}
        )

        raw = minimize(
            objective,
            problem.x0,
            method=self._SCIPY_NAMES[self.method],
            jac=objective_gradient,
            bounds=Bounds(lo, hi, keep_feasible=True),
            constraints=constraints,
            tol=self.tol,
            options=options,
            callback=record,
            **extra,
        )

        x = project(raw.x)
        values = problem.constraint_values(x)
        gradients = {
            name: np.asarray(c.jac(x), dtype=float).ravel()
            for name, c in zip(problem.constraint_names(), problem.constraints, strict=True)
            if c.jac is not None and values[name] >= -self.active_tol
        }
        return OptimizationResult(
            converged=bool(raw.success) and all(v <= self.active_tol for v in values.values()),
            message=str(raw.message),
            x=x,
            objective=float(problem.objective(x)),
            constraint_values=values,
            active_set=[name for name, v in values.items() if abs(v) <= self.active_tol],
            stationarity=kkt_residual(objective_gradient(x), gradients, x, problem.bounds),
            n_iterations=int(getattr(raw, "nit", len(history))),
            n_evaluations=counters["evaluations"],
            history=history,
            variables=dict(zip(problem.names, x.tolist(), strict=True)),
        )


def _projected(
    fun: Callable[[np.ndarray], float], project: Callable[[np.ndarray], np.ndarray]
) -> Callable[[np.ndarray], float]:
    return lambda x: float(fun(project(x)))


def _projected_jac(
    jac: Callable[[np.ndarray], np.ndarray] | None,
    project: Callable[[np.ndarray], np.ndarray],
) -> Callable[[np.ndarray], np.ndarray]:
    if jac is None:
        raise OptimizationError(
            "a constraint without a jacobian would force scipy to differentiate "
            "internally, which spec MS-5.2 forbids"
        )
    return lambda x: np.asarray(jac(project(x)), dtype=float).ravel()


def _negated(
    fun: Callable[[np.ndarray], float], project: Callable[[np.ndarray], np.ndarray]
) -> Callable[[np.ndarray], float]:
    """SLSQP states inequalities as ``g(x) >= 0``; the problem states ``g(x) <= 0``."""
    return lambda x: -float(fun(project(x)))


def _negated_jac(
    jac: Callable[[np.ndarray], np.ndarray] | None,
    project: Callable[[np.ndarray], np.ndarray],
) -> Callable[[np.ndarray], np.ndarray]:
    projected = _projected_jac(jac, project)
    return lambda x: -np.asarray(projected(x), dtype=float).ravel()


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
