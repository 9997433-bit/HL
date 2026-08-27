"""Noise reduction: what comes off, and what has to survive it.

A denoiser is easy to write and hard to trust. Anything that attenuates enough
bins will lower the noise floor, so measuring the hiss on its own proves very
little; what decides whether the tool is usable is the *other* number, the
error against the signal that was supposed to come through untouched. Every
assertion here is therefore one of three kinds: the hiss went down by the
amount asked for, the programme came back at its own level, or the output is
the input when the effect is told to do nothing.

The headline is :meth:`TestNoiseReduction.test_the_signal_to_noise_ratio_improves`,
which measures the full-band SNR against the clean fixture before and after.
"""

from __future__ import annotations

import numpy as np
import pytest

from audio_studio.dsp.effects import EffectChain, ThreeBandEQ
from audio_studio.dsp.repair import (
    DeClickEffect,
    DeHumEffect,
    NoiseProfile,
    NoiseReduceEffect,
    learn_noise_profile,
    reduce_noise,
)
from tests.signals import SR, sine, stereo, white_noise

#: Length of the noise-only pause every fixture opens with. Long enough for the
#: default 300 ms learning span to finish inside it.
LEAD_S = 0.4

#: Hiss amplitude used throughout: -26 dBFS, a plausibly bad analogue transfer.
HISS = 0.05


def noisy_tone(
    lead_s: float = LEAD_S,
    body_s: float = 1.0,
    hiss: float = HISS,
    seed: int = 4_242,
) -> tuple[np.ndarray, np.ndarray]:
    """A pause, then two tones, all of it under steady hiss.

    Returns ``(noisy, clean)``. Two tones rather than one so that a gain which
    only happens to be right at 440 Hz cannot pass, and a pause at the front
    because that is what the effect learns from — the fixture is the situation
    the tool is actually used in, not a convenient one.
    """
    total = lead_s + body_s
    noise = white_noise(total, hiss, seed=seed)
    clean = np.zeros(noise.size, dtype=np.float64)
    body = sine(440.0, body_s, 0.3) + sine(1330.0, body_s, 0.15)
    start = int(round(lead_s * SR))
    clean[start : start + body.size] = body[: clean.size - start]
    return clean + noise, clean


def snr_db(estimate: np.ndarray, reference: np.ndarray, region: slice) -> float:
    """Signal-to-noise ratio of ``estimate`` against the clean ``reference``."""
    error = estimate[region] - reference[region]
    return float(
        10.0 * np.log10(np.sum(np.square(reference[region])) / np.sum(np.square(error)))
    )


def rms(signal: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(signal))))


def tone_level(signal: np.ndarray, frequency: float) -> float:
    """Amplitude of one frequency component, by projection onto its phasor."""
    n = signal.size
    phasor = np.exp(-2j * np.pi * frequency * np.arange(n) / SR)
    return float(2.0 * abs(np.vdot(phasor, signal)) / n)


#: The pause, minus a window at each end so the measurement is not looking at
#: the effect warming up or at the tone leaking backwards through the STFT.
PAUSE = slice(2048, int(round(LEAD_S * SR)) - 2048)

#: The tone, a window in from its start for the same reason.
BODY = slice(int(round(LEAD_S * SR)) + 2048, None)


