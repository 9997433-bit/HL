"""Compressor and true-peak limiter behavior and streaming contract."""

from __future__ import annotations

import numpy as np
import pytest

from audio_studio.dsp.effects import CompressorEffect, Effect, LimiterEffect
from audio_studio.dsp.util import db_to_linear, linear_to_db, true_peak_level

SR = 48_000


def _stream(effect: Effect, audio: np.ndarray, sizes: tuple[int, ...]) -> np.ndarray:
    """Process successive irregular blocks, including channel-first audio."""
    effect.reset()
    effect.prepare(SR, 1 if audio.ndim == 1 else audio.shape[0])
    output: list[np.ndarray] = []
    offset = 0
    size_index = 0
    while offset < audio.shape[-1]:
        size = sizes[size_index % len(sizes)]
        output.append(
            effect.process_block(
                audio[..., offset : offset + size],
                SR,
                channels_last=False if audio.ndim == 2 else None,
            )
        )
        offset += size
        size_index += 1
    return np.concatenate(output, axis=-1)


@pytest.mark.parametrize(
    "effect",
    [
        CompressorEffect(
            threshold_db=-20.0,
            ratio=5.0,
            attack_ms=3.0,
            release_ms=75.0,
            lookahead_ms=2.0,
        ),
        LimiterEffect(ceiling_db=-3.0, release_ms=35.0, lookahead_ms=2.0),
    ],
)
def test_offline_and_irregular_streaming_are_equivalent(effect: Effect) -> None:
    rng = np.random.default_rng(42)
    audio = (0.45 * rng.standard_normal((2, 8193))).astype(np.float32)

    offline = effect.process(audio, SR)
    streamed = _stream(effect, audio, (1, 17, 256, 509, 31))

    assert np.array_equal(streamed, offline)


def test_compressor_reduces_gain_above_threshold() -> None:
    effect = CompressorEffect(
        threshold_db=-12.0,
        ratio=4.0,
        attack_ms=0.0,
        release_ms=100.0,
        lookahead_ms=0.0,
        knee_db=0.0,
    )
    output = effect.process(np.ones(SR // 10), SR)

    # 0 dBFS compressed 4:1 above -12 dBFS lands at -9 dBFS.
    assert float(linear_to_db(np.mean(np.abs(output)))) == pytest.approx(-9.0, abs=0.01)
    assert effect.gain_reduction_db == pytest.approx(9.0, abs=0.01)


def test_compressor_soft_knee_starts_before_threshold() -> None:
    level_db = -14.0
    audio = np.full(2048, float(db_to_linear(level_db)), dtype=np.float32)
    soft = CompressorEffect(
        threshold_db=-12.0,
        ratio=4.0,
        attack_ms=0.0,
        lookahead_ms=0.0,
        knee_db=8.0,
    ).process(audio, SR)
    hard = CompressorEffect(
        threshold_db=-12.0,
        ratio=4.0,
        attack_ms=0.0,
        lookahead_ms=0.0,
        knee_db=0.0,
    ).process(audio, SR)

    assert np.max(np.abs(soft)) < np.max(np.abs(hard))
    assert np.allclose(hard, audio)


def _isp_vector(length: int = 16_384) -> np.ndarray:
    """fs/4 at 45 degrees: samples read -3.01 dBFS but reconstruct at 0 dBTP."""
    sample = np.arange(length)
    return np.sin(np.pi * sample / 2.0 + np.pi / 4.0).astype(np.float32)


def test_limiter_catches_an_intersample_peak_not_visible_in_samples() -> None:
    audio = _isp_vector()
    assert float(linear_to_db(np.max(np.abs(audio)))) == pytest.approx(-3.01, abs=0.02)
    assert float(linear_to_db(true_peak_level(audio))) == pytest.approx(0.0, abs=0.2)

    output = LimiterEffect(ceiling_db=-6.0).process(audio, SR)

    assert float(linear_to_db(true_peak_level(output))) <= -6.0 + 0.02


@pytest.mark.parametrize("ceiling_db", [-0.1, -1.0, -3.0, -9.0])
def test_isp_acceptance_vectors_stay_below_the_dbtp_ceiling(ceiling_db: float) -> None:
    """D3-style vector check: the reconstructed output, not samples, is bounded."""
    output = LimiterEffect(ceiling_db=ceiling_db).process(1.2 * _isp_vector(), SR)
    measured_db_tp = float(linear_to_db(true_peak_level(output, exact=True)))

    assert measured_db_tp <= ceiling_db + 0.02


def test_limiter_links_channels_to_preserve_the_stereo_image() -> None:
    tone = _isp_vector(8192)
    audio = np.stack((1.2 * tone, 0.3 * tone))
    effect = LimiterEffect(ceiling_db=-3.0)
    output = effect.process(audio, SR)
    latency = effect.latency_samples(SR)
    active = slice(latency + 100, -100)

    ratio = np.abs(output[0, active] / output[1, active])
    assert np.allclose(ratio, 4.0, atol=1e-6)


def test_limiter_renews_lookahead_hold_for_dense_peaks() -> None:
    rng = np.random.default_rng(7)
    dense_peaks = (0.8 * rng.standard_normal(20_000)).astype(np.float32)
    output = LimiterEffect(ceiling_db=-1.0).process(dense_peaks, SR)

    assert float(linear_to_db(true_peak_level(output, exact=True))) <= -1.0 + 0.02


def test_parameters_include_dynamics_controls() -> None:
    compressor = CompressorEffect(threshold_db=-24.0, ratio=6.0).parameters()
    limiter = LimiterEffect(ceiling_db=-2.0).parameters()

    assert compressor["threshold_db"] == -24.0
    assert compressor["ratio"] == 6.0
    assert limiter["ceiling_db"] == -2.0
    assert limiter["oversample"] == 4


@pytest.mark.parametrize(
    "factory",
    [
        lambda: CompressorEffect(ratio=0.5),
        lambda: CompressorEffect(attack_ms=-1.0),
        lambda: LimiterEffect(ceiling_db=0.1),
        lambda: LimiterEffect(oversample=1),
    ],
)
def test_invalid_parameters_are_rejected(factory) -> None:
    with pytest.raises(ValueError):
        factory()
