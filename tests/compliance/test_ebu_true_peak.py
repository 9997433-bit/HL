"""EBU Tech 3341 true-peak compliance for the product loudness report."""

from __future__ import annotations

import numpy as np
import pytest
from audio_studio.dsp.loudness import LoudnessMeter

from tools.ebu_vectors import TECH_3341_TRUE_PEAK_VECTORS, synthesize_true_peak


def test_vectors_include_at_least_two_known_inter_sample_peaks() -> None:
    isp_vectors = [
        vector
        for vector in TECH_3341_TRUE_PEAK_VECTORS
        if vector.expected_dbtp - vector.expected_sample_peak_dbfs >= 0.5
    ]
    assert len(isp_vectors) >= 2

    for vector in isp_vectors:
        audio = synthesize_true_peak(vector)
        sample_peak_dbfs = float(20.0 * np.log10(np.max(np.abs(audio))))
        assert sample_peak_dbfs == pytest.approx(vector.expected_sample_peak_dbfs, abs=0.01)


@pytest.mark.parametrize(
    "vector",
    TECH_3341_TRUE_PEAK_VECTORS,
    ids=lambda item: item.case_id,
)
def test_product_loudness_report_true_peak_is_within_tech_3341_tolerance(vector) -> None:
    audio = synthesize_true_peak(vector)

    report = LoudnessMeter(vector.sample_rate).analyze(audio, channels_last=True)

    assert (
        vector.minimum_accepted_dbtp
        <= report.true_peak_dbtp
        <= vector.maximum_accepted_dbtp
    )
    assert report.true_peak_dbtp >= report.sample_peak_dbfs - 1e-6
