"""True-peak ceiling compliance for :class:`LimiterEffect` (SOTA item A6).

Clipping every stored sample to the ceiling satisfies a sample-peak limiter and
still reconstructs above the ceiling in a converter, so the stimuli here are
sinusoids whose sample grid straddles the crest: the peak between the samples
sits a known number of dB above the largest sample, 3.01 dB at a quarter of the
sample rate. :mod:`tools.limiter_isp` derives that overshoot in closed form,
and the first test below refuses to accept a stimulus that does not exhibit it,
so a synthesis mistake cannot quietly turn the rest of the suite into a check
that a limiter passes signals it never needed to touch.

Running this module writes ``.agent_workspace/v1.0/limiter-isp-report.json``,
which is the evidence the A6 acceptance case reads.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
for _import_root in (REPOSITORY_ROOT, REPOSITORY_ROOT / "audio-studio"):
    if str(_import_root) not in sys.path:
        sys.path.insert(0, str(_import_root))

import numpy as np
import pytest
from audio_studio.dsp.util import linear_to_db, true_peak_level

from tools.limiter_isp import (
    DEFAULT_OUTPUT,
    ISP_CASES,
    MAX_UNDERSHOOT_DB,
    METER_OVERSAMPLE,
    NEAR_NYQUIST_FRACTION,
    TOLERANCE_DB,
    IspCase,
    limiter_for,
    measure_all,
    reference_true_peak_dbtp,
    synthesize,
    write_report,
)

REPORT_PATH = REPOSITORY_ROOT / DEFAULT_OUTPUT

CASE_PARAMS = [pytest.param(case, id=case.case_id) for case in ISP_CASES]


@pytest.fixture(scope="module")
def report() -> dict[str, Any]:
    """Measure every case once and publish the run as the A6 evidence file."""
    document = measure_all()
    write_report(document, REPORT_PATH)
    return document


@pytest.fixture(scope="module")
def rows(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["case_id"]: row for row in report["cases"]}


def _stimulus(case: IspCase) -> np.ndarray:
    limiter = limiter_for(case)
    return synthesize(case, tail_samples=limiter.latency_samples(case.sample_rate) + 64)


@pytest.mark.parametrize("case", CASE_PARAMS)
def test_stimulus_has_the_inter_sample_peak_it_claims(case: IspCase) -> None:
    """The stimulus overshoots its own samples by the closed-form amount."""
    stimulus = _stimulus(case)

    sample_peak = float(linear_to_db(np.max(np.abs(stimulus))))
    true_peak = reference_true_peak_dbtp(stimulus)

    assert true_peak == pytest.approx(case.input_true_peak_dbtp, abs=0.001)
    assert true_peak - sample_peak == pytest.approx(case.expected_overshoot_db, abs=0.001)
    assert case.expected_overshoot_db <= 3.0103 + 1e-9, "no sinusoid overshoots further"


@pytest.mark.parametrize("case", CASE_PARAMS)
def test_unlimited_stimulus_would_breach_the_ceiling(case: IspCase) -> None:
    """Control: every case gives the limiter something it has to catch."""
    stimulus = _stimulus(case)

    assert reference_true_peak_dbtp(stimulus) > case.ceiling_dbtp + 0.1


@pytest.mark.parametrize("case", CASE_PARAMS)
def test_limited_output_holds_the_true_peak_ceiling(
    case: IspCase, rows: dict[str, dict[str, Any]]
) -> None:
    """Both meters read the limited output at or below the ceiling."""
    row = rows[case.case_id]

    assert row["output_true_peak_dbtp"] <= case.ceiling_dbtp + TOLERANCE_DB
    assert row["output_true_peak_reference_dbtp"] <= case.ceiling_dbtp + TOLERANCE_DB
    assert row["status"] == "pass", row["checks"]


@pytest.mark.parametrize("case", CASE_PARAMS)
def test_limiter_reaches_the_ceiling_rather_than_ducking_under_it(
    case: IspCase, rows: dict[str, dict[str, Any]]
) -> None:
    """A limiter that simply turned everything down would pass the check above."""
    row = rows[case.case_id]

    assert row["headroom_below_ceiling_db"] <= MAX_UNDERSHOOT_DB
    assert row["gain_reduction_db"] > 0.0


def test_ceiling_holds_across_irregular_streaming_blocks() -> None:
    """Block boundaries must not open a hole in the ceiling."""
    case = ISP_CASES[0]
    limiter = limiter_for(case)
    stimulus = synthesize(
        case, tail_samples=limiter.latency_samples(case.sample_rate) + 64
    )
    offline = limiter.process(stimulus, case.sample_rate, channels_last=False)

    limiter.reset()
    limiter.prepare(case.sample_rate, case.channels)
    blocks, offset = [], 0
    for size in (1, 17, 256, 509, 31) * 200:
        if offset >= stimulus.shape[-1]:
            break
        blocks.append(
            limiter.process_block(
                stimulus[:, offset : offset + size],
                case.sample_rate,
                channels_last=False,
            )
        )
        offset += size
    streamed = np.concatenate(blocks, axis=-1)

    assert streamed.shape == offline.shape
    assert np.array_equal(streamed, offline)
    assert reference_true_peak_dbtp(streamed) <= case.ceiling_dbtp + TOLERANCE_DB


def test_stereo_limiting_is_linked_so_the_image_does_not_move() -> None:
    """One channel's inter-sample peak must duck both channels by the same gain."""
    case = IspCase("stereo-link-probe", 48_000, 1, 4, -1.0, 0.0)
    limiter = limiter_for(case)
    latency = limiter.latency_samples(case.sample_rate)
    mono = synthesize(case, tail_samples=latency + 64)[0]
    stimulus = np.stack((mono, 0.25 * mono))

    limited = limiter.process(stimulus, case.sample_rate, channels_last=False)

    active = slice(latency + 100, mono.size - latency - 100)
    ratio = limited[0, active] / limited[1, active]
    assert np.allclose(ratio, 4.0, atol=1e-9)
    assert reference_true_peak_dbtp(limited) <= case.ceiling_dbtp + TOLERANCE_DB


