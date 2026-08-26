"""Effects: EQ response accuracy, level control, fades and the streaming contract."""

from __future__ import annotations

import numpy as np
import pytest
from signals import SR, bin_centered_frequency, impulse, sine, stereo, white_noise

from audio_studio.dsp import SpectralAnalyzer
from audio_studio.dsp.effects import (
    Effect,
    EffectChain,
    EQBand,
    FadeEffect,
    FadeShape,
    FilterType,
    GainEffect,
    NormalizeEffect,
    NormalizeMode,
    ParametricEQ,
    ThreeBandEQ,
    apply_fade,
    fade_envelope,
    measure_levels,
)
from audio_studio.dsp.util import linear_to_db, peak_level, rms_level


def measured_gain_db(effect: Effect, frequency: float, sample_rate: int = SR) -> float:
    """Actual gain the effect applies to a steady tone, in dB.

    Measured on the second half of a long tone so the filter's transient has
    decayed — this is what the EQ really does, independent of its own maths.
    """
    audio = sine(frequency, duration_s=1.0, amplitude=0.5, sample_rate=sample_rate)
    processed = effect.process(audio, sample_rate)
    half = audio.size // 2
    return float(linear_to_db(rms_level(processed[half:])) - linear_to_db(rms_level(audio[half:])))


# ---------------------------------------------------------------------------
# EQ
# ---------------------------------------------------------------------------


class TestEQBand:
    def test_biquad_is_normalised(self) -> None:
        coefficients = EQBand(1000.0, 6.0, 1.0, FilterType.PEAKING).biquad(SR)
        assert coefficients.shape == (6,)
        assert coefficients[3] == pytest.approx(1.0)

    def test_flat_band_is_an_identity(self) -> None:
        coefficients = EQBand(1000.0, 0.0, 1.0, FilterType.PEAKING).biquad(SR)
        assert np.allclose(coefficients, [1, 0, 0, 1, 0, 0], atol=1e-12) or np.allclose(
            coefficients[:3], coefficients[3:], atol=1e-12
        )

    def test_zero_gain_band_is_reported_as_bypassed(self) -> None:
        assert EQBand(1000.0, 0.0, type=FilterType.PEAKING).is_bypassed
        assert not EQBand(1000.0, 0.0, type=FilterType.HIGH_PASS).is_bypassed

    def test_bandwidth_and_q_are_inverses(self) -> None:
        band = EQBand(1000.0, 3.0, q=2.0)
        octaves = band.bandwidth_octaves()
        band.set_bandwidth_octaves(octaves)
        assert band.q == pytest.approx(2.0, rel=1e-9)

    def test_frequency_above_nyquist_stays_finite(self) -> None:
        coefficients = EQBand(30_000.0, 12.0, 1.0, FilterType.PEAKING).biquad(SR)
        assert np.all(np.isfinite(coefficients))

    @pytest.mark.parametrize("bad", [{"frequency": 0.0}, {"q": 0.0}, {"q": -1.0}])
    def test_invalid_parameters_rejected(self, bad: dict) -> None:
        with pytest.raises(ValueError):
            EQBand(**bad)


