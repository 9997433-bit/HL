"""Multitrack session: the non-destructive Track / Clip / Bus model and its mixer.

Where :mod:`~audio_studio.core.edit_session` is the *destructive* half of the
application — one document, edited in place, undone through a command stack —
this module is the other half. A :class:`MultitrackSession` owns no samples at
all. It owns *references*: every :class:`Clip` points at a
:class:`~audio_studio.core.sample_source.SampleSource` and says which slice of
it lands where on the timeline. Moving a clip, changing a track's gain or
soloing a lane rewrites a handful of integers and floats; the audio underneath
is never rewritten, never copied and never consumed.

The mix is produced on demand by :class:`SessionMixer`, which is itself a
``SampleSource``::

    session = MultitrackSession(sample_rate=48_000)
    vox = session.add_track("Vox")
    session.add_clip(vox, MemorySampleSource(buffer), start=48_000)
    engine.set_source(session.mixer)

That single line is the whole integration story: the transport, the effect
preview insert and the loudness meter all already speak ``SampleSource``, so a
32-track mix reaches the device through exactly the same path a single clip
does.

Two properties of the summing path are load-bearing and are covered by tests:

* a track at unity gain and centre pan performs **no arithmetic at all** on its
  clip audio, so a one-track mixdown is bit-identical to the source and an
  A + (-A) null test lands on exact zeros;
* everything is expressed in integer frames, so clip alignment is exact rather
  than "within a sample or two of where you dropped it".
"""

from __future__ import annotations

import itertools
import threading
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from typing import Final

import numpy as np

from .sample_source import BaseSampleSource, SampleSource
from .types import SAMPLE_DTYPE, AudioBuffer, TimeRange, db_to_amplitude

#: Fader position below which a track or bus is treated as fully silent. Under
#: -96 dB the contribution is smaller than one LSB of 16-bit audio, so folding
#: it to zero costs nothing audible and keeps silent tracks off the summing bus.
SILENCE_DB: Final[float] = -96.0

#: Loudest fader position the model accepts, matching the mixer UI's range.
MAX_GAIN_DB: Final[float] = 24.0

SessionListener = Callable[["MultitrackSession"], None]

_track_counter = itertools.count(1)
_clip_counter = itertools.count(1)


def gain_to_amplitude(gain_db: float) -> float:
    """Fader position in dB as a linear factor, with a hard floor at silence."""
    value = float(gain_db)
    if value <= SILENCE_DB:
        return 0.0
    return 1.0 if value == 0.0 else db_to_amplitude(min(value, MAX_GAIN_DB))


def pan_gains(pan: float) -> tuple[float, float]:
    """Per-channel factors for a pan position in ``[-1, 1]``.

    This is a *balance* law rather than a constant-power one: the centre is
    unity on both channels instead of -3 dB. That choice is deliberate. A
    constant-power centre would scale every track by ``1/sqrt(2)`` even when
    nobody has touched the pan control, which would make a single-track mixdown
    differ from its own source file and turn every null test into an
    approximate one.
    """
    position = float(min(max(pan, -1.0), 1.0))
    return min(1.0, 1.0 - position), min(1.0, 1.0 + position)


def conform_channels(block: np.ndarray, channels: int) -> np.ndarray:
    """Fit a ``(frames, n)`` block onto a bus with ``channels`` channels.

    Mono spreads to every channel, wider material folds down by averaging, and
    a partial match keeps the channels it has and leaves the rest silent.
    """
    have = int(block.shape[1])
    if have == channels:
        return block
    if have == 1:
        return np.repeat(block, channels, axis=1)
    if channels == 1:
        return block.mean(axis=1, keepdims=True).astype(SAMPLE_DTYPE, copy=False)
    out = np.zeros((block.shape[0], channels), dtype=SAMPLE_DTYPE)
    take = min(have, channels)
    out[:, :take] = block[:, :take]
    return out


# ------------------------------------------------------------------- clips


