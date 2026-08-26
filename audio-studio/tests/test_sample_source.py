"""Sample sources: memory/disk parity, block caching and engine integration.

The point of :class:`StreamingSampleSource` is that a clip too large to decode
still plays *identically* to one that fits in RAM. Almost every test here is
therefore a differential test against :class:`MemorySampleSource` rather than
against hand-written expectations.
"""

from __future__ import annotations

import threading
from pathlib import Path

import numpy as np
import pytest

from audio_studio.core.engine import AudioEngine
from audio_studio.core.loader import AudioLoadError, save_audio
from audio_studio.core.output import NullOutput
from audio_studio.core.sample_source import (
    BaseSampleSource,
    MemorySampleSource,
    SampleSource,
    StreamingSampleSource,
    open_source,
)
from audio_studio.core.types import AudioBuffer, TimeRange

SR = 44_100


def chirpy(n_frames: int, channels: int = 2, sample_rate: int = SR) -> AudioBuffer:
    """Broadband, non-repeating material: a block copied from the wrong offset shows up."""
    t = np.arange(n_frames, dtype=np.float64) / sample_rate
    data = np.empty((n_frames, channels), dtype=np.float32)
    for ch in range(channels):
        sweep = 200.0 + (4_000.0 * (ch + 1)) * t
        data[:, ch] = 0.4 * np.sin(2.0 * np.pi * sweep * t)
    return AudioBuffer(data, sample_rate)


@pytest.fixture(scope="module")
def wav(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, AudioBuffer]:
    """A float32 WAV so disk and memory agree bit for bit, not just to a tolerance."""
    buffer = chirpy(37_000)
    path = tmp_path_factory.mktemp("stream") / "sweep.wav"
    save_audio(path, buffer, subtype="FLOAT")
    return path, buffer


@pytest.fixture()
def streaming(wav: tuple[Path, AudioBuffer]):
    source = StreamingSampleSource(wav[0], block_frames=4_096, cache_blocks=3)
    yield source
    source.close()


@pytest.fixture()
def memory(wav: tuple[Path, AudioBuffer]) -> MemorySampleSource:
    return MemorySampleSource(wav[1])


# ---------------------------------------------------------------------------
# protocol
# ---------------------------------------------------------------------------


def test_both_implementations_satisfy_the_protocol(
    memory: MemorySampleSource, streaming: StreamingSampleSource
) -> None:
    for source in (memory, streaming):
        assert isinstance(source, SampleSource)
        assert isinstance(source, BaseSampleSource)


def test_metadata_agrees_between_disk_and_memory(
    memory: MemorySampleSource, streaming: StreamingSampleSource
) -> None:
    assert streaming.sample_rate == memory.sample_rate
    assert streaming.n_channels == memory.n_channels
    assert streaming.n_frames == memory.n_frames
    assert streaming.duration == pytest.approx(memory.duration)
    assert streaming.audio_format().container == "WAV"


# ---------------------------------------------------------------------------
# streaming vs memory parity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("start", "count"),
    [
        (0, 1),
        (0, 4_096),
        (0, 37_000),
        (4_095, 2),  # straddles a block boundary
        (4_096, 4_096),  # exactly one aligned block
        (1_000, 12_000),  # spans several blocks
        (36_990, 10),  # ends exactly at EOF
        (36_990, 500),  # runs past EOF
        (37_000, 100),  # starts at EOF
        (100_000, 10),  # entirely past EOF
    ],
)
def test_streaming_reads_match_memory_reads(
    memory: MemorySampleSource, streaming: StreamingSampleSource, start: int, count: int
) -> None:
    from_disk = streaming.read(start, count)
    from_ram = memory.read(start, count)

    assert from_disk.shape == from_ram.shape
    assert from_disk.dtype == np.float32
    assert np.array_equal(from_disk, from_ram)


def test_a_full_sequential_pass_reproduces_the_file(
    memory: MemorySampleSource, streaming: StreamingSampleSource
) -> None:
    """Playback order, in device-sized blocks, is the access pattern that matters."""
    blocks = [streaming.read(start, 1_024) for start in range(0, streaming.n_frames, 1_024)]

    assert np.array_equal(np.vstack(blocks), memory.read(0, memory.n_frames))


def test_random_access_matches_memory(
    memory: MemorySampleSource, streaming: StreamingSampleSource
) -> None:
    """Scrubbing: a cache that returns a stale block would fail here."""
    rng = np.random.default_rng(7)
    for _ in range(120):
        start = int(rng.integers(0, memory.n_frames))
        count = int(rng.integers(1, 6_000))
        assert np.array_equal(streaming.read(start, count), memory.read(start, count))