class TestThreeBandEQ:
    def test_flat_eq_is_transparent(self) -> None:
        audio = white_noise(duration_s=0.2, amplitude=0.3)
        assert np.allclose(ThreeBandEQ().process(audio, SR), audio, atol=1e-12)

    @pytest.mark.parametrize("gain_db", [-12.0, -6.0, 3.0, 9.0])
    def test_mid_band_gain_is_delivered_at_its_centre(self, gain_db: float) -> None:
        eq = ThreeBandEQ(mid_frequency=1000.0, mid_gain_db=gain_db, mid_q=1.0)
        assert measured_gain_db(eq, 1000.0) == pytest.approx(gain_db, abs=0.1)

    @pytest.mark.parametrize("gain_db", [-9.0, 6.0])
    def test_shelves_reach_full_gain_well_inside_the_band(self, gain_db: float) -> None:
        low = ThreeBandEQ(low_frequency=200.0, low_gain_db=gain_db)
        assert measured_gain_db(low, 30.0) == pytest.approx(gain_db, abs=0.5)

        high = ThreeBandEQ(high_frequency=4000.0, high_gain_db=gain_db)
        assert measured_gain_db(high, 16_000.0) == pytest.approx(gain_db, abs=0.5)

    def test_shelf_corner_sits_at_half_the_gain(self) -> None:
        """The RBJ shelf definition puts gain/2 dB at the corner frequency."""
        eq = ThreeBandEQ(low_frequency=200.0, low_gain_db=12.0)
        assert measured_gain_db(eq, 200.0) == pytest.approx(6.0, abs=0.5)

    def test_bands_are_far_enough_apart_not_to_interact(self) -> None:
        eq = ThreeBandEQ(
            low_frequency=80.0, low_gain_db=6.0,
            mid_frequency=1000.0, mid_gain_db=0.0, mid_q=2.0,
            high_frequency=10_000.0, high_gain_db=-6.0,
        )
        assert measured_gain_db(eq, 1000.0) == pytest.approx(0.0, abs=0.6)

    def test_predicted_response_matches_measurement(self) -> None:
        """The curve the UI draws has to be the curve the audio gets."""
        eq = ThreeBandEQ(
            low_frequency=120.0, low_gain_db=5.0,
            mid_frequency=1500.0, mid_gain_db=-7.0, mid_q=1.4,
            high_frequency=6000.0, high_gain_db=4.0,
        )
        for frequency in (60.0, 120.0, 400.0, 1500.0, 3000.0, 6000.0, 12_000.0):
            predicted = float(eq.magnitude_response_db(np.array([frequency]), SR)[0])
            assert measured_gain_db(eq, frequency) == pytest.approx(predicted, abs=0.2)

    def test_response_from_the_impulse_response_matches_too(self) -> None:
        eq = ThreeBandEQ(mid_frequency=2000.0, mid_gain_db=8.0, mid_q=2.0)
        response = eq.process(impulse(8192), SR)
        spectrum = np.abs(np.fft.rfft(response))
        frequencies = np.fft.rfftfreq(8192, 1 / SR)

        index = int(np.argmin(np.abs(frequencies - 2000.0)))
        assert 20 * np.log10(spectrum[index]) == pytest.approx(8.0, abs=0.2)

    def test_output_gain_shifts_the_whole_curve(self) -> None:
        eq = ThreeBandEQ(output_gain_db=-3.0)
        assert measured_gain_db(eq, 1000.0) == pytest.approx(-3.0, abs=0.05)

    def test_response_curve_spans_the_requested_range(self) -> None:
        eq = ThreeBandEQ(mid_gain_db=6.0)
        frequencies, magnitude = eq.response_curve(SR, n_points=256, f_min=20.0)
        assert frequencies.size == magnitude.size == 256
        assert frequencies[0] == pytest.approx(20.0)
        assert frequencies[-1] == pytest.approx(SR / 2)
        assert np.all(np.isfinite(magnitude))

    def test_named_band_accessors(self) -> None:
        eq = ThreeBandEQ()
        eq.set_low(gain_db=4.0).set_mid(frequency=2500.0, q=3.0).set_high(gain_db=-2.0)
        assert (eq.low.gain_db, eq.mid.frequency, eq.mid.q, eq.high.gain_db) == (
            4.0, 2500.0, 3.0, -2.0,
        )

    def test_disabled_band_is_skipped(self) -> None:
        eq = ThreeBandEQ(mid_frequency=1000.0, mid_gain_db=12.0)
        eq.mid.enabled = False
        assert measured_gain_db(eq, 1000.0) == pytest.approx(0.0, abs=0.05)

    def test_stereo_channels_are_filtered_independently(self) -> None:
        eq = ThreeBandEQ(mid_frequency=1000.0, mid_gain_db=6.0, mid_q=1.0)
        audio = stereo(sine(1000.0, amplitude=0.4), sine(1000.0, amplitude=0.2))
        processed = eq.process(audio, SR)

        half = audio.shape[1] // 2
        ratio = rms_level(processed[0, half:]) / rms_level(processed[1, half:])
        assert ratio == pytest.approx(2.0, rel=0.02)

    def test_parameters_round_trip_through_a_dict(self) -> None:
        eq = ThreeBandEQ(low_gain_db=3.0, mid_frequency=2000.0)
        params = eq.parameters()
        assert len(params["bands"]) == 3
        assert params["bands"][0]["gain_db"] == 3.0
        assert params["bands"][1]["frequency"] == 2000.0

    def test_streaming_matches_offline(self) -> None:
        """Block-by-block filtering must not click at buffer boundaries."""
        eq = ThreeBandEQ(low_gain_db=6.0, mid_gain_db=-4.0, high_gain_db=3.0)
        audio = white_noise(duration_s=0.3, amplitude=0.3)

        offline = eq.process(audio, SR)
        eq.reset()
        eq.prepare(SR, 1)
        blocks = [eq.process_block(audio[i : i + 512], SR) for i in range(0, audio.size, 512)]
        assert np.allclose(np.concatenate(blocks), offline, atol=1e-9)

    def test_disabled_effect_passes_audio_through(self) -> None:
        eq = ThreeBandEQ(mid_gain_db=12.0, enabled=False)
        audio = white_noise(duration_s=0.05)
        assert np.allclose(eq.process(audio, SR), audio)

    def test_empty_input_is_handled(self) -> None:
        assert ThreeBandEQ(mid_gain_db=6.0).process(np.zeros(0), SR).size == 0


