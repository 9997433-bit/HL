"""`.hlprojz` archives: packing, unpacking, atomicity and the File menu."""

from __future__ import annotations

import os
import stat
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from audio_studio.core.edit_session import EditSession
from audio_studio.core.engine import AudioEngine
from audio_studio.core.loader import LoadedAudio
from audio_studio.core.markers import MarkerList
from audio_studio.core.output import NullOutput
from audio_studio.core.sample_source import MemorySampleSource
from audio_studio.core.session import MultitrackSession, Track
from audio_studio.core.types import TimeRange
from audio_studio.project.archive import (
    ARCHIVE_SUFFIX,
    ProjectArchiveError,
    archive_path_for,
    is_archive,
    load_project_archive,
    pack_project,
    project_root_name,
    save_project_archive,
    unpack_project,
)
from audio_studio.project.store import (
    load_project,
    load_waveform_document,
    restore_multitrack,
    save_project,
)
from audio_studio.ui import main_window as main_window_module
from audio_studio.ui.main_window import MainWindow

SELECTION = TimeRange(200, 800)
PLAYHEAD = 1_000


def write_bundle(
    root: Path,
    clip: LoadedAudio,
    *,
    markers: MarkerList | None = None,
    plugins: list[dict[str, Any]] | None = None,
    multitrack: MultitrackSession | None = None,
) -> Path:
    """A saved ``.hlproj`` directory with a waveform document in it."""
    return save_project(
        root,
        edit_session=EditSession.from_buffer(clip.buffer),
        editor_clip=clip,
        multitrack=multitrack or MultitrackSession(sample_rate=clip.buffer.sample_rate),
        workspace="waveform",
        view_mode="split",
        playhead=PLAYHEAD,
        selection=SELECTION,
        markers=markers,
        plugins=plugins,
    )


def member_names(archive: Path) -> list[str]:
    with zipfile.ZipFile(archive) as bundle:
        return bundle.namelist()


class TestNaming:
    """The two representations of one project are named after each other."""

    @pytest.mark.parametrize(
        ("given", "expected"),
        [
            ("demo.hlprojz", "demo.hlprojz"),
            ("demo.hlproj", "demo.hlprojz"),
            ("demo", "demo.hlprojz"),
            ("demo.wav", "demo.wav.hlprojz"),
        ],
    )
    def test_archive_paths_get_the_suffix(self, given: str, expected: str) -> None:
        assert archive_path_for(given).name == expected

    @pytest.mark.parametrize(
        ("given", "expected"),
        [
            ("demo.hlprojz", "demo.hlproj"),
            ("demo.hlproj.hlprojz", "demo.hlproj"),
            ("Session 2.hlprojz", "Session 2.hlproj"),
        ],
    )
    def test_the_unpacked_root_is_named_after_the_archive(
        self, given: str, expected: str
    ) -> None:
        assert project_root_name(given) == expected

    def test_is_archive_only_matches_the_archive_suffix(self) -> None:
        assert is_archive("demo.hlprojz")
        assert not is_archive("demo.hlproj")