@dataclass(frozen=True, slots=True)
class Clip:
    """One placement of a source on a track's timeline.

    ``source`` is the media reference (fable's ``media_ref``); ``start`` is
    where the clip begins on the session timeline, ``duration`` how long it
    plays for and ``offset`` how far into the source playback begins. All four
    are integer frames — the schema forbids floating-point time precisely so
    that a clip dropped at 1.5 s is still at 1.5 s after a thousand edits.

    Clips are immutable. Trimming or moving one produces a new record through
    :meth:`moved_to` and friends, which is what makes a track's clip list cheap
    to snapshot for the mixer while the UI is dragging.
    """

    source: SampleSource
    start: int
    duration: int
    offset: int = 0
    gain_db: float = 0.0
    fade_in: int = 0
    fade_out: int = 0
    name: str = ""
    clip_id: str = ""

    def __post_init__(self) -> None:
        set_ = object.__setattr__
        set_(self, "start", max(0, int(self.start)))
        set_(self, "duration", max(0, int(self.duration)))
        set_(self, "offset", max(0, int(self.offset)))
        set_(self, "gain_db", float(self.gain_db))
        # Fades are clamped rather than rejected: a trim that shortens a clip
        # past its own fade must leave a usable clip, not raise at the model
        # layer while the user is still holding the mouse button down.
        fade_in = max(0, min(int(self.fade_in), self.duration))
        fade_out = max(0, min(int(self.fade_out), self.duration - fade_in))
        set_(self, "fade_in", fade_in)
        set_(self, "fade_out", fade_out)
        if not self.clip_id:
            set_(self, "clip_id", f"clp_{next(_clip_counter):04d}")
        if not self.name:
            set_(self, "name", self.clip_id)

    # -- construction ------------------------------------------------------

    @classmethod
    def from_source(
        cls,
        source: SampleSource,
        *,
        start: int = 0,
        duration: int | None = None,
        offset: int = 0,
        **kwargs: object,
    ) -> Clip:
        """Place the whole of ``source`` (or ``duration`` frames of it) at ``start``."""
        available = max(int(source.n_frames) - max(0, int(offset)), 0)
        length = available if duration is None else min(int(duration), available)
        return cls(source, start, length, offset, **kwargs)  # type: ignore[arg-type]

    # -- geometry ----------------------------------------------------------

    @property
    def ref(self) -> SampleSource:
        """The media reference, under the name the architecture document uses."""
        return self.source

    @property
    def end(self) -> int:
        return self.start + self.duration

    @property
    def range(self) -> TimeRange:
        """Timeline span occupied by the clip."""
        return TimeRange(self.start, self.end)

    @property
    def source_range(self) -> TimeRange:
        """Span consumed inside the source."""
        return TimeRange(self.offset, self.offset + self.duration)

    @property
    def sample_rate(self) -> int:
        return int(self.source.sample_rate)

    @property
    def n_channels(self) -> int:
        return int(self.source.n_channels)

    @property
    def is_empty(self) -> bool:
        return self.duration == 0

    def overlaps(self, rng: TimeRange) -> bool:
        return self.start < rng.end and rng.start < self.end

    def contains(self, frame: int) -> bool:
        return self.start <= int(frame) < self.end

    # -- non-destructive edits --------------------------------------------

    def moved_to(self, start: int) -> Clip:
        """The same audio, starting somewhere else on the timeline."""
        return self.replace(start=start)

    def moved_by(self, frames: int) -> Clip:
        return self.replace(start=max(0, self.start + int(frames)))

    def with_gain(self, gain_db: float) -> Clip:
        return self.replace(gain_db=gain_db)

    def with_fades(self, fade_in: int | None = None, fade_out: int | None = None) -> Clip:
        return self.replace(
            fade_in=self.fade_in if fade_in is None else fade_in,
            fade_out=self.fade_out if fade_out is None else fade_out,
        )

    def trimmed(
        self,
        *,
        start: int | None = None,
        duration: int | None = None,
        offset: int | None = None,
    ) -> Clip:
        """Adjust the window without touching the source."""
        return self.replace(start=start, duration=duration, offset=offset)

    def trimmed_head(self, frames: int) -> Clip:
        """Pull the clip's left edge in by ``frames``, keeping the audio in place."""
        shift = max(0, min(int(frames), self.duration))
        return self.replace(
            start=self.start + shift,
            duration=self.duration - shift,
            offset=self.offset + shift,
            fade_in=max(0, self.fade_in - shift),
        )

    def trimmed_tail(self, frames: int) -> Clip:
        shift = max(0, min(int(frames), self.duration))
        return self.replace(
            duration=self.duration - shift, fade_out=max(0, self.fade_out - shift)
        )

    def split_at(self, frame: int) -> tuple[Clip, Clip]:
        """Cut the clip in two at a timeline frame, preserving both halves' audio."""
        if not self.contains(frame):
            raise ValueError(f"{frame} is outside {self.range!r}")
        head_len = int(frame) - self.start
        head = self.replace(duration=head_len, fade_out=min(self.fade_out, head_len))
        tail = self.replace(
            start=int(frame),
            duration=self.duration - head_len,
            offset=self.offset + head_len,
            fade_in=min(self.fade_in, self.duration - head_len),
            clip_id="",
        )
        return head, tail

    def replace(self, **changes: object) -> Clip:
        """``dataclasses.replace`` with ``None`` meaning "leave this alone"."""
        fields = {
            "source": self.source,
            "start": self.start,
            "duration": self.duration,
            "offset": self.offset,
            "gain_db": self.gain_db,
            "fade_in": self.fade_in,
            "fade_out": self.fade_out,
            "name": self.name,
            "clip_id": self.clip_id,
        }
        fields.update({key: value for key, value in changes.items() if value is not None})
        return Clip(**fields)  # type: ignore[arg-type]

    # -- rendering ---------------------------------------------------------

    def envelope(self, local_start: int, n_frames: int) -> np.ndarray | None:
        """Fade envelope for ``n_frames`` starting ``local_start`` into the clip.

        ``None`` means "unity throughout", which lets the caller skip a
        multiply over the whole block.
        """
        if n_frames <= 0 or (self.fade_in <= 0 and self.fade_out <= 0):
            return None
        index = np.arange(local_start, local_start + n_frames, dtype=np.float32)
        env = np.ones(n_frames, dtype=np.float32)
        if self.fade_in > 0:
            np.minimum(env, index / np.float32(self.fade_in), out=env)
        if self.fade_out > 0:
            np.minimum(env, (self.duration - index) / np.float32(self.fade_out), out=env)
        np.clip(env, 0.0, 1.0, out=env)
        return None if bool(np.all(env == 1.0)) else env

    def mix_into(self, out: np.ndarray, window_start: int) -> int:
        """Add this clip's contribution to ``out``; returns the frames written.

        ``out`` covers ``[window_start, window_start + len(out))`` of the
        timeline. Frames the clip does not cover are left untouched, so several
        clips (including overlapping ones) accumulate into the same buffer.
        """
        n_frames = int(out.shape[0])
        if n_frames <= 0 or self.duration <= 0:
            return 0
        lo = max(int(window_start), self.start)
        hi = min(int(window_start) + n_frames, self.end)
        if hi <= lo:
            return 0

        local = lo - self.start
        block = self.source.read(self.offset + local, hi - lo)
        count = int(block.shape[0])
        if count == 0:
            return 0

        block = conform_channels(block, int(out.shape[1]))
        env = self.envelope(local, count)
        if env is not None:
            block = block * env[:, np.newaxis]
        amplitude = gain_to_amplitude(self.gain_db)
        if amplitude == 0.0:
            return count
        if amplitude != 1.0:
            block = block * SAMPLE_DTYPE(amplitude)

        offset = lo - int(window_start)
        out[offset : offset + count] += block
        return count

    def read(self, window_start: int, n_frames: int, channels: int | None = None) -> np.ndarray:
        """This clip alone, rendered into a fresh timeline window."""
        width = self.n_channels if channels is None else int(channels)
        out = np.zeros((max(int(n_frames), 0), max(width, 1)), dtype=SAMPLE_DTYPE)
        self.mix_into(out, window_start)
        return out

    def __repr__(self) -> str:
        return (
            f"Clip({self.name!r}, [{self.start}, {self.end}) "
            f"<- src[{self.offset}:{self.offset + self.duration}])"
        )


