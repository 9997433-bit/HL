"""Tests for interval autosave and crash recovery (SOTA E4).

The unit tests here cover the parts a crash makes unobservable: what the
journal refuses, what it leaves behind, which slot it writes next. The
end-to-end proof — that a process killed with ``SIGKILL`` comes back — is the
harness in ``tools/crash_recovery.py``, and the last test in this file runs a
short version of it rather than restating it in mocks.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
for _import_root in (REPOSITORY_ROOT, REPOSITORY_ROOT / "audio-studio"):
    if str(_import_root) not in sys.path:
        sys.path.insert(0, str(_import_root))

from audio_studio.core.autosave import (
    JOURNAL_NAME,
    STALE_AFTER_INTERVALS,
    AutosaveJournal,
    JournalEntry,
    bundle_digest,
    default_root,
    discover,
    process_alive,
)
from audio_studio.core.edit_session import EditSession
from audio_studio.core.loader import LoadedAudio, load_audio, save_audio
from audio_studio.core.session import MultitrackSession, Track
from audio_studio.core.types import AudioBuffer, TimeRange
from audio_studio.project.store import PROJECT_JSON

from tools.crash_recovery import build_report, run_clean_exit_control, run_trial

SAMPLE_RATE = 48_000
POSIX_ONLY = pytest.mark.skipif(
    sys.platform == "win32", reason="SIGKILL and os.kill are POSIX"
)


@pytest.fixture
def clip(tmp_path: Path) -> LoadedAudio:
    rng = np.random.default_rng(7)
    samples = (0.3 * (2.0 * rng.random((4_096, 2)) - 1.0)).astype(np.float32)
    path = tmp_path / "source.wav"
    save_audio(path, AudioBuffer(samples, SAMPLE_RATE), subtype="FLOAT")
    return load_audio(path)


@pytest.fixture
def snapshot_source(clip: LoadedAudio):
    session = EditSession.from_buffer(clip.buffer)
    multitrack = MultitrackSession(sample_rate=SAMPLE_RATE, n_channels=2)
    multitrack.add_track(Track(name="Take 1"))

    def snapshot() -> dict:
        return {
            "edit_session": session,
            "editor_clip": clip,
            "multitrack": multitrack,
            "workspace": "waveform",
            "view_mode": "split",
            "playhead": 0,
            "selection": None,
        }

    snapshot.session = session  # type: ignore[attr-defined]
    return snapshot


class TestJournal:
    def test_a_save_publishes_a_pointer_to_a_complete_bundle(
        self, tmp_path: Path, snapshot_source
    ) -> None:
        journal = AutosaveJournal(root=tmp_path, interval_s=0.01)
        entry = journal.save(snapshot_source)
        assert entry.sequence == 1
        assert (journal.slot_path(entry.slot) / PROJECT_JSON).is_file()
        assert entry.payload_sha256 == bundle_digest(journal.slot_path(entry.slot))

    def test_saves_alternate_slots_so_the_live_one_is_never_overwritten(
        self, tmp_path: Path, snapshot_source
    ) -> None:
        """The property the whole scheme rests on.

        If a save overwrote the slot the pointer names, a crash during that
        write would destroy the only snapshot there was.
        """
        journal = AutosaveJournal(root=tmp_path, interval_s=0.01)
        slots = [journal.save(snapshot_source).slot for _ in range(4)]
        assert slots == ["a", "b", "a", "b"]

    def test_the_interval_gates_saving(self, tmp_path: Path, snapshot_source) -> None:
        journal = AutosaveJournal(root=tmp_path, interval_s=3_600.0)
        assert journal.maybe_save(snapshot_source) is not None
        assert journal.maybe_save(snapshot_source) is None
        assert journal.sequence == 1

    def test_an_interval_of_zero_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="interval"):
            AutosaveJournal(root=tmp_path, interval_s=0.0)

    def test_the_autosave_thread_keeps_saving(self, tmp_path: Path, snapshot_source) -> None:
        journal = AutosaveJournal(root=tmp_path, interval_s=0.05)
        journal.start(snapshot_source)
        try:
            deadline = datetime.now(UTC) + timedelta(seconds=10)
            while journal.sequence < 2 and datetime.now(UTC) < deadline:
                pass
        finally:
            journal.stop()
        assert journal.sequence >= 2
        assert journal.last_error is None

    def test_a_failing_snapshot_does_not_take_the_editor_down(self, tmp_path: Path) -> None:
        """An autosave that raises is a recorded fault, never a crash."""
        journal = AutosaveJournal(root=tmp_path, interval_s=0.02)

        def broken() -> dict:
            raise RuntimeError("no session")

        journal.start(broken)
        deadline = datetime.now(UTC) + timedelta(seconds=10)
        while journal.last_error is None and datetime.now(UTC) < deadline:
            pass
        journal.stop()
        assert isinstance(journal.last_error, RuntimeError)

    def test_release_leaves_nothing_to_recover(self, tmp_path: Path, snapshot_source) -> None:
        journal = AutosaveJournal(root=tmp_path, interval_s=0.01)
        journal.save(snapshot_source)
        journal.release()
        assert not journal.directory.exists()
        assert discover(tmp_path) == []


class TestRecovery:
    def _crashed_journal(self, root: Path, snapshot_source) -> AutosaveJournal:
        """A journal whose owner is recorded as a PID that no longer exists."""
        journal = AutosaveJournal(root=root, interval_s=0.01)
        journal.save(snapshot_source)
        payload = json.loads(journal.journal_path.read_text(encoding="utf-8"))
        entry = JournalEntry.from_json(payload)
        dead = JournalEntry(**{**entry.__dict__, "pid": 2**22 - 1})
        journal.journal_path.write_text(
            json.dumps(dead.to_json(), indent=2, sort_keys=True), encoding="utf-8"
        )
        return journal

    def test_an_abandoned_session_is_offered_back(self, tmp_path: Path, snapshot_source) -> None:
        self._crashed_journal(tmp_path, snapshot_source)
        found = discover(tmp_path)
        assert len(found) == 1
        assert found[0].verify()
        snapshot = found[0].load()
        assert snapshot.waveform is not None
        assert len(snapshot.multitrack["tracks"]) == 1

    def test_a_live_session_is_left_alone(self, tmp_path: Path, snapshot_source) -> None:
        """Another running instance's work is not this one's to recover."""
        journal = AutosaveJournal(root=tmp_path, interval_s=3_600.0)
        journal.save(snapshot_source)
        assert discover(tmp_path) == []
        assert len(discover(tmp_path, include_live=True)) == 1

    def test_a_live_pid_that_stopped_saving_is_treated_as_abandoned(
        self, tmp_path: Path, snapshot_source
    ) -> None:
        """A recycled PID must not pin a crashed session as live forever."""
        journal = AutosaveJournal(root=tmp_path, interval_s=1.0)
        journal.save(snapshot_source)
        assert discover(tmp_path) == []
        later = datetime.now(UTC) + timedelta(seconds=STALE_AFTER_INTERVALS + 2)
        assert len(discover(tmp_path, now=later)) == 1

    def test_a_torn_pointer_is_refused(self, tmp_path: Path, snapshot_source) -> None:
        journal = self._crashed_journal(tmp_path, snapshot_source)
        text = journal.journal_path.read_text(encoding="utf-8")
        journal.journal_path.write_text(text[: len(text) // 2], encoding="utf-8")
        assert discover(tmp_path) == []

    def test_a_pointer_whose_checksum_does_not_match_is_refused(
        self, tmp_path: Path, snapshot_source
    ) -> None:
        journal = self._crashed_journal(tmp_path, snapshot_source)
        payload = json.loads(journal.journal_path.read_text(encoding="utf-8"))
        payload["sequence"] = 99
        journal.journal_path.write_text(json.dumps(payload), encoding="utf-8")
        assert discover(tmp_path) == []
        with pytest.raises(ValueError, match="checksum"):
            JournalEntry.from_json(payload)

    def test_a_torn_bundle_is_detected_rather_than_restored(
        self, tmp_path: Path, snapshot_source
    ) -> None:
        """The digest is what distinguishes a whole snapshot from a partial one."""
        self._crashed_journal(tmp_path, snapshot_source)
        session = discover(tmp_path)[0]
        document = session.bundle / "media" / "document.wav"
        document.write_bytes(document.read_bytes()[: 1_024])
        assert session.verify() is False
        with pytest.raises(ValueError, match="incomplete"):
            session.load()

    def test_a_directory_with_no_pointer_is_ignored(self, tmp_path: Path) -> None:
        (tmp_path / "session-orphan").mkdir(parents=True)
        assert discover(tmp_path) == []

    def test_an_unparsable_pointer_never_stops_a_launch(self, tmp_path: Path) -> None:
        """Recovery may fail; it may not prevent the application from starting."""
        directory = tmp_path / "session-broken"
        directory.mkdir(parents=True)
        (directory / JOURNAL_NAME).write_text("{not json", encoding="utf-8")
        assert discover(tmp_path) == []

    def test_the_newest_snapshot_is_offered_first(self, tmp_path: Path, snapshot_source) -> None:
        older = self._crashed_journal(tmp_path, snapshot_source)
        newer = self._crashed_journal(tmp_path, snapshot_source)
        found = discover(tmp_path)
        assert len(found) == 2
        assert found[0].entry.saved_at_utc >= found[1].entry.saved_at_utc
        assert {session.directory for session in found} == {older.directory, newer.directory}

    def test_discarding_a_recovered_session_removes_it(
        self, tmp_path: Path, snapshot_source
    ) -> None:
        self._crashed_journal(tmp_path, snapshot_source)
        discover(tmp_path)[0].discard()
        assert discover(tmp_path) == []


class TestProcessLiveness:
    def test_this_process_is_alive(self) -> None:
        assert process_alive(os.getpid()) is True

    def test_a_pid_that_cannot_exist_is_not(self) -> None:
        assert process_alive(0) is False
        assert process_alive(-1) is False

    def test_the_autosave_root_can_be_pointed_somewhere_else(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AUDIO_STUDIO_AUTOSAVE_DIR", str(tmp_path / "elsewhere"))
        assert default_root() == tmp_path / "elsewhere"


@POSIX_ONLY
class TestKillNine:
    """The claim itself: work survives a signal the process cannot handle."""

    def test_a_killed_editor_comes_back_with_its_edits(self, tmp_path: Path) -> None:
        row = run_trial(1, tmp_path / "trial", interval_s=0.15, kill_delay_s=0.05)
        assert row["termination"] == "kill -9"
        assert row["worker_returncode"] == -9, row.get("failure")
        assert row["session_restored"] is True, row.get("recovery")

        recovery = row["recovery"]
        assert recovery["bundle_intact"] is True
        assert recovery["crashed_pid_alive"] is False
        # The restored document is the state after a whole number of edits,
        # not a bundle stitched together from two moments.
        assert recovery["edited_region_prefix"] is True
        assert recovery["edits_restored"] >= 1
        assert 0 <= row["edits_lost"] <= row["edit_loss_budget"]
        assert recovery["tracks_restored"] == 2

    def test_a_clean_exit_leaves_nothing_to_offer(self, tmp_path: Path) -> None:
        row = run_clean_exit_control(tmp_path / "control", interval_s=0.15)
        assert row["status"] == "pass", row
        assert row["recoverable_sessions"] == 0

    def test_the_report_fails_when_a_trial_does(self) -> None:
        trials = [{"status": "pass", "session_restored": True}, {"status": "fail"}]
        report = build_report(trials, interval_s=0.15)
        assert report["status"] == "fail"
        assert report["termination"] == "kill -9"
        assert report["session_restored"] is False

    def test_the_report_fails_when_the_clean_exit_control_does(self) -> None:
        trials = [{"status": "pass", "session_restored": True}]
        report = build_report(
            trials, interval_s=0.15, clean_exit_control={"status": "fail"}
        )
        assert report["status"] == "fail"


@POSIX_ONLY
def test_an_edit_after_the_last_autosave_is_the_only_thing_at_risk(
    tmp_path: Path, snapshot_source
) -> None:
    """What the interval buys: bounded loss, not zero loss.

    Stating it as a test keeps the report's "edits lost" column from reading
    like a defect. Everything up to the last completed autosave is safe;
    everything after it is gone, by design.
    """
    journal = AutosaveJournal(root=tmp_path, interval_s=3_600.0)
    session = snapshot_source.session
    session.apply_gain(TimeRange(0, 512), -12.0)
    saved = journal.slot_path(journal.save(snapshot_source).slot)

    session.apply_gain(TimeRange(512, 1_024), -12.0)
    # The bundle on disk is untouched by an edit made after it was written.
    assert bundle_digest(saved) == json.loads(
        journal.journal_path.read_text(encoding="utf-8")
    )["payload_sha256"]