class TestRoundTrip:
    """A packed project is the same project on the other side."""

    def test_the_waveform_document_survives_pack_and_unpack(
        self, loaded_clip: LoadedAudio, tmp_path: Path
    ) -> None:
        root = write_bundle(tmp_path / "demo.hlproj", loaded_clip)
        original = load_waveform_document(load_project(root))[1]

        archive = pack_project(root, tmp_path / "demo.hlprojz")
        restored_root = unpack_project(archive, tmp_path / "elsewhere")
        snapshot = load_project(restored_root)

        assert snapshot.waveform is not None
        assert snapshot.waveform.playhead == PLAYHEAD
        assert snapshot.waveform.selection == SELECTION
        assert snapshot.workspace == "waveform"

        _clip, restored, playhead, selection = load_waveform_document(snapshot)
        assert (playhead, selection) == (PLAYHEAD, SELECTION)
        np.testing.assert_allclose(
            restored.read(0, restored.n_frames),
            original.read(0, original.n_frames),
            rtol=0,
            atol=1e-6,
        )

    def test_multitrack_media_travels_inside_the_archive(
        self, loaded_clip: LoadedAudio, tmp_path: Path
    ) -> None:
        mt = MultitrackSession(
            sample_rate=loaded_clip.buffer.sample_rate,
            n_channels=loaded_clip.buffer.n_channels,
        )
        track = mt.add_track(Track(name="Drums"))
        mt.add_clip(
            track,
            MemorySampleSource(loaded_clip.buffer),
            start=0,
            duration=loaded_clip.buffer.n_frames // 2,
            name="Intro",
        )

        archive = save_project_archive(
            tmp_path / "session",
            edit_session=None,
            editor_clip=None,
            multitrack=mt,
            workspace="multitrack",
            view_mode="waveform",
            playhead=0,
            selection=None,
        )
        # The staging directory is scaffolding: only the one file is left.
        assert archive.name == "session.hlprojz"
        assert sorted(p.name for p in tmp_path.iterdir()) == ["session.hlprojz"]

        snapshot = load_project_archive(archive, tmp_path / "opened")
        assert snapshot.source_path is not None
        restored = restore_multitrack(snapshot.multitrack, snapshot.source_path)

        assert restored.tracks[0].clips[0].name == "Intro"
        np.testing.assert_allclose(
            restored.mixer.read(0, restored.n_frames),
            mt.mixer.read(0, mt.n_frames),
            rtol=0,
            atol=1e-6,
        )

    def test_markers_and_plugin_slots_come_back(
        self, loaded_clip: LoadedAudio, tmp_path: Path
    ) -> None:
        markers = MarkerList()
        markers.add_marker(1_000, "Intro", color="#ff0000")
        markers.add_region(2_000, 8_000, "Chorus")
        plugins = [{"slot": 0, "path": "/plugins/Mock.vst3", "bypass": True}]

        root = write_bundle(tmp_path / "rich.hlproj", loaded_clip, markers=markers, plugins=plugins)
        archive = pack_project(root, tmp_path / "rich.hlprojz")
        snapshot = load_project(unpack_project(archive, tmp_path / "out"))

        assert snapshot.markers == markers
        assert snapshot.plugins[0]["path"] == "/plugins/Mock.vst3"
        assert snapshot.plugins[0]["bypass"] is True

    def test_the_container_is_a_plain_zip_of_the_bundle(
        self, loaded_clip: LoadedAudio, tmp_path: Path
    ) -> None:
        root = write_bundle(tmp_path / "plain.hlproj", loaded_clip)
        archive = pack_project(root, tmp_path / "plain.hlprojz")

        names = member_names(archive)
        assert "project.json" in names
        assert "media/document.wav" in names
        assert all(not name.startswith("/") for name in names)

    def test_two_packs_of_one_tree_list_their_members_alike(
        self, loaded_clip: LoadedAudio, tmp_path: Path
    ) -> None:
        root = write_bundle(tmp_path / "stable.hlproj", loaded_clip)
        first = pack_project(root, tmp_path / "a.hlprojz")
        second = pack_project(root, tmp_path / "b.hlprojz")

        assert member_names(first) == member_names(second)

    def test_takes_recorded_into_the_bundle_are_carried_along(
        self, loaded_clip: LoadedAudio, tmp_path: Path
    ) -> None:
        root = write_bundle(tmp_path / "takes.hlproj", loaded_clip)
        (root / "takes").mkdir()
        (root / "takes" / "take-001.wav").write_bytes(b"RIFF-not-really")
        (root / "takes.json").write_text("[]", encoding="utf-8")

        archive = pack_project(root, tmp_path / "takes.hlprojz")
        restored = unpack_project(archive, tmp_path / "out")

        assert (restored / "takes" / "take-001.wav").read_bytes() == b"RIFF-not-really"
        assert (restored / "takes.json").is_file()

    def test_backup_copies_stay_behind(self, loaded_clip: LoadedAudio, tmp_path: Path) -> None:
        """``backups/`` is local undo of last resort, not part of the project."""
        root = write_bundle(tmp_path / "backed.hlproj", loaded_clip)
        write_bundle(tmp_path / "backed.hlproj", loaded_clip)  # second save leaves a backup
        assert list((root / "backups").iterdir())

        archive = pack_project(root, tmp_path / "backed.hlprojz")

        assert not any(name.startswith("backups/") for name in member_names(archive))
        assert not (unpack_project(archive, tmp_path / "out") / "backups").exists()

    def test_backups_can_be_asked_for_explicitly(
        self, loaded_clip: LoadedAudio, tmp_path: Path
    ) -> None:
        root = write_bundle(tmp_path / "kept.hlproj", loaded_clip)
        write_bundle(tmp_path / "kept.hlproj", loaded_clip)

        archive = pack_project(root, tmp_path / "kept.hlprojz", include_backups=True)

        assert any(name.startswith("backups/") for name in member_names(archive))


