"""Restoration: de-click and de-hum.

Repair is judged against the damage, not against the implementation. Every
assertion here is either "the fault is gone" or "the audio that was not faulty
came through untouched", because a restoration tool that fails the second is
worse than no restoration tool at all.
"""

from __future__ import annotations

import numpy as np
import pytest

from audio_studio.dsp.effects import EffectChain, ThreeBandEQ
from audio_studio.dsp.repair import (
    ClickEvent,
    DeClickEffect,
    DeHumEffect,
    detect_clicks,
    detect_hum,
    repair_clicks,
    threshold_sigma_for,
)
from tests.signals import SR, sine, stereo, tone_burst, white_noise


def tone_level(signal: np.ndarray, frequency: float, sample_rate: int = SR) -> float:
    """Amplitude of one frequency component, by projection onto its phasor."""
    n = signal.size
    phasor = np.exp(-2j * np.pi * frequency * np.arange(n) / sample_rate)
    return float(2.0 * abs(np.vdot(phasor, signal)) / n)


def with_clicks(
    signal: np.ndarray, positions: tuple[int, ...], amplitude: float = 0.6
) -> np.ndarray:
    damaged = signal.copy()
    for position in positions:
        damaged[position] += amplitude
    return damaged


class TestClickDetection:
    def test_a_single_tick_is_found_where_it_was_put(self) -> None:
        clean = sine(440.0, 1.0, 0.4)
        report = detect_clicks(with_clicks(clean, (12_345,)), SR)

        assert report.count == 1
        assert report.events[0].start == 12_345
        assert report.events[0].seconds(SR) == pytest.approx(12_345 / SR)

    def test_clean_material_is_left_alone(self) -> None:
        """The false-positive rate is the number that decides if this is usable."""
        music = sine(220.0, 2.0, 0.4) + sine(660.0, 2.0, 0.2) + white_noise(2.0, 0.01)
        assert detect_clicks(music, SR).count == 0

    def test_digital_silence_produces_no_detections(self) -> None:
        assert detect_clicks(np.zeros(SR), SR).count == 0

    def test_a_percussive_onset_is_not_a_click(self) -> None:
        """A drum hit is a discontinuity the predictor cannot follow either."""
        hit = white_noise(0.3, 0.5) * np.exp(-np.arange(int(0.3 * SR)) / (0.05 * SR))
        attack = int(0.001 * SR)
        hit[:attack] *= np.linspace(0.0, 1.0, attack)
        signal = np.zeros(SR)
        signal[10_000 : 10_000 + hit.size] = hit

        assert detect_clicks(signal, SR).count == 0

    def test_a_hard_gate_edge_is_treated_as_damage(self) -> None:
        """An instantaneous cut is a click; that is why fades exist."""
        burst = tone_burst(1000.0, 1.0, 0.5, 0.2, amplitude=0.8)
        report = detect_clicks(burst, SR)
        assert report.count == 2  # the switch on and the switch off
        assert report.repaired_samples < int(0.001 * SR)  # a sample or two, not the note

    def test_higher_sensitivity_finds_at_least_as_much(self) -> None:
        damaged = with_clicks(sine(300.0, 1.0, 0.4) + white_noise(1.0, 0.02), (1_000,), 0.15)
        cautious = detect_clicks(damaged, SR, sensitivity=0.1).count
        keen = detect_clicks(damaged, SR, sensitivity=0.9).count
        assert keen >= cautious

    def test_the_sensitivity_control_spans_the_documented_thresholds(self) -> None:
        assert threshold_sigma_for(0.0) == 20.0
        assert threshold_sigma_for(1.0) == 3.0
        assert threshold_sigma_for(-5.0) == 20.0  # clamped
        assert threshold_sigma_for(5.0) == 3.0

    def test_each_channel_is_scanned_on_its_own(self) -> None:
        left = with_clicks(sine(440.0, 1.0, 0.4), (10_000,))
        right = with_clicks(sine(440.0, 1.0, 0.4), (20_000, 30_000))
        report = detect_clicks(stereo(left, right), SR)

        assert len(report.in_channel(0)) == 1
        assert len(report.in_channel(1)) == 2
        assert report.count == 3

    def test_the_report_describes_the_damage(self) -> None:
        report = detect_clicks(with_clicks(sine(440.0, 2.0, 0.4), (10_000, 60_000)), SR)

        assert report.per_minute == pytest.approx(60.0, abs=1e-6)  # 2 in 2 seconds
        assert report.repaired_samples >= 2
        assert "2 clicks" in str(report)
        assert report.as_dict()["count"] == 2
        assert str(detect_clicks(sine(440.0, 1.0, 0.4), SR)) == "no clicks found"

    def test_a_click_event_knows_its_own_length(self) -> None:
        event = ClickEvent(channel=0, start=100, stop=104, peak_residual=0.5)
        assert event.length == 4


