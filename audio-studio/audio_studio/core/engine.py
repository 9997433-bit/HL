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
:class:`~audio_studio.core.edit_session.EditSession` document mid-edit. An
optional per-block insert — the live effect rack — runs on the feeder as well,
so a rack deep enough to miss a deadline costs latency instead of a dropout;
see :meth:`AudioEngine.set_stream_processor`. The level meter follows the same
rule: the device callback only copies its finished block into the telemetry's
preallocated capture buffer, and the feeder runs the peak/RMS reductions and
publishes them, keeping every NumPy reduction off the device thread.

The playhead is derived as ``frames_queued - frames_still_in_ring`` so it
reports what the listener is actually hearing rather than how far the feeder
has run ahead. That figure only moves once per device callback;
:attr:`AudioEngine.position_interpolated` fills in the gap between callbacks so
a UI repainting faster than the block rate still draws a playhead that glides.

Master volume is smoothed rather than applied as a step. A slider dropped from
unity to silence between two blocks is a discontinuity in the waveform, and a
discontinuity is a click — so every change is walked to its target over
:data:`VOLUME_RAMP_MS`.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path

import numpy as np

from . import rt_discipline
from .loader import LoadedAudio, load_audio, resample
from .output import DEFAULT_BLOCK_SIZE, AudioOutput, OutputDeviceError, create_output
from .peaks import PeakPyramid
from .peaks_cache import cached_pyramid
from .ring_buffer import RingBuffer
from .sample_source import MemorySampleSource, SampleSource, StreamingSampleSource
from .telemetry import EngineTelemetry, LevelSnapshot
from .types import (
    SAMPLE_DTYPE,
    AudioBuffer,
    AudioFormat,
    TimeRange,
    TransportState,
)

#: Ring buffer depth as a multiple of the device block size.
RING_BLOCKS: int = 16

#: Sample rate used when the device rejects the clip's native rate.
FALLBACK_SAMPLE_RATE: int = 48000

#: Time a volume or mute change is spread over, in milliseconds. Long enough to
#: put the step below the ear's click threshold, short enough that the fader
#: still feels attached to the sound.
VOLUME_RAMP_MS: float = 10.0

StateListener = Callable[[TransportState], None]

#: ``processor(block, sample_rate) -> block``. Run on the feeder thread over a
#: ``(frames, channels)`` float32 block before it reaches the ring buffer; see
#: :meth:`AudioEngine.set_stream_processor`.
StreamProcessor = Callable[[np.ndarray, int], np.ndarray]


