"""Pre-updating parameter diagnosis (MS-3.6).

Not every declared parameter is worth updating.  Two failure modes make an
updating run meaningless, and both are visible in the initial relative
sensitivity matrix ``S_0`` before a single iteration is spent:

* **No observability** — a column of ``S_0`` is numerically zero, so the
  targets carry no information about that parameter and the normal equations
  are singular in its direction.
* **Collinearity** — a column is reproduced by the ones already retained, so
  only the combination is identifiable; the split is decided by noise.

Collinearity is measured against the *span* of the retained columns, not
pairwise: the screen is a greedy QR with column pivoting (Businger–Golub) that
at every step admits the column carrying the largest component orthogonal to
what is already kept.  Pairwise cosines miss redundancy that only appears in
combination — ``S_c = S_a + S_b`` sits at cosine 0.71 to each of its two
parents yet adds nothing to their span — and the pivoted ranking orders
parameters by the information each one *adds* rather than by raw column norm.

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

#: Gap above the pairwise cosine at which ``table()`` also prints the span
#: cosine — below it the two numbers are the same measurement twice.
_SPAN_REPORT_TOL = 1.0e-6


@dataclass(frozen=True)
class ParameterDiagnostic:
    """Why one parameter was kept in — or frozen out of — the updating run.

    ``max_cosine`` is the largest *pairwise* cosine against a retained column
    and ``collinear_with`` names that column: the human-readable "which other
    parameter does this one look like".  The screen itself decides on
    ``independence`` — the fraction of the column's magnitude that survives
    projecting out the whole retained span — with ``subspace_cosine`` its
    angle-space counterpart.  For a lone redundant twin the pairwise and
    subspace numbers agree; when a column is only redundant in combination,
    ``subspace_cosine`` is the larger, and the one that triggered the freeze.
    """

    name: str
    sensitivity_norm: float
    relative_norm: float
    selected: bool
    reason: str
    collinear_with: str | None = None
    max_cosine: float = 0.0
    subspace_cosine: float = 0.0
    independence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "sensitivity_norm": self.sensitivity_norm,
            "relative_norm": self.relative_norm,
            "selected": self.selected,
            "reason": self.reason,
            "collinear_with": self.collinear_with,
            "max_cosine": self.max_cosine,
            "subspace_cosine": self.subspace_cosine,
            "independence": self.independence,
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
    #: Parameters in the order the pivoted QR visited them — the observability
    #: ranking, most informative first.  Columns rejected up front as
    #: insensitive never enter the pivoting and are absent.
    pivot_order: list[str] = field(default_factory=list)

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
            "pivot_order": list(self.pivot_order),
        }

    def table(self) -> str:
        header = f"{'parameter':<20} {'|S_j|':>12} {'rel.':>8} {'kept':>6}  reason"
        lines = [header, "-" * len(header)]
        for d in self.diagnostics:
            reason = d.reason
            if d.collinear_with is not None:
                detail = f"cos {d.max_cosine:.4f}"
                if d.subspace_cosine > d.max_cosine + _SPAN_REPORT_TOL:
                    detail = f"{detail}, span cos {d.subspace_cosine:.4f}"
                reason = f"{reason} with {d.collinear_with} ({detail})"
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


def _closest_column(
    matrix: np.ndarray, norms: np.ndarray, column: int, kept: list[int]
) -> tuple[float, int]:
    """Largest pairwise ``|cos|`` between ``column`` and a retained column."""
    best, partner = 0.0, -1
    for k in kept:
        cosine = abs(float(matrix[:, column] @ matrix[:, k])) / (norms[column] * norms[k])
        if cosine > best:
            best, partner = cosine, k
    return min(best, 1.0), partner


def select_parameters(
    sensitivity: np.ndarray,
    parameter_names: Sequence[str],
    *,
    collinearity_threshold: float = 0.99,
    low_sensitivity_ratio: float = 1.0e-3,
    max_condition: float = 1.0e6,
) -> ParameterSelection:
    """Diagnose ``S_0`` and pick the identifiable parameter subset.

    Columns whose norm falls below ``low_sensitivity_ratio`` of the largest are
    rejected up front as unobservable.  The rest go through a QR with column
    pivoting: at each step the pivot is the column with the largest component
    orthogonal to the span of the columns already retained, and it is kept
    unless that component is too small a fraction of the column itself (angle
    to the retained span above ``collinearity_threshold`` in cosine) or
    admitting it would push the retained subset past ``max_condition``.

    Screening against the span rather than pairwise is what lets the
    ``S_c = S_a + S_b`` family of redundancies be caught: no pair among the
    three is near-parallel, but the trio is rank two.

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

    diagnostics: dict[int, ParameterDiagnostic] = {}
    active: list[int] = []
    for j in range(len(names)):
        if norms[j] <= floor or norms[j] == 0.0:
            diagnostics[j] = ParameterDiagnostic(
                name=names[j],
                sensitivity_norm=float(norms[j]),
                relative_norm=float(relative[j]),
                selected=False,
                reason=LOW_SENSITIVITY,
                independence=0.0,
            )
        else:
            active.append(j)

    # The freeze test is "angle to the retained span is shallower than
    # ``collinearity_threshold``", but it is evaluated on the orthogonal
    # residual instead of the cosine: near collinearity the cosine crowds
    # against 1 and loses its significant digits, while the residual fraction
    # it is compared through stays well scaled all the way down to zero.
    independence_floor = float(np.sqrt(max(0.0, 1.0 - collinearity_threshold**2)))

    basis = np.zeros((matrix.shape[0], 0))
    residual = matrix.copy()
    kept: list[int] = []
    pivot_order: list[str] = []

    while active:
        # Businger-Golub pivot: the column adding the most that is genuinely new.
        residual_norms = np.linalg.norm(residual[:, active], axis=0)
        position = int(np.argmax(residual_norms))
        j = active.pop(position)
        pivot_order.append(names[j])

        orthogonal = float(residual_norms[position])
        independence = min(1.0, orthogonal / norms[j])
        projected = float(np.linalg.norm(basis.T @ matrix[:, j])) if kept else 0.0
        subspace_cosine = min(1.0, projected / norms[j])
        best_cosine, partner = _closest_column(matrix, norms, j, kept)

        common = {
            "name": names[j],
            "sensitivity_norm": float(norms[j]),
            "relative_norm": float(relative[j]),
            "max_cosine": float(best_cosine),
            "subspace_cosine": float(subspace_cosine),
            "independence": float(independence),
        }

        # ``orthogonal <= 0`` is the exactly-dependent case: there is no new
        # direction to extend the basis with, whatever the threshold says.
        if kept and (independence < independence_floor or orthogonal <= 0.0):
            diagnostics[j] = ParameterDiagnostic(
                **common,
                selected=False,
                reason=COLLINEAR,
                collinear_with=names[partner],
            )
            continue

        trial = [*kept, j]
        if len(trial) > 1 and _condition_number(matrix[:, trial]) > max_condition:
            diagnostics[j] = ParameterDiagnostic(
                **common,
                selected=False,
                reason=ILL_CONDITIONED,
                collinear_with=None if partner < 0 else names[partner],
            )
            continue

        kept = trial
        diagnostics[j] = ParameterDiagnostic(**common, selected=True, reason=SELECTED)

        # Re-orthogonalise the new direction against the basis before adding it
        # (one classical-Gram-Schmidt pass; the residual is already orthogonal
        # to machine precision, this keeps it there as the basis grows).
        direction = residual[:, j]
        if basis.shape[1]:
            direction = direction - basis @ (basis.T @ direction)
        length = float(np.linalg.norm(direction))
        if length <= 0.0:  # pragma: no cover - guarded by the check above
            continue
        basis = np.column_stack([basis, direction / length])
        residual = matrix - basis @ (basis.T @ matrix)

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
        pivot_order=pivot_order,
    )