class TestClickRepair:
    def test_the_tick_goes_and_the_music_stays(self) -> None:
        clean = sine(440.0, 1.0, 0.5)
        damaged = with_clicks(clean, (12_345,), 0.8)
        repaired, report = repair_clicks(damaged, SR)

        assert report.count == 1
        assert np.max(np.abs(damaged - clean)) == pytest.approx(0.8, abs=1e-6)
        assert np.max(np.abs(repaired - clean)) < 0.01

    def test_repair_beats_the_damage_on_noisy_material(self) -> None:
        clean = sine(220.0, 1.0, 0.4) + white_noise(1.0, 0.01)
        damaged = with_clicks(clean, (5_000, 12_345, 30_000), 0.6)
        repaired, report = repair_clicks(damaged, SR)

        assert report.count == 3
        error_before = float(np.sqrt(np.mean((damaged - clean) ** 2)))
        error_after = float(np.sqrt(np.mean((repaired - clean) ** 2)))
        assert error_after < error_before / 10.0

    def test_a_burst_of_several_samples_is_interpolated_across(self) -> None:
        clean = sine(500.0, 1.0, 0.5)
        damaged = clean.copy()
        damaged[20_000:20_006] = -0.9
        repaired, report = repair_clicks(damaged, SR)

        assert report.count == 1
        assert report.events[0].length >= 6
        assert np.max(np.abs(repaired[19_900:20_100] - clean[19_900:20_100])) < 0.02

    def test_undamaged_audio_comes_back_sample_for_sample(self) -> None:
        clean = sine(220.0, 1.0, 0.4) + white_noise(1.0, 0.01)
        repaired, report = repair_clicks(clean, SR)

        assert report.count == 0
        assert np.array_equal(repaired, clean)

    def test_the_input_is_never_modified(self) -> None:
        damaged = with_clicks(sine(440.0, 1.0, 0.4), (10_000,))
        original = damaged.copy()
        repair_clicks(damaged, SR)
        assert np.array_equal(damaged, original)

    def test_layout_and_dtype_survive_the_round_trip(self) -> None:
        planar = np.stack(
            [with_clicks(sine(440.0, 0.5, 0.4), (5_000,)) for _ in range(2)]
        ).astype(np.float32)
        repaired, _ = repair_clicks(planar, SR)
        assert repaired.shape == planar.shape and repaired.dtype == np.float32

        interleaved = np.ascontiguousarray(planar.T)
        out, _ = repair_clicks(interleaved, SR, channels_last=True)
        assert out.shape == interleaved.shape

    def test_a_nonsense_sample_rate_is_refused(self) -> None:
        with pytest.raises(ValueError, match="sample_rate"):
            repair_clicks(sine(440.0, 0.1, 0.4), 0)


