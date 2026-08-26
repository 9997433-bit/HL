"""Multitrack session: summing, routing, clip alignment and the composite sources.

The mixer's contract is stricter than "sounds about right". A track nobody has
touched must pass its audio through untouched, so the arithmetic assertions
here are exact (``array_equal``, not ``allclose``) wherever the signal path is
supposed to be transparent.
"""

from __future__ import annotations

import numpy as np
import pytest

from audio_studio.core.sample_source import MemorySampleSource
from audio_studio.core.session import (
    MAX_GAIN_DB,
    SILENCE_DB,
    Clip,
    MasterBus,
    MultitrackSession,
    SessionMixer,
    Track,
    conform_channels,
    gain_to_amplitude,
    pan_gains,
)
from audio_studio.core.sources import (
    ENDLESS_FRAMES,
    ArraySource,
    LoopSource,
    RegionSource,
)
from audio_studio.core.types import AudioBuffer, TimeRange, db_to_amplitude

RATE = 48_000


def ramp(n_frames: int, *, channels: int = 2, scale: float = 1.0) -> MemorySampleSource:
    """A source whose every sample is distinguishable, so misalignment shows up."""
    data = np.arange(n_frames * channels, dtype=np.float32).reshape(n_frames, channels)
    return MemorySampleSource(AudioBuffer(data * np.float32(scale / max(n_frames, 1)), RATE))


def constant(value: float, n_frames: int, *, channels: int = 2) -> MemorySampleSource:
    data = np.full((n_frames, channels), value, dtype=np.float32)
    return MemorySampleSource(AudioBuffer(data, RATE))


@pytest.fixture()
def session() -> MultitrackSession:
    return MultitrackSession(sample_rate=RATE, n_channels=2)


# --------------------------------------------------------------- primitives


def test_gain_maps_decibels_to_amplitude_and_floors_at_silence() -> None:
    assert gain_to_amplitude(0.0) == 1.0
    assert gain_to_amplitude(-6.0) == pytest.approx(db_to_amplitude(-6.0))
    assert gain_to_amplitude(SILENCE_DB) == 0.0
    assert gain_to_amplitude(-200.0) == 0.0
    assert gain_to_amplitude(100.0) == pytest.approx(db_to_amplitude(MAX_GAIN_DB))


def test_pan_is_unity_at_the_centre_and_folds_one_side_away_at_the_extremes() -> None:
    assert pan_gains(0.0) == (1.0, 1.0)
    assert pan_gains(-1.0) == (1.0, 0.0)
    assert pan_gains(1.0) == (0.0, 1.0)
    assert pan_gains(-5.0) == pan_gains(-1.0)  # clamped, not wrapped


def test_conform_channels_spreads_mono_and_folds_wider_material() -> None:
    mono = np.array([[1.0], [2.0]], dtype=np.float32)
    assert np.array_equal(conform_channels(mono, 2), np.array([[1.0, 1.0], [2.0, 2.0]]))

    stereo = np.array([[1.0, 3.0]], dtype=np.float32)
    assert conform_channels(stereo, 1) == pytest.approx(np.array([[2.0]]))
    assert conform_channels(stereo, 2) is stereo

    # A partial match keeps what it has and leaves the extra channel silent.
    assert np.array_equal(conform_channels(stereo, 3), np.array([[1.0, 3.0, 0.0]]))


# --------------------------------------------------------------------- clips


def test_clip_from_source_covers_the_whole_source() -> None:
    clip = Clip.from_source(ramp(100), start=25)
    assert (clip.start, clip.duration, clip.offset) == (25, 100, 0)
    assert clip.range == TimeRange(25, 125)
    assert clip.source_range == TimeRange(0, 100)


def test_clip_duration_cannot_run_past_the_end_of_its_source() -> None:
    clip = Clip.from_source(ramp(100), offset=60, duration=999)
    assert clip.duration == 40


def test_clip_renders_only_the_frames_it_covers() -> None:
    source = constant(0.5, 10)
    clip = Clip(source, start=4, duration=10)

    rendered = clip.read(0, 20, channels=2)

    assert np.array_equal(rendered[:4], np.zeros((4, 2), dtype=np.float32))
    assert np.array_equal(rendered[4:14], np.full((10, 2), 0.5, dtype=np.float32))
    assert np.array_equal(rendered[14:], np.zeros((6, 2), dtype=np.float32))


def test_clip_offset_selects_a_window_inside_the_source() -> None:
    source = ramp(64)
    clip = Clip(source, start=0, duration=16, offset=32)

    assert np.array_equal(clip.read(0, 16), source.read(32, 16))


def test_clip_reads_are_exact_across_a_partial_window() -> None:
    source = ramp(64)
    clip = Clip(source, start=100, duration=64)

    # A window that starts inside the clip must line up sample for sample.
    assert np.array_equal(clip.read(120, 20), source.read(20, 20))


def test_clip_fades_reach_zero_at_the_edges_and_unity_in_between() -> None:
    clip = Clip(constant(1.0, 100), start=0, duration=100, fade_in=10, fade_out=10)

    rendered = clip.read(0, 100)[:, 0]

    assert rendered[0] == pytest.approx(0.0)
    assert rendered[10] == pytest.approx(1.0)
    assert rendered[50] == pytest.approx(1.0)
    assert rendered[90] == pytest.approx(1.0)
    assert rendered[-1] == pytest.approx(0.1, abs=1e-6)
    assert np.all(np.diff(rendered[:11]) > 0)
    assert np.all(np.diff(rendered[-10:]) < 0)


def test_clip_fades_are_clamped_to_the_clip_length() -> None:
    clip = Clip(constant(1.0, 10), start=0, duration=10, fade_in=999, fade_out=999)
    assert clip.fade_in == 10
    assert clip.fade_out == 0


