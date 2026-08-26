"""M4 correction-workflow acceptance suite (``docs/ACCEPTANCE_CRITERIA.md`` section 5).

Implemented here
----------------
- **AC-WORK-001** (twin, MS-4.1/MS-4.2) — the AC-UPD-003 detuning scenario wrapped
  in the S1-S6 pipeline ends in ``S6 = PASS`` with every paired mode at
  ``MAC >= 0.95`` and ``|df| <= 1 %``, from a baseline that fails both gates.
- **AC-WORK-002** (contract, MS-4.3) — two invocations with identical inputs and
  ``seed`` produce reports whose every numeric field agrees to ``1e-12``
  relative, and whose JSON is byte-identical once the wall-time fields are
  dropped.
- **AC-WORK-004** (contract, MS-4.1) — test data pairing fewer than ``min_pairs``
  modes halts at S2 with a machine-readable ``{stage, reason}`` failure; the
  stages behind it are ``SKIPPED`` and nothing is marked ``PASS``.
- **AC-WORK-005** (contract, MS-4.3) — the report carries ``schema_version
  "1.0"``, both correlation blocks, the iteration history, the parameter table,
  the gate results, the environment block and per-stage wall time, and
  serializes to valid JSON.

The reference structure is the ``ten_dof_chain`` parameterization of the M3
suite: a fixed-free unit spring-mass chain whose springs are collected into
three groups, each scaled by one dimensionless factor, with the nodal masses
left unparameterized. Synthetic "measurements" come from a detuned twin of the
same model, so the truth the pipeline must recover is known exactly and each
stage gate can be driven into either branch on demand.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pytest

from openfemlab.updating import ScalingModel, UpdatableParameter
from openfemlab.workflow import (
    SCHEMA_VERSION,
    STAGE_ORDER,
    Stage,
    StageStatus,
    ValidationGates,
    run_correction,
)

from ._support import criterion, spring_chain_parts

#: Gates of AC-WORK-001, AC-WORK-002 and AC-WORK-005.
MAC_MIN = 0.95
FREQ_TOLERANCE_PCT = 1.0
REPRODUCIBILITY_RTOL = 1e-12
REPORT_SCHEMA_VERSION = "1.0"

NUM_MASSES = 10
NUM_MODES = 6
STIFFNESS_GROUPS = ((1, 2, 3), (4, 5, 6), (7, 8, 9, 10))
MASS_GROUPS = ((1, 2, 3, 4, 5), (6, 7, 8, 9, 10))

#: The AC-UPD-003 detuning: three groups moved by -20 %, +15 % and +20 %.
TRUTH = {"k1": 1.20, "k2": 0.80, "k3": 1.15}

#: Fixed seed — a criterion only counts if its run is deterministic.
SEED = 11


def _chain_model() -> ScalingModel:
    """Grouped fixed-free chain; only the stiffness groups are parameterized."""
    stiffness_parts, mass_parts = spring_chain_parts(
        NUM_MASSES, STIFFNESS_GROUPS, MASS_GROUPS
    )
    return ScalingModel(
        stiffness_parts,
        base_mass=sum(mass_parts.values()),
        num_modes=NUM_MODES,
        # The element/assembly stack has its own criteria; the matrices are given
        # directly here, so the dense fallback is both enough and reproducible.
        use_solver=False,
    )


def _parameters() -> list[UpdatableParameter]:
    return [UpdatableParameter(name, 1.0, 0.5, 2.0) for name in TRUTH]


def _measured(model: ScalingModel):
    """Noise-free "test" modes taken from the detuned twin."""
    return model.modal_data(TRUTH)


def _assert_reproduces(left, right, path: str = "report") -> None:
    """Recursively compare two report payloads to ``REPRODUCIBILITY_RTOL``."""
    assert type(left) is type(right), f"{path}: {type(left)} vs {type(right)}"
    if isinstance(left, dict):
        assert left.keys() == right.keys(), f"{path}: key sets differ"
        for key in left:
            _assert_reproduces(left[key], right[key], f"{path}.{key}")
    elif isinstance(left, list):
        assert len(left) == len(right), f"{path}: length {len(left)} vs {len(right)}"
        for index, (a, b) in enumerate(zip(left, right, strict=True)):
            _assert_reproduces(a, b, f"{path}[{index}]")
    elif isinstance(left, float):
        if math.isnan(left):
            assert math.isnan(right), f"{path}: {left} vs {right}"
        else:
            assert left == pytest.approx(
                right, rel=REPRODUCIBILITY_RTOL, abs=1e-15
            ), f"{path}: {left} vs {right}"
    else:
        assert left == right, f"{path}: {left!r} vs {right!r}"


# ------------------------------------------------------- AC-WORK-001 end to end


@criterion("AC-WORK-001")
def test_ac_work_001_end_to_end_correction_passes_the_gates():
    """S6 = PASS with every paired mode at MAC >= 0.95 and |df| <= 1 %."""
    model = _chain_model()
    report = run_correction(model, _measured(model), None, _parameters(), seed=SEED)

    assert report.status == "PASS", report.failure
    assert report.passed
    assert report.failed_stage is None
    assert [record.stage for record in report.stages] == list(STAGE_ORDER)
    assert all(record.status is StageStatus.PASSED for record in report.stages)

    final = report.final_correlation.summary
    assert final.min_mac >= MAC_MIN
    assert final.max_abs_freq_error_pct <= FREQ_TOLERANCE_PCT
    for pair in report.final_correlation.pairing.pairs:
        assert pair.mac >= MAC_MIN
        assert abs(pair.frequency_error_pct) <= FREQ_TOLERANCE_PCT


@criterion("AC-WORK-001")
def test_ac_work_001_the_baseline_fails_the_gates_the_correction_passes():
    """The gates discriminate: the un-updated model violates both of them."""
    model = _chain_model()
    report = run_correction(model, _measured(model), None, _parameters(), seed=SEED)

    baseline = report.baseline_correlation.summary
    assert baseline.min_mac < MAC_MIN
    assert baseline.max_abs_freq_error_pct > FREQ_TOLERANCE_PCT

    assert [gate.name for gate in report.gates] == [
        "paired_modes",
        "mac",
        "frequency",
        "parameter_bounds",
        "parameter_plausibility",
    ]
    assert report.gate("mac").limit == MAC_MIN
    assert report.gate("frequency").limit == FREQ_TOLERANCE_PCT
    assert report.blocking_gates == []


@criterion("AC-WORK-001")
def test_ac_work_001_the_recovered_parameters_are_the_detuning():
    """Passing the gates is not luck: the pipeline lands on ``TRUTH``."""
    model = _chain_model()
    report = run_correction(model, _measured(model), None, _parameters(), seed=SEED)

    recovered = np.array([report.parameter(name).final for name in TRUTH])
    expected = np.array([TRUTH[name] for name in TRUTH])
    assert np.max(np.abs(recovered - expected)) <= 1e-3

    costs = [record["cost"] for record in report.iterations]
    assert costs == sorted(costs, reverse=True)


# --------------------------------------------------- AC-WORK-002 reproducibility


@criterion("AC-WORK-002")
def test_ac_work_002_reruns_reproduce_every_reported_number():
    """Identical inputs and seed agree to 1e-12 relative on every numeric field."""
    measured = _measured(_chain_model())

    first = run_correction(_chain_model(), measured, None, _parameters(), seed=SEED)
    second = run_correction(_chain_model(), measured, None, _parameters(), seed=SEED)

    left = first.to_dict(include_timing=False)
    right = second.to_dict(include_timing=False)
    assert left["environment"]["seed"] == SEED
    _assert_reproduces(left, right)


@criterion("AC-WORK-002")
def test_ac_work_002_the_json_is_identical_once_wall_times_are_dropped():
    """``include_timing=False`` removes every wall-time field, leaving byte equality."""
    measured = _measured(_chain_model())

    first = run_correction(_chain_model(), measured, None, _parameters(), seed=SEED)
    second = run_correction(_chain_model(), measured, None, _parameters(), seed=SEED)

    left = first.to_dict(include_timing=False)
    assert "timing" not in left
    assert all("wall_time_s" not in stage for stage in left["stages"])
    assert json.dumps(left, sort_keys=True) == json.dumps(
        second.to_dict(include_timing=False), sort_keys=True
    )


# ------------------------------------------------------- AC-WORK-004 typed halt


@criterion("AC-WORK-004")
def test_ac_work_004_too_few_pairs_halts_at_s2_with_a_typed_reason():
    """A machine-readable ``{stage, reason}`` and no partial PASS."""
    model = _chain_model()
    report = run_correction(
        model, _measured(model).select([0, 1]), None, _parameters(), seed=SEED
    )

    assert report.status == "FAIL"
    assert not report.passed
    assert report.failed_stage is Stage.PAIRING
    assert report.failure["stage"] == "PAIRING"
    assert report.failure["reason"] == "insufficient_pairs"
    assert report.failure["details"]["n_paired"] < report.failure["details"]["min_pairs"]


@criterion("AC-WORK-004")
def test_ac_work_004_the_stages_behind_the_halt_do_not_run():
    """S3-S6 are recorded ``SKIPPED`` and produce no results to misread as a pass."""
    model = _chain_model()
    report = run_correction(
        model, _measured(model).select([0, 1]), None, _parameters(), seed=SEED
    )

    assert report.stage(Stage.BASELINE).status is StageStatus.PASSED
    assert report.stage(Stage.PAIRING).status is StageStatus.FAILED
    for stage in (Stage.DIAGNOSIS, Stage.UPDATING, Stage.REANALYSIS, Stage.VALIDATION):
        assert report.stage(stage).status is StageStatus.SKIPPED

    assert report.gates == []
    assert report.final_correlation is None
    assert report.iterations == []
    payload = report.to_dict()
    assert payload["status"] == "FAIL"
    assert not any(record["status"] == "PASSED" for record in payload["stages"][2:])


@criterion("AC-WORK-004")
def test_ac_work_004_a_failed_validation_gate_is_also_a_typed_halt():
    """The same contract holds at S6, where only the gate limit changes."""
    model = _chain_model()
    report = run_correction(
        model,
        _measured(model),
        None,
        _parameters(),
        gates=ValidationGates(freq_tolerance_pct=0.0),
        seed=SEED,
    )

    assert report.status == "FAIL"
    assert report.failed_stage is Stage.VALIDATION
    assert report.failure["stage"] == "VALIDATION"
    assert report.failure["details"]["failed_gates"] == ["frequency"]


# ------------------------------------------------------- AC-WORK-005 the report


@criterion("AC-WORK-005")
def test_ac_work_005_the_report_carries_the_versioned_schema():
    """``schema_version`` is the string ``"1.0"`` in both the code and the payload."""
    model = _chain_model()
    report = run_correction(model, _measured(model), None, _parameters(), seed=SEED)

    assert SCHEMA_VERSION == REPORT_SCHEMA_VERSION
    assert report.to_dict()["schema_version"] == REPORT_SCHEMA_VERSION


@criterion("AC-WORK-005")
def test_ac_work_005_the_report_contains_every_required_block():
    """Correlations, history, parameter table, gates, environment, per-stage timing."""
    model = _chain_model()
    report = run_correction(model, _measured(model), None, _parameters(), seed=SEED)
    payload = report.to_dict()

    assert {
        "schema_version",
        "status",
        "stages",
        "baseline_correlation",
        "final_correlation",
        "holdout",
        "iterations",
        "parameters",
        "parameter_selection",
        "gates",
        "failure",
        "settings",
        "environment",
        "timing",
    } <= payload.keys()

    assert payload["baseline_correlation"]["summary"]
    assert payload["final_correlation"]["summary"]
    assert payload["iterations"]
    assert payload["iterations"][0].keys() >= {"iteration", "cost", "parameters"}
    assert {entry["name"] for entry in payload["parameters"]} == set(TRUTH)
    for entry in payload["parameters"]:
        assert entry.keys() >= {"initial", "final", "lower", "upper", "sigma_post"}
        assert entry["lower"] <= entry["final"] <= entry["upper"]
    assert payload["gates"] and payload["gates"][0].keys() >= {"name", "passed", "limit"}

    environment = payload["environment"]
    assert environment["seed"] == SEED
    assert environment.keys() >= {"openfemlab", "python", "numpy", "scipy"}

    assert payload["timing"]["stages"].keys() == {stage.value for stage in STAGE_ORDER}
    assert all(record["wall_time_s"] >= 0.0 for record in payload["stages"])


@criterion("AC-WORK-005")
def test_ac_work_005_the_report_serializes_to_valid_json(tmp_path):
    """The payload survives a JSON round trip, from memory and from disk."""
    model = _chain_model()
    report = run_correction(model, _measured(model), None, _parameters(), seed=SEED)

    restored = json.loads(report.to_json())
    assert restored["schema_version"] == REPORT_SCHEMA_VERSION
    assert restored["status"] == "PASS"

    path = report.save(tmp_path / "correction.json")
    assert json.loads(path.read_text(encoding="utf-8")) == restored
