"""Validation gates and held-out targets (MS-4.2, MS-4.1).

The gates are the contract a corrected model has to satisfy before the
pipeline reports ``PASS``: shape agreement (MAC), frequency agreement, a
minimum number of correlated modes, parameter plausibility, and — when the
caller reserved targets — the held-out check that separates a genuinely
corrected model from one that was merely fitted to its own training data.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

__all__ = [
    "GateResult",
    "HoldoutSpec",
    "ValidationGates",
    "evaluate_gates",
    "gates_passed",
]

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..correlation.pairing import ModePairing
    from ..correlation.summary import CorrelationSummary
    from ..updating.parameters import ParameterSet


@dataclass(frozen=True)
class ValidationGates:
    """Acceptance limits evaluated at S6.

    Defaults follow MS-4.2; ``freq_tolerance_pct`` is typically relaxed to 2 %
    for noisy measurements.
    """

    mac_min: float = 0.95
    freq_tolerance_pct: float = 1.0
    min_pairs: int = 3
    pairing_mac_min: float = 0.5
    parameter_change_warning_pct: float = 50.0
    holdout_mac_min: float = 0.9
    require_holdout_improvement: bool = True

    def __post_init__(self) -> None:
        if not 0.0 <= self.mac_min <= 1.0:
            raise ValueError("mac_min must lie in [0, 1]")
        if not 0.0 <= self.holdout_mac_min <= 1.0:
            raise ValueError("holdout_mac_min must lie in [0, 1]")
        if self.freq_tolerance_pct < 0.0:
            raise ValueError("freq_tolerance_pct must be non-negative")
        if self.min_pairs < 1:
            raise ValueError("min_pairs must be at least 1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "mac_min": self.mac_min,
            "freq_tolerance_pct": self.freq_tolerance_pct,
            "min_pairs": self.min_pairs,
            "pairing_mac_min": self.pairing_mac_min,
            "parameter_change_warning_pct": self.parameter_change_warning_pct,
            "holdout_mac_min": self.holdout_mac_min,
            "require_holdout_improvement": self.require_holdout_improvement,
        }


@dataclass(frozen=True)
class HoldoutSpec:
    """Targets reserved from the updating residuals and checked at S6.

    Parameters
    ----------
    modes:
        Test-mode indices excluded from the S4 residuals.
    highest_paired:
        Reserve this many of the highest-frequency *paired* test modes, on top
        of ``modes``.  The highest mode is the usual choice: it is the one an
        over-parameterised fit distorts first.
    channels:
        Sensor channel indices excluded from the S4 shape residuals (they are
        given zero weight, so the MAC ignores them).
    """

    modes: tuple[int, ...] = ()
    highest_paired: int = 0
    channels: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "modes", tuple(sorted({int(i) for i in self.modes})))
        object.__setattr__(self, "channels", tuple(sorted({int(i) for i in self.channels})))
        if self.highest_paired < 0:
            raise ValueError("highest_paired must be non-negative")
        if any(index < 0 for index in self.modes):
            raise ValueError("held-out mode indices must be non-negative")
        if any(index < 0 for index in self.channels):
            raise ValueError("held-out channel indices must be non-negative")

    @property
    def is_empty(self) -> bool:
        return not self.modes and not self.channels and self.highest_paired == 0

    def resolve_modes(self, pairing: ModePairing) -> tuple[int, ...]:
        """Test-mode indices to reserve, given the baseline pairing.

        ``highest_paired`` is resolved against the paired modes ordered by test
        frequency, so the reservation is stable whatever order the pairing
        returns its entries in.
        """
        reserved = set(self.modes)
        if self.highest_paired:
            ordered = sorted(
                pairing.pairs,
                key=lambda pair: (
                    -float("inf") if pair.test_frequency is None else pair.test_frequency,
                    pair.test_index,
                ),
            )
            for pair in ordered[-self.highest_paired :]:
                reserved.add(int(pair.test_index))
        return tuple(sorted(reserved))

    def to_dict(self) -> dict[str, Any]:
        return {
            "modes": list(self.modes),
            "highest_paired": self.highest_paired,
            "channels": list(self.channels),
        }


@dataclass(frozen=True)
class GateResult:
    """Outcome of a single acceptance check.

    ``severity`` distinguishes the gates that decide PASS/FAIL (``"error"``)
    from the plausibility checks that only annotate the report (``"warning"``).
    """

    name: str
    passed: bool
    value: float | None = None
    limit: float | None = None
    message: str = ""
    severity: str = "error"
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def is_blocking(self) -> bool:
        return self.severity == "error" and not self.passed

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "value": self.value,
            "limit": self.limit,
            "message": self.message,
            "severity": self.severity,
            "details": dict(self.details),
        }


def _mac_gate(final: CorrelationSummary, gates: ValidationGates) -> GateResult:
    value = final.min_mac
    passed = final.n_paired > 0 and value >= gates.mac_min
    return GateResult(
        name="mac",
        passed=passed,
        value=value,
        limit=gates.mac_min,
        message=f"min MAC {value:.4f} vs limit {gates.mac_min:.4f}",
        details={"mean_mac": final.mean_mac},
    )


def _frequency_gate(final: CorrelationSummary, gates: ValidationGates) -> GateResult:
    value = final.max_abs_freq_error_pct
    passed = final.n_paired > 0 and value <= gates.freq_tolerance_pct
    return GateResult(
        name="frequency",
        passed=passed,
        value=value,
        limit=gates.freq_tolerance_pct,
        message=f"max |Δf| {value:.4f} % vs limit {gates.freq_tolerance_pct:.4f} %",
        details={"mean_abs_freq_error_pct": final.mean_abs_freq_error_pct},
    )


def _pair_count_gate(final: CorrelationSummary, gates: ValidationGates) -> GateResult:
    value = float(final.n_paired)
    return GateResult(
        name="paired_modes",
        passed=final.n_paired >= gates.min_pairs,
        value=value,
        limit=float(gates.min_pairs),
        message=f"{final.n_paired} paired modes vs minimum {gates.min_pairs}",
    )


def _parameter_gates(
    parameters: ParameterSet | None, gates: ValidationGates
) -> list[GateResult]:
    if parameters is None:
        return []
    out_of_bounds = [
        p.name for p in parameters if not (p.lower - 1e-12 <= p.value <= p.upper + 1e-12)
    ]
    results = [
        GateResult(
            name="parameter_bounds",
            passed=not out_of_bounds,
            message=(
                "all parameters within bounds"
                if not out_of_bounds
                else f"parameters outside bounds: {out_of_bounds}"
            ),
            details={"violations": out_of_bounds},
        )
    ]
    implausible = {
        p.name: p.change_pct
        for p in parameters
        if abs(p.change_pct) > gates.parameter_change_warning_pct
    }
    largest = max((abs(p.change_pct) for p in parameters), default=0.0)
    results.append(
        GateResult(
            name="parameter_plausibility",
            passed=not implausible,
            value=largest,
            limit=gates.parameter_change_warning_pct,
            severity="warning",
            message=(
                f"largest parameter change {largest:.2f} % vs plausibility limit "
                f"{gates.parameter_change_warning_pct:.2f} %"
            ),
            details={"implausible": implausible},
        )
    )
    return results


def _holdout_gates(
    baseline: CorrelationSummary | None,
    final: CorrelationSummary | None,
    gates: ValidationGates,
) -> list[GateResult]:
    if final is None:
        return []
    results = [
        GateResult(
            name="holdout_mac",
            passed=final.n_paired > 0 and final.min_mac >= gates.holdout_mac_min,
            value=final.min_mac,
            limit=gates.holdout_mac_min,
            message=(
                f"held-out min MAC {final.min_mac:.4f} vs limit {gates.holdout_mac_min:.4f}"
            ),
        )
    ]
    if gates.require_holdout_improvement and baseline is not None:
        before = baseline.max_abs_freq_error_pct
        after = final.max_abs_freq_error_pct
        # Equality counts as improved: a target already at zero error cannot get better.
        improved = after <= before + 1e-12
        results.append(
            GateResult(
                name="holdout_frequency_improvement",
                passed=improved,
                value=after,
                limit=before,
                message=(
                    f"held-out max |Δf| {after:.4f} % vs baseline {before:.4f} %"
                ),
                details={"baseline_max_abs_freq_error_pct": before},
            )
        )
    return results


def evaluate_gates(
    final: CorrelationSummary,
    gates: ValidationGates,
    *,
    parameters: ParameterSet | None = None,
    holdout_baseline: CorrelationSummary | None = None,
    holdout_final: CorrelationSummary | None = None,
) -> list[GateResult]:
    """Run every S6 acceptance check and return the results in report order."""
    results: list[GateResult] = [
        _pair_count_gate(final, gates),
        _mac_gate(final, gates),
        _frequency_gate(final, gates),
    ]
    results.extend(_parameter_gates(parameters, gates))
    results.extend(_holdout_gates(holdout_baseline, holdout_final, gates))
    return results


def gates_passed(results: Sequence[GateResult]) -> bool:
    """True when no blocking gate failed."""
    return not any(result.is_blocking for result in results)