def test_clip_edits_are_non_destructive_and_return_new_records() -> None:
    original = Clip.from_source(ramp(100), start=0)

    moved = original.moved_to(500)
    louder = original.with_gain(-6.0)

    assert original.start == 0
    assert moved.start == 500
    assert moved.source is original.source
    assert louder.gain_db == -6.0
    assert original.gain_db == 0.0


def test_clip_split_preserves_the_audio_on_both_sides() -> None:
    source = ramp(100)
    clip = Clip(source, start=1_000, duration=100)

    head, tail = clip.split_at(1_040)

    assert (head.start, head.duration) == (1_000, 40)
    assert (tail.start, tail.duration, tail.offset) == (1_040, 60, 40)
    assert head.clip_id != tail.clip_id
    rejoined = np.concatenate([head.read(1_000, 40), tail.read(1_040, 60)])
    assert np.array_equal(rejoined, source.read(0, 100))


def test_clip_trim_from_the_head_keeps_the_audio_where_it_was() -> None:
    source = ramp(100)
    clip = Clip(source, start=200, duration=100)

    trimmed = clip.trimmed_head(30)

    assert (trimmed.start, trimmed.duration, trimmed.offset) == (230, 70, 30)
    assert np.array_equal(trimmed.read(230, 70), clip.read(230, 70))


def test_clip_split_outside_the_clip_is_rejected() -> None:
    clip = Clip(ramp(10), start=0, duration=10)
    with pytest.raises(ValueError, match="outside"):
        clip.split_at(50)


# -------------------------------------------------------------------- tracks


def test_track_sums_overlapping_clips(session: MultitrackSession) -> None:
    track = session.add_track("Layers")
    session.add_clip(track, constant(0.25, 100), start=0)
    session.add_clip(track, constant(0.25, 100), start=50)

    rendered = track.render(0, 150, 2)

    assert rendered[0, 0] == pytest.approx(0.25)
    assert rendered[75, 0] == pytest.approx(0.5)  # both clips sound here
    assert rendered[120, 0] == pytest.approx(0.25)


def test_track_length_is_where_its_last_clip_ends(session: MultitrackSession) -> None:
    track = session.add_track()
    session.add_clip(track, ramp(100), start=0)
    session.add_clip(track, ramp(100), start=900)

    assert track.n_frames == 1_000


def test_track_keeps_its_clips_in_timeline_order(session: MultitrackSession) -> None:
    track = session.add_track()
    session.add_clip(track, ramp(10), start=500)
    session.add_clip(track, ramp(10), start=100)

    assert [clip.start for clip in track.clips] == [100, 500]


def test_track_clips_property_cannot_be_mutated_behind_the_model(
    session: MultitrackSession,
) -> None:
    track = session.add_track()
    session.add_clip(track, ramp(10), start=0)

    clips = track.clips
    assert isinstance(clips, tuple)
    assert track.n_clips == 1


def test_track_fader_is_a_no_op_at_unity_and_centre() -> None:
    track = Track(name="Flat")
    block = np.array([[0.1, -0.2], [0.3, 0.4]], dtype=np.float32)
    original = block.copy()

    track.apply_fader(block)

    assert np.array_equal(block, original)


def test_track_gain_and_pan_scale_the_channels_independently() -> None:
    track = Track(name="Panned", gain_db=-6.0, pan=-1.0)
    block = np.ones((4, 2), dtype=np.float32)

    track.apply_fader(block)

    assert np.allclose(block[:, 0], db_to_amplitude(-6.0))
    assert np.all(block[:, 1] == 0.0)


def test_track_attribute_changes_are_clamped() -> None:
    track = Track()
    track.pan = 9.0
    track.gain_db = 999.0
    assert track.pan == 1.0
    assert track.gain_db == MAX_GAIN_DB


def test_track_replace_clip_swaps_an_edited_record(session: MultitrackSession) -> None:
    track = session.add_track()
    clip = session.add_clip(track, ramp(100), start=0)

    track.replace_clip(clip.moved_to(400))

    assert track.n_clips == 1
    assert track.clips[0].start == 400
    assert track.clips[0].clip_id == clip.clip_id


def test_track_clip_at_finds_the_covering_clip(session: MultitrackSession) -> None:
    track = session.add_track()
    first = session.add_clip(track, ramp(100), start=0)
    second = session.add_clip(track, ramp(100), start=200)

    assert track.clip_at(50) is first
    assert track.clip_at(250) is second
    assert track.clip_at(150) is None


# ------------------------------------------------------------------- summing


def test_two_tracks_sum_sample_for_sample(session: MultitrackSession) -> None:
    left = session.add_track("A")
    right = session.add_track("B")
    a, b = ramp(256), constant(0.1, 256)
    session.add_clip(left, a, start=0)
    session.add_clip(right, b, start=0)

    mixed = session.read(0, 256)

    assert np.array_equal(mixed, a.read(0, 256) + b.read(0, 256))


def test_a_single_untouched_track_mixes_down_bit_identically(
    session: MultitrackSession,
) -> None:
    source = ramp(1_024)
    session.add_clip(session.add_track("Solo lane"), source, start=0)

    assert np.array_equal(session.mixdown().data, source.read(0, 1_024))


def test_opposite_polarity_tracks_null_exactly(session: MultitrackSession) -> None:
    data = np.random.default_rng(7).standard_normal((2_048, 2)).astype(np.float32) * 0.25
    session.add_clip(session.add_track("A"), MemorySampleSource(AudioBuffer(data, RATE)), start=0)
    session.add_clip(session.add_track("B"), MemorySampleSource(AudioBuffer(-data, RATE)), start=0)

    mixed = session.read(0, 2_048)

    assert np.count_nonzero(mixed) == 0


