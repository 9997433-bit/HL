"""Vertical peak/RMS level meter with ballistics and a clip indicator.

The meter is fed raw linear amplitudes and does its own dB mapping, decay and
peak-hold, so it behaves the same regardless of how often the UI polls it.
"""

from __future__ import annotations

import time

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QLinearGradient, QMouseEvent, QPainter, QPaintEvent, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..core.types import amplitude_to_db
from .theme import PALETTE, Palette

#: Bottom of the meter scale in dBFS.
FLOOR_DB: float = -60.0

#: Fall-back rate of the bar in dB per second.
DECAY_DB_PER_SEC: float = 40.0

#: How long a peak marker stays parked before it starts falling.
PEAK_HOLD_SECONDS: float = 1.2

#: dBFS above which the bar turns amber, then red.
WARN_DB: float = -12.0
CLIP_DB: float = -0.1

#: Width reserved for the dB scale gutter.
SCALE_WIDTH: float = 26.0


class LevelMeter(QWidget):
    """Multi-channel meter; click anywhere to reset the clip indicator."""

    def __init__(
        self,
        channels: int = 2,
        parent: QWidget | None = None,
        palette: Palette = PALETTE,
    ) -> None:
        super().__init__(parent)
        self._palette = palette
        self._channels = max(int(channels), 1)
        self._levels_db = [FLOOR_DB] * self._channels
        self._peaks_db = [FLOOR_DB] * self._channels
        self._peak_times = [0.0] * self._channels
        self._rms_db = [FLOOR_DB] * self._channels
        self._clipped = False
        self._last_update = time.monotonic()

        self.setFixedWidth(int(SCALE_WIDTH) + 14 * self._channels + 4)
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setToolTip("Output level (dBFS) — click to reset clip indicator")

    @property
    def channels(self) -> int:
        return self._channels

    def set_channels(self, channels: int) -> None:
        channels = max(int(channels), 1)
        if channels == self._channels:
            return
        self._channels = channels
        self._levels_db = [FLOOR_DB] * channels
        self._peaks_db = [FLOOR_DB] * channels
        self._peak_times = [0.0] * channels
        self._rms_db = [FLOOR_DB] * channels
        self.setFixedWidth(int(SCALE_WIDTH) + 14 * channels + 4)
        self.update()

    def update_levels(self, peak: tuple[float, ...], rms: tuple[float, ...] = ()) -> None:
        """Feed one metering block of linear per-channel amplitudes."""
        now = time.monotonic()
        elapsed = max(now - self._last_update, 0.0)
        self._last_update = now
        decay = DECAY_DB_PER_SEC * elapsed

        for ch in range(self._channels):
            amplitude = peak[ch] if ch < len(peak) else 0.0
            db = amplitude_to_db(amplitude, FLOOR_DB)
            self._levels_db[ch] = max(db, self._levels_db[ch] - decay)

            rms_amp = rms[ch] if ch < len(rms) else 0.0
            rms_db = amplitude_to_db(rms_amp, FLOOR_DB)
            self._rms_db[ch] = max(rms_db, self._rms_db[ch] - decay)

            if db >= self._peaks_db[ch]:
                self._peaks_db[ch] = db
                self._peak_times[ch] = now
            elif now - self._peak_times[ch] > PEAK_HOLD_SECONDS:
                self._peaks_db[ch] = max(db, self._peaks_db[ch] - decay)

            if amplitude >= 0.999:
                self._clipped = True
        self.update()

    def reset(self) -> None:
        self._levels_db = [FLOOR_DB] * self._channels
        self._peaks_db = [FLOOR_DB] * self._channels
        self._rms_db = [FLOOR_DB] * self._channels
        self._clipped = False
        self.update()

    @property
    def clipped(self) -> bool:
        return self._clipped

    @property
    def is_at_floor(self) -> bool:
        """True once every bar and peak marker has decayed to the scale floor."""
        return all(db <= FLOOR_DB for db in (*self._levels_db, *self._peaks_db, *self._rms_db))

    def mousePressEvent(self, _event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        self._clipped = False
        self.update()

    @staticmethod
    def _db_to_fraction(db: float) -> float:
        return max(0.0, min((db - FLOOR_DB) / (0.0 - FLOOR_DB), 1.0))

    def paintEvent(self, _event: QPaintEvent) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.fillRect(self.rect(), self._palette.color("meter_bg"))

        clip_h = 8.0
        top = clip_h + 4.0
        bottom = float(self.height() - 4)
        track_h = max(bottom - top, 1.0)
        bar_w = 10.0
        gap = 4.0
        scale_w = SCALE_WIDTH
        x0 = scale_w

        gradient = QLinearGradient(0.0, bottom, 0.0, top)
        gradient.setColorAt(0.0, self._palette.color("meter_low"))
        gradient.setColorAt(self._db_to_fraction(WARN_DB), self._palette.color("meter_mid"))
        gradient.setColorAt(1.0, self._palette.color("meter_high"))

        painter.setPen(QPen(self._palette.color("border"), 1))
        painter.setFont(painter.font())
        for db in (0, -6, -12, -24, -36, -48, -60):
            y = bottom - self._db_to_fraction(db) * track_h
            painter.setPen(self._palette.color("text_dim"))
            painter.drawText(QRectF(0.0, y - 6.0, scale_w - 3.0, 12.0),
                             int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                             str(db))
            painter.setPen(QPen(self._palette.color("waveform_grid"), 1))
            painter.drawLine(int(scale_w), int(y), self.width(), int(y))

        for ch in range(self._channels):
            x = x0 + ch * (bar_w + gap)
            track = QRectF(x, top, bar_w, track_h)
            painter.fillRect(track, self._palette.color("surface"))

            level_h = self._db_to_fraction(self._levels_db[ch]) * track_h
            if level_h > 0:
                painter.fillRect(QRectF(x, bottom - level_h, bar_w, level_h), gradient)

            rms_h = self._db_to_fraction(self._rms_db[ch]) * track_h
            if rms_h > 0:
                painter.fillRect(
                    QRectF(x, bottom - rms_h, bar_w, rms_h),
                    self._palette.color("text", alpha=45),
                )

            peak_y = bottom - self._db_to_fraction(self._peaks_db[ch]) * track_h
            if self._peaks_db[ch] > FLOOR_DB:
                colour = (
                    "meter_high"
                    if self._peaks_db[ch] >= CLIP_DB
                    else ("meter_mid" if self._peaks_db[ch] >= WARN_DB else "meter_low")
                )
                painter.setPen(QPen(self._palette.color(colour), 2))
                painter.drawLine(int(x), int(peak_y), int(x + bar_w), int(peak_y))

            painter.setPen(QPen(self._palette.color("border"), 1))
            painter.drawRect(track)

        clip_rect = QRectF(x0, 2.0, self._channels * (bar_w + gap) - gap, clip_h)
        painter.fillRect(
            clip_rect,
            self._palette.color("meter_high" if self._clipped else "surface"),
        )
        painter.setPen(QPen(self._palette.color("border"), 1))
        painter.drawRect(clip_rect)
        painter.end()