# ------------------------------------------------------------------ tracks


class Track:
    """One lane: an ordered set of clips plus a fader, a pan and its toggles.

    The clip list is immutable from the outside (:attr:`clips` hands back a
    tuple) and is only changed through the mutators here, so the mixer can grab
    it without a lock and know it is looking at one coherent arrangement.
    """

    __slots__ = ("_clips", "_gain_db", "_mute", "_name", "_notify", "_pan", "_solo", "_track_id")

    def __init__(
        self,
        track_id: str = "",
        name: str = "",
        clips: Iterable[Clip] = (),
        *,
        gain_db: float = 0.0,
        pan: float = 0.0,
        mute: bool = False,
        solo: bool = False,
    ) -> None:
        self._track_id = track_id or f"trk_{next(_track_counter):02d}"
        self._name = name or self._track_id
        self._clips: list[Clip] = sorted(clips, key=lambda clip: clip.start)
        self._gain_db = float(gain_db)
        self._pan = float(min(max(pan, -1.0), 1.0))
        self._mute = bool(mute)
        self._solo = bool(solo)
        self._notify: Callable[[], None] | None = None

    # -- identity ----------------------------------------------------------

    @property
    def track_id(self) -> str:
        return self._track_id

    #: Alias for :attr:`track_id`, matching the ``Track(id, ...)`` spelling used
    #: in the architecture document and the project schema.
    @property
    def id(self) -> str:  # noqa: A003 - the schema calls this field "id"
        return self._track_id

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        text = str(value)
        if text != self._name:
            self._name = text
            self._touch()

    # -- mixer strip -------------------------------------------------------

    @property
    def gain_db(self) -> float:
        return self._gain_db

    @gain_db.setter
    def gain_db(self, value: float) -> None:
        clamped = float(min(max(float(value), SILENCE_DB), MAX_GAIN_DB))
        if clamped != self._gain_db:
            self._gain_db = clamped
            self._touch()

    @property
    def amplitude(self) -> float:
        return gain_to_amplitude(self._gain_db)

    @property
    def pan(self) -> float:
        return self._pan

    @pan.setter
    def pan(self, value: float) -> None:
        clamped = float(min(max(float(value), -1.0), 1.0))
        if clamped != self._pan:
            self._pan = clamped
            self._touch()

    @property
    def mute(self) -> bool:
        return self._mute

    @mute.setter
    def mute(self, value: bool) -> None:
        flag = bool(value)
        if flag != self._mute:
            self._mute = flag
            self._touch()

    @property
    def solo(self) -> bool:
        return self._solo

    @solo.setter
    def solo(self, value: bool) -> None:
        flag = bool(value)
        if flag != self._solo:
            self._solo = flag
            self._touch()

    # -- clips -------------------------------------------------------------

    @property
    def clips(self) -> tuple[Clip, ...]:
        return tuple(self._clips)

    @property
    def n_clips(self) -> int:
        return len(self._clips)

    @property
    def n_frames(self) -> int:
        """Timeline length of the lane: where its last clip ends."""
        return max((clip.end for clip in self._clips), default=0)

    def add_clip(self, clip: Clip) -> Clip:
        self._clips.append(clip)
        self._clips.sort(key=lambda item: item.start)
        self._touch()
        return clip

    def remove_clip(self, clip: Clip | str) -> bool:
        clip_id = clip if isinstance(clip, str) else clip.clip_id
        for index, existing in enumerate(self._clips):
            if existing.clip_id == clip_id:
                del self._clips[index]
                self._touch()
                return True
        return False

    def replace_clip(self, clip: Clip) -> Clip:
        """Swap in an edited version of a clip, matched by :attr:`Clip.clip_id`."""
        for index, existing in enumerate(self._clips):
            if existing.clip_id == clip.clip_id:
                self._clips[index] = clip
                self._clips.sort(key=lambda item: item.start)
                self._touch()
                return clip
        return self.add_clip(clip)

    def set_clips(self, clips: Iterable[Clip]) -> None:
        self._clips = sorted(clips, key=lambda clip: clip.start)
        self._touch()

    def clear_clips(self) -> None:
        if self._clips:
            self._clips.clear()
            self._touch()

    def clip(self, clip_id: str) -> Clip | None:
        return next((clip for clip in self._clips if clip.clip_id == clip_id), None)

    def clip_at(self, frame: int) -> Clip | None:
        """Topmost clip covering ``frame`` — the last one added wins an overlap."""
        return next((clip for clip in reversed(self._clips) if clip.contains(frame)), None)

    def clips_in(self, rng: TimeRange) -> tuple[Clip, ...]:
        return tuple(clip for clip in self._clips if clip.overlaps(rng))

    def __iter__(self) -> Iterator[Clip]:
        return iter(self._clips)

    def __len__(self) -> int:
        return len(self._clips)

    # -- rendering ---------------------------------------------------------

    def apply_fader(self, block: np.ndarray) -> np.ndarray:
        """Scale a rendered block in place by this track's gain and pan.

        Unity gain at centre pan is a no-op by construction, not by rounding:
        the block is returned untouched so an unaltered track sums bit-exactly.
        """
        amplitude = self.amplitude
        left, right = pan_gains(self._pan)
        if block.shape[1] == 2 and (left != 1.0 or right != 1.0):
            block[:, 0] *= SAMPLE_DTYPE(amplitude * left)
            block[:, 1] *= SAMPLE_DTYPE(amplitude * right)
        elif amplitude != 1.0:
            block *= SAMPLE_DTYPE(amplitude)
        return block

    def render(
        self, start: int, n_frames: int, channels: int, *, pre_fader: bool = False
    ) -> np.ndarray:
        """Sum this lane's clips over ``[start, start + n_frames)``."""
        out = np.zeros((max(int(n_frames), 0), max(int(channels), 1)), dtype=SAMPLE_DTYPE)
        if out.shape[0] == 0:
            return out
        for clip in self._clips:
            clip.mix_into(out, start)
        return out if pre_fader else self.apply_fader(out)

    def mix_into(self, out: np.ndarray, window_start: int) -> np.ndarray:
        """Add this lane, post-fader, into a shared summing buffer."""
        if not self._clips or self.amplitude == 0.0:
            return out
        out += self.render(window_start, int(out.shape[0]), int(out.shape[1]))
        return out

    # -- plumbing ----------------------------------------------------------

    def _bind(self, notify: Callable[[], None] | None) -> None:
        """Attach the owning session's invalidation hook (or detach on removal)."""
        self._notify = notify

    def _touch(self) -> None:
        if self._notify is not None:
            self._notify()

    def __repr__(self) -> str:
        flags = "".join(("M" if self._mute else "", "S" if self._solo else ""))
        return (
            f"Track({self._track_id!r}, {self._name!r}, {len(self._clips)} clips, "
            f"{self._gain_db:+.1f} dB, pan {self._pan:+.2f}{', ' + flags if flags else ''})"
        )


