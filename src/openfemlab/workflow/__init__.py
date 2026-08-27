"""Simulation-correction workflow (L4, MS-4).

The productized loop of the platform: take a nominal FE model and a measured
mode set, and either hand back a corrected, validated model or an explicit
reason why the correction is not trustworthy::

    S1 BASELINE   solve the nominal model
    S2 PAIRING    map sensors, pair FE and test modes
    S3 DIAGNOSIS  correlate, COMAC, select identifiable parameters
    S4 UPDATING   sensitivity-based correction, re-pairing every iteration
    S5 REANALYSIS re-solve at the updated parameters, correlate afresh
    S6 VALIDATION acceptance gates, including held-out targets

Each stage carries a gate; a failed gate halts the pipeline with a
machine-readable ``(stage, reason)`` pair instead of returning a partial result
that looks like a success.  One run produces one schema-versioned
:class:`~openfemlab.workflow.report.CorrectionReport`::

    from openfemlab.workflow import HoldoutSpec, SensorMap, run_correction

    report = run_correction(
        model, test, SensorMap(rows=(0, 3, 7)), params,
        holdout=HoldoutSpec(highest_paired=1),
    )
    print(report.report())
    report.save("correction.json")
"""

from __future__ import annotations

from .correction import CorrectionWorkflow, run_correction
from .gates import GateResult, HoldoutSpec, ValidationGates, evaluate_gates, gates_passed
from .report import SCHEMA_VERSION, CorrectionReport, ParameterEntry, environment_block
from .selection import ParameterDiagnostic, ParameterSelection, select_parameters
from .sensors import SensorMap
from .stages import (
    STAGE_ORDER,
    Stage,
    StageGateError,
    StageRecord,
    StageStatus,
    UpdatingDivergenceError,
    WorkflowError,
)

__all__ = [
    "SCHEMA_VERSION",
    "STAGE_ORDER",
    "CorrectionReport",
    "CorrectionWorkflow",
    "GateResult",
    "HoldoutSpec",
    "ParameterDiagnostic",
    "ParameterEntry",
    "ParameterSelection",
    "SensorMap",
    "Stage",
    "StageGateError",
    "StageRecord",
    "StageStatus",
    "UpdatingDivergenceError",
    "ValidationGates",
    "WorkflowError",
    "environment_block",
    "evaluate_gates",
    "gates_passed",
    "run_correction",
    "select_parameters",
]
