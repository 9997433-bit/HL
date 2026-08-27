"""Editing semantics: copy-on-write documents, reversible commands, undo/redo.

The contract these tests defend is that undoing every command in a history
returns the *exact* samples the session started with. Anything less and an
editor silently degrades a recording each time the user experiments.
"""

from __future__ import annotations

import threading

import numpy as np
import pytest

from audio_studio.core.edit_session import (
    DEFAULT_CHUNK_FRAMES,
    AudioDocument,
    Chunk,
    DeleteCommand,
    EditError,
    EditSession,
    FadeCommand,
    GainCommand,
    InsertSilenceCommand,
    ReverseCommand,
    Segment,
    SilenceCommand,
    TrimCommand,
    UndoStack,
)
from audio_studio.core.types import AudioBuffer, TimeRange, db_to_amplitude

SR = 44_100


def ramp(n_frames: int, channels: int = 2, offset: int = 0) -> np.ndarray:
    """Distinct value per (frame, channel) so a misplaced splice is unmissable."""
    values = np.arange(offset, offset + n_frames, dtype=np.float32)
    data = np.empty((n_frames, channels), dtype=np.float32)
    for ch in range(channels):
        data[:, ch] = values + ch * 0.5
    return data


@pytest.fixture()
def session() -> EditSession:
    return EditSession(AudioDocument.from_array(ramp(2_000), SR, chunk_frames=256))


# ---------------------------------------------------------------------------
# document storage
# ---------------------------------------------------------------------------


class TestDocument:
    def test_round_trips_the_samples_it_was_given(self) -> None:
        data = ramp(5_000)
        document = AudioDocument.from_array(data, SR, chunk_frames=512)

        assert document.n_frames == 5_000
        assert document.n_channels == 2
        assert document.sample_rate == SR
        assert np.array_equal(document.to_array(), data)

    def test_reads_across_chunk_boundaries(self) -> None:
        data = ramp(1_000)
        document = AudioDocument.from_array(data, SR, chunk_frames=64)

        for start, count in ((0, 1_000), (63, 2), (64, 64), (500, 400), (990, 50)):
            expected = data[start : start + count]
            assert np.array_equal(document.read(start, count), expected), (start, count)

    def test_reads_outside_the_document_are_clamped_not_raised(self) -> None:
        document = AudioDocument.from_array(ramp(100), SR)

        assert document.read(-50, 10).shape == (10, 2)  # start clamps to zero
        assert document.read(95, 100).shape == (5, 2)
        assert document.read(500, 10).shape == (0, 2)

    def test_a_document_is_immutable_through_its_chunks(self) -> None:
        document = AudioDocument.from_array(ramp(100), SR)

        with pytest.raises(ValueError, match="read-only"):
            document.segments[0].chunk.data[0, 0] = 99.0

    def test_adopting_a_buffer_does_not_alias_the_caller(self) -> None:
        """``copy=True`` (the default) is what stops a later write rewriting history."""
        data = ramp(100)
        document = AudioDocument.from_array(data, SR)

        data[:] = 0.0

        assert np.array_equal(document.to_array(), ramp(100))

    def test_a_1d_array_becomes_a_mono_document(self) -> None:
        document = AudioDocument.from_array(np.arange(64, dtype=np.float32), SR)

        assert document.n_channels == 1
        assert document.to_array().shape == (64, 1)

    def test_slicing_shares_chunks_instead_of_copying(self) -> None:
        document = AudioDocument.from_array(ramp(100_000), SR, chunk_frames=4_096)

        excerpt = document.slice(TimeRange(10_000, 90_000))

        assert np.array_equal(excerpt.to_array(), ramp(100_000)[10_000:90_000])
        shared = {id(s.chunk) for s in excerpt.segments} & {id(s.chunk) for s in document.segments}
        assert len(shared) == len(excerpt.segments)

    def test_delete_and_insert_are_inverses(self) -> None:
        data = ramp(1_000)
        document = AudioDocument.from_array(data, SR, chunk_frames=128)
        rng = TimeRange(200, 700)

        removed = document.slice(rng)
        shortened = document.delete(rng)
        restored = shortened.insert(rng.start, removed)

        assert shortened.n_frames == 500
        assert np.array_equal(restored.to_array(), data)

    def test_editing_a_range_only_rewrites_that_range(self) -> None:
        """Copy-on-write: an edit costs storage proportional to what it touched."""
        document = AudioDocument.from_array(ramp(400_000), SR, chunk_frames=4_096)

        edited = document.map_range(TimeRange(0, 4_096), np.zeros_like)

        untouched = {id(s.chunk) for s in document.segments} & {
            id(s.chunk) for s in edited.segments
        }
        assert len(untouched) >= document.n_segments - 2
        # The rewritten copy adds one chunk's worth of storage, not the whole file.
        assert edited.stored_frames() - document.stored_frames() <= 8_192

    def test_mismatched_audio_cannot_be_spliced_in(self) -> None:
        stereo = AudioDocument.from_array(ramp(100, channels=2), SR)
        mono = AudioDocument.from_array(ramp(100, channels=1), SR)
        other_rate = AudioDocument.from_array(ramp(100, channels=2), 48_000)

        with pytest.raises(EditError, match="channel"):
            stereo.insert(0, mono)
        with pytest.raises(EditError, match="Hz"):
            stereo.insert(0, other_rate)

    def test_an_in_place_edit_must_preserve_the_frame_count(self) -> None:
        document = AudioDocument.from_array(ramp(100), SR)

        with pytest.raises(EditError, match="preserve the shape"):
            document.map_range(TimeRange(0, 50), lambda block: block[:10])

    def test_a_segment_cannot_escape_its_chunk(self) -> None:
        chunk = Chunk(np.zeros((10, 1), dtype=np.float32))

        with pytest.raises(ValueError, match="past the end"):
            Segment(chunk, 5, 10)


