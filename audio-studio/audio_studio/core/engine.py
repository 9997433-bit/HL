"""Transport and playback engine.

Three threads meet here:

* the **control thread** (the Qt GUI thread) calls :meth:`AudioEngine.play`,
  :meth:`~AudioEngine.seek` and friends;
* the **feeder thread** copies frames from the loaded clip into a
  :class:`~audio_studio.core.ring_buffer.RingBuffer`;
* the **device thread** drains that ring buffer from :meth:`AudioEngine.render`.

The ring buffer is what keeps the device callback free of file I/O and of the
GIL-heavy work that would otherwise cause dropouts. The playhead is derived as
``frames_queued - frames_still_in_ring`` so it reports what the listener is
actually hearing rather than how far the feeder has run ahead.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path

import numpy as np

from .loader import LoadedAudio, load_audio, resample
from .output import DEFAULT_BLOCK_SIZE, AudioOutput, OutputDeviceError, create_output
from .peaks import PeakPyramid
from .ring_buffer import RingBuffer
from .types import (
    SAMPLE_DTYPE,
    AudioBuffer,
    AudioFormat,
    LevelReading,
    TimeRange,
    TransportState,
)

#: Ring buffer depth as a multiple of the device block size.
RING_BLOCKS: int = 16

#: Sample rate used when the device rejects the clip's native rate.
FALLBACK_SAMPLE_RATE: int = 48000

StateListener = Callable[[TransportState], None]


class AudioEngine:
    """Loads a clip and plays it through an :class:`AudioOutput` backend."""

    def __init__(
        self,
        output: AudioOutput | None = None,
        *,
        block_size: int = DEFAULT_BLOCK_SIZE,
        ring_blocks: int = RING_BLOCKS,
    ) -> None:
        self._output = output if output is not None else create_output()
        self._block_size = int(block_size)
        self._ring_blocks = max(int(ring_blocks), 4)

        self._lock = threading.RLock()
        self._clip: LoadedAudio | None = None
        self._pyramid: PeakPyramid | None = None
        self._ring: RingBuffer | None = None

        self._state = TransportState.STOPPED
        self._source_pos = 0
        self._play_origin = 0
        self._exhausted = False
        self._selection: TimeRange | None = None
        self._loop = False
        self._play_selection_only = True

        self._volume = 1.0
        self._muted = False
        self._levels = LevelReading()

        self._feeder: threading.Thread | None = None
        self._feeder_stop = threading.Event()
        self._state_listeners: list[StateListener] = []
        self._finished_listeners: list[Callable[[], None]] = []

    # ------------------------------------------------------------------ clip

    @property
    def clip(self) -> LoadedAudio | None:
        return self._clip

    @property
    def buffer(self) -> AudioBuffer | None:
        return self._clip.buffer if self._clip else None

    @property
    def pyramid(self) -> PeakPyramid | None:
        """Waveform envelope cache for the loaded clip."""
        return self._pyramid

    @property
    def audio_format(self) -> AudioFormat | None:
        return self._clip.audio_format if self._clip else None

    @property
    def has_clip(self) -> bool:
        return self._clip is not None

    @property
    def n_frames(self) -> int:
        return self._clip.buffer.n_frames if self._clip else 0

    @property
    def n_channels(self) -> int:
        return self._clip.buffer.n_channels if self._clip else 0

    @property
    def sample_rate(self) -> int:
        return self._clip.buffer.sample_rate if self._clip else 0

    @property
    def duration(self) -> float:
        return self._clip.buffer.duration if self._clip else 0.0

    def load(self, path: str | Path) -> LoadedAudio:
        """Decode ``path`` and arm the transport at its start."""
        clip = load_audio(path)
        self.set_clip(clip)
        return clip

    def set_clip(self, clip: LoadedAudio | None) -> None:
        """Install an already-decoded clip (used by tests and by DSP results)."""
        self.stop()
        with self._lock:
            self._clip = clip
            self._pyramid = PeakPyramid(clip.buffer.data) if clip is not None else None
            self._selection = None
            self._source_pos = 0
            self._play_origin = 0
            self._exhausted = False
            self._levels = LevelReading()
            self._ring = None
        self._close_output()

    def close_clip(self) -> None:
        self.set_clip(None)

    # ------------------------------------------------------------- transport

    @property
    def state(self) -> TransportState:
        with self._lock:
            return self._state

    @property
    def is_playing(self) -> bool:
        return self.state is TransportState.PLAYING

    @property
    def output(self) -> AudioOutput:
        return self._output

    def play(self) -> None:
        """Start or resume playback from the current playhead."""
        with self._lock:
            if self._clip is None or self._state is TransportState.PLAYING:
                return

            region = self.playback_region
            if self._state is TransportState.PAUSED and self._ring is not None:
                self._set_state(TransportState.PLAYING)
                self._start_output()
                return

            if not region.length:
                return
            if not (region.start <= self._source_pos < region.end):
                self._source_pos = region.start

            self._play_origin = self._source_pos
            self._exhausted = False
            self._prepare_stream()
            self._set_state(TransportState.PLAYING)
            self._start_feeder()
            self._start_output()

    def pause(self) -> None:
        """Halt the device but keep the ring buffer primed for instant resume."""
        with self._lock:
            if self._state is not TransportState.PLAYING:
                return
            self._set_state(TransportState.PAUSED)
        self._output.stop()

    def toggle_play_pause(self) -> None:
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def stop(self) -> None:
        """Stop playback and rewind to where the current pass started."""
        self._teardown(join_feeder=True)
        with self._lock:
            if self._clip is not None:
                self._source_pos = self._play_origin
            self._levels = LevelReading()

    def seek(self, frame: int) -> int:
        """Move the playhead to ``frame``; returns the clamped position."""
        with self._lock:
            if self._clip is None:
                return 0
            target = max(0, min(int(frame), self.n_frames))
            self._source_pos = target
            self._play_origin = target
            self._exhausted = False
            if self._ring is not None:
                self._ring.clear()
            return target

    def seek_seconds(self, seconds: float) -> int:
        return self.seek(int(round(seconds * max(self.sample_rate, 1))))

    @property
    def position(self) -> int:
        """Playhead in frames, compensated for what is still queued in the ring."""
        with self._lock:
            if self._clip is None:
                return 0
            queued = self._ring.available_read if self._ring is not None else 0
            return int(max(0, min(self._source_pos - queued, self.n_frames)))

    @property
    def position_seconds(self) -> float:
        rate = self.sample_rate
        return self.position / rate if rate else 0.0

    # ------------------------------------------------------------- selection

    @property
    def selection(self) -> TimeRange | None:
        with self._lock:
            return self._selection

    def set_selection(self, selection: TimeRange | None) -> None:
        with self._lock:
            if selection is None or selection.is_empty:
                self._selection = None
            else:
                self._selection = selection.clamped(self.n_frames)

    @property
    def playback_region(self) -> TimeRange:
        """Frames the transport will run over: the selection, else the whole clip."""
        with self._lock:
            if self._play_selection_only and self._selection is not None:
                return self._selection
            return TimeRange(0, self.n_frames)

    @property
    def play_selection_only(self) -> bool:
        return self._play_selection_only

    @play_selection_only.setter
    def play_selection_only(self, value: bool) -> None:
        with self._lock:
            self._play_selection_only = bool(value)

    @property
    def loop(self) -> bool:
        return self._loop

    @loop.setter
    def loop(self, value: bool) -> None:
        with self._lock:
            self._loop = bool(value)
            if self._loop:
                self._exhausted = False

    # ----------------------------------------------------------------- mixer

    @property
    def volume(self) -> float:
        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        self._volume = float(max(0.0, min(value, 4.0)))

    @property
    def muted(self) -> bool:
        return self._muted

    @muted.setter
    def muted(self, value: bool) -> None:
        self._muted = bool(value)

    @property
    def levels(self) -> LevelReading:
        """Most recent per-channel peak/RMS reading from the device thread."""
        return self._levels

    # ------------------------------------------------------------- listeners

    def add_state_listener(self, listener: StateListener) -> None:
        self._state_listeners.append(listener)

    def add_finished_listener(self, listener: Callable[[], None]) -> None:
        self._finished_listeners.append(listener)

    def _set_state(self, state: TransportState) -> None:
        if state is self._state:
            return
        self._state = state
        for listener in tuple(self._state_listeners):
            # A misbehaving listener must never take the transport down with it.
            with suppress(Exception):
                listener(state)

    # ------------------------------------------------------------ device I/O

    def render(self, n_frames: int) -> np.ndarray:
        """Device callback: drain the ring buffer, apply gain, publish levels."""
        ring = self._ring
        channels = ring.channels if ring is not None else max(self.n_channels, 1)
        if ring is None or self._state is not TransportState.PLAYING:
            return np.zeros((n_frames, channels), dtype=SAMPLE_DTYPE)

        block = ring.read(n_frames, pad=True)
        gain = 0.0 if self._muted else self._volume
        if gain != 1.0:
            block = block * SAMPLE_DTYPE(gain)
        self._update_levels(block)
        return block

    def _update_levels(self, block: np.ndarray) -> None:
        if block.size == 0:
            return
        peak = np.max(np.abs(block), axis=0)
        rms = np.sqrt(np.mean(np.square(block, dtype=np.float64), axis=0))
        self._levels = LevelReading(
            peak=tuple(float(v) for v in peak), rms=tuple(float(v) for v in rms)
        )

    def _prepare_stream(self) -> None:
        """Open the device for the clip's format, resampling only if forced."""
        assert self._clip is not None
        buffer = self._clip.buffer
        if (
            self._output.is_open
            and self._output.sample_rate == buffer.sample_rate
            and self._output.channels == buffer.n_channels
        ):
            self._reset_ring(buffer.n_channels)
            return

        try:
            self._output.open(
                buffer.sample_rate,
                buffer.n_channels,
                self.render,
                block_size=self._block_size,
            )
        except OutputDeviceError:
            converted = resample(buffer, FALLBACK_SAMPLE_RATE)
            ratio = FALLBACK_SAMPLE_RATE / buffer.sample_rate
            self._clip = LoadedAudio(
                buffer=converted,
                audio_format=self._clip.audio_format,
                path=self._clip.path,
            )
            self._pyramid = PeakPyramid(converted.data)
            self._source_pos = int(self._source_pos * ratio)
            self._play_origin = int(self._play_origin * ratio)
            self._output.open(
                converted.sample_rate,
                converted.n_channels,
                self.render,
                block_size=self._block_size,
            )
            buffer = converted
        self._reset_ring(buffer.n_channels)

    def _reset_ring(self, channels: int) -> None:
        capacity = max(self._block_size * self._ring_blocks, self._block_size * 4)
        self._ring = RingBuffer(capacity, channels)

    def _start_output(self) -> None:
        try:
            self._output.start()
        except OutputDeviceError:
            self._set_state(TransportState.STOPPED)
            raise

    def _close_output(self) -> None:
        with suppress(Exception):  # shutdown is best-effort
            self._output.close()

    # ---------------------------------------------------------------- feeder

    def _start_feeder(self) -> None:
        self._feeder_stop.clear()
        self._prime_ring()
        thread = threading.Thread(target=self._feeder_loop, name="AudioFeeder", daemon=True)
        self._feeder = thread
        thread.start()

    def _prime_ring(self) -> None:
        """Fill the ring before the device starts so the first block is never silent."""
        for _ in range(self._ring_blocks):
            if not self._pump_once():
                break

    def _feeder_loop(self) -> None:
        idle = max(self._block_size / max(self.sample_rate, 1) / 4.0, 0.001)
        while not self._feeder_stop.is_set():
            produced = self._pump_once()
            with self._lock:
                ring_empty = self._ring is None or self._ring.available_read == 0
                finished = self._exhausted and ring_empty
            if finished:
                self._handle_stream_end()
                return
            if not produced:
                self._feeder_stop.wait(idle)

    def _pump_once(self) -> bool:
        """Copy at most one block from the clip into the ring buffer."""
        with self._lock:
            ring = self._ring
            if ring is None or self._clip is None or self._exhausted:
                return False
            if ring.available_write < self._block_size:
                return False

            region = self.playback_region
            if self._source_pos >= region.end:
                if self._loop and region.length:
                    self._source_pos = region.start
                else:
                    self._exhausted = True
                    return False

            n = min(self._block_size, region.end - self._source_pos)
            chunk = self._clip.buffer.data[self._source_pos : self._source_pos + n]
            written = ring.write(chunk)
            self._source_pos += written
            return written > 0

    def _handle_stream_end(self) -> None:
        """Called from the feeder thread once the region has fully played out."""
        # Let the device drain whatever it has already accepted.
        time.sleep(self._output.latency)
        self._teardown(join_feeder=False)
        with self._lock:
            region = self.playback_region
            self._source_pos = region.end
            self._play_origin = region.start
            self._levels = LevelReading()
        for listener in tuple(self._finished_listeners):
            with suppress(Exception):
                listener()

    def _teardown(self, *, join_feeder: bool) -> None:
        self._feeder_stop.set()
        thread, self._feeder = self._feeder, None
        if join_feeder and thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        with suppress(Exception):
            self._output.stop()
        with self._lock:
            if self._ring is not None:
                self._ring.clear()
            self._exhausted = False
            self._set_state(TransportState.STOPPED)

    def shutdown(self) -> None:
        """Release the device; safe to call more than once."""
        self._teardown(join_feeder=True)
        self._close_output()
