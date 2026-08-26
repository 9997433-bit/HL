"""Timeline markers and named regions, from the value types up to the window."""

from __future__ import annotations

from pathlib import Path

import pytest

from audio_studio.core.engine import AudioEngine
from audio_studio.core.loader import LoadedAudio
from audio_studio.core.markers import Marker, MarkerList, Region
from audio_studio.core.output import NullOutput
from audio_studio.core.types import TimeRange


class TestMarker:
    def test_a_marker_names_a_frame(self) -> None:
        marker = Marker(id="mrk_0001", name="Verse", frame=44_100)
        assert marker.position == 44_100
        assert marker.color is None

    def test_negative_frames_and_blank_ids_are_refused(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            Marker(id="mrk_0001", name="", frame=-1)
        with pytest.raises(ValueError, match="non-empty id"):
            Marker(id="", name="", frame=0)

    def test_editing_returns_a_new_record(self) -> None:
        marker = Marker(id="mrk_0001", name="Verse", frame=100)
        renamed = marker.renamed("Chorus")
        moved = marker.moved_to(200)

        assert marker.name == "Verse" and marker.frame == 100
        assert renamed.name == "Chorus" and renamed.frame == 100
        assert moved.frame == 200 and moved.id == marker.id

    def test_json_round_trip_keeps_the_colour(self) -> None:
        marker = Marker(id="mrk_0007", name="Cue", frame=17, color="#ff0000")
        data = marker.to_json()

        assert data["type"] == "marker"
        assert Marker.from_json(data) == marker

    def test_a_colourless_marker_writes_no_colour_key(self) -> None:
        assert "color" not in Marker(id="mrk_0001", name="Cue", frame=0).to_json()


class TestRegion:
    def test_a_region_spans_a_half_open_range(self) -> None:
        region = Region(id="rgn_0001", name="Chorus", start=100, end=400)
        assert region.length == 300
        assert region.range == TimeRange(100, 400)
        assert region.position == 100
        assert region.contains(100) and region.contains(399)
        assert not region.contains(400)

    def test_an_inverted_range_is_refused(self) -> None:
        with pytest.raises(ValueError, match="end precedes start"):
            Region(id="rgn_0001", name="", start=400, end=100)

    def test_an_empty_region_is_allowed_but_says_so(self) -> None:
        assert Region(id="rgn_0001", name="", start=5, end=5).is_empty

    def test_json_round_trip(self) -> None:
        region = Region(id="rgn_0002", name="Bridge", start=1, end=2, color="#00ff00")
        data = region.to_json()

        assert data["type"] == "region"
        assert Region.from_json(data) == region

    def test_from_range_and_with_range(self) -> None:
        region = Region.from_range("rgn_0001", "Solo", TimeRange(10, 20))
        assert (region.start, region.end) == (10, 20)
        assert region.with_range(TimeRange(30, 40)).range == TimeRange(30, 40)


class TestMarkerList:
    def test_a_new_list_is_empty(self) -> None:
        markers = MarkerList()
        assert markers.is_empty
        assert len(markers) == 0
        assert markers.to_json() == []

    def test_added_items_get_sequential_ids_and_default_names(self) -> None:
        markers = MarkerList()

        first = markers.add_marker(100)
        second = markers.add_marker(200)
        region = markers.add_region(0, 50)

        assert (first.id, second.id) == ("mrk_0001", "mrk_0002")
        assert region.id == "rgn_0001"
        assert (first.name, second.name) == ("Marker 1", "Marker 2")
        assert region.name == "Region 1"
        assert len(markers) == 3

    def test_markers_stay_ordered_by_frame(self) -> None:
        markers = MarkerList()
        markers.add_marker(900, "late")
        markers.add_marker(100, "early")
        markers.add_marker(500, "middle")

        assert [m.name for m in markers.markers] == ["early", "middle", "late"]

    def test_regions_stay_ordered_by_start(self) -> None:
        markers = MarkerList()
        markers.add_region(500, 600, "second")
        markers.add_region(0, 100, "first")

        assert [r.name for r in markers.regions] == ["first", "second"]

    def test_iterating_yields_markers_then_regions(self) -> None:
        markers = MarkerList()
        markers.add_region(0, 10, "region")
        markers.add_marker(5, "marker")

        assert [item.name for item in markers] == ["marker", "region"]

    def test_the_sequences_handed_out_are_snapshots(self) -> None:
        """A caller holding `markers` must not see a later add appear in it."""
        markers = MarkerList()
        markers.add_marker(10)
        before = markers.markers

        markers.add_marker(20)

        assert len(before) == 1
        assert len(markers.markers) == 2

    def test_removing_reports_whether_anything_went(self) -> None:
        markers = MarkerList()
        marker = markers.add_marker(10)
        region = markers.add_region(0, 5)

        assert markers.remove(marker.id)
        assert markers.remove(region.id)
        assert not markers.remove(marker.id)
        assert markers.is_empty

    def test_renaming_replaces_the_record_in_place(self) -> None:
        markers = MarkerList()
        marker = markers.add_marker(10, "Take 1")
        region = markers.add_region(0, 5, "Verse")

        assert markers.rename(marker.id, "Take 2").name == "Take 2"
        assert markers.rename(region.id, "Chorus").name == "Chorus"
        assert markers.get(marker.id).name == "Take 2"
        assert markers.get(region.id).name == "Chorus"
        assert marker.name == "Take 1"  # the original record is untouched

    def test_renaming_something_absent_raises(self) -> None:
        with pytest.raises(KeyError, match="mrk_9999"):
            MarkerList().rename("mrk_9999", "nope")

    def test_moving_a_marker_reorders_the_list(self) -> None:
        markers = MarkerList()
        first = markers.add_marker(100, "a")
        markers.add_marker(200, "b")

        markers.move(first.id, 300)

        assert [m.name for m in markers.markers] == ["b", "a"]

    def test_move_and_set_range_refuse_the_wrong_kind(self) -> None:
        markers = MarkerList()
        marker = markers.add_marker(10)
        region = markers.add_region(0, 5)

        with pytest.raises(KeyError, match="no marker"):
            markers.move(region.id, 1)
        with pytest.raises(KeyError, match="no region"):
            markers.set_range(marker.id, TimeRange(0, 1))

    def test_set_range_respans_a_region(self) -> None:
        markers = MarkerList()
        region = markers.add_region(0, 5)

        assert markers.set_range(region.id, TimeRange(10, 40)).length == 30

    def test_duplicate_ids_are_refused(self) -> None:
        markers = MarkerList()
        markers.add_marker(0, marker_id="mrk_0001")

        with pytest.raises(ValueError, match="duplicate marker id"):
            markers.add_marker(1, marker_id="mrk_0001")
        with pytest.raises(ValueError, match="duplicate marker id"):
            MarkerList([Marker("dup", "a", 0)], [Region("dup", "b", 0, 1)])

    def test_fresh_ids_skip_the_ones_already_in_use(self) -> None:
        markers = MarkerList([Marker("mrk_0001", "kept", 0)])

        assert markers.add_marker(10).id == "mrk_0002"

    def test_membership_is_by_id(self) -> None:
        markers = MarkerList()
        markers.add_marker(0, marker_id="mrk_0042")

        assert "mrk_0042" in markers
        assert "mrk_0001" not in markers
        assert 42 not in markers

    def test_clear_empties_both_kinds(self) -> None:
        markers = MarkerList()
        markers.add_marker(0)
        markers.add_region(0, 1)

        markers.clear()

        assert markers.is_empty

    def test_copies_are_equal_but_independent(self) -> None:
        markers = MarkerList()
        markers.add_marker(10)
        clone = markers.copy()

        clone.add_marker(20)

        assert len(markers) == 1
        assert clone != markers


class TestNavigation:
    @pytest.fixture()
    def markers(self) -> MarkerList:
        items = MarkerList()
        items.add_marker(100, "a")
        items.add_marker(500, "b")
        items.add_marker(900, "c")
        return items

    def test_next_marker_is_strictly_after_the_frame(self, markers: MarkerList) -> None:
        assert markers.next_marker(0).name == "a"
        assert markers.next_marker(100).name == "b"
        assert markers.next_marker(900) is None

    def test_previous_marker_is_strictly_before_the_frame(self, markers: MarkerList) -> None:
        assert markers.previous_marker(1_000).name == "c"
        assert markers.previous_marker(500).name == "a"
        assert markers.previous_marker(100) is None

    def test_nearest_marker_breaks_ties_towards_the_earlier_one(
        self, markers: MarkerList
    ) -> None:
        assert markers.nearest_marker(120).name == "a"
        assert markers.nearest_marker(300).name == "a"
        assert markers.nearest_marker(10_000).name == "c"
        assert MarkerList().nearest_marker(0) is None

    def test_regions_at_a_frame_include_overlaps(self) -> None:
        items = MarkerList()
        items.add_region(0, 100, "outer")
        items.add_region(50, 60, "inner")

        assert [r.name for r in items.regions_at(55)] == ["outer", "inner"]
        assert items.regions_at(100) == ()


class TestSerialization:
    def test_a_full_list_round_trips_through_json(self) -> None:
        markers = MarkerList()
        markers.add_marker(100, "Intro", color="#ff0000")
        markers.add_marker(4_410_000, "Outro")
        markers.add_region(200, 800, "Chorus")

        restored = MarkerList.from_json(markers.to_json())

        assert restored == markers
        assert [m.name for m in restored.markers] == ["Intro", "Outro"]
        assert restored.regions[0].name == "Chorus"

    def test_from_json_accepts_nothing(self) -> None:
        assert MarkerList.from_json(None).is_empty
        assert MarkerList.from_json([]).is_empty

    def test_entries_without_a_type_are_classified_by_their_fields(self) -> None:
        restored = MarkerList.from_json(
            [
                {"id": "mrk_0001", "name": "m", "frame": 10},
                {"id": "rgn_0001", "name": "r", "start": 0, "end": 5},
            ]
        )

        assert len(restored.markers) == 1
        assert len(restored.regions) == 1

    def test_an_unclassifiable_entry_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="unknown marker entry"):
            MarkerList.from_json([{"id": "x", "name": "y"}])

    def test_the_serialized_form_is_plain_json_types(self) -> None:
        import json

        markers = MarkerList()
        markers.add_marker(10)
        markers.add_region(0, 5)

        assert json.loads(json.dumps(markers.to_json())) == markers.to_json()