# -------------------------------------------------------------------- bus


class MasterBus:
    """Terminal summing point: every audible track lands here.

    Kept as a class rather than two attributes on the session because it is the
    seat the master effect rack, the master meter and (later) submix buses
    plug into — the mixer already calls :meth:`apply` at exactly the right
    point in the signal path.
    """

    __slots__ = ("_gain_db", "_mute", "_name", "_notify")

    def __init__(self, name: str = "Master", *, gain_db: float = 0.0, mute: bool = False) -> None:
        self._name = name
        self._gain_db = float(gain_db)
        self._mute = bool(mute)
        self._notify: Callable[[], None] | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def gain_db(self) -> float:
        return self._gain_db

    @gain_db.setter
    def gain_db(self, value: float) -> None:
        clamped = float(min(max(float(value), SILENCE_DB), MAX_GAIN_DB))
        if clamped != self._gain_db:
            self._gain_db = clamped
            self._touch()

    @property
    def amplitude(self) -> float:
        return gain_to_amplitude(self._gain_db)

    @property
    def mute(self) -> bool:
        return self._mute

    @mute.setter
    def mute(self, value: bool) -> None:
        flag = bool(value)
        if flag != self._mute:
            self._mute = flag
            self._touch()

    def apply(self, block: np.ndarray) -> np.ndarray:
        """Scale the summed mix in place by the master fader."""
        if self._mute:
            block[:] = 0.0
            return block
        amplitude = self.amplitude
        if amplitude != 1.0:
            block *= SAMPLE_DTYPE(amplitude)
        return block

    def _bind(self, notify: Callable[[], None] | None) -> None:
        self._notify = notify

    def _touch(self) -> None:
        if self._notify is not None:
            self._notify()

    def __repr__(self) -> str:
        state = ", muted" if self._mute else ""
        return f"MasterBus({self._name!r}, {self._gain_db:+.1f} dB{state})"


