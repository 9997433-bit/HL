"""Main application window: a DAW-style single-track editing surface.

Three views share the window: the waveform lane in the centre, a dockable
spectral display, and a dockable effect rack. The rack is a *preview* insert —
it is spliced into the engine's output path (see
:class:`~audio_studio.dsp.preview.EffectPreview`) and changes what is heard
without touching the clip in memory.

Analysis that costs real time — the spectrogram transform, the BS.1770
integrated loudness — never runs on the Qt thread while the user waits.
Loudness is measured on a worker and collected by the same 30 Hz tick that
drives the playhead; the spectrogram is coalesced behind a short timer so that
dragging a selection re-analyses once rather than on every mouse move.
"""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import (
    QAction,
    QActionGroup,
    QCloseEvent,
    QDragEnterEvent,
    QDropEvent,
    QKeySequence,
)
from PyQt6.QtWidgets import (
    QDockWidget,
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
from ..dsp.loudness import LoudnessMeter, LoudnessReport, format_lufs
from ..dsp.preview import EffectPreview
from .effect_rack import EffectRackPanel, default_preview_chain
from .level_meter import LevelMeter
from .spectrum_panel import SpectrumPanel
from .theme import PALETTE, stylesheet
from .track_panel import TrackPanel
from .transport_bar import TransportBar

#: UI refresh rate for the playhead and the meters.
UI_REFRESH_MS: int = 33

#: Delay before a changed selection is re-analysed, in milliseconds. Long
#: enough that a drag produces one transform, short enough to feel immediate.
ANALYSIS_DEBOUNCE_MS: int = 250

MAX_RECENT_FILES: int = 8


class MainWindow(QMainWindow):
    """Hosts the engine and wires it to the editing widgets."""

    def __init__(self, engine: AudioEngine | None = None) -> None:
        super().__init__()
        self.effect_chain = default_preview_chain()
        self.engine = engine if engine is not None else AudioEngine()
        self.preview = attach_preview(self.engine, self.effect_chain)
        self._recent: list[Path] = []

        self.setWindowTitle(__app_name__)
        self.resize(1360, 780)
        self.setStyleSheet(stylesheet(PALETTE))
        self.setAcceptDrops(True)

        self.track_panel = TrackPanel()
        self.level_meter = LevelMeter(channels=2)
        self.transport_bar = TransportBar()
        self.spectrum_panel = SpectrumPanel()
        self.effect_rack = EffectRackPanel(self.effect_chain)

        self._loudness_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="loudness")
        self._loudness_job: Future[LoudnessReport] | None = None
        self.loudness: LoudnessReport | None = None

        self._build_central()
        self._build_docks()
        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        self._build_statusbar()
        self._connect()

        self._analysis_timer = QTimer(self)
        self._analysis_timer.setSingleShot(True)
        self._analysis_timer.setInterval(ANALYSIS_DEBOUNCE_MS)
        self._analysis_timer.timeout.connect(self.analyze_spectrum)

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
        self.editor_widget = central

    def _build_docks(self) -> None:
        """Spectral display along the bottom, effect rack down the right."""
        self.spectrum_dock = QDockWidget("Spectral Frequency Display", self)
        self.spectrum_dock.setObjectName("SpectrumDock")
        self.spectrum_dock.setWidget(self.spectrum_panel)
        self.spectrum_dock.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.TopDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.spectrum_dock)

        self.effects_dock = QDockWidget("Effects Rack", self)
        self.effects_dock.setObjectName("EffectsDock")
        self.effects_dock.setWidget(self.effect_rack)
        self.effects_dock.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.effects_dock)
        self.resizeDocks([self.spectrum_dock], [320], Qt.Orientation.Vertical)

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

        # Layout modes are exclusive: the spectral view can take over the
        # window, sit under the waveform, or be out of the way entirely.
        self.layout_group = QActionGroup(self)
        self.layout_group.setExclusive(True)
        self.action_view_waveform = action(
            "&Waveform", lambda: self.set_view_mode("waveform"), "Alt+1", checkable=True,
            tip="Waveform editor only",
        )
        self.action_view_spectrum = action(
            "&Spectral", lambda: self.set_view_mode("spectrum"), "Alt+2", checkable=True,
            tip="Spectral frequency display only",
        )
        self.action_view_split = action(
            "S&plit", lambda: self.set_view_mode("split"), "Alt+3", checkable=True,
            tip="Waveform above, spectral display below",
        )
        for act in (self.action_view_waveform, self.action_view_spectrum, self.action_view_split):
            self.layout_group.addAction(act)
        self.action_view_split.setChecked(True)

        self.action_analyze = action(
            "&Analyze Now", self.analyze_spectrum, "F5",
            tip="Re-run the spectral analysis over the selection (or the whole clip)",
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
        view_menu.addSeparator()
        view_menu.addAction(self.action_view_waveform)
        view_menu.addAction(self.action_view_spectrum)
        view_menu.addAction(self.action_view_split)
        view_menu.addSeparator()
        view_menu.addAction(self.spectrum_dock.toggleViewAction())
        view_menu.addAction(self.effects_dock.toggleViewAction())
        view_menu.addAction(self.action_analyze)

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
        self.status_loudness = QLabel("Loudness: —")
        self.status_loudness.setToolTip(
            "ITU-R BS.1770 integrated loudness and true peak of the loaded clip"
        )
        self.status_fx = QLabel(self.effect_rack.summary())
        self.status_backend = QLabel(f"Output: {self.engine.output.name}")
        bar = self.statusBar()
        bar.addWidget(self.status_format, 1)
        bar.addPermanentWidget(self.status_loudness)
        bar.addPermanentWidget(self.status_fx)
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

        self.spectrum_panel.seekRequested.connect(self._on_spectrum_seek)
        self.spectrum_panel.readoutChanged.connect(self._on_spectrum_readout)
        self.spectrum_panel.fftSizeChanged.connect(lambda _size: self.analyze_spectrum())
        self.effect_rack.chainChanged.connect(self._on_chain_changed)

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

    # ---------------------------------------------------------- analysis

    def audio_range(self, start: int, stop: int) -> np.ndarray | None:
        """Interleaved frames ``[start, stop)`` of the loaded audio, or ``None``.

        Reads through the engine's sample source when there is one, so a clip
        streamed off disk analyses the same way as one held in memory.
        """
        start, stop = max(0, int(start)), min(int(stop), self.engine.n_frames)
        if stop <= start:
            return None
        source = getattr(self.engine, "source", None)
        if source is not None:
            return source.read(start, stop - start)
        clip = self.engine.clip
        return None if clip is None else clip.buffer.data[start:stop]

    def analysis_region(self) -> TimeRange:
        """What the spectral view shows: the selection, else the whole clip."""
        selection = self.engine.selection
        if selection is not None and not selection.is_empty:
            return selection
        return TimeRange(0, self.engine.n_frames)

    def analyze_spectrum(self) -> None:
        """Re-run the spectrogram over the current analysis region."""
        self._analysis_timer.stop()
        region = self.analysis_region()
        audio = self.audio_range(region.start, region.end)
        if audio is None:
            self.spectrum_panel.clear()
            return
        self.spectrum_panel.analyze(
            audio,
            sample_rate=self.engine.sample_rate,
            offset_s=region.start / max(self.engine.sample_rate, 1),
            channels_last=True,
        )

    def measure_loudness(self) -> None:
        """Start a BS.1770 measurement of the whole clip on a worker thread.

        A ten-minute file takes over a second to K-weight and gate, which is
        far too long to spend inside a slot. The result is collected by
        :meth:`_on_tick`.
        """
        self._loudness_job = None
        self.loudness = None
        audio = self.audio_range(0, self.engine.n_frames)
        rate = self.engine.sample_rate
        if audio is None or rate <= 0:
            self.status_loudness.setText("Loudness: —")
            return
        self.status_loudness.setText("Loudness: measuring…")
        meter = LoudnessMeter(rate)
        self._loudness_job = self._loudness_pool.submit(
            meter.analyze, audio, channels_last=True
        )

    def _collect_loudness(self) -> None:
        job = self._loudness_job
        if job is None or not job.done():
            return
        self._loudness_job = None
        try:
            self.loudness = job.result()
        except Exception as exc:  # noqa: BLE001 - a failed measurement is not fatal
            self.status_loudness.setText("Loudness: unavailable")
            self.status_loudness.setToolTip(str(exc))
            return
        report = self.loudness
        self.status_loudness.setText(
            f"{format_lufs(report.integrated_lufs)}  ·  {report.true_peak_dbtp:.1f} dBTP"
        )
        self.status_loudness.setToolTip(
            f"Integrated {format_lufs(report.integrated_lufs)} (ITU-R BS.1770)\n"
            f"Short-term max {format_lufs(report.short_term_max_lufs)}\n"
            f"Momentary max {format_lufs(report.momentary_max_lufs)}\n"
            f"Loudness range {report.loudness_range_lu:.1f} LU\n"
            f"True peak {report.true_peak_dbtp:.2f} dBTP  ·  "
            f"sample peak {report.sample_peak_dbfs:.2f} dBFS"
        )

    # -------------------------------------------------------------- layout

    def set_view_mode(self, mode: str) -> None:
        """Switch between ``"waveform"``, ``"spectrum"`` and ``"split"``."""
        if mode not in ("waveform", "spectrum", "split"):
            raise ValueError(f"unknown view mode {mode!r}")
        self._view_mode = mode
        self.editor_widget.setVisible(mode != "spectrum")
        self.spectrum_dock.setVisible(mode != "waveform")
        action = {
            "waveform": self.action_view_waveform,
            "spectrum": self.action_view_spectrum,
            "split": self.action_view_split,
        }[mode]
        if not action.isChecked():
            action.setChecked(True)
        if mode != "waveform" and not self.spectrum_panel.has_data:
            self.analyze_spectrum()

    @property
    def view_mode(self) -> str:
        return getattr(self, "_view_mode", "split")

    # -------------------------------------------------------------- reactive

    def _update_for_clip(self) -> None:
        clip = self.engine.clip
        self.track_panel.set_clip(clip, self.engine.pyramid)
        has_clip = self.engine.has_clip

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
        self.analyze_spectrum()
        self.measure_loudness()

    def _on_tick(self) -> None:
        """Poll the engine 30×/s: the audio threads never touch Qt objects."""
        self._collect_loudness()
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

    @pyqtSlot(object)
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
        # Coalesce: a drag emits a selection per mouse move, and each one would
        # otherwise start a transform over the range.
        self._analysis_timer.start()
        if selection is None or selection.is_empty:
            self.transport_bar.set_selection_text("—")
            self.status_selection.setText("Selection: —")
            return
        rate = max(self.engine.sample_rate, 1)
        start, end = selection.to_seconds(rate)
        text = f"{format_timecode(start)} → {format_timecode(end)}"
        self.transport_bar.set_selection_text(format_timecode(end - start))
        self.status_selection.setText(f"Selection: {text} ({selection.length:,} frames)")

    def _on_spectrum_seek(self, time_s: float) -> None:
        self._on_seek(int(round(time_s * max(self.engine.sample_rate, 1))))

    def _on_spectrum_readout(self, text: str) -> None:
        if text:
            self.statusBar().showMessage(text)
        else:
            self.statusBar().clearMessage()

    def _on_chain_changed(self) -> None:
        self.status_fx.setText(self.effect_rack.summary())

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
        self._analysis_timer.stop()
        self.engine.shutdown()
        self._loudness_pool.shutdown(wait=False, cancel_futures=True)
        super().closeEvent(event)


def attach_preview(engine: AudioEngine, chain=None) -> EffectPreview:
    """Insert a live effect rack between ``engine`` and its output device.

    The engine hands its render callback to whatever backend it holds, so
    wrapping the backend is all it takes — no transport code changes and no
    second audio path to keep in sync. An engine that is already previewing
    keeps its wrapper and is simply pointed at the new chain.
    """
    existing = engine.output
    if isinstance(existing, EffectPreview):
        if chain is not None:
            existing.chain = chain
        return existing

    preview = EffectPreview(existing, chain)
    setter = getattr(engine, "set_output", None)
    if callable(setter):
        setter(preview)
    else:
        # AudioEngine takes its backend at construction and exposes no setter;
        # this is the one place that knows about the attribute behind it.
        engine._output = preview  # noqa: SLF001
    return preview
