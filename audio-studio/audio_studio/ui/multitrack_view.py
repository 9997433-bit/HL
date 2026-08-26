"""Multitrack workspace: one strip per track, stacked against a shared timeline.

The waveform editor shows one clip at maximum detail. This view shows the
*arrangement*: every track gets a lane, every lane draws its clips at the frame
they were placed on, and every lane shares the ruler, the zoom and the playhead
with all the others. That shared timeline is the whole point — a clip that
looks aligned here is aligned, because the pixel it starts on is computed from
the same ``view_start``/``view_frames`` pair for every strip on screen.

Nothing here owns audio. The strips read
:class:`~audio_studio.core.session.MultitrackSession` and write back to it
through the same property setters a script would use, and the session's
revision counter is what tells a lane its cached waveform is stale. Repaints
are therefore cheap: a mute click redraws one lane's overlay, not the mix.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QScrollBar,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..core.peaks import PeakPyramid
from ..core.session import MAX_GAIN_DB, Clip, MultitrackSession, Track
from ..core.types import format_timecode
from .theme import PALETTE, Palette
from .time_ruler import TimeRuler

#: Width of the track header column. Matches the waveform editor's lane header
#: so the two workspaces line up when you switch between them.
HEADER_WIDTH: int = 200

#: Height of one track lane, in pixels.
LANE_HEIGHT: int = 76

#: Quietest fader position the strip exposes. The model floors at -96 dB, but a
#: slider that spends half its travel below audibility is a bad control.
MIN_STRIP_DB: float = -60.0

#: Frames above which a clip is drawn as a plain block instead of a waveform.
#: Summarising a source costs one full read; past this length that read belongs
#: on a worker with a cache behind it, which is a later milestone.
MAX_SUMMARY_FRAMES: int = 120 * 48_000

#: Colours cycled through so adjacent lanes stay visually distinct.
CLIP_COLORS: tuple[str, ...] = (
    "#4fc3f7",
    "#81c784",
    "#ffb74d",
    "#ba68c8",
    "#4db6ac",
    "#f06292",
)


@dataclass(frozen=True, slots=True)
class _LaneKey:
    """Everything a lane's cached pixmap depends on."""

    revision: int
    view_start: int
    view_frames: int
    width: int
    height: int