class TestDeClickEffect:
    def test_the_effect_matches_the_function_it_wraps(self) -> None:
        damaged = with_clicks(sine(440.0, 1.0, 0.5), (12_345,), 0.8)
        effect = DeClickEffect()

        processed = effect.process(damaged, SR)
        expected, _ = repair_clicks(damaged, SR)

        assert np.allclose(processed, expected)
        assert effect.last_report is not None and effect.last_report.count == 1

    def test_it_declares_itself_offline_and_says_why_when_streamed(self) -> None:
        effect = DeClickEffect()
        assert effect.is_offline_only
        with pytest.raises(NotImplementedError, match="whole signal"):
            effect.process_block(sine(440.0, 0.1, 0.4), SR)

    def test_a_live_rack_skips_it_rather_than_failing(self) -> None:
        chain = EffectChain([DeClickEffect(), ThreeBandEQ(mid_gain_db=6.0)])
        block = sine(1000.0, 0.02, 0.3)
        assert chain.process_block(block, SR).shape == block.shape

    def test_disabled_it_is_a_pass_through(self) -> None:
        damaged = with_clicks(sine(440.0, 0.5, 0.5), (5_000,), 0.8)
        assert np.array_equal(DeClickEffect(enabled=False).process(damaged, SR), damaged)

    def test_parameters_round_trip_for_a_preset(self) -> None:
        params = DeClickEffect(sensitivity=0.8, order=48, max_click_ms=3.0).parameters()
        assert params["sensitivity"] == 0.8
        assert params["order"] == 48
        assert params["max_click_ms"] == 3.0


class TestHumDetection:
    @pytest.mark.parametrize("frequency", [50.0, 60.0])
    def test_the_mains_frequency_is_measured_not_assumed(self, frequency: float) -> None:
        t = np.arange(4 * SR) / SR
        music = 0.2 * np.sin(2 * np.pi * 440.0 * t) + white_noise(4.0, 0.005)
        hum = 0.02 * np.sin(2 * np.pi * frequency * t)
        hum += 0.01 * np.sin(2 * np.pi * 3 * frequency * t)

        estimate = detect_hum(music + hum, SR)

        assert estimate.frequency == frequency
        assert estimate.present
        assert f"{frequency:.0f} Hz hum" in str(estimate)

    def test_clean_material_is_reported_as_clean(self) -> None:
        music = sine(440.0, 4.0, 0.3) + white_noise(4.0, 0.02)
        estimate = detect_hum(music, SR)
        assert not estimate.present
        assert str(estimate) == "no mains hum detected"

    def test_a_fragment_too_short_to_analyse_is_not_a_crash(self) -> None:
        assert not detect_hum(np.zeros(2), SR).present