@pytest.fixture()
def window(qapp, loaded_clip: LoadedAudio):
    """A window holding the in-memory clip, as ``open_file`` would leave it."""
    from audio_studio.ui.main_window import MainWindow

    engine = AudioEngine(NullOutput(realtime=False), block_size=256)
    main = MainWindow(engine)
    main.resize(1200, 700)
    engine.set_clip(loaded_clip)
    main._bind_edit_session(loaded_clip)  # noqa: SLF001 - mirrors open_file()
    main._update_for_clip()  # noqa: SLF001
    yield main
    main._mark_project_saved()  # noqa: SLF001 - no close prompt in tests
    main.close()


class TestMarkerPanel:
    """The dockable list is a view: it reports intent and shows what it is given."""

    @pytest.fixture()
    def panel(self, qapp):
        from audio_studio.ui.marker_panel import MarkerPanel

        return MarkerPanel()

    def test_it_starts_empty_with_the_edit_buttons_off(self, panel) -> None:
        assert panel.row_count == 0
        assert not panel.rename_button.isEnabled()
        assert not panel.remove_button.isEnabled()

    def test_it_lists_markers_before_regions_with_timecodes(self, panel) -> None:
        markers = MarkerList()
        markers.add_marker(44_100, "Verse")
        markers.add_region(0, 22_050, "Head")

        panel.set_markers(markers, 44_100)

        assert panel.row_count == 2
        first = panel.tree.topLevelItem(0)
        assert first.text(0) == "Verse"
        assert first.text(1) == "00:01.000"
        assert first.text(2) == "—"
        assert panel.tree.topLevelItem(1).text(2) == "00:00.500"

    def test_selecting_a_row_enables_editing_and_is_announced(self, panel) -> None:
        markers = MarkerList()
        marker = markers.add_marker(10, "Cue")
        panel.set_markers(markers, 44_100)
        seen: list[object] = []
        panel.selectionChanged.connect(seen.append)

        assert panel.select(marker.id)

        assert panel.selected_id == marker.id
        assert panel.rename_button.isEnabled()
        assert seen[-1] == marker.id

    def test_the_selected_row_survives_a_refresh(self, panel) -> None:
        markers = MarkerList()
        marker = markers.add_marker(10, "Cue")
        panel.set_markers(markers, 44_100)
        panel.select(marker.id)

        markers.add_marker(20, "Other")
        panel.set_markers(markers, 44_100)

        assert panel.selected_id == marker.id

    def test_activating_a_region_row_asks_for_the_seek_and_the_range(self, panel) -> None:
        markers = MarkerList()
        markers.add_marker(10, "Cue")
        region = markers.add_region(100, 400, "Chorus")
        panel.set_markers(markers, 44_100)
        frames: list[int] = []
        regions: list[object] = []
        panel.goToRequested.connect(frames.append)
        panel.regionActivated.connect(regions.append)

        panel.tree.itemDoubleClicked.emit(panel.tree.topLevelItem(0), 0)  # the marker
        panel.tree.itemDoubleClicked.emit(panel.tree.topLevelItem(1), 0)  # the region

        assert frames == [10, 100]
        assert regions == [region]

    def test_the_buttons_report_intent_rather_than_editing(self, panel) -> None:
        markers = MarkerList()
        marker = markers.add_marker(10, "Cue")
        panel.set_markers(markers, 44_100)
        panel.select(marker.id)
        removals: list[str] = []
        panel.removeRequested.connect(removals.append)

        panel.remove_button.click()

        assert removals == [marker.id]
        assert panel.row_count == 1  # the panel does not edit the list itself