# ------------------------------------------------------------------ mixer


class SessionMixer(BaseSampleSource):
    """Renders a :class:`MultitrackSession` as a plain sample source.

    Summing order is: each audible track's clips accumulate into a per-track
    buffer, the track fader and pan scale it, the result is added to the master
    bus buffer, and the master fader scales the sum. Nothing about this needs
    the transport, so the same object serves live playback, offline mixdown and
    the loudness meter.
    """

    __slots__ = ("_session",)

    def __init__(self, session: MultitrackSession) -> None:
        self._session = session

    @property
    def session(self) -> MultitrackSession:
        return self._session

    @property
    def sample_rate(self) -> int:
        return self._session.sample_rate

    @property
    def n_frames(self) -> int:
        return self._session.n_frames

    @property
    def n_channels(self) -> int:
        return self._session.n_channels

    @property
    def exact(self) -> bool:
        """True only when every clip's media is already in memory."""
        return all(
            bool(getattr(clip.source, "exact", True)) for clip in self._session.clips
        )

    def read(self, start: int, n_frames: int) -> np.ndarray:
        start, count = self._clamp(start, n_frames)
        if count == 0:
            return self._empty()
        out = np.zeros((count, self._session.n_channels), dtype=SAMPLE_DTYPE)
        for track in self._session.audible_tracks():
            track.mix_into(out, start)
        return self._session.master.apply(out)

    def read_into(self, out: np.ndarray, start: int) -> int:
        """Mix straight into the feeder's scratch buffer.

        The summing pass has to start from silence anyway, so filling the
        caller's buffer costs nothing over :meth:`read` and saves the block
        allocation on every pump.
        """
        self._check_out(out)
        start, count = self._clamp(start, int(out.shape[0]))
        out[:] = 0.0
        if count == 0:
            return 0
        view = out[:count]
        try:
            for track in self._session.audible_tracks():
                track.mix_into(view, start)
            self._session.master.apply(view)
        except Exception as exc:  # noqa: BLE001 - the feeder must keep running
            self._last_error = exc
            out[:] = 0.0
            return 0
        return count

    def render_tracks(self, start: int, n_frames: int) -> dict[str, np.ndarray]:
        """Post-fader stems, keyed by track id — the basis for per-track meters."""
        start, count = self._clamp(start, n_frames)
        channels = self._session.n_channels
        return {
            track.track_id: track.render(start, count, channels)
            for track in self._session.tracks
        }

    def mixdown(self, rng: TimeRange | None = None) -> AudioBuffer:
        """Render the whole session (or one range) into memory."""
        span = TimeRange(0, self.n_frames) if rng is None else rng.clamped(self.n_frames)
        return AudioBuffer(self.read(span.start, span.length), self.sample_rate)

    def __repr__(self) -> str:
        return f"SessionMixer({self._session!r})"


