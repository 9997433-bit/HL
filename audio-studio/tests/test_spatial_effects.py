"""Noise gate, delay and FDN reverb behavior and streaming contract."""

from __future__ import annotations

import numpy as np
import pytest

from audio_studio.dsp.effects import (
    DelayEffect,
    Effect,
    FDNReverbEffect,
    NoiseGateEffect,
)

SR = 48_000


def _stream(effect: Effect, audio: np.ndarray, sizes: tuple[int, ...]) -> np.ndarray:
    effect.reset()
    effect.prepare(SR, 1 if audio.ndim == 1 else audio.shape[0])
    blocks: list[np.ndarray] = []
    offset = 0
    size_index = 0
    while offset < audio.shape[-1]:
        size = sizes[size_index % len(sizes)]
        blocks.append(
            effect.process_block(
                audio[..., offset : offset + size],
                SR,
                channels_last=False if audio.ndim == 2 else None,
            )
        )
        offset += size
        size_index += 1
    return np.concatenate(blocks, axis=-1)


@pytest.mark.parametrize(
    "effect",
    [
        NoiseGateEffect(
            threshold_db=-30.0,
            attack_ms=2.0,
            release_ms=75.0,
            hold_ms=11.0,
            ratio=5.0,
            floor_db=-70.0,
            mix=0.8,
        ),
        DelayEffect(time_ms=13.7, feedback=0.62, mix=0.45),
        FDNReverbEffect(room_size=0.72, damping=0.41, mix=0.35),
    ],
)
def test_offline_and_irregular_streaming_are_equivalent(effect: Effect) -> None:
    rng = np.random.default_rng(23)
    audio = (0.3 * rng.standard_normal((2, 8193))).astype(np.float32)

    offline = effect.process(audio, SR)
    streamed = _stream(effect, audio, (1, 17, 256, 509, 31))

    assert np.array_equal(streamed, offline)


def test_noise_gate_reduces_room_tone_but_passes_loud_audio() -> None:
    quiet = np.full(SR // 20, 0.005, dtype=np.float32)
    loud = np.full(SR // 20, 0.5, dtype=np.float32)
    audio = np.concatenate((quiet, loud))
    output = NoiseGateEffect(
        threshold_db=-30.0,
        attack_ms=0.0,
        release_ms=0.0,
        hold_ms=0.0,
        ratio=4.0,
        floor_db=-60.0,
    ).process(audio, SR)

    assert np.max(np.abs(output[: quiet.size])) < np.max(np.abs(quiet)) * 0.01
    assert np.array_equal(output[quiet.size :], loud)


def test_noise_gate_links_stereo_channels() -> None:
    loud = np.full(512, 0.5, dtype=np.float32)
    quiet = np.full(512, 0.001, dtype=np.float32)
    output = NoiseGateEffect(attack_ms=0.0).process(np.stack((loud, quiet)), SR)

    assert np.array_equal(output[0], loud)
    assert np.array_equal(output[1], quiet)


def test_delay_places_audible_feedback_echoes_at_the_requested_time() -> None:
    delay = 480
    impulse = np.zeros(delay * 3 + 1, dtype=np.float32)
    impulse[0] = 1.0

    output = DelayEffect(time_ms=10.0, feedback=0.5, mix=1.0).process(impulse, SR)

    assert output[0] == 0.0
    assert output[delay] == pytest.approx(1.0)
    assert output[2 * delay] == pytest.approx(0.5)
    assert output[3 * delay] == pytest.approx(0.25)


def test_delay_mix_blends_the_dry_impulse_and_wet_echo() -> None:
    impulse = np.zeros(1000, dtype=np.float32)
    impulse[0] = 1.0

    output = DelayEffect(time_ms=10.0, feedback=0.0, mix=0.25).process(impulse, SR)

    assert output[0] == pytest.approx(0.75)
    assert output[480] == pytest.approx(0.25)


def test_fdn_reverb_turns_an_impulse_into_a_decaying_tail() -> None:
    impulse = np.zeros(SR, dtype=np.float32)
    impulse[0] = 1.0
    effect = FDNReverbEffect(room_size=0.65, damping=0.3, mix=1.0)

    output = effect.process(impulse, SR)
    first_delay = min(effect._lengths(SR))  # noqa: SLF001 - verifies network timing

    assert np.all(output[:first_delay] == 0.0)
    assert np.max(np.abs(output[first_delay:])) > 0.1
    assert np.count_nonzero(np.abs(output) > 1e-5) > 100
    assert np.sum(np.square(output[SR // 4 :])) > 0.0


def test_spatial_parameters_are_serialisable() -> None:
    gate = NoiseGateEffect(threshold_db=-36.0, hold_ms=25.0).parameters()
    delay = DelayEffect(time_ms=125.0, feedback=0.4).parameters()
    reverb = FDNReverbEffect(room_size=0.8, damping=0.6).parameters()

    assert gate["threshold_db"] == -36.0
    assert gate["hold_ms"] == 25.0
    assert delay["time_ms"] == 125.0
    assert delay["feedback"] == 0.4
    assert reverb["room_size"] == 0.8
    assert reverb["damping"] == 0.6


@pytest.mark.parametrize(
    "factory",
    [
        lambda: NoiseGateEffect(ratio=0.5),
        lambda: NoiseGateEffect(attack_ms=-1.0),
        lambda: DelayEffect(time_ms=-1.0),
        lambda: DelayEffect(feedback=1.0),
        lambda: FDNReverbEffect(room_size=1.1),
        lambda: FDNReverbEffect(damping=-0.1),
    ],
)
def test_invalid_parameters_are_rejected(factory) -> None:
    with pytest.raises(ValueError):
        factory()
