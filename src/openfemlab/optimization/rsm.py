"""Quadratic response-surface models for screening and surrogate optimization."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from ..exceptions import OptimizationError

__all__ = ["QuadraticRSM", "fit_quadratic_rsm"]


def _feature_row(sample: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    row = np.asarray(sample, dtype=float).reshape(1, -1)
    n_vars = row.shape[1]
    constant = np.ones((1, 1), dtype=float)
    linear = row
    quadratics: list[npt.NDArray[np.float64]] = []
    for i in range(n_vars):
        for j in range(i, n_vars):
            quadratics.append((row[:, i] * row[:, j]).reshape(1, 1))
    if quadratics:
        return np.hstack([constant, linear, *quadratics])[0]
    return np.hstack([constant, linear])[0]


def _design_matrix(samples: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    samples = np.asarray(samples, dtype=float)
    if samples.ndim != 2:
        raise OptimizationError("RSM samples must be a 2-D array")
    n_samples, n_vars = samples.shape
    if n_samples < 1 + n_vars + n_vars * (n_vars + 1) // 2:
        raise OptimizationError(
            "quadratic RSM is under-determined; add more design samples "
            f"(need at least {1 + n_vars + n_vars * (n_vars + 1) // 2}, got {n_samples})"
        )
    rows = [_feature_row(samples[index]) for index in range(n_samples)]
    return np.vstack(rows)


@dataclass(frozen=True, slots=True)
class QuadraticRSM:
    """Least-squares quadratic surrogate ``y(x) = beta^T phi(x)``."""

    coefficients: npt.NDArray[np.float64]
    variable_names: tuple[str, ...]
    r_squared: float
    rmse: float

    @property
    def num_variables(self) -> int:
        return len(self.variable_names)

    def features(self, sample: npt.ArrayLike) -> npt.NDArray[np.float64]:
        row = np.asarray(sample, dtype=float).reshape(1, -1)
        if row.shape[1] != self.num_variables:
            raise OptimizationError(
                f"expected {self.num_variables} design variables, got {row.shape[1]}"
            )
        return _feature_row(row)

    def predict(self, sample: npt.ArrayLike) -> float:
        return float(self.features(sample) @ self.coefficients)

    def gradient(self, sample: npt.ArrayLike) -> npt.NDArray[np.float64]:
        x = np.asarray(sample, dtype=float).reshape(-1)
        n_vars = self.num_variables
        beta = self.coefficients
        grad = beta[1 : 1 + n_vars].copy()
        offset = 1 + n_vars
        for i in range(n_vars):
            for j in range(i, n_vars):
                coeff = beta[offset]
                if i == j:
                    grad[i] += 2.0 * coeff * x[i]
                else:
                    grad[i] += coeff * x[j]
                    grad[j] += coeff * x[i]
                offset += 1
        return grad

    def to_dict(self) -> dict[str, object]:
        return {
            "type": "quadratic_rsm",
            "variable_names": list(self.variable_names),
            "coefficients": self.coefficients.tolist(),
            "r_squared": self.r_squared,
            "rmse": self.rmse,
        }


def fit_quadratic_rsm(
    samples: npt.ArrayLike,
    responses: npt.ArrayLike,
    *,
    variable_names: Sequence[str] | None = None,
) -> QuadraticRSM:
    """Fit a quadratic polynomial response surface by ordinary least squares."""
    design_samples = np.asarray(samples, dtype=float)
    y = np.asarray(responses, dtype=float).reshape(-1)
    if design_samples.shape[0] != y.size:
        raise OptimizationError("sample and response counts must match")
    n_vars = design_samples.shape[1]
    names = (
        tuple(variable_names)
        if variable_names is not None
        else tuple(f"x{i + 1}" for i in range(n_vars))
    )
    if len(names) != n_vars:
        raise OptimizationError("variable_names length must match sample width")
    matrix = _design_matrix(design_samples)
    coefficients, residuals, rank, _ = np.linalg.lstsq(matrix, y, rcond=None)
    if rank < matrix.shape[1]:
        raise OptimizationError("quadratic RSM design matrix is rank deficient")
    predicted = matrix @ coefficients
    ss_res = float(np.sum((y - predicted) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r_squared = 1.0 if ss_tot == 0.0 else 1.0 - ss_res / ss_tot
    rmse = float(np.sqrt(ss_res / max(y.size - matrix.shape[1], 1)))
    return QuadraticRSM(
        coefficients=coefficients,
        variable_names=names,
        r_squared=r_squared,
        rmse=rmse,
    )