def test_reading_backwards_still_matches(
    memory: MemorySampleSource, streaming: StreamingSampleSource
) -> None:
    """Deliberately defeats the LRU: every read misses and must re-seek."""
    for start in range(30_000, 0, -3_000):
        assert np.array_equal(streaming.read(start, 2_048), memory.read(start, 2_048))


def test_the_block_cache_is_bounded(streaming: StreamingSampleSource) -> None:
    for start in range(0, streaming.n_frames, 4_096):
        streaming.read(start, 4_096)

    assert len(streaming._cache) <= 3  # noqa: SLF001 - the bound is the point


def test_prefetch_warms_the_cache_without_changing_results(
    memory: MemorySampleSource, streaming: StreamingSampleSource
) -> None:
    streaming.prefetch(8_192, 8_192)

    assert len(streaming._cache) > 0  # noqa: SLF001 - cache occupancy is the assertion
    assert np.array_equal(streaming.read(8_192, 8_192), memory.read(8_192, 8_192))


def test_block_iteration_covers_the_whole_source(
    memory: MemorySampleSource, streaming: StreamingSampleSource
) -> None:
    joined = np.vstack(list(streaming.blocks(5_000)))

    assert np.array_equal(joined, memory.read(0, memory.n_frames))


def test_materialising_a_stream_reproduces_the_buffer(
    memory: MemorySampleSource, streaming: StreamingSampleSource
) -> None:
    assert np.array_equal(streaming.to_buffer().data, memory.to_buffer().data)
    assert np.array_equal(
        streaming.read_range(TimeRange(1_000, 2_000)),
        memory.read_range(TimeRange(1_000, 2_000)),
    )


def test_concurrent_readers_do_not_corrupt_each_other(
    memory: MemorySampleSource, streaming: StreamingSampleSource
) -> None:
    """Two threads sharing one file handle: the lock has to hold the seek and read together."""
    failures: list[str] = []

    def worker(seed: int) -> None:
        rng = np.random.default_rng(seed)
        for _ in range(80):
            start = int(rng.integers(0, memory.n_frames - 2_000))
            block = streaming.read(start, 2_000)
            if not np.array_equal(block, memory.read(start, 2_000)):
                failures.append(f"mismatch at {start}")

    threads = [threading.Thread(target=worker, args=(seed,)) for seed in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30.0)

    assert not failures


# ---------------------------------------------------------------------------
# lifecycle and errors
# ---------------------------------------------------------------------------


def test_closing_twice_is_harmless(wav: tuple[Path, AudioBuffer]) -> None:
    source = StreamingSampleSource(wav[0])
    source.close()
    source.close()

    assert source.is_closed


def test_reading_a_closed_source_is_reported(wav: tuple[Path, AudioBuffer]) -> None:
    source = StreamingSampleSource(wav[0], block_frames=1_024)
    source.close()

    with pytest.raises(ValueError, match="closed"):
        source.read(0, 10)


def test_the_context_manager_closes_the_handle(wav: tuple[Path, AudioBuffer]) -> None:
    with StreamingSampleSource(wav[0]) as source:
        assert source.read(0, 10).shape == (10, 2)

    assert source.is_closed


def test_a_missing_file_raises_a_load_error(tmp_path: Path) -> None:
    with pytest.raises(AudioLoadError, match="Cannot stream"):
        StreamingSampleSource(tmp_path / "nope.wav")


@pytest.mark.parametrize(("block_frames", "cache_blocks"), [(0, 4), (-1, 4), (1_024, 0)])
def test_degenerate_cache_settings_are_rejected(
    wav: tuple[Path, AudioBuffer], block_frames: int, cache_blocks: int
) -> None:
    with pytest.raises(ValueError):
        StreamingSampleSource(wav[0], block_frames=block_frames, cache_blocks=cache_blocks)


def test_memory_source_needs_a_rate_for_a_raw_array() -> None:
    with pytest.raises(ValueError, match="sample_rate is required"):
        MemorySampleSource(np.zeros((10, 2), dtype=np.float32))


def test_memory_source_rejects_a_contradictory_rate() -> None:
    with pytest.raises(ValueError, match="contradicts"):
        MemorySampleSource(chirpy(10), 48_000)


def test_memory_reads_are_copies_but_views_are_not() -> None:
    buffer = chirpy(100)
    source = MemorySampleSource(buffer)

    source.read(0, 10)[0, 0] = 99.0
    assert buffer.data[0, 0] != 99.0
    assert np.shares_memory(source.view(0, 10), buffer.data)


def test_open_source_picks_memory_for_short_files(wav: tuple[Path, AudioBuffer]) -> None:
    assert isinstance(open_source(wav[0]), MemorySampleSource)


