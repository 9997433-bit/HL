"""The DEV-20 source vocabulary: frozen names, RegionSource and LoopSource.

The Round 2 convergence audit freezes the module path ``core/sources.py`` and
its names; the Round 3 signoff (DEV-20) records two halves: the frozen names
(ArraySource/FileStreamSource/ChunkTableSource) are *aliases* bound to the
implementation objects — identical, not wrappers, so ``isinstance`` holds
across either spelling — while ``RegionSource``/``LoopSource`` are real
composite sources that express selection and looping without transport
cooperation. This file is the dedicated contract check for both halves.

The composites are tested differentially where possible: a region read must
equal the inner source's slice, a looped read must equal a tiled slice, and
the same composition over a disk-streamed source must equal the in-memory
answer bit for bit.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from audio_studio.core import LoopSource as CoreLoopSource
from audio_studio.core import RegionSource as CoreRegionSource
from audio_studio.core.edit_session import EditSession
from audio_studio.core.loader import save_audio
from audio_studio.core.sample_source import (
    BaseSampleSource,
    MemorySampleSource,
    SampleSource,
    StreamingSampleSource,
)
from audio_studio.core.sources import (
    ENDLESS_FRAMES,
    ArraySource,
    ChunkTableSource,
    FileStreamSource,
    LoopSource,
    RegionSource,
)
from audio_studio.core.types import AudioBuffer, TimeRange

SR = 48_000


def ramp(n_frames: int, channels: int = 2) -> MemorySampleSource:
    """Every sample distinct, so a block copied from the wrong offset shows up."""
    data = (
        np.arange(n_frames * channels, dtype=np.float32).reshape(n_frames, channels)
        / 65_536.0
    )
    return MemorySampleSource(AudioBuffer(data, SR))


class Closable(MemorySampleSource):
    """A source that records whether close() reached it."""

    def __init__(self, n_frames: int = 8) -> None:
        super().__init__(AudioBuffer(np.zeros((n_frames, 1), dtype=np.float32), SR))
        self.closed = False

    def close(self) -> None:
        self.closed = True


@pytest.fixture(scope="module")
def wav(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, MemorySampleSource]:
    """A float32 WAV so the disk and memory answers must agree bit for bit."""
    source = ramp(50_000)
    path = tmp_path_factory.mktemp("sources") / "ramp.wav"
    save_audio(path, source.buffer, subtype="FLOAT")
    return path, source


# ---------------------------------------------------------------------------
# the frozen names are the implementation objects, not wrappers
# ---------------------------------------------------------------------------


def test_frozen_names_bind_to_the_implementation_objects() -> None:
    assert ArraySource is MemorySampleSource
    assert FileStreamSource is StreamingSampleSource
    assert ChunkTableSource is EditSession


def test_isinstance_holds_across_either_spelling() -> None:
    clip = ArraySource(AudioBuffer(np.zeros((16, 2), dtype=np.float32), SR))
    assert isinstance(clip, MemorySampleSource)
    assert isinstance(clip, ArraySource)
    assert type(clip).__name__ == "MemorySampleSource"


def test_composites_are_exported_at_the_package_level() -> None:
    assert CoreRegionSource is RegionSource
    assert CoreLoopSource is LoopSource


def test_composites_satisfy_the_sample_source_protocol() -> None:
    inner = ramp(32)
    for source in (RegionSource(inner, TimeRange(4, 12)), LoopSource(inner, repeats=2)):
        assert isinstance(source, SampleSource)
        assert isinstance(source, BaseSampleSource)


# ---------------------------------------------------------------------------
# RegionSource: a window, re-based to frame zero
# ---------------------------------------------------------------------------


def test_region_reads_equal_the_inner_slice() -> None:
    inner = ramp(1_000)
    region = RegionSource(inner, TimeRange(200, 300))

    assert region.n_frames == 100
    assert region.sample_rate == SR
    assert region.n_channels == 2
    assert np.array_equal(region.read(0, 100), inner.read(200, 100))
    assert np.array_equal(region.read(25, 10), inner.read(225, 10))


def test_region_defaults_to_the_whole_inner_source() -> None:
    inner = ramp(64)
    assert RegionSource(inner).n_frames == 64


def test_region_clamps_a_window_past_the_inner_end() -> None:
    region = RegionSource(ramp(100), TimeRange(80, 500))
    assert region.region == TimeRange(80, 100)
    assert region.n_frames == 20


def test_region_reads_clamp_like_any_source() -> None:
    """Out-of-range requests shorten instead of raising — the feeder contract."""
    region = RegionSource(ramp(100), TimeRange(40, 60))
    assert region.read(15, 100).shape == (5, 2)
    assert region.read(60, 8).shape == (0, 2)
    assert region.read(-3, 4).shape == (4, 2)


def test_region_read_into_fills_the_callers_buffer_and_pads_the_tail() -> None:
    inner = ramp(100)
    region = RegionSource(inner, TimeRange(90, 100))
    out = np.full((16, 2), 7.0, dtype=np.float32)

    written = region.read_into(out, 4)

    assert written == 6  # frames 94..99 of the inner source
    assert np.array_equal(out[:6], inner.read(94, 6))
    assert np.all(out[6:] == 0.0)


def test_region_read_into_rejects_a_mis_shaped_buffer() -> None:
    region = RegionSource(ramp(32, channels=2))
    with pytest.raises(ValueError, match="out must be"):
        region.read_into(np.empty((8, 3), dtype=np.float32), 0)


def test_region_maps_frames_back_onto_the_inner_timeline() -> None:
    region = RegionSource(ramp(1_000), TimeRange(400, 600))
    assert region.to_timeline(0) == 400
    assert region.to_timeline(199) == 599


def test_region_exact_follows_the_inner_source(wav: tuple[Path, MemorySampleSource]) -> None:
    path, _ = wav
    assert RegionSource(ramp(16)).exact is True
    with FileStreamSource(path) as streamed:
        assert RegionSource(streamed, TimeRange(0, 100)).exact is False


def test_region_close_respects_ownership() -> None:
    borrowed = Closable()
    RegionSource(borrowed).close()
    assert borrowed.closed is False

    owned = Closable()
    RegionSource(owned, owns_inner=True).close()
    assert owned.closed is True


# ---------------------------------------------------------------------------
# LoopSource: reads past the end fold back to the start
# ---------------------------------------------------------------------------


def test_a_counted_loop_is_exactly_the_tiled_inner_source() -> None:
    inner = ramp(10)
    loop = LoopSource(inner, repeats=3)

    assert loop.n_frames == 30
    assert loop.cycle_frames == 10
    assert loop.is_endless is False
    assert np.array_equal(loop.read(0, 30), np.tile(inner.read(0, 10), (3, 1)))


def test_a_read_across_the_seam_is_stitched_not_truncated() -> None:
    inner = ramp(10)
    block = LoopSource(inner, repeats=4).read(7, 8)

    assert block.shape == (8, 2)
    assert np.array_equal(block[:3], inner.read(7, 3))
    assert np.array_equal(block[3:], inner.read(0, 5))  # no zero gap at the wrap


def test_read_into_across_the_seam_reports_full_delivery() -> None:
    inner = ramp(10)
    loop = LoopSource(inner)
    out = np.full((25, 2), -1.0, dtype=np.float32)

    written = loop.read_into(out, 8)

    assert written == 25
    assert np.array_equal(out[:2], inner.read(8, 2))
    assert np.array_equal(out[2:12], inner.read(0, 10))


def test_an_endless_loop_reports_a_practically_infinite_length() -> None:
    loop = LoopSource(ramp(10))
    assert loop.is_endless is True
    assert loop.repeats is None
    assert loop.n_frames == ENDLESS_FRAMES


def test_endless_frames_leaves_int64_headroom() -> None:
    """A caller adding a block size to n_frames must not overflow int64."""
    assert ENDLESS_FRAMES + 2**31 < 2**63 - 1
    assert np.int64(ENDLESS_FRAMES) + np.int64(2**31) > 0


def test_deep_positions_read_by_modulo() -> None:
    inner = ramp(10)
    loop = LoopSource(inner)
    deep = 10 * 1_000_000 + 3  # a million passes in, three frames past the seam
    assert np.array_equal(loop.read(deep, 4), inner.read(3, 4))


def test_an_endless_loop_over_an_empty_source_is_empty() -> None:
    empty = MemorySampleSource(AudioBuffer(np.zeros((0, 2), dtype=np.float32), SR))
    loop = LoopSource(empty)
    assert loop.n_frames == 0
    assert loop.read(0, 128).shape == (0, 2)

    out = np.full((8, 2), 5.0, dtype=np.float32)
    assert loop.read_into(out, 0) == 0
    assert np.all(out == 0.0)


def test_non_positive_repeat_counts_are_rejected() -> None:
    for repeats in (0, -1):
        with pytest.raises(ValueError, match="repeats"):
            LoopSource(ramp(10), repeats=repeats)


def test_loop_close_respects_ownership() -> None:
    borrowed = Closable()
    LoopSource(borrowed).close()
    assert borrowed.closed is False

    owned = Closable()
    LoopSource(owned, owns_inner=True).close()
    assert owned.closed is True


# ---------------------------------------------------------------------------
# composition: the reason these are sources and not transport state
# ---------------------------------------------------------------------------


def test_a_looped_region_is_the_tiled_slice() -> None:
    inner = ramp(100)
    chorus = LoopSource(RegionSource(inner, TimeRange(40, 50)), repeats=3)

    assert chorus.n_frames == 30
    assert np.array_equal(chorus.read(0, 30), np.tile(inner.read(40, 10), (3, 1)))


def test_the_composition_over_a_streamed_file_matches_memory(
    wav: tuple[Path, MemorySampleSource]
) -> None:
    """Disk-streamed and in-memory answers must be bit-identical."""
    path, memory = wav
    window = TimeRange(30_000, 41_000)

    expected = LoopSource(RegionSource(memory, window), repeats=2).read(0, 22_000)
    with FileStreamSource(path, block_frames=4_096) as streamed:
        looped = LoopSource(RegionSource(streamed, window), repeats=2)
        assert looped.exact is False  # streaming shows through the wrappers
        actual = looped.read(0, 22_000)

    assert np.array_equal(actual, expected)


def test_a_feeder_style_loop_never_raises_over_the_composition(
    wav: tuple[Path, MemorySampleSource]
) -> None:
    """Drain blocks through read_into exactly the way the feeder thread does."""
    path, memory = wav
    window = TimeRange(10_000, 10_700)
    block = np.empty((256, 2), dtype=np.float32)

    with FileStreamSource(path, block_frames=4_096) as streamed:
        source = LoopSource(RegionSource(streamed, window), repeats=5)
        gathered: list[np.ndarray] = []
        position = 0
        while position < source.n_frames:
            written = source.read_into(block, position)
            gathered.append(block[:written].copy())
            position += written
            if written == 0:
                break

    played = np.concatenate(gathered)
    assert played.shape == (3_500, 2)
    assert np.array_equal(played, np.tile(memory.read(10_000, 700), (5, 1)))
