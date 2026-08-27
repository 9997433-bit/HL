"""TPDF dither behavior at the integer export boundary."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import soundfile as sf

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
AUDIO_STUDIO_ROOT = REPOSITORY_ROOT / "audio-studio"
if str(AUDIO_STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(AUDIO_STUDIO_ROOT))

from audio_studio.core.loader import save_audio
from audio_studio.core.types import AudioBuffer


def _program_with_silence_tail() -> AudioBuffer:
    sample_rate = 48_000
    tone_frames = 4_800
    tail_frames = 8_192
    time = np.arange(tone_frames, dtype=np.float32) / sample_rate
    tone = 0.25 * np.sin(2.0 * np.pi * 997.0 * time)
    data = np.concatenate((tone, np.zeros(tail_frames, dtype=np.float32)))
    return AudioBuffer(data[:, np.newaxis], sample_rate)


def test_float32_to_pcm16_dither_leaves_noise_on_silence_tail(tmp_path: Path) -> None:
    target = tmp_path / "dithered.wav"
    save_audio(target, _program_with_silence_tail(), subtype="PCM_16")

    rendered, sample_rate = sf.read(target, dtype="float32", always_2d=True)
    tail = rendered[-8_192:, 0]

    assert sample_rate == 48_000
    assert np.count_nonzero(tail) > 0
    assert float(np.max(np.abs(tail))) <= 1.0 / 32_768.0
    assert float(np.sqrt(np.mean(np.square(tail, dtype=np.float64)))) > 0.0


def test_pcm16_dither_can_be_disabled_for_bit_exact_output(tmp_path: Path) -> None:
    target = tmp_path / "undithered.wav"
    save_audio(
        target,
        _program_with_silence_tail(),
        subtype="PCM_16",
        dither=False,
    )

    rendered, _ = sf.read(target, dtype="float32", always_2d=True)
    assert np.count_nonzero(rendered[-8_192:, 0]) == 0


def test_float_export_does_not_receive_integer_dither(tmp_path: Path) -> None:
    target = tmp_path / "floating.wav"
    silence = AudioBuffer.silence(4_096, 1, 48_000)
    save_audio(target, silence, subtype="FLOAT")

    rendered, _ = sf.read(target, dtype="float32", always_2d=True)
    assert np.count_nonzero(rendered) == 0
