"""EBU Tech 3342 LRA compliance skeleton and first reference case."""

from __future__ import annotations

import pytest

from tools.ebu_r128 import loudness_range
from tools.ebu_vectors import SAMPLE_RATE, TECH_3342_VECTORS, synthesize_segments

# Tech 3342 specifies ±1 LU for LRA (not the ±0.1 LU loudness tolerance in 3341).
TECH_3342_TOLERANCE_LU = 1.0


def test_lra_case_1_two_tone_levels() -> None:
    vector = TECH_3342_VECTORS[0]
    audio = synthesize_segments(vector.segments)

    measured = loudness_range(audio, SAMPLE_RATE)

    assert measured == pytest.approx(
        vector.expected_lra_lu,
        abs=TECH_3342_TOLERANCE_LU,
    )


@pytest.mark.parametrize("vector", TECH_3342_VECTORS)
def test_remaining_vector_definitions_are_well_formed(vector) -> None:
    """Keep cases 2/3 visible until the product-meter adapter is connected."""
    assert vector.case_id.startswith("3342-")
    assert vector.expected_lra_lu > 0.0
    assert len(vector.segments) >= 2
