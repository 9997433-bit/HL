"""Track lane: header controls on the left, ruler + waveform + scrollbar on the right.

Only a single lane exists in the MVP, but the widget is written as a reusable
track so a multi-track session view can stack instances of it later.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..core.loader import LoadedAudio
from ..core.markers import MarkerList
from ..core.peaks import PeakPyramid
from ..core.sample_source import SampleSource
from ..core.types import AudioFormat, TimeRange
from .theme import PALETTE, Palette
from .time_ruler import TimeRuler
from .waveform_view import WaveformView

HEADER_WIDTH: int = 172


class TrackHeader(QWidget):
    """Name, format summary and per-track toggles for one lane."""

    muteToggled = Signal(bool)
    soloToggled = Signal(bool)

    def __init__(self, parent: QWidget | None = None, palette: Palette = PALETTE) -> None:
        super().__init__(parent)
        self._palette = palette
        self.setFixedWidth(HEADER_WIDTH)
        self.setAutoFillBackground(True)
        self.setStyleSheet(
            f"background-color: {palette.surface}; border-right: 1px solid {palette.border};"
        )

        self.title = QLabel("No track")
        self.title.setObjectName("TrackTitle")
        self.title.setWordWrap(False)
        self.title.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.format_label = QLabel("—")
        self.format_label.setObjectName("SecondaryTimecode")
        self.format_label.setWordWrap(True)

        self.mute_button = QPushButton("M")
        self.mute_button.setCheckable(True)
        self.mute_button.setFixedSize(28, 24)
        self.mute_button.setToolTip("Mute")
        self.solo_button = QPushButton("S")
        self.solo_button.setCheckable(True)
        self.solo_button.setFixedSize(28, 24)
        self.solo_button.setToolTip("Solo (single-track MVP: no-op)")
        self.solo_button.setEnabled(False)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(4)
        buttons.addWidget(self.mute_button)
        buttons.addWidget(self.solo_button)
        buttons.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(self.title)
        layout.addWidget(self.format_label)
        layout.addLayout(buttons)
        layout.addStretch(1)

        self.mute_button.toggled.connect(self.muteToggled)
        self.solo_button.toggled.connect(self.soloToggled)

    def set_clip(self, clip: LoadedAudio | None) -> None:
        if clip is None:
            self.title.setText("No track")
            self.title.setToolTip("")
            self.format_label.setText("—")
            return
        self.title.setText(clip.name)
        self.title.setToolTip(str(clip.path))
        self.format_label.setText(clip.audio_format.describe().replace(" · ", "\n"))

    def set_stream(self, path: str | Path, audio_format: AudioFormat) -> None:
        path = Path(path)
        self.title.setText(path.name)
        self.title.setToolTip(str(path))
        self.format_label.setText(audio_format.describe().replace(" · ", "\n"))


class TrackPanel(QWidget):
    """One editable audio lane."""

    seekRequested = Signal(int)
    selectionChanged = Signal(object)
    muteToggled = Signal(bool)

    def __init__(self, parent: QWidget | None = None, palette: Palette = PALETTE) -> None:
        super().__init__(parent)
        self.header = TrackHeader(palette=palette)
        self.ruler = TimeRuler(palette=palette)
        self.waveform = WaveformView(palette=palette)

        self.scrollbar = QScrollBar(Qt.Orientation.Horizontal)
        self.scrollbar.setSingleStep(1)
        self.scrollbar.setEnabled(False)

        spacer = QFrame()
        spacer.setFixedWidth(HEADER_WIDTH)
        spacer.setFixedHeight(self.ruler.height())
        spacer.setStyleSheet(
            f"background-color: {palette.surface}; border-right: 1px solid {palette.border};"
        )

        ruler_row = QHBoxLayout()
        ruler_row.setContentsMargins(0, 0, 0, 0)
        ruler_row.setSpacing(0)
        ruler_row.addWidget(spacer)
        ruler_row.addWidget(self.ruler, 1)

        track_row = QHBoxLayout()
        track_row.setContentsMargins(0, 0, 0, 0)
        track_row.setSpacing(0)
        track_row.addWidget(self.header)
        track_row.addWidget(self.waveform, 1)

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
        layout.addLayout(track_row, 1)
        layout.addLayout(scroll_row)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.waveform.viewChanged.connect(self._on_view_changed)
        self.waveform.seekRequested.connect(self.seekRequested)
        self.waveform.selectionChanged.connect(self.selectionChanged)
        self.ruler.seekRequested.connect(self.seekRequested)
        self.scrollbar.valueChanged.connect(self._on_scroll)
        self.header.muteToggled.connect(self.muteToggled)

        self._syncing = False

    def set_clip(
        self,
        clip: LoadedAudio | None,
        pyramid: PeakPyramid | None,
        *,
        samples: np.ndarray | None = None,
    ) -> None:
        self.header.set_clip(clip)
        sample_rate = clip.buffer.sample_rate if clip else 44100
        if samples is None and clip is not None:
            samples = clip.buffer.data
        self.ruler.set_sample_rate(sample_rate)
        self.waveform.set_clip(pyramid, sample_rate, samples)
        self._on_view_changed(self.waveform.view_start, self.waveform.view_frames)

    def set_stream(
        self,
        path: str | Path,
        audio_format: AudioFormat,
        n_frames: int,
        pyramid: PeakPyramid | None,
        source: SampleSource,
    ) -> None:
        """Attach cached overview peaks and bounded on-demand detail reads."""
        self.header.set_stream(path, audio_format)
        self.ruler.set_sample_rate(source.sample_rate)
        self.waveform.set_clip(
            pyramid,
            source.sample_rate,
            sample_source=source,
            n_frames=n_frames,
        )
        self._on_view_changed(self.waveform.view_start, self.waveform.view_frames)

    def set_playhead(self, frame: float, *, follow: bool = False) -> None:
        """Move the playhead; ``frame`` may be fractional.

        The waveform keeps the fraction, which is what makes an interpolated
        playhead glide; the ruler only draws a timecode and rounds it away.
        """
        self.waveform.set_playhead(frame, follow=follow)
        self.ruler.set_playhead(int(frame))

    def set_selection(self, selection: TimeRange | None) -> None:
        self.waveform.set_selection(selection)

    def set_markers(self, markers: MarkerList | None) -> None:
        self.waveform.set_markers(markers)

    def _on_view_changed(self, view_start: int, view_frames: int) -> None:
        self.ruler.set_view(view_start, view_frames)
        total = self.waveform.n_frames
        self._syncing = True
        try:
            if total > view_frames > 0:
                self.scrollbar.setEnabled(True)
                self.scrollbar.setRange(0, total - view_frames)
                self.scrollbar.setPageStep(view_frames)
                self.scrollbar.setSingleStep(max(view_frames // 20, 1))
                self.scrollbar.setValue(view_start)
            else:
                self.scrollbar.setEnabled(False)
                self.scrollbar.setRange(0, 0)
        finally:
            self._syncing = False

    def _on_scroll(self, value: int) -> None:
        if not self._syncing:
            self.waveform.scroll_to(value)
