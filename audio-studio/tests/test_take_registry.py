"""Numbered recording-take persistence and the File ▸ Takes workflow."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from audio_studio.core.engine import AudioEngine
from audio_studio.core.output import NullOutput
from audio_studio.core.recorder import (
    NullRecorder,
    TakeRegistry,
    TakeRegistryError,
)
from audio_studio.ui.main_window import MainWindow


def write_take(registry: TakeRegistry, content: bytes = b"audio") -> Path:
    path = registry.next_take_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def test_project_registry_numbers_takes_and_uses_bundle_relative_paths(
    tmp_path: Path,
) -> None:
    project = tmp_path / "session.hlproj"
    registry = TakeRegistry(project)
    first_path = write_take(registry)
    first = registry.register(
        first_path,
        sample_rate=48_000,
        channels=2,
        frames=96_000,
        metadata={"notes": "wide"},
    )
    second_path = write_take(registry)
    second = registry.register(
        second_path,
        sample_rate=44_100,
        channels=1,
        frame_count=22_050,
    )

    assert first.number == 1 and first.name == "Take 001"
    assert first.duration == pytest.approx(2.0)
    assert second.number == 2
    assert registry.next_number == 3
    assert registry.metadata_path == project / "takes.json"

    payload = json.loads((project / "takes.json").read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert payload["takes"][0]["path"] == "takes/take-001.wav"
    assert payload["takes"][0]["metadata"] == {"notes": "wide"}

    reopened = TakeRegistry(project)
    assert [take.number for take in reopened] == [1, 2]
    assert reopened.take(1) is not None
    assert reopened.take(1).path == first_path.resolve()


def test_non_project_session_uses_a_sidecar(tmp_path: Path) -> None:
    session = tmp_path / "interview.wav"
    registry = TakeRegistry(session)
    path = write_take(registry)
    registry.register(path, sample_rate=48_000, channels=1, frames=480)

    assert registry.metadata_path == tmp_path / "interview.wav.takes.json"
    assert registry.metadata_path.is_file()
    assert TakeRegistry(session).takes[0].path == path.resolve()


def test_existing_directory_keeps_metadata_inside_it(tmp_path: Path) -> None:
    registry = TakeRegistry(tmp_path)
    path = write_take(registry)
    registry.register(path, sample_rate=48_000, channels=1, frames=48)

    assert registry.metadata_path == tmp_path / "takes.json"
    assert registry.takes[0].path.parent == tmp_path / "takes"


def test_registry_never_reuses_a_number_after_reload(tmp_path: Path) -> None:
    session = tmp_path / "session.takes.json"
    registry = TakeRegistry(session)
    path = write_take(registry)
    registry.register(path, sample_rate=48_000, channels=2, frames=1, number=7)

    reopened = TakeRegistry(session)
    next_path = write_take(reopened, b"next")
    take = reopened.register(next_path, sample_rate=48_000, channels=2, frames=1)

    assert take.number == 8
    assert next_path.name == "take-008.wav"


def test_copy_to_project_makes_take_audio_portable(tmp_path: Path) -> None:
    source = TakeRegistry(tmp_path / "scratch.takes.json")
    source_path = write_take(source, b"recorded bytes")
    source.register(source_path, sample_rate=48_000, channels=1, frames=64)

    project = tmp_path / "portable.hlproj"
    copied = source.copy_to(project)

    assert copied.metadata_path == project / "takes.json"
    assert copied.takes[0].path == project / "takes" / "take-001.wav"
    assert copied.takes[0].path.read_bytes() == b"recorded bytes"
    payload = json.loads(copied.metadata_path.read_text(encoding="utf-8"))
    assert payload["takes"][0]["path"] == "takes/take-001.wav"


def test_corrupt_or_unknown_metadata_is_rejected(tmp_path: Path) -> None:
    sidecar = tmp_path / "broken.takes.json"
    sidecar.write_text('{"version": 99, "takes": []}', encoding="utf-8")

    with pytest.raises(TakeRegistryError, match="version"):
        TakeRegistry(sidecar)


def test_main_window_registers_completed_recording_and_lists_it(qapp, tmp_path: Path) -> None:
    recorder = NullRecorder(realtime=False, tone_frequency=220.0)
    main = MainWindow(
        AudioEngine(NullOutput(realtime=False)),
        recorder=recorder,
    )
    try:
        project = tmp_path / "recording.hlproj"
        main._project_path = project  # noqa: SLF001 - stand in for an open project
        main.take_registry = TakeRegistry(project)
        main._refresh_takes_menu()  # noqa: SLF001
        assert not main.takes_menu.isEnabled()
        main._on_record()  # noqa: SLF001 - exercise the transport slot
        recorder.pump(96)
        main._on_record()  # noqa: SLF001

        assert len(main.take_registry) == 1
        take = main.take_registry.takes[0]
        assert take.number == 1
        assert take.frames == 96
        assert take.path.is_file()
        assert main.take_registry.metadata_path.is_file()
        assert main.takes_menu.isEnabled()
        assert "Take 001" in main.takes_menu.actions()[0].text()
        assert main._project_path == project  # noqa: SLF001
        assert main._project_dirty  # noqa: SLF001 - the take became the waveform document
        main._mark_project_saved()  # noqa: SLF001 - accept the new waveform document
        assert main.open_take(1)
        assert main.engine.n_frames == 96
    finally:
        main._mark_project_saved()  # noqa: SLF001 - avoid a close confirmation
        main.close()