# ---------------------------------------------------------------------------
# individual commands
# ---------------------------------------------------------------------------


class TestCommands:
    def test_delete_removes_the_range_and_undo_puts_it_back(self, session: EditSession) -> None:
        original = session.document.to_array()

        session.delete(TimeRange(500, 900))

        assert session.n_frames == 1_600
        assert np.array_equal(
            session.read(0, session.n_frames),
            np.concatenate([original[:500], original[900:]]),
        )
        assert session.undo()
        assert np.array_equal(session.read(0, session.n_frames), original)

    def test_cut_fills_the_clipboard(self, session: EditSession) -> None:
        original = session.document.to_array()

        removed = session.cut(TimeRange(100, 300))

        assert np.array_equal(removed.to_array(), original[100:300])
        assert session.clipboard is removed
        assert session.n_frames == 1_800

    def test_paste_inserts_the_clipboard_at_the_playhead(self, session: EditSession) -> None:
        original = session.document.to_array()
        session.copy(TimeRange(0, 100))

        session.paste(1_000)

        assert session.n_frames == 2_100
        assert np.array_equal(session.read(1_000, 100), original[:100])
        assert np.array_equal(session.read(1_100, 100), original[1_000:1_100])

    def test_paste_can_replace_a_selection(self, session: EditSession) -> None:
        original = session.document.to_array()
        session.copy(TimeRange(0, 100))

        session.paste(0, replacing=TimeRange(500, 900))

        assert session.n_frames == 2_000 - 400 + 100
        assert np.array_equal(session.read(500, 100), original[:100])
        assert session.undo()
        assert np.array_equal(session.read(0, session.n_frames), original)

    def test_paste_without_a_clipboard_is_refused(self, session: EditSession) -> None:
        with pytest.raises(EditError, match="clipboard"):
            session.paste(0)

    def test_silence_zeroes_the_range_and_keeps_the_length(self, session: EditSession) -> None:
        original = session.document.to_array()

        session.silence(TimeRange(400, 600))

        assert session.n_frames == 2_000
        assert np.all(session.read(400, 200) == 0.0)
        assert np.array_equal(session.read(600, 100), original[600:700])

    def test_gain_scales_only_the_selected_range(self, session: EditSession) -> None:
        original = session.document.to_array()

        session.apply_gain(TimeRange(100, 200), -6.0)

        expected = original[100:200] * np.float32(db_to_amplitude(-6.0))
        assert np.allclose(session.read(100, 100), expected, atol=1e-5)
        assert np.array_equal(session.read(200, 100), original[200:300])

    @pytest.mark.parametrize("shape", ["linear", "cosine", "exponential"])
    def test_fade_in_starts_at_silence_and_reaches_unity(
        self, session: EditSession, shape: str
    ) -> None:
        original = session.document.to_array()

        session.fade_in(TimeRange(0, 500), shape=shape)
        faded = session.read(0, 500)

        assert np.all(faded[0] == 0.0)
        assert np.allclose(faded[-1], original[499], rtol=1e-5)
        # Monotonically rising gain, checked away from the near-zero first frames.
        gain = faded[100:, 0] / original[100:500, 0]
        assert np.all(np.diff(gain) > -1e-6)

    def test_fade_out_ends_at_silence(self, session: EditSession) -> None:
        session.fade_out(TimeRange(1_500, 2_000))
        faded = session.read(1_500, 500)

        assert np.all(faded[-1] == 0.0)
        assert np.abs(faded[0]).max() > 0.0

    def test_fade_rejects_an_unknown_shape(self) -> None:
        with pytest.raises(ValueError, match="shape must be"):
            FadeCommand(TimeRange(0, 10), shape="sigmoid")

    def test_insert_silence_pushes_the_tail_later(self, session: EditSession) -> None:
        original = session.document.to_array()

        session.insert_silence(1_000, 250)

        assert session.n_frames == 2_250
        assert np.all(session.read(1_000, 250) == 0.0)
        assert np.array_equal(session.read(1_250, 100), original[1_000:1_100])

    def test_reverse_is_its_own_inverse(self, session: EditSession) -> None:
        original = session.document.to_array()

        session.reverse(TimeRange(0, 2_000))
        assert np.array_equal(session.read(0, 2_000), original[::-1])

        session.reverse(TimeRange(0, 2_000))
        assert np.array_equal(session.read(0, 2_000), original)

    def test_trim_keeps_only_the_selection(self, session: EditSession) -> None:
        original = session.document.to_array()

        session.trim(TimeRange(700, 900))

        assert session.n_frames == 200
        assert np.array_equal(session.read(0, 200), original[700:900])
        assert session.undo()
        assert np.array_equal(session.read(0, 2_000), original)

    @pytest.mark.parametrize(
        "command",
        [
            DeleteCommand(TimeRange(10, 20)),
            SilenceCommand(TimeRange(10, 20)),
            GainCommand(TimeRange(10, 20), 3.0),
            FadeCommand(TimeRange(10, 20), direction="out"),
            ReverseCommand(TimeRange(10, 20)),
            TrimCommand(TimeRange(10, 20)),
            InsertSilenceCommand(10, 20),
        ],
        ids=lambda c: type(c).__name__,
    )
    def test_every_command_round_trips(self, command) -> None:
        data = ramp(64)
        document = AudioDocument.from_array(data, SR, chunk_frames=16)

        applied = command.apply(document)
        restored = command.revert(applied)

        assert np.array_equal(restored.to_array(), data)

    def test_an_empty_selection_is_rejected(self, session: EditSession) -> None:
        with pytest.raises(EditError, match="empty selection"):
            session.delete(TimeRange(500, 500))

    def test_reverting_before_applying_is_an_error(self) -> None:
        document = AudioDocument.from_array(ramp(64), SR)

        with pytest.raises(EditError, match="revert"):
            DeleteCommand(TimeRange(0, 10)).revert(document)