class ClipLane(QWidget):
    """One track's clips drawn against the shared timeline.

    The rendered strip is cached into a pixmap and only rebuilt when the
    session revision, the visible range or the widget size changes, so dragging
    the playhead across a 32-track arrangement blits rather than re-summarises.
    """

    seekRequested = Signal(int)

    def __init__(
        self,
        track: Track | None = None,
        *,
        color: str = CLIP_COLORS[0],
        palette: Palette = PALETTE,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._palette = palette
        self._track = track
        self._session: MultitrackSession | None = None
        self._color = QColor(color)
        self._sample_rate = 44_100
        self._view_start = 0
        self._view_frames = 0
        self._playhead = 0
        self._revision = 0
        self._summaries: dict[int, PeakPyramid | None] = {}
        self._cache: QPixmap | None = None
        self._cache_key: _LaneKey | None = None

        self.setMinimumHeight(LANE_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(LANE_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    # ------------------------------------------------------------- contents

    @property
    def track(self) -> Track | None:
        return self._track

    def set_track(self, track: Track | None, *, sample_rate: int = 44_100) -> None:
        self._track = track
        self._sample_rate = max(int(sample_rate), 1)
        self._summaries.clear()
        self._invalidate()

    def set_session(self, session: MultitrackSession | None) -> None:
        """Give the lane the session it belongs to, so it can dim under solo."""
        self._session = session
        self.update()

    def set_view(self, view_start: int, view_frames: int) -> None:
        self._view_start = max(0, int(view_start))
        self._view_frames = max(0, int(view_frames))
        self._invalidate()

    def set_revision(self, revision: int) -> None:
        """Tell the lane which arrangement it is looking at."""
        if revision != self._revision:
            self._revision = int(revision)
            self._invalidate()

    def set_playhead(self, frame: int) -> None:
        if int(frame) != self._playhead:
            self._playhead = int(frame)
            self.update()  # overlay only: the cached strip is still valid

    # -------------------------------------------------------------- mapping

    def frame_to_x(self, frame: float) -> float:
        if self._view_frames <= 0:
            return 0.0
        return (frame - self._view_start) * self.width() / self._view_frames

    def x_to_frame(self, x: float) -> int:
        if self._view_frames <= 0 or self.width() <= 0:
            return 0
        return max(0, int(self._view_start + x * self._view_frames / self.width()))

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.LeftButton:
            self.seekRequested.emit(self.x_to_frame(event.position().x()))

    # ------------------------------------------------------------- painting

    def _invalidate(self) -> None:
        self._cache = None
        self._cache_key = None
        self.update()

    def _summary(self, clip: Clip) -> PeakPyramid | None:
        """Envelope pyramid for a clip's source, or ``None`` if too costly.

        Keyed by source identity rather than by clip, so ten clips sliced out of
        one recording share a single summary.
        """
        source = clip.source
        key = id(source)
        if key in self._summaries:
            return self._summaries[key]

        pyramid: PeakPyramid | None = None
        frames = int(source.n_frames)
        if 0 < frames <= MAX_SUMMARY_FRAMES and bool(getattr(source, "exact", True)):
            try:
                pyramid = PeakPyramid(source.read(0, frames))
            except Exception:  # noqa: BLE001 - an unreadable clip still draws as a block
                pyramid = None
        self._summaries[key] = pyramid
        return pyramid

    def paintEvent(self, _event: QPaintEvent) -> None:  # noqa: N802 - Qt override
        key = _LaneKey(
            self._revision, self._view_start, self._view_frames, self.width(), self.height()
        )
        if self._cache is None or self._cache_key != key:
            self._cache = self._render_strip()
            self._cache_key = key

        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._cache)

        track = self._track
        if track is not None and (track.mute or self._dimmed_by_solo()):
            painter.fillRect(self.rect(), QColor(0, 0, 0, 130))

        x = self.frame_to_x(self._playhead)
        if 0 <= x <= self.width():
            painter.setPen(QPen(self._palette.color("playhead"), 1))
            painter.drawLine(int(x), 0, int(x), self.height())
        painter.end()

    def _dimmed_by_solo(self) -> bool:
        """True when some other lane is soloed and this one is not."""
        track = self._track
        if track is None or track.solo:
            return False
        return self._session is not None and self._session.solo_active

    def _render_strip(self) -> QPixmap:
        pixmap = QPixmap(max(self.width(), 1), max(self.height(), 1))
        pixmap.fill(self._palette.color("waveform_bg"))

        painter = QPainter(pixmap)
        painter.setPen(QPen(self._palette.color("waveform_center"), 1))
        mid = self.height() // 2
        painter.drawLine(0, mid, self.width(), mid)

        if self._track is not None and self._view_frames > 0:
            for clip in self._track.clips:
                self._draw_clip(painter, clip)
        painter.end()
        return pixmap

    def _draw_clip(self, painter: QPainter, clip: Clip) -> None:
        x0 = self.frame_to_x(clip.start)
        x1 = self.frame_to_x(clip.end)
        if x1 < 0 or x0 > self.width() or clip.duration <= 0:
            return

        rect = QRectF(x0, 2.0, max(x1 - x0, 1.0), self.height() - 4.0)
        body = QColor(self._color)
        body.setAlpha(46)
        painter.fillRect(rect, body)
        painter.setPen(QPen(self._color.lighter(120), 1))
        painter.drawRect(rect)

        self._draw_envelope(painter, clip, x0, x1)

        if rect.width() > 48:
            painter.setPen(QPen(self._palette.color("text_dim"), 1))
            painter.drawText(
                int(rect.left()) + 4, int(rect.top()) + 12, clip.name[:32]
            )

    def _draw_envelope(self, painter: QPainter, clip: Clip, x0: float, x1: float) -> None:
        pyramid = self._summary(clip)
        if pyramid is None:
            return

        left = max(int(x0), 0)
        right = min(int(x1), self.width())
        n_bins = right - left
        if n_bins <= 0:
            return

        # Map the visible pixel band back onto the source, so a clip that is
        # scrolled half off-screen still draws the correct half of its audio.
        src_lo = clip.offset + (self.x_to_frame(left) - clip.start)
        src_hi = clip.offset + (self.x_to_frame(right) - clip.start)
        src_lo = max(src_lo, clip.offset)
        src_hi = min(max(src_hi, src_lo + 1), clip.offset + clip.duration)

        envelope = pyramid.envelope(src_lo, src_hi, n_bins)
        minima = envelope.minimum.min(axis=1)
        maxima = envelope.maximum.max(axis=1)

        mid = self.height() / 2.0
        half = (self.height() - 8) / 2.0
        tops = mid - np.clip(maxima, -1.0, 1.0) * half
        bottoms = mid - np.clip(minima, -1.0, 1.0) * half

        painter.setPen(QPen(self._color, 1))
        for index in range(n_bins):
            x = left + index
            top, bottom = float(tops[index]), float(bottoms[index])
            if bottom - top < 1.0:
                bottom = top + 1.0
            painter.drawLine(x, int(top), x, int(bottom))


class TrackHeaderStrip(QWidget):
    """Track head: name, mute/solo, fader and pan for one lane."""

    changed = Signal()

    def __init__(
        self,
        track: Track,
        *,
        palette: Palette = PALETTE,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._palette = palette
        self._track = track
        self._syncing = False

        self.setFixedWidth(HEADER_WIDTH)
        self.setFixedHeight(LANE_HEIGHT)
        self.setAutoFillBackground(True)
        self.setStyleSheet(
            f"background-color: {palette.surface}; border-right: 1px solid {palette.border};"
        )

        self.title = QLabel(track.name)
        self.title.setObjectName("TrackTitle")
        self.title.setToolTip(track.track_id)

        self.mute_button = QPushButton("M")
        self.mute_button.setCheckable(True)
        self.mute_button.setFixedSize(24, 20)
        self.mute_button.setToolTip("Mute this track")
        self.solo_button = QPushButton("S")
        self.solo_button.setCheckable(True)
        self.solo_button.setFixedSize(24, 20)
        self.solo_button.setToolTip("Solo: mute every track that is not soloed")

        self.gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.gain_slider.setRange(int(MIN_STRIP_DB), int(MAX_GAIN_DB))
        self.gain_slider.setFixedWidth(84)
        self.gain_slider.setToolTip("Track gain")
        self.gain_label = QLabel("0.0 dB")
        self.gain_label.setObjectName("SecondaryTimecode")
        self.gain_label.setFixedWidth(52)

        self.pan_slider = QSlider(Qt.Orientation.Horizontal)
        self.pan_slider.setRange(-100, 100)
        self.pan_slider.setFixedWidth(84)
        self.pan_slider.setToolTip("Pan")
        self.pan_label = QLabel("C")
        self.pan_label.setObjectName("SecondaryTimecode")
        self.pan_label.setFixedWidth(52)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(4)
        top.addWidget(self.title, 1)
        top.addWidget(self.mute_button)
        top.addWidget(self.solo_button)

        gain_row = QHBoxLayout()
        gain_row.setContentsMargins(0, 0, 0, 0)
        gain_row.setSpacing(4)
        gain_row.addWidget(self.gain_slider)
        gain_row.addWidget(self.gain_label)

        pan_row = QHBoxLayout()
        pan_row.setContentsMargins(0, 0, 0, 0)
        pan_row.setSpacing(4)
        pan_row.addWidget(self.pan_slider)
        pan_row.addWidget(self.pan_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(2)
        layout.addLayout(top)
        layout.addLayout(gain_row)
        layout.addLayout(pan_row)

        self.mute_button.toggled.connect(self._on_mute)
        self.solo_button.toggled.connect(self._on_solo)
        self.gain_slider.valueChanged.connect(self._on_gain)
        self.pan_slider.valueChanged.connect(self._on_pan)

        self.refresh()

    @property
    def track(self) -> Track:
        return self._track

    def refresh(self) -> None:
        """Pull the model's current state back into the widgets.

        Guarded because assigning to a slider emits ``valueChanged``, which
        would write the value straight back into the model and, on a rounded
        value, fight the user's next drag.
        """
        self._syncing = True
        try:
            self.title.setText(self._track.name)
            self.mute_button.setChecked(self._track.mute)
            self.solo_button.setChecked(self._track.solo)
            self.gain_slider.setValue(int(round(self._track.gain_db)))
            self.pan_slider.setValue(int(round(self._track.pan * 100)))
        finally:
            self._syncing = False
        self._update_labels()

    def _update_labels(self) -> None:
        self.gain_label.setText(f"{self._track.gain_db:+.1f} dB")
        pan = self._track.pan
        if abs(pan) < 0.005:
            self.pan_label.setText("C")
        else:
            side = "L" if pan < 0 else "R"
            self.pan_label.setText(f"{side}{abs(pan) * 100:.0f}")

    def _on_mute(self, checked: bool) -> None:
        if self._syncing:
            return
        self._track.mute = checked
        self.changed.emit()

    def _on_solo(self, checked: bool) -> None:
        if self._syncing:
            return
        self._track.solo = checked
        self.changed.emit()

    def _on_gain(self, value: int) -> None:
        if self._syncing:
            return
        self._track.gain_db = float(value)
        self._update_labels()
        self.changed.emit()

    def _on_pan(self, value: int) -> None:
        if self._syncing:
            return
        self._track.pan = value / 100.0
        self._update_labels()
        self.changed.emit()


class TrackStrip(QWidget):
    """A track header and its clip lane, side by side."""

    seekRequested = Signal(int)
    changed = Signal()

    def __init__(
        self,
        track: Track,
        *,
        color: str = CLIP_COLORS[0],
        session: MultitrackSession | None = None,
        palette: Palette = PALETTE,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._track = track
        self.header = TrackHeaderStrip(track, palette=palette)
        self.lane = ClipLane(track, color=color, palette=palette)
        self.lane.set_track(
            track, sample_rate=session.sample_rate if session is not None else 44_100
        )
        self.lane.set_session(session)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.header)
        layout.addWidget(self.lane, 1)
        self.setFixedHeight(LANE_HEIGHT)

        self.lane.seekRequested.connect(self.seekRequested)
        self.header.changed.connect(self.changed)

    @property
    def track(self) -> Track:
        return self._track

    def set_view(self, view_start: int, view_frames: int) -> None:
        self.lane.set_view(view_start, view_frames)

    def set_playhead(self, frame: int) -> None:
        self.lane.set_playhead(frame)

    def refresh(self, revision: int) -> None:
        self.header.refresh()
        self.lane.set_revision(revision)


class MasterStrip(QWidget):
    """The master bus fader, pinned under the tracks."""

    changed = Signal()

    def __init__(
        self,
        session: MultitrackSession | None = None,
        *,
        palette: Palette = PALETTE,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._session = session
        self._syncing = False
        self.setFixedHeight(32)
        self.setAutoFillBackground(True)
        self.setStyleSheet(
            f"background-color: {palette.surface}; border-top: 1px solid {palette.border};"
        )

        self.title = QLabel("MASTER")
        self.title.setObjectName("TrackTitle")
        self.title.setFixedWidth(HEADER_WIDTH - 76)

        self.mute_button = QPushButton("M")
        self.mute_button.setCheckable(True)
        self.mute_button.setFixedSize(24, 20)
        self.mute_button.setToolTip("Mute the master bus")

        self.gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.gain_slider.setRange(int(MIN_STRIP_DB), int(MAX_GAIN_DB))
        self.gain_slider.setFixedWidth(120)
        self.gain_label = QLabel("0.0 dB")
        self.gain_label.setObjectName("SecondaryTimecode")
        self.gain_label.setFixedWidth(56)

        self.summary = QLabel("—")
        self.summary.setObjectName("SecondaryTimecode")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)
        layout.addWidget(self.title)
        layout.addWidget(self.mute_button)
        layout.addWidget(self.gain_slider)
        layout.addWidget(self.gain_label)
        layout.addWidget(self.summary, 1)

        self.mute_button.toggled.connect(self._on_mute)
        self.gain_slider.valueChanged.connect(self._on_gain)
        self.refresh()

    def set_session(self, session: MultitrackSession | None) -> None:
        self._session = session
        self.refresh()

    def refresh(self) -> None:
        session = self._session
        self.setEnabled(session is not None)
        if session is None:
            self.summary.setText("No session")
            return
        self._syncing = True
        try:
            self.mute_button.setChecked(session.master.mute)
            self.gain_slider.setValue(int(round(session.master.gain_db)))
        finally:
            self._syncing = False
        self.gain_label.setText(f"{session.master.gain_db:+.1f} dB")
        soloed = sum(1 for track in session.tracks if track.solo)
        self.summary.setText(
            f"{session.n_tracks} tracks  ·  {format_timecode(session.duration)}"
            + (f"  ·  {soloed} soloed" if soloed else "")
        )

    def _on_mute(self, checked: bool) -> None:
        if self._syncing or self._session is None:
            return
        self._session.master.mute = checked
        self.changed.emit()

    def _on_gain(self, value: int) -> None:
        if self._syncing or self._session is None:
            return
        self._session.master.gain_db = float(value)
        self.gain_label.setText(f"{self._session.master.gain_db:+.1f} dB")
        self.changed.emit()


class MultitrackView(QWidget):
    """The multitrack workspace: ruler, stacked track strips and a master strip."""

    seekRequested = Signal(int)
    sessionChanged = Signal()

    def __init__(
        self,
        session: MultitrackSession | None = None,
        *,
        palette: Palette = PALETTE,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._palette = palette
        self._session: MultitrackSession | None = None
        self._strips: list[TrackStrip] = []
        self._view_start = 0
        self._view_frames = 0
        self._playhead = 0
        self._syncing = False

        self.ruler = TimeRuler(palette=palette)
        self.master_strip = MasterStrip(palette=palette)
        self.placeholder = QLabel("No tracks. Use View ▸ Add Clip as Track to start a session.")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setObjectName("SecondaryTimecode")

        self.scrollbar = QScrollBar(Qt.Orientation.Horizontal)
        self.scrollbar.setEnabled(False)

        self._strip_host = QWidget()
        self._strip_layout = QVBoxLayout(self._strip_host)
        self._strip_layout.setContentsMargins(0, 0, 0, 0)
        self._strip_layout.setSpacing(1)
        self._strip_layout.addWidget(self.placeholder)
        self._strip_layout.addStretch(1)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setWidget(self._strip_host)

        ruler_row = QHBoxLayout()
        ruler_row.setContentsMargins(0, 0, 0, 0)
        ruler_row.setSpacing(0)
        ruler_spacer = QFrame()
        ruler_spacer.setFixedWidth(HEADER_WIDTH)
        ruler_spacer.setFixedHeight(self.ruler.height())
        ruler_spacer.setStyleSheet(
            f"background-color: {palette.surface}; border-right: 1px solid {palette.border};"
        )
        ruler_row.addWidget(ruler_spacer)
        ruler_row.addWidget(self.ruler, 1)

        scroll_row = QHBoxLayout()
        scroll_row.setContentsMargins(0, 0, 0, 0)
        scroll_row.setSpacing(0)
        scroll_spacer = QFrame()
        scroll_spacer.setFixedWidth(HEADER_WIDTH)
        scroll_row.addWidget(scroll_spacer)
        scroll_row.addWidget(self.scrollbar, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(ruler_row)
        layout.addWidget(self._scroll_area, 1)
        layout.addLayout(scroll_row)
        layout.addWidget(self.master_strip)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.ruler.seekRequested.connect(self.seekRequested)
        self.scrollbar.valueChanged.connect(self._on_scroll)
        self.master_strip.changed.connect(self._on_model_edited)

        self.set_session(session)

    # --------------------------------------------------------------- session

    @property
    def session(self) -> MultitrackSession | None:
        return self._session

    @property
    def strips(self) -> tuple[TrackStrip, ...]:
        return tuple(self._strips)

    @property
    def n_frames(self) -> int:
        return self._session.n_frames if self._session is not None else 0

    def set_session(self, session: MultitrackSession | None) -> None:
        """Attach a session and rebuild the strips to match it."""
        if self._session is not None:
            self._session.remove_listener(self._on_session_changed)
        self._session = session
        if session is not None:
            session.add_listener(self._on_session_changed)
            self.ruler.set_sample_rate(session.sample_rate)
        self.master_strip.set_session(session)
        self.rebuild()
        self.zoom_to_fit()

    def _on_session_changed(self, _session: MultitrackSession) -> None:
        """Model callback: the arrangement moved under us."""
        if len(self._strips) != (self._session.n_tracks if self._session else 0) or any(
            strip.track is not track
            for strip, track in zip(self._strips, self._session.tracks, strict=False)
        ):
            self.rebuild()
        else:
            self.refresh()

    def rebuild(self) -> None:
        """Discard the strips and build one per track."""
        for strip in self._strips:
            self._strip_layout.removeWidget(strip)
            strip.setParent(None)
            strip.deleteLater()
        self._strips.clear()

        session = self._session
        tracks = session.tracks if session is not None else ()
        self.placeholder.setVisible(not tracks)

        for index, track in enumerate(tracks):
            strip = TrackStrip(
                track,
                color=CLIP_COLORS[index % len(CLIP_COLORS)],
                session=session,
                palette=self._palette,
            )
            strip.seekRequested.connect(self.seekRequested)
            strip.changed.connect(self._on_model_edited)
            self._strip_layout.insertWidget(self._strip_layout.count() - 1, strip)
            self._strips.append(strip)

        self._apply_view()
        self.refresh()

    def refresh(self) -> None:
        """Re-read the model into the existing strips."""
        revision = self._session.revision if self._session is not None else 0
        for strip in self._strips:
            strip.refresh(revision)
        self.master_strip.refresh()

    def _on_model_edited(self) -> None:
        self.refresh()
        self.sessionChanged.emit()

    # ------------------------------------------------------------------ view

    @property
    def view_start(self) -> int:
        return self._view_start

    @property
    def view_frames(self) -> int:
        return self._view_frames

    def set_view(self, view_start: int, view_frames: int) -> None:
        total = max(self.n_frames, 1)
        frames = max(1, min(int(view_frames), total))
        start = max(0, min(int(view_start), total - frames))
        self._view_start, self._view_frames = start, frames
        self._apply_view()

    def zoom_to_fit(self) -> None:
        self.set_view(0, max(self.n_frames, 1))

    def zoom_by(self, factor: float, anchor: int | None = None) -> None:
        """Scale the visible span, keeping ``anchor`` under the same pixel."""
        if self._view_frames <= 0:
            return
        pivot = self._playhead if anchor is None else int(anchor)
        pivot = max(self._view_start, min(pivot, self._view_start + self._view_frames))
        ratio = (pivot - self._view_start) / max(self._view_frames, 1)
        frames = max(1, int(round(self._view_frames * float(factor))))
        self.set_view(pivot - int(round(ratio * frames)), frames)

    def zoom_in(self) -> None:
        self.zoom_by(0.5)

    def zoom_out(self) -> None:
        self.zoom_by(2.0)

    def scroll_to(self, view_start: int) -> None:
        self.set_view(view_start, self._view_frames)

    def set_playhead(self, frame: int) -> None:
        self._playhead = max(0, int(frame))
        self.ruler.set_playhead(self._playhead)
        for strip in self._strips:
            strip.set_playhead(self._playhead)

    def _apply_view(self) -> None:
        self.ruler.set_view(self._view_start, self._view_frames)
        for strip in self._strips:
            strip.set_view(self._view_start, self._view_frames)

        total = self.n_frames
        self._syncing = True
        try:
            if total > self._view_frames > 0:
                self.scrollbar.setEnabled(True)
                self.scrollbar.setRange(0, total - self._view_frames)
                self.scrollbar.setPageStep(self._view_frames)
                self.scrollbar.setSingleStep(max(self._view_frames // 20, 1))
                self.scrollbar.setValue(self._view_start)
            else:
                self.scrollbar.setEnabled(False)
                self.scrollbar.setRange(0, 0)
        finally:
            self._syncing = False

    def _on_scroll(self, value: int) -> None:
        if not self._syncing:
            self.scroll_to(value)


__all__ = [
    "CLIP_COLORS",
    "HEADER_WIDTH",
    "LANE_HEIGHT",
    "MAX_SUMMARY_FRAMES",
    "MIN_STRIP_DB",
    "ClipLane",
    "MasterStrip",
    "MultitrackView",
    "TrackHeaderStrip",
    "TrackStrip",
]
