"""Track volume automation: the curve, the mixer that rides it and the lane.

The interesting claims here are about *continuity* and *transparency*. A curve
is sampled per block, so the level the mixer produces must not depend on where
the block boundaries happen to fall; and a curve that asks for unity must leave
the audio bit-identical, because an automation lane parked at 0 dB is exactly
the case a user reaches for when they want "no change yet".
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from audio_studio.core.loader import LoadedAudio
from audio_studio.core.sample_source import MemorySampleSource
from audio_studio.core.session import (
    MAX_GAIN_DB,
    SILENCE_DB,
    AutomationPoint,
    GainAutomation,
    MultitrackSession,
    Track,
)
from audio_studio.core.types import AudioBuffer, db_to_amplitude
from audio_studio.project.store import load_project, restore_multitrack, save_project

RATE = 48_000
FRAMES = 4_800


def flat(value: float = 1.0, n_frames: int = FRAMES, *, channels: int = 2) -> MemorySampleSource:
    """A DC source, so a rendered block reads back as the gain applied to it."""
    data = np.full((n_frames, channels), value, dtype=np.float32)
    return MemorySampleSource(AudioBuffer(data, RATE))


@pytest.fixture()
def session() -> MultitrackSession:
    return MultitrackSession(sample_rate=RATE, n_channels=2)


@pytest.fixture()
def automated(session: MultitrackSession) -> tuple[MultitrackSession, Track]:
    """One DC track ramping from unity down to -12 dB across its length."""
    track = session.add_track("Vox")
    session.add_clip(track, flat())
    track.automation.line(0, FRAMES - 1, 0.0, -12.0)
    return session, track


# ------------------------------------------------------------------- points


def test_a_point_clamps_its_frame_and_its_value_to_the_fader_range() -> None:
    assert AutomationPoint(-10, 0.0).frame == 0
    assert AutomationPoint(0, 99.0).value == MAX_GAIN_DB
    assert AutomationPoint(0, -400.0).value == SILENCE_DB
    assert AutomationPoint(7.0, -6.0).frame == 7  # type: ignore[arg-type]


def test_points_are_ordered_and_one_frame_holds_at_most_one_point() -> None:
    curve = GainAutomation([(100, -6.0), (0, 0.0), (100, -3.0)])

    assert [point.frame for point in curve] == [0, 100]
    assert curve.point_at(100) == AutomationPoint(100, -3.0)  # the later one wins
    assert len(curve) == 2


def test_setting_a_point_replaces_the_one_already_on_that_frame() -> None:
    curve = GainAutomation([(0, 0.0), (480, -6.0)])

    curve.set_point(480, -2.0)

    assert len(curve) == 2
    assert curve.value_at(480) == pytest.approx(-2.0)


def test_moving_a_point_takes_it_off_its_old_frame() -> None:
    curve = GainAutomation([(0, 0.0), (480, -6.0)])

    curve.move_point(480, 960, -9.0)

    assert [point.frame for point in curve] == [0, 960]
    assert curve.value_at(960) == pytest.approx(-9.0)
    assert curve.move_point(12_345, 0, 0.0) is None


def test_removing_and_clearing_points_empties_the_curve() -> None:
    curve = GainAutomation([(0, 0.0), (480, -6.0)])

    assert curve.remove_point(480) is True
    assert curve.remove_point(480) is False

    curve.clear()
    assert curve.is_empty


def test_nearest_only_grabs_a_point_inside_its_radius() -> None:
    curve = GainAutomation([(0, 0.0), (1_000, -6.0)])

    assert curve.nearest(1_020, 50) == AutomationPoint(1_000, -6.0)
    assert curve.nearest(1_200, 50) is None


# -------------------------------------------------------------- the envelope


def test_the_curve_interpolates_linearly_between_its_points() -> None:
    curve = GainAutomation([(0, 0.0), (100, -10.0)])

    assert curve.value_at(0) == pytest.approx(0.0)
    assert curve.value_at(50) == pytest.approx(-5.0)
    assert curve.value_at(100) == pytest.approx(-10.0)


def test_the_outermost_values_are_held_rather_than_extrapolated() -> None:
    curve = GainAutomation([(100, -6.0), (200, 0.0)])

    assert curve.value_at(0) == pytest.approx(-6.0)
    assert curve.value_at(99) == pytest.approx(-6.0)
    assert curve.value_at(10_000) == pytest.approx(0.0)


def test_a_single_point_holds_its_value_everywhere() -> None:
    curve = GainAutomation([(500, -3.0)])

    assert curve.values(0, 1_000) == pytest.approx(np.full(1_000, -3.0), abs=1e-5)


def test_the_envelope_reaches_exact_zero_at_the_silence_floor() -> None:
    curve = GainAutomation([(0, SILENCE_DB), (10, SILENCE_DB - 20)])

    assert not np.any(curve.amplitudes(0, 10))
    assert curve.silent is True


def test_an_empty_curve_is_not_the_same_as_a_curve_at_unity() -> None:
    empty = GainAutomation()
    unity = GainAutomation([(0, 0.0)])

    assert empty.is_empty and not unity.is_empty
    assert empty.silent is False  # "no curve" is not "no signal"
    assert unity.amplitudes(0, 4) == pytest.approx(np.ones(4))


# ------------------------------------------------------------------ the mix


def test_an_unautomated_track_still_answers_to_its_fader(session: MultitrackSession) -> None:
    track = session.add_track("Vox")
    session.add_clip(track, flat())
    track.gain_db = -6.0

    assert track.has_automation is False
    assert track.effective_gain_db(0) == pytest.approx(-6.0)
    assert session.read(0, 16) == pytest.approx(db_to_amplitude(-6.0), abs=1e-6)


def test_the_mixer_rides_the_curve_across_the_block(automated) -> None:  # noqa: ANN001
    session, _track = automated

    block = session.read(0, FRAMES)

    assert block[0, 0] == pytest.approx(1.0, abs=1e-6)
    assert block[-1, 0] == pytest.approx(db_to_amplitude(-12.0), abs=1e-6)
    assert block[FRAMES // 2, 0] == pytest.approx(db_to_amplitude(-6.0), abs=1e-3)
    # Monotone all the way down: no step at any point on the ramp.
    assert np.all(np.diff(block[:, 0]) < 0)


def test_where_the_block_boundary_falls_does_not_change_the_level(automated) -> None:  # noqa: ANN001
    session, _track = automated

    whole = session.read(0, FRAMES)
    in_pieces = np.concatenate(
        [session.read(start, 337) for start in range(0, FRAMES, 337)]
    )[:FRAMES]

    assert np.array_equal(whole, in_pieces)


def test_a_curve_at_unity_is_bit_transparent(session: MultitrackSession) -> None:
    source = flat()
    track = session.add_track("Vox")
    session.add_clip(track, source)
    track.automation.line(0, FRAMES - 1, 0.0, 0.0)

    assert np.array_equal(session.read(0, FRAMES), source.read(0, FRAMES))


def test_automation_takes_the_fader_out_of_the_signal_path(automated) -> None:  # noqa: ANN001
    session, track = automated
    before = session.read(0, 512)

    track.gain_db = -24.0

    assert np.array_equal(session.read(0, 512), before)
    assert track.effective_gain_db(0) == pytest.approx(0.0)

    # Emptying the curve hands the lane back to the fader it was ignoring.
    track.automation.clear()
    assert session.read(0, 16) == pytest.approx(db_to_amplitude(-24.0), abs=1e-6)


def test_a_curve_parked_at_silence_keeps_the_lane_off_the_summing_bus(
    session: MultitrackSession,
) -> None:
    track = session.add_track("Vox")
    session.add_clip(track, flat())
    track.automation.line(0, FRAMES, SILENCE_DB, SILENCE_DB)

    assert track.silent is True
    assert np.count_nonzero(session.read(0, FRAMES)) == 0


def test_mute_still_wins_over_an_automated_lane(automated) -> None:  # noqa: ANN001
    session, track = automated

    track.mute = True

    assert session.audible_tracks() == ()
    assert np.count_nonzero(session.read(0, 512)) == 0


def test_automation_and_pan_apply_together(session: MultitrackSession) -> None:
    track = session.add_track("Vox")
    session.add_clip(track, flat())
    track.pan = -1.0
    track.automation.line(0, FRAMES, -6.0, -6.0)

    block = session.read(0, 64)

    assert block[:, 0] == pytest.approx(db_to_amplitude(-6.0), abs=1e-6)
    assert np.count_nonzero(block[:, 1]) == 0


def test_a_bus_scales_the_automated_lane_it_carries(session: MultitrackSession) -> None:
    bus = session.add_bus("Drums")
    track = session.add_track("Kick")
    session.add_clip(track, flat())
    session.route_track(track, bus)
    track.automation.line(0, FRAMES, -6.0, -6.0)
    bus.gain_db = -6.0

    stems = session.render_buses(0, 32)

    assert stems[bus.bus_id] == pytest.approx(db_to_amplitude(-12.0), abs=1e-6)


def test_per_track_stems_follow_the_curve(automated) -> None:  # noqa: ANN001
    session, track = automated

    stem = session.render_tracks(0, FRAMES)[track.track_id]

    assert stem[0, 0] == pytest.approx(1.0, abs=1e-6)
    assert stem[-1, 0] == pytest.approx(db_to_amplitude(-12.0), abs=1e-6)


def test_editing_a_curve_notifies_the_session(session: MultitrackSession) -> None:
    track = session.add_track("Vox")
    seen: list[int] = []
    session.add_listener(lambda item: seen.append(item.revision))

    track.automation.set_point(0, -3.0)
    track.automation.set_point(0, -3.0)  # same value: nothing changed, nothing sent
    track.automation.remove_point(0)

    assert len(seen) == 2
    assert session.revision == seen[-1]


def test_assigning_a_whole_curve_rebinds_the_notification(session: MultitrackSession) -> None:
    track = session.add_track("Vox")
    orphan = track.automation
    track.automation = GainAutomation([(0, -6.0)])
    revision = session.revision

    orphan.set_point(0, 0.0)  # the detached curve must not reach the session
    assert session.revision == revision

    track.automation.set_point(480, -9.0)
    assert session.revision == revision + 1


# ---------------------------------------------------------------- seeding


def test_seeding_lands_points_on_the_clip_boundaries(session: MultitrackSession) -> None:
    track = session.add_track("Vox")
    session.add_clip(track, flat(n_frames=1_000), start=500)
    session.add_clip(track, flat(n_frames=1_000), start=4_000)
    track.gain_db = -4.0

    track.seed_automation()

    assert [point.frame for point in track.automation] == [500, 1_500, 4_000, 5_000]
    assert all(point.value == pytest.approx(-4.0) for point in track.automation)


def test_seeding_an_empty_lane_still_gives_two_points_to_drag(
    session: MultitrackSession,
) -> None:
    track = session.add_track("Empty")

    track.seed_automation()

    assert [point.frame for point in track.automation] == [0, 1]


def test_seeding_at_the_current_fader_is_inaudible(session: MultitrackSession) -> None:
    track = session.add_track("Vox")
    session.add_clip(track, flat())
    track.gain_db = -6.0
    before = session.read(0, 256)

    track.seed_automation()

    assert session.read(0, 256) == pytest.approx(before, abs=1e-7)


# ------------------------------------------------------------ serialization


def test_a_curve_round_trips_through_its_json_form() -> None:
    curve = GainAutomation([(0, 0.0), (480, -6.5), (960, 3.0)])

    restored = GainAutomation.from_json(json.loads(json.dumps(curve.to_json())))

    assert restored.points == curve.points
    assert curve.to_json()[1] == [480, -6.5]


def test_reading_a_curve_skips_the_points_it_cannot_understand() -> None:
    curve = GainAutomation.from_json(
        [[0, 0.0], "nonsense", [480], {"frame": 960, "value": -3.0}, {"frame": "x"}, None]
    )

    assert [point.frame for point in curve] == [0, 960]
    assert GainAutomation.from_json(None).is_empty
    assert GainAutomation.from_json("[[0, 0]]").is_empty


def test_a_project_bundle_carries_the_automation_back(
    loaded_clip: LoadedAudio, tmp_path: Path
) -> None:
    rate = loaded_clip.buffer.sample_rate
    mt = MultitrackSession(sample_rate=rate, n_channels=loaded_clip.buffer.n_channels)
    track = mt.add_track(Track(name="Vox"))
    mt.add_clip(track, MemorySampleSource(loaded_clip.buffer), start=0)
    track.automation.set_points([(0, 0.0), (rate // 2, -8.0), (rate, 2.5)])

    root = tmp_path / "automated.hlproj"
    save_project(
        root,
        edit_session=None,
        editor_clip=None,
        multitrack=mt,
        workspace="multitrack",
        view_mode="split",
        playhead=0,
        selection=None,
    )
    restored = restore_multitrack(load_project(root).multitrack, root)

    assert restored.tracks[0].automation.points == track.automation.points
    assert restored.tracks[0].has_automation is True
    assert restored.read(0, 64) == pytest.approx(mt.read(0, 64), abs=1e-6)


def test_a_track_without_automation_does_not_write_the_key(
    loaded_clip: LoadedAudio, tmp_path: Path
) -> None:
    mt = MultitrackSession(sample_rate=loaded_clip.buffer.sample_rate)
    mt.add_track(Track(name="Plain"))

    root = tmp_path / "plain.hlproj"
    save_project(
        root,
        edit_session=None,
        editor_clip=None,
        multitrack=mt,
        workspace="multitrack",
        view_mode="split",
        playhead=0,
        selection=None,
    )

    payload = json.loads((root / "project.json").read_text(encoding="utf-8"))
    assert "automation" not in payload["multitrack"]["tracks"][0]
    assert restore_multitrack(payload["multitrack"], root).tracks[0].has_automation is False


def test_a_bundle_written_before_automation_existed_still_loads(tmp_path: Path) -> None:
    payload = {
        "sample_rate": RATE,
        "channels": 2,
        "master_gain_db": 0.0,
        "media": [],
        "tracks": [{"id": "trk_x", "name": "Old", "gain_db": -3.0, "clips": []}],
    }

    restored = restore_multitrack(payload, tmp_path)

    assert restored.tracks[0].has_automation is False
    assert restored.tracks[0].gain_db == pytest.approx(-3.0)


# --------------------------------------------------------------- the lane


@pytest.fixture()
def view(qapp: object, automated):  # noqa: ANN001, ANN201 - Qt widget
    from audio_studio.ui.multitrack_view import MultitrackView

    session, _track = automated
    widget = MultitrackView(session)
    widget.resize(900, 300)
    yield widget
    widget.close()


def press(lane, x: float, y: float, button: str = "left") -> None:  # noqa: ANN001
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent

    which = (
        Qt.MouseButton.LeftButton if button == "left" else Qt.MouseButton.RightButton
    )
    lane.mousePressEvent(
        QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(x, y),
            which,
            which,
            Qt.KeyboardModifier.NoModifier,
        )
    )


def drag_to(lane, x: float, y: float) -> None:  # noqa: ANN001
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent

    lane.mouseMoveEvent(
        QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(x, y),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )


def test_a_track_that_arrives_automated_opens_with_its_lane_showing(view) -> None:  # noqa: ANN001
    from audio_studio.ui.multitrack_view import AUTOMATION_LANE_HEIGHT, LANE_HEIGHT

    strip = view.strips[0]

    assert strip.automation_visible is True
    assert strip.header.automation_button.isChecked() is True
    assert strip.height() == LANE_HEIGHT + AUTOMATION_LANE_HEIGHT


def test_the_header_button_opens_the_lane_and_seeds_a_flat_curve(
    qapp: object, session: MultitrackSession
) -> None:
    from audio_studio.ui.multitrack_view import LANE_HEIGHT, MultitrackView

    track = session.add_track("Vox")
    session.add_clip(track, flat())
    track.gain_db = -5.0
    view = MultitrackView(session)
    view.resize(900, 300)
    try:
        strip = view.strips[0]
        assert strip.automation_visible is False
        assert strip.height() == LANE_HEIGHT

        strip.header.automation_button.setChecked(True)

        assert strip.automation_visible is True
        assert track.has_automation is True
        assert [point.value for point in track.automation] == [
            pytest.approx(-5.0),
            pytest.approx(-5.0),
        ]
    finally:
        view.close()


def test_closing_the_lane_keeps_the_curve(view) -> None:  # noqa: ANN001
    strip = view.strips[0]

    strip.header.automation_button.setChecked(False)

    assert strip.automation_visible is False
    assert strip.track.has_automation is True


def test_clicking_the_lane_drops_a_point_where_the_mouse_is(view) -> None:  # noqa: ANN001
    lane = view.strips[0].automation_lane
    lane.resize(700, 40)
    edited: list[int] = []
    lane.curveChanged.connect(lambda: edited.append(1))
    before = len(lane.track.automation)

    press(lane, 350.0, 10.0)

    assert len(lane.track.automation) == before + 1
    assert edited
    point = lane.track.automation.nearest(lane.x_to_frame(350.0), 4)
    assert point is not None
    assert point.value == pytest.approx(lane.y_to_db(10.0), abs=0.5)


def test_dragging_moves_the_point_the_press_grabbed(view) -> None:  # noqa: ANN001
    lane = view.strips[0].automation_lane
    lane.resize(700, 40)
    before = len(lane.track.automation)

    press(lane, 300.0, 10.0)
    drag_to(lane, 420.0, 30.0)

    assert len(lane.track.automation) == before + 1  # dragged, not duplicated
    moved = lane.track.automation.nearest(lane.x_to_frame(420.0), 8)
    assert moved is not None
    assert moved.value == pytest.approx(lane.y_to_db(30.0), abs=0.5)
    assert lane.track.automation.nearest(lane.x_to_frame(300.0), 8) is None


def test_a_drag_is_audible_in_the_mix(view, automated) -> None:  # noqa: ANN001
    session, track = automated
    lane = view.strips[0].automation_lane
    lane.resize(700, 40)
    lane.set_view(0, FRAMES)
    before = session.read(0, FRAMES)

    press(lane, 350.0, 4.0)  # top of the lane: full boost

    after = session.read(0, FRAMES)
    assert after[FRAMES // 2, 0] > before[FRAMES // 2, 0]


def test_right_clicking_removes_a_point(view) -> None:  # noqa: ANN001
    lane = view.strips[0].automation_lane
    lane.resize(700, 40)
    press(lane, 350.0, 10.0)
    frame = lane.x_to_frame(350.0)
    assert lane.track.automation.nearest(frame, 8) is not None

    press(lane, 350.0, 10.0, button="right")

    assert lane.track.automation.nearest(frame, 8) is None


def test_the_lane_maps_the_fader_range_onto_its_height(view) -> None:  # noqa: ANN001
    from audio_studio.ui.multitrack_view import MIN_STRIP_DB

    lane = view.strips[0].automation_lane
    lane.resize(700, 40)

    assert lane.db_to_y(MAX_GAIN_DB) < lane.db_to_y(0.0) < lane.db_to_y(MIN_STRIP_DB)
    assert lane.y_to_db(lane.db_to_y(-12.0)) == pytest.approx(-12.0, abs=1.5)
    # Out-of-range clicks clamp instead of running off the fader's scale.
    assert lane.y_to_db(-50.0) == pytest.approx(MAX_GAIN_DB)
    assert lane.y_to_db(500.0) == pytest.approx(MIN_STRIP_DB)


def test_the_automated_header_shows_the_fader_as_inert(view) -> None:  # noqa: ANN001
    header = view.strips[0].header

    assert header.gain_slider.isEnabled() is False
    assert "auto" in header.gain_label.text()

    view.strips[0].track.automation.clear()
    view.refresh()

    assert header.gain_slider.isEnabled() is True
    assert "auto" not in header.gain_label.text()


def test_the_lane_paints_its_curve_and_its_empty_state(view) -> None:  # noqa: ANN001
    lane = view.strips[0].automation_lane
    lane.resize(700, 40)

    drawn = lane.grab().toImage()
    colours = {drawn.pixel(x, y) for x in range(0, 700, 11) for y in range(0, 40, 3)}
    assert len(colours) > 2

    lane.track.automation.clear()
    lane.grab()  # the dashed "flat at the fader" state must paint too


def test_an_edit_in_the_lane_marks_the_session_dirty(view) -> None:  # noqa: ANN001
    lane = view.strips[0].automation_lane
    lane.resize(700, 40)
    seen: list[int] = []
    view.sessionChanged.connect(lambda: seen.append(1))

    press(lane, 200.0, 12.0)

    assert seen
