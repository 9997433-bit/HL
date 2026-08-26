"""Sparse, undoable edits over a streaming sample source."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from audio_studio.core.edit_session import (
    DEFAULT_CHUNK_FRAMES,
    EditSession,
    StreamingEditSession,
)
from audio_studio.core.types import TimeRange, db_to_amplitude


class MockStreamingSource:
    """Random-access disk-shaped source without involving a decoder."""

    def __init__(self, path: Path, samples: np.ndarray, sample_rate: int = 48_000) -> None:
        self.path = path
        self._samples = np.array(samples, dtype=np.float32, copy=True)
        self._sample_rate = sample_rate
        self.closed = False
        self.last_error: Exception | None = None

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def n_frames(self) -> int:
        return int(self._samples.shape[0])

    @property
    def n_channels(self) -> int:
        return int(self._samples.shape[1])

    @property
    def exact(self) -> bool:
        return False

    def read(self, start: int, n_frames: int) -> np.ndarray:
        start = max(0, min(int(start), self.n_frames))
        count = max(0, min(int(n_frames), self.n_frames - start))
        return self._samples[start : start + count].copy()

    def read_into(self, out: np.ndarray, start: int) -> int:
        block = self.read(start, out.shape[0])
        count = int(block.shape[0])
        out[:count] = block
        if count < out.shape[0]:
            out[count:] = 0.0
        return count

    def close(self) -> None:
        self.closed = True


def _session(
    tmp_path: Path, n_frames: int = 8_192
) -> tuple[StreamingEditSession, MockStreamingSource, np.ndarray, bytes]:
    samples = np.linspace(-0.9, 0.9, n_frames * 2, dtype=np.float32).reshape(-1, 2)
    path = tmp_path / "base.rf64"
    path.write_bytes(b"immutable mocked RF64 payload")
    before = path.read_bytes()
    source = MockStreamingSource(path, samples)
    session = EditSession.from_streaming(source)
    return session, source, samples, before


def test_gain_is_a_sparse_overlay_and_undo_restores_disk_base(tmp_path: Path) -> None:
    session, source, base, disk_before = _session(tmp_path)
    selected = TimeRange(1_000, 1_512)

    session.apply_gain(selected, -6.0)

    expected = base.copy()
    expected[selected.start : selected.end] *= np.float32(db_to_amplitude(-6.0))
    assert np.allclose(session.read(0, session.n_frames), expected)
    assert session.overlay_chunk_count == 1
    assert session.materialized_frames == selected.length
    assert np.array_equal(source._samples, base)  # noqa: SLF001 - proves base immutability
    assert source.path.read_bytes() == disk_before

    assert session.undo()
    assert np.array_equal(session.read(0, session.n_frames), base)
    assert session.overlay_chunk_count == 0
    assert source.path.read_bytes() == disk_before


def test_cut_and_paste_splice_base_ranges_without_materialising(tmp_path: Path) -> None:
    session, source, base, disk_before = _session(tmp_path)
    selected = TimeRange(900, 1_300)

    clipboard = session.cut(selected)
    cut = np.concatenate((base[: selected.start], base[selected.end :]), axis=0)
    assert np.array_equal(session.read(0, session.n_frames), cut)
    assert clipboard.n_frames == selected.length
    assert session.overlay_chunk_count == 0

    session.paste(session.n_frames)
    expected = np.concatenate((cut, base[selected.start : selected.end]), axis=0)
    assert np.array_equal(session.read(0, session.n_frames), expected)
    assert session.overlay_chunk_count == 0
    assert source.path.read_bytes() == disk_before


def test_overlay_chunk_count_is_bounded_by_changed_region(tmp_path: Path) -> None:
    changed_frames = DEFAULT_CHUNK_FRAMES * 2 + 17
    session, _source, _base, _disk_before = _session(tmp_path, changed_frames + 10_000)

    session.apply_gain(TimeRange(5_000, 5_000 + changed_frames), 3.0)

    assert session.overlay_chunk_count == 3
    assert session.materialized_frames == changed_frames