# ---------------------------------------------------------------------------
# the history
# ---------------------------------------------------------------------------


class TestUndoRedo:
    def test_a_long_history_unwinds_to_the_original_samples(self, session: EditSession) -> None:
        original = session.document.to_array()

        session.cut(TimeRange(100, 400))
        session.paste(0)
        session.apply_gain(TimeRange(0, 300), -12.0)
        session.fade_in(TimeRange(0, 200), shape="cosine")
        session.silence(TimeRange(800, 900))
        session.insert_silence(50, 40)
        session.reverse(TimeRange(1_000, 1_200))
        session.delete(TimeRange(0, 60))

        assert session.undo_stack.depth == 8
        while session.undo():
            pass

        assert session.n_frames == 2_000
        assert np.array_equal(session.read(0, 2_000), original)
        assert not session.can_undo

    def test_redo_replays_the_history_exactly(self, session: EditSession) -> None:
        session.cut(TimeRange(100, 400))
        session.apply_gain(TimeRange(0, 200), 6.0)
        session.fade_out(TimeRange(1_000, 1_200))
        final = session.read(0, session.n_frames)

        for _ in range(3):
            assert session.undo()
        for _ in range(3):
            assert session.redo()

        assert np.array_equal(session.read(0, session.n_frames), final)
        assert not session.can_redo

    def test_undo_redo_can_be_driven_back_and_forth(self, session: EditSession) -> None:
        before = session.read(0, session.n_frames)
        session.silence(TimeRange(0, 100))
        after = session.read(0, session.n_frames)

        for _ in range(5):
            assert session.undo()
            assert np.array_equal(session.read(0, session.n_frames), before)
            assert session.redo()
            assert np.array_equal(session.read(0, session.n_frames), after)

    def test_a_new_edit_discards_the_redo_branch(self, session: EditSession) -> None:
        session.silence(TimeRange(0, 100))
        session.silence(TimeRange(200, 300))
        session.undo()
        assert session.can_redo

        session.apply_gain(TimeRange(400, 500), -3.0)

        assert not session.can_redo
        assert session.undo_stack.labels() == ["Silence", "Gain"]

    def test_undo_and_redo_on_an_empty_history_are_no_ops(self) -> None:
        session = EditSession(sample_rate=SR, n_channels=1)

        assert not session.undo()
        assert not session.redo()

    def test_history_labels_describe_the_commands(self, session: EditSession) -> None:
        session.cut(TimeRange(0, 10))
        session.fade_out(TimeRange(100, 200))

        assert session.undo_stack.undo_label == "Fade Out"
        session.undo()
        assert session.undo_stack.undo_label == "Cut"
        assert session.undo_stack.redo_label == "Fade Out"

    def test_the_history_depth_is_bounded(self) -> None:
        session = EditSession(
            AudioDocument.from_array(ramp(1_000), SR, chunk_frames=64), undo_limit=5
        )

        for start in range(0, 500, 50):
            session.apply_gain(TimeRange(start, start + 10), 1.0)

        assert session.undo_stack.depth == 5
        assert session.undo_stack.can_undo

    def test_the_clean_marker_tracks_saved_state(self, session: EditSession) -> None:
        assert not session.is_modified

        session.silence(TimeRange(0, 100))
        assert session.is_modified

        session.undo()
        assert not session.is_modified

        session.redo()
        session.undo_stack.set_clean()
        assert not session.is_modified

    def test_resetting_drops_the_history(self, session: EditSession) -> None:
        session.silence(TimeRange(0, 100))

        session.reset(AudioBuffer(ramp(300), SR))

        assert session.n_frames == 300
        assert not session.can_undo
        assert session.clipboard is None
        assert not session.is_modified

    def test_the_undo_stack_refuses_to_step_past_its_ends(self) -> None:
        stack = UndoStack(limit=2)

        with pytest.raises(EditError, match="nothing to undo"):
            stack.undo()
        with pytest.raises(EditError, match="nothing to redo"):
            stack.redo()


