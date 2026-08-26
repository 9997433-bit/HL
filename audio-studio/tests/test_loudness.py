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
    DELIVERY_TARGETS,
    DeliveryTarget,
    LoudnessMeter,
    LoudnessReport,
    StreamingLoudnessMeter,
    channel_weights,
    delivery_target,
    format_lufs,
    integrated_loudness,
    k_weighting_sos,
    true_peak_oversample,
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
    def test_momentary_and_short_term_refresh_ten_times_a_second(self) -> None:
        """EBU Tech 3341 asks a compliant meter for a 10 Hz M and S display."""
        audio = stereo_tone(-23.0, duration_s=10.0)
        meter = LoudnessMeter(SR)
        momentary_times, momentary = meter.momentary(audio)
        short_times, short = meter.short_term(audio)

        assert np.allclose(np.diff(momentary_times), 0.1, atol=1e-6)  # 400 ms @ 75%
        assert np.allclose(np.diff(short_times), 0.1, atol=1e-6)  # 3 s, 10 Hz
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


class TestTruePeak:
    """BS.1770-4 Annex 2: the peak of the waveform, not of the samples."""

    @pytest.mark.parametrize(
        ("rate", "expected"),
        [(44_100, 4), (48_000, 4), (88_200, 2), (96_000, 2), (192_000, 1)],
    )
    def test_oversampling_reaches_the_rate_the_annex_asks_for(
        self, rate: int, expected: int
    ) -> None:
        assert true_peak_oversample(rate) == expected
        assert rate * true_peak_oversample(rate) >= 176_400 or rate >= 176_400

    @pytest.mark.parametrize("rate", [44_100, 48_000, 96_000])
    def test_a_tone_sampled_between_its_peaks_still_reads_its_amplitude(
        self, rate: int
    ) -> None:
        """Four samples per cycle at 45 degrees: every sample is 3 dB low."""
        n = np.arange(int(0.2 * rate))
        tone = 0.5 * np.sin(2.0 * np.pi * (rate / 4.0) * n / rate + np.pi / 4.0)
        meter = LoudnessMeter(rate)

        assert 20.0 * np.log10(np.max(np.abs(tone))) == pytest.approx(-9.03, abs=0.01)
        # EBU Tech 3341 allows +0.2 / -0.4 dB on a true-peak reading.
        assert meter.true_peak(tone) == pytest.approx(-6.02, abs=0.2)

    def test_a_full_scale_sine_reads_zero_dbtp(self) -> None:
        tone = sine(997.0, 1.0, 1.0)
        assert LoudnessMeter(SR).true_peak(tone) == pytest.approx(0.0, abs=0.2)

    def test_per_channel_peaks_are_reported_in_channel_order(self) -> None:
        audio = np.stack([sine(1000.0, 1.0, 0.5), sine(1000.0, 1.0, 0.25)])
        peaks = LoudnessMeter(SR).true_peak_per_channel(audio)
        assert peaks[0] == pytest.approx(-6.02, abs=0.1)
        assert peaks[1] == pytest.approx(-12.04, abs=0.1)

    def test_silence_has_no_peak_rather_than_a_small_one(self) -> None:
        assert LoudnessMeter(SR).true_peak(np.zeros((2, 4800))) == -math.inf

    def test_the_report_agrees_with_the_direct_measurement(self) -> None:
        audio = stereo_tone(-3.0, duration_s=4.0)
        meter = LoudnessMeter(SR)
        report = meter.analyze(audio)
        assert report.true_peak_dbtp == pytest.approx(meter.true_peak(audio), abs=1e-9)
        assert report.true_peak_dbtp == max(report.true_peak_per_channel_dbtp)


class TestLoudnessRangeCadence:
    def test_the_range_uses_the_tech_3342_one_second_grid(self) -> None:
        """3342 builds LRA from short-term readings once a second, not at 10 Hz."""
        audio = np.concatenate(
            [stereo_tone(-30.0, duration_s=20.0), stereo_tone(-20.0, duration_s=20.0)],
            axis=1,
        )
        meter = LoudnessMeter(SR)
        times, _ = meter.block_loudness(audio, window_s=3.0, step_s=1.0)
        assert np.allclose(np.diff(times), 1.0, atol=1e-6)
        assert meter.loudness_range(audio) == pytest.approx(10.0, abs=1.0)


