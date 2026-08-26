"""WASAPI exclusive-mode output (Windows-only, ``AUDIO_STUDIO_WASAPI_EXCLUSIVE=1``).

The backend is driven against a synthetic ``sounddevice`` module that mimics a
WASAPI host API, so the double opt-in gate (constructor flag *and* environment
switch), the host-API check and the shared-mode fallback are all exercised
without real hardware. The whole module is skipped off Windows: exclusive mode
never engages elsewhere by design, so the assertions would be vacuous.
"""

from __future__ import annotations

import sys
import types
from typing import Any

import numpy as np
import pytest

from audio_studio.core.output import (
    OUTPUT_BACKEND_ENV_VAR,
    WASAPI_EXCLUSIVE_ENV_VAR,
    create_output,
)
from audio_studio.core.sounddevice_output import SoundDeviceOutput

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="WASAPI exclusive mode is Windows-only"
)

SAMPLE_RATE = 48000
CHANNELS = 2


def silence(n_frames: int) -> np.ndarray:
    return np.zeros((n_frames, CHANNELS), dtype=np.float32)


# --------------------------------------------------------------------------- #
# Synthetic WASAPI-flavoured sounddevice module
# --------------------------------------------------------------------------- #


class FakeWasapiSettings:
    """Stand-in for ``sounddevice.WasapiSettings`` recording its arguments."""

    def __init__(self, *, exclusive: bool = False, **kwargs: Any) -> None:
        self.exclusive = exclusive
        self.kwargs = kwargs


class FakeOutputStream:
    def __init__(self, **kwargs: Any) -> None:
        self.config = kwargs
        self.active = False
        self.closed = False

    def start(self) -> None:
        self.active = True

    def stop(self) -> None:
        self.active = False

    def close(self) -> None:
        self.active = False
        self.closed = True


class FakeSoundDevice(types.ModuleType):
    """Synthetic binding advertising one output device on a chosen host API."""

    def __init__(
        self,
        *,
        hostapi_name: str = "Windows WASAPI",
        exclusive_open_error: Exception | None = None,
    ) -> None:
        super().__init__("sounddevice")
        self.hostapi_name = hostapi_name
        self.exclusive_open_error = exclusive_open_error
        self.streams: list[FakeOutputStream] = []
        self.WasapiSettings = FakeWasapiSettings

    def query_devices(self, device: Any = None, kind: str | None = None) -> dict[str, Any]:
        return {"name": "Fake Speakers", "hostapi": 0, "max_output_channels": CHANNELS}

    def query_hostapis(self, index: int | None = None) -> dict[str, Any]:
        return {"name": self.hostapi_name}

    def OutputStream(self, **kwargs: Any) -> FakeOutputStream:  # noqa: N802 - mirrors the binding
        if kwargs.get("extra_settings") is not None and self.exclusive_open_error is not None:
            raise self.exclusive_open_error
        stream = FakeOutputStream(**kwargs)
        self.streams.append(stream)
        return stream


@pytest.fixture()
def fake_sd(monkeypatch: pytest.MonkeyPatch) -> FakeSoundDevice:
    module = FakeSoundDevice()
    monkeypatch.setitem(sys.modules, "sounddevice", module)
    return module


@pytest.fixture()
def exclusive_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(WASAPI_EXCLUSIVE_ENV_VAR, "1")


# --------------------------------------------------------------------------- #
# The exclusive gate on the backend itself
# --------------------------------------------------------------------------- #


def test_exclusive_passes_wasapi_settings(fake_sd: FakeSoundDevice, exclusive_env: None) -> None:
    backend = SoundDeviceOutput(exclusive=True)
    backend.open(SAMPLE_RATE, CHANNELS, silence)
    try:
        extra = fake_sd.streams[0].config["extra_settings"]
        assert isinstance(extra, FakeWasapiSettings)
        assert extra.exclusive is True
        assert backend.name == "sounddevice (WASAPI exclusive)"
    finally:
        backend.close()