class TestParametricEQ:
    @pytest.mark.parametrize(
        "filter_type,probe,expected",
        [
            (FilterType.LOW_PASS, 8000.0, -24.0),
            (FilterType.HIGH_PASS, 125.0, -24.0),
            (FilterType.NOTCH, 1000.0, -40.0),
        ],
    )
    def test_pass_and_notch_shapes_attenuate(self, filter_type, probe, expected) -> None:
        eq = ParametricEQ([EQBand(frequency=1000.0, q=0.707, type=filter_type)])
        assert measured_gain_db(eq, probe) < expected

    def test_all_pass_preserves_magnitude(self) -> None:
        eq = ParametricEQ([EQBand(frequency=1000.0, type=FilterType.ALL_PASS)])
        assert measured_gain_db(eq, 1000.0) == pytest.approx(0.0, abs=0.05)
        assert measured_gain_db(eq, 5000.0) == pytest.approx(0.0, abs=0.05)

    def test_band_pass_peaks_at_its_centre(self) -> None:
        eq = ParametricEQ([EQBand(frequency=1000.0, q=2.0, type=FilterType.BAND_PASS)])
        assert measured_gain_db(eq, 1000.0) == pytest.approx(0.0, abs=0.1)
        assert measured_gain_db(eq, 250.0) < -12.0

    def test_many_bands_cascade(self) -> None:
        eq = ParametricEQ([
            EQBand(f, 3.0, 3.0, FilterType.PEAKING) for f in (500.0, 1000.0, 2000.0, 4000.0)
        ])
        assert measured_gain_db(eq, 1000.0) == pytest.approx(3.0, abs=0.4)

    def test_no_bands_is_an_identity(self) -> None:
        audio = white_noise(duration_s=0.1)
        assert np.allclose(ParametricEQ([]).process(audio, SR), audio, atol=1e-12)

    def test_coefficients_are_cached_until_a_parameter_changes(self) -> None:
        eq = ParametricEQ([EQBand(1000.0, 3.0)])
        first = eq.sos(SR)
        assert eq.sos(SR) is first
        eq.bands[0].gain_db = 6.0
        assert eq.sos(SR) is not first


# ---------------------------------------------------------------------------
# gain and normalisation
# ---------------------------------------------------------------------------


