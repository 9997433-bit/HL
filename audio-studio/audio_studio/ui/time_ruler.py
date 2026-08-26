"""Timeline ruler kept in sync with a :class:`~.waveform_view.WaveformView`."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent, QPainter, QPaintEvent, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..core.types import format_timecode
from .theme import PALETTE, Palette

RULER_HEIGHT: int = 26


class TimeRuler(QWidget):
    """Draws labelled tick marks for the currently visible frame range."""

    seekRequested = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None, palette: Palette = PALETTE) -> None:
        super().__init__(parent)
        self._palette = palette
        self._view_start = 0
        self._view_frames = 0
        self._sample_rate = 44100
        self._playhead = 0

        self.setFixedHeight(RULER_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_sample_rate(self, sample_rate: int) -> None:
        self._sample_rate = max(int(sample_rate), 1)
        self.update()

    def set_view(self, view_start: int, view_frames: int) -> None:
        self._view_start = int(view_start)
        self._view_frames = int(view_frames)
        self.update()

    def set_playhead(self, frame: int) -> None:
        self._playhead = int(frame)
        self.update()

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

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.seekRequested.emit(self.x_to_frame(event.position().x()))

    def _tick_step(self) -> float:
        span = self._view_frames / self._sample_rate
        raw = span / 8.0
        candidates = (
            0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5,
            1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 1800, 3600,
        )
        return next((c for c in candidates if c >= raw), candidates[-1])

    def paintEvent(self, _event: QPaintEvent) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.fillRect(self.rect(), self._palette.color("surface"))
        painter.setPen(QPen(self._palette.color("border"), 1))
        painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)

        if self._view_frames <= 0:
            painter.end()
            return

        step = self._tick_step()
        show_millis = step < 1.0
        start_time = self._view_start / self._sample_rate
        first = int(start_time / step) * step
        count = int(self._view_frames / self._sample_rate / step) + 2

        text_pen = QPen(self._palette.color("text_dim"), 1)
        tick_pen = QPen(self._palette.color("border"), 1)
        for i in range(count):
            seconds = first + i * step
            if seconds < 0:
                continue
            x = self.frame_to_x(seconds * self._sample_rate)
            if not (-40 <= x <= self.width() + 40):
                continue
            painter.setPen(tick_pen)
            painter.drawLine(int(x), self.height() - 8, int(x), self.height() - 1)
            painter.setPen(text_pen)
            label = format_timecode(seconds, show_millis=show_millis)
            painter.drawText(int(x) + 3, self.height() - 10, label)

            for sub in range(1, 4):
                sub_x = self.frame_to_x((seconds + sub * step / 4) * self._sample_rate)
                if 0 <= sub_x <= self.width():
                    painter.setPen(tick_pen)
                    painter.drawLine(int(sub_x), self.height() - 4, int(sub_x), self.height() - 1)

        x = self.frame_to_x(self._playhead)
        if 0 <= x <= self.width():
            painter.setPen(QPen(self._palette.color("playhead"), 2))
            painter.drawLine(int(x), 0, int(x), self.height())
        painter.end()
