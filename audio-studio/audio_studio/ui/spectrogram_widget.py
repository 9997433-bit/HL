"""PyQt6 spectrogram / waterfall display.

The widget renders a dB matrix as a colour-mapped heat map with calibrated
frequency and time axes, a logarithmic frequency option, and a hover read-out
giving the exact time, frequency and level under the cursor — the interaction
model of Adobe Audition's spectral frequency display.

Two modes share the same painter:

``DisplayMode.STATIC``
    Show a fixed :class:`~audio_studio.dsp.spectral.Spectrogram` (a whole file
    or a selection). The time axis runs left to right in absolute seconds.
``DisplayMode.WATERFALL``
    Scroll live frames pushed in by :meth:`SpectrogramWidget.push_frame`. The
    time axis is relative to now.

Rendering cost is dominated by one gather per output pixel, not per input bin:
the dB matrix is reduced to the widget's pixel grid with a max-pooling
``reduceat`` before colourisation, so a 10-minute file paints as fast as a
1-second one and narrow spectral lines survive the downsample instead of
aliasing away.

That reduction is also cached. It depends only on the data and the geometry —
pixel size, frequency scale, frequency range — so changing the palette or the
dB range repaints from the cached pixel grid and never touches the source
matrix again. Dragging a contrast control is then a colour lookup over a few
hundred thousand pixels instead of a max-pool over millions of bins.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import Enum

import numpy as np
from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QImage,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QResizeEvent,
)
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..dsp.spectral import Spectrogram, WaterfallBuffer
from .colormaps import COLORMAP_NAMES, DEFAULT_COLORMAP, get_colormap

__all__ = ["DisplayMode", "FrequencyScale", "SpectrogramWidget"]


class DisplayMode(str, Enum):
    """Whether the widget shows a fixed matrix or a live scrolling history."""

    STATIC = "static"
    WATERFALL = "waterfall"


class FrequencyScale(str, Enum):
    """Vertical axis mapping.

    ``LOG`` matches how pitch is perceived and how Audition draws its spectral
    display by default; ``LINEAR`` gives every hertz equal space and is the
    better choice when hunting for harmonically spaced artefacts.
    """

    LINEAR = "linear"
    LOG = "log"


_MARGIN_LEFT = 56
_MARGIN_BOTTOM = 24
_MARGIN_TOP = 6
_MARGIN_RIGHT = 8
_COLORBAR_WIDTH = 14


def _pixel_reduce(data: np.ndarray, bounds: np.ndarray, axis: int) -> np.ndarray:
    """Max-pool ``data`` along ``axis`` into the segments given by ``bounds``.

    ``bounds`` holds the start index of each output cell. Where two consecutive
    bounds are equal — i.e. the display is zoomed in past one sample per pixel
    — the single element at that index is taken, which is exactly the
    nearest-neighbour behaviour wanted there. Where they differ, the peak of
    the covered range wins, so a one-bin spectral line stays visible however
    far the view is zoomed out.

    This is ``numpy.maximum.reduceat`` semantics, element for element, but it
    is computed as one gather per *offset into a segment* rather than one
    reduction per segment. Segments here are a handful of rows and there are
    thousands of them, which is the case ``reduceat`` handles worst: pooling a
    minute of audio onto a 1920-pixel axis drops from 33 ms to 6 ms, and that
    is the whole cost of the first paint after an analysis.
    """
    length = data.shape[axis]
    if length == 0 or bounds.size == 0:
        shape = list(data.shape)
        shape[axis] = bounds.size
        return np.zeros(shape, dtype=data.dtype)

    spans = np.diff(np.append(bounds, length))
    out = np.take(data, bounds, axis=axis)
    for offset in range(1, int(spans.max())):
        cells = np.flatnonzero(spans > offset)
        if cells.size == 0:
            break
        pooled = np.maximum(
            np.take(out, cells, axis=axis),
            np.take(data, bounds[cells] + offset, axis=axis),
        )
        if axis == 0:
            out[cells] = pooled
        else:
            out[:, cells] = pooled
    return out


class SpectrogramWidget(QWidget):
    """Colour-mapped spectrogram view with axes and a hover read-out.

    Examples
    --------
    >>> # doctest: +SKIP
    >>> widget = SpectrogramWidget()
    >>> widget.set_spectrogram(analyzer.spectrogram(audio))
    >>> widget.set_colormap("viridis")
    >>> widget.set_db_range(-100.0, 0.0)
    """

    #: Emitted while the pointer is over the plot: ``(time_s, frequency_hz, level_db)``.
    cursorMoved = pyqtSignal(float, float, float)

    #: Emitted when the pointer leaves the plot area.
    cursorLeft = pyqtSignal()

    #: Emitted on click: ``(time_s, frequency_hz)``.
    positionClicked = pyqtSignal(float, float)

    def __init__(
        self,
        parent: QWidget | None = None,
        colormap: str = DEFAULT_COLORMAP,
        db_range: tuple[float, float] = (-100.0, 0.0),
        frequency_scale: FrequencyScale | str = FrequencyScale.LOG,
        show_colorbar: bool = True,
    ) -> None:
        super().__init__(parent)

        self._data: np.ndarray | None = None  # (n_frames, n_bins) dB
        self._frequencies: np.ndarray = np.zeros(0)
        self._times: np.ndarray = np.zeros(0)

        self._mode = DisplayMode.STATIC
        self._waterfall: WaterfallBuffer | None = None
        self._frame_interval_s = 0.0

        self._colormap = colormap if colormap in COLORMAP_NAMES else DEFAULT_COLORMAP
        self._db_min, self._db_max = float(db_range[0]), float(db_range[1])
        self._frequency_scale = FrequencyScale(frequency_scale)
        self._f_min = 20.0
        self._f_max = 20_000.0
        self._show_colorbar = bool(show_colorbar)
        self._show_grid = True

        self._image: QImage | None = None
        self._image_buffer: np.ndarray | None = None  # keeps QImage memory alive
        self._image_dirty = True
        self._cursor: QPoint | None = None

        self._data_version = 0
        self._columns_key: tuple | None = None
        self._columns: np.ndarray | None = None  # (width, n_bins) dB
        self._reduce_key: tuple | None = None
        self._reduced: np.ndarray | None = None  # (height, width) dB, display order

        self.setMouseTracking(True)
        self.setMinimumSize(240, 120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAutoFillBackground(False)

    # -- data ------------------------------------------------------------

    def set_spectrogram(
        self,
        spectrogram: Spectrogram | np.ndarray,
        frequencies: np.ndarray | None = None,
        times: np.ndarray | None = None,
        channel: int | None = None,
    ) -> None:
        """Display a complete spectrogram.

        Accepts either a :class:`~audio_studio.dsp.spectral.Spectrogram` — in
        which case ``channel=None`` shows the channel-averaged mix — or a raw
        ``(n_frames, n_bins)`` dB matrix together with its axes.
        """
        if isinstance(spectrogram, Spectrogram):
            data = spectrogram.db(channel=channel)
            frequencies = spectrogram.frequencies
            times = spectrogram.times
        else:
            data = np.asarray(spectrogram, dtype=np.float32)
            if data.ndim != 2:
                raise ValueError(f"expected a 2-D dB matrix, got shape {data.shape}")
            if frequencies is None or times is None:
                raise ValueError("frequencies and times are required for a raw matrix")

        self._mode = DisplayMode.STATIC
        self._data = np.ascontiguousarray(data, dtype=np.float32)
        self._frequencies = np.asarray(frequencies, dtype=np.float64)
        self._times = np.asarray(times, dtype=np.float64)
        self._clamp_frequency_range()
        self._invalidate(data_changed=True)

    def start_waterfall(
        self,
        frequencies: np.ndarray,
        history: int = 512,
        frame_interval_s: float = 0.0,
    ) -> None:
        """Switch to scrolling mode with room for ``history`` frames."""
        self._frequencies = np.asarray(frequencies, dtype=np.float64)
        self._waterfall = WaterfallBuffer(
            n_bins=self._frequencies.size, capacity=int(history), fill_db=self._db_min
        )
        self._frame_interval_s = float(frame_interval_s)
        self._mode = DisplayMode.WATERFALL
        self._data = None
        self._clamp_frequency_range()
        self._invalidate(data_changed=True)

    def push_frame(self, frame_db: np.ndarray, repaint: bool = True) -> None:
        """Append one live spectrum to the waterfall.

        Call :meth:`start_waterfall` first. Pass ``repaint=False`` when pushing
        a burst of frames and repaint once at the end.
        """
        if self._waterfall is None:
            raise RuntimeError("call start_waterfall() before push_frame()")
        self._waterfall.push(np.asarray(frame_db, dtype=np.float32))
        self._data_version += 1
        self._image_dirty = True
        if repaint:
            self.update()

    def clear(self) -> None:
        """Drop all displayed data."""
        self._data = None
        if self._waterfall is not None:
            self._waterfall.clear()
        self._invalidate(data_changed=True)

    # -- appearance --------------------------------------------------------

    @property
    def colormap(self) -> str:
        return self._colormap

    def set_colormap(self, name: str) -> None:
        """Select a palette from :data:`~audio_studio.ui.colormaps.COLORMAP_NAMES`."""
        get_colormap(name)  # validates, raising KeyError with the valid names
        self._colormap = name.strip().lower()
        self._invalidate()

    @property
    def db_range(self) -> tuple[float, float]:
        return (self._db_min, self._db_max)

    def set_db_range(self, db_min: float, db_max: float) -> None:
        """Set the dynamic range mapped onto the palette."""
        if db_max <= db_min:
            raise ValueError(f"db_max ({db_max}) must exceed db_min ({db_min})")
        self._db_min, self._db_max = float(db_min), float(db_max)
        self._invalidate()

    def auto_scale(self, percentile: float = 99.9, floor_range_db: float = 90.0) -> None:
        """Fit the dB range to the data currently on screen.

        The top is taken from a high percentile rather than the absolute
        maximum so that a single stray sample does not wash out the display,
        and the floor is held ``floor_range_db`` below it.
        """
        data = self._current_matrix()
        if data is None or data.size == 0:
            return
        top = float(np.percentile(data, percentile))
        self.set_db_range(top - float(floor_range_db), top)

    @property
    def frequency_scale(self) -> FrequencyScale:
        return self._frequency_scale

    def set_frequency_scale(self, scale: FrequencyScale | str) -> None:
        """Switch the vertical axis between linear and logarithmic hertz."""
        self._frequency_scale = FrequencyScale(scale)
        self._clamp_frequency_range()
        self._invalidate()

    @property
    def frequency_range(self) -> tuple[float, float]:
        return (self._f_min, self._f_max)

    def set_frequency_range(self, f_min: float, f_max: float) -> None:
        """Zoom the vertical axis to ``[f_min, f_max]`` hertz."""
        if f_max <= f_min:
            raise ValueError(f"f_max ({f_max}) must exceed f_min ({f_min})")
        self._f_min, self._f_max = float(f_min), float(f_max)
        self._clamp_frequency_range()
        self._invalidate()

    def set_grid_visible(self, visible: bool) -> None:
        self._show_grid = bool(visible)
        self.update()

    def set_colorbar_visible(self, visible: bool) -> None:
        self._show_colorbar = bool(visible)
        self._invalidate()

    # -- rendering ---------------------------------------------------------

    def render_image(self, width: int, height: int) -> QImage | None:
        """Render just the heat map at an arbitrary size.

        Separated from :meth:`paintEvent` so the renderer can be exercised
        headlessly (and used for thumbnails and export) without a window.
        """
        grid = self.reduced_matrix(width, height)
        if grid is None:
            return None

        lut = get_colormap(self._colormap)
        span = self._db_max - self._db_min
        scale = (lut.shape[0] - 1) / (span if span > 0 else 1.0)
        indices = np.clip((grid - self._db_min) * scale, 0, lut.shape[0] - 1).astype(np.uint8)

        rgb = lut[indices]  # (height, width, 3), contiguous because indices is
        self._image_buffer = rgb
        return QImage(rgb.data, width, height, 3 * width, QImage.Format.Format_RGB888)

    def reduced_matrix(self, width: int, height: int) -> np.ndarray | None:
        """dB max-pooled onto the pixel grid, ``(height, width)`` top row first.

        Two caches back this, because the two axes go stale for different
        reasons. The column reduction depends only on the data and the pixel
        width, so a vertical resize or a frequency-axis zoom reuses it; the row
        reduction on top of it depends on the height and the frequency mapping.
        Neither depends on the palette or the dB range, which is what makes
        those controls repaint at interactive rates on a long file.
        """
        columns = self._reduced_columns(width)
        if columns is None or height < 1:
            return None

        key = (self._data_version, width, height, self._frequency_scale, self._f_min, self._f_max)
        if self._reduced is not None and self._reduce_key == key:
            return self._reduced

        block = _pixel_reduce(columns, self._row_bounds(height, columns.shape[1]), axis=1)
        # block is (width, height) with frequency ascending; the display wants
        # (height, width) with frequency ascending *upwards*, hence the flip.
        self._reduced = np.ascontiguousarray(block.transpose(1, 0)[::-1])
        self._reduce_key = key
        return self._reduced

    def _reduced_columns(self, width: int) -> np.ndarray | None:
        """``(width, n_bins)`` — the source matrix max-pooled along time only."""
        data = self._current_matrix()
        if data is None or data.size == 0 or width < 1:
            return None
        n_frames, n_bins = data.shape
        if n_frames == 0 or n_bins == 0:
            return None

        key = (self._data_version, width)
        if self._columns is not None and self._columns_key == key:
            return self._columns

        bounds = np.clip((np.arange(width) * n_frames) // max(width, 1), 0, n_frames - 1)
        self._columns = _pixel_reduce(data, bounds, axis=0)
        self._columns_key = key
        return self._columns

    def _row_bounds(self, height: int, n_bins: int) -> np.ndarray:
        """Start bin index for each output row, bottom row first."""
        nyquist = float(self._frequencies[-1]) if self._frequencies.size else 1.0
        f_min = max(self._f_min, 1e-6)
        f_max = min(self._f_max, nyquist) if nyquist > 0 else self._f_max
        if f_max <= f_min:
            f_max = f_min * 2.0

        if self._frequency_scale is FrequencyScale.LOG:
            targets = np.geomspace(f_min, f_max, height)
        else:
            targets = np.linspace(f_min, f_max, height)

        if self._frequencies.size:
            bounds = np.searchsorted(self._frequencies, targets)
        else:
            bounds = (targets / max(f_max, 1e-9) * n_bins).astype(np.int64)
        return np.clip(bounds, 0, n_bins - 1)

    def _current_matrix(self) -> np.ndarray | None:
        if self._mode is DisplayMode.WATERFALL and self._waterfall is not None:
            if len(self._waterfall) == 0:
                return None
            return self._waterfall.image()
        return self._data

    def _plot_rect(self) -> QRect:
        right = _MARGIN_RIGHT + (_COLORBAR_WIDTH + 30 if self._show_colorbar else 0)
        return QRect(
            _MARGIN_LEFT,
            _MARGIN_TOP,
            max(1, self.width() - _MARGIN_LEFT - right),
            max(1, self.height() - _MARGIN_TOP - _MARGIN_BOTTOM),
        )

    def _invalidate(self, data_changed: bool = False) -> None:
        """Schedule a repaint; ``data_changed`` also drops the pixel-grid cache.

        Geometry changes need no flag — the cache is keyed on the geometry, so
        a new size or frequency range simply misses.
        """
        if data_changed:
            self._data_version += 1
            self._columns = self._reduced = None
            self._columns_key = self._reduce_key = None
        self._image_dirty = True
        self.update()

    def _clamp_frequency_range(self) -> None:
        if self._frequencies.size:
            nyquist = float(self._frequencies[-1])
            self._f_max = min(self._f_max, nyquist)
            lowest = 1.0 if self._frequency_scale is FrequencyScale.LOG else 0.0
            self._f_min = max(self._f_min, lowest)
            if self._f_max <= self._f_min:
                self._f_min, self._f_max = max(lowest, nyquist / 1000.0), nyquist

    # -- Qt events ---------------------------------------------------------

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 (Qt naming)
        self._image_dirty = True
        super().resizeEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(18, 18, 22))

        plot = self._plot_rect()
        if self._image_dirty or self._image is None:
            self._image = self.render_image(plot.width(), plot.height())
            self._image_dirty = False

        if self._image is not None:
            painter.drawImage(plot.topLeft(), self._image)
        else:
            painter.setPen(QColor(140, 140, 150))
            painter.drawText(plot, Qt.AlignmentFlag.AlignCenter, "No spectral data")

        painter.setPen(QPen(QColor(70, 70, 80), 1))
        painter.drawRect(plot.adjusted(0, 0, -1, -1))

        self._paint_frequency_axis(painter, plot)
        self._paint_time_axis(painter, plot)
        if self._show_colorbar:
            self._paint_colorbar(painter, plot)
        if self._cursor is not None and plot.contains(self._cursor):
            self._paint_cursor(painter, plot)
        painter.end()

    def _axis_font(self) -> QFont:
        font = self.font()
        font.setPointSizeF(max(7.0, font.pointSizeF() - 1.0))
        return font

    def _paint_frequency_axis(self, painter: QPainter, plot: QRect) -> None:
        painter.setFont(self._axis_font())
        ticks = self._frequency_ticks()
        for frequency, label in ticks:
            y = self._frequency_to_y(frequency, plot)
            if y is None:
                continue
            if self._show_grid:
                painter.setPen(QPen(QColor(255, 255, 255, 28), 1))
                painter.drawLine(plot.left(), y, plot.right(), y)
            painter.setPen(QColor(170, 170, 180))
            painter.drawLine(plot.left() - 4, y, plot.left(), y)
            painter.drawText(
                QRect(0, y - 8, _MARGIN_LEFT - 6, 16),
                int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                label,
            )

    def _frequency_ticks(self) -> Sequence[tuple[float, str]]:
        if self._frequency_scale is FrequencyScale.LOG:
            candidates = [
                20, 50, 100, 200, 500, 1_000, 2_000, 5_000,
                10_000, 20_000, 50_000, 100_000,
            ]
        else:
            step = _nice_step((self._f_max - self._f_min) / 8.0)
            start = np.ceil(self._f_min / step) * step
            candidates = list(np.arange(start, self._f_max + step * 0.5, step))
        return [(float(f), _format_hz(float(f))) for f in candidates
                if self._f_min <= f <= self._f_max]

    def _paint_time_axis(self, painter: QPainter, plot: QRect) -> None:
        painter.setFont(self._axis_font())
        painter.setPen(QColor(170, 170, 180))
        t0, t1 = self._time_span()
        if t1 <= t0:
            return
        step = _nice_step((t1 - t0) / 6.0)
        tick = np.ceil(t0 / step) * step
        while tick <= t1 + step * 1e-6:
            x = plot.left() + int((tick - t0) / (t1 - t0) * (plot.width() - 1))
            if plot.left() <= x <= plot.right():
                painter.setPen(QColor(170, 170, 180))
                painter.drawLine(x, plot.bottom(), x, plot.bottom() + 4)
                painter.drawText(
                    QRect(x - 40, plot.bottom() + 5, 80, _MARGIN_BOTTOM - 6),
                    int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop),
                    _format_seconds(float(tick)),
                )
            tick += step

    def _paint_colorbar(self, painter: QPainter, plot: QRect) -> None:
        bar = QRect(plot.right() + 10, plot.top(), _COLORBAR_WIDTH, plot.height())
        lut = get_colormap(self._colormap)
        gradient = np.linspace(lut.shape[0] - 1, 0, bar.height()).astype(np.int32)
        strip = np.ascontiguousarray(
            np.repeat(lut[gradient][:, np.newaxis, :], bar.width(), axis=1)
        )
        self._colorbar_buffer = strip  # keep alive for the QImage below
        image = QImage(
            strip.data, bar.width(), bar.height(), 3 * bar.width(), QImage.Format.Format_RGB888
        )
        painter.drawImage(bar.topLeft(), image)

        painter.setFont(self._axis_font())
        painter.setPen(QColor(170, 170, 180))
        for fraction, value in ((0.0, self._db_max), (1.0, self._db_min)):
            y = bar.top() + int(fraction * (bar.height() - 1))
            painter.drawText(
                QRect(bar.right() + 3, y - 8, 40, 16),
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                f"{value:.0f}",
            )

    def _paint_cursor(self, painter: QPainter, plot: QRect) -> None:
        assert self._cursor is not None
        painter.setPen(QPen(QColor(255, 255, 255, 110), 1, Qt.PenStyle.DashLine))
        painter.drawLine(self._cursor.x(), plot.top(), self._cursor.x(), plot.bottom())
        painter.drawLine(plot.left(), self._cursor.y(), plot.right(), self._cursor.y())

        time_s, frequency, level = self.value_at(self._cursor)
        text = f"{_format_seconds(time_s)}  {_format_hz(frequency)}  {level:.1f} dB"
        painter.setFont(self._axis_font())
        metrics = QFontMetrics(painter.font())
        width = metrics.horizontalAdvance(text) + 10
        box = QRect(plot.left() + 6, plot.top() + 6, width, metrics.height() + 6)
        painter.fillRect(box, QColor(0, 0, 0, 170))
        painter.setPen(QColor(240, 240, 245))
        painter.drawText(box, int(Qt.AlignmentFlag.AlignCenter), text)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        position = event.position().toPoint()
        plot = self._plot_rect()
        if plot.contains(position):
            self._cursor = position
            self.cursorMoved.emit(*self.value_at(position))
        elif self._cursor is not None:
            self._cursor = None
            self.cursorLeft.emit()
        self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802
        if self._cursor is not None:
            self._cursor = None
            self.cursorLeft.emit()
            self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        position = event.position().toPoint()
        if self._plot_rect().contains(position):
            time_s, frequency, _ = self.value_at(position)
            self.positionClicked.emit(time_s, frequency)
        super().mousePressEvent(event)

    # -- coordinate mapping -------------------------------------------------

    def _time_span(self) -> tuple[float, float]:
        if self._mode is DisplayMode.WATERFALL and self._waterfall is not None:
            span = self._waterfall.capacity * self._frame_interval_s
            return (-span, 0.0)
        if self._times.size:
            return (float(self._times[0]), float(self._times[-1]))
        return (0.0, 0.0)

    def _frequency_to_y(self, frequency: float, plot: QRect) -> int | None:
        f_min, f_max = max(self._f_min, 1e-9), self._f_max
        if not f_min < f_max or not f_min <= frequency <= f_max:
            return None
        if self._frequency_scale is FrequencyScale.LOG:
            fraction = np.log(frequency / f_min) / np.log(f_max / f_min)
        else:
            fraction = (frequency - f_min) / (f_max - f_min)
        return plot.bottom() - int(fraction * (plot.height() - 1))

    def _y_to_frequency(self, y: int, plot: QRect) -> float:
        fraction = np.clip((plot.bottom() - y) / max(plot.height() - 1, 1), 0.0, 1.0)
        f_min, f_max = max(self._f_min, 1e-9), self._f_max
        if self._frequency_scale is FrequencyScale.LOG:
            return float(f_min * (f_max / f_min) ** fraction)
        return float(f_min + fraction * (f_max - f_min))

    def _x_to_time(self, x: int, plot: QRect) -> float:
        fraction = np.clip((x - plot.left()) / max(plot.width() - 1, 1), 0.0, 1.0)
        t0, t1 = self._time_span()
        return float(t0 + fraction * (t1 - t0))

    def value_at(self, point: QPoint) -> tuple[float, float, float]:
        """``(time_s, frequency_hz, level_db)`` under a widget-space point."""
        plot = self._plot_rect()
        time_s = self._x_to_time(point.x(), plot)
        frequency = self._y_to_frequency(point.y(), plot)

        data = self._current_matrix()
        if data is None or data.size == 0 or not self._frequencies.size:
            return (time_s, frequency, self._db_min)

        bin_index = int(np.clip(
            np.searchsorted(self._frequencies, frequency), 0, data.shape[1] - 1
        ))
        fraction = np.clip((point.x() - plot.left()) / max(plot.width() - 1, 1), 0.0, 1.0)
        frame_index = int(np.clip(round(fraction * (data.shape[0] - 1)), 0, data.shape[0] - 1))
        return (time_s, frequency, float(data[frame_index, bin_index]))


def _nice_step(raw: float) -> float:
    """Round ``raw`` up to the nearest 1, 2 or 5 times a power of ten."""
    if raw <= 0 or not np.isfinite(raw):
        return 1.0
    exponent = np.floor(np.log10(raw))
    base = raw / (10.0**exponent)
    nice = 1.0 if base <= 1.0 else 2.0 if base <= 2.0 else 5.0 if base <= 5.0 else 10.0
    return float(nice * 10.0**exponent)


def _format_hz(frequency: float) -> str:
    if frequency >= 1000.0:
        value = frequency / 1000.0
        return f"{value:.0f}k" if value >= 10 or value == int(value) else f"{value:.1f}k"
    return f"{frequency:.0f}"


def _format_seconds(seconds: float) -> str:
    sign = "-" if seconds < 0 else ""
    seconds = abs(seconds)
    if seconds < 1.0:
        return f"{sign}{seconds * 1000:.0f}ms"
    if seconds < 60.0:
        return f"{sign}{seconds:g}s"
    minutes, remainder = divmod(seconds, 60.0)
    return f"{sign}{int(minutes)}:{remainder:05.2f}"
