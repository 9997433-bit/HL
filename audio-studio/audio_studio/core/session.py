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

Tracks reach the master either directly or through one :class:`Bus`, which is
as deep as the routing goes: a bus never sends to another bus, so the mixer
resolves the whole graph in two passes and a cycle cannot be expressed.

A track's fader can also be *automated*: :class:`GainAutomation` holds a list of
:class:`AutomationPoint` breakpoints and the mixer interpolates between them per
block, so a lane can ride its own level over the arrangement.

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
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

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
_bus_counter = itertools.count(1)


def gain_to_amplitude(gain_db: float) -> float:
    """Fader position in dB as a linear factor, with a hard floor at silence."""
    value = float(gain_db)
    if value <= SILENCE_DB:
        return 0.0
    return 1.0 if value == 0.0 else db_to_amplitude(min(value, MAX_GAIN_DB))


def gain_curve_to_amplitude(gain_db: np.ndarray) -> np.ndarray:
    """:func:`gain_to_amplitude` over a whole array of fader positions.

    Kept beside the scalar version and floored at the same place, so a
    breakpoint parked at silence produces exact zeros rather than a value that
    is merely very small.
    """
    values = np.asarray(gain_db, dtype=SAMPLE_DTYPE)
    amplitude = np.power(
        SAMPLE_DTYPE(10.0), np.minimum(values, SAMPLE_DTYPE(MAX_GAIN_DB)) / SAMPLE_DTYPE(20.0)
    )
    amplitude[values <= SILENCE_DB] = 0.0
    return amplitude


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


def _bus_id_of(target: object) -> str | None:
    """Normalise a routing target — a :class:`Bus`, a bus id or ``None`` — to an id."""
    bus_id = getattr(target, "bus_id", target)
    if bus_id is None:
        return None
    text = str(bus_id).strip()
    return text or None


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


# -------------------------------------------------------------- automation


@dataclass(frozen=True, slots=True)
class AutomationPoint:
    """One breakpoint on an automation curve: a frame and the value held there.

    ``value`` is in the same units as the parameter being automated — for the
    only curve that exists so far, :attr:`Track.automation`, that is the fader
    position in dB, clamped to the range the fader itself accepts.
    """

    frame: int
    value: float

    def __post_init__(self) -> None:
        set_ = object.__setattr__
        set_(self, "frame", max(0, int(self.frame)))
        set_(self, "value", float(min(max(float(self.value), SILENCE_DB), MAX_GAIN_DB)))

    def moved_to(self, frame: int) -> AutomationPoint:
        return AutomationPoint(frame, self.value)

    def with_value(self, value: float) -> AutomationPoint:
        return AutomationPoint(self.frame, value)

    def to_json(self) -> list[float]:
        """``[frame, value]`` — the compact pair the project bundle stores."""
        return [int(self.frame), float(self.value)]