class TestGainEffect:
    @pytest.mark.parametrize("gain_db,factor", [(0.0, 1.0), (6.0206, 2.0), (-6.0206, 0.5)])
    def test_applies_the_requested_gain(self, gain_db: float, factor: float) -> None:
        out = GainEffect(gain_db=gain_db).process(np.ones(64), SR)
        assert np.allclose(out, factor, rtol=1e-4)

    def test_polarity_inversion(self) -> None:
        out = GainEffect(gain_db=0.0, invert_polarity=True).process(np.ones(16), SR)
        assert np.allclose(out, -1.0)

    def test_offline_processing_does_not_ramp(self) -> None:
        out = GainEffect(gain_db=-6.0, ramp_ms=50.0).process(np.ones(4800), SR)
        assert np.allclose(out, out[0])

    def test_streaming_ramps_when_the_gain_changes(self) -> None:
        """A parameter change mid-stream must glide, not step."""
        effect = GainEffect(gain_db=0.0, ramp_ms=10.0)
        effect.prepare(SR, 1)
        effect.process_block(np.ones(480), SR)

        effect.gain_db = -20.0
        second = effect.process_block(np.ones(480), SR)
        assert second[0] == pytest.approx(1.0, abs=0.02)
        assert second[-1] == pytest.approx(0.1, rel=1e-3)
        assert np.all(np.diff(second) <= 1e-12)  # monotonically falling

    def test_stereo_gain_is_applied_to_both_channels(self) -> None:
        out = GainEffect(gain_db=-6.0206).process(np.ones((2, 32)), SR)
        assert np.allclose(out, 0.5, rtol=1e-4)


class TestNormalizeEffect:
    @pytest.mark.parametrize("target_db", [0.0, -1.0, -3.0, -20.0])
    def test_peak_mode_hits_the_target(self, target_db: float) -> None:
        audio = 0.02 * sine(440.0, duration_s=0.2)
        out = NormalizeEffect(target_db=target_db, mode=NormalizeMode.PEAK).process(audio, SR)
        assert float(linear_to_db(peak_level(out))) == pytest.approx(target_db, abs=0.01)

    def test_rms_mode_hits_the_target(self) -> None:
        audio = 0.05 * sine(440.0, duration_s=0.5)
        out = NormalizeEffect(target_db=-20.0, mode="rms").process(audio, SR)
        assert float(linear_to_db(rms_level(out))) == pytest.approx(-20.0, abs=0.01)

    def test_true_peak_mode_leaves_sample_peak_below_target(self) -> None:
        """Inter-sample peaks exceed sample peaks, so the gain must be smaller."""
        audio = sine(bin_centered_frequency(11_000.0, 1024), duration_s=0.2, amplitude=0.5)
        out = NormalizeEffect(target_db=-1.0, mode=NormalizeMode.TRUE_PEAK).process(audio, SR)

        report = measure_levels(out)
        assert report.true_peak_db == pytest.approx(-1.0, abs=0.05)
        assert report.peak_db <= report.true_peak_db + 1e-6

    def test_true_peak_is_more_conservative_than_sample_peak(self) -> None:
        audio = sine(11_037.0, duration_s=0.2, amplitude=0.5)
        sample = NormalizeEffect(target_db=-0.1, mode="peak").process(audio, SR)
        true = NormalizeEffect(target_db=-0.1, mode="true_peak").process(audio, SR)
        assert peak_level(true) < peak_level(sample)

    def test_common_gain_preserves_the_stereo_image(self) -> None:
        audio = stereo(0.4 * sine(440.0, 0.2), 0.1 * sine(440.0, 0.2))
        out = NormalizeEffect(target_db=-1.0).process(audio, SR)
        assert peak_level(out[0]) / peak_level(out[1]) == pytest.approx(4.0, rel=1e-6)

    def test_per_channel_mode_equalises_the_channels(self) -> None:
        audio = stereo(0.4 * sine(440.0, 0.2), 0.1 * sine(440.0, 0.2))
        out = NormalizeEffect(target_db=-1.0, per_channel=True).process(audio, SR)
        assert peak_level(out[0]) == pytest.approx(peak_level(out[1]), rel=1e-6)

    def test_ceiling_caps_the_gain_that_rms_mode_asks_for(self) -> None:
        audio = 0.3 * sine(440.0, duration_s=0.2)
        out = NormalizeEffect(target_db=0.0, mode="rms", ceiling_db=-3.0).process(audio, SR)
        assert float(linear_to_db(peak_level(out))) == pytest.approx(-3.0, abs=0.01)

    def test_max_gain_bounds_the_boost_of_a_very_quiet_signal(self) -> None:
        audio = 1e-9 * sine(440.0, duration_s=0.1)
        out = NormalizeEffect(target_db=0.0, max_gain_db=20.0).process(audio, SR)
        assert peak_level(out) / peak_level(audio) == pytest.approx(10.0, rel=1e-6)

    def test_silence_is_left_alone_rather_than_amplified(self) -> None:
        out = NormalizeEffect(target_db=-1.0).process(np.zeros(1024), SR)
        assert np.all(out == 0.0)

    def test_applied_gain_is_reported(self) -> None:
        effect = NormalizeEffect(target_db=-6.0206)
        effect.process(0.5 * sine(440.0, 0.1), SR)
        assert effect.applied_gain_db[0] == pytest.approx(0.0, abs=0.01)

    def test_streaming_is_refused_with_a_useful_message(self) -> None:
        with pytest.raises(NotImplementedError, match="whole signal"):
            NormalizeEffect().process_block(np.ones(128), SR)


