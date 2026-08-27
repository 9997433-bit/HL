"""Pack and unpack `.hlprojz` single-file project archives.

A ``.hlproj`` bundle is a directory: convenient for the application, awkward to
mail, attach to a ticket or drop on a share. A ``.hlprojz`` is exactly that
directory stored in a zip container, so the two representations carry the same
``project.json``, the same ``media/`` copies and the same take registry, and
nothing about the schema changes when a session travels as one file.

Both directions are atomic in the sense that matters after a crash or a full
disk: a pack writes the container beside its destination and renames it into
place only once the last member is written, and an unpack extracts into a
sibling staging directory and renames the finished tree, so a reader never
observes a half-written archive or a half-extracted bundle at the real path.
The rename is what provides this, which is why both temporaries are created in
the destination's own directory rather than in the system temp dir — a rename
across filesystems is a copy, and a copy is not atomic.

``backups/`` is deliberately left out of the container. Those are timestamped
copies of ``project.json`` that the store keeps as local undo of last resort;
they grow with every save and mean nothing on the machine the archive lands on.
Everything else in the bundle, including anything a future schema adds, is
copied verbatim.
"""

from __future__ import annotations

import os
import shutil
import stat
import tempfile
import zipfile
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

from ..core.edit_session import EditSession
from ..core.loader import LoadedAudio
from ..core.markers import MarkerList
from ..core.session import MultitrackSession
from ..core.types import TimeRange
from .store import (
    BACKUPS_DIR,
    PROJECT_JSON,
    ProjectLoadError,
    ProjectSnapshot,
    load_project,
    save_project,
)

ARCHIVE_SUFFIX = ".hlprojz"
PROJECT_SUFFIX = ".hlproj"

#: Bundle-relative directories that never travel inside an archive.
EXCLUDED_DIRS = frozenset({BACKUPS_DIR})


class ProjectArchiveError(ProjectLoadError):
    """Raised when a ``.hlprojz`` archive cannot be written, read or trusted.

    It derives from :class:`~audio_studio.project.store.ProjectLoadError` so
    the UI's existing "cannot open project" handling covers archives too.
    """


def archive_path_for(path: str | Path) -> Path:
    """``path`` with the ``.hlprojz`` suffix, whatever it arrived with."""
    candidate = Path(path)
    if candidate.suffix.lower() == ARCHIVE_SUFFIX:
        return candidate
    if candidate.suffix.lower() == PROJECT_SUFFIX:
        return candidate.with_suffix(ARCHIVE_SUFFIX)
    return candidate.with_name(candidate.name + ARCHIVE_SUFFIX)


def project_root_name(archive: str | Path) -> str:
    """Directory name an archive unpacks to: ``demo.hlprojz`` → ``demo.hlproj``."""
    stem = Path(archive).name
    if stem.lower().endswith(ARCHIVE_SUFFIX):
        stem = stem[: -len(ARCHIVE_SUFFIX)]
    if stem.lower().endswith(PROJECT_SUFFIX):
        stem = stem[: -len(PROJECT_SUFFIX)]
    return f"{stem or 'project'}{PROJECT_SUFFIX}"


def is_archive(path: str | Path) -> bool:
    return Path(path).suffix.lower() == ARCHIVE_SUFFIX


def _bundle_members(root: Path, *, include_backups: bool) -> Iterator[tuple[Path, str]]:
    """Yield ``(absolute path, archive name)`` for every file in the bundle.

    Walked in sorted order so two packs of the same tree lay their members out
    the same way, which makes archives diffable and comparable in tests.
    """
    for dirpath, dirnames, filenames in os.walk(root):
        here = Path(dirpath)
        rel_dir = here.relative_to(root)
        if not include_backups and rel_dir == Path(".") and BACKUPS_DIR in dirnames:
            dirnames.remove(BACKUPS_DIR)
        dirnames.sort()
        for name in sorted(filenames):
            source = here / name
            if source.is_symlink() or not source.is_file():
                # A symlink points outside the bundle as often as not, and the
                # archive has to stand on its own on another machine.
                continue
            yield source, (rel_dir / name).as_posix()


def pack_project(
    root: str | Path,
    archive: str | Path,
    *,
    include_backups: bool = False,
    compresslevel: int = 6,
) -> Path:
    """Store the ``.hlproj`` directory ``root`` as the archive ``archive``.

    Returns the archive path actually written (the suffix is normalised). The
    destination is replaced only after the container is complete and flushed.
    """
    source = Path(root).expanduser()
    if not source.is_dir():
        raise ProjectArchiveError(f"not a project directory: {source}")
    if not (source / PROJECT_JSON).is_file():
        raise ProjectArchiveError(f"missing {PROJECT_JSON} in {source}")

    target = archive_path_for(archive).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)

    handle, temp_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".part", dir=target.parent
    )
    os.close(handle)
    temp = Path(temp_name)
    try:
        with zipfile.ZipFile(
            temp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=compresslevel
        ) as bundle:
            for path, name in _bundle_members(source, include_backups=include_backups):
                bundle.write(path, name)
        os.replace(temp, target)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise
    return target


