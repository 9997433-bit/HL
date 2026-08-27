"""A whole editing session driven by nothing but key sequences.

Open a file, select the document, cut it, undo the cut and export the result —
each step delivered as a real key event into the main window and dispatched by
the :class:`QAction` that owns the sequence. Nothing here calls the slot
behind an action, and an event filter over the application counts every mouse
event that reaches it, so a step that quietly needed a click cannot pass.

The two file dialogs are answered without a user, which is the one thing a
headless run cannot do from the keyboard; the commands that open them are
still reached by their shortcut.

The run writes machine-readable evidence for SOTA checklist item D3; see
:data:`EVIDENCE_PATH`.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QAction
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog

from audio_studio.core.engine import AudioEngine
from audio_studio.core.loader import load_audio, save_audio
from audio_studio.core.output import NullOutput
from audio_studio.core.types import AudioBuffer
from audio_studio.ui.main_window import MainWindow, strip_mnemonic

pytestmark = pytest.mark.usefixtures("qapp")

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_PATH = (
    REPOSITORY_ROOT / ".agent_workspace" / "v1.0" / "keyboard-workflow-evidence.json"
)

#: Every pointer event the filter refuses to see during the workflow.
POINTER_EVENTS = frozenset(
    {
        QEvent.Type.MouseButtonPress,
        QEvent.Type.MouseButtonRelease,
        QEvent.Type.MouseButtonDblClick,
        QEvent.Type.MouseMove,
        QEvent.Type.Wheel,
        QEvent.Type.TabletPress,
        QEvent.Type.TabletRelease,
    }
)


class PointerCounter(QObject):
    """Counts every pointer event the application delivers while installed."""

    def __init__(self) -> None:
        super().__init__()
        self.count = 0

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt override
        if event.type() in POINTER_EVENTS:
            self.count += 1
        return False


@pytest.fixture()
def pointer_counter(qapp: QApplication) -> Iterator[PointerCounter]:
    counter = PointerCounter()
    qapp.installEventFilter(counter)
    try:
        yield counter
    finally:
        qapp.removeEventFilter(counter)


@pytest.fixture()
def source_wav(tmp_path: Path) -> Path:
    """A short deterministic stereo tone the workflow opens from disk."""
    rate = 44_100
    t = np.arange(rate // 2, dtype=np.float32) / rate
    data = np.stack(
        [0.4 * np.sin(2.0 * np.pi * 440.0 * t), 0.4 * np.sin(2.0 * np.pi * 880.0 * t)],
        axis=1,
    ).astype(np.float32)
    path = tmp_path / "keyboard-source.wav"
    save_audio(path, AudioBuffer(data, rate), subtype="PCM_16")
    return path


@pytest.fixture()
def window(qapp: QApplication) -> Iterator[MainWindow]:
    main = MainWindow(AudioEngine(NullOutput(realtime=False), block_size=256))
    main.resize(1200, 700)
    main.show()
    qapp.processEvents()
    main.activateWindow()
    qapp.processEvents()
    try:
        yield main
    finally:
        main._mark_project_saved()  # noqa: SLF001 - no close prompt in tests
        main.close()


class KeyboardDriver:
    """Sends key sequences at a window and records what each one ran."""

    def __init__(self, window: MainWindow, app: QApplication) -> None:
        self.window = window
        self.app = app
        self.log: list[dict[str, object]] = []

    def press(self, step: str, action: QAction) -> None:
        sequence = action.shortcut()
        assert not sequence.isEmpty(), f"{step}: {action.text()!r} has no shortcut"
        assert action.isEnabled(), f"{step}: {action.text()!r} is not reachable yet"

        fired: list[bool] = []
        connection = action.triggered.connect(lambda *_: fired.append(True))
        try:
            QTest.keySequence(self.window, sequence)
            self.app.processEvents()
        finally:
            action.triggered.disconnect(connection)

        assert fired, f"{step}: {sequence.toString()} did not reach {action.text()!r}"
        self.log.append(
            {
                "step": step,
                "command": strip_mnemonic(action.text()),
                "keys": sequence.toString(),
                "triggered": True,
            }
        )

    @property
    def steps(self) -> list[str]:
        return [str(entry["step"]) for entry in self.log]


def _unique_shortcuts(window: MainWindow) -> None:
    """No two window-level actions answer to the same key sequence."""
    seen: dict[str, str] = {}
    for action in window.actions():
        keys = action.shortcut().toString()
        if not keys:
            continue
        assert keys not in seen, f"{keys} is bound to both {seen[keys]!r} and {action.text()!r}"
        seen[keys] = action.text()


def _run_workflow(
    window: MainWindow,
    app: QApplication,
    source: Path,
    export: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[KeyboardDriver, dict[str, object]]:
    """Open, select, cut, undo and export, entirely from key sequences."""
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(source), ""))
    )
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(export), ""))
    )

    driver = KeyboardDriver(window, app)
    measured: dict[str, object] = {}

    driver.press("open", window.action_open)
    assert window.engine.has_clip
    measured["source_frames"] = int(window.engine.n_frames)

    driver.press("select", window.action_select_all)
    selection = window.engine.selection
    assert selection is not None and selection.length == window.engine.n_frames
    measured["selected_frames"] = int(selection.length)

    driver.press("cut", window.action_cut)
    measured["frames_after_cut"] = int(window.engine.n_frames)

    driver.press("undo", window.action_undo)
    measured["frames_after_undo"] = int(window.engine.n_frames)

    driver.press("export", window.action_export)
    assert export.is_file()
    exported = load_audio(export).buffer
    original = load_audio(source).buffer
    measured["exported_frames"] = int(exported.n_frames)
    measured["export_matches_source"] = bool(
        exported.n_frames == original.n_frames
        and np.allclose(exported.data, original.data, atol=1e-4)
    )
    return driver, measured


def test_every_workflow_command_has_a_unique_shortcut(window: MainWindow) -> None:
    _unique_shortcuts(window)
    for action in (
        window.action_open,
        window.action_select_all,
        window.action_cut,
        window.action_undo,
        window.action_export,
    ):
        assert not action.shortcut().isEmpty()


def test_selecting_a_range_enables_the_range_commands(
    window: MainWindow, qapp: QApplication, source_wav: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Select All has to leave Cut reachable, or the chain stops at step two."""
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(source_wav), ""))
    )
    driver = KeyboardDriver(window, qapp)
    driver.press("open", window.action_open)
    assert not window.action_cut.isEnabled()

    driver.press("select", window.action_select_all)

    for action in (window.action_cut, window.action_copy, window.action_trim):
        assert action.isEnabled(), strip_mnemonic(action.text())


