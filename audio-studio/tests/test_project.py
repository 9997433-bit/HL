"""Round-trip tests for .hlproj project bundles."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from audio_studio.core.edit_session import EditSession
from audio_studio.core.loader import LoadedAudio, load_audio
from audio_studio.core.sample_source import MemorySampleSource
from audio_studio.core.session import MultitrackSession, Track
from audio_studio.core.types import TimeRange
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
