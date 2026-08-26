"""Main application window: a DAW-style single-track editing surface."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QAction, QCloseEvent, QDragEnterEvent, QDropEvent, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from .. import __app_name__, __version__
from ..core.engine import AudioEngine
from ..core.loader import (
    SUPPORTED_EXTENSIONS,
    AudioLoadError,
    describe_backends,
    file_dialog_filter,
    save_audio,
)
from ..core.types import TimeRange, TransportState, format_timecode
from .level_meter import LevelMeter
from .theme import PALETTE, stylesheet
from .track_panel import TrackPanel
from .transport_bar import TransportBar

#: UI refresh rate for the playhead and the meters.
UI_REFRESH_MS: int = 33

MAX_RECENT_FILES: int = 8


class MainWindow(QMainWindow):
    """Hosts the engine and wires it to the editing widgets."""

    def __init__(self, engine: AudioEngine | None = None) -> None:
        super().__init__()
        self.engine = engine if engine is not None else AudioEngine()
        self._recent: list[Path] = []

        self.setWindowTitle(__app_name__)
        self.resize(1360, 780)
        self.setStyleSheet(stylesheet(PALETTE))
        self.setAcceptDrops(True)

        self.track_panel = TrackPanel()
        self.level_meter = LevelMeter(channels=2)
        self.transport_bar = TransportBar()

        self._build_central()
        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        self._build_statusbar()
        self._connect()

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(UI_REFRESH_MS)
        self._refresh_timer.timeout.connect(self._on_tick)
        self._refresh_timer.start()

        self._update_for_clip()

    # ----------------------------------------------------------- composition

    def _build_central(self) -> None:
        meter_column = QVBoxLayout()
        meter_column.setContentsMargins(6, 6, 6, 6)
        meter_column.setSpacing(4)
        meter_label = QLabel("OUT")
        meter_label.setObjectName("SecondaryTimecode")
        meter_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        meter_column.addWidget(meter_label)
        meter_column.addWidget(self.level_meter, 1)

        editor_row = QHBoxLayout()
        editor_row.setContentsMargins(0, 0, 0, 0)
        editor_row.setSpacing(0)
        editor_row.addWidget(self.track_panel, 1)
        editor_row.addLayout(meter_column)

        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addLayout(editor_row, 1)
        root.addWidget(self.transport_bar)

        central = QWidget()
        central.setLayout(root)
        self.setCentralWidget(central)

    def _build_actions(self) -> None:
        def action(
            text: str, slot, shortcut: QKeySequence | QKeySequence.StandardKey | str | None = None,
            *, checkable: bool = False, tip: str = "",
        ) -> QAction:
            act = QAction(text, self)
            if shortcut is not None:
                act.setShortcut(shortcut)
            act.setCheckable(checkable)
            if tip:
                act.setStatusTip(tip)
            act.triggered.connect(slot)
            self.addAction(act)
            return act

        self.action_open = action(
            "&Open…", self.open_file_dialog, QKeySequence.StandardKey.Open,
            tip="Open an audio file",
        )
        self.action_close = action("&Close", self.close_clip, QKeySequence.StandardKey.Close)
        self.action_export = action(
            "&Export As…", self.export_dialog, QKeySequence.StandardKey.SaveAs,
            tip="Write the clip (or the selection) to a new file",
        )
        self.action_quit = action("E&xit", self.close, QKeySequence.StandardKey.Quit)

        self.action_select_all = action(
            "Select &All", self.track_panel.waveform.select_all,
            QKeySequence.StandardKey.SelectAll,
        )
        self.action_deselect = action(
            "&Deselect", self.track_panel.waveform.clear_selection, "Ctrl+Shift+A"
        )

        self.action_zoom_in = action("Zoom &In", self.track_panel.waveform.zoom_in, "Ctrl+=")
        self.action_zoom_out = action("Zoom &Out", self.track_panel.waveform.zoom_out, "Ctrl+-")
        self.action_zoom_fit = action(
            "Zoom to &Fit", self.track_panel.waveform.zoom_to_fit, "Ctrl+0"
        )
        self.action_zoom_sel = action(
            "Zoom to &Selection", self.track_panel.waveform.zoom_to_selection, "Ctrl+Shift+0"
        )
        self.action_amp_up = action("Amplitude &Up", lambda: self._scale_amplitude(1.5), "Ctrl+Up")
        self.action_amp_down = action(
            "Amplitude &Down", lambda: self._scale_amplitude(1 / 1.5), "Ctrl+Down"
        )

        self.action_play = action("&Play / Pause", self._on_play_pause, "Space")
        self.action_stop = action("&Stop", self._on_stop, "Esc")
        self.action_home = action("Go to &Start", self._on_skip_start, "Home")
        self.action_end = action("Go to &End", self._on_skip_end, "End")
        self.action_loop = action("&Loop", self._on_loop_toggled, "L", checkable=True)
        self.action_sel_only = action(
            "Play Selection &Only", self._on_play_selection_only, checkable=True,
            tip="Restrict the transport to the selected range",
        )
        self.action_sel_only.setChecked(True)

        self.action_about = action("&About", self.show_about)

    def _build_menus(self) -> None:
        bar = self.menuBar()

        file_menu = bar.addMenu("&File")
        file_menu.addAction(self.action_open)
        self.recent_menu = file_menu.addMenu("Open &Recent")
        self.recent_menu.setEnabled(False)
        file_menu.addSeparator()
        file_menu.addAction(self.action_export)
        file_menu.addAction(self.action_close)
        file_menu.addSeparator()
        file_menu.addAction(self.action_quit)

        edit_menu = bar.addMenu("&Edit")
        edit_menu.addAction(self.action_select_all)
        edit_menu.addAction(self.action_deselect)

        view_menu = bar.addMenu("&View")
        view_menu.addAction(self.action_zoom_in)
        view_menu.addAction(self.action_zoom_out)
        view_menu.addAction(self.action_zoom_fit)
        view_menu.addAction(self.action_zoom_sel)
        view_menu.addSeparator()
        view_menu.addAction(self.action_amp_up)
        view_menu.addAction(self.action_amp_down)

        transport_menu = bar.addMenu("&Transport")
        transport_menu.addAction(self.action_play)
        transport_menu.addAction(self.action_stop)
        transport_menu.addAction(self.action_home)
        transport_menu.addAction(self.action_end)
        transport_menu.addSeparator()
        transport_menu.addAction(self.action_loop)
        transport_menu.addAction(self.action_sel_only)

        bar.addMenu("&Help").addAction(self.action_about)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        toolbar.addAction(self.action_open)
        toolbar.addAction(self.action_close)
        toolbar.addSeparator()
        toolbar.addAction(self.action_zoom_in)
        toolbar.addAction(self.action_zoom_out)
        toolbar.addAction(self.action_zoom_fit)
        toolbar.addAction(self.action_zoom_sel)
        toolbar.addSeparator()
        toolbar.addAction(self.action_select_all)
        toolbar.addAction(self.action_deselect)
        self.addToolBar(toolbar)

    def _build_statusbar(self) -> None:
        self.status_format = QLabel("No file")
        self.status_selection = QLabel("Selection: —")
        self.status_backend = QLabel(f"Output: {self.engine.output.name}")
        bar = self.statusBar()
        bar.addWidget(self.status_format, 1)
        bar.addPermanentWidget(self.status_selection)
        bar.addPermanentWidget(self.status_backend)

    def _connect(self) -> None:
        self.track_panel.seekRequested.connect(self._on_seek)
        self.track_panel.selectionChanged.connect(self._on_selection_changed)
        self.track_panel.muteToggled.connect(self._on_mute)

        self.transport_bar.playPauseRequested.connect(self._on_play_pause)
        self.transport_bar.stopRequested.connect(self._on_stop)
        self.transport_bar.skipToStartRequested.connect(self._on_skip_start)
        self.transport_bar.skipToEndRequested.connect(self._on_skip_end)
        self.transport_bar.loopToggled.connect(self._on_loop_toggled)
        self.transport_bar.volumeChanged.connect(self._on_volume)

        self.engine.add_state_listener(self._on_engine_state)

    # ----------------------------------------------------------- file access

    def open_file_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open audio file", str(Path.home()), file_dialog_filter()
        )
        if path:
            self.open_file(path)

    def open_file(self, path: str | Path) -> bool:
        """Load ``path`` into the editor; returns False and reports on failure."""
        try:
            clip = self.engine.load(path)
        except AudioLoadError as exc:
            QMessageBox.critical(self, "Cannot open file", str(exc))
            return False
        self._remember_recent(clip.path)
        self._update_for_clip()
        self.statusBar().showMessage(f"Loaded {clip.name}", 4000)
        return True

    def close_clip(self) -> None:
        self.engine.close_clip()
        self._update_for_clip()

    def export_dialog(self) -> None:
        clip = self.engine.clip
        if clip is None:
            return
        selection = self.engine.selection
        suggested = clip.path.with_name(f"{clip.path.stem}-export.wav")
        path, _ = QFileDialog.getSaveFileName(
            self, "Export audio", str(suggested), "WAV (*.wav);;FLAC (*.flac)"
        )
        if not path:
            return
        buffer = clip.buffer.slice(selection) if selection else clip.buffer
        try:
            written = save_audio(path, buffer)
        except AudioLoadError as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        self.statusBar().showMessage(f"Exported {written.name}", 4000)

    def _remember_recent(self, path: Path) -> None:
        resolved = path.resolve()
        if resolved in self._recent:
            self._recent.remove(resolved)
        self._recent.insert(0, resolved)
        del self._recent[MAX_RECENT_FILES:]

        self.recent_menu.clear()
        self.recent_menu.setEnabled(bool(self._recent))
        for entry in self._recent:
            act = QAction(entry.name, self)
            act.setStatusTip(str(entry))
            act.triggered.connect(lambda _checked=False, p=entry: self.open_file(p))
            self.recent_menu.addAction(act)

    # -------------------------------------------------------------- reactive

    def _update_for_clip(self) -> None:
        clip = self.engine.clip
        self.track_panel.set_clip(clip, self.engine.pyramid)
        has_clip = clip is not None

        self.transport_bar.set_enabled_for_clip(has_clip)
        self.transport_bar.set_duration(self.engine.duration)
        self.transport_bar.set_position(0.0)
        self.transport_bar.set_selection_text("—")
        self.level_meter.set_channels(max(self.engine.n_channels, 1))
        self.level_meter.reset()

        for act in (self.action_close, self.action_export, self.action_select_all):
            act.setEnabled(has_clip)

        if clip is None:
            self.setWindowTitle(__app_name__)
            self.status_format.setText("No file")
        else:
            self.setWindowTitle(f"{clip.name} — {__app_name__}")
            self.status_format.setText(
                f"{clip.name}  ·  {clip.audio_format.describe()}  ·  "
                f"{format_timecode(clip.duration)}  ·  {clip.buffer.n_frames:,} frames"
            )
        self.status_selection.setText("Selection: —")

    def _on_tick(self) -> None:
        """Poll the engine 30×/s: the audio threads never touch Qt objects."""
        if not self.engine.has_clip:
            return
        position = self.engine.position
        playing = self.engine.is_playing
        self.track_panel.set_playhead(position, follow=playing)
        self.transport_bar.set_position(position / max(self.engine.sample_rate, 1))

        levels = self.engine.levels
        if playing and not levels.is_empty:
            self.level_meter.update_levels(levels.peak, levels.rms)
        elif not self.level_meter.is_at_floor:
            # Keep feeding silence so the ballistics decay instead of freezing,
            # but stop repainting once the meter has bottomed out.
            self.level_meter.update_levels((0.0,) * self.level_meter.channels)

    @Slot(object)
    def _on_engine_state(self, state: TransportState) -> None:
        self.transport_bar.set_state(state)

    def _on_play_pause(self) -> None:
        if not self.engine.has_clip:
            return
        self.engine.toggle_play_pause()
        self.transport_bar.set_state(self.engine.state)

    def _on_stop(self) -> None:
        self.engine.stop()
        self.transport_bar.set_state(self.engine.state)
        self.track_panel.set_playhead(self.engine.position)
        self.level_meter.reset()

    def _on_seek(self, frame: int) -> None:
        position = self.engine.seek(frame)
        self.track_panel.set_playhead(position)
        self.track_panel.waveform.set_cursor_frame(position, emit=False)
        self.transport_bar.set_position(position / max(self.engine.sample_rate, 1))

    def _on_skip_start(self) -> None:
        region = self.engine.playback_region
        self._on_seek(region.start)

    def _on_skip_end(self) -> None:
        region = self.engine.playback_region
        self._on_seek(region.end)

    def _on_loop_toggled(self, enabled: bool | None = None) -> None:
        value = self.action_loop.isChecked() if enabled is None else bool(enabled)
        self.engine.loop = value
        self.action_loop.setChecked(value)
        self.transport_bar.loop_button.setChecked(value)

    def _on_play_selection_only(self) -> None:
        self.engine.play_selection_only = self.action_sel_only.isChecked()

    def _on_volume(self, volume: float) -> None:
        self.engine.volume = volume

    def _on_mute(self, muted: bool) -> None:
        self.engine.muted = muted

    def _on_selection_changed(self, selection: TimeRange | None) -> None:
        self.engine.set_selection(selection)
        if selection is None or selection.is_empty:
            self.transport_bar.set_selection_text("—")
            self.status_selection.setText("Selection: —")
            return
        rate = max(self.engine.sample_rate, 1)
        start, end = selection.to_seconds(rate)
        text = f"{format_timecode(start)} → {format_timecode(end)}"
        self.transport_bar.set_selection_text(format_timecode(end - start))
        self.status_selection.setText(f"Selection: {text} ({selection.length:,} frames)")

    def _scale_amplitude(self, factor: float) -> None:
        waveform = self.track_panel.waveform
        waveform.set_amplitude_scale(waveform.amplitude_scale * factor)

    # ----------------------------------------------------------- misc events

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            f"About {__app_name__}",
            f"<h3>{__app_name__} {__version__}</h3>"
            "<p>Professional audio editing and analysis workstation (MVP).</p>"
            f"<pre>{describe_backends()}\nOutput backend: {self.engine.output.name}</pre>",
        )

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802 - Qt override
        mime = event.mimeData()
        if mime.hasUrls() and any(
            Path(url.toLocalFile()).suffix.lower() in SUPPORTED_EXTENSIONS
            for url in mime.urls()
        ):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802 - Qt override
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if local and Path(local).suffix.lower() in SUPPORTED_EXTENSIONS:
                self.open_file(local)
                event.acceptProposedAction()
                return

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt override
        self._refresh_timer.stop()
        self.engine.shutdown()
        super().closeEvent(event)
