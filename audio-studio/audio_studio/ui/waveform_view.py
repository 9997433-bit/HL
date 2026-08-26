"""Interactive waveform display.

Rendering goes through the clip's :class:`~audio_studio.core.peaks.PeakPyramid`,
so a repaint costs O(widget width) regardless of clip length. Below roughly
four pixels per sample the view switches from a min/max envelope to a true
sample-connected polyline, matching what an editor is expected to show when you
zoom all the way in.

The static waveform is cached into a :class:`QPixmap` and only re-rendered when
the clip, the visible range or the widget size changes; playhead, selection and
marker updates just blit the cache and draw the overlays on top.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import QPoint, QRect, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFontMetrics,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPixmap,
    QPolygon,
    QResizeEvent,
    QWheelEvent,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..core.markers import MarkerList
from ..core.peaks import PeakPyramid
from ..core.types import TimeRange
from .theme import PALETTE, Palette

#: Smallest visible span, in frames, to keep the zoom from collapsing.
MIN_VIEW_FRAMES: int = 32

#: Pixels per sample above which individual samples are drawn as a polyline.
SAMPLE_MODE_PPS: float = 4.0

#: Drag distance, in pixels, below which a press counts as a click, not a selection.
SELECTION_DRAG_SLOP: int = 3

#: Height of the strip along the top where marker and region flags are drawn.
MARKER_FLAG_HEIGHT: int = 14

#: Widest a flag label is allowed to get before it is elided.
MARKER_LABEL_MAX_WIDTH: int = 140


@dataclass(frozen=True, slots=True)
class _CacheKey:
    clip_id: int
    view_start: int
    view_frames: int
    width: int
    height: int
    amplitude_scale: float
    channels: int


class WaveformView(QWidget):
    """Scrollable, zoomable, selectable waveform canvas."""

    seekRequested = Signal(int)
    selectionChanged = Signal(object)  # TimeRange | None
    viewChanged = Signal(int, int)  # view_start, view_frames
    cursorMoved = Signal(int)

    def __init__(self, parent: QWidget | None = None, palette: Palette = PALETTE) -> None:
        super().__init__(parent)
        self._palette = palette

        self._pyramid: PeakPyramid | None = None
        self._samples: np.ndarray | None = None
        self._sample_rate = 44100
        self._n_frames = 0

        self._view_start = 0
        self._view_frames = 0
        self._amplitude_scale = 1.0

        self._selection: TimeRange | None = None
        self._playhead = 0.0
        self._cursor_frame = 0
        self._markers = MarkerList()

        self._drag_anchor: int | None = None
        self._drag_origin_x: int | None = None
        self._pan_anchor: tuple[int, int] | None = None
        self._cache: QPixmap | None = None
        self._cache_key: _CacheKey | None = None

        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAutoFillBackground(False)
        self.setCursor(Qt.CursorShape.IBeamCursor)

    # ------------------------------------------------------------------ clip

    def set_clip(
        self,
        pyramid: PeakPyramid | None,
        sample_rate: int = 44100,
        samples: np.ndarray | None = None,
    ) -> None:
        """Attach a clip's envelope pyramid (and raw samples for sample-level zoom)."""
        self._pyramid = pyramid
        self._samples = samples
        self._sample_rate = max(int(sample_rate), 1)
        self._n_frames = pyramid.n_frames if pyramid is not None else 0
        self._selection = None
        self._playhead = 0.0
        self._cursor_frame = 0
        self._invalidate_cache()
        self.zoom_to_fit()
        self.selectionChanged.emit(None)

    def clear(self) -> None:
        self.set_clip(None)

    @property
    def n_frames(self) -> int:
        return self._n_frames

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def has_clip(self) -> bool:
        return self._pyramid is not None and self._n_frames > 0

    # ------------------------------------------------------------ view range

    @property
    def view_start(self) -> int:
        return self._view_start

    @property
    def view_frames(self) -> int:
        return self._view_frames

    @property
    def view_end(self) -> int:
        return self._view_start + self._view_frames

    @property
    def view_range(self) -> TimeRange:
        return TimeRange(self._view_start, min(self.view_end, max(self._n_frames, 0)))

    @property
    def pixels_per_frame(self) -> float:
        if self._view_frames <= 0:
            return 0.0
        return self.width() / self._view_frames

    def set_view(self, start: int, frames: int, *, emit: bool = True) -> None:
        """Set the visible window, clamped to the clip and to the zoom limits."""
        if self._n_frames <= 0:
            changed = self._view_start != 0 or self._view_frames != 0
            self._view_start, self._view_frames = 0, 0
            if changed and emit:
                self.viewChanged.emit(0, 0)
            self._invalidate_cache()
            self.update()
            return

        frames = int(max(min(int(frames), self._n_frames), min(MIN_VIEW_FRAMES, self._n_frames)))
        start = int(max(0, min(int(start), self._n_frames - frames)))
        if start == self._view_start and frames == self._view_frames:
            return

        self._view_start, self._view_frames = start, frames
        self._invalidate_cache()
        self.update()
        if emit:
            self.viewChanged.emit(start, frames)

    def zoom_to_fit(self) -> None:
        self.set_view(0, max(self._n_frames, MIN_VIEW_FRAMES))

    def zoom_to_selection(self) -> None:
        if self._selection is None or self._selection.is_empty:
            return
        margin = max(self._selection.length // 20, 1)
        self.set_view(self._selection.start - margin, self._selection.length + 2 * margin)

    def zoom_by(self, factor: float, anchor_frame: int | None = None) -> None:
        """Multiply the visible span by ``factor``, holding ``anchor_frame`` in place."""
        if not self.has_clip or factor <= 0:
            return
        anchor = self._playhead if anchor_frame is None else anchor_frame
        anchor = max(self._view_start, min(anchor, self.view_end))
        ratio = (anchor - self._view_start) / max(self._view_frames, 1)
        new_frames = int(round(self._view_frames * factor))
        new_frames = max(min(new_frames, self._n_frames), MIN_VIEW_FRAMES)
        self.set_view(int(round(anchor - ratio * new_frames)), new_frames)

    def zoom_in(self) -> None:
        self.zoom_by(0.5, self._cursor_frame)

    def zoom_out(self) -> None:
        self.zoom_by(2.0, self._cursor_frame)

    def scroll_by(self, frames: int) -> None:
        self.set_view(self._view_start + frames, self._view_frames)

    def scroll_to(self, start: int) -> None:
        self.set_view(start, self._view_frames)

    def ensure_visible(self, frame: int, *, margin: float = 0.1) -> None:
        """Scroll so ``frame`` sits inside the view, page-flipping when it runs off."""
        if not self.has_clip or self._view_frames <= 0:
            return
        pad = int(self._view_frames * margin)
        if frame < self._view_start + pad:
            self.set_view(frame - pad, self._view_frames)
        elif frame > self.view_end - pad:
            self.set_view(frame - self._view_frames + pad, self._view_frames)

    @property
    def amplitude_scale(self) -> float:
        return self._amplitude_scale

    def set_amplitude_scale(self, scale: float) -> None:
        self._amplitude_scale = float(max(0.1, min(scale, 32.0)))
        self._invalidate_cache()
        self.update()

    # ------------------------------------------------------- selection/state

    @property
    def selection(self) -> TimeRange | None:
        return self._selection

    def set_selection(self, selection: TimeRange | None, *, emit: bool = True) -> None:
        normalised = None
        if selection is not None and not selection.is_empty:
            normalised = selection.clamped(self._n_frames)
            if normalised.is_empty:
                normalised = None
        if normalised == self._selection:
            return
        self._selection = normalised
        self.update()
        if emit:
            self.selectionChanged.emit(normalised)

    def select_all(self) -> None:
        if self.has_clip:
            self.set_selection(TimeRange(0, self._n_frames))

    def clear_selection(self) -> None:
        self.set_selection(None)

    @property
    def playhead(self) -> int:
        return int(self._playhead)

    @property
    def playhead_exact(self) -> float:
        """The playhead with its fractional part, as the transport reported it."""
        return self._playhead

    def set_playhead(self, frame: float, *, follow: bool = False) -> None:
        """Move the playhead to ``frame``, which may be fractional.

        A fraction of a frame is far below a pixel at any useful zoom, but it
        is what lets a 30 Hz repaint interpolate between device blocks instead
        of stepping between them.
        """
        frame = float(max(0.0, min(float(frame), float(self._n_frames))))
        if frame == self._playhead:
            return
        self._playhead = frame
        if follow:
            self.ensure_visible(int(frame))
        self.update()

    @property
    def markers(self) -> MarkerList:
        return self._markers

    def set_markers(self, markers: MarkerList | None) -> None:
        """Show ``markers`` as flags along the top of the canvas."""
        self._markers = markers if markers is not None else MarkerList()
        self.update()

    @property
    def cursor_frame(self) -> int:
        return self._cursor_frame

    def set_cursor_frame(self, frame: int, *, emit: bool = True) -> None:
        self._cursor_frame = int(max(0, min(frame, self._n_frames)))
        self.update()
        if emit:
            self.cursorMoved.emit(self._cursor_frame)

    # ------------------------------------------------------- coordinate math

    def frame_to_x(self, frame: float) -> float:
        if self._view_frames <= 0:
            return 0.0
        return (frame - self._view_start) * self.width() / self._view_frames

    def x_to_frame(self, x: float) -> int:
        if self._view_frames <= 0 or self.width() <= 0:
            return 0
        frame = self._view_start + x * self._view_frames / self.width()
        return int(max(0, min(round(frame), self._n_frames)))

    # ----------------------------------------------------------------- input

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        if not self.has_clip:
            return
        pos = event.position().toPoint()
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_anchor = (pos.x(), self._view_start)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return

        frame = self.x_to_frame(pos.x())
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier and self._selection is not None:
            anchor = (
                self._selection.end
                if abs(frame - self._selection.start) < abs(frame - self._selection.end)
                else self._selection.start
            )
        else:
            anchor = frame
        self._drag_anchor = anchor
        self._drag_origin_x = pos.x()
        self.set_cursor_frame(frame)
        if anchor != frame:
            self.set_selection(TimeRange(*sorted((anchor, frame))))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        pos = event.position().toPoint()
        if self._pan_anchor is not None:
            anchor_x, anchor_start = self._pan_anchor
            delta = int((anchor_x - pos.x()) * self._view_frames / max(self.width(), 1))
            self.set_view(anchor_start + delta, self._view_frames)
            return
        if self._drag_anchor is None or self._drag_origin_x is None:
            return
        if abs(pos.x() - self._drag_origin_x) < SELECTION_DRAG_SLOP:
            return
        frame = self.x_to_frame(pos.x())
        lo, hi = sorted((self._drag_anchor, frame))
        self.set_selection(TimeRange(lo, hi))

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_anchor = None
            self.setCursor(Qt.CursorShape.IBeamCursor)
            return
        if self._drag_anchor is None or self._drag_origin_x is None:
            return

        pos = event.position().toPoint()
        was_click = abs(pos.x() - self._drag_origin_x) < SELECTION_DRAG_SLOP
        self._drag_anchor = None
        self._drag_origin_x = None
        if was_click:
            frame = self.x_to_frame(pos.x())
            self.set_selection(None)
            self.seekRequested.emit(frame)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.LeftButton and self.has_clip:
            self.select_all()

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802 - Qt override
        if not self.has_clip:
            return
        steps = event.angleDelta().y() / 120.0
        if steps == 0:
            steps = event.angleDelta().x() / 120.0
        modifiers = event.modifiers()

        if modifiers & Qt.KeyboardModifier.ControlModifier:
            anchor = self.x_to_frame(event.position().toPoint().x())
            self.zoom_by(0.8**steps, anchor)
        elif modifiers & Qt.KeyboardModifier.AltModifier:
            self.set_amplitude_scale(self._amplitude_scale * (1.2**steps))
        else:
            self.scroll_by(int(-steps * self._view_frames * 0.15))
        event.accept()

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        self._invalidate_cache()

    # --------------------------------------------------------------- drawing

    def _invalidate_cache(self) -> None:
        self._cache = None
        self._cache_key = None

    def paintEvent(self, _event: QPaintEvent) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.fillRect(self.rect(), self._palette.color("waveform_bg"))

        if not self.has_clip or self.width() <= 0 or self.height() <= 0:
            self._paint_placeholder(painter)
            painter.end()
            return

        painter.drawPixmap(0, 0, self._waveform_pixmap())
        self._paint_regions(painter)
        self._paint_selection(painter)
        self._paint_markers(painter)
        self._paint_cursor(painter)
        self._paint_playhead(painter)
        painter.end()

    def _paint_placeholder(self, painter: QPainter) -> None:
        painter.setPen(self._palette.color("text_dim"))
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignCenter,
            "No audio loaded\nFile ▸ Open… (Ctrl+O)",
        )

    def _waveform_pixmap(self) -> QPixmap:
        key = _CacheKey(
            clip_id=id(self._pyramid),
            view_start=self._view_start,
            view_frames=self._view_frames,
            width=self.width(),
            height=self.height(),
            amplitude_scale=self._amplitude_scale,
            channels=self._pyramid.n_channels if self._pyramid else 0,
        )
        if self._cache is not None and self._cache_key == key:
            return self._cache

        ratio = self.devicePixelRatioF()
        pixmap = QPixmap(int(self.width() * ratio), int(self.height() * ratio))
        pixmap.setDevicePixelRatio(ratio)
        pixmap.fill(self._palette.color("waveform_bg"))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        self._paint_grid(painter)
        self._paint_channels(painter)
        painter.end()

        self._cache, self._cache_key = pixmap, key
        return pixmap

    def _channel_rects(self) -> list[QRectF]:
        assert self._pyramid is not None
        channels = max(self._pyramid.n_channels, 1)
        lane = self.height() / channels
        return [QRectF(0.0, i * lane, float(self.width()), lane) for i in range(channels)]

    def _paint_grid(self, painter: QPainter) -> None:
        painter.setPen(QPen(self._palette.color("waveform_grid"), 1))
        for seconds in self._grid_seconds():
            x = self.frame_to_x(seconds * self._sample_rate)
            if 0 <= x <= self.width():
                painter.drawLine(int(x), 0, int(x), self.height())

    def _grid_seconds(self) -> list[float]:
        """Pick a round gridline interval giving ~10 divisions across the view."""
        if self._view_frames <= 0:
            return []
        span = self._view_frames / self._sample_rate
        raw = span / 10.0
        candidates = (
            0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5,
            1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 1800, 3600,
        )
        step = next((c for c in candidates if c >= raw), candidates[-1])
        start_time = self._view_start / self._sample_rate
        first = int(start_time / step) * step
        count = int(span / step) + 2
        return [first + i * step for i in range(count)]

    def _paint_channels(self, painter: QPainter) -> None:
        assert self._pyramid is not None
        n_bins = max(self.width(), 1)
        pixels_per_frame = self.pixels_per_frame
        sample_mode = (
            self._samples is not None and pixels_per_frame >= SAMPLE_MODE_PPS
        )
        envelope = (
            None
            if sample_mode
            else self._pyramid.envelope(self._view_start, self.view_end, n_bins)
        )

        peak_pen = QPen(self._palette.color("waveform_peak"), 1)
        rms_pen = QPen(self._palette.color("waveform_rms"), 1)
        clip_pen = QPen(self._palette.color("waveform_clip"), 1)
        centre_pen = QPen(self._palette.color("waveform_center"), 1)

        for channel, rect in enumerate(self._channel_rects()):
            mid = rect.center().y()
            half = rect.height() / 2.0 - 2.0
            painter.setPen(centre_pen)
            painter.drawLine(0, int(mid), self.width(), int(mid))

            if sample_mode:
                self._paint_samples(painter, channel, mid, half, peak_pen)
                continue

            assert envelope is not None
            if channel >= envelope.n_channels:
                continue
            lows = np.clip(envelope.minimum[:, channel] * self._amplitude_scale, -1.0, 1.0)
            highs = np.clip(envelope.maximum[:, channel] * self._amplitude_scale, -1.0, 1.0)
            rms = np.clip(envelope.rms[:, channel] * self._amplitude_scale, 0.0, 1.0)
            clipped = (envelope.maximum[:, channel] >= 0.999) | (
                envelope.minimum[:, channel] <= -0.999
            )

            y_low = mid - lows * half
            y_high = mid - highs * half
            y_rms_hi = mid - rms * half
            y_rms_lo = mid + rms * half

            painter.setPen(peak_pen)
            for x in range(len(lows)):
                painter.drawLine(x, int(y_high[x]), x, int(y_low[x]))
            painter.setPen(rms_pen)
            for x in range(len(rms)):
                painter.drawLine(x, int(y_rms_hi[x]), x, int(y_rms_lo[x]))
            if clipped.any():
                painter.setPen(clip_pen)
                for x in np.flatnonzero(clipped):
                    painter.drawLine(int(x), int(rect.top()), int(x), int(rect.top()) + 3)

    def _paint_samples(
        self, painter: QPainter, channel: int, mid: float, half: float, pen: QPen
    ) -> None:
        """Sample-accurate polyline used when zoomed past ~4 px per sample."""
        samples = self._samples
        if samples is None or channel >= samples.shape[1]:
            return
        start = max(self._view_start - 1, 0)
        end = min(self.view_end + 2, self._n_frames)
        if end <= start:
            return

        values = np.clip(samples[start:end, channel] * self._amplitude_scale, -1.0, 1.0)
        xs = [self.frame_to_x(start + i) for i in range(len(values))]
        ys = [mid - float(v) * half for v in values]

        painter.setPen(pen)
        polyline = QPolygon([QPoint(int(x), int(y)) for x, y in zip(xs, ys, strict=True)])
        painter.drawPolyline(polyline)
        if self.pixels_per_frame >= 8.0:
            for point in polyline:
                painter.drawEllipse(point, 2, 2)

    def _paint_selection(self, painter: QPainter) -> None:
        if self._selection is None or self._selection.is_empty:
            return
        x0 = self.frame_to_x(self._selection.start)
        x1 = self.frame_to_x(self._selection.end)
        rect = QRectF(min(x0, x1), 0.0, abs(x1 - x0), float(self.height()))
        painter.fillRect(rect, self._palette.color("selection_fill", alpha=52))
        painter.setPen(QPen(self._palette.color("selection_edge"), 1))
        painter.drawLine(int(x0), 0, int(x0), self.height())
        painter.drawLine(int(x1), 0, int(x1), self.height())

    def _flag_colour(self, value: str | None, fallback: str) -> QColor:
        """A stored colour string, falling back to the palette when unusable."""
        if value:
            colour = QColor(value)
            if colour.isValid():
                return colour
        return self._palette.color(fallback)

    def _paint_regions(self, painter: QPainter) -> None:
        for region in self._markers.regions:
            x0 = self.frame_to_x(region.start)
            x1 = self.frame_to_x(region.end)
            if x1 < 0 or x0 > self.width():
                continue
            colour = self._flag_colour(region.color, "region")
            wash = QColor(colour)
            wash.setAlpha(30)
            painter.fillRect(
                QRectF(x0, 0.0, max(x1 - x0, 1.0), float(self.height())), wash
            )
            painter.setPen(QPen(colour, 1, Qt.PenStyle.DashLine))
            painter.drawLine(int(x0), 0, int(x0), self.height())
            painter.drawLine(int(x1), 0, int(x1), self.height())
            self._paint_flag_label(painter, colour, region.name, int(x0) + 4, int(x1))

    def _paint_markers(self, painter: QPainter) -> None:
        markers = self._markers.markers
        for index, marker in enumerate(markers):
            x = int(self.frame_to_x(marker.frame))
            if not (-1 <= x <= self.width() + 1):
                continue
            colour = self._flag_colour(marker.color, "marker")
            painter.setPen(QPen(colour, 1))
            painter.drawLine(x, MARKER_FLAG_HEIGHT, x, self.height())
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(colour)
            painter.drawPolygon(
                QPolygon(
                    [
                        QPoint(x, 0),
                        QPoint(x + 11, 0),
                        QPoint(x + 8, 5),
                        QPoint(x + 11, 10),
                        QPoint(x, 10),
                    ]
                )
            )
            painter.setBrush(Qt.BrushStyle.NoBrush)
            neighbour = (
                int(self.frame_to_x(markers[index + 1].frame)) - 2
                if index + 1 < len(markers)
                else self.width()
            )
            self._paint_flag_label(painter, colour, marker.name, x + 14, neighbour)

    def _paint_flag_label(
        self, painter: QPainter, colour: QColor, text: str, x: int, limit_x: int
    ) -> None:
        """Draw a flag caption from ``x``, elided so it cannot run into its neighbour."""
        available = min(limit_x, self.width()) - x
        if not text or available < 12:
            return
        metrics = QFontMetrics(painter.font())
        elided = metrics.elidedText(
            text, Qt.TextElideMode.ElideRight, min(available, MARKER_LABEL_MAX_WIDTH)
        )
        painter.setPen(QPen(colour, 1))
        painter.drawText(
            QRect(x, 0, available, MARKER_FLAG_HEIGHT),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            elided,
        )

    def _paint_cursor(self, painter: QPainter) -> None:
        if self._selection is not None:
            return
        x = self.frame_to_x(self._cursor_frame)
        if not (0 <= x <= self.width()):
            return
        pen = QPen(self._palette.color("cursor"), 1, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawLine(int(x), 0, int(x), self.height())

    def _paint_playhead(self, painter: QPainter) -> None:
        x = self.frame_to_x(self._playhead)
        if not (0 <= x <= self.width()):
            return
        colour: QColor = self._palette.color("playhead")
        painter.setPen(QPen(colour, 2))
        painter.drawLine(int(x), 0, int(x), self.height())
        painter.setBrush(colour)
        painter.drawPolygon(
            QPolygon([QPoint(int(x) - 5, 0), QPoint(int(x) + 5, 0), QPoint(int(x), 8)])
        )