class GainAutomation:
    """A track's gain envelope: breakpoints joined by straight lines.

    The curve is a sorted list of :class:`AutomationPoint`, at most one per
    frame, and reading it is a plain linear interpolation. Outside the outermost
    breakpoints the first and last values are *held* rather than extrapolated,
    so adding a point in the middle of an arrangement cannot silently change
    what happens at its edges.

    An empty curve means "not automated": the track falls back to its static
    fader. That distinction matters, because a curve flat at 0 dB is not the
    same thing as no curve at all — the first one pins the lane at unity and
    ignores the fader, the second one lets the fader through.
    """

    __slots__ = ("_notify", "_points")

    def __init__(self, points: Iterable[AutomationPoint | tuple[int, float]] = ()) -> None:
        self._points: tuple[AutomationPoint, ...] = _sorted_points(points)
        self._notify: Callable[[], None] | None = None

    # -- contents ----------------------------------------------------------

    @property
    def points(self) -> tuple[AutomationPoint, ...]:
        return self._points

    @property
    def is_empty(self) -> bool:
        return not self._points

    @property
    def n_frames(self) -> int:
        """Frame of the last breakpoint; 0 when the curve is empty."""
        return self._points[-1].frame if self._points else 0

    def __len__(self) -> int:
        return len(self._points)

    def __iter__(self) -> Iterator[AutomationPoint]:
        return iter(self._points)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, GainAutomation):
            return self._points == other._points
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._points)

    # -- editing -----------------------------------------------------------

    def set_point(self, frame: int, value: float) -> AutomationPoint:
        """Add a breakpoint, or move the one already sitting on ``frame``."""
        point = AutomationPoint(frame, value)
        kept = tuple(item for item in self._points if item.frame != point.frame)
        self._replace(_sorted_points((*kept, point)))
        return point

    def set_points(self, points: Iterable[AutomationPoint | tuple[int, float]]) -> None:
        self._replace(_sorted_points(points))

    def move_point(self, frame: int, new_frame: int, value: float) -> AutomationPoint | None:
        """Drag the breakpoint at ``frame`` to a new position and value."""
        existing = self.point_at(frame)
        if existing is None:
            return None
        kept = tuple(item for item in self._points if item.frame not in (frame, int(new_frame)))
        moved = AutomationPoint(new_frame, value)
        self._replace(_sorted_points((*kept, moved)))
        return moved

    def remove_point(self, frame: int) -> bool:
        kept = tuple(item for item in self._points if item.frame != int(frame))
        if len(kept) == len(self._points):
            return False
        self._replace(kept)
        return True

    def clear(self) -> None:
        """Drop every breakpoint, handing the lane back to its static fader."""
        if self._points:
            self._replace(())

    def line(self, start: int, end: int, start_value: float, end_value: float) -> None:
        """Replace the curve with a straight two-point ramp."""
        self._replace(
            _sorted_points(
                (AutomationPoint(start, start_value), AutomationPoint(end, end_value))
            )
        )

    def flat(self, frames: Iterable[int], value: float) -> None:
        """Replace the curve with points at ``frames``, all holding ``value``."""
        self._replace(_sorted_points(AutomationPoint(frame, value) for frame in frames))

    # -- lookup ------------------------------------------------------------

    def point_at(self, frame: int) -> AutomationPoint | None:
        return next((item for item in self._points if item.frame == int(frame)), None)

    def nearest(self, frame: int, radius: int) -> AutomationPoint | None:
        """The breakpoint within ``radius`` frames of ``frame``, if there is one."""
        candidates = [
            item for item in self._points if abs(item.frame - int(frame)) <= max(int(radius), 0)
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda item: abs(item.frame - int(frame)))

    def value_at(self, frame: int) -> float:
        """Interpolated value at one frame; 0 dB when the curve is empty."""
        if not self._points:
            return 0.0
        return float(self.values(int(frame), 1)[0])

    def values(self, start: int, n_frames: int) -> np.ndarray:
        """The curve sampled over ``[start, start + n_frames)``, in dB."""
        count = max(int(n_frames), 0)
        if not self._points:
            return np.zeros(count, dtype=SAMPLE_DTYPE)
        frames = np.arange(int(start), int(start) + count, dtype=np.float64)
        breakpoints = np.fromiter(
            (item.frame for item in self._points), dtype=np.float64, count=len(self._points)
        )
        levels = np.fromiter(
            (item.value for item in self._points), dtype=np.float64, count=len(self._points)
        )
        return np.interp(frames, breakpoints, levels).astype(SAMPLE_DTYPE)

    def amplitudes(self, start: int, n_frames: int) -> np.ndarray:
        """The curve sampled as linear factors, ready to multiply a block by."""
        return gain_curve_to_amplitude(self.values(start, n_frames))

    @property
    def silent(self) -> bool:
        """True when every breakpoint sits at or below silence.

        Interpolating between two silent points stays silent, so this is enough
        to know the whole curve is: no sample can escape between them.
        """
        return bool(self._points) and all(item.value <= SILENCE_DB for item in self._points)

    # -- serialization -----------------------------------------------------

    def to_json(self) -> list[list[float]]:
        return [point.to_json() for point in self._points]

    @classmethod
    def from_json(cls, raw: Any) -> GainAutomation:
        """Read a curve back, accepting ``[frame, value]`` pairs or objects.

        Anything that is not a readable breakpoint is skipped rather than
        raising: a mangled point costs the arrangement one node, and refusing
        the whole project over it would cost the user everything else.
        """
        if not isinstance(raw, Sequence) or isinstance(raw, str | bytes):
            return cls()
        points: list[AutomationPoint] = []
        for item in raw:
            if isinstance(item, Mapping):
                frame, value = item.get("frame"), item.get("value")
            elif isinstance(item, Sequence) and not isinstance(item, str | bytes):
                if len(item) < 2:
                    continue
                frame, value = item[0], item[1]
            else:
                continue
            try:
                points.append(AutomationPoint(int(frame), float(value)))  # type: ignore[arg-type]
            except (TypeError, ValueError):
                continue
        return cls(points)

    # -- plumbing ----------------------------------------------------------

    def _replace(self, points: tuple[AutomationPoint, ...]) -> None:
        if points != self._points:
            self._points = points
            if self._notify is not None:
                self._notify()

    def _bind(self, notify: Callable[[], None] | None) -> None:
        """Attach the owning track's invalidation hook (or detach on removal)."""
        self._notify = notify

    def __repr__(self) -> str:
        if not self._points:
            return "GainAutomation(off)"
        return (
            f"GainAutomation({len(self._points)} points, "
            f"{self._points[0].value:+.1f}..{self._points[-1].value:+.1f} dB)"
        )


