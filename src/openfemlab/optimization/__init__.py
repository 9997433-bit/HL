"""Optimization layer (L3): design optimization on validated models.

Thin, swappable abstraction over ``scipy.optimize`` so the updating loop and
design studies share one problem statement. Round 2 wires ``ModelUpdater``'s
regularized step through this interface; Round 3 adds DOE sampling and
response-surface surrogates for expensive objectives.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt

__all__ = ["OptimizationProblem"]


@dataclass(slots=True)
class OptimizationProblem:
    """Bound-constrained minimization problem statement.

    Attributes
    ----------
    objective:
        ``f(x) -> float`` on the normalized design vector.
    x0:
        Initial design, shape ``(n,)``.
    bounds:
        ``(lower, upper)`` arrays, each shape ``(n,)``.
    gradient:
        Optional analytic gradient ``g(x) -> (n,)``; finite differences
        otherwise.
    """

    objective: Callable[[npt.NDArray[np.float64]], float]
    x0: npt.NDArray[np.float64]
    bounds: tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]
    gradient: Callable[[npt.NDArray[np.float64]], npt.NDArray[np.float64]] | None = None
    options: dict = field(default_factory=dict)

    def solve(self) -> np.ndarray:
        """Run the configured backend (scipy L-BFGS-B default). Round 2."""
        raise NotImplementedError("optimization backend lands in Round 2")
