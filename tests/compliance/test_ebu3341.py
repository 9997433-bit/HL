"""EBU Tech 3341 minimum-requirements reference vectors.

Every vector runs twice: once through the independent oracle in
``tools.ebu_r128``, which keeps the vectors themselves honest, and once through
the application's own :class:`~audio_studio.dsp.loudness.LoudnessMeter`, which
is the thing being certified. A vector that only the oracle passes is a bug in
the product; a vector that only the product passes is a bug in the vector.

Covered: programme loudness (both gates), the momentary and short-term windows
and their 10 Hz refresh, channel weighting including the LFE exclusion, and
true peak per BS.1770-4 Annex 2.
"""

from __future__ import annotations

import numpy as np
import pytest
from audio_studio.dsp.loudness import LoudnessMeter

from tools.ebu_r128 import integrated_loudness, maximum_window_loudness
from tools.ebu_vectors import (
    SAMPLE_RATE,
    TECH_3341_CHANNEL_VECTORS,
    TECH_3341_TRUE_PEAK_VECTORS,
    TECH_3341_VECTORS,
    TOLERANCE_LU,
    synthesize_channels,
    synthesize_segments,
    synthesize_true_peak,
)

#: Kept for anything importing the old name.
TECH_3341_TOLERANCE_LU = TOLERANCE_LU

METERS = ("oracle", "product")