def _sorted_points(
    points: Iterable[AutomationPoint | tuple[int, float]],
) -> tuple[AutomationPoint, ...]:
    """Coerce, de-duplicate by frame (last one wins) and order a set of points."""
    by_frame: dict[int, AutomationPoint] = {}
    for item in points:
        point = item if isinstance(item, AutomationPoint) else AutomationPoint(*item)
        by_frame[point.frame] = point
    return tuple(by_frame[frame] for frame in sorted(by_frame))


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

    __slots__ = (
        "_automation",
        "_clips",
        "_gain_db",
        "_mute",
        "_name",
        "_notify",
        "_pan",
        "_send_to_bus",
        "_solo",
        "_track_id",
    )

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
        send_to_bus: str | None = None,
        automation: GainAutomation | Iterable[AutomationPoint | tuple[int, float]] = (),
    ) -> None:
        self._track_id = track_id or f"trk_{next(_track_counter):02d}"
        self._name = name or self._track_id
        self._clips: list[Clip] = sorted(clips, key=lambda clip: clip.start)
        self._gain_db = float(gain_db)
        self._pan = float(min(max(pan, -1.0), 1.0))
        self._mute = bool(mute)
        self._solo = bool(solo)
        self._send_to_bus = _bus_id_of(send_to_bus)
        self._notify: Callable[[], None] | None = None
        self._automation = (
            automation if isinstance(automation, GainAutomation) else GainAutomation(automation)
        )
        self._automation._bind(self._touch)  # noqa: SLF001 - the track owns its curve

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

    # -- automation --------------------------------------------------------

    @property
    def automation(self) -> GainAutomation:
        """This lane's gain envelope. Empty means the static fader is in charge."""
        return self._automation

    @automation.setter
    def automation(
        self, value: GainAutomation | Iterable[AutomationPoint | tuple[int, float]] | None
    ) -> None:
        if isinstance(value, GainAutomation):
            self._automation._bind(None)  # noqa: SLF001 - detach the old curve
            self._automation = value
            self._automation._bind(self._touch)  # noqa: SLF001 - and adopt the new one
            self._touch()
        else:
            self._automation.set_points(value or ())

    @property
    def has_automation(self) -> bool:
        return not self._automation.is_empty

    @property
    def silent(self) -> bool:
        """True when nothing on this lane can reach the mix at any frame."""
        if self._automation.is_empty:
            return self.amplitude == 0.0
        return self._automation.silent

    def effective_gain_db(self, frame: int = 0) -> float:
        """The fader position actually in force at ``frame``.

        Automation *replaces* the fader rather than trimming it, which is what
        makes the envelope readable: a breakpoint at -6 dB means the lane plays
        at -6 dB, not at -6 dB below wherever the fader happens to be sitting.
        """
        if self._automation.is_empty:
            return self._gain_db
        return self._automation.value_at(frame)

    def seed_automation(self, value: float | None = None) -> GainAutomation:
        """Lay down a flat envelope so there is something to drag.

        The breakpoints land on the clip boundaries — the frames an edit is
        most likely to want a level change at — and all hold the fader's
        current position, so switching automation on is inaudible. A lane with
        nothing on it gets a plain two-point line instead.
        """
        level = self._gain_db if value is None else float(value)
        edges = sorted({frame for clip in self._clips for frame in (clip.start, clip.end)})
        if len(edges) < 2:
            edges = [0, max(self.n_frames, 1)]
        self._automation.flat(edges, level)
        return self._automation

    def gain_envelope(self, start: int, n_frames: int) -> np.ndarray | None:
        """Per-frame linear gain for a block, or ``None`` when not automated."""
        if self._automation.is_empty or n_frames <= 0:
            return None
        return self._automation.amplitudes(start, n_frames)

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

    # -- routing -----------------------------------------------------------

    @property
    def send_to_bus(self) -> str | None:
        """Id of the bus this lane feeds, or ``None`` for straight to master.

        Only the id is held, not the bus itself, so a routing target that has
        been deleted — or one restored from a project before its buses were
        rebuilt — degrades to "goes to master" instead of dangling.
        """
        return self._send_to_bus

    @send_to_bus.setter
    def send_to_bus(self, value: str | Bus | None) -> None:
        bus_id = _bus_id_of(value)
        if bus_id != self._send_to_bus:
            self._send_to_bus = bus_id
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

    def apply_fader(self, block: np.ndarray, start: int | None = None) -> np.ndarray:
        """Scale a rendered block in place by this track's gain and pan.

        Unity gain at centre pan is a no-op by construction, not by rounding:
        the block is returned untouched so an unaltered track sums bit-exactly.

        ``start`` is the block's first frame on the timeline. It is only needed
        by an automated lane, whose envelope has to be sampled at the right
        place; a caller that has no timeline position simply gets the static
        fader, which is also what an un-automated lane gets either way.
        """
        left, right = pan_gains(self._pan)
        envelope = None if start is None else self.gain_envelope(start, int(block.shape[0]))
        if envelope is not None:
            # Multiplying by an exact 1.0 is bit-transparent, so a curve parked
            # at unity still nulls against its own source.
            if block.shape[1] == 2 and (left != 1.0 or right != 1.0):
                block[:, 0] *= envelope * SAMPLE_DTYPE(left)
                block[:, 1] *= envelope * SAMPLE_DTYPE(right)
            else:
                block *= envelope[:, np.newaxis]
            return block

        amplitude = self.amplitude
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
        return out if pre_fader else self.apply_fader(out, int(start))

    def mix_into(self, out: np.ndarray, window_start: int) -> np.ndarray:
        """Add this lane, post-fader, into a shared summing buffer."""
        if not self._clips or self.silent:
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
        gain = (
            f"{len(self._automation)}-point auto"
            if self.has_automation
            else f"{self._gain_db:+.1f} dB"
        )
        return (
            f"Track({self._track_id!r}, {self._name!r}, {len(self._clips)} clips, "
            f"{gain}, pan {self._pan:+.2f}{', ' + flags if flags else ''})"
        )