class TestMarkerCommands:
    def test_a_new_window_has_no_markers(self, window) -> None:
        assert window.markers.is_empty
        assert window.marker_panel.row_count == 0
        assert window.markers_dock.isHidden()

    def test_adding_a_marker_puts_it_at_the_playhead(self, window) -> None:
        window.engine.seek(12_345)

        marker = window.add_marker_at_playhead()

        assert marker is not None
        assert marker.frame == 12_345
        assert window.markers.markers == (marker,)
        assert window.marker_panel.row_count == 1
        assert window.track_panel.waveform.markers is window.markers

    def test_the_m_shortcut_is_wired_to_the_command(self, window) -> None:
        window.engine.seek(500)

        window.action_add_marker.trigger()

        assert window.action_add_marker.shortcut().toString() == "M"
        assert window.markers.markers[0].frame == 500

    def test_adding_a_marker_shows_the_dock_and_dirties_the_project(self, window) -> None:
        window._mark_project_saved()  # noqa: SLF001

        window.add_marker_at_playhead()

        assert not window.markers_dock.isHidden()
        assert window._has_unsaved_changes()  # noqa: SLF001

    def test_a_region_spans_the_selection(self, window) -> None:
        window.track_panel.waveform.set_selection(TimeRange(1_000, 5_000))

        region = window.add_region_from_selection()

        assert region is not None
        assert region.range == TimeRange(1_000, 5_000)
        assert window.markers.regions == (region,)

    def test_a_region_needs_a_selection(self, window) -> None:
        window.track_panel.waveform.clear_selection()

        assert window.add_region_from_selection() is None
        assert window.markers.is_empty
        assert "Select a range" in window.statusBar().currentMessage()

    def test_the_add_region_action_follows_the_selection(self, window) -> None:
        window.track_panel.waveform.clear_selection()
        assert not window.action_add_region.isEnabled()

        window.track_panel.waveform.set_selection(TimeRange(0, 100))
        assert window.action_add_region.isEnabled()

    def test_renaming_goes_through_the_dialog(self, window, monkeypatch) -> None:
        marker = window.add_marker_at_playhead()
        monkeypatch.setattr(
            "audio_studio.ui.main_window.QInputDialog.getText",
            lambda *args, **kwargs: ("Downbeat", True),
        )

        assert window.rename_marker(marker.id)

        assert window.markers.get(marker.id).name == "Downbeat"
        assert window.marker_panel.tree.topLevelItem(0).text(0) == "Downbeat"

    def test_a_cancelled_rename_changes_nothing(self, window, monkeypatch) -> None:
        marker = window.add_marker_at_playhead()
        monkeypatch.setattr(
            "audio_studio.ui.main_window.QInputDialog.getText",
            lambda *args, **kwargs: ("", False),
        )

        assert not window.rename_marker(marker.id)
        assert window.markers.get(marker.id).name == marker.name

    def test_removing_takes_the_row_with_it(self, window) -> None:
        marker = window.add_marker_at_playhead()

        assert window.remove_marker(marker.id)
        assert not window.remove_marker(marker.id)
        assert window.markers.is_empty
        assert window.marker_panel.row_count == 0

    def test_the_selected_row_drives_rename_and_remove(self, window) -> None:
        marker = window.add_marker_at_playhead()
        window.marker_panel.select(marker.id)

        assert window.action_remove_marker.isEnabled()
        assert window.remove_selected_marker()
        assert window.markers.is_empty
        assert not window.action_remove_marker.isEnabled()
        assert not window.remove_selected_marker()

    def test_clearing_empties_both_kinds(self, window) -> None:
        window.add_marker_at_playhead()
        window.track_panel.waveform.set_selection(TimeRange(0, 100))
        window.add_region_from_selection()

        window.clear_markers()

        assert window.markers.is_empty
        assert window.marker_panel.row_count == 0

    def test_closing_the_clip_drops_its_markers(self, window) -> None:
        window.add_marker_at_playhead()

        window.close_clip()

        assert window.markers.is_empty