class TestAtomicity:
    """A crash mid-save must not cost the reader the file it already had."""

    def test_a_failed_pack_leaves_the_previous_archive_intact(
        self, loaded_clip: LoadedAudio, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = write_bundle(tmp_path / "demo.hlproj", loaded_clip)
        archive = pack_project(root, tmp_path / "demo.hlprojz")
        before = archive.read_bytes()

        written = 0

        def explode(self: zipfile.ZipFile, *args: Any, **kwargs: Any) -> None:
            nonlocal written
            written += 1
            if written > 1:
                raise OSError("no space left on device")

        monkeypatch.setattr(zipfile.ZipFile, "write", explode)
        with pytest.raises(OSError, match="no space left"):
            pack_project(root, archive)

        assert archive.read_bytes() == before

    def test_a_failed_pack_cleans_up_its_temporary(
        self, loaded_clip: LoadedAudio, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = write_bundle(tmp_path / "demo.hlproj", loaded_clip)

        def explode(self: zipfile.ZipFile, *args: Any, **kwargs: Any) -> None:
            raise OSError("disk on fire")

        monkeypatch.setattr(zipfile.ZipFile, "write", explode)
        with pytest.raises(OSError, match="disk on fire"):
            pack_project(root, tmp_path / "demo.hlprojz")

        assert not (tmp_path / "demo.hlprojz").exists()
        assert not [p for p in tmp_path.iterdir() if p.name.endswith(".part")]

    def test_the_archive_appears_only_once_it_is_complete(
        self, loaded_clip: LoadedAudio, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Readers see a rename, never a growing file at the real name."""
        root = write_bundle(tmp_path / "demo.hlproj", loaded_clip)
        target = tmp_path / "demo.hlprojz"
        seen: list[bool] = []
        real_write = zipfile.ZipFile.write

        def watch(self: zipfile.ZipFile, *args: Any, **kwargs: Any) -> None:
            seen.append(target.exists())
            real_write(self, *args, **kwargs)

        monkeypatch.setattr(zipfile.ZipFile, "write", watch)
        pack_project(root, target)

        assert seen and not any(seen)
        assert target.is_file()

    def test_a_bad_archive_does_not_replace_the_unpacked_bundle(
        self, loaded_clip: LoadedAudio, tmp_path: Path
    ) -> None:
        root = write_bundle(tmp_path / "good.hlproj", loaded_clip)
        good = pack_project(root, tmp_path / "good.hlprojz")
        existing = unpack_project(good, tmp_path / "out")
        marker = (existing / "project.json").read_text(encoding="utf-8")

        empty = tmp_path / "empty.hlprojz"
        with zipfile.ZipFile(empty, "w") as bundle:
            bundle.writestr("notes.txt", "no project here")

        with pytest.raises(ProjectArchiveError, match="no project.json"):
            unpack_project(empty, tmp_path / "out", name=existing.name, overwrite=True)

        assert (existing / "project.json").read_text(encoding="utf-8") == marker
        assert not [p for p in (tmp_path / "out").iterdir() if p.name.endswith(".part")]

    def test_unpacking_refuses_to_clobber_by_default(
        self, loaded_clip: LoadedAudio, tmp_path: Path
    ) -> None:
        root = write_bundle(tmp_path / "demo.hlproj", loaded_clip)
        archive = pack_project(root, tmp_path / "demo.hlprojz")
        unpack_project(archive, tmp_path / "out")

        with pytest.raises(ProjectArchiveError, match="refusing to overwrite"):
            unpack_project(archive, tmp_path / "out")

        replaced = unpack_project(archive, tmp_path / "out", overwrite=True)
        assert (replaced / "project.json").is_file()


class TestUntrustedArchives:
    """Member names are text from someone else's machine, not paths to obey."""

    @staticmethod
    def _archive_with(tmp_path: Path, name: str) -> Path:
        archive = tmp_path / "hostile.hlprojz"
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("project.json", '{"schema_version": 1}')
            bundle.writestr(name, "owned")
        return archive

    @pytest.mark.parametrize("name", ["../escape.txt", "media/../../escape.txt"])
    def test_a_traversing_member_is_refused(self, tmp_path: Path, name: str) -> None:
        archive = self._archive_with(tmp_path, name)

        with pytest.raises(ProjectArchiveError, match="unsafe path"):
            unpack_project(archive, tmp_path / "out")

        assert not (tmp_path / "escape.txt").exists()
        assert not (tmp_path / "out" / "hostile.hlproj").exists()

    def test_an_absolute_member_is_refused(self, tmp_path: Path) -> None:
        archive = tmp_path / "absolute.hlprojz"
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("project.json", "{}")
            info = zipfile.ZipInfo("/etc/owned.conf")
            bundle.writestr(info, "owned")

        with pytest.raises(ProjectArchiveError, match="unsafe path"):
            unpack_project(archive, tmp_path / "out")

    def test_a_symlink_member_is_refused(self, tmp_path: Path) -> None:
        archive = tmp_path / "linked.hlprojz"
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("project.json", "{}")
            info = zipfile.ZipInfo("media/passwd")
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            bundle.writestr(info, "/etc/passwd")

        with pytest.raises(ProjectArchiveError, match="symlink"):
            unpack_project(archive, tmp_path / "out")

    def test_a_corrupt_container_reports_itself(self, tmp_path: Path) -> None:
        archive = tmp_path / "shredded.hlprojz"
        archive.write_bytes(b"PK\x03\x04 and then nothing useful")

        with pytest.raises(ProjectArchiveError, match="corrupt project archive"):
            unpack_project(archive, tmp_path / "out")

    def test_a_missing_archive_reports_itself(self, tmp_path: Path) -> None:
        with pytest.raises(ProjectArchiveError, match="no such project archive"):
            unpack_project(tmp_path / "absent.hlprojz", tmp_path / "out")

    def test_packing_something_that_is_not_a_bundle_is_refused(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty.hlproj"
        empty.mkdir()

        with pytest.raises(ProjectArchiveError, match="missing project.json"):
            pack_project(empty, tmp_path / "empty.hlprojz")

        with pytest.raises(ProjectArchiveError, match="not a project directory"):
            pack_project(tmp_path / "nowhere.hlproj", tmp_path / "nowhere.hlprojz")

    @pytest.mark.skipif(os.name == "nt", reason="symlinks need a privileged account on Windows")
    def test_a_symlink_inside_a_bundle_is_left_out(
        self, loaded_clip: LoadedAudio, tmp_path: Path
    ) -> None:
        """An archive has to stand on its own wherever it is opened."""
        outside = tmp_path / "outside.wav"
        outside.write_bytes(b"not part of the project")
        root = write_bundle(tmp_path / "linked.hlproj", loaded_clip)
        (root / "media" / "elsewhere.wav").symlink_to(outside)

        archive = pack_project(root, tmp_path / "linked.hlprojz")

        assert "media/elsewhere.wav" not in member_names(archive)


class TestFileMenu:
    """The window saves and opens archives through the same session state."""

    @pytest.fixture()
    def window(self, loaded_clip: LoadedAudio, qapp: object) -> Iterator[MainWindow]:
        engine = AudioEngine(NullOutput(realtime=False), block_size=256)
        main = MainWindow(engine)
        engine.set_clip(loaded_clip)
        main._bind_edit_session(loaded_clip)  # noqa: SLF001 - mirrors open_file()
        main._update_for_clip()  # noqa: SLF001 - normally triggered by open_file()
        yield main
        main._mark_project_saved()  # noqa: SLF001 - avoid a close prompt
        main.close()

    @staticmethod
    def _answer_dialogs(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
        monkeypatch.setattr(
            main_window_module.QFileDialog,
            "getSaveFileName",
            lambda *args, **kwargs: (str(path), ""),
        )
        monkeypatch.setattr(
            main_window_module.QFileDialog,
            "getOpenFileName",
            lambda *args, **kwargs: (str(path), ""),
        )

    def test_the_archive_commands_are_in_the_file_menu(self, window: MainWindow) -> None:
        file_menu = window.menuBar().actions()[0].menu()
        texts = [main_window_module.strip_mnemonic(act.text()) for act in file_menu.actions()]

        assert "Save Project Archive As…" in texts
        assert "Open Project Archive…" in texts

    def test_save_as_archive_writes_one_file(
        self, window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "menu.hlprojz"
        self._answer_dialogs(monkeypatch, target)

        assert window.save_project_archive_as() is True

        assert target.is_file()
        assert "project.json" in member_names(target)
        assert sorted(p.name for p in tmp_path.iterdir()) == ["menu.hlprojz"]

    def test_a_plain_save_repacks_the_open_archive(
        self, window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "again.hlprojz"
        self._answer_dialogs(monkeypatch, target)
        window.save_project_archive_as()

        window.markers.add_marker(4_242, "Later")
        assert window.save_project() is True

        snapshot = load_project_archive(target, tmp_path / "read-back")
        assert [m.name for m in snapshot.markers.markers] == ["Later"]
        assert sorted(p.name for p in tmp_path.iterdir()) == ["again.hlprojz", "read-back"]

    def test_an_archive_reopens_with_its_markers_and_document(
        self, window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "trip.hlprojz"
        self._answer_dialogs(monkeypatch, target)
        window.markers.add_region(100, 900, "Verse")
        window.save_project_archive_as()
        frames = window.engine.n_frames

        window.close_clip()
        window.set_markers(MarkerList())
        window.open_project_archive_dialog()

        assert [r.name for r in window.markers.regions] == ["Verse"]
        assert window.engine.n_frames == frames
        assert window._project_path is not None  # noqa: SLF001 - scratch bundle
        assert window._project_path.is_dir()  # noqa: SLF001

    def test_opening_a_plain_file_forgets_the_archive(
        self, window: MainWindow, tmp_path: Path, wav_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "forget.hlprojz"
        self._answer_dialogs(monkeypatch, target)
        window.save_project_archive_as()
        scratch = window._project_path  # noqa: SLF001

        assert window.open_file(wav_path) is True

        assert window._archive_path is None  # noqa: SLF001
        assert scratch is not None and not scratch.exists()

    def test_the_window_is_titled_after_the_archive(
        self, window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "titled.hlprojz"
        self._answer_dialogs(monkeypatch, target)

        window.save_project_archive_as()

        assert window.windowTitle().startswith("titled ")

    def test_a_failed_archive_save_is_reported_not_raised(
        self, window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "denied.hlprojz"
        self._answer_dialogs(monkeypatch, target)
        warned: list[str] = []
        monkeypatch.setattr(
            main_window_module.QMessageBox,
            "critical",
            lambda *args, **kwargs: warned.append(str(args[2])),
        )

        def explode(*args: Any, **kwargs: Any) -> None:
            raise OSError("read-only file system")

        monkeypatch.setattr(main_window_module, "pack_project", explode)

        assert window.save_project_archive_as() is False
        assert warned and "read-only" in warned[0]
        assert not target.exists()