class TestNoiseProfile:
    def test_the_profile_reads_back_the_floor_it_was_shown(self) -> None:
        """0.02 RMS of hiss is -34 dBFS, and the profile should say so."""
        profile = learn_noise_profile(white_noise(1.0, 0.02), SR)

        assert isinstance(profile, NoiseProfile)
        assert profile.level_db == pytest.approx(-33.98, abs=0.5)
        assert profile.n_channels == 1 and profile.n_bins == 1025

    def test_the_level_is_independent_of_the_transform_that_measured_it(self) -> None:
        """A profile is a property of the noise, not of the analysis."""
        hiss = white_noise(1.0, 0.02)
        short = learn_noise_profile(hiss, SR, fft_size=512)
        long = learn_noise_profile(hiss, SR, fft_size=4096)

        assert short.level_db == pytest.approx(long.level_db, abs=0.3)
        assert short.n_bins != long.n_bins

    def test_a_selection_measures_the_pause_and_not_the_take(self) -> None:
        noisy, _ = noisy_tone()

        pause = learn_noise_profile(noisy, SR, start_s=0.02, duration_s=0.35)
        everything = learn_noise_profile(noisy, SR)

        assert pause.level_db == pytest.approx(-26.02, abs=0.5)  # the hiss alone
        assert everything.level_db > pause.level_db + 10.0  # the tones dragged it up

    def test_the_profile_says_where_the_noise_lives(self) -> None:
        """Per-bin, not broadband: a 1 kHz whine reads as a peak at 1 kHz."""
        profile = learn_noise_profile(sine(1000.0, 1.0, 0.1), SR)
        peak = profile.frequencies()[int(np.argmax(profile.to_db()))]

        assert peak == pytest.approx(1000.0, abs=SR / 2048)

    def test_a_profile_knows_how_much_it_was_shown(self) -> None:
        profile = learn_noise_profile(white_noise(0.5, 0.01), SR)

        assert profile.duration_s == pytest.approx(0.5, abs=0.02)
        assert profile.frames > 40
        assert "dBFS noise floor" in str(profile)

    def test_one_channels_hiss_stands_in_for_anothers(self) -> None:
        profile = learn_noise_profile(white_noise(0.5, 0.02), SR)
        power = profile.power_for(2, profile.n_bins, SR)

        assert power.shape == (2, profile.n_bins)
        assert np.array_equal(power[0], power[1])

    def test_a_profile_carries_over_to_a_finer_bin_grid(self) -> None:
        profile = learn_noise_profile(white_noise(0.5, 0.02), SR, fft_size=512)
        power = profile.power_for(1, 2049, SR)

        assert power.shape == (1, 2049)
        assert float(np.mean(power)) == pytest.approx(0.02**2, rel=0.2)

    def test_a_span_too_short_to_be_a_spectrum_is_refused(self) -> None:
        with pytest.raises(ValueError, match="at least 2048 samples"):
            learn_noise_profile(white_noise(0.01, 0.02), SR)

    def test_a_nonsense_sample_rate_is_refused(self) -> None:
        with pytest.raises(ValueError, match="sample_rate"):
            learn_noise_profile(white_noise(1.0, 0.02), 0)