def test_a_null_test_survives_being_read_in_blocks(session: MultitrackSession) -> None:
    data = np.random.default_rng(11).standard_normal((1_000, 2)).astype(np.float32) * 0.3
    session.add_clip(session.add_track("A"), MemorySampleSource(AudioBuffer(data, RATE)), start=0)
    session.add_clip(
        session.add_track("B"), MemorySampleSource(AudioBuffer(-data, RATE)), start=0
    )

    blocks = [session.read(start, 128) for start in range(0, 1_000, 128)]

    assert np.count_nonzero(np.concatenate(blocks)) == 0


def test_gain_offset_of_plus_and_minus_six_db_nulls_to_within_float_epsilon(
    session: MultitrackSession,
) -> None:
    data = np.random.default_rng(3).standard_normal((512, 2)).astype(np.float32) * 0.2
    positive = session.add_track("A")
    negative = session.add_track("B")
    session.add_clip(positive, MemorySampleSource(AudioBuffer(data, RATE)), start=0)
    session.add_clip(negative, MemorySampleSource(AudioBuffer(-data, RATE)), start=0)
    positive.gain_db = -6.0
    negative.gain_db = -6.0

    assert np.max(np.abs(session.read(0, 512))) < 1e-7


def test_clips_are_aligned_to_the_frame_they_were_placed_on(
    session: MultitrackSession,
) -> None:
    track = session.add_track()
    source = ramp(64)
    session.add_clip(track, source, start=1_000)

    mixed = session.read(0, 1_100)

    assert np.count_nonzero(mixed[:1_000]) == 0
    assert np.array_equal(mixed[1_000:1_064], source.read(0, 64))
    assert np.count_nonzero(mixed[1_064:]) == 0


def test_clips_on_different_tracks_line_up_at_the_same_timeline_frame(
    session: MultitrackSession,
) -> None:
    early = session.add_track("Early")
    late = session.add_track("Late")
    session.add_clip(early, constant(0.5, 100), start=100)
    session.add_clip(late, constant(0.5, 100), start=150)
    session.add_clip(session.add_track("Tail"), constant(0.0, 1), start=299)

    mixed = session.read(0, 300)[:, 0]

    assert mixed[99] == pytest.approx(0.0)
    assert mixed[100] == pytest.approx(0.5)
    assert mixed[150] == pytest.approx(1.0)  # the overlap
    assert mixed[199] == pytest.approx(1.0)
    assert mixed[200] == pytest.approx(0.5)
    assert mixed[250] == pytest.approx(0.0)


def test_a_read_that_straddles_a_clip_boundary_is_still_aligned(
    session: MultitrackSession,
) -> None:
    track = session.add_track()
    source = ramp(200)
    session.add_clip(track, source, start=500)

    straddling = session.read(450, 100)

    assert np.count_nonzero(straddling[:50]) == 0
    assert np.array_equal(straddling[50:], source.read(0, 50))


def test_mono_clips_spread_across_a_stereo_session(session: MultitrackSession) -> None:
    track = session.add_track()
    session.add_clip(track, constant(0.4, 32, channels=1), start=0)

    mixed = session.read(0, 32)

    assert mixed.shape == (32, 2)
    assert np.allclose(mixed[:, 0], mixed[:, 1])
    assert mixed[0, 0] == pytest.approx(0.4)


def test_reading_past_the_end_of_the_session_is_clamped(session: MultitrackSession) -> None:
    session.add_clip(session.add_track(), ramp(100), start=0)

    assert session.read(0, 10_000).shape == (100, 2)
    assert session.read(500, 100).shape == (0, 2)


def test_an_empty_session_reads_as_nothing(session: MultitrackSession) -> None:
    assert session.n_frames == 0
    assert session.read(0, 512).shape == (0, 2)
    assert session.mixdown().n_frames == 0


# ------------------------------------------------------------- mute and solo


def test_muting_a_track_removes_it_from_the_mix(session: MultitrackSession) -> None:
    kept = session.add_track("Kept")
    dropped = session.add_track("Dropped")
    source = constant(0.3, 64)
    session.add_clip(kept, source, start=0)
    session.add_clip(dropped, source, start=0)

    dropped.mute = True

    assert np.array_equal(session.read(0, 64), source.read(0, 64))


def test_soloing_a_track_silences_every_other_lane(session: MultitrackSession) -> None:
    first = session.add_track("First")
    second = session.add_track("Second")
    session.add_clip(first, constant(0.3, 64), start=0)
    session.add_clip(second, constant(0.7, 64), start=0)

    second.solo = True

    assert session.solo_active is True
    assert session.audible_tracks() == (second,)
    assert session.read(0, 64)[0, 0] == pytest.approx(0.7)


def test_several_solos_all_stay_audible(session: MultitrackSession) -> None:
    a, b, c = (session.add_track(name) for name in ("A", "B", "C"))
    for track in (a, b, c):
        session.add_clip(track, constant(0.1, 32), start=0)

    a.solo = True
    c.solo = True

    assert session.audible_tracks() == (a, c)
    assert session.read(0, 32)[0, 0] == pytest.approx(0.2)


def test_mute_beats_solo_on_the_same_track(session: MultitrackSession) -> None:
    track = session.add_track("Contradictory")
    other = session.add_track("Other")
    session.add_clip(track, constant(0.5, 32), start=0)
    session.add_clip(other, constant(0.5, 32), start=0)

    track.mute = True
    track.solo = True

    assert session.audible_tracks() == ()
    assert np.count_nonzero(session.read(0, 32)) == 0


def test_clearing_solo_brings_the_other_tracks_back(session: MultitrackSession) -> None:
    first = session.add_track("First")
    second = session.add_track("Second")
    session.add_clip(first, constant(0.25, 32), start=0)
    session.add_clip(second, constant(0.25, 32), start=0)

    second.solo = True
    second.solo = False

    assert session.solo_active is False
    assert session.read(0, 32)[0, 0] == pytest.approx(0.5)


