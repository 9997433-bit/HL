"""Vector-level problem statement and result types consumed by the backends.

The structural layer (:mod:`~openfemlab.optimization.sizing`) lowers models,
design spaces and responses into this plain bound-constrained NLP over the
design vector::

    min_x  f(x)
    s.t.   g_k(x) <= 0        k = 1..m      (standardized inequality form)
           lo <= x <= hi

Backends (:mod:`~openfemlab.optimization.backends`) see nothing but this —
no FE concepts leak below this line, which is what makes the backend swappable
(scipy today, external optimizers later, per the architecture extension
points).  Every callable receives the design vector; gradients are design-
space gradients (the physical-to-design chain rule is applied during
lowering).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt

from ..exceptions import OptimizationError

__all__ = [
    "VectorConstraint",
    "OptimizationProblem",
    "OptimizationIterate",
    "OptimizationResult",
]

Vector = npt.NDArray[np.float64]
ScalarFn = Callable[[Vector], float]
GradientFn = Callable[[Vector], Vector]


@dataclass
class VectorConstraint:
    """One standardized scalar inequality ``fun(x) <= 0`` with optional jacobian."""

    fun: ScalarFn
    jac: GradientFn | None = None
    name: str = "g"


@dataclass
class OptimizationProblem:
    """Bound-constrained minimization problem over the design vector.

    Attributes
    ----------
    objective:
        ``f(x) -> float`` on the design vector.
    x0:
        Initial design, shape ``(n,)``; must satisfy the bounds.
    bounds:
        ``(lower, upper)`` arrays, each shape ``(n,)``.  Hard constraints:
        backends must never evaluate outside the box (AC-OPT-003).
    gradient:
        Analytic design-space gradient ``df/dx``; ``None`` only for problems
        lowered without any gradient route (the compiler always supplies at
        least the tracked finite-difference fallback).
    constraints:
        Standardized inequalities ``g_k(x) <= 0``.
    names:
        Design variable names, for reports.
    options:
        Backend-specific settings (tolerances, iteration limits, seeds).
    """

    objective: ScalarFn
    x0: Vector
    bounds: tuple[Vector, Vector]
    gradient: GradientFn | None = None
    constraints: list[VectorConstraint] = field(default_factory=list)
    names: list[str] = field(default_factory=list)
    options: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.x0 = np.asarray(self.x0, dtype=float).ravel()
        lo = np.asarray(self.bounds[0], dtype=float).ravel()
        hi = np.asarray(self.bounds[1], dtype=float).ravel()
        n = self.x0.size
        if lo.size != n or hi.size != n:
            raise OptimizationError(
                f"bounds ({lo.size}, {hi.size}) do not match {n} design variables"
            )
        if np.any(lo > hi):
            raise OptimizationError("lower bounds exceed upper bounds")
        if np.any(self.x0 < lo) or np.any(self.x0 > hi):
            raise OptimizationError("initial design violates the box bounds")
        self.bounds = (lo, hi)
        if not self.names:
            self.names = [f"x{k}" for k in range(n)]

    @property
    def n_variables(self) -> int:
        return int(self.x0.size)

    def clip(self, x: Vector) -> Vector:
        """Project a design vector onto the box bounds."""
        return np.clip(np.asarray(x, dtype=float).ravel(), *self.bounds)

    def feasible(self, x: Vector, tolerance: float = 1.0e-12) -> bool:
        """Bound feasibility of a point (the AC-OPT-003 iterate contract)."""
        x = np.asarray(x, dtype=float).ravel()
        lo, hi = self.bounds
        return bool(np.all(x >= lo - tolerance) and np.all(x <= hi + tolerance))

    def solve(self, backend: str = "slsqp", **options: object) -> OptimizationResult:
        """Run a registered backend on this problem.

        Round 1 registers the scipy backend as a documented stub; the wired
        implementation lands with Round 2 (GAP-12).
        """
        from .backends import get_backend

        return get_backend(backend, **{**self.options, **options}).solve(self)


@dataclass
class OptimizationIterate:
    """One accepted iterate of an optimization run (backend callback record)."""

    iteration: int
    x: Vector
    objective: float
    max_violation: float = 0.0
    in_bounds: bool = True


@dataclass
class OptimizationResult:
    """Termination report of an optimization run (spec MS-5.2).

    Attributes
    ----------
    converged:
        Whether the backend reported successful termination.
    message:
        Backend termination message.
    x:
        Final design vector.
    objective:
        Objective value at ``x``.
    constraint_values:
        Standardized ``g_k(x)`` at the solution, keyed by constraint name.
    active_set:
        Names of constraints active at the solution (``|g| <= active_tol``).
    stationarity:
        KKT/stationarity measure as reported by the backend (NaN when the
        backend provides none).
    n_iterations, n_evaluations, n_modal_solves:
        Iteration and cost counters; ``n_modal_solves`` counts actual
        eigensolves, the dominant expense.
    history:
        Accepted iterates, in order (basis of the AC-OPT-003 bound audit).
    variables:
        Final design values keyed by variable name.
    """

    converged: bool
    message: str
    x: Vector
    objective: float
    constraint_values: dict[str, float] = field(default_factory=dict)
    active_set: list[str] = field(default_factory=list)
    stationarity: float = float("nan")
    n_iterations: int = 0
    n_evaluations: int = 0
    n_modal_solves: int = 0
    history: list[OptimizationIterate] = field(default_factory=list)
    variables: dict[str, float] = field(default_factory=dict)

    @property
    def max_violation(self) -> float:
        """Largest standardized constraint value at the solution (<= 0 is feasible)."""
        if not self.constraint_values:
            return 0.0
        return max(self.constraint_values.values())

    def report(self) -> str:
        lines = [
            f"converged    : {self.converged} ({self.message})",
            f"objective    : {self.objective:.6e}",
            f"iterations   : {self.n_iterations} "
            f"({self.n_modal_solves} modal solves, {self.n_evaluations} evaluations)",
            f"stationarity : {self.stationarity:.3e}",
            f"active set   : {', '.join(self.active_set) if self.active_set else '(none)'}",
        ]
        if self.variables:
            width = max(len(name) for name in self.variables)
            lines.append("design variables:")
            lines.extend(
                f"  {name:<{width}} = {value:.6g}" for name, value in self.variables.items()
            )
        return "\n".join(lines)

    def __str__(self) -> str:  # pragma: no cover - convenience only
        return self.report()