class AudioEngine:
    """Loads a clip and plays it through an :class:`AudioOutput` backend."""

    def __init__(
        self,
        output: AudioOutput | None = None,
        *,
        block_size: int = DEFAULT_BLOCK_SIZE,
        ring_blocks: int = RING_BLOCKS,
        volume_ramp_ms: float = VOLUME_RAMP_MS,
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
        self._telemetry = EngineTelemetry(block_size=self._block_size)

        # Gain smoothing. ``_gain`` is what the last frame was actually scaled
        # by; the device thread walks it towards ``_gain_target`` in
        # ``_gain_step`` increments over ``_gain_remaining`` more frames.
        self._ramp_ms = max(float(volume_ramp_ms), 0.0)
        self._ramp_frames = 1
        self._gain = 1.0
        self._gain_target = 1.0
        self._gain_step = 0.0
        self._gain_remaining = 0
        self._ramp_curve = np.empty(self._block_size, dtype=SAMPLE_DTYPE)
        self._ramp_index = np.arange(1, self._block_size + 1, dtype=SAMPLE_DTYPE)

        # Playhead interpolation: how many real frames the device has taken
        # since the last seek, how big the last helping was, and when it was
        # handed over. Written by the device thread, read by the GUI.
        self._frames_rendered = 0
        self._render_span = 0
        self._render_time = time.perf_counter()

        self._stream_processor: StreamProcessor | None = None

        self._feeder: threading.Thread | None = None
        self._feeder_stop = threading.Event()
        self._realtime_mode_entered = False
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
        source = self._source
        return isinstance(source, StreamingSampleSource) or bool(
            getattr(source, "is_streaming", False)
        )

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
            self._telemetry.configure(
                source.n_channels if source is not None else 0,
                block_size=self._block_size,
            )
            self._ring = None
            self._reset_render_clock()
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
            self._telemetry.clear()

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
            self._reset_render_clock()
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

    @property
    def frames_rendered(self) -> int:
        """Real output frames the device has taken since the last seek or load.

        Silence written into an underrun does not count, so this matches the
        distance :attr:`position` has travelled rather than how long the stream
        has been open.
        """
        return self._frames_rendered

    @property
    def position_interpolated(self) -> float:
        """Playhead in frames, sub-block accurate, as a float.

        :attr:`position` can only move when the device asks for a block, so a
        GUI polling faster than the block rate sees the playhead sit still and
        then jump. This estimate trails :attr:`position` by one block and walks
        that block's worth of frames off against the wall clock, which turns
        the same information into continuous motion.

        The result is clamped to the last delivered block, so a device that
        stops pulling (a pause, an underrun, a stopped test harness) leaves the
        playhead parked on a real position instead of drifting off it.
        """
        position = self.position
        span = self._render_span
        rate = self.sample_rate
        if span <= 0 or rate <= 0 or self._state is not TransportState.PLAYING:
            return float(position)
        elapsed = time.perf_counter() - self._render_time
        played = min(max(elapsed * rate, 0.0), float(span))
        estimate = position - span + played
        return float(min(max(estimate, 0.0), float(self.n_frames)))

    @property
    def position_seconds_interpolated(self) -> float:
        rate = self.sample_rate
        return self.position_interpolated / rate if rate else 0.0

    def _reset_render_clock(self) -> None:
        """Forget the render history a seek has just invalidated."""
        self._frames_rendered = 0
        self._render_span = 0
        self._render_time = time.perf_counter()

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
    def telemetry(self) -> EngineTelemetry:
        """Lock-free render-thread telemetry consumed by the UI."""
        return self._telemetry

    @property
    def levels(self) -> LevelSnapshot:
        """Most recent per-channel peak/RMS meter reading.

        The device callback only captures its rendered block; the feeder
        thread measures and publishes it a moment later, so a reading trails
        the newest callback by up to one feeder tick.
        """
        return self._telemetry.read_levels()

    @property
    def buffered_frames(self) -> int:
        """Frames decoded and queued ahead of the device callback."""
        ring = self._ring
        return ring.available_read if ring is not None else 0

    @property
    def underrun_frames(self) -> int:
        """Frames the device callback zero-filled because the feeder fell behind.

        Counted since the current pass opened its ring buffer; the soak
        harness and health displays read this instead of reaching into the
        ring directly.
        """
        ring = self._ring
        return ring.underrun_frames if ring is not None else 0

    @property
    def volume_ramp_ms(self) -> float:
        """How long a volume or mute change takes to reach its target."""
        return self._ramp_ms

    @property
    def applied_gain(self) -> float:
        """Gain the most recently rendered frame was scaled by.

        Equal to the target volume except while a ramp is in flight, which is
        what makes the smoothing observable from outside the device thread.
        """
        return self._gain

    # ---------------------------------------------------------------- insert

    @property
    def stream_processor(self) -> StreamProcessor | None:
        return self._stream_processor

    def set_stream_processor(self, processor: StreamProcessor | None) -> None:
        """Install a per-block insert that runs on the **feeder** thread.

        ``processor(block, sample_rate)`` is handed each decoded block on its
        way into the ring buffer and returns the block to queue — the same
        shape and dtype, or the input untouched. Running it here rather than in
        :meth:`render_into` buys it the ring buffer's whole depth as slack: a
        block that takes longer than its own duration to process costs latency
        the ring absorbs, where on the device thread it would have cost a
        dropout.

        The cost is that a parameter change only reaches the speakers once the
        already-queued blocks have drained, so an insert whose settings must
        respond instantly wants the device path instead.
        """
        self._stream_processor = processor

    def _process_block(self, block: np.ndarray, sample_rate: int) -> np.ndarray:
        """Run the insert on the feeder thread, falling back to dry audio."""
        processor = self._stream_processor
        if processor is None or block.size == 0:
            return block
        try:
            processed = np.asarray(processor(block, sample_rate), dtype=SAMPLE_DTYPE)
        except Exception:  # noqa: BLE001 - a broken insert must not kill the feeder
            return block
        # A processor that changed the block's length would desynchronise the
        # playhead from the audio, so only a same-shaped result is accepted.
        return processed if processed.shape == block.shape else block

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
        """Device callback: drain the ring buffer, apply gain, capture levels.

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
        do — because the feeder thread has already done all of them. Even the
        level meter obeys that split: the callback only copies the rendered
        block into the telemetry's preallocated capture buffer, and the feeder
        thread runs the NumPy peak/RMS reductions and publishes them.
        """
        ring = self._ring
        if ring is None or self._state is not TransportState.PLAYING:
            out[:] = 0.0
            return 0

        delivered = ring.read_into(out)
        self._apply_gain(out)
        self._telemetry.capture_block(out)
        if delivered:
            # Only a real block re-anchors the interpolator; an underrun would
            # otherwise restart the clock and stall the playhead.
            self._frames_rendered += delivered
            self._render_span = delivered
            self._render_time = time.perf_counter()
        return delivered

    def _apply_gain(self, out: np.ndarray) -> None:
        """Scale ``out`` by the master gain, ramping across a change.

        Steady state costs one multiply (and nothing at all at unity). Only the
        ~10 ms after the fader moves takes the ramped path, which walks a
        pre-allocated curve rather than building one per block.
        """
        target = 0.0 if self._muted else self._volume
        if target != self._gain_target:
            self._begin_gain_ramp(target)

        if not self._gain_remaining:
            if self._gain != 1.0:
                out *= SAMPLE_DTYPE(self._gain)
            return

        n = int(out.shape[0])
        ramped = min(n, self._gain_remaining)
        out[:ramped] *= self._gain_curve(ramped)[:, np.newaxis]

        self._gain_remaining -= ramped
        self._gain = (
            self._gain_target if not self._gain_remaining else self._gain + self._gain_step * ramped
        )
        if ramped < n and self._gain != 1.0:
            out[ramped:] *= SAMPLE_DTYPE(self._gain)

    def _begin_gain_ramp(self, target: float) -> None:
        """Aim the ramp at ``target``, starting from wherever it is now."""
        self._gain_target = target
        frames = self._ramp_frames
        if frames <= 0 or target == self._gain:
            self._snap_gain(target)
            return
        self._gain_step = (target - self._gain) / frames
        self._gain_remaining = frames

    def _snap_gain(self, target: float) -> None:
        """Jump to ``target`` with no ramp — only safe when nothing is playing."""
        self._gain = self._gain_target = target
        self._gain_step = 0.0
        self._gain_remaining = 0

    def _gain_curve(self, n: int) -> np.ndarray:
        """The next ``n`` gain values of the ramp, in a reused buffer."""
        if self._ramp_index.shape[0] < n:
            self._ramp_index = np.arange(1, n + 1, dtype=SAMPLE_DTYPE)
            self._ramp_curve = np.empty(n, dtype=SAMPLE_DTYPE)
        curve = self._ramp_curve[:n]
        np.multiply(self._ramp_index[:n], SAMPLE_DTYPE(self._gain_step), out=curve)
        curve += SAMPLE_DTYPE(self._gain)
        return curve

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
        self._adopt_output_block_size(channels)
        self._reset_ring(channels)

    def _adopt_output_block_size(self, channels: int) -> None:
        """Resize preallocated engine workspaces after hardware negotiation."""
        negotiated = int(self._output.block_size)
        if negotiated == self._block_size:
            return
        self._block_size = negotiated
        self._telemetry.configure(channels, block_size=negotiated)
        self._ramp_curve = np.empty(negotiated, dtype=SAMPLE_DTYPE)
        self._ramp_index = np.arange(1, negotiated + 1, dtype=SAMPLE_DTYPE)

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
        rate = self._output.sample_rate or self.sample_rate
        self._ramp_frames = max(int(round(self._ramp_ms * rate / 1000.0)), 1)
        # A pass starts at whatever the fader says: the only reason to ramp is
        # a change made to audio already in flight.
        self._snap_gain(0.0 if self._muted else self._volume)
        self._reset_render_clock()

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
        if not self._realtime_mode_entered:
            rt_discipline.enter_realtime_mode()
            self._realtime_mode_entered = True
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
            # Measure and publish whatever block the device captured last.
            # Running the meter reductions here keeps them off the device
            # thread; the ring's depth means the latency this adds is invisible
            # next to the audio already queued ahead of the reading.
            self._telemetry.publish_pending()
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
            sample_rate = source.sample_rate
            n = min(self._block_size, region.end - position)

        # Decoding and processing happen outside the lock. A streaming source
        # touches the disk here, an insert runs a whole effect chain, and the
        # GUI polls :attr:`position` thirty times a second throughout.
        chunk = scratch[:n]
        decoded = source.read_into(chunk, position)
        block = self._process_block(chunk[:decoded], sample_rate) if decoded else chunk[:0]

        with self._lock:
            if generation != self._generation or ring is not self._ring:
                return True  # a seek landed mid-read: drop the block and re-pump
            if decoded == 0:  # truncated, closed or failed source
                self._exhausted = True
                return False
            written = ring.write(block)
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
            self._telemetry.clear()
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
        if self._realtime_mode_entered:
            self._realtime_mode_entered = False
            rt_discipline.leave_realtime_mode()
