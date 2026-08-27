"""Offline clipped-peak detection and cubic reconstruction."""

from __future__ import annotations

import numpy as np
import pytest

from audio_studio.dsp.repair import (
    DeClipEffect,
    detect_clipping,
    repair_clipping,
)

SAMPLE_RATE = 48_000


def sine(frequency: float, seconds: float, amplitude: float = 0.9) -> np.ndarray:
    frames = np.arange(round(seconds * SAMPLE_RATE), dtype=np.float64)
    return amplitude * np.sin(2.0 * np.pi * frequency * frames / SAMPLE_RATE)


def test_cubic_reconstruction_restores_flattened_peaks() -> None:
    clean = sine(500.0, 0.1)
    damaged = np.clip(clean, -0.55, 0.55)

    repaired, report = repair_clipping(damaged, SAMPLE_RATE, threshold=0.55)

    clipped = damaged != clean
    before = np.sqrt(np.mean(np.square(damaged[clipped] - clean[clipped])))
    after = np.sqrt(np.mean(np.square(repaired[clipped] - clean[clipped])))
    assert report.count > 0
    assert report.repaired_count == report.count
    assert after < before / 5.0
    assert np.array_equal(repaired[~clipped], damaged[~clipped])


def test_clean_near_full_scale_audio_is_not_mistaken_for_a_plateau() -> None:
    clean = sine(997.0, 0.1, amplitude=0.99)
    repaired, report = repair_clipping(clean, SAMPLE_RATE, threshold=0.98)

    assert report.count == 0
    assert np.array_equal(repaired, clean)


def test_detection_reports_polarity_channel_and_half_open_range() -> None:
    audio = np.zeros((2, 64), dtype=np.float32)
    audio[0, 10:15] = 1.0
    audio[1, 30:36] = -1.0

    report = detect_clipping(audio, SAMPLE_RATE)

    actual = [
        (event.channel, event.start, event.stop, event.polarity)
        for event in report.events
    ]
    assert actual == [
        (0, 10, 15, 1),
        (1, 30, 36, -1),
    ]
    assert report.clipped_samples == 11


def test_interleaved_layout_and_float32_dtype_survive() -> None:
    clean = sine(400.0, 0.05).astype(np.float32)
    damaged = np.clip(clean, -0.6, 0.6)
    interleaved = np.column_stack((damaged, -damaged))

    repaired, report = repair_clipping(
        interleaved,
        SAMPLE_RATE,
        threshold=0.6,
        channels_last=True,
    )

    assert repaired.shape == interleaved.shape
    assert repaired.dtype == np.float32
    assert len(report.in_channel(0)) == len(report.in_channel(1)) > 0


def test_edge_and_overlong_plateaus_are_reported_but_not_rewritten() -> None:
    audio = np.zeros(100, dtype=np.float64)
    audio[:4] = 1.0
    audio[20:80] = -1.0

    repaired, report = repair_clipping(
        audio,
        1_000,
        max_clip_ms=10.0,
    )

    assert report.count == 2
    assert report.repaired_count == 0
    assert np.array_equal(repaired, audio)


def test_effect_is_offline_only_and_exposes_its_report() -> None:
    audio = np.clip(sine(440.0, 0.05), -0.5, 0.5)
    effect = DeClipEffect(clip_threshold=0.5)

    processed = effect.process(audio, SAMPLE_RATE)

    assert processed.shape == audio.shape
    assert effect.is_offline_only
    assert effect.last_report is not None and effect.last_report.repaired_count > 0
    assert effect.parameters()["threshold"] == 0.5
    with pytest.raises(NotImplementedError, match="whole signal"):
        effect.process_block(audio, SAMPLE_RATE)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"threshold": 0.0}, "threshold"),
        ({"flat_tolerance": -1.0}, "flat_tolerance"),
        ({"min_run_samples": 1}, "min_run_samples"),
    ],
)
def test_invalid_detection_controls_are_rejected(kwargs: dict[str, float], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        repair_clipping(np.zeros(10), SAMPLE_RATE, **kwargs)