class TestStreamingMeter:
    """The live meter has to agree with the file meter, or it is decoration."""

    @pytest.mark.parametrize("block_size", [128, 1024, 4801])
    def test_pushing_blocks_matches_measuring_the_whole_buffer(
        self, block_size: int
    ) -> None:
        audio = np.concatenate(
            [stereo_tone(-30.0, duration_s=6.0), stereo_tone(-18.0, duration_s=6.0)],
            axis=1,
        )
        offline = LoudnessMeter(SR).analyze(audio)

        live = StreamingLoudnessMeter(SR, n_channels=2)
        for start in range(0, audio.shape[1], block_size):
            live.push(audio[:, start : start + block_size])

        assert live.integrated_lufs == pytest.approx(offline.integrated_lufs, abs=0.01)
        assert live.loudness_range_lu == pytest.approx(offline.loudness_range_lu, abs=0.1)
        assert live.true_peak_dbtp == pytest.approx(offline.true_peak_dbtp, abs=0.01)
        assert live.duration_s == pytest.approx(offline.duration_s, abs=1e-9)

    def test_the_momentary_reading_follows_the_last_400_ms(self) -> None:
        live = StreamingLoudnessMeter(SR, n_channels=2)
        live.push(stereo_tone(-30.0, duration_s=5.0))
        quiet = live.momentary_lufs
        live.push(stereo_tone(-20.0, duration_s=5.0))

        assert quiet == pytest.approx(-30.0, abs=0.1)
        assert live.momentary_lufs == pytest.approx(-20.0, abs=0.1)
        assert live.short_term_lufs == pytest.approx(-20.0, abs=0.1)

    def test_readings_are_minus_infinity_until_a_window_has_arrived(self) -> None:
        live = StreamingLoudnessMeter(SR, n_channels=2)
        live.push(stereo_tone(-23.0, duration_s=0.2))
        assert live.momentary_lufs == -math.inf
        assert live.integrated_lufs == -math.inf
        assert live.loudness_range_lu == 0.0

    def test_reset_forgets_the_stream_but_not_the_configuration(self) -> None:
        live = StreamingLoudnessMeter(SR, n_channels=2)
        live.push(stereo_tone(-23.0, duration_s=4.0))
        live.reset()

        assert live.duration_s == 0.0
        assert live.integrated_lufs == -math.inf
        assert live.true_peak_dbtp == -math.inf

        live.push(stereo_tone(-33.0, duration_s=4.0))
        assert live.integrated_lufs == pytest.approx(-33.0, abs=0.1)

    def test_a_block_with_the_wrong_channel_count_is_refused(self) -> None:
        live = StreamingLoudnessMeter(SR, n_channels=2)
        with pytest.raises(ValueError, match="channels"):
            live.push(np.zeros((3, 1024)))

    def test_the_snapshot_report_matches_the_live_properties(self) -> None:
        live = StreamingLoudnessMeter(SR, n_channels=2)
        live.push(stereo_tone(-23.0, duration_s=5.0))
        report = live.report()

        assert report.integrated_lufs == pytest.approx(live.integrated_lufs, abs=1e-9)
        assert report.short_term_max_lufs == pytest.approx(-23.0, abs=0.1)
        assert report.sample_rate == SR


class TestDeliveryCompliance:
    def test_a_broadcast_master_on_target_passes_r128(self) -> None:
        report = LoudnessMeter(SR).analyze(stereo_tone(-23.0, duration_s=8.0))
        result = report.check("EBU R128")

        assert result.passed and bool(result)
        assert result.target.integrated_lufs == -23.0
        assert "pass" in str(result)

    def test_being_too_loud_fails_with_the_reason(self) -> None:
        report = LoudnessMeter(SR).analyze(stereo_tone(-14.0, duration_s=8.0))
        result = report.check("ebu_r128")

        assert not result.passed
        assert any("integrated" in failure for failure in result.failures)
        assert result.gain_to_target_db == pytest.approx(-9.0, abs=0.1)

    def test_an_inter_sample_overshoot_fails_on_the_ceiling_alone(self) -> None:
        """-23 LUFS is not compliant if the peaks are over the ceiling."""
        loud_peaks = stereo_tone(-23.0, duration_s=8.0)
        loud_peaks[:, ::97] = 0.99  # spikes that do not move the loudness much
        result = LoudnessMeter(SR).analyze(loud_peaks).check("ebu_r128")

        assert not result.passed
        assert any("true peak" in failure for failure in result.failures)

    def test_normalisation_gain_is_held_back_by_the_ceiling(self) -> None:
        report = LoudnessMeter(SR).analyze(stereo_tone(-6.0, duration_s=6.0))

        unconstrained = report.normalization_gain_db(-14.0)
        constrained = report.normalization_gain_db("spotify")

        assert unconstrained == pytest.approx(-8.0, abs=0.1)
        assert constrained == pytest.approx(-8.0, abs=0.1)
        assert report.normalization_gain_db("apple_podcasts") < 0.0

    def test_a_quiet_master_is_lifted_only_as_far_as_the_ceiling_allows(self) -> None:
        """Peaky, quiet material cannot reach -23 LUFS without a limiter."""
        spiky = stereo_tone(-40.0, duration_s=6.0)
        spiky[:, ::24_001] = 0.9
        report = LoudnessMeter(SR).analyze(spiky)

        assert report.integrated_lufs < -30.0
        assert report.normalization_gain_db(-23.0) > 5.0  # what the target asks for
        assert report.normalization_gain_db("ebu_r128") == pytest.approx(
            -1.0 - report.true_peak_dbtp, abs=0.01
        )

    def test_silence_asks_for_no_gain_rather_than_infinite_gain(self) -> None:
        report = LoudnessMeter(SR).analyze(np.zeros((2, SR)))
        assert report.normalization_gain_db("ebu_r128") == 0.0
        assert not report.check("ebu_r128").passed

    def test_targets_resolve_by_name_and_by_object(self) -> None:
        assert delivery_target("EBU R128") is DELIVERY_TARGETS["ebu_r128"]
        custom = DeliveryTarget("House", -18.0, 1.0, -1.5)
        assert delivery_target(custom) is custom
        with pytest.raises(KeyError):
            delivery_target("not-a-platform")

    def test_the_report_serialises_for_a_session_file(self) -> None:
        data = LoudnessMeter(SR).analyze(stereo_tone(-23.0, duration_s=5.0)).as_dict()
        assert data["integrated_lufs"] == pytest.approx(-23.0, abs=0.1)
        assert data["sample_rate"] == SR
        assert len(data["true_peak_per_channel_dbtp"]) == 2


class TestFormatting:
    def test_finite_values_get_one_decimal(self) -> None:
        assert format_lufs(-23.04) == "-23.0 LUFS"

    def test_silence_is_rendered_as_minus_infinity(self) -> None:
        assert format_lufs(-math.inf) == "-\u221e LUFS"

    def test_the_unit_can_be_changed(self) -> None:
        assert format_lufs(-9.0, "LU") == "-9.0 LU"


def test_the_absolute_gate_is_the_value_the_standard_names() -> None:
    assert ABSOLUTE_GATE_LUFS == -70.0