class TestMarkerNavigation:
    def test_next_and_previous_move_the_playhead(self, window) -> None:
        window.engine.seek(1_000)
        window.add_marker_at_playhead()
        window.engine.seek(20_000)
        window.add_marker_at_playhead()
        window.engine.seek(0)

        assert window.go_to_next_marker()
        assert window.engine.position == 1_000
        assert window.go_to_next_marker()
        assert window.engine.position == 20_000
        assert not window.go_to_next_marker()

        assert window.go_to_previous_marker()
        assert window.engine.position == 1_000
        assert not window.go_to_previous_marker()

    def test_navigation_is_off_until_there_is_a_marker(self, window) -> None:
        assert not window.action_next_marker.isEnabled()

        window.add_marker_at_playhead()

        assert window.action_next_marker.isEnabled()
        assert window.action_prev_marker.isEnabled()

    def test_reaching_a_marker_selects_its_row(self, window) -> None:
        window.engine.seek(4_000)
        marker = window.add_marker_at_playhead()
        window.engine.seek(0)

        window.go_to_next_marker()

        assert window.marker_panel.selected_id == marker.id
        assert marker.name in window.statusBar().currentMessage()

    def test_activating_a_region_restores_its_range_as_the_selection(self, window) -> None:
        window.track_panel.waveform.set_selection(TimeRange(2_000, 6_000))
        region = window.add_region_from_selection()
        window.track_panel.waveform.clear_selection()

        window.marker_panel.regionActivated.emit(region)

        assert window.engine.selection == TimeRange(2_000, 6_000)


