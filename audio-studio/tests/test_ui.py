"""Widget-level tests run against the Qt offscreen platform plugin."""

from __future__ import annotations

from pathlib import Path

import pytest

from audio_studio.core.engine import AudioEngine
from audio_studio.core.loader import LoadedAudio
from audio_studio.core.output import NullOutput
from audio_studio.core.peaks import PeakPyramid
from audio_studio.core.types import TimeRange, TransportState
from audio_studio.ui.level_meter import FLOOR_DB, LevelMeter
from audio_studio.ui.main_window import MainWindow
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
    main._update_for_clip()  # noqa: SLF001 - normally triggered by open_file()
    yield main
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


def test_waveform_renders_without_error_at_several_zoom_levels(
    waveform: WaveformView,
) -> None:
    from PyQt6.QtGui import QPixmap

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


def test_opening_a_real_file_through_the_window(wav_path: Path) -> None:
    engine = AudioEngine(NullOutput(realtime=False))
    main = MainWindow(engine)
    try:
        assert main.open_file(wav_path)
        assert main.engine.has_clip
        assert main.track_panel.waveform.n_frames == main.engine.n_frames
        assert main.recent_menu.isEnabled()
    finally:
        main.close()
