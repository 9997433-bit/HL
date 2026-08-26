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

``ScipyBackend.solve`` is the single Round 1 stub in this package: the mapping
is specified below and in ``docs/OPTIMIZATION.md``; the wired implementation
is a Round 2 deliverable (GAP-12), gated by AC-OPT-002 on the reference
spring-mass sizing problem.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ..exceptions import OptimizationError
from .problem import OptimizationProblem, OptimizationResult

__all__ = ["OptimizerBackend", "ScipyBackend", "get_backend", "available_backends"]


@runtime_checkable
class OptimizerBackend(Protocol):
    """Anything that can minimize a lowered :class:`OptimizationProblem`."""

    def solve(self, problem: OptimizationProblem) -> OptimizationResult: ...


@dataclass
class ScipyBackend:
    """Adapter over :func:`scipy.optimize.minimize` (SLSQP / trust-constr).

    Planned lowering (Round 2):

    - ``bounds`` -> ``scipy.optimize.Bounds(lo, hi)``; iterates additionally
      clipped in the objective wrapper so SLSQP round-off cannot escape the
      box (AC-OPT-003, tolerance 1e-12).
    - each :class:`~openfemlab.optimization.problem.VectorConstraint` ->
      ``{"type": "ineq", "fun": -g, "jac": -dg}`` for SLSQP, or a
      ``NonlinearConstraint(g, -inf, 0)`` for trust-constr.
    - ``jac`` always set from ``problem.gradient`` — scipy's 2-point fallback
      is explicitly disabled (spec MS-5.2).
    - a callback records :class:`~openfemlab.optimization.problem.
      OptimizationIterate` rows and the modal-solve counter of the evaluator.
    - termination maps ``result.status/message`` onto
      :class:`OptimizationResult` with the KKT measure trust-constr reports
      (``optimality``) or SLSQP's final gradient norm as ``stationarity``.

    Parameters
    ----------
    method:
        ``"slsqp"`` (default, spec MS-5.2) or ``"trust-constr"``.
    tol, max_iter, seed:
        Termination tolerance, iteration cap, and the seed forwarded to any
        stochastic multistart wrapper (single-start in Round 2).
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
        """Minimize the problem.  Round 1 stub — wired in Round 2 (GAP-12)."""
        raise NotImplementedError(
            "ScipyBackend.solve is the Round 2 deliverable of GAP-12: the "
            "scipy.optimize.minimize mapping is specified in "
            "docs/OPTIMIZATION.md section 7 and in this class's docstring, and "
            "is gated by AC-OPT-002/003 before it can land"
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