class TestMarkerProjectIntegration:
    def test_markers_survive_a_save_and_reopen(
        self, window, qapp, tmp_path: Path
    ) -> None:
        from audio_studio.project.store import load_project
        from audio_studio.ui.main_window import MainWindow

        window.engine.seek(3_000)
        window.add_marker_at_playhead()
        window.track_panel.waveform.set_selection(TimeRange(100, 900))
        window.add_region_from_selection()
        project_dir = tmp_path / "markers.hlproj"
        window._write_project(project_dir)  # noqa: SLF001
        window._mark_project_saved()  # noqa: SLF001

        other = MainWindow(AudioEngine(NullOutput(realtime=False)))
        try:
            other._apply_project(project_dir, load_project(project_dir))  # noqa: SLF001

            assert other.markers == window.markers
            assert other.marker_panel.row_count == 2
            assert other.track_panel.waveform.markers.markers[0].frame == 3_000
        finally:
            other._mark_project_saved()  # noqa: SLF001
            other.close()

    def test_opening_another_file_starts_a_fresh_list(
        self, window, wav_path: Path
    ) -> None:
        window.add_marker_at_playhead()
        window._mark_project_saved()  # noqa: SLF001

        assert window.open_file(wav_path)
        assert window.markers.is_empty


def test_the_waveform_paints_markers_without_error(qapp, loaded_clip: LoadedAudio) -> None:
    from PySide6.QtGui import QPixmap

    from audio_studio.core.peaks import PeakPyramid
    from audio_studio.ui.waveform_view import WaveformView

    view = WaveformView()
    view.resize(800, 200)
    view.set_clip(
        PeakPyramid(loaded_clip.buffer.data),
        loaded_clip.buffer.sample_rate,
        loaded_clip.buffer.data,
    )
    markers = MarkerList()
    markers.add_marker(0, "at the very start")
    markers.add_marker(view.n_frames // 2, "middle", color="#ff0000")
    markers.add_marker(view.n_frames, "at the very end")
    markers.add_marker(10, "", color="not-a-colour")
    markers.add_region(1_000, 20_000, "Chorus")
    markers.add_region(0, 0, "empty")

    view.set_markers(markers)

    assert view.markers is markers
    for frames in (view.n_frames, 20_000, 200):
        view.set_view(0, frames)
        target = QPixmap(view.size())
        view.render(target)
        assert not target.isNull()
