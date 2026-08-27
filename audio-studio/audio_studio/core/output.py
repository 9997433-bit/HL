"""Output-device backends.

The engine only ever talks to :class:`AudioOutput`, so the same code drives a
real PortAudio stream on a workstation and a simulated clock on a headless CI
box. ``RenderCallback`` is pulled from a real-time thread: it must never
allocate unpredictably, block, or raise.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from typing import Any

import numpy as np

from .types import SAMPLE_DTYPE

#: ``callback(n_frames) -> (n_frames, channels) float32``.
RenderCallback = Callable[[int], np.ndarray]

#: About 5.3 ms of audio at 48 kHz.
DEFAULT_BLOCK_SIZE: int = 256

#: Hardware backends try the low-latency default first, then progressively
#: larger buffers when a device or host API rejects it.
_BLOCK_SIZE_FALLBACKS: tuple[int, ...] = (512, 1024)


def _block_size_candidates(requested: int) -> tuple[int, ...]:
    """Return the hardware negotiation ladder for a requested block size."""
    if requested != DEFAULT_BLOCK_SIZE:
        return (requested,)
    return (requested, *_BLOCK_SIZE_FALLBACKS)


class OutputDeviceError(RuntimeError):
    """Raised when a device cannot be opened or started."""


@contextmanager
def _quiet_native_stderr() -> Iterator[None]:
    """Silence file-descriptor 2 while ALSA/JACK probe every backend they know.

    PortAudio's enumeration writes directly to the C ``stderr``, so a Python
    ``redirect_stderr`` does not catch it. Any real failure still surfaces as an
    exception message, which is what callers report.
    """
    if os.name != "posix":
        yield
        return
    sys.stderr.flush()
    saved = os.dup(2)
    devnull = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull, 2)
        yield
    finally:
        os.dup2(saved, 2)
        os.close(devnull)
        os.close(saved)


class AudioOutput(ABC):
    """Common surface of every playback backend."""

    name: str = "abstract"

    def __init__(self) -> None:
        self._sample_rate: int = 0
        self._channels: int = 0
        self._block_size: int = DEFAULT_BLOCK_SIZE
        self._callback: RenderCallback | None = None
        self._running: bool = False

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def channels(self) -> int:
        return self._channels

    @property
    def block_size(self) -> int:
        return self._block_size

    @property
    def is_open(self) -> bool:
        return self._callback is not None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def latency(self) -> float:
        """Output latency in seconds (best-effort estimate)."""
        if not self._sample_rate:
            return 0.0
        return self._block_size / self._sample_rate

    def open(
        self,
        sample_rate: int,
        channels: int,
        callback: RenderCallback,
        *,
        block_size: int = DEFAULT_BLOCK_SIZE,
    ) -> None:
        if sample_rate <= 0 or channels <= 0:
            raise OutputDeviceError(f"invalid stream format {sample_rate} Hz / {channels} ch")
        self.close()
        self._sample_rate = int(sample_rate)
        self._channels = int(channels)
        self._block_size = int(block_size)
        self._callback = callback
        self._open_stream()

    @abstractmethod
    def _open_stream(self) -> None: ...

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    def close(self) -> None:
        if self.is_open:
            self.stop()
        self._callback = None

    def _render(self, n_frames: int) -> np.ndarray:
        """Invoke the engine callback, hardening the result for the device."""
        callback = self._callback
        if callback is None:
            return np.zeros((n_frames, max(self._channels, 1)), dtype=SAMPLE_DTYPE)
        try:
            block = np.asarray(callback(n_frames), dtype=SAMPLE_DTYPE)
        except Exception:  # noqa: BLE001 - never let an exception cross the device boundary
            return np.zeros((n_frames, self._channels), dtype=SAMPLE_DTYPE)
        if block.ndim == 1:
            block = block[:, np.newaxis]
        if block.shape[0] < n_frames:
            pad = np.zeros((n_frames - block.shape[0], block.shape[1]), dtype=SAMPLE_DTYPE)
            block = np.vstack((block, pad))
        return np.ascontiguousarray(block[:n_frames], dtype=SAMPLE_DTYPE)


class NullOutput(AudioOutput):
    """Backend with no hardware behind it.

    In ``realtime`` mode a worker thread pulls blocks on a wall-clock schedule,
    which lets the whole application run on a machine with no sound card. With
    ``realtime=False`` nothing is pulled automatically and tests drive the
    stream deterministically through :meth:`pump`.
    """

    name = "null"

    def __init__(self, *, realtime: bool = True) -> None:
        super().__init__()
        self._realtime = realtime
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._frames_rendered = 0

    @property
    def frames_rendered(self) -> int:
        """Total frames pulled since the stream was opened."""
        return self._frames_rendered

    def _open_stream(self) -> None:
        self._frames_rendered = 0
        self._stop_event.clear()

    def start(self) -> None:
        if not self.is_open:
            raise OutputDeviceError("start() called before open()")
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        if self._realtime:
            self._thread = threading.Thread(
                target=self._run, name="NullOutput", daemon=True
            )
            self._thread.start()

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        self._stop_event.set()
        thread, self._thread = self._thread, None
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)

    def pump(self, n_frames: int | None = None) -> np.ndarray:
        """Pull one block synchronously; only meaningful in non-realtime mode."""
        n = n_frames if n_frames is not None else self._block_size
        block = self._render(n)
        self._frames_rendered += n
        return block

    def _run(self) -> None:
        period = self._block_size / self._sample_rate
        next_deadline = time.perf_counter()
        while not self._stop_event.is_set():
            self._render(self._block_size)
            self._frames_rendered += self._block_size
            next_deadline += period
            delay = next_deadline - time.perf_counter()
            if delay > 0:
                self._stop_event.wait(delay)
            else:
                next_deadline = time.perf_counter()


class PyAudioOutput(AudioOutput):
    """PortAudio backend driven in callback (pull) mode."""

    name = "pyaudio"

    def __init__(self, device_index: int | None = None) -> None:
        super().__init__()
        self._device_index = device_index
        self._pyaudio: object | None = None
        self._stream: object | None = None

    @staticmethod
    def is_available() -> bool:
        try:
            import pyaudio  # noqa: F401
        except Exception:  # noqa: BLE001 - missing PortAudio shared library included
            return False
        return True

    @property
    def latency(self) -> float:
        stream = self._stream
        if stream is not None:
            try:
                return float(stream.get_output_latency())  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001 - fall through to the nominal estimate
                pass
        return super().latency

    def _open_stream(self) -> None:
        try:
            import pyaudio
        except Exception as exc:  # noqa: BLE001
            raise OutputDeviceError(f"PyAudio is unavailable: {exc}") from exc

        requested = self._block_size
        last_error: Exception | None = None
        try:
            with _quiet_native_stderr():
                instance = pyaudio.PyAudio()
                self._pyaudio = instance
                for block_size in _block_size_candidates(requested):
                    self._block_size = block_size
                    try:
                        self._stream = instance.open(
                            format=pyaudio.paFloat32,
                            channels=self._channels,
                            rate=self._sample_rate,
                            output=True,
                            output_device_index=self._device_index,
                            frames_per_buffer=block_size,
                            stream_callback=self._pyaudio_callback,
                            start=False,
                        )
                    except Exception as exc:  # noqa: BLE001 - try the next safe size
                        last_error = exc
                        continue
                    return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        self._block_size = requested
        self._teardown()
        assert last_error is not None
        raise OutputDeviceError(f"Cannot open output stream: {last_error}") from last_error

    def _pyaudio_callback(
        self, _in_data: bytes | None, frame_count: int, _time_info: dict, _status: int
    ) -> tuple[bytes, int]:
        import pyaudio

        block = self._render(frame_count)
        return block.tobytes(), pyaudio.paContinue

    def start(self) -> None:
        if self._stream is None:
            raise OutputDeviceError("start() called before open()")
        try:
            self._stream.start_stream()  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            raise OutputDeviceError(f"Cannot start output stream: {exc}") from exc
        self._running = True

    def stop(self) -> None:
        self._running = False
        stream = self._stream
        if stream is not None:
            with suppress(Exception):  # the device may already be gone
                stream.stop_stream()  # type: ignore[attr-defined]

    def close(self) -> None:
        super().close()
        self._teardown()

    def _teardown(self) -> None:
        stream, self._stream = self._stream, None
        instance, self._pyaudio = self._pyaudio, None
        for obj, method in ((stream, "close"), (instance, "terminate")):
            if obj is not None:
                with suppress(Exception):  # shutdown is best-effort
                    getattr(obj, method)()


#: Overrides the backend search order. ``pyaudio`` pins the legacy binding,
#: ``sounddevice`` pins the new one, ``null`` skips hardware entirely.
OUTPUT_BACKEND_ENV_VAR = "AUDIO_STUDIO_OUTPUT"

#: Safety switch for WASAPI exclusive-mode output. Only the value ``1`` on a
#: Windows host makes :func:`create_output` request exclusive mode from the
#: sounddevice backend; every other value or platform keeps shared mode.
WASAPI_EXCLUSIVE_ENV_VAR = "AUDIO_STUDIO_WASAPI_EXCLUSIVE"


def _wasapi_exclusive_requested() -> bool:
    """True when the WASAPI exclusive switch is set on a Windows host."""
    if sys.platform != "win32":
        return False
    return os.environ.get(WASAPI_EXCLUSIVE_ENV_VAR, "").strip() == "1"

_BACKEND_ALIASES: dict[str, tuple[str, ...]] = {
    "pyaudio": ("pyaudio",),
    "portaudio": ("pyaudio",),
    "sounddevice": ("sounddevice",),
    "sd": ("sounddevice",),
    "null": (),
    "none": (),
    "": ("sounddevice", "pyaudio"),
}

#: Default preference: ``sounddevice`` first (bundled PortAudio, WASAPI on
#: Windows, xrun reporting), then the legacy PyAudio binding.
_DEFAULT_BACKEND_ORDER: tuple[str, ...] = ("sounddevice", "pyaudio")


def _backend_class(name: str) -> type[AudioOutput] | None:
    if name == "pyaudio":
        return PyAudioOutput
    if name == "sounddevice":
        try:
            from .sounddevice_output import SoundDeviceOutput
        except Exception:  # noqa: BLE001 - treat an unimportable backend as absent
            return None
        return SoundDeviceOutput
    return None


def _backend_order() -> tuple[str, ...]:
    requested = os.environ.get(OUTPUT_BACKEND_ENV_VAR, "").strip().lower()
    return _BACKEND_ALIASES.get(requested, _DEFAULT_BACKEND_ORDER)


def _open_probe(cls: type[AudioOutput], **kwargs: Any) -> AudioOutput | None:
    """Return a fresh backend instance when a throwaway stream really opens."""
    if not getattr(cls, "is_available", lambda: False)():
        return None
    probe = cls(**kwargs)
    try:
        probe.open(48000, 2, lambda n: np.zeros((n, 2), dtype=SAMPLE_DTYPE))
    except OutputDeviceError:
        return None
    finally:
        probe.close()
    return cls(**kwargs)


def create_output(*, prefer_null: bool = False) -> AudioOutput:
    """Return the best backend available on this machine.

    The search order is ``sounddevice`` then ``pyaudio``, and
    ``AUDIO_STUDIO_OUTPUT`` pins one of them (``pyaudio``, ``sounddevice`` or
    ``null``). On Windows, ``AUDIO_STUDIO_WASAPI_EXCLUSIVE=1`` additionally asks
    the sounddevice backend for WASAPI exclusive mode. Falls back to
    :class:`NullOutput` so the application always starts, even on a container
    with no ALSA device.
    """
    if prefer_null:
        return NullOutput()
    for name in _backend_order():
        cls = _backend_class(name)
        if cls is None:
            continue
        kwargs: dict[str, Any] = {}
        if name == "sounddevice" and _wasapi_exclusive_requested():
            kwargs["exclusive"] = True
        backend = _open_probe(cls, **kwargs)
        if backend is not None:
            return backend
    return NullOutput()
