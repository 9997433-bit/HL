"""Stages of the correction pipeline and their bookkeeping (MS-4.1).

The correction workflow is a strictly ordered state machine::

    S1 BASELINE -> S2 PAIRING -> S3 DIAGNOSIS -> S4 UPDATING
                -> S5 REANALYSIS -> S6 VALIDATION

Every stage carries a gate.  A stage that fails its gate halts the pipeline
with a machine-readable ``(stage, reason)`` pair; the stages behind it are
recorded as :attr:`StageStatus.SKIPPED` so a partially executed run can never
be mistaken for a passing one.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..exceptions import OpenFEMLabError

__all__ = [
    "STAGE_ORDER",
    "Stage",
    "StageGateError",
    "StageRecord",
    "StageStatus",
    "StageTimer",
    "UpdatingDivergenceError",
    "WorkflowError",
]


class Stage(str, Enum):
    """The six pipeline stages, in execution order."""

    BASELINE = "BASELINE"
    PAIRING = "PAIRING"
    DIAGNOSIS = "DIAGNOSIS"
    UPDATING = "UPDATING"
    REANALYSIS = "REANALYSIS"
    VALIDATION = "VALIDATION"

    @property
    def index(self) -> int:
        """1-based stage number (``S1``..``S6``)."""
        return STAGE_ORDER.index(self) + 1

    @property
    def label(self) -> str:
        return f"S{self.index} {self.value}"


STAGE_ORDER: tuple[Stage, ...] = (
    Stage.BASELINE,
    Stage.PAIRING,
    Stage.DIAGNOSIS,
    Stage.UPDATING,
    Stage.REANALYSIS,
    Stage.VALIDATION,
)


class StageStatus(str, Enum):
    """Outcome of a single stage."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class WorkflowError(OpenFEMLabError):
    """Base class for correction-workflow failures."""


class StageGateError(WorkflowError):
    """A stage gate rejected the run.

    The exception is the machine-readable failure contract of the pipeline:
    ``stage`` says where it stopped, ``reason`` is a stable snake_case code a
    caller can branch on, and ``details`` carries the numbers behind it.
    """

    def __init__(
        self,
        stage: Stage,
        reason: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(f"{stage.label}: {message} [{reason}]")
        self.stage = stage
        self.reason = reason
        self.message = message
        self.details: dict[str, Any] = dict(details or {})

    def as_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage.value,
            "reason": self.reason,
            "message": self.message,
            "details": dict(self.details),
        }


class UpdatingDivergenceError(WorkflowError):
    """The updating loop increased the objective instead of reducing it."""


@dataclass
class StageRecord:
    """What one stage did, how long it took, and whether its gate passed."""

    stage: Stage
    status: StageStatus
    wall_time_s: float = 0.0
    reason: str | None = None
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status is StageStatus.PASSED

    def to_dict(self, *, include_timing: bool = True) -> dict[str, Any]:
        out: dict[str, Any] = {
            "stage": self.stage.value,
            "index": self.stage.index,
            "status": self.status.value,
            "reason": self.reason,
            "message": self.message,
            "details": dict(self.details),
        }
        if include_timing:
            out["wall_time_s"] = self.wall_time_s
        return out


class StageTimer:
    """Accumulates :class:`StageRecord` entries in execution order."""

    def __init__(self) -> None:
        self._records: list[StageRecord] = []
        self._started: float | None = None
        self._stage: Stage | None = None

    def __iter__(self) -> Iterator[StageRecord]:
        return iter(self._records)

    def __len__(self) -> int:
        return len(self._records)

    @property
    def records(self) -> list[StageRecord]:
        return list(self._records)

    def start(self, stage: Stage) -> None:
        self._stage = stage
        self._started = time.perf_counter()

    def finish(
        self,
        status: StageStatus,
        *,
        reason: str | None = None,
        message: str = "",
        details: dict[str, Any] | None = None,
    ) -> StageRecord:
        if self._stage is None or self._started is None:  # pragma: no cover - misuse guard
            raise RuntimeError("finish() called before start()")
        record = StageRecord(
            stage=self._stage,
            status=status,
            wall_time_s=time.perf_counter() - self._started,
            reason=reason,
            message=message,
            details=dict(details or {}),
        )
        self._records.append(record)
        self._stage = None
        self._started = None
        return record

    def skip_remaining(self, after: Stage, reason: str) -> None:
        """Mark every stage behind ``after`` as skipped."""
        for stage in STAGE_ORDER[after.index :]:
            self._records.append(
                StageRecord(
                    stage=stage,
                    status=StageStatus.SKIPPED,
                    reason=reason,
                    message=f"not run: {after.label} failed",
                )
            )