# ---------------------------------------------------------------------------
# session integration
# ---------------------------------------------------------------------------


class TestSession:
    def test_a_session_is_a_sample_source(self, session: EditSession) -> None:
        from audio_studio.core.sample_source import SampleSource

        assert isinstance(session, SampleSource)
        assert session.read(0, 10).shape == (10, 2)
        assert session.exact
        assert session.last_error is None
        session.close()  # a session owns no OS handle; must still be callable

    def test_read_into_serves_the_feeder_without_allocating(self, session: EditSession) -> None:
        out = np.full((300, 2), -1.0, dtype=np.float32)

        delivered = session.read_into(out, 1_800)

        assert delivered == 200  # only 200 frames remain from 1_800
        assert np.array_equal(out[:200], session.read(1_800, 200))
        assert np.all(out[200:] == 0.0)

    def test_read_into_rejects_a_mis_shaped_buffer(self, session: EditSession) -> None:
        with pytest.raises(ValueError, match=r"out must be \(frames, 2\)"):
            session.read_into(np.empty((16, 1), dtype=np.float32), 0)

    def test_read_into_crosses_segment_boundaries(self) -> None:
        """After a paste the document is a patchwork; a read must not see the seams."""
        data = ramp(1_000)
        session = EditSession(AudioDocument.from_array(data, SR, chunk_frames=64))
        session.copy(TimeRange(0, 100))
        session.paste(500)

        out = np.empty((1_100, 2), dtype=np.float32)
        assert session.read_into(out, 0) == 1_100
        expected = np.concatenate([data[:500], data[:100], data[500:]])
        assert np.array_equal(out, expected)

    def test_the_revision_counter_advances_on_every_change(self, session: EditSession) -> None:
        start = session.revision

        session.silence(TimeRange(0, 10))
        session.undo()
        session.redo()

        assert session.revision == start + 3

    def test_listeners_see_every_revision(self, session: EditSession) -> None:
        seen: list[int] = []
        session.add_listener(lambda s: seen.append(s.n_frames))

        session.delete(TimeRange(0, 500))
        session.undo()

        assert seen == [1_500, 2_000]
        session.remove_listener(session._listeners[0])  # noqa: SLF001 - listener identity
        session.delete(TimeRange(0, 500))
        assert seen == [1_500, 2_000]

    def test_copy_leaves_the_document_untouched(self, session: EditSession) -> None:
        before = session.read(0, session.n_frames)

        session.copy(TimeRange(0, 100))

        assert np.array_equal(session.read(0, session.n_frames), before)
        assert not session.can_undo

    def test_pasting_a_raw_array_works(self, session: EditSession) -> None:
        payload = np.ones((50, 2), dtype=np.float32)

        session.paste(0, payload)

        assert np.array_equal(session.read(0, 50), payload)

    def test_a_reader_never_observes_a_half_applied_edit(self) -> None:
        """The playback thread reads while the GUI thread edits."""
        session = EditSession(AudioDocument.from_array(ramp(50_000), SR, chunk_frames=1_024))
        stop = threading.Event()
        failures: list[str] = []

        def reader() -> None:
            while not stop.is_set():
                document = session.document
                block = document.read(0, min(4_096, document.n_frames))
                # Every revision here is built from the same ramp, so any frame
                # read must equal a frame that exists somewhere in the original.
                if not np.all(np.isfinite(block)):
                    failures.append("non-finite sample")
                if block.shape[1] != 2:
                    failures.append(f"channel count changed: {block.shape}")

        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        try:
            for i in range(60):
                session.apply_gain(TimeRange(i * 100, i * 100 + 500), -1.0)
                session.undo()
        finally:
            stop.set()
            thread.join(timeout=5.0)

        assert not failures
        assert np.array_equal(session.read(0, 50_000), ramp(50_000))

    def test_the_default_chunk_size_is_used_when_unspecified(self) -> None:
        document = AudioDocument.from_array(ramp(DEFAULT_CHUNK_FRAMES + 10), SR)

        assert document.n_segments == 2

    def test_an_empty_session_reports_zero_length(self) -> None:
        session = EditSession(sample_rate=SR, n_channels=2)

        assert session.n_frames == 0
        assert session.duration == 0.0
        assert session.read(0, 100).shape == (0, 2)
        assert "0 frames" in repr(session)
