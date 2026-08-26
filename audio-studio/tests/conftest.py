"""Shared fixtures: synthetic audio files and a deterministic engine."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest

# Qt must be told to use the offscreen plugin before any widget is created.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from audio_studio.core.engine import AudioEngine  # noqa: E402
from audio_studio.core.loader import LoadedAudio, save_audio  # noqa: E402
from audio_studio.core.output import NullOutput  # noqa: E402
from audio_studio.core.types import AudioBuffer, AudioFormat  # noqa: E402

SAMPLE_RATE = 44100
DURATION = 1.5


def make_tone(
    frequency: float = 440.0,
    *,
    duration: float = DURATION,
    sample_rate: int = SAMPLE_RATE,
    channels: int = 2,
    amplitude: float = 0.5,
) -> AudioBuffer:
    """Deterministic multi-channel test tone; each channel gets its own octave."""
    n_frames = int(duration * sample_rate)
    t = np.arange(n_frames, dtype=np.float32) / sample_rate
    data = np.empty((n_frames, channels), dtype=np.float32)
    for ch in range(channels):
        data[:, ch] = amplitude * np.sin(2.0 * np.pi * frequency * (ch + 1) * t)
    return AudioBuffer(data, sample_rate)


@pytest.fixture(scope="session")
def tone() -> AudioBuffer:
    return make_tone()


@pytest.fixture(scope="session")
def wav_path(tmp_path_factory: pytest.TempPathFactory, tone: AudioBuffer) -> Path:
    path = tmp_path_factory.mktemp("audio") / "tone.wav"
    save_audio(path, tone, subtype="PCM_16")
    return path


@pytest.fixture(scope="session")
def flac_path(tmp_path_factory: pytest.TempPathFactory, tone: AudioBuffer) -> Path:
    path = tmp_path_factory.mktemp("audio") / "tone.flac"
    save_audio(path, tone, subtype="PCM_16")
    return path


@pytest.fixture(scope="session")
def mono_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("audio") / "mono.wav"
    save_audio(path, make_tone(220.0, channels=1, duration=0.5), subtype="PCM_24")
    return path


@pytest.fixture()
def loaded_clip(tone: AudioBuffer, tmp_path: Path) -> LoadedAudio:
    """An in-memory clip that never touches the filesystem loader."""
    return LoadedAudio(
        buffer=tone,
        audio_format=AudioFormat(tone.sample_rate, tone.n_channels, "PCM_16", "WAV"),
        path=tmp_path / "in-memory.wav",
    )


@pytest.fixture()
def engine() -> Iterator[AudioEngine]:
    """Engine on a manually-pumped backend so playback is fully deterministic."""
    instance = AudioEngine(NullOutput(realtime=False), block_size=256, ring_blocks=8)
    yield instance
    instance.shutdown()


@pytest.fixture()
def realtime_engine() -> Iterator[AudioEngine]:
    """Engine on the simulated wall-clock backend, for timing-sensitive checks."""
    instance = AudioEngine(NullOutput(realtime=True), block_size=256, ring_blocks=8)
    yield instance
    instance.shutdown()


@pytest.fixture(scope="session")
def qapp() -> Iterator[object]:
    """A single offscreen QApplication shared by the widget tests."""
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app