# -------------------------------------------------------------------- bus


class SummingPoint:
    """A named fader and mute that a group of signals is summed through.

    Both the master and the submix buses are this plus an identity, and the
    mixer only ever asks them for :meth:`apply`, so adding a bus level to the
    signal path did not need a second implementation of "scale or silence a
    block".
    """

    __slots__ = ("_gain_db", "_mute", "_name", "_notify")

    def __init__(self, name: str = "", *, gain_db: float = 0.0, mute: bool = False) -> None:
        self._name = name
        self._gain_db = float(gain_db)
        self._mute = bool(mute)
        self._notify: Callable[[], None] | None = None

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        text = str(value)
        if text != self._name:
            self._name = text
            self._touch()

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

    @property
    def silent(self) -> bool:
        """True when nothing routed here can reach the mix."""
        return self._mute or self.amplitude == 0.0

    def apply(self, block: np.ndarray) -> np.ndarray:
        """Scale a summed block in place by this fader."""
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
        return f"{type(self).__name__}({self._name!r}, {self._gain_db:+.1f} dB{state})"


class MasterBus(SummingPoint):
    """Terminal summing point: every audible track and bus lands here.

    Kept as a class rather than two attributes on the session because it is the
    seat the master effect rack, the master meter and the submix buses plug
    into — the mixer already calls :meth:`apply` at exactly the right point in
    the signal path.
    """

    __slots__ = ()

    def __init__(self, name: str = "Master", *, gain_db: float = 0.0, mute: bool = False) -> None:
        super().__init__(name, gain_db=gain_db, mute=mute)


