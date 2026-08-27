"""PortAudio output through the ``sounddevice`` (CFFI) binding.

This is the same contract as :class:`~audio_studio.core.output.PyAudioOutput` —
callback pull mode, interleaved ``float32``, a configurable block size — over a
binding whose wheels carry their own PortAudio build (so no ``portaudio19-dev``
on the build host) and whose Windows wheels expose WASAPI. The binding also
hands the stream status flags to every callback, which is what lets this backend
report under/overruns instead of dropping them silently.

On Windows the backend can additionally request **WASAPI exclusive mode**, which
bypasses the shared-mode system mixer for a shorter output path. Exclusive mode
is opt-in twice over: the constructor must ask for it *and* the
``AUDIO_STUDIO_WASAPI_EXCLUSIVE=1`` safety switch must be set, because an
exclusive stream takes over the device and can be refused outright. When the
device rejects the exclusive stream the backend falls back to an ordinary
shared-mode stream instead of failing playback.

``AUDIO_STUDIO_ASIO=1`` makes an output device already exposed by PortAudio's
ASIO host API the first choice on Windows. Audio Studio does not bundle or use
the official ASIO SDK; this is only host selection over the PortAudio library
loaded by ``sounddevice``. If that library exposes no ASIO output, or the
preferred stream cannot open, the ordinary default-device ladder is unchanged.

The module is imported lazily by :func:`audio_studio.core.output.create_output`;
importing it never imports ``sounddevice`` itself, so it stays safe to ship on a
machine that has no PortAudio at all.
"""

from __future__ import annotations

import os
import sys
from contextlib import suppress
from typing import Any

import numpy as np

from .output import (
    WASAPI_EXCLUSIVE_ENV_VAR,
    AudioOutput,
    OutputDeviceError,
    _block_size_candidates,
    _quiet_native_stderr,
)

__all__ = ["ASIO_ENV_VAR", "SoundDeviceOutput"]

#: Windows-only opt-in for preferring an ASIO output already exposed by the
#: PortAudio library loaded by sounddevice. This does not enable or bundle an
#: ASIO SDK or set sounddevice's own ``SD_ENABLE_ASIO`` loader switch.
ASIO_ENV_VAR = "AUDIO_STUDIO_ASIO"


def _device_uses_host_api(sd: Any, device: int | str | None, name: str) -> bool:
    """Best-effort check that ``device`` is served by the named host API."""
    try:
        info = sd.query_devices(device, kind="output")
        host_api = sd.query_hostapis(int(info["hostapi"]))
        return name.lower() in str(host_api["name"]).lower()
    except Exception:  # noqa: BLE001 - an unknown host API stays in shared mode
        return False


def _device_uses_wasapi(sd: Any, device: int | str | None) -> bool:
    return _device_uses_host_api(sd, device, "wasapi")


def _asio_output_device(sd: Any) -> int | None:
    """Return the first usable output on a PortAudio ASIO host API.

    PortAudio host dictionaries normally name a ``default_output_device``.
    Some binding/build combinations omit that key, so enumeration is retained
    as a fallback. Every failure is treated as "ASIO unavailable" and leaves
    the normal default-device path intact.
    """
    try:
        host_apis = tuple(sd.query_hostapis())
        devices = tuple(sd.query_devices())
    except Exception:  # noqa: BLE001 - device enumeration is best-effort
        return None

    asio_hosts = {
        index
        for index, host_api in enumerate(host_apis)
        if "asio" in str(host_api.get("name", "")).lower()
    }
    if not asio_hosts:
        return None

    candidates: list[int] = []
    for index in asio_hosts:
        default = host_apis[index].get("default_output_device", -1)
        try:
            default_index = int(default)
        except (TypeError, ValueError):
            continue
        if default_index >= 0:
            candidates.append(default_index)
    candidates.extend(index for index in range(len(devices)) if index not in candidates)

    for index in candidates:
        if index < 0 or index >= len(devices):
            continue
        info = devices[index]
        try:
            host_index = int(info.get("hostapi", -1))
            output_channels = int(info.get("max_output_channels", 0))
        except (TypeError, ValueError):
            continue
        if host_index in asio_hosts and output_channels > 0:
            return index
    return None


