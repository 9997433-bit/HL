"""Transport and playback engine.

Three threads meet here:

* the **control thread** (the Qt GUI thread) calls :meth:`AudioEngine.play`,
  :meth:`~AudioEngine.seek` and friends;
* the **feeder thread** pulls frames from the active
  :class:`~audio_studio.core.sample_source.SampleSource` into a
  :class:`~audio_studio.core.ring_buffer.RingBuffer`;
* the **device thread** drains that ring buffer from :meth:`AudioEngine.render`.

The ring buffer is what keeps the device callback free of file I/O and of the
GIL-heavy work that would otherwise cause dropouts. Because the feeder talks to
a ``SampleSource`` rather than to a decoded array, the same transport plays an
in-memory clip, a file being streamed off disk, and an
:class:`~audio_studio.core.edit_session.EditSession` document mid-edit.

The playhead is derived as ``frames_queued - frames_still_in_ring`` so it
reports what the listener is actually hearing rather than how far the feeder
has run ahead.
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
from .peaks_cache import cached_pyramid
from .ring_buffer import RingBuffer
from .sample_source import MemorySampleSource, SampleSource, StreamingSampleSource
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
        self._source: SampleSource | None = None
        self._owns_source = False
        self._audio_format: AudioFormat | None = None
        self._pyramid: PeakPyramid | None = None
        self._ring: RingBuffer | None = None
        self._scratch = np.empty((self._block_size, 1), dtype=SAMPLE_DTYPE)

        self._state = TransportState.STOPPED
        self._source_pos = 0
        self._play_origin = 0
        self._exhausted = False
        # Bumped whenever the playhead jumps, so a block decoded outside the
        # lock can tell that it is describing a position nobody wants any more.
        self._generation = 0
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
        """The decoded clip, or ``None`` when playing a streamed or edited source."""
        return self._clip

    @property
    def source(self) -> SampleSource | None:
        """Whatever the feeder is currently pulling frames from."""
        return self._source

    @property
    def buffer(self) -> AudioBuffer | None:
        return self._clip.buffer if self._clip else None

    @property
    def pyramid(self) -> PeakPyramid | None:
        """Waveform envelope cache for the loaded clip."""
        return self._pyramid

    @property
    def audio_format(self) -> AudioFormat | None:
        return self._audio_format

    @property
    def has_clip(self) -> bool:
        return self._source is not None

    @property
    def is_streaming(self) -> bool:
        """True when frames are being decoded from disk rather than held in RAM."""
        return isinstance(self._source, StreamingSampleSource)

    @property
    def n_frames(self) -> int:
        return self._source.n_frames if self._source else 0

    @property
    def n_channels(self) -> int:
        return self._source.n_channels if self._source else 0

    @property
    def sample_rate(self) -> int:
        return self._source.sample_rate if self._source else 0

    @property
    def duration(self) -> float:
        rate = self.sample_rate
        return self.n_frames / rate if rate else 0.0

    def load(self, path: str | Path, *, peak_cache: bool | None = None) -> LoadedAudio:
        """Decode ``path`` into memory and arm the transport at its start.

        The waveform overview comes from the file's ``.pk`` sidecar when one is
        current; ``peak_cache`` overrides the ``AUDIO_STUDIO_PEAK_CACHE``
        environment switch for this call.
        """
        clip = load_audio(path)
        self.set_clip(
            clip,
            pyramid=cached_pyramid(clip.path, clip.buffer.data, enabled=peak_cache),
        )
        return clip

    def open_stream(
        self,
        path: str | Path,
        *,
        build_pyramid: bool = False,
        peak_cache: bool | None = None,
    ) -> StreamingSampleSource:
        """Play ``path`` straight off disk instead of decoding it up front.

        Nothing but the file header is read, so an hour-long session opens
        instantly. ``build_pyramid`` produces the waveform overview, which is
        what a UI wants but a batch job does not; a current ``.pk`` sidecar
        supplies it without the extra pass over the file.
        """
        source = StreamingSampleSource(path)
        pyramid = None
        if build_pyramid:
            pyramid = cached_pyramid(
                source.path,
                lambda: source.read(0, source.n_frames),
                enabled=peak_cache,
            )
        self.set_source(
            source,
            audio_format=source.audio_format(),
            pyramid=pyramid,
            owns_source=True,
        )
        return source

    def set_clip(self, clip: LoadedAudio | None, *, pyramid: PeakPyramid | None = None) -> None:
        """Install an already-decoded clip (used by tests and by DSP results).

        ``pyramid`` is built from the clip when it is not supplied. Callers that
        know the clip still matches its file on disk pass a cached one instead.
        """
        if clip is None:
            self.set_source(None)
            return
        self.set_source(
            MemorySampleSource(clip.buffer),
            clip=clip,
            audio_format=clip.audio_format,
            pyramid=pyramid if pyramid is not None else PeakPyramid(clip.buffer.data),
        )

    def set_source(
        self,
        source: SampleSource | None,
        *,
        clip: LoadedAudio | None = None,
        audio_format: AudioFormat | None = None,
        pyramid: PeakPyramid | None = None,
        owns_source: bool = False,
    ) -> None:
        """Point the transport at any :class:`SampleSource` and rewind it.

        ``owns_source`` makes the engine responsible for closing the source when
        it is replaced or the engine shuts down — the right default for a file
        handle it opened itself, and the wrong one for a session the UI shares.
        """
        self.stop()
        with self._lock:
            previous, owned = self._source, self._owns_source
            self._source = source
            self._owns_source = owns_source
            self._clip = clip
            self._audio_format = audio_format
            self._pyramid = pyramid
            self._selection = None
            self._source_pos = 0
            self._play_origin = 0
            self._exhausted = False
            self._generation += 1
            self._levels = LevelReading()
            self._ring = None
        if owned and previous is not None and previous is not source:
            with suppress(Exception):  # a stale handle must not block the new clip
                previous.close()
        self._close_output()

    def close_clip(self) -> None:
        self.set_source(None)

    def update_pyramid(self, pyramid: PeakPyramid | None) -> None:
        """Refresh the waveform envelope cache without rewinding transport."""
        with self._lock:
            self._pyramid = pyramid

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
            if self._source is None or self._state is TransportState.PLAYING:
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
            if self._source is not None:
                self._source_pos = self._play_origin
            self._levels = LevelReading()

    def seek(self, frame: int) -> int:
        """Move the playhead to ``frame``; returns the clamped position."""
        with self._lock:
            if self._source is None:
                return 0
            target = max(0, min(int(frame), self.n_frames))
            self._source_pos = target
            self._play_origin = target
            self._exhausted = False
            self._generation += 1
            if self._ring is not None:
                self._ring.clear()
            return target

    def seek_seconds(self, seconds: float) -> int:
        return self.seek(int(round(seconds * max(self.sample_rate, 1))))

    @property
    def position(self) -> int:
        """Playhead in frames, compensated for what is still queued in the ring."""
        with self._lock:
            if self._source is None:
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
        """Device callback: drain the ring buffer, apply gain, publish levels.

        Allocates the block it returns, because the backend owns the result
        afterwards. A backend that can supply its own buffer should call
        :meth:`render_into` instead and pay no allocation at all.
        """
        ring = self._ring
        channels = ring.channels if ring is not None else max(self.n_channels, 1)
        out = np.empty((n_frames, channels), dtype=SAMPLE_DTYPE)
        self.render_into(out)
        return out

    def render_into(self, out: np.ndarray) -> int:
        """Zero-allocation device callback: fill ``out`` in place.

        Returns the number of real frames; anything beyond that is silence the
        ring buffer could not cover. Nothing here allocates, takes a lock or
        touches the filesystem — the three things a real-time callback must not
        do — because the feeder thread has already done all of them.
        """
        ring = self._ring
        if ring is None or self._state is not TransportState.PLAYING:
            out[:] = 0.0
            return 0

        delivered = ring.read_into(out)
        gain = 0.0 if self._muted else self._volume
        if gain != 1.0:
            out *= SAMPLE_DTYPE(gain)
        self._update_levels(out)
        return delivered

    def _update_levels(self, block: np.ndarray) -> None:
        if block.size == 0:
            return
        peak = np.max(np.abs(block), axis=0)
        rms = np.sqrt(np.mean(np.square(block, dtype=np.float64), axis=0))
        self._levels = LevelReading(
            peak=tuple(float(v) for v in peak), rms=tuple(float(v) for v in rms)
        )

    def _prepare_stream(self) -> None:
        """Open the device for the source's format, resampling only if forced."""
        source = self._source
        assert source is not None
        sample_rate, channels = source.sample_rate, source.n_channels
        if (
            self._output.is_open
            and self._output.sample_rate == sample_rate
            and self._output.channels == channels
        ):
            self._reset_ring(channels)
            return

        try:
            self._output.open(sample_rate, channels, self.render, block_size=self._block_size)
        except OutputDeviceError:
            channels = self._resample_to_fallback_rate(sample_rate)
            self._output.open(
                FALLBACK_SAMPLE_RATE, channels, self.render, block_size=self._block_size
            )
        self._reset_ring(channels)

    def _resample_to_fallback_rate(self, sample_rate: int) -> int:
        """Convert the whole source when the device refuses its native rate.

        Streamed sources are materialised first: a device that cannot be opened
        at the file's rate leaves no way to convert block by block without a
        stateful resampler, and pulling one in belongs to a later milestone.
        """
        source = self._source
        assert source is not None
        original = source.to_buffer() if hasattr(source, "to_buffer") else None
        if original is None:
            original = AudioBuffer(source.read(0, source.n_frames), sample_rate)
        converted = resample(original, FALLBACK_SAMPLE_RATE)
        ratio = FALLBACK_SAMPLE_RATE / sample_rate

        if self._owns_source:
            with suppress(Exception):
                source.close()
        self._source = MemorySampleSource(converted)
        self._owns_source = False
        if self._clip is not None:
            self._clip = LoadedAudio(
                buffer=converted,
                audio_format=self._clip.audio_format,
                path=self._clip.path,
            )
        if self._pyramid is not None:
            self._pyramid = PeakPyramid(converted.data)
        self._source_pos = int(self._source_pos * ratio)
        self._play_origin = int(self._play_origin * ratio)
        return converted.n_channels

    def _reset_ring(self, channels: int) -> None:
        capacity = max(self._block_size * self._ring_blocks, self._block_size * 4)
        self._ring = RingBuffer(capacity, channels)
        # Reused by every pump, so steady-state playback allocates nothing on
        # the feeder thread either -- the ring copies out of it immediately.
        self._scratch = np.empty((self._block_size, channels), dtype=SAMPLE_DTYPE)

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
        """Pull at most one block from the source into the ring buffer."""
        with self._lock:
            ring = self._ring
            source = self._source
            if ring is None or source is None or self._exhausted:
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

            position = self._source_pos
            generation = self._generation
            scratch = self._scratch
            n = min(self._block_size, region.end - position)

        # Decoding happens outside the lock. A streaming source touches the disk
        # here, and the GUI polls :attr:`position` thirty times a second.
        chunk = scratch[:n]
        decoded = source.read_into(chunk, position)

        with self._lock:
            if generation != self._generation or ring is not self._ring:
                return True  # a seek landed mid-read: drop the block and re-pump
            if decoded == 0:  # truncated, closed or failed source
                self._exhausted = True
                return False
            written = ring.write(chunk[:decoded])
            self._source_pos = position + written
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
        """Release the device and any file handle we own; safe to call twice."""
        self._teardown(join_feeder=True)
        with self._lock:
            source, owned = self._source, self._owns_source
            self._owns_source = False
        if owned and source is not None:
            with suppress(Exception):  # shutdown is best-effort
                source.close()
        self._close_output()
