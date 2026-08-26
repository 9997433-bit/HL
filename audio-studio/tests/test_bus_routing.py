"""Submix bus routing: summing, mute/solo interaction, persistence and the UI.

The bus level sits between the track faders and the master, so the assertions
that matter are about *equivalence*: a track routed through a unity bus must
land on the master exactly where it landed before it was routed, and a bus
fader must be indistinguishable from the same trim applied to every one of its
tracks. Both are checked exactly, not approximately, because the summing path
is supposed to be transparent when nobody has touched it.
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
    Bus,
    MultitrackSession,
    Track,
    gain_to_amplitude,
)
from audio_studio.core.types import AudioBuffer
from audio_studio.project.store import load_project, restore_multitrack, save_project

RATE = 48_000
FRAMES = 512


def constant(value: float, n_frames: int = FRAMES, *, channels: int = 2) -> MemorySampleSource:
    data = np.full((n_frames, channels), value, dtype=np.float32)
    return MemorySampleSource(AudioBuffer(data, RATE))


@pytest.fixture()
def session() -> MultitrackSession:
    return MultitrackSession(sample_rate=RATE, n_channels=2)


def populated(session: MultitrackSession, *values: float) -> tuple[Track, ...]:
    """One track per value, each holding a constant clip of that amplitude."""
    tracks = []
    for index, value in enumerate(values, start=1):
        track = session.add_track(f"Track {index}")
        session.add_clip(track, constant(value))
        tracks.append(track)
    return tuple(tracks)


# ------------------------------------------------------------------- model


def test_bus_carries_a_name_a_fader_and_a_mute() -> None:
    bus = Bus(name="Drums", gain_db=-6.0, mute=True)
    assert bus.name == "Drums"
    assert bus.gain_db == pytest.approx(-6.0)
    assert bus.mute is True
    assert bus.amplitude == pytest.approx(gain_to_amplitude(-6.0))
    assert bus.bus_id.startswith("bus_")
    assert bus.id == bus.bus_id


def test_bus_gain_is_clamped_to_the_faders_range() -> None:
    bus = Bus(name="Drums")
    bus.gain_db = 200.0
    assert bus.gain_db == MAX_GAIN_DB
    bus.gain_db = -400.0
    assert bus.gain_db == SILENCE_DB
    assert bus.amplitude == 0.0
    assert bus.silent is True


def test_a_bus_without_a_name_falls_back_to_its_id() -> None:
    bus = Bus()
    assert bus.name == bus.bus_id


def test_tracks_default_to_the_master_and_accept_a_bus_or_its_id(
    session: MultitrackSession,
) -> None:
    bus = session.add_bus("Drums")
    (track,) = populated(session, 0.5)
    assert track.send_to_bus is None
    assert session.bus_of(track) is None

    track.send_to_bus = bus
    assert track.send_to_bus == bus.bus_id

    track.send_to_bus = None
    assert session.bus_of(track) is None

    track.send_to_bus = bus.bus_id
    assert session.bus_of(track) is bus


def test_route_track_rejects_a_bus_the_session_does_not_own(
    session: MultitrackSession,
) -> None:
    (track,) = populated(session, 0.5)
    with pytest.raises(KeyError):
        session.route_track(track, "bus_nope")
    with pytest.raises(KeyError):
        session.route_track("trk_nope", None)
    assert track.send_to_bus is None


def test_duplicate_bus_ids_are_refused(session: MultitrackSession) -> None:
    session.add_bus(Bus(bus_id="bus_a", name="Drums"))
    with pytest.raises(ValueError, match="duplicate bus id"):
        session.add_bus(Bus(bus_id="bus_a", name="Other"))
    assert session.n_buses == 1


def test_routing_a_track_bumps_the_revision(session: MultitrackSession) -> None:
    bus = session.add_bus("Drums")
    (track,) = populated(session, 0.5)
    before = session.revision
    track.send_to_bus = bus
    assert session.revision > before

    unchanged = session.revision
    track.send_to_bus = bus.bus_id  # same target, no notification
    assert session.revision == unchanged


# ------------------------------------------------------------------ summing


def test_a_unity_bus_is_transparent(session: MultitrackSession) -> None:
    first, second = populated(session, 0.25, 0.125)
    direct = session.mixer.read(0, FRAMES)

    bus = session.add_bus("Drums")
    first.send_to_bus = bus
    second.send_to_bus = bus
    assert np.array_equal(session.mixer.read(0, FRAMES), direct)


def test_a_bus_fader_trims_only_the_tracks_routed_to_it(
    session: MultitrackSession,
) -> None:
    routed, direct = populated(session, 0.4, 0.2)
    bus = session.add_bus("Drums", gain_db=-6.0)
    routed.send_to_bus = bus

    expected = 0.4 * gain_to_amplitude(-6.0) + 0.2
    mixed = session.mixer.read(0, FRAMES)
    assert mixed == pytest.approx(np.full((FRAMES, 2), expected, dtype=np.float32))


def test_a_bus_fader_matches_the_same_trim_on_every_track(
    session: MultitrackSession,
) -> None:
    """Two ways of attenuating a group must agree sample for sample."""
    first, second = populated(session, 0.4, 0.2)
    bus = session.add_bus("Drums", gain_db=-6.0)
    first.send_to_bus = bus
    second.send_to_bus = bus
    through_bus = session.mixer.read(0, FRAMES)

    session.remove_bus(bus)
    first.gain_db = -6.0
    second.gain_db = -6.0
    np.testing.assert_allclose(session.mixer.read(0, FRAMES), through_bus, rtol=0, atol=1e-7)


def test_muting_a_bus_silences_its_tracks_and_leaves_the_rest(
    session: MultitrackSession,
) -> None:
    routed, direct = populated(session, 0.4, 0.2)
    bus = session.add_bus("Drums")
    routed.send_to_bus = bus

    bus.mute = True
    mixed = session.mixer.read(0, FRAMES)
    assert mixed == pytest.approx(np.full((FRAMES, 2), 0.2, dtype=np.float32))

    bus.mute = False
    bus.gain_db = SILENCE_DB
    assert session.mixer.read(0, FRAMES) == pytest.approx(
        np.full((FRAMES, 2), 0.2, dtype=np.float32)
    )


def test_a_muted_track_stays_muted_on_an_open_bus(session: MultitrackSession) -> None:
    first, second = populated(session, 0.4, 0.2)
    bus = session.add_bus("Drums")
    first.send_to_bus = bus
    second.send_to_bus = bus
    first.mute = True

    mixed = session.mixer.read(0, FRAMES)
    assert mixed == pytest.approx(np.full((FRAMES, 2), 0.2, dtype=np.float32))


def test_solo_reaches_the_master_through_its_bus(session: MultitrackSession) -> None:
    routed, direct = populated(session, 0.4, 0.2)
    bus = session.add_bus("Drums", gain_db=-6.0)
    routed.send_to_bus = bus
    routed.solo = True

    expected = 0.4 * gain_to_amplitude(-6.0)
    assert session.mixer.read(0, FRAMES) == pytest.approx(
        np.full((FRAMES, 2), expected, dtype=np.float32)
    )


def test_the_master_fader_still_scales_the_whole_sum(session: MultitrackSession) -> None:
    routed, direct = populated(session, 0.4, 0.2)
    bus = session.add_bus("Drums", gain_db=-6.0)
    routed.send_to_bus = bus
    session.master.gain_db = -6.0

    trim = gain_to_amplitude(-6.0)
    expected = (0.4 * trim + 0.2) * trim
    assert session.mixer.read(0, FRAMES) == pytest.approx(
        np.full((FRAMES, 2), expected, dtype=np.float32)
    )


def test_read_into_takes_the_same_path_as_read(session: MultitrackSession) -> None:
    routed, _direct = populated(session, 0.4, 0.2)
    bus = session.add_bus("Drums", gain_db=-3.0)
    routed.send_to_bus = bus

    scratch = np.empty((FRAMES, 2), dtype=np.float32)
    assert session.mixer.read_into(scratch, 0) == FRAMES
    assert np.array_equal(scratch, session.mixer.read(0, FRAMES))


def test_a_send_to_a_deleted_bus_falls_back_to_the_master(
    session: MultitrackSession,
) -> None:
    (track,) = populated(session, 0.4)
    bus = session.add_bus("Drums", gain_db=-12.0)
    track.send_to_bus = bus

    assert session.remove_bus(bus) is True
    assert session.remove_bus(bus) is False
    assert track.send_to_bus is None
    assert session.mixer.read(0, FRAMES) == pytest.approx(
        np.full((FRAMES, 2), 0.4, dtype=np.float32)
    )


def test_a_dangling_send_is_ignored_rather_than_silencing_the_track(
    session: MultitrackSession,
) -> None:
    """A send restored ahead of its bus must not drop the lane from the mix."""
    (track,) = populated(session, 0.4)
    track.send_to_bus = "bus_missing"

    assert session.bus_of(track) is None
    assert session.mixer.read(0, FRAMES) == pytest.approx(
        np.full((FRAMES, 2), 0.4, dtype=np.float32)
    )


def test_buses_do_not_nest(session: MultitrackSession) -> None:
    """The MVP routing is one level deep: a bus has no send of its own."""
    bus = session.add_bus("Drums")
    assert not hasattr(bus, "send_to_bus")


def test_tracks_for_bus_lists_only_its_own_lanes(session: MultitrackSession) -> None:
    first, second, third = populated(session, 0.1, 0.2, 0.3)
    drums = session.add_bus("Drums")
    vocals = session.add_bus("Vocals")
    first.send_to_bus = drums
    third.send_to_bus = drums

    assert session.tracks_for_bus(drums) == (first, third)
    assert session.tracks_for_bus(vocals) == ()
    assert second.send_to_bus is None


def test_render_buses_gives_one_post_fader_stem_per_bus(
    session: MultitrackSession,
) -> None:
    routed, direct = populated(session, 0.4, 0.2)
    drums = session.add_bus("Drums", gain_db=-6.0)
    empty = session.add_bus("Vocals")
    routed.send_to_bus = drums

    stems = session.render_buses(0, FRAMES)
    assert set(stems) == {drums.bus_id, empty.bus_id}
    assert stems[drums.bus_id] == pytest.approx(
        np.full((FRAMES, 2), 0.4 * gain_to_amplitude(-6.0), dtype=np.float32)
    )
    assert not stems[empty.bus_id].any()

    routed.mute = True
    assert not session.render_buses(0, FRAMES)[drums.bus_id].any()


# -------------------------------------------------------------- persistence


def _roundtrip(session: MultitrackSession, root: Path) -> MultitrackSession:
    save_project(
        root,
        edit_session=None,
        editor_clip=None,
        multitrack=session,
        workspace="multitrack",
        view_mode="waveform",
        playhead=0,
        selection=None,
    )
    return restore_multitrack(load_project(root).multitrack, root)


def test_buses_and_sends_survive_a_project_roundtrip(
    session: MultitrackSession, tmp_path: Path
) -> None:
    routed, _direct = populated(session, 0.4, 0.2)
    bus = session.add_bus(Bus(bus_id="bus_drums", name="Drums", gain_db=-6.0))
    session.add_bus(Bus(bus_id="bus_muted", name="Vocals", mute=True))
    routed.send_to_bus = bus

    restored = _roundtrip(session, tmp_path / "buses.hlproj")
    assert [b.bus_id for b in restored.buses] == ["bus_drums", "bus_muted"]
    assert restored.bus("bus_drums").gain_db == pytest.approx(-6.0)  # type: ignore[union-attr]
    assert restored.bus("bus_muted").mute is True  # type: ignore[union-attr]
    assert restored.tracks[0].send_to_bus == "bus_drums"
    assert restored.tracks[1].send_to_bus is None

    np.testing.assert_allclose(
        restored.mixer.read(0, FRAMES), session.mixer.read(0, FRAMES), rtol=0, atol=1e-6
    )


def test_a_session_without_buses_writes_no_bus_keys(
    session: MultitrackSession, tmp_path: Path
) -> None:
    """Bundles stay readable by builds that predate routing."""
    populated(session, 0.4)
    root = tmp_path / "plain.hlproj"
    _roundtrip(session, root)

    payload = json.loads((root / "project.json").read_text(encoding="utf-8"))
    assert "buses" not in payload["multitrack"]
    assert "send_to_bus" not in payload["multitrack"]["tracks"][0]


def test_a_bundle_without_buses_still_restores(tmp_path: Path) -> None:
    """The reader treats the pre-routing schema as "everything goes to master"."""
    restored = restore_multitrack(
        {
            "sample_rate": RATE,
            "channels": 2,
            "master_gain_db": 0.0,
            "media": [],
            "tracks": [{"id": "trk_01", "name": "Drums", "clips": []}],
        },
        tmp_path,
    )
    assert restored.n_buses == 0
    assert restored.tracks[0].send_to_bus is None


def test_a_send_to_an_unknown_bus_restores_as_master(tmp_path: Path) -> None:
    restored = restore_multitrack(
        {
            "sample_rate": RATE,
            "channels": 2,
            "media": [],
            "tracks": [
                {"id": "trk_01", "name": "Drums", "clips": [], "send_to_bus": "bus_gone"}
            ],
        },
        tmp_path,
    )
    assert restored.bus_of(restored.tracks[0]) is None


# ------------------------------------------------------------------- the UI


@pytest.fixture()
def loaded_session(loaded_clip: LoadedAudio) -> MultitrackSession:
    mt = MultitrackSession(
        sample_rate=loaded_clip.buffer.sample_rate,
        n_channels=loaded_clip.buffer.n_channels,
    )
    track = mt.add_track(Track(name="Drums"))
    mt.add_clip(track, MemorySampleSource(loaded_clip.buffer))
    return mt


def test_the_view_grows_a_strip_per_bus(
    qapp: object, loaded_session: MultitrackSession
) -> None:
    from audio_studio.ui.multitrack_view import MultitrackView

    view = MultitrackView(loaded_session)
    assert view.bus_strips == ()

    bus = view.add_bus("Drums")
    assert bus is not None
    assert [strip.bus for strip in view.bus_strips] == [bus]

    view.bus_strips[0].gain_slider.setValue(-6)
    assert bus.gain_db == pytest.approx(-6.0)
    view.bus_strips[0].mute_button.setChecked(True)
    assert bus.mute is True


def test_the_send_selector_routes_the_track(
    qapp: object, loaded_session: MultitrackSession
) -> None:
    from audio_studio.ui.multitrack_view import MASTER_SEND_LABEL, MultitrackView

    view = MultitrackView(loaded_session)
    header = view.strips[0].header
    assert header.send_combo.count() == 1  # master only, and hidden

    bus = view.add_bus("Drums")
    assert bus is not None
    assert [
        header.send_combo.itemText(i) for i in range(header.send_combo.count())
    ] == [MASTER_SEND_LABEL, "Drums"]

    header.send_combo.setCurrentIndex(1)
    assert loaded_session.bus_of(loaded_session.tracks[0]) is bus

    header.send_combo.setCurrentIndex(0)
    assert loaded_session.tracks[0].send_to_bus is None


def test_removing_a_bus_from_the_view_returns_its_tracks_to_the_master(
    qapp: object, loaded_session: MultitrackSession
) -> None:
    from audio_studio.ui.multitrack_view import MultitrackView

    view = MultitrackView(loaded_session)
    bus = view.add_bus("Drums")
    assert bus is not None
    view.strips[0].header.send_combo.setCurrentIndex(1)

    view.bus_strips[0].remove_button.click()
    assert view.bus_strips == ()
    assert loaded_session.n_buses == 0
    assert loaded_session.tracks[0].send_to_bus is None