class TestNoiseReduction:
    def test_the_signal_to_noise_ratio_improves(self) -> None:
        """The headline number: at least 12 dB better against the clean take."""
        noisy, clean = noisy_tone()

        cleaned, profile = reduce_noise(noisy, SR)

        before = snr_db(noisy, clean, BODY)
        after = snr_db(cleaned, clean, BODY)
        assert after - before >= 12.0
        assert profile is not None and profile.level_db == pytest.approx(-26.0, abs=1.0)

    def test_the_hiss_drops_by_the_amount_asked_for(self) -> None:
        noisy, _ = noisy_tone()

        for reduction_db in (12.0, 24.0):
            cleaned, _ = reduce_noise(noisy, SR, reduction_db=reduction_db)
            measured = 20.0 * np.log10(rms(cleaned[PAUSE]) / rms(noisy[PAUSE]))
            assert measured == pytest.approx(-reduction_db, abs=2.0)

    def test_the_tones_come_back_at_their_own_level(self) -> None:
        """The reason the SNR improves has to be the noise, not a duck."""
        noisy, _ = noisy_tone()

        cleaned, _ = reduce_noise(noisy, SR)

        assert tone_level(cleaned[BODY], 440.0) == pytest.approx(0.3, rel=0.02)
        assert tone_level(cleaned[BODY], 1330.0) == pytest.approx(0.15, rel=0.02)

    def test_a_profile_from_a_selection_works_as_well_as_the_head(self) -> None:
        """The operator drags over a pause instead of trusting the first 300 ms."""
        noisy, clean = noisy_tone()
        profile = learn_noise_profile(noisy, SR, start_s=0.05, duration_s=0.3)

        cleaned, used = reduce_noise(noisy, SR, profile=profile)

        assert used is profile
        assert snr_db(cleaned, clean, BODY) - snr_db(noisy, clean, BODY) >= 12.0

    def test_asking_for_no_reduction_returns_the_input(self) -> None:
        """Which also shows the analysis/resynthesis round trip is exact."""
        noisy, _ = noisy_tone()

        cleaned, _ = reduce_noise(noisy, SR, reduction_db=0.0)

        assert np.allclose(cleaned, noisy, atol=1e-12)

    def test_silence_comes_back_silent(self) -> None:
        cleaned, profile = reduce_noise(np.zeros(SR), SR)

        assert np.all(np.isfinite(cleaned))
        assert not np.any(cleaned)
        assert profile is not None and profile.level_db < -200.0

    def test_the_input_is_never_modified(self) -> None:
        noisy, _ = noisy_tone(body_s=0.3)
        original = noisy.copy()

        reduce_noise(noisy, SR)

        assert np.array_equal(noisy, original)

    def test_each_channel_is_reduced_on_its_own(self) -> None:
        """One channel carries the take, the other only ever carried hiss."""
        left, _ = noisy_tone(body_s=0.4)
        right = white_noise(left.size / SR, HISS, seed=99)
        settled = slice(4096, None)  # past the first window, which warms up

        cleaned, _ = reduce_noise(stereo(left, right), SR)

        assert cleaned.shape == (2, left.size)
        assert tone_level(cleaned[0][BODY], 440.0) == pytest.approx(0.3, rel=0.03)
        assert rms(cleaned[1][settled]) < rms(right[settled]) / 8.0

    def test_layout_and_dtype_survive_the_round_trip(self) -> None:
        noisy, _ = noisy_tone(body_s=0.3)
        planar = np.stack([noisy, noisy]).astype(np.float32)

        cleaned, _ = reduce_noise(planar, SR)
        assert cleaned.shape == planar.shape and cleaned.dtype == np.float32

        interleaved = np.ascontiguousarray(planar.T)
        out, _ = reduce_noise(interleaved, SR, channels_last=True)
        assert out.shape == interleaved.shape


