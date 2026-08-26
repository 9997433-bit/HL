"""Timeline markers and named regions."""

from __future__ import annotations

import pytest

from audio_studio.core.markers import Marker, MarkerList, Region
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

