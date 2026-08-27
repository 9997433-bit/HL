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
- **AC-WORK-003** (twin, MS-4.1) — with the highest paired mode reserved, S4
  fits one target fewer and S6 evaluates the reserved one on its own; an
  over-parameterized fit to noisy targets is blocked by the held-out gate with
  a machine-readable reason, while the same run passes every other gate when
  nothing is reserved.
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

import argparse
import json
import math

import numpy as np
import pytest

from openfemlab.updating import ScalingModel, UpdatableParameter
from openfemlab.updating.sensitivity import ModalData
from openfemlab.workflow import (
    SCHEMA_VERSION,
    STAGE_ORDER,
    HoldoutSpec,
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


# ------------------------------------------------- AC-WORK-003 held-out targets

#: MS-4.1 gate on the reserved target.
HOLDOUT_MAC_MIN = 0.9

#: The over-parameterized twin: one factor per pair of springs, so five free
#: factors face five fitted frequency residuals once the highest mode is
#: reserved. An exactly determined fit has nowhere to put the measurement noise
#: except into the parameters, which is what overfitting is.
OVERFIT_GROUPS = tuple((2 * index + 1, 2 * index + 2) for index in range(5))
OVERFIT_NOISE_PCT = 1.0
OVERFIT_SEED = 4242

#: Limits the overfitted run is judged against. Deliberately looser than the
#: AC-WORK-001 gates on the modal set as a whole: the point of the criterion is
#: that the *held-out* gate catches what the others let through.
OVERFIT_GATES = ValidationGates(
    mac_min=0.95, freq_tolerance_pct=2.0, holdout_mac_min=HOLDOUT_MAC_MIN
)


def _overfit_model() -> ScalingModel:
    stiffness_parts, mass_parts = spring_chain_parts(
        NUM_MASSES, OVERFIT_GROUPS, MASS_GROUPS
    )
    return ScalingModel(
        stiffness_parts,
        base_mass=sum(mass_parts.values()),
        num_modes=NUM_MODES,
        use_solver=False,
    )


def _noisy_targets(model: ScalingModel):
    """Measurements of the *nominal* model, with 1 % scatter on the frequencies.

    Nominal, so there is no correction to find: every parameter move the run
    makes is a move onto the noise. The mode shapes are left clean, which keeps
    the pairing unambiguous and the failure attributable to the frequencies.
    """
    truth = {name: 1.0 for name in model.parameter_names}
    clean = model.modal_data(truth)
    rng = np.random.default_rng(OVERFIT_SEED)
    scatter = 1.0 + 0.01 * OVERFIT_NOISE_PCT * rng.standard_normal(clean.frequencies.size)
    return ModalData(clean.frequencies * scatter, clean.mode_shapes)


def _overfit_report(holdout: HoldoutSpec):
    model = _overfit_model()
    parameters = [
        UpdatableParameter(name, 1.0, 0.5, 2.0) for name in sorted(model.parameter_names)
    ]
    return run_correction(
        model,
        _noisy_targets(model),
        None,
        parameters,
        gates=OVERFIT_GATES,
        holdout=holdout,
        seed=SEED,
    )


def _reserved_run(highest_paired: int = 1):
    """The clean AC-WORK-001 twin with the highest paired mode reserved."""
    model = _chain_model()
    return run_correction(
        model,
        _measured(model),
        None,
        _parameters(),
        holdout=HoldoutSpec(highest_paired=highest_paired),
        seed=SEED,
    )


def _stage_details(report, stage: Stage) -> dict:
    return next(record for record in report.stages if record.stage is stage).details


@criterion("AC-WORK-003")
def test_ac_work_003_the_reserved_mode_is_kept_out_of_the_updating_residuals():
    """``HoldoutSpec(highest_paired=1)`` removes one target from S4, and says which."""
    report = _reserved_run()

    assert report.holdout_modes == (NUM_MODES - 1,)
    assert _stage_details(report, Stage.PAIRING)["holdout_modes"] == [NUM_MODES - 1]
    assert _stage_details(report, Stage.UPDATING)["n_fitted_modes"] == NUM_MODES - 1
    assert report.settings["holdout"] == {
        "modes": [], "highest_paired": 1, "channels": [],
    }


@criterion("AC-WORK-003")
def test_ac_work_003_the_reserved_mode_is_evaluated_at_s6():
    """S6 correlates the reserved target on its own, before and after (MS-4.1)."""
    report = _reserved_run()

    assert report.holdout_baseline is not None
    assert report.holdout_final is not None
    assert report.holdout_final.summary.n_paired == 1
    assert report.holdout_final.summary.min_mac >= HOLDOUT_MAC_MIN
    assert report.holdout_final.summary.max_abs_freq_error_pct <= (
        report.holdout_baseline.summary.max_abs_freq_error_pct
    )

    names = {result.name for result in report.gates}
    assert {"holdout_mac", "holdout_frequency_improvement"} <= names


@criterion("AC-WORK-003")
def test_ac_work_003_reserving_a_target_does_not_spoil_a_genuine_correction():
    """The noise-free twin still passes, with the reserved mode as the evidence.

    Fitting five of the six modes is enough to identify all three factors, so
    the reserved mode — which no residual ever saw — comes out correlated too.
    That is what distinguishes a corrected model from a fitted one.
    """
    report = _reserved_run()

    assert report.status == "PASS", report.failure
    assert report.holdout_baseline.summary.max_abs_freq_error_pct > FREQ_TOLERANCE_PCT
    assert report.holdout_final.summary.max_abs_freq_error_pct <= FREQ_TOLERANCE_PCT
    for name, expected in TRUTH.items():
        assert report.parameter(name).final == pytest.approx(expected, abs=1e-6)


@criterion("AC-WORK-003")
def test_ac_work_003_an_overfitted_run_fails_the_held_out_gate():
    """Five factors fitted to five noisy targets: blocked, with a reason."""
    report = _overfit_report(HoldoutSpec(highest_paired=1))

    assert report.status == "FAIL"
    blocking = [result.name for result in report.gates if result.is_blocking]
    assert "holdout_frequency_improvement" in blocking
    assert report.failure["stage"] == Stage.VALIDATION.value
    assert report.failure["reason"] == "gate_failed"
    assert "holdout_frequency_improvement" in report.failure["details"]["failed_gates"]

    holdout = next(r for r in report.gates if r.name == "holdout_frequency_improvement")
    assert holdout.value > holdout.limit, "the reserved target has to have got worse"


@criterion("AC-WORK-003")
def test_ac_work_003_the_same_run_passes_when_nothing_is_reserved():
    """Why the reservation is the detector and not an incidental extra gate.

    Judged on the targets it was fitted to, the overfitted model looks
    corrected: every ordinary S6 gate is met. Only the target the fit never saw
    exposes it.
    """
    unguarded = _overfit_report(HoldoutSpec())

    assert unguarded.status == "PASS", unguarded.failure
    assert unguarded.holdout_modes == ()
    assert unguarded.holdout_final is None
    assert not any(result.name.startswith("holdout") for result in unguarded.gates)


@criterion("AC-WORK-003")
def test_ac_work_003_the_overfit_shows_as_a_gap_between_fitted_and_reserved_modes():
    """The signature of overfitting, read off the report the run produced."""
    report = _overfit_report(HoldoutSpec(highest_paired=1))
    reserved = set(report.holdout_modes)

    fitted_error = max(
        abs(pair.frequency_error_pct)
        for pair in report.final_correlation.pairing.pairs
        if pair.test_index not in reserved
    )
    reserved_error = report.holdout_final.summary.max_abs_freq_error_pct

    assert fitted_error <= OVERFIT_NOISE_PCT
    assert reserved_error > 2.0 * fitted_error, (
        f"fitted {fitted_error:.4f} % vs reserved {reserved_error:.4f} %"
    )


@criterion("AC-WORK-003")
def test_ac_work_003_reserving_every_target_leaves_nothing_to_fit():
    """The degenerate reservation is a typed S3 failure, not an empty update."""
    model = _chain_model()

    report = run_correction(
        model,
        _measured(model),
        None,
        _parameters(),
        holdout=HoldoutSpec(modes=tuple(range(NUM_MODES))),
        seed=SEED,
    )

    assert report.status == "FAIL"
    assert report.failure["stage"] == Stage.DIAGNOSIS.value
    assert report.failure["reason"] == "no_fitted_targets"


@criterion("AC-WORK-003")
def test_ac_work_003_the_held_out_blocks_travel_in_the_report():
    """A validation nobody can audit is not one; both blocks are serialized."""
    payload = json.loads(_reserved_run().to_json())

    holdout = payload["holdout"]
    assert holdout["modes"] == [NUM_MODES - 1]
    assert holdout["baseline"] is not None
    assert holdout["final"] is not None
    assert holdout["final"]["summary"]["n_paired"] == 1


# --------------------------------------------------------------- AC-WORK-006


@criterion("AC-WORK-006")
def test_ac_work_006_side_by_side_mode_plot_returns_axes() -> None:
    from openfemlab import ModalSolver
    from openfemlab.mesh.simple import spring_mass_chain
    from openfemlab.viz.plotting import plot_modes_side_by_side, require_matplotlib

    require_matplotlib()
    model = spring_mass_chain(num_masses=4, stiffness=1.0, mass=1.0, fixed_end=False)
    result = ModalSolver(model).solve(num_modes=2)
    figure, axes = plot_modes_side_by_side(
        model,
        result.mode_shapes[:, 0],
        model,
        result.mode_shapes[:, 1],
        title_a="mode 1",
        title_b="mode 2",
    )
    assert figure is not None
    assert len(axes) == 2


# --------------------------------------------------------------- AC-WORK-007


@criterion("AC-WORK-007")
def test_ac_work_007_align_cli_writes_sensor_map_json(tmp_path) -> None:
    from openfemlab.cli.commands.align import run
    from openfemlab.cli.console import Reporter

    model_csv = tmp_path / "model.csv"
    sensor_csv = tmp_path / "sensors.csv"
    output = tmp_path / "map.json"
    model_coords = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]],
        dtype=np.float64,
    )
    sensor_coords = model_coords + np.array([0.05, 0.02, -0.01])
    model_csv.write_text(
        "\n".join(f"{x},{y},{z}" for x, y, z in model_coords) + "\n",
        encoding="utf-8",
    )
    sensor_csv.write_text(
        "\n".join(f"{x},{y},{z},ch{i}" for i, (x, y, z) in enumerate(sensor_coords))
        + "\n",
        encoding="utf-8",
    )
    exit_code = run(
        argparse.Namespace(
            model_coords=str(model_csv),
            sensor_coords=str(sensor_csv),
            output=str(output),
            max_distance=0.2,
            reference_model=str(model_csv),
            reference_sensors=str(sensor_csv),
        ),
        Reporter(quiet=True),
    )
    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["rows"] == [0, 1, 2]
    assert payload["labels"] == ["ch0", "ch1", "ch2"]
    assert "rigid_transform" in payload
