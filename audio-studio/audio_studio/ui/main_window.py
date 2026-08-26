"""Main application window: a DAW-style editing surface with two workspaces.

The window hosts the two halves of the application side by side, exactly as
Audition does. The **waveform** workspace is the destructive editor: one clip,
one lane, a dockable spectral display and a dockable effect rack. The
**multitrack** workspace (View ▸ Multitrack Mode) is the non-destructive one:
a :class:`~audio_studio.core.session.MultitrackSession` of tracks and clip
references, drawn by :class:`~audio_studio.ui.multitrack_view.MultitrackView`.

Switching between them re-points the transport rather than duplicating it —
the session's mixer is a ``SampleSource`` like any other, so it reaches the
device through the same feeder, the same ring buffer and the same effect
preview insert. The rack is a *preview*: it is spliced into the engine's output
path (see :class:`~audio_studio.dsp.preview.EffectPreview`) and changes what is
heard without touching the audio in memory.

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
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QCloseEvent,
    QDragEnterEvent,
    QDropEvent,
    QKeySequence,
)
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from .. import __app_name__, __version__
from ..core.engine import AudioEngine
from ..core.edit_session import EditError, EditSession
from ..core.loader import (
    SUPPORTED_EXTENSIONS,
    AudioLoadError,
    LoadedAudio,
    describe_backends,
    file_dialog_filter,
    save_audio,
)
from ..core.peaks import PeakPyramid
from ..core.sample_source import MemorySampleSource
from ..core.session import MultitrackSession, Track
from ..core.types import TimeRange, TransportState, format_timecode
from ..dsp.loudness import LoudnessMeter, LoudnessReport, format_lufs
from ..dsp.preview import EffectPreview
from ..project.store import (
    ProjectLoadError,
    ProjectSnapshot,
    load_project,
    load_waveform_document,
    restore_multitrack,
    save_project,
)
from .effect_rack import EffectRackPanel, default_preview_chain
from .level_meter import LevelMeter
from .multitrack_view import MultitrackView
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

        self.session = MultitrackSession()
        self.multitrack_view = MultitrackView(self.session)
        self._workspace = "waveform"
        # The clip the waveform editor owns. Held separately because the engine
        # forgets it while the transport is pointed at the session mixer.
        self._editor_clip: LoadedAudio | None = None
        self._edit_session: EditSession | None = None
        self._project_path: Path | None = None
        self._project_dirty: bool = False

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

        # The two workspaces are siblings rather than stacked pages so that the
        # transport bar and the output meter stay put across a mode switch.
        self.waveform_page = QWidget()
        self.waveform_page.setLayout(editor_row)
        self.multitrack_view.hide()

        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.waveform_page, 1)
        root.addWidget(self.multitrack_view, 1)
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
        self.action_save_project = action(
            "Save &Project", self.save_project, "Ctrl+Shift+S",
            tip="Save the session to an .hlproj project bundle",
        )
        self.action_save_project_as = action(
            "Save Project &As…", self.save_project_as, "Ctrl+Alt+S",
            tip="Save the session to a new .hlproj directory",
        )
        self.action_open_project = action(
            "Open &Project…", self.open_project_dialog, "Ctrl+Shift+O",
            tip="Open an .hlproj project bundle",
        )
        self.action_quit = action("E&xit", self.close, QKeySequence.StandardKey.Quit)

        self.action_select_all = action(
            "Select &All", self.track_panel.waveform.select_all,
            QKeySequence.StandardKey.SelectAll,
        )
        self.action_deselect = action(
            "&Deselect", self.track_panel.waveform.clear_selection, "Ctrl+Shift+A"
        )

        self.action_undo = action(
            "&Undo", self.edit_undo, QKeySequence.StandardKey.Undo,
            tip="Undo the last edit",
        )
        self.action_redo = action(
            "&Redo", self.edit_redo, QKeySequence.StandardKey.Redo,
            tip="Redo the last undone edit",
        )
        self.action_cut = action(
            "Cu&t", self.edit_cut, QKeySequence.StandardKey.Cut,
            tip="Cut the selection to the clipboard",
        )
        self.action_copy = action(
            "&Copy", self.edit_copy, QKeySequence.StandardKey.Copy,
            tip="Copy the selection to the clipboard",
        )
        self.action_paste = action(
            "&Paste", self.edit_paste, QKeySequence.StandardKey.Paste,
            tip="Paste the clipboard at the playhead",
        )
        self.action_delete = action(
            "&Delete", self.edit_delete, QKeySequence.StandardKey.Delete,
            tip="Delete the selected range",
        )
        self.action_silence = action(
            "&Silence", self.edit_silence, "Ctrl+Shift+M",
            tip="Replace the selection with digital silence",
        )
        self.action_trim = action(
            "Trim to &Selection", self.edit_trim, "Ctrl+T",
            tip="Keep only the selected range",
        )
        self.action_gain = action(
            "Apply &Gain…", self.edit_gain, "Ctrl+G",
            tip="Change the level of the selection in decibels",
        )
        self.action_fade_in = action(
            "Fade &In", self.edit_fade_in, "Ctrl+Shift+I",
            tip="Apply a cosine fade-in across the selection",
        )
        self.action_fade_out = action(
            "Fade O&ut", self.edit_fade_out, "Ctrl+Shift+U",
            tip="Apply a cosine fade-out across the selection",
        )
        self.action_reverse = action(
            "&Reverse", self.edit_reverse, "Ctrl+R",
            tip="Reverse the selected audio",
        )
        self.action_insert_silence = action(
            "Insert &Silence…", self.edit_insert_silence, "Ctrl+Shift+N",
            tip="Insert silence at the playhead",
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

        # The workspace switch is orthogonal to the layout modes above: it
        # chooses which *document* is on screen, not how it is laid out.
        self.action_multitrack = action(
            "&Multitrack Mode", self._on_multitrack_toggled, "Alt+4", checkable=True,
            tip="Switch between the waveform editor and the multitrack session",
        )
        self.action_add_track = action(
            "Add Clip as &Track", self.add_clip_as_track, "Ctrl+Shift+T",
            tip="Place the loaded clip on a new multitrack lane",
        )
        self.action_mt_zoom_in = action(
            "Multitrack Zoom I&n", self.multitrack_view.zoom_in, "Alt+="
        )
        self.action_mt_zoom_out = action(
            "Multitrack Zoom O&ut", self.multitrack_view.zoom_out, "Alt+-"
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
        file_menu.addSeparator()
        file_menu.addAction(self.action_open_project)
        file_menu.addAction(self.action_save_project)
        file_menu.addAction(self.action_save_project_as)
        file_menu.addSeparator()
        file_menu.addAction(self.action_close)
        file_menu.addSeparator()
        file_menu.addAction(self.action_quit)

        edit_menu = bar.addMenu("&Edit")
        edit_menu.addAction(self.action_undo)
        edit_menu.addAction(self.action_redo)
        edit_menu.addSeparator()
        edit_menu.addAction(self.action_cut)
        edit_menu.addAction(self.action_copy)
        edit_menu.addAction(self.action_paste)
        edit_menu.addAction(self.action_delete)
        edit_menu.addSeparator()
        edit_menu.addAction(self.action_silence)
        edit_menu.addAction(self.action_trim)
        edit_menu.addSeparator()
        edit_menu.addAction(self.action_gain)
        edit_menu.addAction(self.action_fade_in)
        edit_menu.addAction(self.action_fade_out)
        edit_menu.addAction(self.action_reverse)
        edit_menu.addAction(self.action_insert_silence)
        edit_menu.addSeparator()
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
        view_menu.addAction(self.action_multitrack)
        view_menu.addAction(self.action_add_track)
        view_menu.addAction(self.action_mt_zoom_in)
        view_menu.addAction(self.action_mt_zoom_out)
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
        toolbar.addSeparator()
        toolbar.addAction(self.action_undo)
        toolbar.addAction(self.action_redo)
        toolbar.addAction(self.action_cut)
        toolbar.addAction(self.action_copy)
        toolbar.addAction(self.action_paste)
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

        self.multitrack_view.seekRequested.connect(self._on_seek)
        self.multitrack_view.sessionChanged.connect(self._on_session_edited)

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
        if not self._confirm_discard_unsaved(action="opening another file"):
            return False
        try:
            clip = self.engine.load(path)
        except AudioLoadError as exc:
            QMessageBox.critical(self, "Cannot open file", str(exc))
            return False
        self._project_path = None
        self._project_dirty = False
        self._bind_edit_session(clip)
        self._remember_recent(clip.path)
        self._update_for_clip()
        self.statusBar().showMessage(f"Loaded {clip.name}", 4000)
        return True

    def close_clip(self) -> None:
        self._clear_edit_session()
        self.engine.close_clip()
        self._editor_clip = None
        self._update_for_clip()

    def export_dialog(self) -> None:
        clip = self.editor_clip
        if clip is None:
            return
        selection = self.engine.selection if not self.is_playing_session else None
        suggested = clip.path.with_name(f"{clip.path.stem}-export.wav")
        path, _ = QFileDialog.getSaveFileName(
            self, "Export audio", str(suggested), "WAV (*.wav);;FLAC (*.flac)"
        )
        if not path:
            return
        if self._edit_session is not None and not self.is_playing_session:
            buffer = self._edit_session.to_buffer(selection)
        else:
            buffer = clip.buffer.slice(selection) if selection else clip.buffer
        try:
            written = save_audio(path, buffer)
        except AudioLoadError as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        if self._edit_session is not None and selection is None:
            self._edit_session.undo_stack.set_clean()
            self._update_window_title()
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

    def open_project_dialog(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Open project (.hlproj folder)",
            str(self._project_path.parent if self._project_path else Path.home()),
        )
        if not path:
            return
        self._open_project(Path(path))

    def _open_project(self, path: Path) -> bool:
        if not self._confirm_discard_unsaved(action="opening a project"):
            return False
        root = path if path.suffix.lower() == ".hlproj" else path.with_suffix(".hlproj")
        try:
            snapshot = load_project(root)
        except ProjectLoadError as exc:
            QMessageBox.critical(self, "Cannot open project", str(exc))
            return False
        try:
            self._apply_project(root, snapshot)
        except ProjectLoadError as exc:
            QMessageBox.critical(self, "Cannot open project", str(exc))
            return False
        self.statusBar().showMessage(f"Opened project {root.name}", 4000)
        return True

    def _apply_project(self, path: Path, snapshot: ProjectSnapshot) -> None:
        """Replace the current session with the contents of a project bundle."""
        self.engine.stop()
        self._clear_edit_session()
        self._editor_clip = None

        self.session = restore_multitrack(snapshot.multitrack, path)
        self.multitrack_view.set_session(self.session)

        if snapshot.waveform is not None:
            clip, session, playhead, selection = load_waveform_document(snapshot)
            session.add_listener(self._on_edit_session_changed)
            self._edit_session = session
            self._editor_clip = clip
            self._install_editor_source(clip)
            self.engine.seek(playhead)
            self.engine.set_selection(selection)
            self.track_panel.set_selection(selection)
            self.track_panel.set_playhead(playhead, follow=False)
        else:
            self.engine.set_source(None)

        self._project_path = path
        self._mark_project_saved()
        self.set_view_mode(snapshot.view_mode)
        self.set_workspace(snapshot.workspace)
        self._update_for_clip()

    def save_project(self) -> bool:
        if self._project_path is None:
            return self.save_project_as()
        try:
            saved = self._write_project(self._project_path)
        except OSError as exc:
            QMessageBox.critical(self, "Save failed", str(exc))
            return False
        self._project_path = saved
        self._mark_project_saved()
        self.statusBar().showMessage(f"Saved project {saved.name}", 4000)
        return True

    def save_project_as(self) -> bool:
        suggested = (
            self._project_path
            if self._project_path is not None
            else Path.home() / "Untitled.hlproj"
        )
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save project as",
            str(suggested),
            "Audio Studio Project (*.hlproj)",
        )
        if not path:
            return False
        try:
            saved = self._write_project(Path(path))
        except OSError as exc:
            QMessageBox.critical(self, "Save failed", str(exc))
            return False
        self._project_path = saved
        self._mark_project_saved()
        self.statusBar().showMessage(f"Saved project {saved.name}", 4000)
        return True

    def _write_project(self, path: Path) -> Path:
        playhead = self.engine.position if not self.is_playing_session else 0
        selection = self.engine.selection if not self.is_playing_session else None
        return save_project(
            path,
            edit_session=self._edit_session,
            editor_clip=self._editor_clip,
            multitrack=self.session,
            workspace=self._workspace,
            view_mode=self.view_mode,
            playhead=playhead,
            selection=selection,
        )

    def _has_unsaved_changes(self) -> bool:
        if self._project_dirty:
            return True
        return self._edit_session is not None and self._edit_session.is_modified

    def _mark_project_dirty(self) -> None:
        self._project_dirty = True
        self._update_window_title()

    def _mark_project_saved(self) -> None:
        self._project_dirty = False
        if self._edit_session is not None:
            self._edit_session.undo_stack.set_clean()
        self._update_window_title()

    def _confirm_discard_unsaved(self, *, action: str = "continue") -> bool:
        if not self._has_unsaved_changes():
            return True
        reply = QMessageBox.question(
            self,
            "Unsaved changes",
            f"You have unsaved changes. Save before {action}?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if reply == QMessageBox.StandardButton.Cancel:
            return False
        if reply == QMessageBox.StandardButton.Save and not self.save_project():
            return False
        return True

    # ----------------------------------------------------------- editing

    def _clear_edit_session(self) -> None:
        if self._edit_session is None:
            return
        self._edit_session.remove_listener(self._on_edit_session_changed)
        self._edit_session = None

    def _bind_edit_session(self, clip: LoadedAudio) -> None:
        """Wrap the loaded clip in an :class:`EditSession` wired to the transport."""
        self._clear_edit_session()
        session = EditSession.from_buffer(clip.buffer)
        session.add_listener(self._on_edit_session_changed)
        self._edit_session = session
        self._editor_clip = clip
        self._install_editor_source(clip)

    def _install_editor_source(self, clip: LoadedAudio) -> None:
        session = self._edit_session
        if session is None:
            self.engine.set_clip(clip)
            return
        pyramid, samples = self._waveform_cache(session)
        self.engine.set_source(
            session,
            clip=clip,
            audio_format=clip.audio_format,
            pyramid=pyramid,
            owns_source=False,
        )
        session.undo_stack.set_clean()

    def _restore_editor_source(self) -> None:
        clip = self._editor_clip
        if clip is None:
            self.engine.set_source(None)
            return
        if self._edit_session is not None:
            self._install_editor_source(clip)
        else:
            self.engine.set_clip(clip)

    @staticmethod
    def _waveform_cache(session: EditSession) -> tuple[PeakPyramid | None, np.ndarray | None]:
        n_frames = session.n_frames
        if n_frames <= 0:
            return None, None
        samples = session.read(0, n_frames)
        return PeakPyramid(samples), samples

    def _on_edit_session_changed(self, _session: EditSession) -> None:
        if self._workspace != "waveform" or self.is_playing_session:
            self._update_edit_actions()
            return
        clip = self._editor_clip
        if clip is None:
            return
        pyramid, samples = self._waveform_cache(_session)
        self.engine.update_pyramid(pyramid)
        self.track_panel.set_clip(clip, pyramid, samples=samples)
        self.transport_bar.set_duration(self.engine.duration)

        selection = self.engine.selection
        if selection is not None:
            clipped = selection.clamped(self.engine.n_frames)
            if clipped != selection:
                self.engine.set_selection(clipped if not clipped.is_empty else None)
                self.track_panel.set_selection(self.engine.selection)

        position = min(self.engine.position, max(self.engine.n_frames - 1, 0))
        if position != self.engine.position:
            self.engine.seek(position)

        self._update_edit_actions()
        self._update_window_title()
        self._update_status_format()
        self._analysis_timer.start()

    def _update_edit_actions(self) -> None:
        session = self._edit_session
        editing = (
            session is not None
            and self._workspace == "waveform"
            and not self.is_playing_session
            and self.engine.has_clip
        )
        selection = self.engine.selection
        has_selection = selection is not None and not selection.is_empty
        has_clipboard = (
            editing
            and session is not None
            and session.clipboard is not None
            and session.clipboard.n_frames > 0
        )

        self.action_undo.setEnabled(editing and session.can_undo)
        self.action_redo.setEnabled(editing and session.can_redo)
        undo_label = session.undo_stack.undo_label if session else None
        redo_label = session.undo_stack.redo_label if session else None
        self.action_undo.setText(f"&Undo {undo_label}" if undo_label else "&Undo")
        self.action_redo.setText(f"&Redo {redo_label}" if redo_label else "&Redo")

        for act in (
            self.action_cut,
            self.action_copy,
            self.action_delete,
            self.action_silence,
            self.action_trim,
            self.action_gain,
            self.action_fade_in,
            self.action_fade_out,
            self.action_reverse,
        ):
            act.setEnabled(editing and has_selection)
        self.action_paste.setEnabled(editing and has_clipboard)
        self.action_insert_silence.setEnabled(editing)

    def _update_window_title(self) -> None:
        clip = self.editor_clip
        dirty = self._has_unsaved_changes()
        if self._project_path is not None:
            prefix = self._project_path.stem + ("*" if dirty else "")
        elif clip is None:
            self.setWindowTitle(__app_name__)
            return
        else:
            prefix = f"{clip.name}*" if dirty else clip.name
        self.setWindowTitle(f"{prefix} — {__app_name__}")

    def _selected_range(self) -> TimeRange:
        selection = self.engine.selection
        if selection is None or selection.is_empty:
            raise EditError("make a selection first")
        return selection

    def _run_edit(self, operation: str, callback) -> None:
        if self._edit_session is None or self._workspace != "waveform":
            return
        try:
            callback()
        except EditError as exc:
            QMessageBox.warning(self, operation, str(exc))

    def edit_undo(self) -> None:
        def _undo() -> None:
            assert self._edit_session is not None
            if not self._edit_session.undo():
                raise EditError("nothing to undo")

        self._run_edit("Undo", _undo)

    def edit_redo(self) -> None:
        def _redo() -> None:
            assert self._edit_session is not None
            if not self._edit_session.redo():
                raise EditError("nothing to redo")

        self._run_edit("Redo", _redo)

    def edit_cut(self) -> None:
        def _cut() -> None:
            assert self._edit_session is not None
            self._edit_session.cut(self._selected_range())

        self._run_edit("Cut", _cut)

    def edit_copy(self) -> None:
        def _copy() -> None:
            assert self._edit_session is not None
            self._edit_session.copy(self._selected_range())
            self._update_edit_actions()

        self._run_edit("Copy", _copy)

    def edit_paste(self) -> None:
        def _paste() -> None:
            assert self._edit_session is not None
            at = int(self.engine.position)
            selection = self.engine.selection
            replacing = selection if selection is not None and not selection.is_empty else None
            self._edit_session.paste(at, replacing=replacing)

        self._run_edit("Paste", _paste)

    def edit_delete(self) -> None:
        def _delete() -> None:
            assert self._edit_session is not None
            self._edit_session.delete(self._selected_range())

        self._run_edit("Delete", _delete)

    def edit_silence(self) -> None:
        def _silence() -> None:
            assert self._edit_session is not None
            self._edit_session.silence(self._selected_range())

        self._run_edit("Silence", _silence)

    def edit_trim(self) -> None:
        def _trim() -> None:
            assert self._edit_session is not None
            self._edit_session.trim(self._selected_range())

        self._run_edit("Trim", _trim)

    def edit_gain(self) -> None:
        gain_db, ok = QInputDialog.getDouble(
            self,
            "Apply Gain",
            "Gain (dB):",
            0.0,
            -96.0,
            24.0,
            2,
        )
        if not ok:
            return

        def _gain() -> None:
            assert self._edit_session is not None
            self._edit_session.apply_gain(self._selected_range(), gain_db)

        self._run_edit("Apply Gain", _gain)

    def edit_fade_in(self) -> None:
        def _fade() -> None:
            assert self._edit_session is not None
            self._edit_session.fade_in(self._selected_range(), shape="cosine")

        self._run_edit("Fade In", _fade)

    def edit_fade_out(self) -> None:
        def _fade() -> None:
            assert self._edit_session is not None
            self._edit_session.fade_out(self._selected_range(), shape="cosine")

        self._run_edit("Fade Out", _fade)

    def edit_reverse(self) -> None:
        def _reverse() -> None:
            assert self._edit_session is not None
            self._edit_session.reverse(self._selected_range())

        self._run_edit("Reverse", _reverse)

    def edit_insert_silence(self) -> None:
        rate = max(self.engine.sample_rate, 1)
        duration_ms, ok = QInputDialog.getDouble(
            self,
            "Insert Silence",
            "Duration (milliseconds):",
            1000.0,
            1.0,
            3_600_000.0,
            1,
        )
        if not ok:
            return
        n_frames = max(1, int(round(duration_ms * rate / 1000.0)))

        def _insert() -> None:
            assert self._edit_session is not None
            at = int(self.engine.position)
            self._edit_session.insert_silence(at, n_frames)

        self._run_edit("Insert Silence", _insert)

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

    # ----------------------------------------------------------- workspaces

    @property
    def workspace(self) -> str:
        """``"waveform"`` or ``"multitrack"`` — which document is on screen."""
        return self._workspace

    @property
    def editor_clip(self) -> LoadedAudio | None:
        """The clip the waveform editor holds, whatever the transport is playing."""
        return self._editor_clip if self._editor_clip is not None else self.engine.clip

    def set_workspace(self, name: str) -> None:
        """Show the waveform editor or the multitrack session.

        The first switch into multitrack seeds the session from the loaded clip
        so the workspace is never an empty room; after that it is left alone.
        """
        if name not in ("waveform", "multitrack"):
            raise ValueError(f"unknown workspace {name!r}")
        self._workspace = name
        multitrack = name == "multitrack"

        if multitrack and self.session.n_tracks == 0 and self.editor_clip is not None:
            self.add_clip_as_track()

        self.waveform_page.setVisible(not multitrack)
        self.multitrack_view.setVisible(multitrack)
        if self.action_multitrack.isChecked() != multitrack:
            self.action_multitrack.setChecked(multitrack)

        self._route_transport()
        if multitrack:
            self.multitrack_view.zoom_to_fit()
            self.multitrack_view.set_playhead(self.engine.position)
        else:
            self._refresh_editor_waveform()
        self._update_edit_actions()
        self._update_status_format()

    def _refresh_editor_waveform(self) -> None:
        clip = self._editor_clip
        session = self._edit_session
        if clip is None or session is None:
            return
        pyramid, samples = self._waveform_cache(session)
        self.engine.update_pyramid(pyramid)
        self.track_panel.set_clip(clip, pyramid, samples=samples)

    def _on_multitrack_toggled(self) -> None:
        self.set_workspace("multitrack" if self.action_multitrack.isChecked() else "waveform")

    def add_clip_as_track(self, name: str | None = None) -> Track | None:
        """Place the loaded clip on a new lane of the multitrack session."""
        clip = self.editor_clip
        if clip is None:
            return None
        if self._edit_session is not None:
            buffer = self._edit_session.to_buffer()
        else:
            buffer = clip.buffer
        if self.session.n_tracks == 0 or not self.session.clips:
            # An empty session has no opinion about format yet, so it adopts
            # the first clip's rather than refusing it.
            self.session.set_format(buffer.sample_rate, buffer.n_channels)
        if buffer.sample_rate != self.session.sample_rate:
            QMessageBox.warning(
                self,
                "Sample rate mismatch",
                f"{clip.name} is {buffer.sample_rate} Hz but the session runs at "
                f"{self.session.sample_rate} Hz. Resampling is not implemented yet.",
            )
            return None

        track = self.session.add_track(name or clip.name)
        self.session.add_clip(track, MemorySampleSource(buffer), start=0, name=clip.name)
        self.multitrack_view.zoom_to_fit()
        self._route_transport()
        self._update_status_format()
        self.statusBar().showMessage(f"Added {clip.name} to the session", 4000)
        return track

    @property
    def is_playing_session(self) -> bool:
        """True when the transport is pulling from the session mixer."""
        return self.engine.source is self.session.mixer

    def _route_transport(self) -> None:
        """Point the transport at whichever document the visible workspace owns.

        Swapping the source is all it takes: the mixer satisfies the same
        protocol a decoded clip does, so the feeder, the ring buffer and the
        effect preview insert carry on unchanged.
        """
        wants_session = self._workspace == "multitrack" and self.session.n_frames > 0
        if wants_session == self.is_playing_session:
            return
        if wants_session:
            self._editor_clip = self.engine.clip
            self.engine.set_source(self.session.mixer)
        else:
            self._restore_editor_source()

        has_audio = self.engine.has_clip
        self.transport_bar.set_enabled_for_clip(has_audio)
        self.transport_bar.set_duration(self.engine.duration)
        self.transport_bar.set_position(0.0)
        self.level_meter.set_channels(max(self.engine.n_channels, 1))
        self.level_meter.reset()

    def _on_session_edited(self) -> None:
        self._mark_project_dirty()
        self._route_transport()
        self._update_status_format()

    # -------------------------------------------------------------- reactive

    def _update_for_clip(self) -> None:
        if not self.is_playing_session:
            self._editor_clip = self.engine.clip
        clip = self.editor_clip
        if self._edit_session is not None and clip is not None:
            _, samples = self._waveform_cache(self._edit_session)
            self.track_panel.set_clip(clip, self.engine.pyramid, samples=samples)
        else:
            self.track_panel.set_clip(self.engine.clip, self.engine.pyramid)
        has_clip = self.engine.has_clip

        self.transport_bar.set_enabled_for_clip(has_clip)
        self.transport_bar.set_duration(self.engine.duration)
        self.transport_bar.set_position(0.0)
        self.transport_bar.set_selection_text("—")
        self.level_meter.set_channels(max(self.engine.n_channels, 1))
        self.level_meter.reset()

        for act in (
            self.action_close,
            self.action_export,
            self.action_select_all,
            self.action_undo,
            self.action_redo,
            self.action_cut,
            self.action_copy,
            self.action_paste,
            self.action_delete,
            self.action_silence,
            self.action_trim,
            self.action_gain,
            self.action_fade_in,
            self.action_fade_out,
            self.action_reverse,
            self.action_insert_silence,
        ):
            act.setEnabled(has_clip)
        can_save = self._edit_session is not None or self.session.n_tracks > 0
        self.action_save_project.setEnabled(can_save)
        self.action_save_project_as.setEnabled(can_save)
        self.action_open_project.setEnabled(True)
        self.action_add_track.setEnabled(clip is not None)

        self._update_edit_actions()
        self._update_window_title()
        self._route_transport()
        self._update_status_format()
        self.status_selection.setText("Selection: —")
        self.analyze_spectrum()
        self.measure_loudness()

    def _update_status_format(self) -> None:
        """Describe whatever the transport is currently pointed at."""
        if self.is_playing_session:
            self.status_format.setText(
                f"{self.session.n_tracks} tracks  ·  "
                f"{self.session.sample_rate / 1000:g} kHz  ·  "
                f"{format_timecode(self.session.duration)}  ·  "
                f"{self.session.n_frames:,} frames"
            )
            return
        clip = self.editor_clip
        if clip is None:
            self.status_format.setText("No file")
            return
        self.status_format.setText(
            f"{clip.name}  ·  {clip.audio_format.describe()}  ·  "
            f"{format_timecode(clip.duration)}  ·  {clip.buffer.n_frames:,} frames"
        )

    def _on_tick(self) -> None:
        """Poll the engine 30×/s: the audio threads never touch Qt objects."""
        self._collect_loudness()
        if not self.engine.has_clip:
            return
        position = self.engine.position
        playing = self.engine.is_playing
        if self._workspace == "multitrack":
            self.multitrack_view.set_playhead(position)
        else:
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
        self.multitrack_view.set_playhead(position)
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
        if not self._confirm_discard_unsaved(action="closing"):
            event.ignore()
            return
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
