"""Broadcast Wave metadata, cue, atomic-publish, and crash-recovery coverage."""

from __future__ import annotations

import struct
from pathlib import Path

from audio_studio.core.loader import load_audio
from audio_studio.core.markers import MarkerList
from audio_studio.core.recorder import NullRecorder, recover_bwf_recording


def riff_chunks(path: Path) -> dict[bytes, bytes]:
    raw = path.read_bytes()
    assert raw[:4] == b"RIFF"
    assert raw[8:12] == b"WAVE"
    chunks: dict[bytes, bytes] = {}
    offset = 12
    while offset + 8 <= len(raw):
        chunk_id, size = struct.unpack_from("<4sI", raw, offset)
        payload_start = offset + 8
        payload_end = payload_start + size
        if payload_end > len(raw):
            break
        chunks[chunk_id] = raw[payload_start:payload_end]
        offset = payload_end + (size & 1)
    return chunks


def test_recording_is_atomically_published_with_bext_and_marker_cues(
    tmp_path: Path,
) -> None:
    target = tmp_path / "take.wav"
    markers = MarkerList()
    markers.add_marker(12, "Slate")
    recorder = NullRecorder(realtime=False, tone_frequency=440.0)
    recorder.open(
        48_000,
        1,
        target_path=target,
        description="Session take 7",
        originator="Audio Studio Tests",
        markers=markers,
        flush_interval=0,
    )
    partial = recorder.temporary_path

    assert partial is not None and partial.exists()
    assert not target.exists()

    recorder.start()
    recorder.pump(64)
    recorder.stop()

    assert target.exists()
    assert not partial.exists()
    chunks = riff_chunks(target)
    assert chunks[b"bext"][:256].rstrip(b"\0") == b"Session take 7"
    assert chunks[b"bext"][256:288].rstrip(b"\0") == b"Audio Studio Tests"
    assert b"cue " in chunks
    assert b"LIST" in chunks

    cue_count = struct.unpack_from("<I", chunks[b"cue "], 0)[0]
    cue_frame = struct.unpack_from("<I", chunks[b"cue "], 4 + 20)[0]
    assert cue_count == 1
    assert cue_frame == 12
    assert b"Slate\0" in chunks[b"LIST"]


def test_truncated_temporary_recording_recovers_complete_frames(
    tmp_path: Path,
) -> None:
    target = tmp_path / "interrupted.wav"
    recorder = NullRecorder(realtime=False, tone_frequency=220.0)
    recorder.open(8_000, 1, target_path=target, flush_interval=0)
    recorder.start()
    recorder.pump(101)
    partial = recorder.abandon()

    assert partial is not None and partial.exists()
    assert not target.exists()

    # Simulate a crash/torn final sample: recovery may discard that frame but
    # must leave a standards-compliant, decodable BWF.
    partial.write_bytes(partial.read_bytes()[:-2])
    recovered = recover_bwf_recording(partial, target)
    loaded = load_audio(recovered)

    assert recovered == target
    assert loaded.buffer.sample_rate == 8_000
    assert loaded.buffer.n_channels == 1
    assert loaded.buffer.n_frames == 100
    assert b"bext" in riff_chunks(recovered)