class TestNoiseReduceEffect:
    def test_streaming_output_equals_the_offline_result(self) -> None:
        """The contract every rack member owes a live preview."""
        noisy, _ = noisy_tone(body_s=0.3)
        audio = np.stack([noisy, noisy * 0.7])
        effect = NoiseReduceEffect()

        offline = effect.process(audio, SR)
        effect.reset()
        effect.prepare(SR, 2)
        blocks = [
            effect.process_block(audio[:, start : start + 512], SR, channels_last=False)
            for start in range(0, audio.shape[1], 512)
        ]

        assert np.allclose(np.concatenate(blocks, axis=1), offline, atol=1e-12)

    def test_a_block_size_that_does_not_divide_the_hop_still_lines_up(self) -> None:
        """Device buffers are not obliged to be a multiple of anything."""
        noisy, _ = noisy_tone(body_s=0.2)
        effect = NoiseReduceEffect()
        offline = effect.process(noisy, SR)

        effect.reset()
        effect.prepare(SR, 1)
        blocks, start = [], 0
        for size in [1, 7, 3_000, 129, 511] * 20:
            if start >= noisy.size:
                break
            blocks.append(effect.process_block(noisy[start : start + size], SR))
            start += size
        streamed = np.concatenate(blocks)

        assert np.allclose(streamed, offline[: streamed.size], atol=1e-12)

    def test_it_delays_the_signal_by_one_analysis_window(self) -> None:
        noisy, _ = noisy_tone(body_s=0.3)
        effect = NoiseReduceEffect()
        latency = effect.latency_samples()

        delayed = effect.process(noisy, SR)
        aligned, _ = reduce_noise(noisy, SR)

        assert latency == effect.fft_size == 2048
        assert delayed.size == noisy.size
        assert not np.any(delayed[:latency])  # the delay, declared and real
        assert np.allclose(delayed[latency:], aligned[:-latency], atol=1e-12)

    def test_a_live_rack_streams_it_rather_than_skipping_it(self) -> None:
        """Unlike the de-clicker, this one can be auditioned."""
        chain = EffectChain([NoiseReduceEffect(), ThreeBandEQ(mid_gain_db=6.0)])
        block = sine(1000.0, 0.02, 0.3)

        assert not NoiseReduceEffect().is_offline_only
        assert chain.process_block(block, SR).shape == block.shape

    def test_disabled_it_is_a_pass_through(self) -> None:
        noisy, _ = noisy_tone(body_s=0.2)
        assert np.array_equal(NoiseReduceEffect(enabled=False).process(noisy, SR), noisy)

    def test_a_profile_it_learned_itself_is_dropped_on_reset(self) -> None:
        """What the head of one buffer said says nothing about the next."""
        noisy, _ = noisy_tone(body_s=0.2)
        effect = NoiseReduceEffect()

        effect.process(noisy, SR)
        assert effect.profile is not None

        effect.reset()
        assert effect.profile is None

    def test_a_profile_it_was_given_is_a_parameter_and_stays(self) -> None:
        noisy, _ = noisy_tone(body_s=0.2)
        profile = learn_noise_profile(noisy, SR, duration_s=0.3)
        effect = NoiseReduceEffect(profile=profile)

        effect.process(noisy, SR)
        effect.reset()

        assert effect.profile is profile

    def test_learning_from_a_selection_adopts_it(self) -> None:
        noisy, _ = noisy_tone()
        effect = NoiseReduceEffect()

        profile = effect.learn_from(noisy, SR, start_s=0.05, duration_s=0.3)

        assert effect.profile is profile
        assert profile.level_db == pytest.approx(-26.02, abs=0.5)

    def test_parameters_round_trip_for_a_preset(self) -> None:
        params = NoiseReduceEffect(
            reduction_db=18.0, over_subtraction=2.0, noise_ms=500.0, fft_size=1024
        ).parameters()

        assert params["reduction_db"] == 18.0
        assert params["over_subtraction"] == 2.0
        assert params["noise_ms"] == 500.0
        assert params["fft_size"] == 1024 and params["hop_size"] == 256

    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [
            ({"reduction_db": -1.0}, "reduction_db"),
            ({"over_subtraction": 0.0}, "over_subtraction"),
            ({"smoothing": 1.0}, "smoothing"),
            ({"noise_ms": -10.0}, "noise_ms"),
            ({"fft_size": 1024, "hop_size": 300}, "divisor"),
        ],
    )
    def test_settings_that_cannot_work_are_refused(
        self, kwargs: dict[str, float], message: str
    ) -> None:
        with pytest.raises(ValueError, match=message):
            NoiseReduceEffect(**kwargs)


def test_the_whole_repair_suite_combines_into_one_chain() -> None:
    """Hum out, then ticks, then the hiss that was under both of them."""
    noisy, clean = noisy_tone()
    t = np.arange(noisy.size) / SR
    damaged = noisy + 0.05 * np.sin(2 * np.pi * 50.0 * t)
    damaged[30_000] += 0.7
    damaged[45_000] += 0.7

    reducer = NoiseReduceEffect()
    chain = EffectChain([DeHumEffect(frequency=50.0), DeClickEffect(), reducer])
    cleaned = chain.process(damaged, SR)

    # Notching and interpolating are sample-aligned, so the only delay in the
    # chain is the noise reducer's window; the measurement shifts back by it.
    settled = cleaned[reducer.latency_samples() :]

    assert tone_level(settled[BODY], 50.0) < 0.002
    assert tone_level(settled[BODY], 440.0) == pytest.approx(0.3, rel=0.03)
    assert rms(settled[PAUSE]) < rms(damaged[PAUSE]) / 8.0