def test_a_track_at_the_silence_floor_contributes_nothing(
    session: MultitrackSession,
) -> None:
    track = session.add_track()
    session.add_clip(track, constant(1.0, 32), start=0)

    track.gain_db = SILENCE_DB

    assert np.count_nonzero(session.read(0, 32)) == 0


# --------------------------------------------------------------- master bus


def test_the_master_fader_scales_the_finished_mix(session: MultitrackSession) -> None:
    session.add_clip(session.add_track(), constant(0.5, 32), start=0)

    session.master.gain_db = -6.0

    assert session.read(0, 32)[0, 0] == pytest.approx(0.5 * db_to_amplitude(-6.0))


def test_muting_the_master_silences_everything(session: MultitrackSession) -> None:
    session.add_clip(session.add_track(), constant(0.9, 32), start=0)

    session.master.mute = True

    assert np.count_nonzero(session.read(0, 32)) == 0


def test_the_master_bus_applies_in_place() -> None:
    bus = MasterBus(gain_db=-6.0)
    block = np.ones((4, 2), dtype=np.float32)

    returned = bus.apply(block)

    assert returned is block
    assert np.allclose(block, db_to_amplitude(-6.0))


# ------------------------------------------------------- session bookkeeping


def test_tracks_get_unique_ids_and_default_names(session: MultitrackSession) -> None:
    first = session.add_track()
    second = session.add_track()

    assert first.track_id != second.track_id
    assert first.id == first.track_id
    assert first.name == first.track_id


def test_a_duplicate_track_id_is_rejected(session: MultitrackSession) -> None:
    session.add_track(Track("trk_x"))
    with pytest.raises(ValueError, match="duplicate track id"):
        session.add_track(Track("trk_x"))


def test_removing_a_track_takes_it_out_of_the_mix(session: MultitrackSession) -> None:
    keep = session.add_track("Keep")
    drop = session.add_track("Drop")
    session.add_clip(keep, constant(0.2, 32), start=0)
    session.add_clip(drop, constant(0.2, 32), start=0)

    assert session.remove_track(drop) is True
    assert session.remove_track(drop) is False
    assert session.n_tracks == 1
    assert session.read(0, 32)[0, 0] == pytest.approx(0.2)


def test_a_removed_track_no_longer_invalidates_the_session(
    session: MultitrackSession,
) -> None:
    track = session.add_track()
    session.remove_track(track)
    revision = session.revision

    track.gain_db = -12.0

    assert session.revision == revision


def test_move_track_reorders_the_lanes(session: MultitrackSession) -> None:
    a, b, c = (session.add_track(name) for name in ("A", "B", "C"))

    session.move_track(c, 0)

    assert [track.name for track in session.tracks] == ["C", "A", "B"]
    assert (a, b) == (session.track(a.track_id), session.track(b.track_id))


def test_every_change_bumps_the_revision(session: MultitrackSession) -> None:
    seen: list[int] = []
    session.add_listener(lambda sess: seen.append(sess.revision))

    track = session.add_track()
    session.add_clip(track, ramp(32), start=0)
    track.mute = True
    track.gain_db = -3.0
    session.master.gain_db = -1.0

    assert len(seen) == 5
    assert seen == sorted(set(seen))


def test_setting_an_unchanged_value_does_not_bump_the_revision(
    session: MultitrackSession,
) -> None:
    track = session.add_track()
    revision = session.revision

    track.mute = False
    track.gain_db = 0.0
    track.pan = 0.0

    assert session.revision == revision


def test_a_removed_listener_stops_hearing_about_changes(
    session: MultitrackSession,
) -> None:
    seen: list[int] = []

    def listener(_session: MultitrackSession) -> None:
        seen.append(1)

    session.add_listener(listener)
    session.add_track()
    session.remove_listener(listener)
    session.add_track()

    assert len(seen) == 1


def test_a_clip_at_the_wrong_sample_rate_is_refused(session: MultitrackSession) -> None:
    track = session.add_track()
    wrong = MemorySampleSource(AudioBuffer(np.zeros((10, 2), dtype=np.float32), 8_000))

    with pytest.raises(ValueError, match="Hz"):
        session.add_clip(track, wrong, start=0)


def test_adding_a_clip_to_a_foreign_track_is_refused(session: MultitrackSession) -> None:
    with pytest.raises(KeyError):
        session.add_clip(Track("trk_elsewhere"), ramp(10), start=0)
    with pytest.raises(KeyError):
        session.add_clip("trk_missing", ramp(10), start=0)


def test_the_session_format_is_locked_once_clips_exist(session: MultitrackSession) -> None:
    session.set_format(96_000, 1)
    assert (session.sample_rate, session.n_channels) == (96_000, 1)

    session.add_clip(
        session.add_track(),
        MemorySampleSource(AudioBuffer(np.zeros((8, 1), dtype=np.float32), 96_000)),
        start=0,
    )
    with pytest.raises(ValueError, match="once clips have been placed"):
        session.set_format(RATE, 2)


def test_an_invalid_session_format_is_rejected() -> None:
    with pytest.raises(ValueError, match="sample_rate"):
        MultitrackSession(sample_rate=0)
    with pytest.raises(ValueError, match="n_channels"):
        MultitrackSession(n_channels=0)


