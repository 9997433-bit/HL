"""Save and load `.hlproj` directory projects (schema v1).

A project bundles the waveform editor document, optional multitrack session,
timeline markers, UI state and on-disk media copies so a session can be
reopened on another machine without chasing the original source files.

The schema stays at version 1 while it grows: readers treat every top-level key
they do not recognise as absent, and every key added after the first release
(``markers``, so far) is written only when it carries something, so a bundle
saved by this build still opens in one that predates the addition.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from .. import __app_name__, __version__
from ..core.edit_session import EditSession
from ..core.loader import LoadedAudio, load_audio, save_audio
from ..core.markers import MarkerList
from ..core.sample_source import MemorySampleSource, SampleSource
from ..core.session import MultitrackSession, Track
from ..core.types import AudioBuffer, TimeRange

SCHEMA_VERSION = 1
PROJECT_JSON = "project.json"
MEDIA_DIR = "media"
BACKUPS_DIR = "backups"


class ProjectLoadError(RuntimeError):
    """Raised when a project bundle cannot be read or validated."""


@dataclass(slots=True)
class WaveformState:
    """Serializable waveform-editor snapshot."""

    source_name: str
    source_media: str
    document_media: str
    playhead: int = 0
    selection: TimeRange | None = None


@dataclass(slots=True)
class ProjectSnapshot:
    """Everything the UI needs to round-trip a working session."""

    waveform: WaveformState | None
    multitrack: dict[str, Any]
    workspace: str = "waveform"
    view_mode: str = "split"
    source_path: Path | None = None
    markers: MarkerList = field(default_factory=MarkerList)


def _time_range_to_json(rng: TimeRange | None) -> dict[str, int] | None:
    if rng is None or rng.is_empty:
        return None
    return {"start": int(rng.start), "end": int(rng.end)}


def _time_range_from_json(data: dict[str, int] | None) -> TimeRange | None:
    if not data:
        return None
    return TimeRange(int(data["start"]), int(data["end"]))


def _write_wav(path: Path, source: SampleSource) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    n_frames = int(source.n_frames)
    if n_frames <= 0:
        save_audio(
            path,
            AudioBuffer(
                np.zeros((0, source.n_channels), dtype=np.float32),
                source.sample_rate,
            ),
        )
        return
    data = source.read(0, n_frames)
    save_audio(path, AudioBuffer(data, source.sample_rate))


def _source_key(source: SampleSource) -> str:
    return f"{type(source).__name__}:{id(source)}"


class ProjectStore:
    """Read/write a single ``.hlproj`` directory."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.media_dir = self.root / MEDIA_DIR
        self.json_path = self.root / PROJECT_JSON

    def save(
        self,
        *,
        edit_session: EditSession | None,
        editor_clip: LoadedAudio | None,
        multitrack: MultitrackSession,
        workspace: str,
        view_mode: str,
        playhead: int,
        selection: TimeRange | None,
        markers: MarkerList | None = None,
    ) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.media_dir.mkdir(parents=True, exist_ok=True)
        (self.root / BACKUPS_DIR).mkdir(parents=True, exist_ok=True)

        if self.json_path.is_file():
            stamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
            backup = self.root / BACKUPS_DIR / f"project.json.{stamp}"
            shutil.copy2(self.json_path, backup)

        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "app": __app_name__,
            "app_version": __version__,
            "saved_at": datetime.now(tz=UTC).isoformat(),
            "ui": {"workspace": workspace, "view_mode": view_mode},
            "waveform": None,
            "multitrack": self._serialize_multitrack(multitrack),
        }
        if markers is not None and not markers.is_empty:
            payload["markers"] = markers.to_json()

        if edit_session is not None and editor_clip is not None:
            source_rel = "media/source.wav"
            document_rel = "media/document.wav"
            _write_wav(self.root / source_rel, MemorySampleSource(editor_clip.buffer))
            _write_wav(self.root / document_rel, edit_session)
            payload["waveform"] = {
                "source_name": editor_clip.name,
                "source_media": source_rel,
                "document_media": document_rel,
                "playhead": int(playhead),
                "selection": _time_range_to_json(selection),
            }

        temp = self.json_path.with_suffix(".json.tmp")
        temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp.replace(self.json_path)

    def load(self) -> ProjectSnapshot:
        if not self.json_path.is_file():
            raise ProjectLoadError(f"missing {PROJECT_JSON} in {self.root}")
        try:
            payload = json.loads(self.json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ProjectLoadError(f"invalid JSON in {self.json_path}") from exc

        if payload.get("schema_version") != SCHEMA_VERSION:
            raise ProjectLoadError(
                f"unsupported schema_version {payload.get('schema_version')!r}"
            )

        waveform = None
        raw_wave = payload.get("waveform")
        if raw_wave:
            waveform = WaveformState(
                source_name=str(raw_wave["source_name"]),
                source_media=str(raw_wave["source_media"]),
                document_media=str(raw_wave["document_media"]),
                playhead=int(raw_wave.get("playhead", 0)),
                selection=_time_range_from_json(raw_wave.get("selection")),
            )

        try:
            markers = MarkerList.from_json(payload.get("markers"))
        except (KeyError, TypeError, ValueError) as exc:
            raise ProjectLoadError(f"invalid markers in {self.json_path}: {exc}") from exc

        ui = payload.get("ui") or {}
        return ProjectSnapshot(
            waveform=waveform,
            multitrack=payload.get("multitrack") or {},
            workspace=str(ui.get("workspace", "waveform")),
            view_mode=str(ui.get("view_mode", "split")),
            source_path=self.root,
            markers=markers,
        )

    def _serialize_multitrack(self, session: MultitrackSession) -> dict[str, Any]:
        media_index: dict[str, str] = {}
        media_items: list[dict[str, Any]] = []
        tracks_json: list[dict[str, Any]] = []

        for track in session.tracks:
            clips_json: list[dict[str, Any]] = []
            for clip in track.clips:
                key = _source_key(clip.source)
                if key not in media_index:
                    media_id = f"med_{len(media_items) + 1:04d}"
                    rel = f"media/{media_id}.wav"
                    _write_wav(self.root / rel, clip.source)
                    media_index[key] = media_id
                    media_items.append(
                        {
                            "id": media_id,
                            "path": rel,
                            "sample_rate": int(clip.source.sample_rate),
                            "channels": int(clip.source.n_channels),
                            "frames": int(clip.source.n_frames),
                        }
                    )
                clips_json.append(
                    {
                        "id": clip.clip_id,
                        "media": media_index[key],
                        "name": clip.name,
                        "start": int(clip.start),
                        "duration": int(clip.duration),
                        "offset": int(clip.offset),
                        "gain_db": float(clip.gain_db),
                        "fade_in": int(clip.fade_in),
                        "fade_out": int(clip.fade_out),
                    }
                )
            tracks_json.append(
                {
                    "id": track.track_id,
                    "name": track.name,
                    "gain_db": float(track.gain_db),
                    "pan": float(track.pan),
                    "mute": bool(track.mute),
                    "solo": bool(track.solo),
                    "clips": clips_json,
                }
            )

        return {
            "sample_rate": int(session.sample_rate),
            "channels": int(session.n_channels),
            "master_gain_db": float(session.master.gain_db),
            "media": media_items,
            "tracks": tracks_json,
        }


def save_project(
    path: Path,
    *,
    edit_session: EditSession | None,
    editor_clip: LoadedAudio | None,
    multitrack: MultitrackSession,
    workspace: str,
    view_mode: str,
    playhead: int,
    selection: TimeRange | None,
    markers: MarkerList | None = None,
) -> Path:
    """Write a project bundle and return the normalized directory path."""
    root = path
    if root.suffix.lower() != ".hlproj":
        root = root.with_suffix(".hlproj")
    ProjectStore(root).save(
        edit_session=edit_session,
        editor_clip=editor_clip,
        multitrack=multitrack,
        workspace=workspace,
        view_mode=view_mode,
        playhead=playhead,
        selection=selection,
        markers=markers,
    )
    return root


def load_project(path: Path) -> ProjectSnapshot:
    root = path
    if root.suffix.lower() != ".hlproj":
        root = root.with_suffix(".hlproj")
    return ProjectStore(root).load()


def restore_multitrack(data: dict[str, Any], project_root: Path) -> MultitrackSession:
    """Rebuild a :class:`MultitrackSession` from serialized project JSON."""
    session = MultitrackSession(
        sample_rate=int(data.get("sample_rate", 48_000)),
        n_channels=int(data.get("channels", 2)),
    )
    session.master.gain_db = float(data.get("master_gain_db", 0.0))

    media_by_id = {item["id"]: item for item in data.get("media", [])}
    source_cache: dict[str, MemorySampleSource] = {}

    def source_for(media_id: str) -> MemorySampleSource:
        if media_id not in source_cache:
            entry = media_by_id.get(media_id)
            if entry is None:
                raise ProjectLoadError(f"unknown media id {media_id!r}")
            loaded = load_audio(project_root / entry["path"])
            source_cache[media_id] = MemorySampleSource(loaded.buffer)
        return source_cache[media_id]

    for track_data in data.get("tracks", []):
        track = session.add_track(
            Track(
                name=str(track_data.get("name", "Track")),
                track_id=str(track_data["id"]),
                gain_db=float(track_data.get("gain_db", 0.0)),
                pan=float(track_data.get("pan", 0.0)),
                mute=bool(track_data.get("mute", False)),
                solo=bool(track_data.get("solo", False)),
            )
        )
        for clip_data in track_data.get("clips", []):
            session.add_clip(
                track,
                source_for(str(clip_data["media"])),
                start=int(clip_data.get("start", 0)),
                duration=int(clip_data["duration"]),
                offset=int(clip_data.get("offset", 0)),
                gain_db=float(clip_data.get("gain_db", 0.0)),
                fade_in=int(clip_data.get("fade_in", 0)),
                fade_out=int(clip_data.get("fade_out", 0)),
                name=str(clip_data.get("name", "")),
            )
    return session


def load_waveform_document(
    snapshot: ProjectSnapshot,
) -> tuple[LoadedAudio, EditSession, int, TimeRange | None]:
    """Load the edited waveform document from a project snapshot."""
    if snapshot.waveform is None or snapshot.source_path is None:
        raise ProjectLoadError("project has no waveform editor state")
    root = snapshot.source_path
    wf = snapshot.waveform
    document_path = root / wf.document_media
    if not document_path.is_file():
        raise ProjectLoadError(f"missing document media {document_path}")
    loaded = load_audio(document_path)
    source_path = Path(wf.source_name)
    if not source_path.is_absolute():
        source_path = root / wf.source_name
    clip = LoadedAudio(
        buffer=loaded.buffer,
        audio_format=loaded.audio_format,
        path=source_path,
    )
    session = EditSession.from_buffer(loaded.buffer)
    session.undo_stack.set_clean()
    return clip, session, wf.playhead, wf.selection
