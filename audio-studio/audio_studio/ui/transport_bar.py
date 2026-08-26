"""Transport controls: record, play/pause/stop, skip, loop, timecode and gain."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..core.types import TransportState, format_timecode

#: Text glyphs stand in for icon assets in the MVP.
GLYPH_PLAY = "▶"
GLYPH_PAUSE = "❚❚"
GLYPH_STOP = "■"
GLYPH_START = "|◀"
GLYPH_END = "▶|"
GLYPH_LOOP = "⟲"
GLYPH_RECORD = "●"


def _button(text: str, tooltip: str, *, checkable: bool = False) -> QPushButton:
    button = QPushButton(text)
    button.setToolTip(tooltip)
    button.setCheckable(checkable)
    button.setFixedSize(44, 32)
    button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return button


class TransportBar(QWidget):
    """Bottom transport strip. Emits intent only; the window owns the engine."""

    playPauseRequested = Signal()
    recordRequested = Signal()
    stopRequested = Signal()
    skipToStartRequested = Signal()
    skipToEndRequested = Signal()
    loopToggled = Signal(bool)
    volumeChanged = Signal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._duration = 0.0
        self._selection_text = "—"
        self._has_clip = False

        self.record_button = _button(GLYPH_RECORD, "Start recording", checkable=True)
        self.record_button.setObjectName("RecordButton")
        self.record_button.setStyleSheet("color: #ef5350;")
        self.play_button = _button(GLYPH_PLAY, "Play / Pause (Space)")
        self.stop_button = _button(GLYPH_STOP, "Stop (Esc)")
        self.start_button = _button(GLYPH_START, "Go to start (Home)")
        self.end_button = _button(GLYPH_END, "Go to end (End)")
        self.loop_button = _button(GLYPH_LOOP, "Loop playback (L)", checkable=True)

        self.position_label = QLabel(format_timecode(0.0))
        self.position_label.setObjectName("TimecodeDisplay")
        self.position_label.setMinimumWidth(140)
        self.position_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.duration_label = QLabel("of 00:00.000")
        self.duration_label.setObjectName("SecondaryTimecode")
        self.selection_label = QLabel("Sel —")
        self.selection_label.setObjectName("SecondaryTimecode")

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 150)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(120)
        self.volume_slider.setToolTip("Output gain")
        self.volume_label = QLabel("100%")
        self.volume_label.setObjectName("SecondaryTimecode")
        self.volume_label.setFixedWidth(42)

        self._build_layout()
        self._connect()

    def _build_layout(self) -> None:
        info = QVBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(1)
        info.addWidget(self.duration_label)
        info.addWidget(self.selection_label)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)
        layout.addWidget(self.record_button)
        layout.addWidget(self.start_button)
        layout.addWidget(self.play_button)
        layout.addWidget(self.stop_button)
        layout.addWidget(self.end_button)
        layout.addWidget(self.loop_button)
        layout.addSpacing(10)
        layout.addWidget(self.position_label)
        layout.addLayout(info)
        layout.addStretch(1)
        layout.addWidget(separator)
        layout.addWidget(QLabel("Gain"))
        layout.addWidget(self.volume_slider)
        layout.addWidget(self.volume_label)

    def _connect(self) -> None:
        self.record_button.clicked.connect(lambda _checked=False: self.recordRequested.emit())
        self.play_button.clicked.connect(self.playPauseRequested)
        self.stop_button.clicked.connect(self.stopRequested)
        self.start_button.clicked.connect(self.skipToStartRequested)
        self.end_button.clicked.connect(self.skipToEndRequested)
        self.loop_button.toggled.connect(self.loopToggled)
        self.volume_slider.valueChanged.connect(self._on_volume)

    def _on_volume(self, value: int) -> None:
        self.volume_label.setText(f"{value}%")
        self.volumeChanged.emit(value / 100.0)

    def set_state(self, state: TransportState) -> None:
        playing = state is TransportState.PLAYING
        self.play_button.setText(GLYPH_PAUSE if playing else GLYPH_PLAY)
        self.play_button.setToolTip("Pause (Space)" if playing else "Play (Space)")

    def set_recording(self, recording: bool) -> None:
        """Reflect capture state and lock playback controls while recording."""
        self.record_button.setChecked(recording)
        self.record_button.setToolTip("Stop recording" if recording else "Start recording")
        enabled = self._has_clip and not recording
        for widget in (
            self.play_button,
            self.stop_button,
            self.start_button,
            self.end_button,
            self.loop_button,
        ):
            widget.setEnabled(enabled)

    def set_position(self, seconds: float) -> None:
        self.position_label.setText(format_timecode(seconds))

    def set_duration(self, seconds: float) -> None:
        self._duration = seconds
        self.duration_label.setText(f"of {format_timecode(seconds)}")

    def set_selection_text(self, text: str) -> None:
        self._selection_text = text
        self.selection_label.setText(f"Sel {text}")

    def set_enabled_for_clip(self, has_clip: bool) -> None:
        self._has_clip = has_clip
        self.set_recording(self.record_button.isChecked())
