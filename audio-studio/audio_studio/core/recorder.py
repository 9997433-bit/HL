"""Input-device backends and recorded-audio accumulation.

Like :mod:`audio_studio.core.output`, this module keeps PortAudio behind a
small Qt-free interface. Hardware callbacks publish float32 blocks while the
base class owns lifecycle, thread-safe accumulation, and the optional WAV
flush performed when recording stops.
"""

from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod
from contextlib import suppress
from pathlib import Path

import numpy as np

from .loader import save_audio
from .output import DEFAULT_BLOCK_SIZE, _quiet_native_stderr
from .types import SAMPLE_DTYPE, AudioBuffer


class RecorderDeviceError(RuntimeError):
    """Raised when an input device cannot be opened or started."""


class AudioRecorder(ABC):
    """Common surface of hardware and synthetic recording backends.

    Captured blocks are copied out of the device callback and accumulated in
    memory. If ``target_path`` is supplied to :meth:`open`, :meth:`stop`
    flushes the complete recording to that path as a WAV (or another container
    selected by the suffix).
    """

    name: str = "abstract"

    def __init__(self) -> None:
        self._sample_rate = 0
        self._channels = 0
        self._block_size = DEFAULT_BLOCK_SIZE
        self._target_path: Path | None = None
        self._chunks: list[np.ndarray] = []
        self._frame_count = 0
        self._opened = False
        self._running = False
        self._state_lock = threading.RLock()
        self._transition_lock = threading.RLock()

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
    def target_path(self) -> Path | None:
        return self._target_path

    @property
    def is_open(self) -> bool:
        with self._state_lock:
            return self._opened

    @property
    def is_running(self) -> bool:
        with self._state_lock:
            return self._running

    @property
    def frame_count(self) -> int:
        """Number of frames captured since the stream was opened."""
        with self._state_lock:
            return self._frame_count

    @property
    def frames_recorded(self) -> int:
        """Alias useful next to ``NullOutput.frames_rendered``."""
        return self.frame_count

    @property
    def duration(self) -> float:
        return self.frame_count / self._sample_rate if self._sample_rate else 0.0

    @property
    def buffer(self) -> AudioBuffer:
        """A consistent snapshot of all audio captured so far."""
        with self._state_lock:
            if self._chunks:
                data = np.concatenate(self._chunks, axis=0)
            else:
                data = np.zeros((0, max(self._channels, 1)), dtype=SAMPLE_DTYPE)
            sample_rate = max(self._sample_rate, 1)
        return AudioBuffer(data, sample_rate)

    def open(
        self,
        sample_rate: int,
        channels: int,
        *,
        block_size: int = DEFAULT_BLOCK_SIZE,
        target_path: str | Path | None = None,
    ) -> None:
        """Configure a fresh recording and open its input stream."""
        if sample_rate <= 0 or channels <= 0 or block_size <= 0:
            raise RecorderDeviceError(
                f"invalid stream format {sample_rate} Hz / {channels} ch / {block_size} frames"
            )
        with self._transition_lock:
            self.close()
            with self._state_lock:
                self._sample_rate = int(sample_rate)
                self._channels = int(channels)
                self._block_size = int(block_size)
                self._target_path = Path(target_path) if target_path is not None else None
                self._chunks.clear()
                self._frame_count = 0
            try:
                self._open_stream()
            except Exception:
                self._close_stream()
                raise
            with self._state_lock:
                self._opened = True

    @abstractmethod
    def _open_stream(self) -> None: ...

    def start(self) -> None:
        """Start capturing; repeated calls while running are harmless."""
        with self._transition_lock:
            with self._state_lock:
                if not self._opened:
                    raise RecorderDeviceError("start() called before open()")
                if self._running:
                    return
                self._running = True
            try:
                self._start_stream()
            except Exception:
                with self._state_lock:
                    self._running = False
                raise

    @abstractmethod
    def _start_stream(self) -> None: ...

    def stop(self) -> AudioBuffer:
        """Stop capturing, flush the target file, and return the audio."""
        with self._transition_lock:
            with self._state_lock:
                was_running = self._running
                self._running = False
            if was_running:
                self._stop_stream()
            captured = self.buffer
            target = self._target_path
            if target is not None:
                save_audio(target, captured)
            return captured

    @abstractmethod
    def _stop_stream(self) -> None: ...

    def save(self, path: str | Path | None = None) -> Path:
        """Write the current snapshot without changing capture state."""
        target = Path(path) if path is not None else self._target_path
        if target is None:
            raise ValueError("no recording target path was provided")
        written = save_audio(target, self.buffer)
        with self._state_lock:
            self._target_path = written
        return written

    def close(self) -> None:
        """Stop and release the stream; safe to call more than once."""
        with self._transition_lock:
            with self._state_lock:
                opened = self._opened
            if not opened:
                return
            self.stop()
            self._close_stream()
            with self._state_lock:
                self._opened = False

    @abstractmethod
    def _close_stream(self) -> None: ...

    def _capture(self, block: np.ndarray) -> None:
        """Normalise and append one device block without exposing its storage."""
        data = np.asarray(block, dtype=SAMPLE_DTYPE)
        if data.ndim == 1:
            data = data[:, np.newaxis]
        if data.ndim != 2 or data.shape[1] != self._channels:
            raise RecorderDeviceError(
                f"input block has shape {data.shape}, expected (frames, {self._channels})"
            )
        copied = np.ascontiguousarray(data, dtype=SAMPLE_DTYPE).copy()
        with self._state_lock:
            if not self._running or copied.shape[0] == 0:
                return
            self._chunks.append(copied)
            self._frame_count += int(copied.shape[0])