def test_measure_levels_reports_sensible_numbers() -> None:
    report = measure_levels(sine(1000.0, duration_s=0.5, amplitude=1.0))
    assert report.peak_db == pytest.approx(0.0, abs=0.01)
    assert report.rms_db == pytest.approx(-3.01, abs=0.05)  # sine crest factor
    assert report.crest_factor_db == pytest.approx(3.01, abs=0.05)
    assert report.true_peak_db >= report.peak_db - 1e-6
    assert len(report.per_channel_peak_db) == 1
    assert "dBFS" in str(report)


# ---------------------------------------------------------------------------
# fades
# ---------------------------------------------------------------------------


class TestFades:
    @pytest.mark.parametrize("shape", list(FadeShape))
    def test_envelope_spans_zero_to_one(self, shape: FadeShape) -> None:
        envelope = fade_envelope(1000, shape, fade_in=True)
        assert envelope[0] == pytest.approx(0.0, abs=1e-9)
        assert envelope[-1] == pytest.approx(1.0, abs=1e-9)

    @pytest.mark.parametrize("shape", list(FadeShape))
    def test_envelope_is_monotonic(self, shape: FadeShape) -> None:
        assert np.all(np.diff(fade_envelope(1000, shape, fade_in=True)) >= -1e-12)

    @pytest.mark.parametrize("shape", list(FadeShape))
    def test_fade_out_mirrors_fade_in(self, shape: FadeShape) -> None:
        rising = fade_envelope(512, shape, fade_in=True)
        falling = fade_envelope(512, shape, fade_in=False)
        assert np.allclose(falling, rising[::-1])

    def test_shapes_differ_at_the_midpoint(self) -> None:
        midpoints = {
            shape: float(fade_envelope(1001, shape)[500]) for shape in FadeShape
        }
        assert midpoints[FadeShape.LINEAR] == pytest.approx(0.5, abs=1e-3)
        assert midpoints[FadeShape.EXPONENTIAL] < 0.5  # stays quiet longer
        assert midpoints[FadeShape.EQUAL_POWER] > 0.5  # rises early
        assert midpoints[FadeShape.COSINE] == pytest.approx(0.5, abs=1e-3)
        assert len({round(v, 4) for v in midpoints.values()}) >= 4

    def test_equal_power_pair_holds_constant_power(self) -> None:
        """The property that makes this shape the right one for a crossfade."""
        rising = fade_envelope(1024, FadeShape.EQUAL_POWER, fade_in=True)
        falling = fade_envelope(1024, FadeShape.EQUAL_POWER, fade_in=False)
        assert np.allclose(np.square(rising) + np.square(falling), 1.0, atol=1e-9)

    def test_cosine_shape_starts_and_ends_flat(self) -> None:
        envelope = fade_envelope(1000, FadeShape.COSINE)
        slope = np.diff(envelope)
        assert slope[0] < slope[len(slope) // 2] / 10
        assert slope[-1] < slope[len(slope) // 2] / 10

    @pytest.mark.parametrize("curve", [-0.8, -0.4, 0.4, 0.8])
    def test_curve_skews_without_moving_the_endpoints(self, curve: float) -> None:
        envelope = fade_envelope(1000, FadeShape.LINEAR, curve=curve)
        assert envelope[0] == pytest.approx(0.0, abs=1e-9)
        assert envelope[-1] == pytest.approx(1.0, abs=1e-9)
        assert np.all(np.diff(envelope) >= -1e-12)

    def test_positive_curve_starts_slower_than_negative(self) -> None:
        slow = fade_envelope(1000, FadeShape.LINEAR, curve=0.8)
        fast = fade_envelope(1000, FadeShape.LINEAR, curve=-0.8)
        assert slow[250] < fast[250]

    def test_degenerate_lengths(self) -> None:
        assert fade_envelope(0).size == 0
        assert fade_envelope(1).tolist() == [1.0]

    def test_fade_in_only_touches_the_head(self) -> None:
        audio = np.ones(SR)
        out = FadeEffect(fade_in_s=0.25).process(audio, SR)
        assert out[0] == pytest.approx(0.0, abs=1e-9)
        assert out[SR // 8] == pytest.approx(0.5, abs=0.01)
        assert np.allclose(out[SR // 4 :], 1.0)

    def test_fade_out_only_touches_the_tail(self) -> None:
        audio = np.ones(SR)
        out = FadeEffect(fade_out_s=0.25).process(audio, SR)
        assert out[-1] == pytest.approx(0.0, abs=1e-9)
        assert np.allclose(out[: 3 * SR // 4], 1.0)

    def test_both_fades_at_once(self) -> None:
        out = FadeEffect(fade_in_s=0.1, fade_out_s=0.1).process(np.ones(SR), SR)
        assert out[0] == pytest.approx(0.0, abs=1e-9)
        assert out[-1] == pytest.approx(0.0, abs=1e-9)
        assert out[SR // 2] == pytest.approx(1.0)

    def test_overlapping_fades_are_shrunk_to_fit(self) -> None:
        """Asking for more fade than there is audio must not double-attenuate."""
        out = FadeEffect(fade_in_s=1.0, fade_out_s=1.0).process(np.ones(SR // 2), SR)
        assert np.max(out) == pytest.approx(1.0, abs=0.01)
        assert out[0] == pytest.approx(0.0, abs=1e-9)
        assert out[-1] == pytest.approx(0.0, abs=1e-9)

    def test_no_fade_is_a_copy_not_a_reference(self) -> None:
        audio = np.ones(128)
        out = FadeEffect().process(audio, SR)
        out[0] = 99.0
        assert audio[0] == 1.0

    def test_stereo_fade_is_applied_to_every_channel(self) -> None:
        out = FadeEffect(fade_in_s=0.1).process(np.ones((2, SR)), SR)
        assert np.allclose(out[0], out[1])
        assert out[0, 0] == pytest.approx(0.0, abs=1e-9)

    def test_envelope_is_exposed_for_drawing(self) -> None:
        envelope = FadeEffect(fade_in_s=0.1, fade_out_s=0.2).envelope(SR, SR)
        assert envelope.shape == (SR,)
        assert envelope[0] == pytest.approx(0.0, abs=1e-9)
        assert envelope[SR // 2] == pytest.approx(1.0)

    def test_apply_fade_helper(self) -> None:
        out = apply_fade(np.ones(SR), SR, fade_in_s=0.1, shape="cosine")
        assert out[0] == pytest.approx(0.0, abs=1e-9)

    def test_negative_duration_rejected(self) -> None:
        with pytest.raises(ValueError):
            FadeEffect(fade_in_s=-1.0)

    def test_streaming_is_refused(self) -> None:
        with pytest.raises(NotImplementedError):
            FadeEffect(fade_in_s=0.1).process_block(np.ones(128), SR)


# ---------------------------------------------------------------------------
# chaining and layout handling
# ---------------------------------------------------------------------------


class TestEffectChain:
    def test_applies_effects_in_order(self) -> None:
        chain = EffectChain([GainEffect(gain_db=-6.0206), GainEffect(gain_db=-6.0206)])
        assert np.allclose(chain.process(np.ones(16), SR), 0.25, rtol=1e-4)

    def test_disabled_members_are_skipped(self) -> None:
        chain = EffectChain([GainEffect(gain_db=-20.0, enabled=False), GainEffect(gain_db=0.0)])
        assert np.allclose(chain.process(np.ones(16), SR), 1.0)

    def test_a_strict_chain_reports_offline_only_when_a_member_is(self) -> None:
        strict = EffectChain([GainEffect(), NormalizeEffect()], skip_offline_in_stream=False)
        assert strict.is_offline_only
        assert not EffectChain([GainEffect()], skip_offline_in_stream=False).is_offline_only
        with pytest.raises(NotImplementedError):
            strict.process_block(np.ones(128), SR)

    def test_streaming_chain_matches_offline(self) -> None:
        audio = white_noise(duration_s=0.2, amplitude=0.3)
        chain = EffectChain([ThreeBandEQ(mid_gain_db=6.0), GainEffect(gain_db=-3.0)])

        offline = chain.process(audio, SR)
        chain.reset()
        chain.prepare(SR, 1)
        blocks = [chain.process_block(audio[i : i + 256], SR) for i in range(0, audio.size, 256)]
        assert np.allclose(np.concatenate(blocks), offline, atol=1e-9)

    def test_add_and_remove(self) -> None:
        gain = GainEffect(gain_db=-6.0)
        chain = EffectChain()
        chain.add(gain)
        assert len(chain) == 1 and chain[0] is gain
        chain.remove(gain)
        assert len(chain) == 0

    def test_parameters_describe_every_member(self) -> None:
        params = EffectChain([ThreeBandEQ(), GainEffect()]).parameters()
        assert [e["type"] for e in params["effects"]] == ["ThreeBandEQ", "GainEffect"]

    def test_chain_is_iterable(self) -> None:
        chain = EffectChain([GainEffect(), FadeEffect()])
        assert [type(e).__name__ for e in chain] == ["GainEffect", "FadeEffect"]


class TestLayoutHandling:
    def test_mono_in_mono_out(self) -> None:
        assert GainEffect(gain_db=-6.0).process(np.ones(64), SR).ndim == 1

    def test_planar_layout_is_preserved(self) -> None:
        assert GainEffect().process(np.ones((2, 64)), SR).shape == (2, 64)

    def test_interleaved_layout_is_preserved(self) -> None:
        out = GainEffect(gain_db=-6.0).process(np.ones((64, 2)), SR, channels_last=True)
        assert out.shape == (64, 2)

    def test_input_is_never_modified(self) -> None:
        audio = np.ones(64)
        ThreeBandEQ(mid_gain_db=12.0).process(audio, SR)
        assert np.all(audio == 1.0)

    def test_integer_input_is_promoted_to_float(self) -> None:
        out = GainEffect(gain_db=0.0).process(np.ones(16, dtype=np.int16), SR)
        assert out.dtype == np.float32

    def test_repr_shows_parameters(self) -> None:
        assert "gain_db=-6.0" in repr(GainEffect(gain_db=-6.0))


def test_eq_boost_is_visible_in_the_spectrum() -> None:
    """End-to-end sanity: what the EQ does shows up where the analyzer looks."""
    fft_size = 8192
    frequency = bin_centered_frequency(2000.0, fft_size)
    audio = white_noise(duration_s=2.0, amplitude=0.2)

    eq = ThreeBandEQ(mid_frequency=frequency, mid_gain_db=12.0, mid_q=4.0)
    analyzer = SpectralAnalyzer(sample_rate=SR, fft_size=fft_size, dtype=np.float64, center=False)

    before = analyzer.spectrogram(audio).mono().mean(axis=0)
    after = analyzer.spectrogram(eq.process(audio, SR)).mono().mean(axis=0)

    index = int(np.argmin(np.abs(analyzer.frequencies - frequency)))
    boost_db = 20 * np.log10(after[index] / before[index])
    assert boost_db == pytest.approx(12.0, abs=1.0)