def _safe_member_path(name: str) -> PurePosixPath:
    """Validate one archive member name and return it as a relative path.

    Zip member names are attacker-controlled text, not filesystem paths: an
    absolute name or one containing ``..`` would let an archive write outside
    the directory it is being extracted into. Refuse the whole archive rather
    than silently skipping the member, because a bundle missing a piece is not
    the project someone meant to open.
    """
    candidate = PurePosixPath(name)
    if candidate.is_absolute() or name.startswith("/") or "\\" in name:
        raise ProjectArchiveError(f"unsafe path in archive: {name!r}")
    parts = [part for part in candidate.parts if part not in (".",)]
    if any(part == ".." for part in parts):
        raise ProjectArchiveError(f"unsafe path in archive: {name!r}")
    if not parts:
        raise ProjectArchiveError(f"unsafe path in archive: {name!r}")
    return PurePosixPath(*parts)


def _extract_all(bundle: zipfile.ZipFile, destination: Path) -> None:
    for info in bundle.infolist():
        if info.is_dir():
            (destination / _safe_member_path(info.filename)).mkdir(parents=True, exist_ok=True)
            continue
        mode = info.external_attr >> 16
        if mode and stat.S_ISLNK(mode):
            raise ProjectArchiveError(f"symlink in archive: {info.filename!r}")
        rel = _safe_member_path(info.filename)
        out = destination / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        with bundle.open(info) as src, out.open("wb") as dst:
            shutil.copyfileobj(src, dst)


def unpack_project(
    archive: str | Path,
    destination: str | Path,
    *,
    name: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Extract ``archive`` into ``destination`` and return the ``.hlproj`` root.

    The root is named after the archive (``demo.hlprojz`` → ``demo.hlproj``)
    unless ``name`` says otherwise. An existing root is left alone unless
    ``overwrite`` is set, in which case it is replaced only once the new tree
    is fully extracted.
    """
    source = Path(archive).expanduser()
    if not source.is_file():
        raise ProjectArchiveError(f"no such project archive: {source}")

    parent = Path(destination).expanduser()
    parent.mkdir(parents=True, exist_ok=True)
    root = parent / (name or project_root_name(source))
    if root.exists() and not overwrite:
        raise ProjectArchiveError(f"refusing to overwrite {root}")

    staging = Path(tempfile.mkdtemp(prefix=f".{root.name}.", suffix=".part", dir=parent))
    try:
        try:
            with zipfile.ZipFile(source) as bundle:
                _extract_all(bundle, staging)
        except zipfile.BadZipFile as exc:
            raise ProjectArchiveError(f"corrupt project archive {source}: {exc}") from exc
        if not (staging / PROJECT_JSON).is_file():
            raise ProjectArchiveError(f"archive has no {PROJECT_JSON}: {source}")
        if root.exists():
            shutil.rmtree(root)
        os.replace(staging, root)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return root


def save_project_archive(
    path: str | Path,
    *,
    edit_session: EditSession | None,
    editor_clip: LoadedAudio | None,
    multitrack: MultitrackSession,
    workspace: str,
    view_mode: str,
    playhead: int,
    selection: TimeRange | None,
    markers: MarkerList | None = None,
    plugins: Sequence[Mapping[str, Any]] | None = None,
    work_dir: str | Path | None = None,
) -> Path:
    """Write a session straight to a ``.hlprojz`` archive.

    The bundle is staged as a real directory first — the store only knows how
    to write directories, and media copies have to exist as files before they
    can be compressed — then packed. The staging directory defaults to a
    temporary one beside the archive and is removed afterwards; pass
    ``work_dir`` to keep the expanded bundle (the application does, so that a
    later plain save can rewrite it without unpacking again).
    """
    target = archive_path_for(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    root_name = project_root_name(target)

    staging: Path | None = None
    if work_dir is None:
        staging = Path(
            tempfile.mkdtemp(prefix=f".{target.name}.", suffix=".work", dir=target.parent)
        )
        work_root = staging / root_name
    else:
        work_root = Path(work_dir).expanduser()
        if work_root.suffix.lower() != PROJECT_SUFFIX:
            work_root = work_root / root_name

    try:
        saved = save_project(
            work_root,
            edit_session=edit_session,
            editor_clip=editor_clip,
            multitrack=multitrack,
            workspace=workspace,
            view_mode=view_mode,
            playhead=playhead,
            selection=selection,
            markers=markers,
            plugins=plugins,
        )
        return pack_project(saved, target)
    finally:
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)


def load_project_archive(
    archive: str | Path,
    destination: str | Path,
    *,
    name: str | None = None,
    overwrite: bool = False,
) -> ProjectSnapshot:
    """Unpack ``archive`` under ``destination`` and load the bundle inside it.

    The returned snapshot carries the extracted directory in
    :attr:`~audio_studio.project.store.ProjectSnapshot.source_path`, which is
    where its media lives: the caller has to keep that directory around for as
    long as the project is open.
    """
    root = unpack_project(archive, destination, name=name, overwrite=overwrite)
    return load_project(root)