class Bus(SummingPoint):
    """A submix the tracks routed to it are summed through before the master.

    The routing model is deliberately one level deep: a track sends to at most
    one bus, and a bus always lands on the master. There are no bus-to-bus
    sends, which means the signal path can never contain a cycle and the mixer
    needs no graph traversal — one pass over the tracks fills the submix
    buffers, one pass over the buses folds them into the master sum.
    """

    __slots__ = ("_bus_id",)

    def __init__(
        self,
        bus_id: str = "",
        name: str = "",
        *,
        gain_db: float = 0.0,
        mute: bool = False,
    ) -> None:
        self._bus_id = bus_id or f"bus_{next(_bus_counter):02d}"
        super().__init__(name or self._bus_id, gain_db=gain_db, mute=mute)

    @property
    def bus_id(self) -> str:
        return self._bus_id

    #: Alias for :attr:`bus_id`, matching the ``id`` field in the project schema.
    @property
    def id(self) -> str:  # noqa: A003 - the schema calls this field "id"
        return self._bus_id

    def __repr__(self) -> str:
        state = ", muted" if self.mute else ""
        return f"Bus({self._bus_id!r}, {self.name!r}, {self.gain_db:+.1f} dB{state})"


# ------------------------------------------------------------------ mixer


class SessionMixer(BaseSampleSource):
    """Renders a :class:`MultitrackSession` as a plain sample source.

    Summing order is: each audible track's clips accumulate into a per-track
    buffer, the track fader (or its automation curve, interpolated across the
    block being rendered) and pan scale it, the result is added to the buffer
    of the bus it is sent to (or straight to the master sum when it is not sent
    anywhere), each bus fader scales its submix into the master sum, and the
    master fader scales the total. Nothing about this needs the transport, so
    the same object serves live playback, offline mixdown and the loudness
    meter.

    A session with no buses takes the direct path, so the one-track null test
    still passes through zero extra arithmetic.
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

    def _sum_into(self, out: np.ndarray, start: int) -> None:
        """Accumulate every audible track into ``out``, via its bus if it has one."""
        session = self._session
        grouped: dict[str, list[Track]] = {}
        for track in session.audible_tracks():
            bus = session.bus_of(track)
            if bus is None:
                track.mix_into(out, start)
            else:
                grouped.setdefault(bus.bus_id, []).append(track)

        for bus_id, tracks in grouped.items():
            bus = session.bus(bus_id)
            if bus is None or bus.silent:
                continue
            submix = np.zeros_like(out)
            for track in tracks:
                track.mix_into(submix, start)
            out += bus.apply(submix)

    def read(self, start: int, n_frames: int) -> np.ndarray:
        start, count = self._clamp(start, n_frames)
        if count == 0:
            return self._empty()
        out = np.zeros((count, self._session.n_channels), dtype=SAMPLE_DTYPE)
        self._sum_into(out, start)
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
            self._sum_into(view, start)
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

    def render_buses(self, start: int, n_frames: int) -> dict[str, np.ndarray]:
        """Post-bus-fader submixes, keyed by bus id — the basis for bus meters.

        This is what each bus actually contributes to the master, so muted and
        solo-dimmed lanes are left out. A bus nobody is routed to renders as
        silence rather than being omitted, so a meter bank built from these
        keys keeps its shape as tracks are rerouted underneath it.
        """
        session = self._session
        start, count = self._clamp(start, n_frames)
        channels = session.n_channels
        audible = set(session.audible_tracks())
        stems: dict[str, np.ndarray] = {}
        for bus in session.buses:
            submix = np.zeros((count, channels), dtype=SAMPLE_DTYPE)
            for track in session.tracks_for_bus(bus):
                if track in audible:
                    track.mix_into(submix, start)
            stems[bus.bus_id] = bus.apply(submix)
        return stems

    def mixdown(self, rng: TimeRange | None = None) -> AudioBuffer:
        """Render the whole session (or one range) into memory."""
        span = TimeRange(0, self.n_frames) if rng is None else rng.clamped(self.n_frames)
        return AudioBuffer(self.read(span.start, span.length), self.sample_rate)

    def __repr__(self) -> str:
        return f"SessionMixer({self._session!r})"


# ---------------------------------------------------------------- session


class MultitrackSession:
    """The non-destructive arrangement: tracks, their clips, buses and a master.

    Every structural change bumps :attr:`revision` and notifies listeners, which
    is how the multitrack view knows to drop its cached waveform strips without
    the model importing a single Qt symbol.
    """

    __slots__ = (
        "_buses",
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
        self._buses: list[Bus] = []
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

    # -- buses -------------------------------------------------------------

    @property
    def buses(self) -> tuple[Bus, ...]:
        return tuple(self._buses)

    @property
    def n_buses(self) -> int:
        return len(self._buses)

    def add_bus(self, bus: Bus | str | None = None, **kwargs: object) -> Bus:
        """Append a submix bus; ``add_bus("Drums")`` builds one from a name."""
        if not isinstance(bus, Bus):
            bus = Bus(name=bus or "", **kwargs)  # type: ignore[arg-type]
        with self._lock:
            if any(existing.bus_id == bus.bus_id for existing in self._buses):
                raise ValueError(f"duplicate bus id {bus.bus_id!r}")
            bus._bind(self._touch)  # noqa: SLF001 - the session owns its buses
            self._buses.append(bus)
            self._touch()
        return bus

    def remove_bus(self, bus: Bus | str) -> bool:
        """Delete a bus, returning every track that fed it to the master."""
        bus_id = bus if isinstance(bus, str) else bus.bus_id
        with self._lock:
            for index, existing in enumerate(self._buses):
                if existing.bus_id == bus_id:
                    existing._bind(None)  # noqa: SLF001 - detach on removal
                    del self._buses[index]
                    for track in self._tracks:
                        if track.send_to_bus == bus_id:
                            track.send_to_bus = None
                    self._touch()
                    return True
        return False

    def bus(self, bus_id: str) -> Bus | None:
        return next((item for item in self._buses if item.bus_id == bus_id), None)

    def bus_of(self, track: Track | str) -> Bus | None:
        """The bus a track feeds, or ``None`` when it goes straight to master.

        A send pointing at a bus that no longer exists reads as ``None`` here
        rather than raising, so deleting a bus can never silence a lane.
        """
        lane = self.track(track) if isinstance(track, str) else track
        if lane is None or lane.send_to_bus is None:
            return None
        return self.bus(lane.send_to_bus)

    def tracks_for_bus(self, bus: Bus | str) -> tuple[Track, ...]:
        bus_id = bus if isinstance(bus, str) else bus.bus_id
        return tuple(track for track in self._tracks if track.send_to_bus == bus_id)

    def route_track(self, track: Track | str, bus: Bus | str | None) -> None:
        """Send ``track`` to ``bus``, or to the master when ``bus`` is ``None``."""
        lane = self.track(track) if isinstance(track, str) else track
        if lane is None or lane not in self._tracks:
            raise KeyError(f"no such track: {track!r}")
        bus_id = _bus_id_of(bus)
        if bus_id is not None and self.bus(bus_id) is None:
            raise KeyError(f"no such bus: {bus!r}")
        lane.send_to_bus = bus_id

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

    def render_buses(self, start: int, n_frames: int) -> dict[str, np.ndarray]:
        return self._mixer.render_buses(start, n_frames)

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
        buses = f"{len(self._buses)} buses, " if self._buses else ""
        return (
            f"MultitrackSession({self._name!r}, {len(self._tracks)} tracks, {buses}"
            f"{self.n_frames} frames, {self._channels}ch @ {self._sample_rate} Hz, "
            f"rev {self._revision})"
        )


__all__ = [
    "MAX_GAIN_DB",
    "SILENCE_DB",
    "AutomationPoint",
    "Bus",
    "Clip",
    "GainAutomation",
    "MasterBus",
    "MultitrackSession",
    "SessionMixer",
    "SummingPoint",
    "Track",
    "conform_channels",
    "gain_curve_to_amplitude",
    "gain_to_amplitude",
    "pan_gains",
]
