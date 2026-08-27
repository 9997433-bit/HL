"""Tests for the cross-platform DSP golden comparison (SOTA E2).

The report this tool produces is the only evidence behind E2, so the tests
that matter most are the ones that show the comparison can *fail*: a merge
that passes no matter what the runners recorded would be worse than no
evidence at all.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from tools.cross_platform_golden import (
    FLOAT32_TOLERANCE_ULPS,
    PLATFORM_KEYS,
    TOLERANCE_ABSOLUTE,
    VECTORS,
    build_record,
    main,
    measure_vector,
    merge_records,
    platform_key,
    probe_indices,
    vector_tolerance,
)

#: Two cheap vectors: one closed-form transfer function, one polyphase meter.
#: Enough to exercise a real record end to end without measuring every filter
#: in the product twice per test session.
CHEAP_VECTORS = tuple(
    vector
    for vector in VECTORS
    if vector.vector_id in {"eq-magnitude-response", "true-peak-polyphase"}
)


@pytest.fixture(scope="module")
def linux_record() -> dict:
    record = build_record(CHEAP_VECTORS)
    record["platform"] = "linux"
    return record


def _three_platforms(record: dict) -> list[dict]:
    """The same measurements attributed to all three platforms.

    A merge of identical inputs is the control case: it must report zero
    error, and every test that expects a failure gets there by perturbing one
    copy of this.
    """
    records = []
    for key in PLATFORM_KEYS:
        clone = copy.deepcopy(record)
        clone["platform"] = key
        records.append(clone)
    return records


class TestVectors:
    def test_every_vector_has_a_unique_id(self) -> None:
        ids = [vector.vector_id for vector in VECTORS]
        assert len(ids) == len(set(ids))
        assert len(ids) >= 8, "a golden matrix of a handful of vectors proves little"

    def test_measurements_repeat_exactly_within_one_host(self) -> None:
        """Determinism on one machine is the precondition for comparing three.

        A vector seeded from the clock, or one that leaked state from a
        previous run, would make every cross-platform difference unreadable.
        """
        for vector in CHEAP_VECTORS:
            first = measure_vector(vector)
            second = measure_vector(vector)
            assert first == second, vector.vector_id

    def test_stimuli_are_hashed_alongside_results(self) -> None:
        row = measure_vector(CHEAP_VECTORS[0])
        assert row["stimulus_sha256"] != row["result_sha256"]
        assert len(row["stimulus_sha256"]) == 64

    def test_probes_sample_the_whole_signal(self) -> None:
        indices = probe_indices(48_000, 256)
        assert indices[0] == 0
        assert indices[-1] == 47_999
        assert len(indices) == 256
        assert list(indices) == sorted(set(indices))

    def test_short_signals_are_probed_in_full(self) -> None:
        assert list(probe_indices(4, 256)) == [0, 1, 2, 3]

    def test_platform_key_maps_the_ci_runner_names(self) -> None:
        assert platform_key("Linux") == "linux"
        assert platform_key("Darwin") == "macos"
        assert platform_key("Windows") == "windows"
        with pytest.raises(ValueError):
            platform_key("Plan9")

    def test_record_names_the_dependency_versions_it_measured_with(
        self, linux_record: dict
    ) -> None:
        runtime = linux_record["runtime"]
        assert {"numpy", "scipy", "python", "src_backend"} <= set(runtime)
        assert linux_record["platform"] in PLATFORM_KEYS


class TestMerge:
    def test_identical_records_agree_exactly(self, linux_record: dict) -> None:
        report = merge_records(_three_platforms(linux_record))
        assert report["status"] == "pass"
        assert report["maximum_absolute_error"] == 0.0
        assert set(report["platforms"]) == {"linux", "macos", "windows"}
        assert report["bit_identical_vectors"] == [v.vector_id for v in CHEAP_VECTORS]
        assert all(report["checks"].values())

    def test_report_answers_the_questions_the_e2_case_asks(self, linux_record: dict) -> None:
        report = merge_records(_three_platforms(linux_record))
        assert set(report["platforms"]) == {"linux", "macos", "windows"}
        assert report["maximum_absolute_error"] <= 1e-9
        assert report["status"] == "pass"

    def test_a_last_ulp_difference_still_passes(self, linux_record: dict) -> None:
        """Bit-exactness is not the bar; agreement to 1e-9 is.

        Different libm implementations round transcendentals differently, and
        a report that failed on that would fail forever for no audible reason.
        """
        records = _three_platforms(linux_record)
        records[1]["vectors"][0]["probes"][7] += 1e-13
        records[1]["vectors"][0]["result_sha256"] = "0" * 64
        report = merge_records(records)
        assert report["status"] == "pass"
        assert 0.0 < report["maximum_absolute_error"] < TOLERANCE_ABSOLUTE
        assert report["bit_identical_vectors"] == ["true-peak-polyphase"]

    def test_a_real_divergence_fails_and_is_attributed(self, linux_record: dict) -> None:
        records = _three_platforms(linux_record)
        records[2]["vectors"][0]["probes"][11] += 1e-6
        report = merge_records(records)
        assert report["status"] == "fail"
        assert report["checks"]["values_within_tolerance"] is False
        assert report["maximum_absolute_error"] == pytest.approx(1e-6, rel=1e-6)
        failed = [row for row in report["vectors"] if not row["within_tolerance"]]
        assert [row["vector_id"] for row in failed] == ["eq-magnitude-response"]
        assert failed[0]["pairwise_maximum_absolute_error"]["linux-vs-windows"] == pytest.approx(
            1e-6, rel=1e-6
        )
        assert failed[0]["pairwise_maximum_absolute_error"]["linux-vs-macos"] == 0.0

    def test_a_missing_platform_cannot_pass(self, linux_record: dict) -> None:
        records = _three_platforms(linux_record)[:2]
        report = merge_records(records)
        assert report["status"] == "fail"
        assert report["missing_platforms"] == ["windows"]
        assert set(report["platforms"]) != {"linux", "macos", "windows"}

    def test_diverging_stimuli_are_not_a_comparison(self, linux_record: dict) -> None:
        """Equal outputs mean nothing if the runners were fed different inputs."""
        records = _three_platforms(linux_record)
        records[1]["vectors"][0]["stimulus_probes"][3] += 0.5
        report = merge_records(records)
        assert report["status"] == "fail"
        assert report["checks"]["identical_stimuli"] is False
        assert report["vectors"][0]["identical_stimulus"] is False
        assert report["vectors"][0]["stimulus_maximum_absolute_error"] == pytest.approx(0.5)

    def test_a_stimulus_that_differs_only_in_the_last_ulp_is_still_the_same_question(
        self, linux_record: dict
    ) -> None:
        """libm rounding makes the stimulus digests differ; that is not a fault."""
        records = _three_platforms(linux_record)
        records[1]["vectors"][0]["stimulus_probes"][3] += 1e-15
        records[1]["vectors"][0]["stimulus_sha256"] = "f" * 64
        report = merge_records(records)
        assert report["status"] == "pass"
        assert report["vectors"][0]["identical_stimulus"] is True
        assert report["vectors"][0]["bit_identical_stimulus"] is False

    def test_dependency_skew_invalidates_the_comparison(self, linux_record: dict) -> None:
        records = _three_platforms(linux_record)
        records[2]["runtime"]["numpy"] = "1.26.0"
        report = merge_records(records)
        assert report["status"] == "fail"
        assert report["checks"]["pinned_dependency_versions_agree"] is False

    def test_a_vector_missing_from_one_runner_is_not_silently_dropped(
        self, linux_record: dict
    ) -> None:
        records = _three_platforms(linux_record)
        records[1]["vectors"] = records[1]["vectors"][:1]
        report = merge_records(records)
        assert report["status"] == "fail"
        assert report["checks"]["same_vector_set"] is False

    def test_two_records_from_the_same_platform_are_rejected(self, linux_record: dict) -> None:
        records = _three_platforms(linux_record)
        records[1]["platform"] = "linux"
        with pytest.raises(ValueError, match="linux"):
            merge_records(records)


class TestPrecision:
    """The bar a vector is held to has to match the format it computes in."""

    def test_float64_paths_are_held_to_the_absolute_tolerance(self) -> None:
        limit, basis = vector_tolerance("float64", 0.9)
        assert limit == TOLERANCE_ABSOLUTE
        assert "absolute" in basis

    def test_float32_paths_are_held_to_a_few_ulps_of_float32(self) -> None:
        limit, basis = vector_tolerance("float32", 0.9)
        assert limit == pytest.approx(FLOAT32_TOLERANCE_ULPS * float(np.spacing(np.float32(0.9))))
        assert limit > TOLERANCE_ABSOLUTE
        assert "float32 ulp" in basis

    def test_one_ulp_of_disagreement_in_a_float32_path_passes(
        self, linux_record: dict
    ) -> None:
        """What the macOS arm64 runner actually does to the resampler.

        A float32 signal has no bits in which to disagree more finely, so a
        one-ulp difference is the format's resolution, not a DSP divergence.
        """
        records = _three_platforms(linux_record)
        for record in records:
            record["vectors"][0]["working_precision"] = "float32"
        ulp = float(np.spacing(np.float32(records[0]["vectors"][0]["peak_absolute"])))
        records[1]["vectors"][0]["probes"][5] += ulp
        report = merge_records(records)
        assert report["status"] == "pass"
        assert report["vectors"][0]["tolerance_absolute"] == pytest.approx(
            FLOAT32_TOLERANCE_ULPS * ulp
        )
        assert report["maximum_absolute_error_by_precision"]["float32"] == pytest.approx(ulp)
        # The headline figure is the float64 one the 1e-9 bar applies to, and
        # the report says so rather than leaving a reader to infer it.
        assert report["maximum_absolute_error"] == 0.0
        assert report["maximum_absolute_error_all_vectors"] == pytest.approx(ulp)
        assert "float32" in report["maximum_absolute_error_scope"]

    def test_a_float32_path_off_by_many_ulps_still_fails(self, linux_record: dict) -> None:
        records = _three_platforms(linux_record)
        for record in records:
            record["vectors"][0]["working_precision"] = "float32"
        ulp = float(np.spacing(np.float32(records[0]["vectors"][0]["peak_absolute"])))
        records[1]["vectors"][0]["probes"][5] += 20 * ulp
        report = merge_records(records)
        assert report["status"] == "fail"
        assert report["checks"]["values_within_tolerance"] is False

    def test_platforms_disagreeing_about_the_precision_is_itself_a_failure(
        self, linux_record: dict
    ) -> None:
        records = _three_platforms(linux_record)
        records[2]["vectors"][0]["working_precision"] = "float32"
        report = merge_records(records)
        assert report["status"] == "fail"
        assert report["checks"]["working_precisions_agree"] is False

    def test_python_patch_levels_may_differ_across_runner_images(
        self, linux_record: dict
    ) -> None:
        """setup-python resolves 3.12 to a different patch per OS, routinely."""
        records = _three_platforms(linux_record)
        records[0]["runtime"]["python"] = "3.12.14"
        records[1]["runtime"]["python"] = "3.12.10"
        report = merge_records(records)
        assert report["checks"]["pinned_dependency_versions_agree"] is True

    def test_a_different_python_minor_version_is_not_the_same_matrix(
        self, linux_record: dict
    ) -> None:
        records = _three_platforms(linux_record)
        records[1]["runtime"]["python"] = "3.13.1"
        report = merge_records(records)
        assert report["checks"]["pinned_dependency_versions_agree"] is False


class TestCommandLine:
    def test_record_then_merge_round_trips_through_files(self, tmp_path: Path) -> None:
        paths = []
        for key in PLATFORM_KEYS:
            path = tmp_path / f"{key}.json"
            assert main(["record", "--output", str(path), "--provenance", f"os={key}"]) == 0
            record = json.loads(path.read_text(encoding="utf-8"))
            # One host can only record its own platform, so the round trip
            # relabels the copies; the CI matrix is what produces three real
            # ones, and merge_records is identical either way.
            record["platform"] = key
            path.write_text(json.dumps(record), encoding="utf-8")
            paths.append(str(path))

        output = tmp_path / "report.json"
        assert main(["merge", *paths, "--output", str(output)]) == 0
        report = json.loads(output.read_text(encoding="utf-8"))
        assert report["status"] == "pass"
        assert set(report["platforms"]) == {"linux", "macos", "windows"}
        assert report["platforms"]["macos"]["provenance"]["os"] == "macos"

    def test_merge_exits_nonzero_when_the_platforms_disagree(self, tmp_path: Path) -> None:
        paths = []
        for index, key in enumerate(PLATFORM_KEYS):
            record = build_record(CHEAP_VECTORS)
            record["platform"] = key
            if index == 1:
                record["vectors"][0]["probes"][0] += 0.25
            path = tmp_path / f"{key}.json"
            path.write_text(json.dumps(record), encoding="utf-8")
            paths.append(str(path))
        assert main(["merge", *paths, "--output", str(tmp_path / "report.json")]) == 1

    def test_merge_rejects_a_file_that_is_not_a_platform_record(self, tmp_path: Path) -> None:
        stray = tmp_path / "stray.json"
        stray.write_text(json.dumps({"kind": "something-else"}), encoding="utf-8")
        with pytest.raises(ValueError, match="not a golden platform record"):
            main(["merge", str(stray), "--output", str(tmp_path / "report.json")])