class NullRecorder(AudioRecorder):
    """Synthetic input used when hardware is absent and by deterministic tests.

    The default source is digital silence. Set ``tone_frequency`` to generate a
    phase-continuous sine tone. ``realtime=False`` leaves capture under explicit
    :meth:`pump` control.
    """

    name = "null"

    def __init__(
        self,
        *,
        realtime: bool = True,
        tone_frequency: float | None = None,
        amplitude: float = 0.1,
    ) -> None:
        super().__init__()
        self._realtime = realtime
        self._tone_frequency = tone_frequency
        self._amplitude = float(amplitude)
        self._phase_frame = 0
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def _open_stream(self) -> None:
        self._phase_frame = 0
        self._stop_event.clear()

    def _start_stream(self) -> None:
        self._stop_event.clear()
        if self._realtime:
            self._thread = threading.Thread(
                target=self._run, name="NullRecorder", daemon=True
            )
            self._thread.start()

    def _stop_stream(self) -> None:
        self._stop_event.set()
        thread, self._thread = self._thread, None
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)

    def _close_stream(self) -> None:
        self._stop_event.set()

    def pump(self, n_frames: int | None = None) -> np.ndarray:
        """Synthesize one block and offer it to the recorder."""
        count = self._block_size if n_frames is None else int(n_frames)
        if count < 0:
            raise ValueError(f"n_frames must be non-negative, got {count}")
        if self._tone_frequency is None:
            block = np.zeros((count, self._channels), dtype=SAMPLE_DTYPE)
        else:
            frames = self._phase_frame + np.arange(count, dtype=np.float64)
            mono = self._amplitude * np.sin(
                2.0 * np.pi * self._tone_frequency * frames / self._sample_rate
            )
            block = np.repeat(mono[:, np.newaxis], self._channels, axis=1).astype(
                SAMPLE_DTYPE
            )
        self._phase_frame += count
        self._capture(block)
        return block

    def _run(self) -> None:
        period = self._block_size / self._sample_rate
        next_deadline = time.perf_counter()
        while not self._stop_event.is_set():
            self.pump()
            next_deadline += period
            delay = next_deadline - time.perf_counter()
            if delay > 0:
                self._stop_event.wait(delay)
            else:
                next_deadline = time.perf_counter()


class PyAudioRecorder(AudioRecorder):
    """PortAudio input backend driven in callback (push) mode."""

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

    def _open_stream(self) -> None:
        try:
            import pyaudio
        except Exception as exc:  # noqa: BLE001
            raise RecorderDeviceError(f"PyAudio is unavailable: {exc}") from exc

        try:
            with _quiet_native_stderr():
                instance = pyaudio.PyAudio()
                self._pyaudio = instance
                self._stream = instance.open(
                    format=pyaudio.paFloat32,
                    channels=self._channels,
                    rate=self._sample_rate,
                    input=True,
                    input_device_index=self._device_index,
                    frames_per_buffer=self._block_size,
                    stream_callback=self._pyaudio_callback,
                    start=False,
                )
        except Exception as exc:  # noqa: BLE001
            self._teardown()
            raise RecorderDeviceError(f"Cannot open input stream: {exc}") from exc

    def _pyaudio_callback(
        self, in_data: bytes | None, frame_count: int, _time_info: dict, _status: int
    ) -> tuple[None, int]:
        import pyaudio

        try:
            raw = np.frombuffer(in_data or b"", dtype="<f4")
            expected = frame_count * self._channels
            if raw.size < expected:
                padded = np.zeros(expected, dtype=SAMPLE_DTYPE)
                padded[: raw.size] = raw
                raw = padded
            self._capture(raw[:expected].reshape(frame_count, self._channels))
        except Exception:  # noqa: BLE001 - never let an exception cross the device boundary
            pass
        return None, pyaudio.paContinue

    def _start_stream(self) -> None:
        if self._stream is None:
            raise RecorderDeviceError("start() called before open()")
        try:
            self._stream.start_stream()  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            raise RecorderDeviceError(f"Cannot start input stream: {exc}") from exc

    def _stop_stream(self) -> None:
        stream = self._stream
        if stream is not None:
            with suppress(Exception):  # the device may already be gone
                stream.stop_stream()  # type: ignore[attr-defined]

    def _close_stream(self) -> None:
        self._teardown()

    def _teardown(self) -> None:
        stream, self._stream = self._stream, None
        instance, self._pyaudio = self._pyaudio, None
        for obj, method in ((stream, "close"), (instance, "terminate")):
            if obj is not None:
                with suppress(Exception):  # shutdown is best-effort
                    getattr(obj, method)()


def create_recorder(*, prefer_null: bool = False) -> AudioRecorder:
    """Return a hardware recorder when possible, otherwise a synthetic one."""
    if not prefer_null and PyAudioRecorder.is_available():
        probe = PyAudioRecorder()
        try:
            probe.open(48000, 1)
        except RecorderDeviceError:
            probe.close()
        else:
            probe.close()
            return PyAudioRecorder()
    return NullRecorder()
