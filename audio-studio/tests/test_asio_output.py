"""Mocked PortAudio ASIO host selection for the sounddevice backend."""

from __future__ import annotations

import sys
import types
from typing import Any

import numpy as np
import pytest

from audio_studio.core import sounddevice_output as sounddevice_module
from audio_studio.core.sounddevice_output import ASIO_ENV_VAR, SoundDeviceOutput

SAMPLE_RATE = 48_000
CHANNELS = 2
ASIO_DEVICE = 2


class FakeStream:
    def __init__(self, **config: Any) -> None:
        self.config = config

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def close(self) -> None:
        pass


class FakeSoundDevice(types.ModuleType):
    def __init__(self, *, asio: bool = True, reject_asio: bool = False) -> None:
        super().__init__("sounddevice")
        self.reject_asio = reject_asio
        self.attempts: list[int | str | None] = []
        self.streams: list[FakeStream] = []
        self.hostapis = [
            {"name": "Windows WASAPI", "default_output_device": 0},
            {"name": "ASIO" if asio else "Windows DirectSound", "default_output_device": 2},
        ]
        self.devices = [
            {"name": "Speakers", "hostapi": 0, "max_output_channels": 2},
            {"name": "ASIO Input", "hostapi": 1, "max_output_channels": 0},
            {"name": "ASIO Output", "hostapi": 1, "max_output_channels": 2},
        ]

    def query_hostapis(self, index: int | None = None) -> Any:
        return self.hostapis if index is None else self.hostapis[index]

    def query_devices(self, device: Any = None, kind: str | None = None) -> Any:
        if device is None and kind is None:
            return self.devices
        if device is None:
            device = 0
        return self.devices[int(device)]

    def OutputStream(self, **kwargs: Any) -> FakeStream:  # noqa: N802
        device = kwargs["device"]
        self.attempts.append(device)
        if self.reject_asio and device == ASIO_DEVICE:
            raise RuntimeError("ASIO driver is busy")
        stream = FakeStream(**kwargs)
        self.streams.append(stream)
        return stream


def silence(n_frames: int) -> np.ndarray:
    return np.zeros((n_frames, CHANNELS), dtype=np.float32)


@pytest.fixture()
def windows_asio(
    monkeypatch: pytest.MonkeyPatch,
) -> FakeSoundDevice:
    module = FakeSoundDevice()
    monkeypatch.setitem(sys.modules, "sounddevice", module)
    monkeypatch.setattr(sounddevice_module.sys, "platform", "win32")
    monkeypatch.setenv(ASIO_ENV_VAR, "1")
    return module


def test_opt_in_prefers_the_asio_host_output(windows_asio: FakeSoundDevice) -> None:
    backend = SoundDeviceOutput()
    backend.open(SAMPLE_RATE, CHANNELS, silence)
    try:
        assert windows_asio.streams[0].config["device"] == ASIO_DEVICE
        assert backend.name == "sounddevice (ASIO)"
    finally:
        backend.close()


def test_explicit_device_is_never_overridden(windows_asio: FakeSoundDevice) -> None:
    backend = SoundDeviceOutput(device=0)
    backend.open(SAMPLE_RATE, CHANNELS, silence)
    try:
        assert windows_asio.streams[0].config["device"] == 0
        assert backend.name == "sounddevice"
    finally:
        backend.close()


def test_env_switch_is_windows_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = FakeSoundDevice()
    monkeypatch.setitem(sys.modules, "sounddevice", module)
    monkeypatch.setattr(sounddevice_module.sys, "platform", "linux")
    monkeypatch.setenv(ASIO_ENV_VAR, "1")

    backend = SoundDeviceOutput()
    backend.open(SAMPLE_RATE, CHANNELS, silence)
    try:
        assert module.streams[0].config["device"] is None
    finally:
        backend.close()


def test_missing_asio_host_keeps_the_default_device(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = FakeSoundDevice(asio=False)
    monkeypatch.setitem(sys.modules, "sounddevice", module)
    monkeypatch.setattr(sounddevice_module.sys, "platform", "win32")
    monkeypatch.setenv(ASIO_ENV_VAR, "1")

    backend = SoundDeviceOutput()
    backend.open(SAMPLE_RATE, CHANNELS, silence)
    try:
        assert module.streams[0].config["device"] is None
        assert backend.name == "sounddevice"
    finally:
        backend.close()


def test_rejected_asio_stream_falls_back_to_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = FakeSoundDevice(reject_asio=True)
    monkeypatch.setitem(sys.modules, "sounddevice", module)
    monkeypatch.setattr(sounddevice_module.sys, "platform", "win32")
    monkeypatch.setenv(ASIO_ENV_VAR, "1")

    backend = SoundDeviceOutput()
    backend.open(SAMPLE_RATE, CHANNELS, silence)
    try:
        assert module.attempts[:3] == [ASIO_DEVICE, ASIO_DEVICE, ASIO_DEVICE]
        assert module.streams[-1].config["device"] is None
        assert backend.name == "sounddevice"
    finally:
        backend.close()
