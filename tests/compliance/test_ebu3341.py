"""EBU Tech 3341 minimum-requirements reference vectors.

These tests validate the independent oracle and generated vectors.  They are
the adapter seam for the production meter: replace ``integrated_loudness`` (and
the window helpers) with the application implementation once it is available.
Passing this file alone is not a claim that the application meter is compliant.
"""

from __future__ import annotations

import pytest

from tools.ebu_r128 import integrated_loudness, maximum_window_loudness
from tools.ebu_vectors import SAMPLE_RATE, TECH_3341_VECTORS, synthesize_segments

TECH_3341_TOLERANCE_LU = 0.1


@pytest.mark.parametrize("vector", TECH_3341_VECTORS, ids=lambda item: item.case_id)
def test_integrated_loudness_reference_vectors(vector) -> None:
    audio = synthesize_segments(vector.segments)

    measured = integrated_loudness(audio, SAMPLE_RATE)

    assert measured == pytest.approx(
        vector.expected_integrated_lufs,
        abs=TECH_3341_TOLERANCE_LU,
    )


@pytest.mark.parametrize("vector", TECH_3341_VECTORS[:2], ids=lambda item: item.case_id)
def test_stationary_tone_momentary_and_short_term(vector) -> None:
    audio = synthesize_segments(vector.segments)

    momentary = maximum_window_loudness(
        audio,
        SAMPLE_RATE,
        window_seconds=0.4,
    )
    short_term = maximum_window_loudness(
        audio,
        SAMPLE_RATE,
        window_seconds=3.0,
    )

    assert momentary == pytest.approx(
        vector.expected_integrated_lufs,
        abs=TECH_3341_TOLERANCE_LU,
    )
    assert short_term == pytest.approx(
        vector.expected_integrated_lufs,
        abs=TECH_3341_TOLERANCE_LU,
    )
