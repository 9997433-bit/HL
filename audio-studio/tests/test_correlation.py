"""Phase correlation meter: one-shot measurement and streaming ballistics."""

from __future__ import annotations

import numpy as np
import pytest

from audio_studio.dsp import CorrelationMeter, phase_correlation

SAMPLE_RATE = 48_000


def _sine(frequency: float, seconds: float = 0.25, phase: float = 0.0) -> np.ndarray:
    time = np.arange(round(SAMPLE_RATE * seconds), dtype=np.float64) / SAMPLE_RATE
    return np.sin(2.0 * np.pi * frequency * time + phase)


def _stereo(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    return np.stack((left, right)).astype(np.float32)


class TestPhaseCorrelation:
    def test_identical_channels_read_plus_one(self) -> None:
        tone = _sine(997.0)
        assert phase_correlation(_stereo(tone, tone)) == pytest.approx(1.0)

    def test_polarity_inverted_channels_read_minus_one(self) -> None:
        tone = _sine(997.0)
        assert phase_correlation(_stereo(tone, -tone)) == pytest.approx(-1.0)

    def test_reading_is_level_independent(self) -> None:
        """A hard-panned mono source still folds to mono: it must read +1."""
        tone = _sine(440.0)
        assert phase_correlation(_stereo(tone, 0.05 * tone)) == pytest.approx(1.0)
        assert phase_correlation(_stereo(0.7 * tone, -0.01 * tone)) == pytest.approx(-1.0)

    def test_quadrature_channels_read_zero(self) -> None:
        """A 90-degree phase offset is the textbook mid-scale reading."""
        left = _sine(1_000.0, seconds=1.0)
        right = _sine(1_000.0, seconds=1.0, phase=np.pi / 2.0)
        assert phase_correlation(_stereo(left, right)) == pytest.approx(0.0, abs=1e-3)

    def test_uncorrelated_noise_reads_near_zero(self) -> None:
        rng = np.random.default_rng(1770)
        left = rng.standard_normal(SAMPLE_RATE).astype(np.float32)
        right = rng.standard_normal(SAMPLE_RATE).astype(np.float32)
        assert abs(phase_correlation(np.stack((left, right)))) < 0.02

    def test_mono_and_silence_read_plus_one(self) -> None:
        assert phase_correlation(_sine(997.0)) == pytest.approx(1.0)
        assert phase_correlation(np.zeros((2, 4_800), dtype=np.float32)) == 1.0
        assert phase_correlation(np.zeros((2, 0), dtype=np.float32)) == 1.0

    def test_interleaved_layout_matches_planar(self) -> None:
        tone = _sine(200.0)
        planar = _stereo(tone, -0.5 * tone)
        interleaved = planar.T.copy()
        assert phase_correlation(interleaved, channels_last=True) == pytest.approx(
            phase_correlation(planar, channels_last=False)
        )

    def test_reading_is_clamped_to_the_meter_scale(self) -> None:
        tone = _sine(997.0)
        assert -1.0 <= phase_correlation(_stereo(tone, tone * 1.0000001)) <= 1.0


class TestCorrelationMeter:
    def test_fresh_meter_idles_at_plus_one(self) -> None:
        meter = CorrelationMeter(SAMPLE_RATE)
        assert meter.correlation == 1.0
        assert meter.frames_processed == 0

    def test_needle_converges_on_out_of_phase_program(self) -> None:
        tone = _sine(997.0, seconds=1.0)
        stereo = _stereo(tone, -tone)
        meter = CorrelationMeter(SAMPLE_RATE)
        for start in range(0, stereo.shape[1], 512):
            meter.process_block(stereo[:, start : start + 512])
        assert meter.correlation == pytest.approx(-1.0, abs=1e-6)
        assert meter.frames_processed == stereo.shape[1]

    def test_ballistics_are_block_size_independent(self) -> None:
        """Chopping the same audio differently must land on the same needle."""
        rng = np.random.default_rng(31)
        audio = rng.standard_normal((2, SAMPLE_RATE)).astype(np.float32)

        readings = []
        for sizes in ((SAMPLE_RATE,), (64,) * (SAMPLE_RATE // 64), (1_000, 47_000)):
            meter = CorrelationMeter(SAMPLE_RATE)
            offset = 0
            for size in sizes:
                meter.process_block(audio[:, offset : offset + size])
                offset += size
            readings.append(meter.correlation)

        assert readings[0] == pytest.approx(readings[1], abs=0.05)
        assert readings[0] == pytest.approx(readings[2], abs=0.05)

    def test_needle_tracks_a_phase_flip_within_the_window(self) -> None:
        """The meter is a meter: it follows the program, with ~300 ms lag."""
        tone = _sine(997.0, seconds=2.0)
        in_phase = _stereo(tone, tone)
        flipped = _stereo(tone, -tone)
        meter = CorrelationMeter(SAMPLE_RATE, window_ms=300.0)

        meter.process_block(in_phase)
        assert meter.correlation == pytest.approx(1.0, abs=1e-6)

        # One window's worth of inverted audio swings the needle below zero;
        # several more time constants settle it onto -1.
        meter.process_block(flipped[:, : round(0.3 * SAMPLE_RATE)])
        assert meter.correlation < 0.0
        for start in range(round(0.3 * SAMPLE_RATE), flipped.shape[1], 512):
            meter.process_block(flipped[:, start : start + 512])
        assert meter.correlation == pytest.approx(-1.0, abs=0.01)

    def test_silence_holds_the_last_reading(self) -> None:
        tone = _sine(997.0)
        meter = CorrelationMeter(SAMPLE_RATE)
        meter.process_block(_stereo(tone, -tone))
        before = meter.correlation
        meter.process_block(np.zeros((2, SAMPLE_RATE), dtype=np.float32))
        assert meter.correlation == before

    def test_empty_block_is_a_no_op(self) -> None:
        meter = CorrelationMeter(SAMPLE_RATE)
        assert meter.process_block(np.zeros((2, 0), dtype=np.float32)) == 1.0
        assert meter.frames_processed == 0

    def test_reset_returns_to_idle(self) -> None:
        tone = _sine(997.0)
        meter = CorrelationMeter(SAMPLE_RATE)
        meter.process_block(_stereo(tone, -tone))
        meter.reset()
        assert meter.correlation == 1.0
        assert meter.frames_processed == 0

    def test_invalid_construction_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            CorrelationMeter(0)
        with pytest.raises(ValueError):
            CorrelationMeter(SAMPLE_RATE, window_ms=0.0)

    def test_streaming_agrees_with_the_one_shot_measurement(self) -> None:
        """On stationary program the needle settles on the buffer figure."""
        rng = np.random.default_rng(8)
        shared = rng.standard_normal(2 * SAMPLE_RATE)
        left = shared + 0.5 * rng.standard_normal(2 * SAMPLE_RATE)
        right = shared + 0.5 * rng.standard_normal(2 * SAMPLE_RATE)
        stereo = np.stack((left, right)).astype(np.float32)

        meter = CorrelationMeter(SAMPLE_RATE)
        for start in range(0, stereo.shape[1], 4_096):
            meter.process_block(stereo[:, start : start + 4_096])

        assert meter.correlation == pytest.approx(
            phase_correlation(stereo), abs=0.02
        )
