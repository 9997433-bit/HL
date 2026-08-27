"""Save and load `.hlproj` directory projects (schema v1).

A project bundles the waveform editor document, optional multitrack session,
timeline markers, UI state and on-disk media copies so a session can be
reopened on another machine without chasing the original source files.

The schema stays at version 1 while it grows: readers treat every key they do
not recognise as absent, and every key added after the first release (the
top-level ``markers`` array, the top-level ``plugins`` array, the per-media
``peaks`` sidecar pointer, the multitrack ``buses`` array with its per-track
``send_to_bus`` pointer, the per-track ``automation`` envelopes and the ``ui``
section's ``layout`` object, so far) is written only when it carries something,
so a bundle saved by this build still opens in one that predates the addition.

The ``layout`` object under ``ui`` holds the dock arrangement: the base64 of
:meth:`QMainWindow.saveState` and :meth:`QMainWindow.saveGeometry` plus a
``docks`` map of object name to visibility. The store never interprets the two
blobs — they are Qt's own versioned format — but it does insist they decode as
base64, so a truncated one is dropped here rather than at the window that would
have fed it to ``restoreState``. The ``docks`` map is the part a future reader
can still act on if Qt ever refuses the blob.

Automation is stored as ``{"gain_db": [[frame, value], ...]}`` under a track's
``automation`` key: compact pairs rather than named objects, because a ridden
fader can run to thousands of breakpoints and the array is read back
positionally either way.

The ``plugins`` array records which VST3 bundle sits in which slot of the plugin
rack: the path, the bypass flag, and — when the host could produce one — an
optional ``state`` key holding a base64-encoded opaque blob (the backend's
native state chunk when it has one, a parameter-dict JSON fallback otherwise;
see :meth:`audio_studio.plugins.host.PluginHost.state_blob`). The store treats
the blob as ballast: it validates that the string decodes as base64 and carries
it, and applying it back to a live plugin is the panel's best-effort job. The
bundles themselves are properties of the machine rather than of the project, so
a section that cannot be honoured (plugin uninstalled, no ``plugins`` extra
here, a state blob the plugin no longer understands) is the UI's problem to
report, not a reason to refuse the bundle.
"""

from __future__ import annotations

import base64
import binascii
import json
import shutil
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from .. import __app_name__, __version__
from ..core import peaks_cache
from ..core.edit_session import EditSession
from ..core.loader import LoadedAudio, load_audio, save_audio
from ..core.markers import MarkerList
from ..core.peaks import PeakPyramid
from ..core.sample_source import MemorySampleSource, SampleSource
from ..core.session import Bus, GainAutomation, MultitrackSession, Track
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
class LayoutState:
    """The dock arrangement of a main window, as the bundle carries it.

    ``window_state`` and ``geometry`` are base64 of the opaque blobs Qt's
    ``saveState``/``saveGeometry`` produce; ``docks`` maps a dock's object name
    to whether it was on screen. The map is redundant with the blob when Qt
    accepts the blob, and is the only thing left when it does not — a state
    written by a newer Qt, say, which ``restoreState`` refuses outright.
    """

    window_state: str | None = None
    geometry: str | None = None
    docks: dict[str, bool] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not (self.window_state or self.geometry or self.docks)

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.window_state:
            payload["window_state"] = self.window_state
        if self.geometry:
            payload["geometry"] = self.geometry
        if self.docks:
            payload["docks"] = {str(name): bool(shown) for name, shown in self.docks.items()}
        return payload

    @classmethod
    def from_json(cls, raw: Any) -> LayoutState:
        """Read a ``layout`` object back, dropping anything unusable.

        A layout is a convenience, never the point of a project, so a blob
        that is not base64 or a ``docks`` entry that is not a name/flag pair
        costs only itself: the bundle still opens, at the window's defaults.
        """
        if not isinstance(raw, Mapping):
            return cls()
        docks_raw = raw.get("docks")
        docks: dict[str, bool] = {}
        if isinstance(docks_raw, Mapping):
            for name, shown in docks_raw.items():
                key = str(name).strip()
                if key:
                    docks[key] = bool(shown)
        return cls(
            window_state=_base64_or_none(raw.get("window_state")),
            geometry=_base64_or_none(raw.get("geometry")),
            docks=docks,
        )


@dataclass(slots=True)
class ProjectSnapshot:
    """Everything the UI needs to round-trip a working session."""

    waveform: WaveformState | None
    multitrack: dict[str, Any]
    workspace: str = "waveform"
    view_mode: str = "split"
    source_path: Path | None = None
    markers: MarkerList = field(default_factory=MarkerList)
    plugins: list[dict[str, Any]] = field(default_factory=list)
    layout: LayoutState = field(default_factory=LayoutState)


