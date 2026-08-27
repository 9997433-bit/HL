"""Round-trip tests for .hlproj project bundles."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from audio_studio.core.edit_session import EditSession
from audio_studio.core.loader import LoadedAudio, load_audio
from audio_studio.core.markers import MarkerList
from audio_studio.core.sample_source import MemorySampleSource
from audio_studio.core.session import MultitrackSession, Track
from audio_studio.core.types import TimeRange
from audio_studio.plugins import PluginEffectAdapter, PluginHost
from audio_studio.project.store import (
    ProjectLoadError,
    load_project,
    load_waveform_document,
    restore_multitrack,
    save_project,
)


def test_save_load_waveform_roundtrip(loaded_clip: LoadedAudio, tmp_path: Path) -> None:
    session = EditSession.from_buffer(loaded_clip.buffer)
    session.delete(TimeRange(0, 500))

    root = tmp_path / "demo.hlproj"
    save_project(
        root,
        edit_session=session,
        editor_clip=loaded_clip,
        multitrack=MultitrackSession(sample_rate=loaded_clip.buffer.sample_rate),
        workspace="waveform",
        view_mode="split",
        playhead=1_000,
        selection=TimeRange(200, 800),
    )

    snapshot = load_project(root)
    assert snapshot.workspace == "waveform"
    assert snapshot.view_mode == "split"
    assert snapshot.waveform is not None
    assert snapshot.waveform.playhead == 1_000
    assert snapshot.waveform.selection == TimeRange(200, 800)

    clip, restored, playhead, selection = load_waveform_document(snapshot)
    assert playhead == 1_000
    assert selection == TimeRange(200, 800)
    assert restored.n_frames == session.n_frames
    assert restored.n_channels == session.n_channels
    np.testing.assert_allclose(
        restored.read(0, restored.n_frames),
        session.read(0, session.n_frames),
        rtol=0,
        atol=1e-6,
    )
    assert (root / "media" / "document.wav").is_file()
    assert (root / "media" / "source.wav").is_file()
    assert snapshot.waveform is not None
    assert snapshot.waveform.source_name == loaded_clip.name


def test_save_load_multitrack_roundtrip(loaded_clip: LoadedAudio, tmp_path: Path) -> None:
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
    mt.master.gain_db = -3.0

    root = tmp_path / "session.hlproj"
    save_project(
        root,
        edit_session=None,
        editor_clip=None,
        multitrack=mt,
        workspace="multitrack",
        view_mode="waveform",
        playhead=0,
        selection=None,
    )

    snapshot = load_project(root)
    restored = restore_multitrack(snapshot.multitrack, root)
    assert restored.n_tracks == 1
    assert restored.tracks[0].name == "Drums"
    assert restored.tracks[0].clips[0].name == "Intro"
    assert restored.master.gain_db == pytest.approx(-3.0)
    assert restored.n_frames == mt.n_frames

    mixed = restored.mixer.read(0, restored.n_frames)
    expected = mt.mixer.read(0, mt.n_frames)
    np.testing.assert_allclose(mixed, expected, rtol=0, atol=1e-6)


def test_load_rejects_unknown_schema(tmp_path: Path) -> None:
    root = tmp_path / "bad.hlproj"
    root.mkdir()
    (root / "project.json").write_text('{"schema_version": 99}', encoding="utf-8")
    with pytest.raises(ProjectLoadError, match="unsupported schema_version"):
        load_project(root)


class TestMarkerPersistence:
    """Markers ride along with the waveform state, without moving the schema."""

    @staticmethod
    def _save(
        root: Path, clip: LoadedAudio, markers: MarkerList | None
    ) -> None:
        save_project(
            root,
            edit_session=EditSession.from_buffer(clip.buffer),
            editor_clip=clip,
            multitrack=MultitrackSession(sample_rate=clip.buffer.sample_rate),
            workspace="waveform",
            view_mode="split",
            playhead=0,
            selection=None,
            markers=markers,
        )

    def test_markers_and_regions_survive_a_round_trip(
        self, loaded_clip: LoadedAudio, tmp_path: Path
    ) -> None:
        markers = MarkerList()
        markers.add_marker(1_000, "Intro", color="#ff0000")
        markers.add_marker(44_100, "Verse")
        markers.add_region(2_000, 8_000, "Chorus")

        root = tmp_path / "marked.hlproj"
        self._save(root, loaded_clip, markers)
        restored = load_project(root).markers

        assert restored == markers
        assert [m.name for m in restored.markers] == ["Intro", "Verse"]
        assert restored.markers[0].color == "#ff0000"
        assert restored.regions[0].range == TimeRange(2_000, 8_000)

    def test_the_schema_version_does_not_move(
        self, loaded_clip: LoadedAudio, tmp_path: Path
    ) -> None:
        markers = MarkerList()
        markers.add_marker(10, "Cue")

        root = tmp_path / "versioned.hlproj"
        self._save(root, loaded_clip, markers)
        payload = json.loads((root / "project.json").read_text(encoding="utf-8"))

        assert payload["schema_version"] == 1
        assert payload["markers"][0]["name"] == "Cue"

    def test_a_project_without_markers_omits_the_key(
        self, loaded_clip: LoadedAudio, tmp_path: Path
    ) -> None:
        """Nothing to say means nothing written, so older readers see no change."""
        root = tmp_path / "bare.hlproj"
        self._save(root, loaded_clip, MarkerList())
        payload = json.loads((root / "project.json").read_text(encoding="utf-8"))

        assert "markers" not in payload
        assert load_project(root).markers.is_empty

    def test_a_pre_marker_project_still_loads(
        self, loaded_clip: LoadedAudio, tmp_path: Path
    ) -> None:
        """A bundle written before markers existed opens with an empty list."""
        root = tmp_path / "legacy.hlproj"
        self._save(root, loaded_clip, None)
        payload = json.loads((root / "project.json").read_text(encoding="utf-8"))
        assert "markers" not in payload

        snapshot = load_project(root)
        assert snapshot.markers.is_empty
        assert snapshot.waveform is not None

    def test_markers_load_beside_the_waveform_state(
        self, loaded_clip: LoadedAudio, tmp_path: Path
    ) -> None:
        markers = MarkerList()
        markers.add_region(0, 500, "Head")

        root = tmp_path / "beside.hlproj"
        save_project(
            root,
            edit_session=EditSession.from_buffer(loaded_clip.buffer),
            editor_clip=loaded_clip,
            multitrack=MultitrackSession(sample_rate=loaded_clip.buffer.sample_rate),
            workspace="waveform",
            view_mode="split",
            playhead=1_234,
            selection=TimeRange(10, 20),
            markers=markers,
        )

        snapshot = load_project(root)
        assert snapshot.waveform is not None
        assert snapshot.waveform.playhead == 1_234
        assert snapshot.waveform.selection == TimeRange(10, 20)
        assert snapshot.markers.regions[0].name == "Head"

    def test_a_corrupt_marker_entry_is_reported_as_a_load_error(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "broken.hlproj"
        root.mkdir()
        (root / "project.json").write_text(
            json.dumps({"schema_version": 1, "markers": [{"nonsense": True}]}),
            encoding="utf-8",
        )

        with pytest.raises(ProjectLoadError, match="invalid markers"):
            load_project(root)


class MockHost(PluginHost):
    """A writable pass-through plugin host — no plugin binary, no Qt, no GPL."""

    def __init__(
        self,
        path: str | Path = "/plugins/Mock.vst3",
        parameters: dict[str, Any] | None = None,
    ) -> None:
        self._path = Path(path)
        self._parameters = dict(
            parameters if parameters is not None else {"drive": 0.25, "tone": 0.5}
        )

    @property
    def name(self) -> str:
        return self._path.stem

    @property
    def plugin_path(self) -> Path:
        return self._path

    def prepare(self, sample_rate: float, n_channels: int) -> None: ...

    def process_block(self, block: np.ndarray, sample_rate: float) -> np.ndarray:
        return block

    def latency_samples(self) -> int:
        return 0

    def parameters(self) -> dict[str, Any]:
        return dict(self._parameters)

    def set_parameter(self, name: str, value: Any) -> None:
        if name not in self._parameters:
            raise KeyError(name)
        self._parameters[name] = value


class TestPluginStatePersistence:
    """The optional base64 ``state`` blob rides the ``plugins`` array."""

    @staticmethod
    def _save(root: Path, plugins: list[dict[str, Any]]) -> None:
        save_project(
            root,
            edit_session=None,
            editor_clip=None,
            multitrack=MultitrackSession(),
            workspace="waveform",
            view_mode="split",
            playhead=0,
            selection=None,
            plugins=plugins,
        )

    @staticmethod
    def _entry(adapter: PluginEffectAdapter, slot: int = 0) -> dict[str, Any]:
        """The dict the plugin panel would write for ``adapter``."""
        blob = adapter.state_blob()
        assert blob is not None
        return {
            "slot": slot,
            "path": str(adapter.plugin_path),
            "bypass": adapter.bypass,
            "state": base64.b64encode(blob).decode("ascii"),
        }

    def test_the_state_blob_round_trips_through_the_bundle(self, tmp_path: Path) -> None:
        """Save a tweaked mock plugin, reopen, restore a fresh one from the blob."""
        saved_host = MockHost(parameters={"drive": 0.9, "tone": 0.1})
        root = tmp_path / "stateful.hlproj"
        self._save(root, [self._entry(PluginEffectAdapter(saved_host))])

        (restored,) = load_project(root).plugins
        fresh = PluginEffectAdapter(MockHost())
        assert fresh.restore_state(base64.b64decode(restored["state"])) is True

        assert fresh.plugin_parameters() == {"drive": 0.9, "tone": 0.1}
        assert restored["path"] == "/plugins/Mock.vst3"

    def test_the_blob_is_stored_verbatim(self, tmp_path: Path) -> None:
        adapter = PluginEffectAdapter(MockHost(parameters={"drive": 0.75}))
        entry = self._entry(adapter)
        root = tmp_path / "verbatim.hlproj"

        self._save(root, [entry])

        payload = json.loads((root / "project.json").read_text(encoding="utf-8"))
        assert payload["plugins"][0]["state"] == entry["state"]
        assert load_project(root).plugins[0]["state"] == entry["state"]

    def test_an_entry_without_state_stays_without_it(self, tmp_path: Path) -> None:
        """Pre-state projects (and hosts that cannot serialise) change nothing."""
        root = tmp_path / "stateless.hlproj"
        self._save(root, [{"slot": 0, "path": "/plugins/Old.vst3"}])

        payload = json.loads((root / "project.json").read_text(encoding="utf-8"))
        assert "state" not in payload["plugins"][0]
        assert "state" not in load_project(root).plugins[0]

    def test_a_blob_that_is_not_base64_is_dropped_at_save(self, tmp_path: Path) -> None:
        root = tmp_path / "mangled.hlproj"
        self._save(
            root,
            [{"slot": 0, "path": "/plugins/Mock.vst3", "state": "%%% not base64 %%%"}],
        )

        payload = json.loads((root / "project.json").read_text(encoding="utf-8"))
        assert "state" not in payload["plugins"][0]

    def test_a_hand_mangled_blob_is_dropped_at_load(self, tmp_path: Path) -> None:
        """The plugin entry survives; only its unusable state is discarded."""
        root = tmp_path / "edited.hlproj"
        root.mkdir()
        (root / "project.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "plugins": [
                        {"slot": 0, "path": "/plugins/Mock.vst3", "state": "!!!"}
                    ],
                }
            ),
            encoding="utf-8",
        )

        (entry,) = load_project(root).plugins
        assert entry["path"] == "/plugins/Mock.vst3"
        assert "state" not in entry


def test_document_media_is_readable_wav(loaded_clip: LoadedAudio, tmp_path: Path) -> None:
    session = EditSession.from_buffer(loaded_clip.buffer)
    session.apply_gain(TimeRange(0, 200), -6.0)

    root = tmp_path / "gain.hlproj"
    save_project(
        root,
        edit_session=session,
        editor_clip=loaded_clip,
        multitrack=MultitrackSession(sample_rate=loaded_clip.buffer.sample_rate),
        workspace="waveform",
        view_mode="split",
        playhead=0,
        selection=None,
    )

    document = load_audio(root / "media" / "document.wav")
    np.testing.assert_allclose(
        document.buffer.data,
        session.read(0, session.n_frames),
        rtol=0,
        atol=1e-6,
    )