class TestDeHumEffect:
    @staticmethod
    def hummed(frequency: float = 50.0, duration: float = 2.0) -> tuple[np.ndarray, ...]:
        t = np.arange(int(duration * SR)) / SR
        music = 0.3 * np.sin(2 * np.pi * 440.0 * t)
        hum = 0.05 * np.sin(2 * np.pi * frequency * t)
        hum += 0.02 * np.sin(2 * np.pi * 2 * frequency * t)
        hum += 0.02 * np.sin(2 * np.pi * 3 * frequency * t)
        return music, hum

    def test_the_fundamental_and_its_harmonics_all_go(self) -> None:
        music, hum = self.hummed(50.0)
        cleaned = DeHumEffect(frequency=50.0).process(music + hum, SR)
        settled = cleaned[SR:]

        for harmonic in (1, 2, 3):
            before = tone_level((music + hum)[SR:], 50.0 * harmonic)
            after = tone_level(settled, 50.0 * harmonic)
            assert after < before / 30.0

    def test_the_music_is_left_where_it_was(self) -> None:
        music, hum = self.hummed(50.0)
        cleaned = DeHumEffect(frequency=50.0).process(music + hum, SR)
        assert tone_level(cleaned[SR:], 440.0) == pytest.approx(0.3, abs=0.01)

    def test_the_response_is_flat_away_from_the_teeth(self) -> None:
        dehum = DeHumEffect(frequency=50.0, harmonics=8)
        assert dehum.magnitude_response_db(np.array([1000.0]), SR)[0] == pytest.approx(
            0.0, abs=0.05
        )
        assert dehum.magnitude_response_db(np.array([150.0]), SR)[0] < -40.0

    def test_teeth_stop_below_nyquist_rather_than_folding_back(self) -> None:
        dehum = DeHumEffect(frequency=1000.0, harmonics=8)
        centres = [band.frequency for band in dehum.teeth(8_000)]
        assert centres == [1000.0, 2000.0, 3000.0]
        assert all(centre < 4_000 for centre in centres)

    def test_a_finite_depth_cuts_instead_of_nulling(self) -> None:
        dehum = DeHumEffect(frequency=50.0, harmonics=2, depth_db=12.0)
        assert dehum.magnitude_response_db(np.array([50.0]), SR)[0] == pytest.approx(
            -12.0, abs=0.1
        )

    def test_streaming_output_equals_the_offline_result(self) -> None:
        music, hum = self.hummed(60.0)
        audio = np.stack([music + hum, music + hum])
        effect = DeHumEffect(frequency=60.0)

        offline = effect.process(audio, SR)
        effect.reset()
        effect.prepare(SR, 2)
        blocks = [
            effect.process_block(audio[:, start : start + 512], SR)
            for start in range(0, audio.shape[1], 512)
        ]

        assert np.allclose(np.concatenate(blocks, axis=1), offline, atol=1e-12)

    def test_auto_mode_measures_the_first_buffer_it_sees(self) -> None:
        music, hum = self.hummed(60.0, duration=4.0)
        effect = DeHumEffect(frequency="auto")

        cleaned = effect.process(music + hum, SR)

        assert effect.frequency == 60.0
        assert effect.detected is not None and effect.detected.present
        assert tone_level(cleaned[SR:], 60.0) < tone_level((music + hum)[SR:], 60.0) / 30.0

    def test_a_frequency_that_is_neither_a_number_nor_auto_is_refused(self) -> None:
        with pytest.raises(ValueError, match="auto"):
            DeHumEffect(frequency="mains")
        with pytest.raises(ValueError, match="auto"):
            DeHumEffect().frequency = "whatever"

    def test_parameters_round_trip_for_a_preset(self) -> None:
        params = DeHumEffect(frequency="auto", harmonics=4, q=20.0, depth_db=9.0).parameters()
        assert params["frequency"] == "auto"
        assert params["harmonics"] == 4
        assert params["q"] == 20.0
        assert params["depth_db"] == 9.0

    def test_disabled_it_is_a_pass_through(self) -> None:
        music, hum = self.hummed(50.0, duration=0.5)
        audio = music + hum
        assert np.array_equal(DeHumEffect(frequency=50.0, enabled=False).process(audio, SR), audio)


def test_the_restoration_pair_combines_into_one_chain() -> None:
    """The order a restoration engineer works in: hum out, then ticks."""
    t = np.arange(2 * SR) / SR
    music = 0.3 * np.sin(2 * np.pi * 440.0 * t)
    damaged = with_clicks(music + 0.05 * np.sin(2 * np.pi * 50.0 * t), (30_000, 60_000), 0.7)

    chain = EffectChain([DeHumEffect(frequency=50.0), DeClickEffect()])
    cleaned = chain.process(damaged, SR)

    # Notches are minimum-phase, so the music is compared by spectrum rather
    # than sample for sample: the 440 Hz tone survives with its phase rotated.
    assert tone_level(cleaned[SR:], 50.0) < 0.005
    assert tone_level(cleaned[SR:], 440.0) == pytest.approx(0.3, abs=0.01)

    # A synthetic tone has no noise floor for what is left of a repaired tick to
    # hide under, so the ticks are still findable — three orders of magnitude
    # weaker, which is the number that matters.
    before = max(event.peak_residual for event in detect_clicks(damaged, SR).events)
    after = max(event.peak_residual for event in detect_clicks(cleaned, SR).events)
    assert after < before / 1000.0
