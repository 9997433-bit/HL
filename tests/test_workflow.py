"""The six-stage simulation-correction workflow (MS-4, AC-WORK-001..005).

The reference structure is a fixed-free spring/mass chain whose springs are
collected into groups, each scaled by one dimensionless factor.  Synthetic
"measurements" come from a detuned twin of the same model, so the truth the
pipeline has to recover is known exactly and every stage gate can be driven
into both its passing and its failing branch on demand.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pytest

from openfemlab.correlation.pairing import ModePair, ModePairing
from openfemlab.updating import ScalingModel, UpdatableParameter
from openfemlab.updating.sensitivity import ModalData
from openfemlab.workflow import (
    SCHEMA_VERSION,
    STAGE_ORDER,
    CorrectionWorkflow,
    HoldoutSpec,
    SensorMap,
    Stage,
    StageGateError,
    StageStatus,
    ValidationGates,
    run_correction,
    select_parameters,
)

N_DOF = 8
BASE_STIFFNESS = 1.0e6
BASE_MASS = 2.0
TRUTH = {"k0": 1.30, "k1": 0.80, "k2": 1.10}


# --------------------------------------------------------------------- helpers


def chain_stiffness(stiffnesses: np.ndarray) -> np.ndarray:
    """Fixed-free chain: spring ``j`` links DOF ``j-1`` (ground for 0) to DOF ``j``."""
    n = stiffnesses.size
    K = np.zeros((n, n))
    for j, k in enumerate(stiffnesses):
        K[j, j] += k
        if j > 0:
            K[j - 1, j - 1] += k
            K[j - 1, j] -= k
            K[j, j - 1] -= k
    return K


def group_masks(n_dof: int, n_groups: int) -> list[np.ndarray]:
    bounds = np.linspace(0, n_dof, n_groups + 1).astype(int)
    return [
        np.isin(np.arange(n_dof), np.arange(lo, hi)).astype(float)
        for lo, hi in zip(bounds[:-1], bounds[1:], strict=False)
    ]


def chain_model(
    *,
    n_groups: int = 3,
    num_modes: int = 5,
    duplicate: bool = False,
    dead_parameter: bool = False,
) -> ScalingModel:
    """Grouped spring/mass chain as an affine :class:`ScalingModel`.

    ``duplicate`` adds a second factor scaling exactly the first group (the
    collinear pair MS-3.6 has to detect); ``dead_parameter`` adds a factor that
    scales nothing at all (the unobservable column).
    """
    parts = {
        f"k{g}": chain_stiffness(BASE_STIFFNESS * mask)
        for g, mask in enumerate(group_masks(N_DOF, n_groups))
    }
    if duplicate:
        parts["k0_copy"] = parts["k0"].copy()
    if dead_parameter:
        parts["dead"] = np.zeros((N_DOF, N_DOF))
    return ScalingModel(
        parts,
        base_mass=np.eye(N_DOF) * BASE_MASS,
        num_modes=num_modes,
        # The element/assembly stack has its own tests; here the matrices are
        # given directly, so the dense eigensolver is enough.
        use_solver=False,
    )


def params(names, *, lower: float = 0.5, upper: float = 2.0) -> list[UpdatableParameter]:
    return [UpdatableParameter(name, 1.0, lower, upper) for name in names]


def assert_numbers_reproduce(left, right, path: str = "report") -> None:
    """Recursively compare two report payloads to 1e-12 relative (AC-WORK-002)."""
    assert type(left) is type(right), f"{path}: {type(left)} vs {type(right)}"
    if isinstance(left, dict):
        assert left.keys() == right.keys(), f"{path}: key sets differ"
        for key in left:
            assert_numbers_reproduce(left[key], right[key], f"{path}.{key}")
    elif isinstance(left, list):
        assert len(left) == len(right), f"{path}: length {len(left)} vs {len(right)}"
        for index, (a, b) in enumerate(zip(left, right, strict=True)):
            assert_numbers_reproduce(a, b, f"{path}[{index}]")
    elif isinstance(left, float):
        if math.isnan(left):
            assert math.isnan(right), f"{path}: {left} vs {right}"
        else:
            assert left == pytest.approx(right, rel=1e-12, abs=1e-15), f"{path}: {left} vs {right}"
    else:
        assert left == right, f"{path}: {left!r} vs {right!r}"


@pytest.fixture
def model() -> ScalingModel:
    return chain_model()


@pytest.fixture
def measured(model: ScalingModel) -> ModalData:
    """Noise-free measurements taken from the detuned twin."""
    return model.modal_data(TRUTH)


# ------------------------------------------------------------- happy path (S1..S6)


def test_pipeline_visits_the_six_stages_in_order(model, measured) -> None:
    report = run_correction(model, measured, None, params(TRUTH))

    assert [record.stage for record in report.stages] == list(STAGE_ORDER)
    assert all(record.status is StageStatus.PASSED for record in report.stages)
    assert report.failed_stage is None
    assert report.stage(Stage.UPDATING).details["converged"] is True
    assert report.wall_time_s > 0.0


def test_correction_recovers_the_detuned_parameters(model, measured) -> None:
    """AC-WORK-001: end-to-end run passes the MAC and frequency gates."""
    report = run_correction(model, measured, None, params(TRUTH))

    assert report.status == "PASS"
    assert report.passed
    baseline = report.baseline_correlation.summary
    final = report.final_correlation.summary
    assert baseline.max_abs_freq_error_pct > 4.0
    assert baseline.min_mac < 0.9
    assert final.min_mac >= 0.95
    assert final.max_abs_freq_error_pct <= 1.0
    for name, expected in TRUTH.items():
        assert report.parameter(name).final == pytest.approx(expected, rel=1e-4)


def test_every_validation_gate_is_reported_with_its_limit(model, measured) -> None:
    report = run_correction(model, measured, None, params(TRUTH))

    names = [gate.name for gate in report.gates]
    assert names == [
        "paired_modes",
        "mac",
        "frequency",
        "parameter_bounds",
        "parameter_plausibility",
    ]
    assert all(gate.passed for gate in report.gates)
    assert report.gate("mac").limit == 0.95
    assert report.gate("frequency").limit == 1.0
    assert report.blocking_gates == []


def test_iteration_history_records_a_monotone_cost_decrease(model, measured) -> None:
    report = run_correction(model, measured, None, params(TRUTH))

    costs = [record["cost"] for record in report.iterations]
    assert len(costs) >= 1
    assert costs == sorted(costs, reverse=True)
    assert costs[-1] < 1e-12
    assert set(report.iterations[0]["parameters"]) == set(TRUTH)


def test_posterior_sigma_is_reported_per_updated_parameter(model, measured) -> None:
    report = run_correction(model, measured, None, params(TRUTH))

    for name in TRUTH:
        entry = report.parameter(name)
        assert entry.sigma_post is not None
        # Noise-free targets are matched exactly, so the estimate collapses.
        assert entry.sigma_post < 1e-6


# ------------------------------------------------------------------ the artifact


def test_report_schema_is_versioned_and_complete(model, measured) -> None:
    """AC-WORK-005: required keys, ``schema_version`` 1.0, valid JSON."""
    report = run_correction(model, measured, None, params(TRUTH))
    payload = report.to_dict()

    assert payload["schema_version"] == SCHEMA_VERSION == "1.0"
    required = {
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
    }
    assert required <= payload.keys()
    assert payload["environment"]["seed"] == 0
    assert payload["environment"]["numpy"]
    assert payload["timing"]["stages"].keys() == {stage.value for stage in STAGE_ORDER}
    assert {entry["name"] for entry in payload["parameters"]} == set(TRUTH)
    assert payload["parameters"][0].keys() >= {"initial", "final", "lower", "upper", "sigma_post"}

    restored = json.loads(report.to_json())
    assert restored["status"] == "PASS"


def test_report_saves_itself_as_json(tmp_path, model, measured) -> None:
    report = run_correction(model, measured, None, params(TRUTH))
    path = report.save(tmp_path / "correction.json")

    assert path.exists()
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == "1.0"


def test_reruns_reproduce_every_reported_number(model, measured) -> None:
    """AC-WORK-002: identical inputs and seed reproduce the report bit for bit."""
    first = run_correction(chain_model(), measured, None, params(TRUTH), seed=7)
    second = run_correction(chain_model(), measured, None, params(TRUTH), seed=7)

    left = first.to_dict(include_timing=False)
    right = second.to_dict(include_timing=False)
    assert "timing" not in left
    assert all("wall_time_s" not in stage for stage in left["stages"])
    assert_numbers_reproduce(left, right)
    assert left["environment"]["seed"] == 7


def test_the_text_report_names_the_stage_that_halted(model, measured) -> None:
    report = run_correction(model, measured.select([0, 1]), None, params(TRUTH))

    text = report.report()
    assert "correction status : FAIL" in text
    assert "halted at PAIRING" in text
    assert "insufficient_pairs" in text


# ------------------------------------------------------------------ failed gates


def test_pairing_gate_halts_the_pipeline_with_a_machine_readable_reason(
    model, measured
) -> None:
    """AC-WORK-004: too few pairs stops at S2, nothing downstream runs."""
    report = run_correction(model, measured.select([0, 1]), None, params(TRUTH))

    assert report.status == "FAIL"
    assert report.failed_stage is Stage.PAIRING
    assert report.failure["stage"] == "PAIRING"
    assert report.failure["reason"] == "insufficient_pairs"
    assert report.failure["details"] == {
        "n_paired": 2,
        "min_pairs": 3,
        "mac_threshold": 0.5,
    }
    assert report.stage(Stage.BASELINE).status is StageStatus.PASSED
    for stage in (Stage.DIAGNOSIS, Stage.UPDATING, Stage.REANALYSIS, Stage.VALIDATION):
        assert report.stage(stage).status is StageStatus.SKIPPED
    assert report.gates == []
    assert report.final_correlation is None
    assert report.iterations == []


def test_strict_mode_raises_the_stage_gate_error(model, measured) -> None:
    with pytest.raises(StageGateError) as excinfo:
        run_correction(model, measured.select([0, 1]), None, params(TRUTH), strict=True)

    error = excinfo.value
    assert error.stage is Stage.PAIRING
    assert error.reason == "insufficient_pairs"
    assert error.as_dict()["details"]["n_paired"] == 2
    assert "S2 PAIRING" in str(error)


def test_a_failing_solver_is_reported_as_a_baseline_failure(measured) -> None:
    def broken(_values):
        raise RuntimeError("factorization failed")

    report = run_correction(broken, measured, None, params(TRUTH))

    assert report.failed_stage is Stage.BASELINE
    assert report.failure["reason"] == "baseline_solve_failed"
    assert "factorization failed" in report.failure["message"]
    assert report.stage(Stage.PAIRING).status is StageStatus.SKIPPED


def test_a_baseline_with_too_few_modes_fails_before_pairing(measured) -> None:
    report = run_correction(
        chain_model(num_modes=2), measured, None, params(TRUTH)
    )

    assert report.failed_stage is Stage.BASELINE
    assert report.failure["reason"] == "insufficient_modes"
    assert report.failure["details"] == {"n_modes": 2, "min_pairs": 3}


def test_a_failed_gate_never_leaves_the_report_marked_pass(model, measured) -> None:
    report = run_correction(
        model, measured, None, params(TRUTH), gates=ValidationGates(freq_tolerance_pct=0.0)
    )

    assert report.status == "FAIL"
    assert not report.passed
    assert report.failed_stage is Stage.VALIDATION
    assert report.failure["details"]["failed_gates"] == ["frequency"]
    # The stages before the gate did run, and their results are still reported.
    assert report.final_correlation is not None


def test_parameter_plausibility_only_warns(model) -> None:
    """A large but bounded parameter change annotates the report, it does not fail it."""
    measured = model.modal_data({"k0": 1.7, "k1": 1.0, "k2": 1.0})
    report = run_correction(model, measured, None, params(["k0", "k1", "k2"]))

    plausibility = report.gate("parameter_plausibility")
    assert plausibility.severity == "warning"
    assert not plausibility.passed
    assert plausibility.details["implausible"].keys() == {"k0"}
    assert not plausibility.is_blocking
    assert report.status == "PASS"


# ------------------------------------------------------------- held-out targets


def test_held_out_mode_is_excluded_from_updating_and_checked_at_validation(
    model, measured
) -> None:
    """AC-WORK-003: reserved targets never enter S4 but do gate S6."""
    report = run_correction(
        model, measured, None, params(TRUTH), holdout=HoldoutSpec(highest_paired=1)
    )

    assert report.holdout_modes == (4,)
    assert report.stage(Stage.UPDATING).details["n_fitted_modes"] == 4
    assert report.holdout_baseline is not None
    assert report.holdout_final is not None
    assert [gate.name for gate in report.gates][-2:] == [
        "holdout_mac",
        "holdout_frequency_improvement",
    ]
    assert report.gate("holdout_mac").value >= 0.9
    assert report.status == "PASS"
    payload = report.to_dict()["holdout"]
    assert payload["modes"] == [4]
    assert payload["final"]["summary"]["n_paired"] == 1


def test_overfitting_run_fails_the_held_out_gate() -> None:
    """AC-WORK-003: eight parameters fitted to four noisy targets overfit.

    Every in-sample gate passes — the fitted modes are matched to 1e-3 % — yet
    the reserved mode degrades by two orders of magnitude, which is exactly
    what the held-out check exists to catch.
    """
    overparameterised = chain_model(n_groups=8, num_modes=4)
    truth = dict(
        zip(
            [f"k{g}" for g in range(8)],
            [1.2, 0.85, 1.15, 0.9, 1.1, 0.95, 1.25, 0.8],
            strict=True,
        )
    )
    clean = overparameterised.modal_data(truth)
    rng = np.random.default_rng(0)
    noisy = ModalData(
        clean.frequencies * (1.0 + 0.03 * rng.standard_normal(clean.frequencies.size)),
        clean.mode_shapes,
    )

    report = run_correction(
        overparameterised,
        noisy,
        None,
        params(truth),
        holdout=HoldoutSpec(highest_paired=1),
    )

    assert report.status == "FAIL"
    assert report.failure["details"]["failed_gates"] == ["holdout_frequency_improvement"]
    assert report.gate("mac").passed
    assert report.gate("frequency").passed
    improvement = report.gate("holdout_frequency_improvement")
    assert not improvement.passed
    assert improvement.value > 10.0 * improvement.limit

    fitted = [
        abs(pair["frequency_error_pct"])
        for pair in report.final_correlation.to_dict()["pairs"]
        if pair["test_index"] not in report.holdout_modes
    ]
    assert max(fitted) < 1.0e-3


def test_held_out_channels_are_given_zero_weight_during_updating(model, measured) -> None:
    workflow = CorrectionWorkflow(
        model, measured, None, params(TRUTH), holdout=HoldoutSpec(channels=(0, 3))
    )
    report = workflow.run()

    assert report.status == "PASS"
    assert report.to_dict()["settings"]["holdout"]["channels"] == [0, 3]


def test_reserving_every_mode_leaves_nothing_to_fit(model, measured) -> None:
    report = run_correction(
        model, measured, None, params(TRUTH), holdout=HoldoutSpec(modes=tuple(range(5)))
    )

    assert report.failed_stage is Stage.DIAGNOSIS
    assert report.failure["reason"] == "no_fitted_targets"


def test_holdout_spec_reserves_the_highest_paired_test_modes() -> None:
    pairing = ModePairing(
        pairs=[
            ModePair(test_index=0, fe_index=1, mac=0.99, test_frequency=30.0, fe_frequency=31.0),
            ModePair(test_index=1, fe_index=0, mac=0.98, test_frequency=10.0, fe_frequency=11.0),
            ModePair(test_index=2, fe_index=2, mac=0.97, test_frequency=20.0, fe_frequency=21.0),
        ]
    )

    assert HoldoutSpec(highest_paired=1).resolve_modes(pairing) == (0,)
    assert HoldoutSpec(highest_paired=2).resolve_modes(pairing) == (0, 2)
    assert HoldoutSpec(modes=(1,), highest_paired=1).resolve_modes(pairing) == (0, 1)
    assert HoldoutSpec().resolve_modes(pairing) == ()
    assert HoldoutSpec().is_empty


# ----------------------------------------------------------- parameter diagnosis


def test_duplicated_parameter_is_frozen_and_updating_still_converges() -> None:
    """MS-3.6: a collinear pair is detected, one is frozen, the run still passes."""
    duplicated = chain_model(duplicate=True)
    measured = duplicated.modal_data({"k0": 1.3, "k0_copy": 1.0, "k1": 0.8, "k2": 1.1})

    report = run_correction(
        duplicated, measured, None, params(["k0", "k1", "k2", "k0_copy"])
    )

    selection = report.parameter_selection
    assert set(selection.selected) == {"k0", "k1", "k2"}
    assert selection.frozen == ["k0_copy"]
    frozen = report.parameter("k0_copy")
    assert not frozen.selected
    assert frozen.freeze_reason == "collinear"
    assert frozen.final == 1.0
    assert report.status == "PASS"
    assert report.parameter("k0").final == pytest.approx(1.3, rel=1e-4)


def test_parameter_scaling_nothing_is_frozen_as_insensitive(measured) -> None:
    insensitive = chain_model(dead_parameter=True)
    report = run_correction(
        insensitive, measured, None, params(["k0", "k1", "k2", "dead"])
    )

    assert report.parameter("dead").freeze_reason == "low_sensitivity"
    assert "dead" not in report.parameter_selection.selected
    assert report.status == "PASS"


def test_diagnosis_halts_when_no_parameter_is_observable(model, measured) -> None:
    frozen_structure = ScalingModel(
        {"dead": np.zeros((N_DOF, N_DOF))},
        base_stiffness=chain_stiffness(np.full(N_DOF, BASE_STIFFNESS)),
        base_mass=np.eye(N_DOF) * BASE_MASS,
        num_modes=5,
        use_solver=False,
    )
    baseline = frozen_structure.modal_data({"dead": 1.0})

    report = run_correction(frozen_structure, baseline, None, params(["dead"]))

    assert report.failed_stage is Stage.DIAGNOSIS
    assert report.failure["reason"] == "no_identifiable_parameters"
    assert report.failure["details"]["frozen"] == ["dead"]


def test_select_parameters_ranks_collinear_and_insensitive_columns() -> None:
    sensitivity = np.array(
        [
            [1.0, 0.0, 2.0, 1e-9],
            [0.0, 1.0, 0.0, 0.0],
            [1.0, 0.0, 2.0, 0.0],
        ]
    )
    selection = select_parameters(sensitivity, ["a", "b", "a_copy", "dead"])

    # ``a_copy`` has the larger norm, so it is the one kept and ``a`` the one dropped.
    assert selection.selected == ["b", "a_copy"]
    assert selection.frozen == ["a", "dead"]
    assert selection.reason_for("a") == "collinear"
    assert selection.reason_for("dead") == "low_sensitivity"
    assert selection.selected_condition_number < selection.condition_number
    assert "collinear with" in selection.table()
    assert selection.to_dict()["parameters"][0]["name"] == "a"


def test_select_parameters_rejects_a_mislabelled_matrix() -> None:
    with pytest.raises(ValueError, match="parameter names"):
        select_parameters(np.eye(3), ["a", "b"])


# --------------------------------------------------------------- the sensor map


def test_pipeline_correlates_through_a_sensor_map() -> None:
    model = chain_model()
    sensors = SensorMap(rows=(1, 3, 5, 7), signs=(1.0, -1.0, 1.0, 1.0))
    truth_shapes = model.modal_data(TRUTH)
    measured = ModalData(truth_shapes.frequencies, sensors.reduce(truth_shapes.mode_shapes))

    report = run_correction(model, measured, sensors, params(TRUTH))

    assert report.status == "PASS"
    assert report.final_correlation.dof_labels == ("dof1", "dof3", "dof5", "dof7")
    assert report.final_correlation.summary.min_mac >= 0.95
    assert report.to_dict()["settings"]["sensor_map"]["rows"] == [1, 3, 5, 7]


def test_sensor_map_reduces_and_flips_channels() -> None:
    shapes = np.arange(12.0).reshape(6, 2)
    sensors = SensorMap(rows=(0, 4), signs=(1.0, -1.0), labels=("a1:z", "a2:z"))

    reduced = sensors.reduce(shapes)
    assert reduced.shape == (2, 2)
    np.testing.assert_allclose(reduced[0], shapes[0])
    np.testing.assert_allclose(reduced[1], -shapes[4])
    np.testing.assert_allclose(sensors.operator(6) @ shapes, reduced)
    assert sensors.channel_labels() == ("a1:z", "a2:z")
    assert len(sensors) == sensors.n_channels == 2
    assert SensorMap.identity(3).channel_labels() == ("dof0", "dof1", "dof2")


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"rows": ()}, "at least one channel"),
        ({"rows": (1, 1)}, "same analysis row twice"),
        ({"rows": (0, 1), "signs": (1.0,)}, "one entry per channel"),
        ({"rows": (0, 1), "signs": (1.0, 0.0)}, "must be nonzero"),
        ({"rows": (0,), "labels": ("a", "b")}, "one entry per channel"),
    ],
)
def test_sensor_map_rejects_inconsistent_definitions(kwargs, match) -> None:
    with pytest.raises(ValueError, match=match):
        SensorMap(**kwargs)


def test_sensor_map_rejects_shapes_that_are_too_short() -> None:
    with pytest.raises(ValueError, match="observes analysis row"):
        SensorMap(rows=(0, 9)).reduce(np.zeros((4, 2)))


# ---------------------------------------------------------------- stage plumbing


def test_stage_numbering_matches_the_specification() -> None:
    assert [stage.index for stage in STAGE_ORDER] == [1, 2, 3, 4, 5, 6]
    assert Stage.VALIDATION.label == "S6 VALIDATION"
    assert Stage.BASELINE.value == "BASELINE"


def test_validation_gates_reject_impossible_limits() -> None:
    with pytest.raises(ValueError, match="mac_min"):
        ValidationGates(mac_min=1.5)
    with pytest.raises(ValueError, match="freq_tolerance_pct"):
        ValidationGates(freq_tolerance_pct=-1.0)
    with pytest.raises(ValueError, match="min_pairs"):
        ValidationGates(min_pairs=0)


def test_workflow_needs_parameters_and_a_test_set(model, measured) -> None:
    with pytest.raises(ValueError, match="at least one updating parameter"):
        run_correction(model, measured)
    with pytest.raises(ValueError, match="test mode set is empty"):
        run_correction(model, ModalData(np.empty(0)), None, params(TRUTH))


def test_the_workflow_never_mutates_the_callers_parameters(model, measured) -> None:
    declared = params(TRUTH)
    run_correction(model, measured, None, declared)

    assert [p.value for p in declared] == [1.0, 1.0, 1.0]
    assert [p.fixed for p in declared] == [False, False, False]


def test_unknown_stages_and_gates_raise_key_errors(model, measured) -> None:
    report = run_correction(model, measured.select([0, 1]), None, params(TRUTH))

    with pytest.raises(KeyError):
        report.gate("mac")
    with pytest.raises(KeyError):
        report.parameter("nonexistent")