def test_near_nyquist_cases_are_the_ones_that_need_a_finer_detector(
    report: dict[str, Any],
) -> None:
    """The 4x floor BS.1770-4 allows is not enough close to Nyquist.

    Pinning this keeps the per-case ``detector_oversample`` in
    :data:`tools.limiter_isp.ISP_CASES` honest: it is a documented consequence
    of the interpolator, not a knob tuned until the suite went green.
    """
    sensitivity = report["detector_oversample_sensitivity"]
    errors = {
        row["detector_oversample"]: row["error_above_ceiling_db"]
        for row in sensitivity["readings"]
    }

    assert sensitivity["tone_fraction_of_nyquist"] > NEAR_NYQUIST_FRACTION
    assert errors[4] > TOLERANCE_DB, "4x would have to hold for the default to suffice"
    assert errors[8] <= 0.0
    assert errors[16] <= 0.0

    for case in ISP_CASES:
        expected = 8 if case.is_near_nyquist else 4
        assert case.detector_oversample == expected, case.case_id


def test_product_meter_and_independent_reconstruction_agree(
    report: dict[str, Any],
) -> None:
    """The two read-outs bound the same peak, so neither alone carries the claim."""
    for row in report["cases"]:
        product = row["output_true_peak_dbtp"]
        reference = row["output_true_peak_reference_dbtp"]
        assert product == pytest.approx(reference, abs=0.5), row["case_id"]
        assert reference >= row["output_sample_peak_dbfs"] - 1e-6, row["case_id"]


def test_run_publishes_a_passing_evidence_report(report: dict[str, Any]) -> None:
    """The artifact the A6 acceptance case reads is written by this run."""
    assert REPORT_PATH.is_file()
    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["measurement"]["product_meter_oversample"] == METER_OVERSAMPLE
    assert {row["case_id"] for row in report["cases"]} == {
        case.case_id for case in ISP_CASES
    }
    assert report["worst_case_headroom_db"] > 0.0
    assert len({row["sample_rate_hz"] for row in report["cases"]}) >= 3
    assert any(row["channels"] == 2 for row in report["cases"])


def test_meter_read_back_is_not_the_limiters_own_detector() -> None:
    """The reference oracle is exact on a signal whose peak is known outright."""
    case = ISP_CASES[0]
    stimulus = _stimulus(case)

    reference = reference_true_peak_dbtp(stimulus)
    product = float(linear_to_db(true_peak_level(stimulus, METER_OVERSAMPLE)))

    assert reference == pytest.approx(0.0, abs=1e-4)
    assert product != pytest.approx(reference, abs=1e-9)