def test_open_source_streams_when_the_file_exceeds_the_limit(
    wav: tuple[Path, AudioBuffer],
) -> None:
    source = open_source(wav[0], memory_limit_frames=1_000)
    try:
        assert isinstance(source, StreamingSampleSource)
    finally:
        source.close()


def test_open_source_honours_an_explicit_choice(wav: tuple[Path, AudioBuffer]) -> None:
    with open_source(wav[0], streaming=True) as source:
        assert isinstance(source, StreamingSampleSource)


# ---------------------------------------------------------------------------
# transport integration
# ---------------------------------------------------------------------------


def _render_all(engine: AudioEngine, n_frames: int) -> np.ndarray:
    """Drive the manually-pumped backend until ``n_frames`` have been delivered."""
    import time

    output = engine.output
    assert isinstance(output, NullOutput)
    block = output.block_size
    rendered = []
    while sum(b.shape[0] for b in rendered) < n_frames:
        for _ in range(200):
            ring = engine._ring  # noqa: SLF001 - the test watches the buffering directly
            if ring is not None and ring.available_read >= block:
                break
            time.sleep(0.002)
        rendered.append(output.pump())
    return np.vstack(rendered)[:n_frames]


def test_the_engine_plays_a_streamed_file_exactly_like_a_decoded_one(
    wav: tuple[Path, AudioBuffer],
) -> None:
    path, buffer = wav
    n = 4 * 256

    decoded = AudioEngine(NullOutput(realtime=False), block_size=256, ring_blocks=8)
    streamed = AudioEngine(NullOutput(realtime=False), block_size=256, ring_blocks=8)
    try:
        decoded.load(path)
        decoded.seek(5_000)
        decoded.play()
        from_memory = _render_all(decoded, n)

        streamed.open_stream(path)
        streamed.seek(5_000)
        streamed.play()
        from_disk = _render_all(streamed, n)
    finally:
        decoded.shutdown()
        streamed.shutdown()

    assert np.allclose(from_memory, buffer.data[5_000 : 5_000 + n], atol=1e-6)
    assert np.array_equal(from_disk, from_memory)


def test_open_stream_reports_the_clip_without_decoding_it(
    wav: tuple[Path, AudioBuffer],
) -> None:
    engine = AudioEngine(NullOutput(realtime=False), block_size=256)
    try:
        source = engine.open_stream(wav[0])

        assert engine.is_streaming
        assert engine.has_clip
        assert engine.clip is None  # nothing was decoded into RAM
        assert engine.buffer is None
        assert engine.pyramid is None
        assert engine.n_frames == source.n_frames
        assert engine.n_channels == 2
        assert engine.sample_rate == SR
        assert engine.duration == pytest.approx(wav[1].duration)
        assert engine.audio_format.subtype == "FLOAT"
    finally:
        engine.shutdown()


def test_open_stream_can_build_the_waveform_overview(wav: tuple[Path, AudioBuffer]) -> None:
    engine = AudioEngine(NullOutput(realtime=False), block_size=256)
    try:
        engine.open_stream(wav[0], build_pyramid=True)

        assert engine.pyramid is not None
        assert engine.pyramid.n_frames == wav[1].n_frames
    finally:
        engine.shutdown()


def test_shutdown_releases_the_streamed_file_handle(wav: tuple[Path, AudioBuffer]) -> None:
    engine = AudioEngine(NullOutput(realtime=False))
    source = engine.open_stream(wav[0])

    engine.shutdown()

    assert source.is_closed


def test_replacing_a_streamed_clip_closes_the_previous_handle(
    wav: tuple[Path, AudioBuffer],
) -> None:
    engine = AudioEngine(NullOutput(realtime=False))
    try:
        first = engine.open_stream(wav[0])
        second = engine.open_stream(wav[0])

        assert first.is_closed
        assert not second.is_closed
    finally:
        engine.shutdown()


def test_the_engine_can_play_an_edit_session(wav: tuple[Path, AudioBuffer]) -> None:
    """An EditSession is a SampleSource, so edits are audible without flattening."""
    from audio_studio.core.edit_session import EditSession

    session = EditSession.from_buffer(wav[1])
    session.silence(TimeRange(0, 10_000))

    engine = AudioEngine(NullOutput(realtime=False), block_size=256, ring_blocks=8)
    try:
        engine.set_source(session, audio_format=None)
        assert engine.n_frames == session.n_frames

        engine.play()
        rendered = _render_all(engine, 1_024)
    finally:
        engine.shutdown()

    assert np.all(rendered == 0.0)
    assert not session.document.segments[0].chunk.data.flags.writeable
