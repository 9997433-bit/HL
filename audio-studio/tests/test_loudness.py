"""ITU-R BS.1770 / EBU R 128 loudness measurement.

The assertions are against the standard rather than against the implementation:
the published 48 kHz coefficient tables, the EBU Tech 3341 test signals, the
+1.5 dB surround weighting, and the behaviour the gate exists to produce.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from scipy.signal import sosfreqz

from audio_studio.dsp.loudness import (
    ABSOLUTE_GATE_LUFS,
    LoudnessMeter,
    LoudnessReport,
    channel_weights,
    format_lufs,
    integrated_loudness,
    k_weighting_sos,
)

SR = 48_000

# ITU-R BS.1770-4, Tables 1 and 2, at 48 kHz.
PUBLISHED_SHELF = ([1.53512485958697, -2.69169618940638, 1.19839281085285],
                   [1.0, -1.69065929318241, 0.73248077421585])
PUBLISHED_HIGHPASS = ([1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621])


def sine(frequency: float, duration_s: float, amplitude: float, sample_rate: int = SR):
    t = np.arange(int(duration_s * sample_rate)) / sample_rate
    return amplitude * np.sin(2.0 * np.pi * frequency * t)


def stereo_tone(dbfs_peak: float, duration_s: float = 10.0, sample_rate: int = SR):
    """The EBU Tech 3341 test signal: 1 kHz in both channels at a stated peak."""
    mono = sine(1000.0, duration_s, 10.0 ** (dbfs_peak / 20.0), sample_rate)
    return np.stack([mono, mono])


class TestKWeighting:
    def test_matches_the_published_48k_coefficients(self) -> None:
        sos = k_weighting_sos(48_000)
        assert sos[0, :3] == pytest.approx(PUBLISHED_SHELF[0], abs=1e-6)
        assert sos[0, 3:] == pytest.approx(PUBLISHED_SHELF[1], abs=1e-6)
        assert sos[1, :3] == pytest.approx(PUBLISHED_HIGHPASS[0], abs=1e-9)
        assert sos[1, 3:] == pytest.approx(PUBLISHED_HIGHPASS[1], abs=1e-6)

    @pytest.mark.parametrize("rate", [44_100, 48_000, 96_000, 192_000])
    def test_shape_is_the_same_at_every_sample_rate(self, rate: int) -> None:
        """Re-deriving from the analog prototype, not resampling a table."""
        _, response = sosfreqz(k_weighting_sos(rate), worN=[38.0, 1000.0, 10_000.0], fs=rate)
        gains = 20.0 * np.log10(np.abs(response))
        # The RLB high-pass is critically damped (Q = 0.5), so its corner sits
        # 6 dB down rather than the 3 dB a Butterworth section would give.
        assert gains[0] == pytest.approx(-6.0, abs=0.6)
        assert gains[1] == pytest.approx(0.7, abs=0.1)  # ~unity at 1 kHz
        assert gains[2] == pytest.approx(4.0, abs=0.3)  # the +4 dB shelf

    def test_coefficients_are_cached(self) -> None:
        assert k_weighting_sos(SR) is k_weighting_sos(SR)

    def test_rejects_a_nonsense_rate(self) -> None:
        with pytest.raises(ValueError):
            k_weighting_sos(0.0)


class TestIntegratedLoudness:
    def test_ebu_3341_case_1_stereo_1khz_at_minus_23(self) -> None:
        """EBU Tech 3341 test 1: -23 dBFS 1 kHz in both channels reads -23 LUFS."""
        assert LoudnessMeter(SR).integrated(stereo_tone(-23.0)) == pytest.approx(-23.0, abs=0.1)

    def test_ebu_3341_case_2_stereo_1khz_at_minus_33(self) -> None:
        assert LoudnessMeter(SR).integrated(stereo_tone(-33.0)) == pytest.approx(-33.0, abs=0.1)

    def test_a_10_db_louder_signal_reads_10_lu_louder(self) -> None:
        meter = LoudnessMeter(SR)
        quiet = meter.integrated(stereo_tone(-33.0))
        loud = meter.integrated(stereo_tone(-23.0))
        assert loud - quiet == pytest.approx(10.0, abs=0.01)

    def test_doubling_the_channels_adds_3_lu(self) -> None:
        """Loudness sums power across channels, so the same signal twice is +3."""
        mono = sine(1000.0, 10.0, 0.1)
        meter = LoudnessMeter(SR)
        assert meter.integrated(np.stack([mono, mono])) - meter.integrated(
            mono
        ) == pytest.approx(3.01, abs=0.02)

    def test_scaling_the_signal_scales_the_reading(self) -> None:
        audio = stereo_tone(-20.0)
        meter = LoudnessMeter(SR)
        assert meter.integrated(audio * 0.5) == pytest.approx(
            meter.integrated(audio) - 6.02, abs=0.02
        )

    def test_layout_matches_the_planar_and_interleaved_forms(self) -> None:
        audio = stereo_tone(-23.0)
        meter = LoudnessMeter(SR)
        assert meter.integrated(
            np.ascontiguousarray(audio.T), channels_last=True
        ) == pytest.approx(meter.integrated(audio), abs=1e-9)

    def test_module_level_helper_agrees_with_the_meter(self) -> None:
        audio = stereo_tone(-23.0)
        assert integrated_loudness(audio, SR) == pytest.approx(
            LoudnessMeter(SR).integrated(audio), abs=1e-9
        )

    @pytest.mark.parametrize("rate", [44_100, 48_000, 96_000])
    def test_reading_is_independent_of_sample_rate(self, rate: int) -> None:
        audio = stereo_tone(-23.0, duration_s=8.0, sample_rate=rate)
        assert LoudnessMeter(rate).integrated(audio) == pytest.approx(-23.0, abs=0.15)


class TestGating:
    def test_silence_between_programme_does_not_drag_the_reading_down(self) -> None:
        """The whole point of the gate: leading silence must not count."""
        meter = LoudnessMeter(SR)
        tone = stereo_tone(-23.0, duration_s=10.0)
        padded = np.concatenate([np.zeros((2, SR * 20)), tone], axis=1)
        assert meter.integrated(padded) == pytest.approx(meter.integrated(tone), abs=0.1)

    def test_quiet_passages_below_the_relative_gate_are_dropped(self) -> None:
        meter = LoudnessMeter(SR)
        loud = stereo_tone(-20.0, duration_s=10.0)
        quiet = stereo_tone(-45.0, duration_s=10.0)
        mixed = np.concatenate([loud, quiet], axis=1)
        assert meter.integrated(mixed) == pytest.approx(meter.integrated(loud), abs=0.2)

    def test_digital_silence_reads_minus_infinity(self) -> None:
        assert LoudnessMeter(SR).integrated(np.zeros((2, SR * 2))) == -math.inf

    def test_everything_below_the_absolute_gate_reads_minus_infinity(self) -> None:
        assert LoudnessMeter(SR).integrated(stereo_tone(-90.0, duration_s=5.0)) == -math.inf

    def test_a_fragment_shorter_than_one_block_has_no_reading(self) -> None:
        assert LoudnessMeter(SR).integrated(np.ones((2, 100)) * 0.1) == -math.inf


class TestChannelWeights:
    def test_surround_channels_count_one_and_a_half_db_louder(self) -> None:
        mono = sine(1000.0, 5.0, 0.3)
        front = np.zeros((5, mono.size))
        front[0] = mono
        surround = np.zeros((5, mono.size))
        surround[3] = mono  # Ls

        meter = LoudnessMeter(SR)
        assert meter.integrated(surround) - meter.integrated(front) == pytest.approx(
            1.5, abs=0.02
        )

    def test_the_lfe_is_ignored(self) -> None:
        mono = sine(60.0, 5.0, 0.5)
        five_one = np.zeros((6, mono.size))
        five_one[3] = mono  # LFE
        assert LoudnessMeter(SR).integrated(five_one) == -math.inf

    def test_layouts_are_listed_in_itu_order(self) -> None:
        assert channel_weights(2) == (1.0, 1.0)
        assert channel_weights(6)[3] == 0.0
        assert channel_weights(9) == (1.0,) * 9  # unknown layout: no weighting

    def test_explicit_weights_override_the_layout(self) -> None:
        mono = sine(1000.0, 5.0, 0.2)
        audio = np.stack([mono, mono])
        boosted = LoudnessMeter(SR, weights=(2.0, 2.0)).integrated(audio)
        assert boosted - LoudnessMeter(SR).integrated(audio) == pytest.approx(3.01, abs=0.01)

    def test_a_short_weight_tuple_is_padded(self) -> None:
        assert LoudnessMeter(SR, weights=(1.0,)).weights_for(3).tolist() == [1.0, 1.0, 1.0]


class TestWindows:
    def test_momentary_and_short_term_have_the_expected_cadence(self) -> None:
        audio = stereo_tone(-23.0, duration_s=10.0)
        meter = LoudnessMeter(SR)
        momentary_times, momentary = meter.momentary(audio)
        short_times, short = meter.short_term(audio)

        assert np.allclose(np.diff(momentary_times), 0.1, atol=1e-6)  # 400 ms @ 75%
        assert np.allclose(np.diff(short_times), 0.75, atol=1e-6)  # 3 s @ 75%
        assert momentary == pytest.approx(-23.0, abs=0.1)
        assert short == pytest.approx(-23.0, abs=0.1)

    def test_short_term_needs_three_seconds_of_audio(self) -> None:
        times, values = LoudnessMeter(SR).short_term(stereo_tone(-23.0, duration_s=1.0))
        assert times.size == 0 and values.size == 0

    def test_momentary_tracks_a_step_within_one_window(self) -> None:
        meter = LoudnessMeter(SR)
        audio = np.concatenate(
            [stereo_tone(-30.0, duration_s=5.0), stereo_tone(-20.0, duration_s=5.0)], axis=1
        )
        times, values = meter.momentary(audio)
        settled = values[times > 5.5]
        assert settled == pytest.approx(-20.0, abs=0.1)


class TestLoudnessRange:
    def test_a_steady_tone_has_no_range(self) -> None:
        assert LoudnessMeter(SR).loudness_range(stereo_tone(-23.0, duration_s=20.0)) < 0.5

    def test_a_programme_that_moves_has_one(self) -> None:
        audio = np.concatenate(
            [
                stereo_tone(-30.0, duration_s=20.0),
                stereo_tone(-20.0, duration_s=20.0),
            ],
            axis=1,
        )
        assert LoudnessMeter(SR).loudness_range(audio) == pytest.approx(10.0, abs=1.5)

    def test_silence_has_no_range(self) -> None:
        assert LoudnessMeter(SR).loudness_range(np.zeros((2, SR * 10))) == 0.0


class TestReport:
    def test_report_covers_every_headline_number(self) -> None:
        audio = stereo_tone(-23.0, duration_s=10.0)
        report = LoudnessMeter(SR).analyze(audio)

        assert isinstance(report, LoudnessReport)
        assert report.integrated_lufs == pytest.approx(-23.0, abs=0.1)
        assert report.momentary_max_lufs == pytest.approx(-23.0, abs=0.1)
        assert report.short_term_max_lufs == pytest.approx(-23.0, abs=0.1)
        assert report.true_peak_dbtp == pytest.approx(-23.0, abs=0.2)
        assert report.sample_peak_dbfs == pytest.approx(-23.0, abs=0.01)
        assert report.duration_s == pytest.approx(10.0, abs=1e-6)
        assert report.gated_blocks > 90
        assert "LUFS" in str(report)

    def test_true_peak_is_at_or_above_the_sample_peak(self) -> None:
        audio = stereo_tone(-1.0, duration_s=4.0)
        report = LoudnessMeter(SR).analyze(audio)
        assert report.true_peak_dbtp >= report.sample_peak_dbfs - 1e-6

    def test_offset_from_a_delivery_target(self) -> None:
        report = LoudnessMeter(SR).analyze(stereo_tone(-23.0, duration_s=8.0))
        assert report.target_offset_lu(-23.0) == pytest.approx(0.0, abs=0.1)
        assert report.target_offset_lu(-14.0) == pytest.approx(-9.0, abs=0.1)

    def test_silence_reports_without_raising(self) -> None:
        report = LoudnessMeter(SR).analyze(np.zeros((2, SR)))
        assert report.integrated_lufs == -math.inf
        assert report.gated_blocks == 0
        assert "\u221e" in str(report)


class TestFormatting:
    def test_finite_values_get_one_decimal(self) -> None:
        assert format_lufs(-23.04) == "-23.0 LUFS"

    def test_silence_is_rendered_as_minus_infinity(self) -> None:
        assert format_lufs(-math.inf) == "-\u221e LUFS"

    def test_the_unit_can_be_changed(self) -> None:
        assert format_lufs(-9.0, "LU") == "-9.0 LU"


def test_the_absolute_gate_is_the_value_the_standard_names() -> None:
    assert ABSOLUTE_GATE_LUFS == -70.0