def _time_range_to_json(rng: TimeRange | None) -> dict[str, int] | None:
    if rng is None or rng.is_empty:
        return None
    return {"start": int(rng.start), "end": int(rng.end)}


def _time_range_from_json(data: dict[str, int] | None) -> TimeRange | None:
    if not data:
        return None
    return TimeRange(int(data["start"]), int(data["end"]))


def _base64_or_none(value: Any) -> str | None:
    """``value`` as the base64 string the bundle stores, or ``None`` to omit it.

    The store never decodes the blobs it carries into anything meaningful —
    they belong to a plugin or to Qt — but it does insist each string is
    base64, so a truncated or hand-edited value is dropped at the boundary
    instead of being carried around until something chokes on it.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        base64.b64decode(text, validate=True)
    except (binascii.Error, ValueError):
        return None
    return text


def _plugins_to_json(entries: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Normalise the plugin rack for the bundle: one entry per loaded slot.

    Entries without a path carry nothing a reader could act on and are dropped;
    ``bypass`` is written only when it is set and ``state`` only when it holds a
    valid base64 blob, so the common case serialises the way it did before
    either key was recorded.
    """
    out: list[dict[str, Any]] = []
    for entry in entries:
        path = str(entry.get("path", "")).strip()
        if not path:
            continue
        item: dict[str, Any] = {"slot": int(entry.get("slot", len(out))), "path": path}
        if entry.get("bypass"):
            item["bypass"] = True
        state = _base64_or_none(entry.get("state"))
        if state is not None:
            item["state"] = state
        out.append(item)
    return out