def test_keyboard_only_workflow_runs_without_a_pointer(
    window: MainWindow,
    qapp: QApplication,
    pointer_counter: PointerCounter,
    source_wav: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver, measured = _run_workflow(
        window, qapp, source_wav, tmp_path / "keyboard-export.wav", monkeypatch
    )

    assert driver.steps == ["open", "select", "cut", "undo", "export"]
    assert measured["frames_after_cut"] == 0
    assert measured["frames_after_undo"] == measured["source_frames"]
    assert measured["export_matches_source"] is True
    assert pointer_counter.count == 0


def test_keyboard_workflow_evidence_is_recorded(
    window: MainWindow,
    qapp: QApplication,
    pointer_counter: PointerCounter,
    source_wav: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Re-run the workflow and write the D3 evidence report."""
    _unique_shortcuts(window)
    driver, measured = _run_workflow(
        window, qapp, source_wav, tmp_path / "evidence-export.wav", monkeypatch
    )

    passed = (
        driver.steps == ["open", "select", "cut", "undo", "export"]
        and all(entry["triggered"] for entry in driver.log)
        and measured["frames_after_cut"] == 0
        and measured["frames_after_undo"] == measured["source_frames"]
        and measured["export_matches_source"] is True
        and pointer_counter.count == 0
    )

    report = {
        "item": "D3",
        "title": "Keyboard-only end-to-end workflow",
        "status": "pass" if passed else "fail",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "generated_by": "audio-studio/tests/test_keyboard_workflow.py",
        "platform": "qt-offscreen",
        "dispatch": "QTest.keySequence delivered to the main window, run by QAction shortcuts",
        "mouse_events": pointer_counter.count,
        "steps": driver.steps,
        "keystrokes": driver.log,
        "measurements": measured,
        "notes": [
            "The Open and Export As file dialogs are answered by the harness; "
            "the commands that raise them are reached by their key sequence.",
            "Every pointer event delivered to the application during the run is "
            "counted by an installed event filter.",
        ],
    }

    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    assert report["status"] == "pass"
