"""Method of Moving Asymptotes (MMA) for constrained topology updates."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

__all__ = ["MmaState", "create_mma_state", "mma_update"]


@dataclass
class MmaState:
    """Persistent MMA asymptote and history state across iterations."""

    xold1: np.ndarray
    xold2: np.ndarray
    low: np.ndarray
    upp: np.ndarray


def create_mma_state(x: np.ndarray) -> MmaState:
    """Initial asymptotes for a new MMA run."""
    x = np.asarray(x, dtype=float).reshape(-1)
    return MmaState(
        xold1=x.copy(),
        xold2=x.copy(),
        low=x.copy(),
        upp=x.copy(),
    )


def _build_coefficients(
    xval: np.ndarray,
    low: np.ndarray,
    upp: np.ndarray,
    gradient: np.ndarray,
    *,
    raa0: float = 1e-5,
) -> tuple[np.ndarray, np.ndarray]:
    """MMA separable approximation coefficients for one function."""
    gradient = np.asarray(gradient, dtype=float).reshape(-1)
    positive = gradient > 0.0
    negative = gradient < 0.0
    p = np.zeros_like(xval)
    q = np.zeros_like(xval)
    p[positive] = (upp[positive] - xval[positive]) ** 2 * gradient[positive]
    q[negative] = -((xval[negative] - low[negative]) ** 2) * gradient[negative]
    return np.maximum(p, raa0), np.maximum(q, raa0)


def _approximate(
    x: np.ndarray,
    *,
    value: float,
    p: np.ndarray,
    q: np.ndarray,
    low: np.ndarray,
    upp: np.ndarray,
) -> float:
    x = np.asarray(x, dtype=float)
    return float(value + np.sum(p / (upp - x) + q / (x - low)))


def mma_update(
    x: np.ndarray,
    xmin: np.ndarray,
    xmax: np.ndarray,
    state: MmaState,
    *,
    f0: float,
    df0dx: np.ndarray,
    constraints: list[tuple[float, np.ndarray]],
    move: float = 0.2,
) -> tuple[np.ndarray, MmaState]:
    """One MMA subproblem step for ``min f0(x)`` subject to ``f_i(x) <= 0``."""
    xval = np.asarray(x, dtype=float).reshape(-1)
    xmin = np.asarray(xmin, dtype=float).reshape(-1)
    xmax = np.asarray(xmax, dtype=float).reshape(-1)
    df0dx = np.asarray(df0dx, dtype=float).reshape(-1)
    n = xval.size
    m = len(constraints)
    if m == 0:
        raise ValueError("MMA requires at least one constraint")
    if df0dx.size != n:
        raise ValueError(f"expected {n} objective sensitivities, got {df0dx.size}")

    low = np.asarray(state.low, dtype=float).copy()
    upp = np.asarray(state.upp, dtype=float).copy()
    xold1 = np.asarray(state.xold1, dtype=float).copy()
    xold2 = np.asarray(state.xold2, dtype=float).copy()

    move = float(move)
    asyinit = 0.5
    asyincr = 1.2
    asydecr = 0.7

    if np.allclose(xold1, xval) and np.allclose(xold2, xval):
        low = xval - asyinit * (xmax - xmin)
        upp = xval + asyinit * (xmax - xmin)
    else:
        factor = np.ones(n, dtype=float)
        increase = (xval - xold1) * (xold1 - xold2) > 0.0
        decrease = (xval - xold1) * (xold1 - xold2) < 0.0
        factor[increase] = asyincr
        factor[decrease] = asydecr
        low = xval - factor * (xold1 - low)
        upp = xval + factor * (upp - xold1)
        low = np.minimum(low, xval - 0.01 * (xmax - xmin))
        upp = np.maximum(upp, xval + 0.01 * (xmax - xmin))

    alfa = np.maximum(xmin, xval - move * (xmax - xmin))
    beta = np.minimum(xmax, xval + move * (xmax - xmin))
    low = np.minimum(low, alfa)
    upp = np.maximum(upp, beta)

    p0, q0 = _build_coefficients(xval, low, upp, df0dx)
    approx_constraints: list[tuple[float, np.ndarray, np.ndarray]] = []
    for value, gradient in constraints:
        gradient = np.asarray(gradient, dtype=float).reshape(-1)
        if gradient.size != n:
            raise ValueError(
                f"constraint gradient has {gradient.size} entries, expected {n}"
            )
        p_i, q_i = _build_coefficients(xval, low, upp, gradient)
        approx_constraints.append((float(value), p_i, q_i))

    margin = 1e-6 * (beta - alfa + 1.0)
    alfa_safe = alfa + margin
    beta_safe = beta - margin

    def objective(candidate: np.ndarray) -> float:
        return _approximate(candidate, value=f0, p=p0, q=q0, low=low, upp=upp)

    def objective_jac(candidate: np.ndarray) -> np.ndarray:
        candidate = np.asarray(candidate, dtype=float)
        return p0 / (upp - candidate) ** 2 - q0 / (candidate - low) ** 2

    scipy_constraints = []
    for value, p_i, q_i in approx_constraints:
        def constraint_fun(
            candidate: np.ndarray,
            *,
            value=value,
            p_i=p_i,
            q_i=q_i,
        ) -> float:
            return -_approximate(candidate, value=value, p=p_i, q=q_i, low=low, upp=upp)

        def constraint_jac(
            candidate: np.ndarray,
            *,
            p_i=p_i,
            q_i=q_i,
        ) -> np.ndarray:
            candidate = np.asarray(candidate, dtype=float)
            return -(p_i / (upp - candidate) ** 2 - q_i / (candidate - low) ** 2)

        scipy_constraints.append(
            {"type": "ineq", "fun": constraint_fun, "jac": constraint_jac}
        )

    bounds = list(zip(alfa_safe, beta_safe, strict=True))
    result = minimize(
        objective,
        xval,
        jac=objective_jac,
        bounds=bounds,
        constraints=scipy_constraints,
        method="SLSQP",
        options={"ftol": 1e-9, "maxiter": 200, "disp": False},
    )
    candidate = np.asarray(result.x, dtype=float) if result.x is not None else xval
    if not np.all(np.isfinite(candidate)):
        candidate = xval
    xnew = np.maximum(xmin, np.minimum(xmax, candidate))
    new_state = MmaState(xold1=xval.copy(), xold2=xold1.copy(), low=low, upp=upp)
    return xnew, new_state
