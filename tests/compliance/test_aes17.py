"""AES17 THD+N compliance for the core signal paths (SOTA item A8).

:mod:`tools.aes17` drives each measured path with the standard's 997 Hz tone,
subtracts a least-squares-fitted fundamental (a zero-width notch), and reads
the residual through the 20 Hz - 20 kHz measurement bandwidth. The tests here
hold every path to its published limit and hold the two dithered paths to the
closed-form TPDF figure, so a regression in any of them fails a specific case
rather than a summary flag.

Running this module writes ``.agent_workspace/round3/aes17-report.json``,
which is the evidence the A8 acceptance case reads.
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

from tools.aes17 import (
    AES17_CASES,
    ANALYSIS_SECONDS,
    BAND_HIGH_HZ,
    BAND_LOW_HZ,
    DEFAULT_OUTPUT,
    FUNDAMENTAL_HZ,
    THEORY_TOLERANCE_DB,
    Aes17Case,
    measure_all,
    measure_thd_plus_n,
    synthesize_stimulus,
    tpdf_expected_thd_plus_n_db,
    write_report,
)

REPORT_PATH = REPOSITORY_ROOT / DEFAULT_OUTPUT

CASE_PARAMS = [pytest.param(case, id=case.case_id) for case in AES17_CASES]


@pytest.fixture(scope="module")
def report() -> dict[str, Any]:
    """Measure every case once and publish the run as the A8 evidence file."""
    document = measure_all()
    write_report(document, REPORT_PATH)
    return document


@pytest.fixture(scope="module")
def rows(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["case_id"]: row for row in report["cases"]}


def test_stimulus_is_the_aes17_tone() -> None:
    """997 Hz at the requested level, long enough for the analysis window."""
    stimulus = synthesize_stimulus(48_000, -1.0)

    assert FUNDAMENTAL_HZ == 997.0
    assert stimulus.size >= round(48_000 * ANALYSIS_SECONDS)
    assert float(np.max(np.abs(stimulus))) == pytest.approx(
        10.0 ** (-1.0 / 20.0), rel=1e-6
    )
    # The gates start and end the tone in silence.
    assert stimulus[0] == 0.0 and abs(stimulus[-1]) < 1e-9


def test_analyzer_reads_a_known_noise_floor() -> None:
    """A synthetic DUT that adds white noise of known RMS must read that RMS.

    This calibrates the whole chain — notch, band limit, RMS — against a
    residual whose level is known independently of any product code.
    """
    injected_dbfs = -100.0
    rng = np.random.default_rng(20)

    def noisy(stimulus: np.ndarray, _sample_rate: int) -> np.ndarray:
        noise = 10.0 ** (injected_dbfs / 20.0) * rng.standard_normal(stimulus.size)
        return stimulus.astype(np.float64) + noise

    reading = measure_thd_plus_n(noisy, 48_000, -1.0)

    # White noise to Nyquist loses the out-of-band fraction to the 20 kHz cap.
    band_fraction = (BAND_HIGH_HZ - BAND_LOW_HZ) / 24_000.0
    expected_residual = injected_dbfs + 10.0 * np.log10(band_fraction)
    assert reading["residual_rms_dbfs"] == pytest.approx(expected_residual, abs=0.3)


def test_analyzer_detects_gross_distortion(report: dict[str, Any]) -> None:
    """The clipped control must read as badly distorted, or nothing here counts."""
    control = report["analyzer_control"]

    assert control["distortion_detected"] is True
    assert control["thd_plus_n_db"] >= control["minimum_expected_db"]
    assert control["status"] == "pass"


@pytest.mark.parametrize("case", CASE_PARAMS)
def test_path_meets_its_thd_plus_n_limit(
    case: Aes17Case, rows: dict[str, dict[str, Any]]
) -> None:
    row = rows[case.case_id]

    assert row["thd_plus_n_db"] <= case.limit_db, row["checks"]
    assert row["status"] == "pass", row["checks"]


@pytest.mark.parametrize("case", CASE_PARAMS)
def test_fundamental_comes_through_at_the_stimulus_level(
    case: Aes17Case, rows: dict[str, dict[str, Any]]
) -> None:
    """A path that attenuated or lost the tone is not being measured at all."""
    row = rows[case.case_id]

    assert row["fundamental_dbfs"] == pytest.approx(case.stimulus_level_dbfs, abs=0.1)


def test_dithered_paths_sit_on_tpdf_theory(rows: dict[str, dict[str, Any]]) -> None:
    """Quantized paths must match the closed-form dither floor, both ways.

    A figure meaningfully *below* theory would mean the dither is missing or
    the analyzer is dropping residual, so the tolerance is two-sided.
    """
    theory_cases = [case for case in AES17_CASES if case.expected_db is not None]
    assert len(theory_cases) >= 2, "at least 16- and 24-bit paths carry theory"

    for case in theory_cases:
        row = rows[case.case_id]
        assert row["thd_plus_n_db"] == pytest.approx(
            case.expected_db, abs=THEORY_TOLERANCE_DB
        ), case.case_id


def test_expected_figures_are_the_published_theory() -> None:
    """Pin the closed form so a silent constant edit cannot move the gates.

    16-bit TPDF at -1 dBFS reads near the textbook ~-92.7 dB once the
    20 Hz - 20 kHz bandwidth is accounted for; 24 bits buys 8 * 6.02 dB more.
    """
    sixteen = tpdf_expected_thd_plus_n_db(16, 44_100, -1.0)
    twenty_four = tpdf_expected_thd_plus_n_db(24, 44_100, -1.0)

    assert sixteen == pytest.approx(-92.75, abs=0.05)
    assert twenty_four - sixteen == pytest.approx(-8 * 6.0206, abs=1e-6)


def test_run_publishes_a_passing_evidence_report(report: dict[str, Any]) -> None:
    """The artifact the A8 acceptance case reads is written by this run."""
    assert REPORT_PATH.is_file()
    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert {row["case_id"] for row in report["cases"]} == {
        case.case_id for case in AES17_CASES
    }
    assert len({row["sample_rate_hz"] for row in report["cases"]}) >= 3
    assert report["worst_thd_plus_n_margin_db"] > 0.0
