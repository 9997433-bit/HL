"""Peak pyramid correctness against brute-force numpy reductions."""

from __future__ import annotations

import numpy as np
import pytest

from audio_studio.core.peaks import BASE_DECIMATION, PeakPyramid


def noisy_signal(n_frames: int = 200_000, channels: int = 2) -> np.ndarray:
    rng = np.random.default_rng(1234)
    t = np.arange(n_frames, dtype=np.float32) / 44100.0
    base = np.sin(2.0 * np.pi * 220.0 * t) * 0.6
    data = np.empty((n_frames, channels), dtype=np.float32)
    for ch in range(channels):
        data[:, ch] = base * (ch + 1) * 0.5 + rng.standard_normal(n_frames).astype(np.float32) * 0.05
    return np.clip(data, -1.0, 1.0)


def test_pyramid_builds_multiple_levels_for_long_clips() -> None:
    pyramid = PeakPyramid(noisy_signal())

    assert pyramid.n_frames == 200_000
    assert pyramid.n_channels == 2
    assert pyramid.n_levels >= 1


def test_full_view_envelope_bounds_every_sample() -> None:
    data = noisy_signal(50_000)
    pyramid = PeakPyramid(data)

    envelope = pyramid.envelope(0, 50_000, 500)

    assert envelope.n_bins == 500
    assert envelope.minimum.min() == pytest.approx(data.min(), abs=1e-6)
    assert envelope.maximum.max() == pytest.approx(data.max(), abs=1e-6)
    assert np.all(envelope.minimum <= envelope.maximum + 1e-7)


def test_envelope_matches_a_brute_force_reduction() -> None:
    data = noisy_signal(64 * BASE_DECIMATION, channels=1)
    pyramid = PeakPyramid(data)
    n_bins = 64

    envelope = pyramid.envelope(0, data.shape[0], n_bins)
    blocks = data.reshape(n_bins, -1, 1)

    assert np.allclose(envelope.minimum, blocks.min(axis=1), atol=1e-6)
    assert np.allclose(envelope.maximum, blocks.max(axis=1), atol=1e-6)
    assert np.allclose(
        envelope.rms, np.sqrt(np.square(blocks, dtype=np.float64).mean(axis=1)), atol=1e-5
    )


def test_partial_range_does_not_leak_samples_from_outside() -> None:
    data = np.zeros((100_000, 1), dtype=np.float32)
    data[80_000:80_100] = 1.0  # a burst well outside the queried window
    pyramid = PeakPyramid(data)

    envelope = pyramid.envelope(0, 40_000, 200)

    assert envelope.maximum.max() == pytest.approx(0.0)
    assert pyramid.envelope(0, 100_000, 200).maximum.max() == pytest.approx(1.0)


def test_zoomed_in_view_reads_raw_samples() -> None:
    data = noisy_signal(20_000, channels=1)
    pyramid = PeakPyramid(data)

    envelope = pyramid.envelope(1_000, 1_100, 100)

    assert envelope.n_bins == 100
    assert np.allclose(envelope.maximum[:, 0], data[1_000:1_100, 0], atol=1e-6)
    assert np.allclose(envelope.minimum[:, 0], data[1_000:1_100, 0], atol=1e-6)


def test_more_bins_than_frames_is_still_well_formed() -> None:
    data = noisy_signal(50, channels=2)
    pyramid = PeakPyramid(data)

    envelope = pyramid.envelope(0, 50, 400)

    assert envelope.n_bins == 400
    assert envelope.n_channels == 2
    assert np.all(np.isfinite(envelope.minimum))
    assert np.all(envelope.rms >= 0.0)


def test_empty_clip_returns_zero_envelope() -> None:
    pyramid = PeakPyramid(np.zeros((0, 2), dtype=np.float32))

    envelope = pyramid.envelope(0, 0, 32)

    assert envelope.n_bins == 32
    assert np.all(envelope.maximum == 0.0)


def test_channels_are_summarised_independently() -> None:
    data = np.zeros((10_000, 2), dtype=np.float32)
    data[:, 0] = 0.25
    data[:, 1] = -0.75
    pyramid = PeakPyramid(data)

    envelope = pyramid.envelope(0, 10_000, 50)

    assert np.allclose(envelope.maximum[:, 0], 0.25, atol=1e-6)
    assert np.allclose(envelope.minimum[:, 1], -0.75, atol=1e-6)
    assert np.allclose(envelope.rms[:, 1], 0.75, atol=1e-5)


def test_invalid_bin_count_is_rejected() -> None:
    pyramid = PeakPyramid(noisy_signal(1_000, 1))

    with pytest.raises(ValueError, match="n_bins must be positive"):
        pyramid.envelope(0, 1_000, 0)
