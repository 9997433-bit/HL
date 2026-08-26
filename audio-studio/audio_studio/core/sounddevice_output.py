"""PortAudio output through the ``sounddevice`` (CFFI) binding.

This is the same contract as :class:`~audio_studio.core.output.PyAudioOutput` —
callback pull mode, interleaved ``float32``, a configurable block size — over a
binding whose wheels carry their own PortAudio build (so no ``portaudio19-dev``
on the build host) and whose Windows wheels expose WASAPI. The binding also
hands the stream status flags to every callback, which is what lets this backend
report under/overruns instead of dropping them silently.

The module is imported lazily by :func:`audio_studio.core.output.create_output`;
importing it never imports ``sounddevice`` itself, so it stays safe to ship on a
machine that has no PortAudio at all.
"""

from __future__ import annotations

from contextlib import suppress
from typing import Any

import numpy as np

from .output import (
    AudioOutput,
    OutputDeviceError,
    _block_size_candidates,
    _quiet_native_stderr,
)

__all__ = ["SoundDeviceOutput"]


class SoundDeviceOutput(AudioOutput):
    """PortAudio backend driven in callback (pull) mode via ``sounddevice``."""

    name = "sounddevice"

    def __init__(self, device: int | str | None = None) -> None:
        super().__init__()
        self._device = device
        self._stream: Any | None = None
        self._underflows = 0
        self._overflows = 0

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

    def _open_stream(self) -> None:
        try:
            import sounddevice as sd
        except Exception as exc:  # noqa: BLE001
            raise OutputDeviceError(f"sounddevice is unavailable: {exc}") from exc

        self._underflows = 0
        self._overflows = 0
        requested = self._block_size
        last_error: Exception | None = None
        try:
            with _quiet_native_stderr():
                for block_size in _block_size_candidates(requested):
                    self._block_size = block_size
                    try:
                        self._stream = sd.OutputStream(
                            samplerate=self._sample_rate,
                            channels=self._channels,
                            dtype="float32",
                            blocksize=block_size,
                            device=self._device,
                            callback=self._sounddevice_callback,
                        )
                    except Exception as exc:  # noqa: BLE001 - try the next safe size
                        last_error = exc
                        self._teardown()
                        continue
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
