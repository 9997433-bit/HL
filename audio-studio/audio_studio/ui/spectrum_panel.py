"""Dockable spectral view: a :class:`SpectrogramWidget` plus its controls.

The panel owns the analysis as well as the display. It picks an FFT size and
hop from the length of the audio it is given so that a ten-minute file produces
about as many columns as a ten-second one — beyond a few thousand columns the
extra detail cannot reach the screen anyway, and the transform stops being
interactive.

It also owns the *spectral selection*: the rectangle dragged over the
spectrogram, which the widget reports in its own excerpt-relative seconds and
the panel republishes in document coordinates — a
:class:`~audio_studio.core.types.TimeRange` in frames plus a band in hertz.
That is what an edit needs, because the analysis usually covers a selection
rather than the whole file, and the offset between the two has to be added back
before any sample is touched.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..core.types import TimeRange
from ..dsp.spectral import SpectralAnalyzer, SpectralConfig
from ..dsp.spectral_edit import ATTENUATION_DB
from .colormaps import COLORMAP_NAMES, DEFAULT_COLORMAP
from .spectrogram_widget import FrequencyScale, SpectralRegion, SpectrogramWidget

__all__ = ["SpectralSelection", "SpectrumPanel", "analysis_config"]

#: Columns beyond this cannot be resolved on any screen, so the hop is widened
#: instead of computing frames nobody will see.
MAX_ANALYSIS_FRAMES = 4096

#: Selectable dynamic ranges, as ``(label, floor_db)`` below 0 dBFS.
DB_RANGES: tuple[tuple[str, float], ...] = (
    ("60 dB", -60.0),
    ("90 dB", -90.0),
    ("120 dB", -120.0),
)

FFT_SIZES: tuple[int, ...] = (512, 1024, 2048, 4096, 8192)


@dataclass(frozen=True, slots=True)
class SpectralSelection:
    """A spectrogram rectangle expressed in document coordinates."""

    time: TimeRange
    low_hz: float
    high_hz: float

    @property
    def bandwidth_hz(self) -> float:
        return self.high_hz - self.low_hz

    def describe(self, sample_rate: float) -> str:
        start, end = self.time.to_seconds(int(max(sample_rate, 1)))
        return (
            f"{start:.3f}–{end:.3f} s · "
            f"{self.low_hz:.0f}–{self.high_hz:.0f} Hz"
        )


def analysis_config(sample_rate: float, n_frames: int, fft_size: int = 2048) -> SpectralConfig:
    """Config whose hop keeps the column count under :data:`MAX_ANALYSIS_FRAMES`."""
    hop = max(fft_size // 4, 1)
    if n_frames > 0:
        hop = max(hop, int(np.ceil(n_frames / MAX_ANALYSIS_FRAMES)))
    return SpectralConfig(
        sample_rate=sample_rate,
        fft_size=fft_size,
        hop_size=hop,
        dtype=np.float32,
    )


class SpectrumPanel(QWidget):
    """Spectrogram view with palette, scale, range and resolution controls."""

    #: Emitted when the user clicks the plot: ``(time_s,)`` relative to the clip.
    seekRequested = Signal(float)

    #: Emitted with the hover read-out, or an empty string when the pointer leaves.
    readoutChanged = Signal(str)

    #: Emitted when the FFT size changes; the owner re-runs the analysis.
    fftSizeChanged = Signal(int)

    #: Emitted when the dragged rectangle changes: ``(TimeRange | None,
    #: low_hz, high_hz)``, with the range in document frames. Both hertz
    #: values are zero when the selection is dropped.
    selectionChanged = Signal(object, float, float)

    #: Emitted when the user asks for the selected band to be turned down.
    attenuateRequested = Signal()

    #: Emitted when the user asks for the selected band to be removed.
    deleteRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAccessibleName("Spectral frequency display")
        self.spectrogram = SpectrogramWidget()
        self._offset_s = 0.0
        self._sample_rate = 0.0
        self._fft_size = 2048
        self._analysed_frames = 0
        self._selection: SpectralSelection | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_controls())
        layout.addWidget(self.spectrogram, 1)

        self.spectrogram.cursorMoved.connect(self._on_cursor)
        self.spectrogram.cursorLeft.connect(lambda: self.readoutChanged.emit(""))
        self.spectrogram.positionClicked.connect(
            lambda time_s, _hz: self.seekRequested.emit(self._offset_s + time_s)
        )
        self.spectrogram.regionChanged.connect(self._on_region)

    def _build_controls(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("SpectrumControls")

        self.colormap_box = QComboBox()
        self.colormap_box.addItems(COLORMAP_NAMES)
        self.colormap_box.setCurrentText(DEFAULT_COLORMAP)
        self.colormap_box.currentTextChanged.connect(self.spectrogram.set_colormap)

        self.scale_button = QPushButton("Log")
        self.scale_button.setCheckable(True)
        self.scale_button.setChecked(True)
        self.scale_button.setToolTip("Logarithmic or linear frequency axis")
        self.scale_button.toggled.connect(self._on_scale)

        self.range_box = QComboBox()
        self.range_box.addItems([label for label, _ in DB_RANGES])
        self.range_box.setCurrentIndex(1)
        self.range_box.currentIndexChanged.connect(self._on_range)

        self.fft_box = QComboBox()
        self.fft_box.addItems([str(size) for size in FFT_SIZES])
        self.fft_box.setCurrentText(str(self._fft_size))
        self.fft_box.setToolTip("FFT size: resolution in frequency against resolution in time")
        self.fft_box.currentTextChanged.connect(self._on_fft_size)

        self.auto_button = QPushButton("Auto")
        self.auto_button.setToolTip("Fit the dynamic range to what is on screen")
        self.auto_button.clicked.connect(lambda: self.spectrogram.auto_scale())

        self.attenuate_button = QPushButton("Attenuate")
        self.attenuate_button.setToolTip(
            f"Turn the selected band down by {abs(ATTENUATION_DB):.0f} dB"
        )
        self.attenuate_button.clicked.connect(self.attenuateRequested)

        self.delete_button = QPushButton("Delete")
        self.delete_button.setToolTip("Remove the selected band and resynthesise the rest")
        self.delete_button.clicked.connect(self.deleteRequested)

        self.info_label = QLabel("No spectral data")
        self.info_label.setObjectName("SecondaryTimecode")

        self.selection_label = QLabel("")
        self.selection_label.setObjectName("SecondaryTimecode")
        self.selection_label.setToolTip("Drag a box over the spectrogram to select a band")

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)
        for widget in (
            QLabel("Palette"), self.colormap_box,
            QLabel("Range"), self.range_box,
            QLabel("FFT"), self.fft_box,
            self.scale_button, self.auto_button,
            self.attenuate_button, self.delete_button,
        ):
            layout.addWidget(widget)
        layout.addSpacing(8)
        layout.addWidget(self.info_label, 1, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.selection_label, 0, Qt.AlignmentFlag.AlignRight)
        self._update_selection_ui()
        return bar

    # -- analysis ----------------------------------------------------------

    @property
    def fft_size(self) -> int:
        return self._fft_size

    @property
    def has_data(self) -> bool:
        return self._analysed_frames > 0

    @property
    def selection(self) -> SpectralSelection | None:
        """The dragged rectangle in document coordinates, or ``None``."""
        return self._selection

    @property
    def sample_rate(self) -> float:
        """Sample rate of the audio last analysed; ``0`` before the first one."""
        return self._sample_rate

    def clear_selection(self) -> None:
        self.spectrogram.clear_region()

    def analyze(
        self,
        audio: np.ndarray | None,
        sample_rate: float,
        offset_s: float = 0.0,
        channels_last: bool = True,
    ) -> None:
        """Transform ``audio`` and show it. ``None`` clears the view."""
        if audio is None or getattr(audio, "size", 0) == 0 or sample_rate <= 0:
            self.clear()
            return

        n_frames = audio.shape[0] if channels_last and audio.ndim == 2 else audio.shape[-1]
        config = analysis_config(sample_rate, int(n_frames), self._fft_size)
        analyzer = SpectralAnalyzer(config)
        spectrogram = analyzer.spectrogram(audio, channels_last=channels_last)

        self._offset_s = float(offset_s)
        self._sample_rate = float(sample_rate)
        self._analysed_frames = spectrogram.n_frames
        self.spectrogram.set_spectrogram(spectrogram)
        self.spectrogram.set_frequency_range(20.0, sample_rate / 2.0)
        self.info_label.setText(
            f"{config.fft_size}-pt {config.window.value} · "
            f"{config.frequency_resolution_hz:.1f} Hz · "
            f"{config.time_resolution_s * 1000:.0f} ms · "
            f"{spectrogram.n_frames} columns"
        )

    def clear(self) -> None:
        self._analysed_frames = 0
        self._offset_s = 0.0
        self._sample_rate = 0.0
        self.spectrogram.clear()
        self.info_label.setText("No spectral data")

    # -- slots -------------------------------------------------------------

    def _on_region(self, region: SpectralRegion | None) -> None:
        """Republish the widget's rectangle in frames on the document timeline."""
        if region is None or self._sample_rate <= 0:
            self._selection = None
            self._update_selection_ui()
            self.selectionChanged.emit(None, 0.0, 0.0)
            return

        rate = int(round(self._sample_rate))
        self._selection = SpectralSelection(
            TimeRange.from_seconds(
                self._offset_s + region.start_s, self._offset_s + region.end_s, rate
            ),
            region.low_hz,
            region.high_hz,
        )
        self._update_selection_ui()
        self.selectionChanged.emit(
            self._selection.time, self._selection.low_hz, self._selection.high_hz
        )

    def _update_selection_ui(self) -> None:
        selection = self._selection
        self.attenuate_button.setEnabled(selection is not None)
        self.delete_button.setEnabled(selection is not None)
        self.selection_label.setText(
            "" if selection is None else selection.describe(self._sample_rate)
        )

    def _on_scale(self, logarithmic: bool) -> None:
        self.scale_button.setText("Log" if logarithmic else "Linear")
        self.spectrogram.set_frequency_scale(
            FrequencyScale.LOG if logarithmic else FrequencyScale.LINEAR
        )

    def _on_range(self, index: int) -> None:
        _, floor_db = DB_RANGES[max(0, min(index, len(DB_RANGES) - 1))]
        self.spectrogram.set_db_range(floor_db, 0.0)

    def _on_fft_size(self, text: str) -> None:
        self._fft_size = int(text)
        self.fftSizeChanged.emit(self._fft_size)

    def _on_cursor(self, time_s: float, frequency_hz: float, level_db: float) -> None:
        self.readoutChanged.emit(
            f"{self._offset_s + time_s:7.3f} s   {frequency_hz:8.1f} Hz   {level_db:6.1f} dB"
        )