def _plugins_from_json(raw: Any) -> list[dict[str, Any]]:
    """Read the ``plugins`` array back, skipping anything unusable.

    A malformed plugin entry is not worth refusing a project over: the audio,
    the arrangement and the markers are all still there, and the rack simply
    comes back with one slot fewer. A malformed ``state`` value costs only
    itself — the plugin still loads, at its own defaults.
    """
    if not isinstance(raw, list):
        return []
    entries: list[dict[str, Any]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        path = str(item.get("path", "")).strip()
        if not path:
            continue
        try:
            slot = int(item.get("slot", index))
        except (TypeError, ValueError):
            slot = index
        entry: dict[str, Any] = {
            "slot": slot,
            "path": path,
            "bypass": bool(item.get("bypass", False)),
        }
        state = _base64_or_none(item.get("state"))
        if state is not None:
            entry["state"] = state
        entries.append(entry)
    entries.sort(key=lambda entry: entry["slot"])
    return entries


def _automation_from_json(raw: Any) -> GainAutomation:
    """Read a track's ``automation`` section back into a gain envelope.

    The section is keyed by parameter name so a later release can automate pan
    or a send without moving the ones already written; a bundle that predates
    automation, or one whose section holds a parameter this build does not know
    about, simply comes back with an empty curve and a live fader.
    """
    if not isinstance(raw, Mapping):
        return GainAutomation()
    return GainAutomation.from_json(raw.get("gain_db"))


def _write_wav(path: Path, source: SampleSource) -> np.ndarray:
    """Copy ``source`` into the bundle and hand back the frames written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n_frames = int(source.n_frames)
    data = (
        source.read(0, n_frames)
        if n_frames > 0
        else np.zeros((0, source.n_channels), dtype=np.float32)
    )
    save_audio(path, AudioBuffer(data, source.sample_rate))
    return data


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
        plugins: Sequence[Mapping[str, Any]] | None = None,
        layout: LayoutState | None = None,
    ) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.media_dir.mkdir(parents=True, exist_ok=True)
        (self.root / BACKUPS_DIR).mkdir(parents=True, exist_ok=True)

        if self.json_path.is_file():
            stamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
            backup = self.root / BACKUPS_DIR / f"project.json.{stamp}"
            shutil.copy2(self.json_path, backup)

        ui: dict[str, Any] = {"workspace": workspace, "view_mode": view_mode}
        if layout is not None and not layout.is_empty:
            ui["layout"] = layout.to_json()
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "app": __app_name__,
            "app_version": __version__,
            "saved_at": datetime.now(tz=UTC).isoformat(),
            "ui": ui,
            "waveform": None,
            "multitrack": self._serialize_multitrack(multitrack),
        }
        if markers is not None and not markers.is_empty:
            payload["markers"] = markers.to_json()
        plugin_entries = _plugins_to_json(plugins or [])
        if plugin_entries:
            payload["plugins"] = plugin_entries

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
            plugins=_plugins_from_json(payload.get("plugins")),
            layout=LayoutState.from_json(ui.get("layout")),
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
                    samples = _write_wav(self.root / rel, clip.source)
                    media_index[key] = media_id
                    entry: dict[str, Any] = {
                        "id": media_id,
                        "path": rel,
                        "sample_rate": int(clip.source.sample_rate),
                        "channels": int(clip.source.n_channels),
                        "frames": int(clip.source.n_frames),
                    }
                    peaks_rel = self._write_peaks(rel, samples)
                    if peaks_rel is not None:
                        entry["peaks"] = peaks_rel
                    media_items.append(entry)
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
            track_json: dict[str, Any] = {
                "id": track.track_id,
                "name": track.name,
                "gain_db": float(track.gain_db),
                "pan": float(track.pan),
                "mute": bool(track.mute),
                "solo": bool(track.solo),
                "clips": clips_json,
            }
            # Only routed tracks carry the key, so an unrouted arrangement
            # serializes byte-for-byte the way it did before buses existed.
            if track.send_to_bus:
                track_json["send_to_bus"] = str(track.send_to_bus)
            if track.has_automation:
                track_json["automation"] = {"gain_db": track.automation.to_json()}
            tracks_json.append(track_json)

        payload: dict[str, Any] = {
            "sample_rate": int(session.sample_rate),
            "channels": int(session.n_channels),
            "master_gain_db": float(session.master.gain_db),
            "media": media_items,
            "tracks": tracks_json,
        }
        if session.n_buses:
            payload["buses"] = [
                {
                    "id": bus.bus_id,
                    "name": bus.name,
                    "gain_db": float(bus.gain_db),
                    "mute": bool(bus.mute),
                }
                for bus in session.buses
            ]
        return payload

    def _write_peaks(self, media_rel: str, samples: np.ndarray) -> str | None:
        """Cache the waveform overview beside a media copy.

        The returned bundle-relative path goes into the media entry as the
        optional ``peaks`` key; a reader that predates it ignores the key, and
        a reader that knows it still has to cope with the file being absent,
        because peak caching can be switched off at save time.
        """
        if not peaks_cache.cache_enabled() or samples.shape[0] == 0:
            return None
        media_path = self.root / media_rel
        peaks_rel = f"{media_rel}{peaks_cache.SUFFIX}"
        written = peaks_cache.write(
            media_path, PeakPyramid(samples), cache_path=self.root / peaks_rel
        )
        return peaks_rel if written is not None else None


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
    plugins: Sequence[Mapping[str, Any]] | None = None,
    layout: LayoutState | None = None,
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
        plugins=plugins,
        layout=layout,
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

    # Buses come back before the tracks that send to them so a restored send
    # always resolves; a bundle written before buses existed simply has none.
    for bus_data in data.get("buses", []):
        session.add_bus(
            Bus(
                bus_id=str(bus_data["id"]),
                name=str(bus_data.get("name", "Bus")),
                gain_db=float(bus_data.get("gain_db", 0.0)),
                mute=bool(bus_data.get("mute", False)),
            )
        )

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
        send_to = track_data.get("send_to_bus")
        track = session.add_track(
            Track(
                name=str(track_data.get("name", "Track")),
                track_id=str(track_data["id"]),
                gain_db=float(track_data.get("gain_db", 0.0)),
                pan=float(track_data.get("pan", 0.0)),
                mute=bool(track_data.get("mute", False)),
                solo=bool(track_data.get("solo", False)),
                send_to_bus=str(send_to) if send_to else None,
                automation=_automation_from_json(track_data.get("automation")),
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


def load_media_pyramid(
    entry: dict[str, Any],
    project_root: Path,
    *,
    samples: np.ndarray | None = None,
) -> PeakPyramid | None:
    """Waveform overview for one media entry, or ``None`` when it is not cached.

    Bundles written before the optional ``peaks`` key, and bundles saved with
    peak caching disabled, simply have no overview to restore; the caller then
    builds one from the samples as it always did.
    """
    media_rel = entry.get("path")
    if not media_rel:
        return None
    peaks_rel = entry.get("peaks") or f"{media_rel}{peaks_cache.SUFFIX}"
    return peaks_cache.read(
        project_root / str(media_rel),
        samples=samples,
        cache_path=project_root / str(peaks_rel),
    )


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
