"""Widget-level tests run against the Qt offscreen platform plugin."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PySide6.QtCore import Qt

from audio_studio.core.engine import AudioEngine
from audio_studio.core.loader import LoadedAudio
from audio_studio.core.output import NullOutput
from audio_studio.core.peaks import PeakPyramid
from audio_studio.core.types import TimeRange, TransportState
from audio_studio.dsp.effects import EffectChain, ThreeBandEQ
from audio_studio.dsp.repair import DeHumEffect
from audio_studio.ui.effect_rack import EffectRackPanel, default_preview_chain
from audio_studio.ui.level_meter import FLOOR_DB, LevelMeter
from audio_studio.ui.main_window import MainWindow
from audio_studio.ui.spectrum_panel import SpectrumPanel
from audio_studio.ui.waveform_view import MIN_VIEW_FRAMES, WaveformView

pytestmark = pytest.mark.usefixtures("qapp")


@pytest.fixture()
def waveform(loaded_clip: LoadedAudio) -> WaveformView:
    view = WaveformView()
    view.resize(800, 200)
    view.set_clip(
        PeakPyramid(loaded_clip.buffer.data),
        loaded_clip.buffer.sample_rate,
        loaded_clip.buffer.data,
    )
    return view


@pytest.fixture()
def window(loaded_clip: LoadedAudio) -> MainWindow:
    engine = AudioEngine(NullOutput(realtime=False), block_size=256)
    main = MainWindow(engine)
    main.resize(1200, 700)
    engine.set_clip(loaded_clip)
    main._bind_edit_session(loaded_clip)  # noqa: SLF001 - mirrors open_file()
    main._update_for_clip()  # noqa: SLF001 - normally triggered by open_file()
    yield main
    main._mark_project_saved()  # noqa: SLF001 - avoid blocking close prompts in tests
    main.close()


def test_waveform_starts_fitted_to_the_clip(waveform: WaveformView) -> None:
    assert waveform.has_clip
    assert waveform.view_start == 0
    assert waveform.view_frames == waveform.n_frames


def test_zoom_keeps_the_anchor_frame_under_the_same_pixel(waveform: WaveformView) -> None:
    anchor = waveform.n_frames // 2
    x_before = waveform.frame_to_x(anchor)

    waveform.zoom_by(0.25, anchor)

    assert waveform.view_frames == pytest.approx(waveform.n_frames * 0.25, rel=0.01)
    assert waveform.frame_to_x(anchor) == pytest.approx(x_before, abs=2.0)


def test_zoom_is_clamped_at_both_ends(waveform: WaveformView) -> None:
    for _ in range(40):
        waveform.zoom_by(0.5)
    assert waveform.view_frames >= MIN_VIEW_FRAMES

    for _ in range(40):
        waveform.zoom_by(2.0)
    assert waveform.view_frames == waveform.n_frames
    assert waveform.view_start == 0


def test_scrolling_cannot_run_past_the_clip(waveform: WaveformView) -> None:
    waveform.zoom_by(0.1)
    span = waveform.view_frames

    waveform.scroll_to(10**9)
    assert waveform.view_start == waveform.n_frames - span

    waveform.scroll_to(-10**9)
    assert waveform.view_start == 0


def test_frame_and_pixel_conversions_round_trip(waveform: WaveformView) -> None:
    waveform.set_view(10_000, 20_000)

    for x in (0, 133, 400, 799):
        assert waveform.frame_to_x(waveform.x_to_frame(x)) == pytest.approx(x, abs=1.0)


def test_ensure_visible_pages_the_view_to_follow_the_playhead(waveform: WaveformView) -> None:
    waveform.set_view(0, 10_000)

    waveform.ensure_visible(45_000)

    assert waveform.view_start <= 45_000 <= waveform.view_start + waveform.view_frames


def test_selection_is_clamped_and_announced(waveform: WaveformView) -> None:
    received: list[TimeRange | None] = []
    waveform.selectionChanged.connect(received.append)

    waveform.set_selection(TimeRange(1_000, 10**9))
    assert waveform.selection == TimeRange(1_000, waveform.n_frames)

    waveform.clear_selection()
    assert waveform.selection is None
    assert received[-1] is None


def test_select_all_and_zoom_to_selection(waveform: WaveformView) -> None:
    waveform.set_selection(TimeRange(20_000, 30_000))

    waveform.zoom_to_selection()

    assert waveform.view_start <= 20_000
    assert waveform.view_start + waveform.view_frames >= 30_000
    assert waveform.view_frames < waveform.n_frames

    waveform.select_all()
    assert waveform.selection == TimeRange(0, waveform.n_frames)


def test_playhead_is_clamped_to_the_clip(waveform: WaveformView) -> None:
    waveform.set_playhead(10**9)
    assert waveform.playhead == waveform.n_frames

    waveform.set_playhead(-5)
    assert waveform.playhead == 0


def test_a_fractional_playhead_keeps_its_fraction(waveform: WaveformView) -> None:
    """The transport interpolates between blocks; the view must not round it off."""
    waveform.set_playhead(1_234.5)

    assert waveform.playhead_exact == 1_234.5
    assert waveform.playhead == 1_234
    # Sub-frame motion still moves the drawn position.
    assert waveform.frame_to_x(1_234.5) > waveform.frame_to_x(1_234.0)


def test_waveform_renders_without_error_at_several_zoom_levels(
    waveform: WaveformView,
) -> None:
    from PySide6.QtGui import QPixmap

    for frames in (waveform.n_frames, 20_000, 2_000, 200, 64):
        waveform.set_view(1_000, frames)
        target = QPixmap(waveform.size())
        waveform.render(target)
        assert not target.isNull()


def test_level_meter_tracks_peaks_and_latches_clipping() -> None:
    meter = LevelMeter(channels=2)

    meter.update_levels((0.5, 0.25), (0.3, 0.1))
    assert meter._levels_db[0] > FLOOR_DB  # noqa: SLF001 - internal ballistics state
    assert not meter.clipped

    meter.update_levels((1.0, 1.0))
    assert meter.clipped

    meter.reset()
    assert not meter.clipped


def test_main_window_reflects_the_loaded_clip(window: MainWindow) -> None:
    assert "in-memory.wav" in window.windowTitle()
    assert window.track_panel.waveform.has_clip
    assert window.transport_bar.play_button.isEnabled()
    assert window.level_meter.channels == 2


def test_main_window_transport_buttons_drive_the_engine(window: MainWindow) -> None:
    window._on_play_pause()  # noqa: SLF001 - the slot the button is wired to
    assert window.engine.state is TransportState.PLAYING

    window._on_play_pause()  # noqa: SLF001
    assert window.engine.state is TransportState.PAUSED

    window._on_stop()  # noqa: SLF001
    assert window.engine.state is TransportState.STOPPED


def test_selecting_in_the_waveform_updates_the_engine_region(window: MainWindow) -> None:
    selection = TimeRange(1_000, 5_000)

    window.track_panel.waveform.set_selection(selection)

    assert window.engine.selection == selection
    assert window.engine.playback_region == selection
    assert "1,000" in window.status_selection.text() or "4,000" in window.status_selection.text()


def test_seek_from_the_ruler_moves_the_playhead(window: MainWindow) -> None:
    window._on_seek(12_345)  # noqa: SLF001

    assert window.engine.position == 12_345
    assert window.track_panel.waveform.playhead == 12_345


class TestSpectrumPanel:
    """The dockable spectral view and the controls that drive it."""

    @pytest.fixture()
    def panel(self, loaded_clip: LoadedAudio) -> SpectrumPanel:
        view = SpectrumPanel()
        view.resize(800, 300)
        return view

    def test_starts_empty_and_says_so(self, panel: SpectrumPanel) -> None:
        assert not panel.has_data
        assert "No spectral" in panel.info_label.text()
        assert panel.spectrogram.render_image(100, 50) is None

    def test_analysis_fills_the_view_and_the_read_out(
        self, panel: SpectrumPanel, loaded_clip: LoadedAudio
    ) -> None:
        buffer = loaded_clip.buffer
        panel.analyze(buffer.data, buffer.sample_rate)

        assert panel.has_data
        assert panel.spectrogram.render_image(200, 100) is not None
        assert "columns" in panel.info_label.text()
        assert f"{panel.fft_size}-pt" in panel.info_label.text()

    def test_a_long_clip_is_not_analysed_at_full_resolution(self) -> None:
        """Past a few thousand columns the hop widens instead of the wait."""
        from audio_studio.ui.spectrum_panel import MAX_ANALYSIS_FRAMES, analysis_config

        config = analysis_config(48_000, 48_000 * 600, 2048)
        assert config.hop_size > 512
        assert config.n_frames(48_000 * 600) <= MAX_ANALYSIS_FRAMES + 1

    def test_clearing_returns_to_the_empty_state(
        self, panel: SpectrumPanel, loaded_clip: LoadedAudio
    ) -> None:
        panel.analyze(loaded_clip.buffer.data, loaded_clip.buffer.sample_rate)
        panel.clear()
        assert not panel.has_data

    def test_empty_or_nonsense_input_clears_instead_of_raising(
        self, panel: SpectrumPanel
    ) -> None:
        panel.analyze(None, 48_000)
        panel.analyze(np.zeros((0, 2)), 48_000)
        panel.analyze(np.zeros((128, 2)), 0)
        assert not panel.has_data

    def test_the_range_control_moves_the_floor(self, panel: SpectrumPanel) -> None:
        panel.range_box.setCurrentIndex(0)
        assert panel.spectrogram.db_range == (-60.0, 0.0)
        panel.range_box.setCurrentIndex(2)
        assert panel.spectrogram.db_range == (-120.0, 0.0)

    def test_the_scale_button_switches_the_frequency_axis(self, panel: SpectrumPanel) -> None:
        from audio_studio.ui.spectrogram_widget import FrequencyScale

        panel.scale_button.setChecked(False)
        assert panel.spectrogram.frequency_scale is FrequencyScale.LINEAR
        assert panel.scale_button.text() == "Linear"

    def test_changing_the_fft_size_asks_the_owner_to_re_analyse(
        self, panel: SpectrumPanel
    ) -> None:
        sizes: list[int] = []
        panel.fftSizeChanged.connect(sizes.append)

        panel.fft_box.setCurrentText("8192")

        assert sizes == [8192]
        assert panel.fft_size == 8192

    def test_a_click_seeks_in_clip_time_not_selection_time(
        self, panel: SpectrumPanel, loaded_clip: LoadedAudio
    ) -> None:
        """A selection is analysed on its own, so its offset has to come back."""
        seeks: list[float] = []
        panel.seekRequested.connect(seeks.append)
        buffer = loaded_clip.buffer
        panel.analyze(buffer.data[:20_000], buffer.sample_rate, offset_s=1.5)

        panel.spectrogram.positionClicked.emit(0.25, 1000.0)

        assert seeks == [pytest.approx(1.75)]


class TestEffectRackPanel:
    """Controls that write straight into the chain the device thread reads."""

    @pytest.fixture()
    def rack(self, qapp) -> EffectRackPanel:
        return EffectRackPanel(default_preview_chain())

    def test_moving_a_band_reaches_the_effect_immediately(
        self, rack: EffectRackPanel
    ) -> None:
        changes: list[None] = []
        rack.chainChanged.connect(lambda: changes.append(None))

        rack.eq_low.set_value(6.0)

        assert rack.eq.low.gain_db == pytest.approx(6.0)
        assert changes

    def test_the_bypass_button_bypasses_the_whole_rack(self, rack: EffectRackPanel) -> None:
        rack.bypass_button.setChecked(True)
        assert rack.chain.bypass
        assert rack.summary() == "FX bypassed"

    def test_the_mix_slider_is_the_chains_wet_amount(self, rack: EffectRackPanel) -> None:
        rack.mix_slider.set_value(40.0)
        assert rack.chain.mix == pytest.approx(0.4)
        assert "40% wet" in rack.summary()

    def test_switching_a_member_off_takes_it_out_of_the_summary(
        self, rack: EffectRackPanel
    ) -> None:
        rack.eq_enabled.setChecked(False)
        assert not rack.eq.enabled
        assert "3-Band EQ" not in rack.summary()
        assert "Gain" in rack.summary()

    def test_polarity_and_trim_reach_the_gain_stage(self, rack: EffectRackPanel) -> None:
        rack.trim_gain.set_value(-3.0)
        rack.polarity.setChecked(True)
        assert rack.trim.gain_db == pytest.approx(-3.0)
        assert rack.trim.invert_polarity

    def test_reset_flattens_without_swapping_the_chain(self, rack: EffectRackPanel) -> None:
        chain = rack.chain
        rack.eq_high.set_value(9.0)
        rack.mix_slider.set_value(20.0)
        rack.bypass_button.setChecked(True)

        rack.reset()

        assert rack.chain is chain  # the device thread keeps its object
        assert rack.eq.high.gain_db == 0.0
        assert chain.mix == 1.0
        assert not chain.bypass
        assert rack.bypass_button.isChecked() is False

    def test_pointing_the_panel_at_another_chain_reads_its_state(
        self, rack: EffectRackPanel
    ) -> None:
        other = default_preview_chain()
        other.mix = 0.6
        next(e for e in other if isinstance(e, ThreeBandEQ)).low.gain_db = -4.0

        rack.set_chain(other)

        assert rack.mix_slider.value == pytest.approx(60.0)
        assert rack.eq_low.value == pytest.approx(-4.0)

    def test_refreshing_does_not_write_back_through_the_signals(
        self, rack: EffectRackPanel
    ) -> None:
        rack.chain.mix = 0.5
        changes: list[None] = []
        rack.chainChanged.connect(lambda: changes.append(None))

        rack.refresh()

        assert changes == []
        assert rack.chain.mix == 0.5

    def test_an_unrecognised_rack_still_renders(self, qapp) -> None:
        """The panel targets EQ and trim, but must not require them."""
        panel = EffectRackPanel(EffectChain())
        assert panel.eq is None and panel.trim is None
        assert panel.dehum is None and panel.declick is None
        assert panel.summary() == "FX empty"
        panel.reset()
        panel.eq_low.set_value(3.0)  # no crash without an EQ to write to
        panel.hum_q.set_value(20.0)
        panel.declick_sensitivity.set_value(80.0)

    def test_repair_starts_switched_off(self, rack: EffectRackPanel) -> None:
        """A new session must not be quietly rewriting samples."""
        assert not rack.dehum.enabled
        assert not rack.declick.enabled
        assert "De-Hum" not in rack.summary()
        assert "De-Click" not in rack.summary()

    def test_the_dehum_controls_reach_the_effect(self, rack: EffectRackPanel) -> None:
        rack.dehum_enabled.setChecked(True)
        rack.hum_frequency.setCurrentIndex(2)  # 60 Hz
        rack.hum_harmonics.setValue(5)
        rack.hum_q.set_value(45.0)

        assert rack.dehum.enabled
        assert rack.dehum.frequency == pytest.approx(60.0)
        assert rack.dehum.harmonics == 5
        assert rack.dehum.q == pytest.approx(45.0)
        assert "De-Hum" in rack.summary()

    def test_auto_hum_detection_is_the_first_choice(self, rack: EffectRackPanel) -> None:
        rack.hum_frequency.setCurrentIndex(1)  # 50 Hz
        assert not rack.dehum.auto
        rack.hum_frequency.setCurrentIndex(0)  # Auto
        assert rack.dehum.auto

    def test_the_declick_controls_reach_the_effect(self, rack: EffectRackPanel) -> None:
        rack.declick_enabled.setChecked(True)
        rack.declick_sensitivity.set_value(80.0)

        assert rack.declick.enabled
        assert rack.declick.sensitivity == pytest.approx(0.8)

    def test_reset_switches_repair_back_off(self, rack: EffectRackPanel) -> None:
        rack.dehum_enabled.setChecked(True)
        rack.declick_enabled.setChecked(True)

        rack.reset()

        assert not rack.dehum.enabled and not rack.declick.enabled
        assert rack.dehum_enabled.isChecked() is False
        assert rack.declick_enabled.isChecked() is False

    def test_the_panel_reads_repair_state_back_from_a_chain(self, rack: EffectRackPanel) -> None:
        other = default_preview_chain()
        dehum = next(e for e in other if isinstance(e, DeHumEffect))
        dehum.enabled = True
        dehum.frequency = 60.0
        dehum.harmonics = 3

        rack.set_chain(other)

        assert rack.dehum_enabled.isChecked()
        assert rack.hum_frequency.currentIndex() == 2
        assert rack.hum_harmonics.value() == 3


class TestWindowIntegration:
    def test_the_docks_are_built_and_named(self, window: MainWindow) -> None:
        assert window.spectrum_dock.widget() is window.spectrum_panel
        assert window.effects_dock.widget() is window.effect_rack
        assert window.dockWidgetArea(window.spectrum_dock) == Qt.DockWidgetArea.BottomDockWidgetArea
        assert window.dockWidgetArea(window.effects_dock) == Qt.DockWidgetArea.RightDockWidgetArea

    def test_loading_a_clip_analyses_it(self, window: MainWindow) -> None:
        assert window.spectrum_panel.has_data
        assert "columns" in window.spectrum_panel.info_label.text()

    @pytest.mark.parametrize(
        ("mode", "editor", "spectrum"),
        [("waveform", True, False), ("spectrum", False, True), ("split", True, True)],
    )
    def test_view_modes_show_the_right_panes(
        self, window: MainWindow, qapp, mode: str, editor: bool, spectrum: bool
    ) -> None:
        window.show()
        qapp.processEvents()

        window.set_view_mode(mode)
        qapp.processEvents()

        assert window.view_mode == mode
        assert window.editor_widget.isVisible() is editor
        assert window.spectrum_dock.isVisible() is spectrum
        assert window.effects_dock.isVisible()  # the rack is independent of the mode
        window.hide()

    def test_the_view_menu_actions_stay_in_step_with_the_mode(
        self, window: MainWindow
    ) -> None:
        window.action_view_spectrum.trigger()
        assert window.view_mode == "spectrum"
        assert window.action_view_spectrum.isChecked()
        assert not window.action_view_waveform.isChecked()

    def test_an_unknown_mode_is_refused(self, window: MainWindow) -> None:
        with pytest.raises(ValueError, match="unknown view mode"):
            window.set_view_mode("waterfall")

    def test_selecting_a_range_analyses_only_that_range(self, window: MainWindow) -> None:
        rate = window.engine.sample_rate
        window.track_panel.waveform.set_selection(TimeRange(rate // 2, rate))

        assert window.analysis_region() == TimeRange(rate // 2, rate)
        window.analyze_spectrum()

        assert window.spectrum_panel.has_data
        assert window.spectrum_panel._offset_s == pytest.approx(0.5)  # noqa: SLF001

    def test_clicking_the_spectrogram_seeks_the_transport(self, window: MainWindow) -> None:
        window.spectrum_panel.seekRequested.emit(0.5)
        assert window.engine.position == window.engine.sample_rate // 2

    def test_the_hover_read_out_reaches_the_status_bar(self, window: MainWindow) -> None:
        window.spectrum_panel.readoutChanged.emit("0.500 s  1000.0 Hz  -20.0 dB")
        assert "1000.0 Hz" in window.statusBar().currentMessage()

        window.spectrum_panel.readoutChanged.emit("")
        assert window.statusBar().currentMessage() == ""

    def test_the_rack_is_inserted_in_the_playback_path(self, window: MainWindow) -> None:
        assert window.engine.output is window.preview
        assert window.preview.chain is window.effect_chain
        assert window.effect_rack.chain is window.effect_chain
        assert "+fx" in window.status_backend.text()

    def test_a_rack_change_is_reported_in_the_status_bar(self, window: MainWindow) -> None:
        window.effect_rack.trim_gain.set_value(-6.0)
        assert "Gain" in window.status_fx.text()

        window.effect_rack.bypass_button.setChecked(True)
        assert window.status_fx.text() == "FX bypassed"

    def test_loudness_is_measured_off_the_ui_thread_and_reported(
        self, window: MainWindow
    ) -> None:
        window.measure_loudness()
        assert "measuring" in window.status_loudness.text()

        window._loudness_job.result(timeout=30.0)  # noqa: SLF001 - wait for the worker
        window._collect_loudness()  # noqa: SLF001 - normally driven by the refresh timer

        assert window.loudness is not None
        # Two 0.5-amplitude sines: -6.02 dB of mean square per channel, summed
        # over two channels and offset by the -0.691 LU of BS.1770.
        assert window.loudness.integrated_lufs == pytest.approx(-6.7, abs=0.5)
        assert "LUFS" in window.status_loudness.text()
        assert "dBTP" in window.status_loudness.text()

    def test_a_window_with_no_clip_reports_no_loudness(self, qapp) -> None:
        engine = AudioEngine(NullOutput(realtime=False), block_size=256)
        main = MainWindow(engine)
        try:
            assert main.status_loudness.text() == "Loudness: —"
            assert not main.spectrum_panel.has_data
            main.set_view_mode("spectrum")  # must not raise without audio
        finally:
            main.close()


def test_opening_a_real_file_through_the_window(wav_path: Path) -> None:
    engine = AudioEngine(NullOutput(realtime=False))
    main = MainWindow(engine)
    try:
        assert main.open_file(wav_path)
        assert main.engine.has_clip
        assert main.track_panel.waveform.n_frames == main.engine.n_frames
        assert main.recent_menu.isEnabled()
        assert main._edit_session is not None
    finally:
        main.close()


class TestEditSessionUi:
    def test_cut_shortens_the_document_and_undo_restores_it(self, window: MainWindow) -> None:
        before = window.engine.n_frames
        window.track_panel.waveform.set_selection(TimeRange(100, 500))

        window.edit_cut()

        assert window.engine.n_frames == before - 400
        assert window.action_undo.isEnabled()
        window.edit_undo()
        assert window.engine.n_frames == before

    def test_copy_and_paste_extends_the_document(self, window: MainWindow) -> None:
        before = window.engine.n_frames
        window.track_panel.waveform.set_selection(TimeRange(0, 200))
        window.edit_copy()
        assert window.action_paste.isEnabled()
        window.track_panel.waveform.clear_selection()
        window.engine.set_selection(None)

        window.engine.seek(1_000)
        window.edit_paste()

        assert window.engine.n_frames == before + 200

    def test_a_modified_clip_shows_an_asterisk_in_the_title(self, window: MainWindow) -> None:
        window.track_panel.waveform.set_selection(TimeRange(0, 100))
        window.edit_delete()
        assert "*" in window.windowTitle()

    def test_gain_shortens_the_selection_in_level(self, window: MainWindow, monkeypatch) -> None:
        window.track_panel.waveform.set_selection(TimeRange(0, 500))
        monkeypatch.setattr(
            "audio_studio.ui.main_window.QInputDialog.getDouble",
            lambda *args, **kwargs: (-6.0, True),
        )
        before = window._edit_session.read(0, 500).copy()  # noqa: SLF001
        window.edit_gain()
        after = window._edit_session.read(0, 500)  # noqa: SLF001
        assert np.max(np.abs(after)) < np.max(np.abs(before))

    def test_insert_silence_extends_the_document(self, window: MainWindow, monkeypatch) -> None:
        before = window.engine.n_frames
        window.engine.seek(1_000)
        monkeypatch.setattr(
            "audio_studio.ui.main_window.QInputDialog.getDouble",
            lambda *args, **kwargs: (10.0, True),
        )
        window.edit_insert_silence()
        rate = window.engine.sample_rate
        expected = max(1, int(round(10.0 * rate / 1000.0)))
        assert window.engine.n_frames == before + expected


def test_project_apply_roundtrip_through_window(
    loaded_clip: LoadedAudio, tmp_path: Path,
) -> None:
    from audio_studio.project.store import load_project

    engine = AudioEngine(NullOutput(realtime=False))
    main = MainWindow(engine)
    try:
        main._bind_edit_session(loaded_clip)  # noqa: SLF001
        main._update_for_clip()  # noqa: SLF001
        main.track_panel.waveform.set_selection(TimeRange(0, 200))
        main.edit_delete()
        project_dir = tmp_path / "roundtrip.hlproj"
        main._write_project(project_dir)  # noqa: SLF001
        main._mark_project_saved()  # noqa: SLF001

        other = MainWindow(AudioEngine(NullOutput(realtime=False)))
        try:
            snapshot = load_project(project_dir)
            other._apply_project(project_dir, snapshot)  # noqa: SLF001
            assert other._project_path == project_dir  # noqa: SLF001
            assert other.engine.n_frames == main.engine.n_frames
            assert not other._has_unsaved_changes()  # noqa: SLF001
        finally:
            other._mark_project_saved()  # noqa: SLF001
            other.close()
    finally:
        main._mark_project_saved()  # noqa: SLF001
        main.close()
