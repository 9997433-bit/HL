"""The ``CorrectionReport`` artifact (MS-4.3).

One schema-versioned JSON document per correction run: what the baseline model
looked like, what the updating loop did to it, what the corrected model looks
like, and whether the acceptance gates passed.  It is the stable external
interface of the workflow layer — CI publishes it, reviewers diff it, and a
rerun with the same inputs and seed must reproduce every number in it.

Wall times are the only non-reproducible content, so they live behind
``include_timing`` and can be dropped when two runs are compared.
"""

from __future__ import annotations

import json
import platform
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .gates import GateResult
from .stages import Stage, StageRecord, StageStatus

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..correlation.report import CorrelationReport
    from .selection import ParameterSelection

__all__ = [
    "SCHEMA_VERSION",
    "CorrectionReport",
    "ParameterEntry",
    "environment_block",
]

SCHEMA_VERSION = "1.0"


def _package_version(name: str) -> str | None:
    try:
        from importlib.metadata import PackageNotFoundError, version
    except ImportError:  # pragma: no cover - Python < 3.8 only
        return None
    try:
        return version(name)
    except PackageNotFoundError:  # pragma: no cover - source checkout without install
        module = sys.modules.get(name)
        return getattr(module, "__version__", None)


def environment_block(seed: int) -> dict[str, Any]:
    """Everything needed to reproduce the run, bar the inputs themselves."""
    from .. import __version__

    return {
        "openfemlab": __version__,
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "numpy": _package_version("numpy"),
        "scipy": _package_version("scipy"),
        "seed": int(seed),
    }


@dataclass(frozen=True)
class ParameterEntry:
    """One row of the report's parameter table."""

    name: str
    kind: str
    initial: float
    final: float
    lower: float
    upper: float
    change_pct: float
    selected: bool
    freeze_reason: str | None = None
    sigma_post: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "initial": self.initial,
            "final": self.final,
            "lower": self.lower,
            "upper": self.upper,
            "change_pct": self.change_pct,
            "selected": self.selected,
            "freeze_reason": self.freeze_reason,
            "sigma_post": self.sigma_post,
        }


@dataclass
class CorrectionReport:
    """Complete, serializable outcome of one ``S1..S6`` correction run."""

    status: str = "FAIL"
    stages: list[StageRecord] = field(default_factory=list)
    baseline_correlation: CorrelationReport | None = None
    final_correlation: CorrelationReport | None = None
    holdout_baseline: CorrelationReport | None = None
    holdout_final: CorrelationReport | None = None
    iterations: list[dict[str, Any]] = field(default_factory=list)
    parameters: list[ParameterEntry] = field(default_factory=list)
    parameter_selection: ParameterSelection | None = None
    gates: list[GateResult] = field(default_factory=list)
    holdout_modes: tuple[int, ...] = ()
    failure: dict[str, Any] | None = None
    settings: dict[str, Any] = field(default_factory=dict)
    environment: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    # ------------------------------------------------------------------ views

    @property
    def passed(self) -> bool:
        return self.status == "PASS"

    @property
    def failed_stage(self) -> Stage | None:
        """The stage that stopped the pipeline, or ``None`` if all six ran."""
        for record in self.stages:
            if record.status is StageStatus.FAILED:
                return record.stage
        return None

    def stage(self, stage: Stage) -> StageRecord:
        for record in self.stages:
            if record.stage is stage:
                return record
        raise KeyError(f"stage {stage.value} is not in the report")

    def gate(self, name: str) -> GateResult:
        for result in self.gates:
            if result.name == name:
                return result
        raise KeyError(f"gate {name!r} is not in the report")

    @property
    def blocking_gates(self) -> list[GateResult]:
        return [result for result in self.gates if result.is_blocking]

    @property
    def wall_time_s(self) -> float:
        return sum(record.wall_time_s for record in self.stages)

    def parameter(self, name: str) -> ParameterEntry:
        for entry in self.parameters:
            if entry.name == name:
                return entry
        raise KeyError(f"parameter {name!r} is not in the report")

    # ----------------------------------------------------------- serialization

    def to_dict(self, *, include_timing: bool = True) -> dict[str, Any]:
        """Plain-Python view of the report.

        ``include_timing=False`` drops the wall-time fields, leaving only
        content that a rerun with the same inputs and seed must reproduce
        exactly.
        """
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "status": self.status,
            "stages": [record.to_dict(include_timing=include_timing) for record in self.stages],
            "baseline_correlation": (
                None if self.baseline_correlation is None else self.baseline_correlation.to_dict()
            ),
            "final_correlation": (
                None if self.final_correlation is None else self.final_correlation.to_dict()
            ),
            "holdout": {
                "modes": list(self.holdout_modes),
                "baseline": (
                    None if self.holdout_baseline is None else self.holdout_baseline.to_dict()
                ),
                "final": None if self.holdout_final is None else self.holdout_final.to_dict(),
            },
            "iterations": [dict(record) for record in self.iterations],
            "parameters": [entry.to_dict() for entry in self.parameters],
            "parameter_selection": (
                None if self.parameter_selection is None else self.parameter_selection.to_dict()
            ),
            "gates": [result.to_dict() for result in self.gates],
            "failure": None if self.failure is None else dict(self.failure),
            "settings": dict(self.settings),
            "environment": dict(self.environment),
        }
        if include_timing:
            payload["timing"] = {
                "total_s": self.wall_time_s,
                "stages": {
                    record.stage.value: record.wall_time_s for record in self.stages
                },
            }
        return payload

    def to_json(self, *, indent: int | None = 2, include_timing: bool = True) -> str:
        return json.dumps(self.to_dict(include_timing=include_timing), indent=indent)

    def save(self, path: str | Path, *, indent: int | None = 2) -> Path:
        """Write the report as JSON and return the path written."""
        target = Path(path)
        target.write_text(self.to_json(indent=indent), encoding="utf-8")
        return target

    # -------------------------------------------------------------- reporting

    def report(self) -> str:
        lines = [
            f"correction status : {self.status}",
            f"schema version    : {self.schema_version}",
            "",
            f"{'stage':<14} {'status':<8} {'time [s]':>9}  reason",
            "-" * 58,
        ]
        for record in self.stages:
            reason = record.reason or ""
            lines.append(
                f"{record.stage.value:<14} {record.status.value:<8} "
                f"{record.wall_time_s:9.4f}  {reason}"
            )
        if self.gates:
            lines.append("")
            lines.append(f"{'gate':<32} {'result':<8} detail")
            lines.append("-" * 58)
            for result in self.gates:
                verdict = "pass" if result.passed else result.severity
                lines.append(f"{result.name:<32} {verdict:<8} {result.message}")
        if self.parameters:
            lines.append("")
            header = (
                f"{'parameter':<20} {'initial':>10} {'final':>10} {'change [%]':>11} {'kept':>6}"
            )
            lines.append(header)
            lines.append("-" * len(header))
            for entry in self.parameters:
                lines.append(
                    f"{entry.name:<20} {entry.initial:10.4f} {entry.final:10.4f} "
                    f"{entry.change_pct:11.3f} {'yes' if entry.selected else 'no':>6}"
                )
        if self.failure is not None:
            lines.append("")
            lines.append(
                f"halted at {self.failure['stage']}: {self.failure['message']} "
                f"[{self.failure['reason']}]"
            )
        return "\n".join(lines)

    def __str__(self) -> str:  # pragma: no cover - convenience only
        return self.report()