def test_env_switch_off_keeps_shared_mode(
    fake_sd: FakeSoundDevice, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The constructor flag alone must not engage exclusive mode."""
    monkeypatch.delenv(WASAPI_EXCLUSIVE_ENV_VAR, raising=False)
    backend = SoundDeviceOutput(exclusive=True)
    backend.open(SAMPLE_RATE, CHANNELS, silence)
    try:
        assert "extra_settings" not in fake_sd.streams[0].config
        assert backend.name == "sounddevice"
    finally:
        backend.close()


def test_default_constructor_stays_shared(
    fake_sd: FakeSoundDevice, exclusive_env: None
) -> None:
    """The environment switch alone must not engage exclusive mode either."""
    backend = SoundDeviceOutput()
    backend.open(SAMPLE_RATE, CHANNELS, silence)
    try:
        assert "extra_settings" not in fake_sd.streams[0].config
        assert backend.name == "sounddevice"
    finally:
        backend.close()


def test_non_wasapi_host_api_stays_shared(
    monkeypatch: pytest.MonkeyPatch, exclusive_env: None
) -> None:
    module = FakeSoundDevice(hostapi_name="MME")
    monkeypatch.setitem(sys.modules, "sounddevice", module)
    backend = SoundDeviceOutput(exclusive=True)
    backend.open(SAMPLE_RATE, CHANNELS, silence)
    try:
        assert "extra_settings" not in module.streams[0].config
        assert backend.name == "sounddevice"
    finally:
        backend.close()


def test_rejected_exclusive_stream_falls_back_to_shared(
    monkeypatch: pytest.MonkeyPatch, exclusive_env: None
) -> None:
    """A busy or format-refusing device degrades to shared mode, not to a crash."""
    module = FakeSoundDevice(exclusive_open_error=RuntimeError("device is busy"))
    monkeypatch.setitem(sys.modules, "sounddevice", module)
    backend = SoundDeviceOutput(exclusive=True)
    backend.open(SAMPLE_RATE, CHANNELS, silence)
    try:
        assert len(module.streams) == 1
        assert "extra_settings" not in module.streams[0].config
        assert backend.name == "sounddevice"
    finally:
        backend.close()


def test_reopen_re_evaluates_the_gate(
    fake_sd: FakeSoundDevice, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(WASAPI_EXCLUSIVE_ENV_VAR, "1")
    backend = SoundDeviceOutput(exclusive=True)
    backend.open(SAMPLE_RATE, CHANNELS, silence)
    assert backend.name == "sounddevice (WASAPI exclusive)"
    monkeypatch.setenv(WASAPI_EXCLUSIVE_ENV_VAR, "0")
    backend.open(SAMPLE_RATE, CHANNELS, silence)
    try:
        assert backend.name == "sounddevice"
        assert "extra_settings" not in fake_sd.streams[-1].config
    finally:
        backend.close()


# --------------------------------------------------------------------------- #
# create_output() honours the environment switch
# --------------------------------------------------------------------------- #


def test_create_output_engages_exclusive_from_env(
    fake_sd: FakeSoundDevice, exclusive_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(OUTPUT_BACKEND_ENV_VAR, "sounddevice")
    backend = create_output()
    assert isinstance(backend, SoundDeviceOutput)
    backend.open(SAMPLE_RATE, CHANNELS, silence)
    try:
        extra = fake_sd.streams[-1].config["extra_settings"]
        assert isinstance(extra, FakeWasapiSettings)
        assert extra.exclusive is True
        assert backend.name == "sounddevice (WASAPI exclusive)"
    finally:
        backend.close()


def test_create_output_defaults_to_shared(
    fake_sd: FakeSoundDevice, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(WASAPI_EXCLUSIVE_ENV_VAR, raising=False)
    monkeypatch.setenv(OUTPUT_BACKEND_ENV_VAR, "sounddevice")
    backend = create_output()
    assert isinstance(backend, SoundDeviceOutput)
    backend.open(SAMPLE_RATE, CHANNELS, silence)
    try:
        assert "extra_settings" not in fake_sd.streams[-1].config
        assert backend.name == "sounddevice"
    finally:
        backend.close()