# ---------------------------------------------------------------- session


class MultitrackSession:
    """The non-destructive arrangement: tracks, their clips and a master bus.

    Every structural change bumps :attr:`revision` and notifies listeners, which
    is how the multitrack view knows to drop its cached waveform strips without
    the model importing a single Qt symbol.
    """

    __slots__ = (
        "_channels",
        "_lock",
        "_listeners",
        "_master",
        "_mixer",
        "_name",
        "_revision",
        "_sample_rate",
        "_tracks",
    )

    def __init__(
        self,
        *,
        sample_rate: int = 44_100,
        n_channels: int = 2,
        name: str = "Session",
        tracks: Iterable[Track] = (),
    ) -> None:
        if sample_rate <= 0:
            raise ValueError(f"sample_rate must be positive, got {sample_rate}")
        if n_channels <= 0:
            raise ValueError(f"n_channels must be positive, got {n_channels}")
        self._sample_rate = int(sample_rate)
        self._channels = int(n_channels)
        self._name = name
        self._tracks: list[Track] = []
        self._master = MasterBus()
        self._master._bind(self._touch)  # noqa: SLF001 - the session owns its bus
        self._mixer = SessionMixer(self)
        self._listeners: list[SessionListener] = []
        self._revision = 0
        self._lock = threading.RLock()
        for track in tracks:
            self.add_track(track)

    # -- format ------------------------------------------------------------

    @property
    def name(self) -> str:
        return self._name

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def n_channels(self) -> int:
        return self._channels

    def set_format(self, sample_rate: int, n_channels: int) -> None:
        """Adopt a rate and channel count — only legal while the session is empty.

        Resampling a placed clip is a Round 3+ concern; refusing the change is
        better than silently detuning an arrangement.
        """
        if any(track.n_clips for track in self._tracks):
            raise ValueError("cannot change the session format once clips have been placed")
        if sample_rate <= 0 or n_channels <= 0:
            raise ValueError(f"invalid session format {sample_rate} Hz / {n_channels} ch")
        self._sample_rate = int(sample_rate)
        self._channels = int(n_channels)
        self._touch()

    # -- tracks ------------------------------------------------------------

    @property
    def tracks(self) -> tuple[Track, ...]:
        return tuple(self._tracks)

    @property
    def n_tracks(self) -> int:
        return len(self._tracks)

    @property
    def master(self) -> MasterBus:
        return self._master

    @property
    def mixer(self) -> SessionMixer:
        return self._mixer

    def add_track(self, track: Track | str | None = None, **kwargs: object) -> Track:
        """Append a track; ``add_track("Vox")`` builds one from a name."""
        if not isinstance(track, Track):
            track = Track(name=track or "", **kwargs)  # type: ignore[arg-type]
        with self._lock:
            if any(existing.track_id == track.track_id for existing in self._tracks):
                raise ValueError(f"duplicate track id {track.track_id!r}")
            track._bind(self._touch)  # noqa: SLF001 - the session owns its tracks
            self._tracks.append(track)
            self._touch()
        return track

    def remove_track(self, track: Track | str) -> bool:
        track_id = track if isinstance(track, str) else track.track_id
        with self._lock:
            for index, existing in enumerate(self._tracks):
                if existing.track_id == track_id:
                    existing._bind(None)  # noqa: SLF001 - detach on removal
                    del self._tracks[index]
                    self._touch()
                    return True
        return False

    def move_track(self, track: Track | str, index: int) -> None:
        """Reorder a lane; the mix is order-independent but the view is not."""
        track_id = track if isinstance(track, str) else track.track_id
        with self._lock:
            current = next(
                (i for i, item in enumerate(self._tracks) if item.track_id == track_id), None
            )
            if current is None:
                raise KeyError(track_id)
            item = self._tracks.pop(current)
            self._tracks.insert(max(0, min(int(index), len(self._tracks))), item)
            self._touch()

    def track(self, track_id: str) -> Track | None:
        return next((item for item in self._tracks if item.track_id == track_id), None)

    def clear(self) -> None:
        with self._lock:
            for track in self._tracks:
                track._bind(None)  # noqa: SLF001 - detach on removal
            self._tracks.clear()
            self._touch()

    def __iter__(self) -> Iterator[Track]:
        return iter(self._tracks)

    def __len__(self) -> int:
        return len(self._tracks)

    # -- clips -------------------------------------------------------------

    def add_clip(
        self,
        track: Track | str,
        source: SampleSource,
        *,
        start: int = 0,
        duration: int | None = None,
        offset: int = 0,
        gain_db: float = 0.0,
        fade_in: int = 0,
        fade_out: int = 0,
        name: str = "",
    ) -> Clip:
        """Place ``source`` on ``track``, checking that it belongs in this session."""
        lane = self.track(track) if isinstance(track, str) else track
        if lane is None or lane not in self._tracks:
            raise KeyError(f"no such track: {track!r}")
        if int(source.sample_rate) != self._sample_rate:
            raise ValueError(
                f"clip is {source.sample_rate} Hz but the session runs at {self._sample_rate} Hz"
            )
        clip = Clip.from_source(
            source,
            start=start,
            duration=duration,
            offset=offset,
            gain_db=gain_db,
            fade_in=fade_in,
            fade_out=fade_out,
            name=name,
        )
        return lane.add_clip(clip)

    @property
    def clips(self) -> tuple[Clip, ...]:
        return tuple(clip for track in self._tracks for clip in track.clips)

    # -- geometry ----------------------------------------------------------

    @property
    def n_frames(self) -> int:
        """Session length: the end of the last clip on any track."""
        return max((track.n_frames for track in self._tracks), default=0)

    @property
    def duration(self) -> float:
        return self.n_frames / self._sample_rate

    @property
    def range(self) -> TimeRange:
        return TimeRange(0, self.n_frames)

    # -- mixing ------------------------------------------------------------

    @property
    def solo_active(self) -> bool:
        return any(track.solo for track in self._tracks)

    def audible_tracks(self) -> tuple[Track, ...]:
        """Tracks that reach the master bus right now.

        Solo implicitly mutes everything else, but an explicit mute still wins:
        arming solo on a lane you had deliberately muted should not un-mute it.
        """
        if self.solo_active:
            return tuple(track for track in self._tracks if track.solo and not track.mute)
        return tuple(track for track in self._tracks if not track.mute)

    def read(self, start: int, n_frames: int) -> np.ndarray:
        """SampleSource surface: the finished mix, master fader included."""
        return self._mixer.read(start, n_frames)

    def read_into(self, out: np.ndarray, start: int) -> int:
        return self._mixer.read_into(out, start)

    def read_range(self, rng: TimeRange) -> np.ndarray:
        return self._mixer.read_range(rng)

    @property
    def exact(self) -> bool:
        return self._mixer.exact

    @property
    def last_error(self) -> Exception | None:
        return self._mixer.last_error

    def render_tracks(self, start: int, n_frames: int) -> dict[str, np.ndarray]:
        return self._mixer.render_tracks(start, n_frames)

    def mixdown(self, rng: TimeRange | None = None) -> AudioBuffer:
        return self._mixer.mixdown(rng)

    def to_buffer(self, rng: TimeRange | None = None) -> AudioBuffer:
        return self._mixer.mixdown(rng)

    def close(self) -> None:
        """Present for the SampleSource protocol; clips do not own their media."""

    # -- change notification ----------------------------------------------

    @property
    def revision(self) -> int:
        """Bumped on every change; the invalidation key for cached strips."""
        return self._revision

    def add_listener(self, listener: SessionListener) -> None:
        self._listeners.append(listener)

    def remove_listener(self, listener: SessionListener) -> None:
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _touch(self) -> None:
        self._revision += 1
        for listener in tuple(self._listeners):
            listener(self)

    def __repr__(self) -> str:
        return (
            f"MultitrackSession({self._name!r}, {len(self._tracks)} tracks, "
            f"{self.n_frames} frames, {self._channels}ch @ {self._sample_rate} Hz, "
            f"rev {self._revision})"
        )


__all__ = [
    "MAX_GAIN_DB",
    "SILENCE_DB",
    "Clip",
    "MasterBus",
    "MultitrackSession",
    "SessionMixer",
    "Track",
    "conform_channels",
    "gain_to_amplitude",
    "pan_gains",
]
