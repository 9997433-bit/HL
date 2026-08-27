"""EBU Tech 3342 loudness range vectors.

As in the Tech 3341 suite, every case runs through both the independent oracle
and the application meter. Tech 3342 specifies +-1 LU here rather than the
+-0.1 LU of a loudness reading, because the range is built from a percentile of
a distribution and moves with the block grid.
"""

from __future__ import annotations

import numpy as np
import pytest
from audio_studio.dsp.loudness import LoudnessMeter

from tools.ebu_r128 import loudness_range
from tools.ebu_vectors import (
    LRA_TOLERANCE_LU,
    SAMPLE_RATE,
    TECH_3342_VECTORS,
    synthesize_segments,
)

TECH_3342_TOLERANCE_LU = LRA_TOLERANCE_LU

METERS = ("oracle", "product")


def measure_lra(meter: str, audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> float:
    if meter == "oracle":
        return loudness_range(audio, sample_rate)
    return LoudnessMeter(sample_rate).loudness_range(audio, channels_last=True)


@pytest.mark.parametrize("meter", METERS)
@pytest.mark.parametrize("vector", TECH_3342_VECTORS, ids=lambda item: item.case_id)
def test_loudness_range_reference_vectors(vector, meter: str) -> None:
    audio = synthesize_segments(vector.segments)

    measured = measure_lra(meter, audio)

    assert measured == pytest.approx(vector.expected_lra_lu, abs=vector.tolerance_lu)


@pytest.mark.parametrize("meter", METERS)
def test_a_steady_programme_has_no_range(meter: str) -> None:
    audio = synthesize_segments(((30.0, -23.0),))
    assert measure_lra(meter, audio) < 1.0


def test_the_two_implementations_agree_on_every_vector() -> None:
    """Different code, same standard: the readings have to land together."""
    for vector in TECH_3342_VECTORS:
        audio = synthesize_segments(vector.segments)
        assert measure_lra("product", audio) == pytest.approx(
            measure_lra("oracle", audio), abs=TECH_3342_TOLERANCE_LU
        )


def test_the_range_ignores_a_passage_below_the_relative_gate() -> None:
    """Tech 3342 gates 20 LU down, so a fade to nothing is not 60 LU of range."""
    audio = synthesize_segments(((20.0, -23.0), (20.0, -80.0)))
    assert LoudnessMeter(SAMPLE_RATE).loudness_range(audio, channels_last=True) < 1.0