class SoundDeviceOutput(AudioOutput):
    """PortAudio backend driven in callback (pull) mode via ``sounddevice``."""

    def __init__(self, device: int | str | None = None, *, exclusive: bool = False) -> None:
        super().__init__()
        self._device = device
        self._exclusive = exclusive
        self._exclusive_active = False
        self._asio_active = False
        self._stream: Any | None = None
        self._underflows = 0
        self._overflows = 0

    @property
    def name(self) -> str:  # type: ignore[override]
        """Backend label; carries the selected low-latency host mode."""
        if self._asio_active:
            return "sounddevice (ASIO)"
        if self._exclusive_active:
            return "sounddevice (WASAPI exclusive)"
        return "sounddevice"

    @staticmethod
    def is_available() -> bool:
        """True when ``sounddevice`` imports, including its PortAudio library."""
        try:
            import sounddevice  # noqa: F401
        except Exception:  # noqa: BLE001 - a missing PortAudio shared library raises OSError
            return False
        return True

    @property
    def underflows(self) -> int:
        """Callbacks that arrived after the device had already run dry."""
        return self._underflows

    @property
    def overflows(self) -> int:
        """Callbacks the device reported as output overflow."""
        return self._overflows

    @property
    def xruns(self) -> int:
        """Total under/overruns since the stream was opened."""
        return self._underflows + self._overflows

    @property
    def latency(self) -> float:
        stream = self._stream
        if stream is not None:
            with suppress(Exception):  # a closed device has no latency to report
                reported = stream.latency
                if isinstance(reported, (tuple, list)):
                    reported = reported[-1]
                latency = float(reported)
                if latency > 0.0:
                    return latency
        return super().latency

    def _device_candidates(self, sd: Any) -> tuple[int | str | None, ...]:
        """Preferred ASIO output followed by the configured/default device."""
        if self._device is not None:
            return (self._device,)
        if sys.platform != "win32" or os.environ.get(ASIO_ENV_VAR, "").strip() != "1":
            return (None,)
        asio_device = _asio_output_device(sd)
        return (asio_device, None) if asio_device is not None else (None,)

    def _wasapi_exclusive_enabled(self, sd: Any, device: int | str | None) -> bool:
        """True when every gate for WASAPI exclusive mode is open.

        The mode engages only when it was requested at construction time, the
        process runs on Windows, the ``AUDIO_STUDIO_WASAPI_EXCLUSIVE=1`` safety
        switch is set, and the target output device is driven by WASAPI.
        """
        if not (self._exclusive and sys.platform == "win32"):
            return False
        if os.environ.get(WASAPI_EXCLUSIVE_ENV_VAR, "").strip() != "1":
            return False
        return _device_uses_wasapi(sd, device)

    def _extra_settings_candidates(
        self, sd: Any, device: int | str | None
    ) -> tuple[Any, ...]:
        """Host-API ladder: WASAPI exclusive first when engaged, then shared."""
        if not self._wasapi_exclusive_enabled(sd, device):
            return (None,)
        try:
            settings = sd.WasapiSettings(exclusive=True)
        except Exception:  # noqa: BLE001 - a binding without WASAPI support
            return (None,)
        return (settings, None)

    def _open_stream(self) -> None:
        try:
            import sounddevice as sd
        except Exception as exc:  # noqa: BLE001
            raise OutputDeviceError(f"sounddevice is unavailable: {exc}") from exc

        self._underflows = 0
        self._overflows = 0
        self._exclusive_active = False
        self._asio_active = False
        requested = self._block_size
        last_error: Exception | None = None
        try:
            with _quiet_native_stderr():
                for device in self._device_candidates(sd):
                    for extra_settings in self._extra_settings_candidates(sd, device):
                        stream_kwargs: dict[str, Any] = {}
                        if extra_settings is not None:
                            stream_kwargs["extra_settings"] = extra_settings
                        for block_size in _block_size_candidates(requested):
                            self._block_size = block_size
                            try:
                                self._stream = sd.OutputStream(
                                    samplerate=self._sample_rate,
                                    channels=self._channels,
                                    dtype="float32",
                                    blocksize=block_size,
                                    device=device,
                                    callback=self._sounddevice_callback,
                                    **stream_kwargs,
                                )
                            except Exception as exc:  # noqa: BLE001 - try next candidate
                                last_error = exc
                                self._teardown()
                                continue
                            self._exclusive_active = extra_settings is not None
                            self._asio_active = (
                                self._device is None
                                and device is not None
                                and _device_uses_host_api(sd, device, "asio")
                            )
                            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        self._block_size = requested
        assert last_error is not None
        raise OutputDeviceError(f"Cannot open output stream: {last_error}") from last_error

    def _sounddevice_callback(
        self, outdata: np.ndarray, frames: int, _time_info: Any, status: Any
    ) -> None:
        """Real-time callback: fill ``outdata`` in place, never raise."""
        if status:
            # ``priming_output`` is PortAudio pre-rolling the device, not a glitch.
            if getattr(status, "output_underflow", False):
                self._underflows += 1
            if getattr(status, "output_overflow", False):
                self._overflows += 1
        block = self._render(frames)
        wanted = outdata.shape[1] if outdata.ndim > 1 else 1
        if block.shape[1] == wanted:
            outdata[:] = block
        else:  # a mis-shaped render is silenced rather than aborting the stream
            outdata[:] = 0.0
            common = min(block.shape[1], wanted)
            outdata[:, :common] = block[:, :common]

    def start(self) -> None:
        stream = self._stream
        if stream is None:
            raise OutputDeviceError("start() called before open()")
        try:
            with _quiet_native_stderr():
                stream.start()
        except Exception as exc:  # noqa: BLE001
            raise OutputDeviceError(f"Cannot start output stream: {exc}") from exc
        self._running = True

    def stop(self) -> None:
        self._running = False
        stream = self._stream
        if stream is not None:
            with suppress(Exception):  # the device may already be gone
                stream.stop()

    def close(self) -> None:
        super().close()
        self._teardown()

    def _teardown(self) -> None:
        stream, self._stream = self._stream, None
        if stream is not None:
            with suppress(Exception):  # shutdown is best-effort
                stream.close()
