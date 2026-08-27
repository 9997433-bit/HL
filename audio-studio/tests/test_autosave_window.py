"""The window's half of crash recovery (SOTA E4).

``tests/test_crash_recovery.py`` at the repository root proves the journal
survives a kill. What is left to show is that the window is wired to it: that
it snapshots work a crash would destroy, leaves nothing behind when it closes
normally, and offers a recovered session back on the next launch.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtWidgets import QMessageBox

from audio_studio.core.autosave import discover
from audio_studio.core.engine import AudioEngine
from audio_studio.core.loader import LoadedAudio
from audio_studio.core.output import NullOutput
from audio_studio.core.types import TimeRange
from audio_studio.ui.main_window import MainWindow


@pytest.fixture()
def autosave_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "autosave"
    monkeypatch.setenv("AUDIO_STUDIO_AUTOSAVE_DIR", str(root))
    return root


@pytest.fixture()
def window(qapp: object, loaded_clip: LoadedAudio, autosave_root: Path) -> Iterator[MainWindow]:
    engine = AudioEngine(NullOutput(realtime=False), block_size=256)
    main = MainWindow(engine)
    engine.set_clip(loaded_clip)
    main._bind_edit_session(loaded_clip)  # noqa: SLF001 - mirrors open_file()
    main._update_for_clip()  # noqa: SLF001 - normally triggered by open_file()
    yield main
    main._mark_project_saved()  # noqa: SLF001 - avoid blocking close prompts
    main.close()


def _edit(window: MainWindow) -> None:
    window._edit_session.apply_gain(TimeRange(0, 256), -6.0)  # noqa: SLF001


class TestWindowAutosave:
    def test_a_dirty_session_is_snapshotted(self, window: MainWindow) -> None:
        _edit(window)
        window._autosave_tick()  # noqa: SLF001 - the timer's slot
        assert window._autosave.sequence == 1  # noqa: SLF001
        assert len(discover(include_live=True)) == 1

    def test_a_clean_session_is_not(self, window: MainWindow) -> None:
        """Work already on disk under its own name does not need copying."""
        window._mark_project_saved()  # noqa: SLF001
        window._autosave_tick()  # noqa: SLF001
        assert window._autosave.sequence == 0  # noqa: SLF001
        assert discover(include_live=True) == []

    def test_closing_the_window_takes_its_journal_with_it(
        self, window: MainWindow
    ) -> None:
        _edit(window)
        window._autosave_tick()  # noqa: SLF001
        window._mark_project_saved()  # noqa: SLF001
        window.close()
        assert discover(include_live=True) == []


class TestOfferRecovery:
    def _abandon(self, window: MainWindow) -> None:
        """Leave a journal behind the way a crash would: unreleased."""
        _edit(window)
        window._autosave_tick()  # noqa: SLF001
        window._autosave.stop()  # noqa: SLF001 - no release: this is the crash
        window._mark_project_saved()  # noqa: SLF001

    def test_an_abandoned_session_is_offered_and_reopened(
        self, window: MainWindow, monkeypatch: pytest.MonkeyPatch, autosave_root: Path
    ) -> None:
        self._abandon(window)
        for session in discover(autosave_root, include_live=True):
            # The journal names this very process, which is alive; a real
            # launch is a new process and the owner is gone.
            _force_stale(session.directory)

        monkeypatch.setattr(
            QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes
        )
        assert window.offer_crash_recovery() is True
        # Recovered work is unsaved work, and it does not belong to the
        # journal's scratch bundle.
        assert window._has_unsaved_changes() is True  # noqa: SLF001
        assert window._project_path is None  # noqa: SLF001
        assert discover(autosave_root, include_live=True) == []

    def test_a_declined_offer_is_not_made_twice(
        self, window: MainWindow, monkeypatch: pytest.MonkeyPatch, autosave_root: Path
    ) -> None:
        self._abandon(window)
        for session in discover(autosave_root, include_live=True):
            _force_stale(session.directory)

        monkeypatch.setattr(
            QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.No
        )
        assert window.offer_crash_recovery() is False
        assert discover(autosave_root, include_live=True) == []

    def test_a_launch_with_nothing_to_recover_asks_nothing(
        self, window: MainWindow, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def refuse(*args: object, **kwargs: object) -> None:
            raise AssertionError("the user was asked about a session that never crashed")

        monkeypatch.setattr(QMessageBox, "question", refuse)
        assert window.offer_crash_recovery() is False


def _force_stale(directory: Path) -> None:
    """Rewrite a journal's PID to one that cannot be running.

    The alternative is spawning a process to kill, which the harness at
    ``tools/crash_recovery.py`` already does; here the point is the window's
    behaviour once recovery has something to offer it.
    """
    import json

    from audio_studio.core.autosave import JOURNAL_NAME, JournalEntry

    path = directory / JOURNAL_NAME
    entry = JournalEntry.from_json(json.loads(path.read_text(encoding="utf-8")))
    dead = JournalEntry(**{**entry.__dict__, "pid": 2**22 - 1})
    path.write_text(json.dumps(dead.to_json(), indent=2, sort_keys=True), encoding="utf-8")