def test_the_session_reports_its_length_in_frames_and_seconds(
    session: MultitrackSession,
) -> None:
    session.add_clip(session.add_track(), ramp(RATE), start=RATE // 2)

    assert session.n_frames == RATE + RATE // 2
    assert session.duration == pytest.approx(1.5)
    assert session.range == TimeRange(0, session.n_frames)


# --------------------------------------------------------------- the mixer


def test_the_mixer_satisfies_the_sample_source_protocol(session: MultitrackSession) -> None:
    from audio_studio.core.sample_source import SampleSource

    session.add_clip(session.add_track(), ramp(128), start=0)

    assert isinstance(session.mixer, SampleSource)
    assert isinstance(session, SampleSource)
    assert session.mixer.sample_rate == RATE
    assert session.mixer.n_channels == 2
    assert session.mixer.n_frames == 128


def test_the_engine_can_play_a_session_through_the_mixer(session: MultitrackSession) -> None:
    from audio_studio.core.engine import AudioEngine
    from audio_studio.core.output import NullOutput

    source = constant(0.5, 4_096)
    session.add_clip(session.add_track("Bed"), source, start=0)

    engine = AudioEngine(NullOutput(realtime=False), block_size=256, ring_blocks=8)
    try:
        engine.set_source(session.mixer)
        assert engine.n_frames == 4_096
        assert engine.sample_rate == RATE
        engine.play()
        engine.output.pump(256)
        rendered = engine.render(256)
    finally:
        engine.shutdown()

    assert rendered.shape == (256, 2)
    assert np.max(np.abs(rendered)) == pytest.approx(0.5)


def test_the_mixer_reaches_the_device_through_the_effect_preview_insert(
    session: MultitrackSession,
) -> None:
    from audio_studio.core.engine import AudioEngine
    from audio_studio.core.output import NullOutput
    from audio_studio.dsp.effects import EffectChain, GainEffect
    from audio_studio.dsp.preview import EffectPreview

    session.add_clip(session.add_track("Bed"), constant(0.5, 8_192), start=0)

    chain = EffectChain([GainEffect(gain_db=-6.0)])
    preview = EffectPreview(NullOutput(realtime=False), chain)
    engine = AudioEngine(preview, block_size=256, ring_blocks=8)
    try:
        engine.set_source(session.mixer)
        engine.play()
        preview.output.pump(256)
        rendered = preview.render(256)
    finally:
        engine.shutdown()

    assert preview.processed_blocks > 0
    assert np.max(np.abs(rendered)) == pytest.approx(0.5 * db_to_amplitude(-6.0), rel=1e-3)


def test_render_tracks_returns_one_post_fader_stem_per_track(
    session: MultitrackSession,
) -> None:
    quiet = session.add_track("Quiet")
    loud = session.add_track("Loud")
    session.add_clip(quiet, constant(0.5, 64), start=0)
    session.add_clip(loud, constant(0.5, 64), start=0)
    quiet.gain_db = -6.0

    stems = session.render_tracks(0, 64)

    assert set(stems) == {quiet.track_id, loud.track_id}
    assert stems[quiet.track_id][0, 0] == pytest.approx(0.5 * db_to_amplitude(-6.0))
    assert stems[loud.track_id][0, 0] == pytest.approx(0.5)


def test_stems_sum_to_the_mix_when_nothing_is_muted(session: MultitrackSession) -> None:
    for level in (0.1, 0.2, 0.3):
        session.add_clip(session.add_track(), constant(level, 64), start=0)

    stems = session.render_tracks(0, 64)
    summed = sum(stems.values())

    assert np.allclose(summed, session.read(0, 64))


def test_mixdown_of_a_range_matches_a_direct_read(session: MultitrackSession) -> None:
    session.add_clip(session.add_track(), ramp(500), start=0)

    span = TimeRange(100, 300)
    buffer = session.mixdown(span)

    assert isinstance(buffer, AudioBuffer)
    assert buffer.sample_rate == RATE
    assert np.array_equal(buffer.data, session.read(100, 200))


def test_a_dedicated_mixer_instance_sees_the_same_session(
    session: MultitrackSession,
) -> None:
    session.add_clip(session.add_track(), ramp(64), start=0)
    mixer = SessionMixer(session)

    assert mixer.session is session
    assert np.array_equal(mixer.read(0, 64), session.read(0, 64))


def test_a_session_with_1024_frames_over_32_tracks_still_sums_correctly() -> None:
    session = MultitrackSession(sample_rate=RATE, n_channels=2)
    for _ in range(32):
        session.add_clip(session.add_track(), constant(0.01, 1_024), start=0)

    mixed = session.read(0, 1_024)

    assert mixed[0, 0] == pytest.approx(0.32, rel=1e-4)


# ---------------------------------------------------- composite sample sources


def test_region_source_rebases_the_window_to_frame_zero() -> None:
    inner = ramp(1_000)
    region = RegionSource(inner, TimeRange(200, 300))

    assert region.n_frames == 100
    assert region.sample_rate == inner.sample_rate
    assert region.n_channels == inner.n_channels
    assert np.array_equal(region.read(0, 100), inner.read(200, 100))
    assert np.array_equal(region.read(10, 20), inner.read(210, 20))


def test_region_source_clamps_a_window_that_runs_off_the_end() -> None:
    inner = ramp(100)
    region = RegionSource(inner, TimeRange(80, 500))

    assert region.region == TimeRange(80, 100)
    assert region.n_frames == 20
    assert region.read(0, 999).shape[0] == 20


def test_region_source_defaults_to_the_whole_inner_source() -> None:
    inner = ramp(64)
    region = RegionSource(inner)

    assert region.n_frames == 64
    assert np.array_equal(region.read(0, 64), inner.read(0, 64))
    assert region.to_timeline(5) == 5


def test_region_source_maps_frames_back_onto_the_inner_timeline() -> None:
    region = RegionSource(ramp(1_000), TimeRange(400, 600))
    assert region.to_timeline(0) == 400
    assert region.to_timeline(50) == 450


def test_region_source_only_closes_what_it_owns() -> None:
    class Closable(MemorySampleSource):
        closed = False

        def close(self) -> None:
            self.closed = True

    borrowed = Closable(AudioBuffer(np.zeros((8, 1), dtype=np.float32), RATE))
    RegionSource(borrowed).close()
    assert borrowed.closed is False

    owned = Closable(AudioBuffer(np.zeros((8, 1), dtype=np.float32), RATE))
    RegionSource(owned, owns_inner=True).close()
    assert owned.closed is True


def test_loop_source_wraps_at_the_seam() -> None:
    inner = ramp(10)
    loop = LoopSource(inner, repeats=3)

    assert loop.n_frames == 30
    assert loop.cycle_frames == 10
    assert np.array_equal(loop.read(0, 30), np.tile(inner.read(0, 10), (3, 1)))


def test_a_loop_read_that_straddles_the_seam_is_stitched_not_truncated() -> None:
    inner = ramp(10)
    loop = LoopSource(inner, repeats=4)

    block = loop.read(8, 6)

    assert block.shape[0] == 6
    expected = np.concatenate([inner.read(8, 2), inner.read(0, 4)])
    assert np.array_equal(block, expected)


def test_an_endless_loop_reports_a_practically_infinite_length() -> None:
    loop = LoopSource(ramp(10))

    assert loop.is_endless is True
    assert loop.repeats is None
    assert loop.n_frames == ENDLESS_FRAMES
    assert np.array_equal(loop.read(1_000_003, 4), ramp(10).read(3, 4))


def test_an_endless_loop_over_an_empty_source_is_empty() -> None:
    empty = MemorySampleSource(AudioBuffer(np.zeros((0, 2), dtype=np.float32), RATE))
    loop = LoopSource(empty)

    assert loop.n_frames == 0
    assert loop.read(0, 128).shape == (0, 2)


def test_a_loop_of_zero_passes_is_rejected() -> None:
    with pytest.raises(ValueError, match="repeats"):
        LoopSource(ramp(10), repeats=0)


def test_region_and_loop_compose_into_a_looped_selection() -> None:
    inner = ramp(100)
    chorus = LoopSource(RegionSource(inner, TimeRange(40, 50)), repeats=3)

    assert chorus.n_frames == 30
    assert np.array_equal(chorus.read(0, 30), np.tile(inner.read(40, 10), (3, 1)))


def test_a_looped_region_can_be_placed_on_a_track(session: MultitrackSession) -> None:
    inner = constant(0.5, 100)
    track = session.add_track("Looped")
    session.add_clip(track, LoopSource(RegionSource(inner, TimeRange(0, 25)), repeats=8), start=0)

    assert track.n_frames == 200
    assert np.allclose(session.read(0, 200), 0.5)


def test_the_spec_facing_aliases_are_the_same_objects() -> None:
    from audio_studio.core.edit_session import EditSession
    from audio_studio.core.sample_source import StreamingSampleSource
    from audio_studio.core.sources import ChunkTableSource, FileStreamSource

    assert ArraySource is MemorySampleSource
    assert FileStreamSource is StreamingSampleSource
    assert ChunkTableSource is EditSession


def test_an_edit_session_can_be_placed_on_a_track(session: MultitrackSession) -> None:
    from audio_studio.core.edit_session import EditSession

    data = np.linspace(-0.5, 0.5, 200, dtype=np.float32)[:, np.newaxis].repeat(2, axis=1)
    document = EditSession.from_array(data, RATE)
    track = session.add_track("Edited")
    session.add_clip(track, document, start=50)

    assert np.array_equal(session.read(50, 200), data)

    document.silence(TimeRange(0, 200))

    # The clip holds a live reference, so the edit is audible without re-adding it.
    assert np.count_nonzero(session.read(50, 200)) == 0


def test_the_core_package_exports_the_session_vocabulary() -> None:
    import audio_studio.core as core

    for name in ("MultitrackSession", "SessionMixer", "Track", "Clip", "MasterBus"):
        assert name in core.__all__
        assert getattr(core, name) is not None
    assert core.RegionSource is RegionSource
    assert core.LoopSource is LoopSource


# ------------------------------------------------------------------ the view


@pytest.fixture()
def qt_session() -> MultitrackSession:
    """A two-track arrangement the widget tests can draw."""
    session = MultitrackSession(sample_rate=RATE, n_channels=2)
    tone = np.sin(np.arange(RATE, dtype=np.float32) / 40.0)[:, np.newaxis].repeat(2, axis=1)
    session.add_clip(
        session.add_track("Vox"), MemorySampleSource(AudioBuffer(tone * 0.6, RATE)), start=0
    )
    session.add_clip(
        session.add_track("Guitar"),
        MemorySampleSource(AudioBuffer(tone * 0.3, RATE)),
        start=RATE // 2,
    )
    return session


@pytest.fixture()
def view(qapp: object, qt_session: MultitrackSession):  # noqa: ANN201 - Qt widget
    from audio_studio.ui.multitrack_view import MultitrackView

    widget = MultitrackView(qt_session)
    widget.resize(900, 400)
    yield widget
    widget.close()


def test_the_view_builds_one_strip_per_track(view, qt_session) -> None:  # noqa: ANN001
    assert len(view.strips) == qt_session.n_tracks
    assert [strip.track.name for strip in view.strips] == ["Vox", "Guitar"]
    assert view.n_frames == qt_session.n_frames


def test_the_view_starts_fitted_to_the_session(view, qt_session) -> None:  # noqa: ANN001
    assert view.view_start == 0
    assert view.view_frames == qt_session.n_frames


def test_every_lane_shares_one_timeline(view) -> None:  # noqa: ANN001
    view.set_view(1_000, 20_000)

    for strip in view.strips:
        assert strip.lane.frame_to_x(1_000) == pytest.approx(0.0)
        assert strip.lane.x_to_frame(0) == 1_000
    assert view.ruler.frame_to_x(1_000) == pytest.approx(0.0)


def test_a_clip_lands_on_the_pixel_its_start_frame_maps_to(view, qt_session) -> None:  # noqa: ANN001
    lane = view.strips[1].lane
    clip = qt_session.tracks[1].clips[0]

    expected = lane.frame_to_x(clip.start)

    assert 0 < expected < lane.width()
    assert lane.x_to_frame(expected) == pytest.approx(clip.start, abs=view.view_frames / 900 + 1)


def test_zoom_keeps_the_anchor_frame_under_the_same_pixel(view) -> None:  # noqa: ANN001
    anchor = view.n_frames // 2
    before = view.strips[0].lane.frame_to_x(anchor)

    view.zoom_by(0.25, anchor)

    assert view.view_frames == pytest.approx(view.n_frames * 0.25, rel=0.05)
    assert view.strips[0].lane.frame_to_x(anchor) == pytest.approx(before, abs=2.0)


def test_the_view_scrollbar_follows_the_visible_span(view) -> None:  # noqa: ANN001
    view.set_view(0, view.n_frames // 4)

    assert view.scrollbar.isEnabled()
    assert view.scrollbar.maximum() == view.n_frames - view.view_frames

    view.scrollbar.setValue(1_234)

    assert view.view_start == 1_234


def test_the_header_controls_write_back_to_the_model(view, qt_session) -> None:  # noqa: ANN001
    header = view.strips[0].header

    header.mute_button.setChecked(True)
    header.gain_slider.setValue(-9)
    header.pan_slider.setValue(-50)

    track = qt_session.tracks[0]
    assert track.mute is True
    assert track.gain_db == pytest.approx(-9.0)
    assert track.pan == pytest.approx(-0.5)
    assert "-9.0 dB" in header.gain_label.text()
    assert header.pan_label.text() == "L50"


def test_solo_from_the_header_changes_what_the_mixer_renders(view, qt_session) -> None:  # noqa: ANN001
    view.strips[1].header.solo_button.setChecked(True)

    assert qt_session.solo_active is True
    assert qt_session.audible_tracks() == (qt_session.tracks[1],)


def test_a_model_change_is_reflected_back_into_the_header(view, qt_session) -> None:  # noqa: ANN001
    qt_session.tracks[0].gain_db = -12.0
    qt_session.tracks[0].mute = True

    header = view.strips[0].header
    assert header.gain_slider.value() == -12
    assert header.mute_button.isChecked() is True


def test_syncing_the_header_does_not_write_back_to_the_model(view, qt_session) -> None:  # noqa: ANN001
    track = qt_session.tracks[0]
    track.gain_db = -3.5
    revision = qt_session.revision

    view.refresh()

    # The slider rounds to -4 dB, but refreshing must not commit that rounding.
    assert track.gain_db == pytest.approx(-3.5)
    assert qt_session.revision == revision


def test_adding_a_track_rebuilds_the_strips(view, qt_session) -> None:  # noqa: ANN001
    qt_session.add_track("Bass")

    assert len(view.strips) == 3
    assert view.strips[-1].track.name == "Bass"


def test_removing_a_track_rebuilds_the_strips(view, qt_session) -> None:  # noqa: ANN001
    qt_session.remove_track(qt_session.tracks[0])

    assert len(view.strips) == 1
    assert view.strips[0].track.name == "Guitar"


def test_the_master_strip_edits_the_master_bus(view, qt_session) -> None:  # noqa: ANN001
    view.master_strip.gain_slider.setValue(-4)
    view.master_strip.mute_button.setChecked(True)

    assert qt_session.master.gain_db == pytest.approx(-4.0)
    assert qt_session.master.mute is True
    assert "2 tracks" in view.master_strip.summary.text()


def test_the_view_paints_without_a_session(qapp: object) -> None:
    from audio_studio.ui.multitrack_view import MultitrackView

    empty = MultitrackView()
    empty.resize(600, 200)
    try:
        assert empty.strips == ()
        assert empty.n_frames == 0
        assert empty.placeholder.isVisibleTo(empty)
        empty.grab()  # must not raise
    finally:
        empty.close()


def test_the_lanes_render_their_clips(view) -> None:  # noqa: ANN001
    view.set_playhead(view.n_frames // 3)
    image = view.grab().toImage()

    assert image.width() == 900
    # A rendered arrangement is not a flat field of background pixels.
    colours = {image.pixel(x, y) for x in range(0, 900, 37) for y in range(0, 400, 13)}
    assert len(colours) > 3


def test_a_lane_caches_its_strip_until_something_changes(view, qt_session) -> None:  # noqa: ANN001
    lane = view.strips[0].lane
    view.grab()
    cached = lane._cache  # noqa: SLF001 - the cache is the thing under test
    assert cached is not None

    lane.set_playhead(500)
    view.grab()
    assert lane._cache is cached  # noqa: SLF001 - a playhead move is an overlay

    lane.set_revision(qt_session.revision + 1)
    view.grab()
    assert lane._cache is not cached  # noqa: SLF001


def test_clicking_a_lane_asks_for_a_seek(view) -> None:  # noqa: ANN001
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent

    seen: list[int] = []
    view.seekRequested.connect(seen.append)
    lane = view.strips[0].lane
    lane.resize(700, 76)

    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(350.0, 30.0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    lane.mousePressEvent(event)

    assert seen == [lane.x_to_frame(350.0)]


def test_a_long_clip_is_drawn_as_a_block_rather_than_summarised(qapp: object) -> None:
    from audio_studio.ui.multitrack_view import MAX_SUMMARY_FRAMES, ClipLane

    class HugeSource(MemorySampleSource):
        @property
        def n_frames(self) -> int:
            return MAX_SUMMARY_FRAMES + 1

    session = MultitrackSession(sample_rate=RATE, n_channels=2)
    track = session.add_track("Long")
    huge = HugeSource(AudioBuffer(np.zeros((16, 2), dtype=np.float32), RATE))
    track.add_clip(Clip(huge, start=0, duration=1_000))

    lane = ClipLane(track)
    lane.resize(400, 76)
    lane.set_view(0, 1_000)
    try:
        lane.grab()  # must not try to read a two-minute source
        assert lane._summary(track.clips[0]) is None  # noqa: SLF001
    finally:
        lane.close()


# ------------------------------------------------------ main window workspace


@pytest.fixture()
def window(qapp: object, tmp_path):  # noqa: ANN001, ANN201 - Qt widget
    from audio_studio.core.engine import AudioEngine
    from audio_studio.core.loader import LoadedAudio
    from audio_studio.core.output import NullOutput
    from audio_studio.core.types import AudioFormat
    from audio_studio.ui.main_window import MainWindow

    tone = np.sin(np.arange(RATE // 2, dtype=np.float32) / 30.0)[:, np.newaxis].repeat(2, axis=1)
    clip = LoadedAudio(
        buffer=AudioBuffer(tone * 0.4, RATE),
        audio_format=AudioFormat(RATE, 2, "PCM_16", "WAV"),
        path=tmp_path / "tone.wav",
    )
    engine = AudioEngine(NullOutput(realtime=False), block_size=256)
    main = MainWindow(engine)
    main.resize(1200, 700)
    engine.set_clip(clip)
    main._update_for_clip()  # noqa: SLF001 - normally triggered by open_file()
    yield main
    main.close()


def test_the_window_starts_in_the_waveform_workspace(window) -> None:  # noqa: ANN001
    assert window.workspace == "waveform"
    assert window.action_multitrack.isChecked() is False
    assert window.multitrack_view.isVisibleTo(window) is False
    assert window.waveform_page.isVisibleTo(window) is True


def test_the_menu_action_switches_to_the_multitrack_workspace(window) -> None:  # noqa: ANN001
    window.action_multitrack.trigger()

    assert window.workspace == "multitrack"
    assert window.multitrack_view.isVisibleTo(window) is True
    assert window.waveform_page.isVisibleTo(window) is False

    window.action_multitrack.trigger()

    assert window.workspace == "waveform"
    assert window.waveform_page.isVisibleTo(window) is True


def test_an_unknown_workspace_is_rejected(window) -> None:  # noqa: ANN001
    with pytest.raises(ValueError, match="unknown workspace"):
        window.set_workspace("mixer")


def test_entering_multitrack_seeds_the_session_from_the_loaded_clip(window) -> None:  # noqa: ANN001
    window.set_workspace("multitrack")

    assert window.session.n_tracks == 1
    assert window.session.sample_rate == RATE
    assert window.session.n_frames == RATE // 2
    assert len(window.multitrack_view.strips) == 1


def test_the_transport_follows_the_visible_workspace(window) -> None:  # noqa: ANN001
    window.set_workspace("multitrack")

    assert window.is_playing_session is True
    assert window.engine.source is window.session.mixer
    assert window.engine.n_frames == window.session.n_frames

    window.set_workspace("waveform")

    assert window.is_playing_session is False
    assert window.engine.clip is not None
    assert window.engine.n_frames == RATE // 2


def test_the_session_mix_is_what_the_transport_renders(window) -> None:  # noqa: ANN001
    window.set_workspace("multitrack")
    window.session.tracks[0].gain_db = -6.0

    engine = window.engine
    engine.seek(0)
    engine.play()
    engine.output.pump(256)
    rendered = engine.render(256)
    engine.stop()

    expected = window.session.read(0, 256)
    assert np.max(np.abs(rendered)) == pytest.approx(np.max(np.abs(expected)), rel=1e-4)


def test_adding_a_second_track_extends_the_session(window) -> None:  # noqa: ANN001
    window.set_workspace("multitrack")

    added = window.add_clip_as_track("Double")

    assert added is not None
    assert window.session.n_tracks == 2
    assert len(window.multitrack_view.strips) == 2
    # Two copies of the same clip sum to twice the level.
    assert np.max(np.abs(window.session.read(0, 512))) == pytest.approx(
        2 * np.max(np.abs(window.editor_clip.buffer.data[:512])), rel=1e-5
    )


def test_muting_a_lane_from_the_ui_changes_the_transport_output(window) -> None:  # noqa: ANN001
    window.set_workspace("multitrack")
    window.multitrack_view.strips[0].header.mute_button.setChecked(True)

    assert np.count_nonzero(window.session.read(0, 512)) == 0


def test_the_status_bar_describes_the_session_in_multitrack_mode(window) -> None:  # noqa: ANN001
    window.set_workspace("multitrack")
    assert "1 tracks" in window.status_format.text()

    window.set_workspace("waveform")
    assert "tone.wav" in window.status_format.text()


def test_switching_workspaces_with_no_clip_is_harmless(qapp: object) -> None:
    from audio_studio.core.engine import AudioEngine
    from audio_studio.core.output import NullOutput
    from audio_studio.ui.main_window import MainWindow

    main = MainWindow(AudioEngine(NullOutput(realtime=False), block_size=256))
    try:
        main.set_workspace("multitrack")
        assert main.session.n_tracks == 0
        assert main.is_playing_session is False
        assert main.add_clip_as_track() is None
        main.set_workspace("waveform")
    finally:
        main.close()


def test_the_playhead_reaches_the_multitrack_lanes(window) -> None:  # noqa: ANN001
    window.set_workspace("multitrack")

    window._on_seek(1_000)  # noqa: SLF001 - normally emitted by a lane click

    assert window.multitrack_view._playhead == 1_000  # noqa: SLF001
    assert window.engine.position == 1_000
