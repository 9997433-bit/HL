"""Dock-layout persistence: a project bundle and a restart both remember it.

Two independent paths have to survive: a ``.hlproj`` bundle carries the
arrangement in its ``ui.layout`` section, and a window opened on nothing falls
back to whatever the application last quit with. The second path is exercised
against an isolated ``QSettings`` file rather than the user's real one, so the
suite neither reads nor writes the desktop session's preferences.

The round trip is also recorded as machine-readable evidence for SOTA
checklist item D2; see :func:`test_dock_layout_evidence_is_recorded`.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from audio_studio.core.engine import AudioEngine
from audio_studio.core.loader import LoadedAudio
from audio_studio.core.output import NullOutput
from audio_studio.project.store import LayoutState, load_project
from audio_studio.ui.main_window import LAYOUT_SETTINGS_KEY, MainWindow

pytestmark = pytest.mark.usefixtures("qapp")

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_PATH = REPOSITORY_ROOT / ".agent_workspace" / "v1.0" / "dock-layout-evidence.json"

#: Deliberately unlike the window's defaults on every dock that can differ:
#: the effect rack goes away, the plugin slots come forward out of the tab it
#: was in front of, and the marker list — hidden until something needs it —
#: is pinned open.
ARRANGEMENT: dict[str, bool] = {
    "SpectrumDock": True,
    "EffectsDock": False,
    "PluginDock": True,
    "MarkersDock": True,
}


@contextmanager
def main_window(settings: QSettings | None = None) -> Iterator[MainWindow]:
    """A window on a silent engine, closed cleanly however the test ends."""
    window = MainWindow(AudioEngine(NullOutput(realtime=False)), settings=settings)
    try:
        yield window
    finally:
        window._mark_project_saved()  # noqa: SLF001 - no close prompt in tests
        window.close()


def _arrange(window: MainWindow, arrangement: dict[str, bool]) -> dict[str, bool]:
    docks = window.dock_widgets()
    for name, shown in arrangement.items():
        docks[name].setVisible(shown)
    return window.dock_visibility()


def _saved_project(window: MainWindow, root: Path, clip: LoadedAudio) -> Path:
    window._bind_edit_session(clip)  # noqa: SLF001 - mirrors open_file()
    window._update_for_clip()  # noqa: SLF001
    saved = window._write_project(root)  # noqa: SLF001
    window._mark_project_saved()  # noqa: SLF001
    return saved


def test_default_arrangement_differs_from_the_one_under_test() -> None:
    """Guards every other case here: a no-op restore must not look like a pass."""
    with main_window() as window:
        assert window.dock_visibility() != ARRANGEMENT


def test_project_bundle_restores_the_dock_arrangement(
    loaded_clip: LoadedAudio, tmp_path: Path
) -> None:
    with main_window() as source:
        expected = _arrange(source, ARRANGEMENT)
        saved = _saved_project(source, tmp_path / "layout.hlproj", loaded_clip)

    snapshot = load_project(saved)
    assert not snapshot.layout.is_empty
    assert snapshot.layout.docks == expected

    with main_window() as target:
        assert target.dock_visibility() != expected
        assert target._open_project(saved)  # noqa: SLF001
        assert target.dock_visibility() == expected


def test_project_json_records_the_layout_under_the_ui_section(
    loaded_clip: LoadedAudio, tmp_path: Path
) -> None:
    with main_window() as window:
        _arrange(window, ARRANGEMENT)
        saved = _saved_project(window, tmp_path / "written.hlproj", loaded_clip)

    payload = json.loads((saved / "project.json").read_text(encoding="utf-8"))
    layout = payload["ui"]["layout"]
    assert layout["docks"] == ARRANGEMENT
    for key in ("window_state", "geometry"):
        # The store carries Qt's blobs without interpreting them, but a value
        # that is not base64 would fail on the way back in, not here.
        assert base64.b64decode(layout[key], validate=True)


def test_a_bundle_without_a_layout_still_opens(
    loaded_clip: LoadedAudio, tmp_path: Path
) -> None:
    """A project written before layouts existed leaves the window as it was."""
    with main_window() as window:
        saved = _saved_project(window, tmp_path / "legacy.hlproj", loaded_clip)

    json_path = saved / "project.json"
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    del payload["ui"]["layout"]
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    assert load_project(saved).layout.is_empty
    with main_window() as window:
        before = window.dock_visibility()
        assert window._open_project(saved)  # noqa: SLF001
        assert window.dock_visibility() == before


def test_a_fresh_window_opens_with_the_layout_the_last_one_quit_with(
    tmp_path: Path,
) -> None:
    settings = QSettings(
        str(tmp_path / "audio-studio.ini"), QSettings.Format.IniFormat
    )
    with main_window(settings) as first:
        expected = _arrange(first, ARRANGEMENT)
    assert settings.value(LAYOUT_SETTINGS_KEY)

    with main_window(settings) as second:
        assert second.dock_visibility() == expected


def test_a_window_without_settings_keeps_nothing_across_runs() -> None:
    with main_window() as window:
        assert window.settings is None
        assert window.save_layout_settings() is False
        assert window.restore_layout_settings() is False


def test_an_unusable_saved_layout_leaves_the_window_at_its_defaults(
    tmp_path: Path,
) -> None:
    state = LayoutState.from_json(
        {"window_state": "not base64!", "geometry": 17, "docks": {"NoSuchDock": True}}
    )
    assert state.window_state is None
    assert state.geometry is None

    settings = QSettings(str(tmp_path / "broken.ini"), QSettings.Format.IniFormat)
    settings.setValue(LAYOUT_SETTINGS_KEY, "{not json")

    with main_window() as window:
        before = window.dock_visibility()
        assert window.apply_layout_state(state) is False
        assert window.apply_layout_state(LayoutState.from_json(None)) is False
        window.settings = settings
        assert window.restore_layout_settings() is False
        assert window.dock_visibility() == before
        window.settings = None


def test_dock_layout_evidence_is_recorded(
    loaded_clip: LoadedAudio, tmp_path: Path
) -> None:
    """Re-run both persistence paths and write the D2 evidence report."""
    checks: list[dict[str, object]] = []

    with main_window() as source:
        default_arrangement = source.dock_visibility()
        expected = _arrange(source, ARRANGEMENT)
        saved = _saved_project(source, tmp_path / "evidence.hlproj", loaded_clip)

    snapshot = load_project(saved)
    with main_window() as target:
        reopened = target._open_project(saved)  # noqa: SLF001
        bundle_docks = target.dock_visibility()
    checks.append(
        {
            "check": "project-bundle",
            "detail": "docks recorded in .hlproj ui.layout and restored on open",
            "reopened": reopened,
            "expected": expected,
            "restored": bundle_docks,
            "status": "pass" if reopened and bundle_docks == expected else "fail",
        }
    )

    settings = QSettings(str(tmp_path / "quit.ini"), QSettings.Format.IniFormat)
    with main_window(settings) as first:
        _arrange(first, ARRANGEMENT)
    with main_window(settings) as second:
        settings_docks = second.dock_visibility()
    checks.append(
        {
            "check": "application-restart",
            "detail": "layout written on quit and reapplied by a window with no project",
            "expected": expected,
            "restored": settings_docks,
            "status": "pass" if settings_docks == expected else "fail",
        }
    )

    report = {
        "item": "D2",
        "title": "Dock presets and layout persistence",
        "status": "pass" if all(check["status"] == "pass" for check in checks) else "fail",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "generated_by": "audio-studio/tests/test_ui_persistence.py",
        "platform": "qt-offscreen",
        "mechanism": {
            "save": "QMainWindow.saveState/saveGeometry + per-dock visibility",
            "project_key": "ui.layout",
            "settings_key": LAYOUT_SETTINGS_KEY,
        },
        "default_arrangement": default_arrangement,
        "arrangement_under_test": ARRANGEMENT,
        "state_blob_bytes": len(base64.b64decode(snapshot.layout.window_state or "")),
        "checks": checks,
    }

    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    assert report["status"] == "pass"