def measure_integrated(meter: str, audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> float:
    """Integrated loudness from whichever implementation is under test."""
    if meter == "oracle":
        return integrated_loudness(audio, sample_rate)
    return LoudnessMeter(sample_rate).integrated(audio, channels_last=True)


def measure_window(
    meter: str,
    audio: np.ndarray,
    window_seconds: float,
    sample_rate: int = SAMPLE_RATE,
) -> float:
    """Maximum ungated momentary (0.4 s) or short-term (3 s) loudness."""
    if meter == "oracle":
        return maximum_window_loudness(audio, sample_rate, window_seconds=window_seconds)
    product = LoudnessMeter(sample_rate)
    _, values = product.block_loudness(
        audio, window_s=window_seconds, step_s=0.1, channels_last=True
    )
    return float(np.max(values))


@pytest.mark.parametrize("meter", METERS)
@pytest.mark.parametrize("vector", TECH_3341_VECTORS, ids=lambda item: item.case_id)
def test_integrated_loudness_reference_vectors(vector, meter: str) -> None:
    audio = synthesize_segments(vector.segments)

    measured = measure_integrated(meter, audio)

    assert measured == pytest.approx(
        vector.expected_integrated_lufs,
        abs=vector.tolerance_lu,
    )


@pytest.mark.parametrize("vector", TECH_3341_VECTORS, ids=lambda item: item.case_id)
def test_the_two_implementations_agree_far_inside_the_tolerance(vector) -> None:
    """Two independent meters reading the same standard should not merely both
    land within +-0.1 LU of the answer; they should land on each other."""
    audio = synthesize_segments(vector.segments)

    assert measure_integrated("product", audio) == pytest.approx(
        measure_integrated("oracle", audio), abs=0.01
    )


@pytest.mark.parametrize("meter", METERS)
@pytest.mark.parametrize("vector", TECH_3341_VECTORS[:2], ids=lambda item: item.case_id)
def test_stationary_tone_momentary_and_short_term(vector, meter: str) -> None:
    audio = synthesize_segments(vector.segments)

    momentary = measure_window(meter, audio, 0.4)
    short_term = measure_window(meter, audio, 3.0)

    assert momentary == pytest.approx(
        vector.expected_integrated_lufs,
        abs=vector.tolerance_lu,
    )
    assert short_term == pytest.approx(
        vector.expected_integrated_lufs,
        abs=vector.tolerance_lu,
    )


@pytest.mark.parametrize("meter", METERS)
@pytest.mark.parametrize(
    "vector", TECH_3341_CHANNEL_VECTORS, ids=lambda item: item.case_id
)
def test_channel_weighting_vectors(vector, meter: str) -> None:
    audio = synthesize_channels(vector.levels_dbfs, vector.duration_s)

    measured = measure_integrated(meter, audio)

    assert measured == pytest.approx(
        vector.expected_integrated_lufs,
        abs=vector.tolerance_lu,
    )


def test_the_lfe_is_excluded_rather_than_merely_quiet() -> None:
    """Tech 3341's 5.1 case is only meaningful if the LFE is really ignored."""
    quiet_lfe, loud_lfe = TECH_3341_CHANNEL_VECTORS[1], TECH_3341_CHANNEL_VECTORS[2]

    product = LoudnessMeter(SAMPLE_RATE)
    without = product.integrated(
        synthesize_channels(quiet_lfe.levels_dbfs, quiet_lfe.duration_s), channels_last=True
    )
    with_lfe = product.integrated(
        synthesize_channels(loud_lfe.levels_dbfs, loud_lfe.duration_s), channels_last=True
    )

    assert with_lfe == pytest.approx(without, abs=1e-9)


class TestMeterDynamics:
    """Tech 3341 asks for a 10 Hz display that settles inside its own window."""

    @staticmethod
    def stepped() -> np.ndarray:
        return synthesize_segments(((10.0, -30.0), (10.0, -20.0)))

    def test_the_momentary_display_refreshes_at_least_ten_times_a_second(self) -> None:
        times, _ = LoudnessMeter(SAMPLE_RATE).momentary(self.stepped(), channels_last=True)
        assert np.max(np.diff(times)) <= 0.1 + 1e-9

    def test_the_short_term_display_refreshes_at_least_ten_times_a_second(self) -> None:
        times, _ = LoudnessMeter(SAMPLE_RATE).short_term(self.stepped(), channels_last=True)
        assert np.max(np.diff(times)) <= 0.1 + 1e-9

    def test_momentary_settles_within_its_own_window_of_a_step(self) -> None:
        times, values = LoudnessMeter(SAMPLE_RATE).momentary(
            self.stepped(), channels_last=True
        )
        before = values[(times > 5.0) & (times <= 10.0)]
        after = values[times >= 10.4]

        assert before == pytest.approx(-30.0, abs=TOLERANCE_LU)
        assert after == pytest.approx(-20.0, abs=TOLERANCE_LU)

    def test_short_term_settles_within_its_own_window_of_a_step(self) -> None:
        times, values = LoudnessMeter(SAMPLE_RATE).short_term(
            self.stepped(), channels_last=True
        )
        assert values[times >= 13.0] == pytest.approx(-20.0, abs=TOLERANCE_LU)


@pytest.mark.parametrize(
    "vector", TECH_3341_TRUE_PEAK_VECTORS, ids=lambda item: item.case_id
)
def test_true_peak_reference_vectors(vector) -> None:
    """BS.1770-4 Annex 2: the peak of the waveform, not of the samples."""
    audio = synthesize_true_peak(vector)
    meter = LoudnessMeter(vector.sample_rate)

    sample_peak = 20.0 * np.log10(np.max(np.abs(audio)))
    measured = meter.true_peak(audio, channels_last=True)

    assert sample_peak == pytest.approx(vector.expected_sample_peak_dbfs, abs=0.1)
    assert measured == pytest.approx(vector.expected_dbtp, abs=vector.tolerance_db)
    assert measured >= sample_peak - 1e-6


def test_a_true_peak_meter_reads_above_the_sample_peak_where_it_should() -> None:
    """The half-Nyquist vectors exist to catch a meter that just reports samples."""
    quarter = [v for v in TECH_3341_TRUE_PEAK_VECTORS if "quarter" in v.case_id]
    assert quarter, "the inter-sample vectors went missing"

    for vector in quarter:
        audio = synthesize_true_peak(vector)
        measured = LoudnessMeter(vector.sample_rate).true_peak(audio, channels_last=True)
        sample_peak = 20.0 * np.log10(np.max(np.abs(audio)))
        assert measured - sample_peak == pytest.approx(3.01, abs=0.4)
