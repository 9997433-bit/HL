"""Pre-updating parameter diagnosis (MS-3.6).

Not every declared parameter is worth updating.  Two failure modes make an
updating run meaningless, and both are visible in the initial relative
sensitivity matrix ``S_0`` before a single iteration is spent:

* **No observability** — a column of ``S_0`` is numerically zero, so the
  targets carry no information about that parameter and the normal equations
  are singular in its direction.
* **Collinearity** — two columns point the same way, so only their combination
  is identifiable; the split between them is decided by noise.

Both are handled by freezing parameters rather than by silently regularising
them away: every frozen parameter appears in the report with the reason and
the number that triggered it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

__all__ = [
    "ParameterDiagnostic",
    "ParameterSelection",
    "select_parameters",
]

#: Reason codes attached to a diagnosed parameter.
SELECTED = "selected"
LOW_SENSITIVITY = "low_sensitivity"
COLLINEAR = "collinear"
ILL_CONDITIONED = "ill_conditioned"


@dataclass(frozen=True)
class ParameterDiagnostic:
    """Why one parameter was kept in — or frozen out of — the updating run."""

    name: str
    sensitivity_norm: float
    relative_norm: float
    selected: bool
    reason: str
    collinear_with: str | None = None
    max_cosine: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "sensitivity_norm": self.sensitivity_norm,
            "relative_norm": self.relative_norm,
            "selected": self.selected,
            "reason": self.reason,
            "collinear_with": self.collinear_with,
            "max_cosine": self.max_cosine,
        }


@dataclass
class ParameterSelection:
    """Outcome of the S3 parameter diagnosis."""

    diagnostics: list[ParameterDiagnostic] = field(default_factory=list)
    sensitivity: np.ndarray | None = None
    parameter_names: list[str] = field(default_factory=list)
    condition_number: float = float("inf")
    selected_condition_number: float = float("inf")
    settings: dict[str, Any] = field(default_factory=dict)

    @property
    def selected(self) -> list[str]:
        return [d.name for d in self.diagnostics if d.selected]

    @property
    def frozen(self) -> list[str]:
        return [d.name for d in self.diagnostics if not d.selected]

    def reason_for(self, name: str) -> str:
        for diagnostic in self.diagnostics:
            if diagnostic.name == name:
                return diagnostic.reason
        raise KeyError(f"no diagnostic for parameter {name!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "parameters": [d.to_dict() for d in self.diagnostics],
            "selected": self.selected,
            "frozen": self.frozen,
            "condition_number": self.condition_number,
            "selected_condition_number": self.selected_condition_number,
            "sensitivity": None if self.sensitivity is None else self.sensitivity.tolist(),
            "parameter_names": list(self.parameter_names),
            "settings": dict(self.settings),
        }

    def table(self) -> str:
        header = f"{'parameter':<20} {'|S_j|':>12} {'rel.':>8} {'kept':>6}  reason"
        lines = [header, "-" * len(header)]
        for d in self.diagnostics:
            reason = d.reason
            if d.collinear_with is not None:
                reason = f"{reason} with {d.collinear_with} (cos {d.max_cosine:.4f})"
            lines.append(
                f"{d.name:<20} {d.sensitivity_norm:12.4e} {d.relative_norm:8.3f} "
                f"{'yes' if d.selected else 'no':>6}  {reason}"
            )
        return "\n".join(lines)


def _condition_number(matrix: np.ndarray) -> float:
    if matrix.size == 0 or matrix.shape[1] == 0:
        return float("inf")
    singular = np.linalg.svd(matrix, compute_uv=False)
    if singular.size == 0 or singular[-1] <= 0.0:
        return float("inf")
    return float(singular[0] / singular[-1])


def select_parameters(
    sensitivity: np.ndarray,
    parameter_names: Sequence[str],
    *,
    collinearity_threshold: float = 0.99,
    low_sensitivity_ratio: float = 1.0e-3,
    max_condition: float = 1.0e6,
) -> ParameterSelection:
    """Diagnose ``S_0`` and pick the identifiable parameter subset.

    Columns are visited in decreasing norm (the observability ranking a QR with
    column pivoting would produce) and a column is kept unless it is
    numerically insensitive, nearly parallel to a column already kept, or would
    push the condition number of the retained subset past ``max_condition``.

    Parameters
    ----------
    sensitivity:
        ``(n_responses, n_parameters)`` **relative** sensitivity matrix
        ``∂z_i/∂θ_j``, columns already scaled by the parameter values.
    parameter_names:
        Column labels, in matrix order.
    """
    matrix = np.atleast_2d(np.asarray(sensitivity, dtype=float))
    names = [str(name) for name in parameter_names]
    if matrix.shape[1] != len(names):
        raise ValueError(
            f"sensitivity has {matrix.shape[1]} columns but {len(names)} parameter names"
        )
    if not 0.0 < collinearity_threshold <= 1.0:
        raise ValueError("collinearity_threshold must lie in (0, 1]")
    if low_sensitivity_ratio < 0.0:
        raise ValueError("low_sensitivity_ratio must be non-negative")

    norms = np.linalg.norm(matrix, axis=0)
    largest = float(norms.max()) if norms.size else 0.0
    relative = norms / largest if largest > 0.0 else np.zeros_like(norms)
    floor = low_sensitivity_ratio * largest

    order = sorted(range(len(names)), key=lambda j: (-norms[j], j))
    kept: list[int] = []
    diagnostics: dict[int, ParameterDiagnostic] = {}

    for j in order:
        if norms[j] <= floor or norms[j] == 0.0:
            diagnostics[j] = ParameterDiagnostic(
                name=names[j],
                sensitivity_norm=float(norms[j]),
                relative_norm=float(relative[j]),
                selected=False,
                reason=LOW_SENSITIVITY,
            )
            continue

        cosines = [
            (abs(float(matrix[:, j] @ matrix[:, k])) / (norms[j] * norms[k]), k) for k in kept
        ]
        best_cosine, partner = max(cosines, default=(0.0, -1))
        if kept and best_cosine > collinearity_threshold:
            diagnostics[j] = ParameterDiagnostic(
                name=names[j],
                sensitivity_norm=float(norms[j]),
                relative_norm=float(relative[j]),
                selected=False,
                reason=COLLINEAR,
                collinear_with=names[partner],
                max_cosine=float(best_cosine),
            )
            continue

        trial = [*kept, j]
        if len(trial) > 1 and _condition_number(matrix[:, trial]) > max_condition:
            diagnostics[j] = ParameterDiagnostic(
                name=names[j],
                sensitivity_norm=float(norms[j]),
                relative_norm=float(relative[j]),
                selected=False,
                reason=ILL_CONDITIONED,
                collinear_with=None if partner < 0 else names[partner],
                max_cosine=float(best_cosine),
            )
            continue

        kept = trial
        diagnostics[j] = ParameterDiagnostic(
            name=names[j],
            sensitivity_norm=float(norms[j]),
            relative_norm=float(relative[j]),
            selected=True,
            reason=SELECTED,
            max_cosine=float(best_cosine),
        )

    return ParameterSelection(
        diagnostics=[diagnostics[j] for j in range(len(names))],
        sensitivity=matrix,
        parameter_names=names,
        condition_number=_condition_number(matrix),
        selected_condition_number=_condition_number(matrix[:, sorted(kept)]),
        settings={
            "collinearity_threshold": collinearity_threshold,
            "low_sensitivity_ratio": low_sensitivity_ratio,
            "max_condition": max_condition,
        },
    )
