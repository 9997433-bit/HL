"""Peak pyramid disk cache: round-trips, invalidation and failure handling."""

from __future__ import annotations

import json
import os
import struct
from pathlib import Path

import numpy as np
import pytest

from audio_studio.core import peaks_cache
from audio_studio.core.engine import AudioEngine
from audio_studio.core.loader import LoadedAudio, save_audio
from audio_studio.core.output import NullOutput
from audio_studio.core.peaks import PeakPyramid
from audio_studio.core.sample_source import MemorySampleSource
from audio_studio.core.session import MultitrackSession, Track
from audio_studio.core.types import AudioBuffer
from audio_studio.project.store import load_media_pyramid, load_project, save_project

SAMPLE_RATE = 44100


@pytest.fixture(autouse=True)
def _clean_cache_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test starts from the documented defaults, whatever the shell says."""
    for name in (peaks_cache.ENV_ENABLED, peaks_cache.ENV_DIR, peaks_cache.ENV_KEY_MODE):
        monkeypatch.delenv(name, raising=False)


def noise(n_frames: int = 60_000, channels: int = 2, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return (rng.standard_normal((n_frames, channels)) * 0.3).astype(np.float32)


@pytest.fixture()
def audio_file(tmp_path: Path) -> tuple[Path, np.ndarray]:
    data = noise()
    path = tmp_path / "clip.wav"
    save_audio(path, AudioBuffer(data, SAMPLE_RATE), subtype="FLOAT")
    return path, data


class UnbuildablePyramid(PeakPyramid):
    """Stand-in that can be restored from a cache but never reduced from samples."""

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise AssertionError("the pyramid was rebuilt instead of read from disk")


def save_multitrack_project(root: Path, clip: LoadedAudio) -> Path:
    session = MultitrackSession(
        sample_rate=clip.buffer.sample_rate, n_channels=clip.buffer.n_channels
    )
    track = session.add_track(Track(name="Drums"))
    session.add_clip(
        track, MemorySampleSource(clip.buffer), start=0, duration=clip.buffer.n_frames
    )
    return save_project(
        root,
        edit_session=None,
        editor_clip=None,
        multitrack=session,
        workspace="multitrack",
        view_mode="waveform",
        playhead=0,
        selection=None,
    )


def envelopes_match(left: PeakPyramid, right: PeakPyramid, *, n_bins: int = 400) -> bool:
    a = left.envelope(0, left.n_frames, n_bins)
    b = right.envelope(0, right.n_frames, n_bins)
    return (
        np.array_equal(a.minimum, b.minimum)
        and np.array_equal(a.maximum, b.maximum)
        and np.array_equal(a.rms, b.rms)
    )


# ------------------------------------------------------------------ round-trip


def test_a_written_pyramid_reads_back_bit_identical(
    audio_file: tuple[Path, np.ndarray],
) -> None:
    path, data = audio_file
    original = PeakPyramid(data)

    written = peaks_cache.write(path, original)
    restored = peaks_cache.read(path, samples=data)

    assert written == path.with_name("clip.wav.pk")
    assert written.is_file()
    assert restored is not None
    assert restored.n_frames == original.n_frames
    assert restored.n_channels == original.n_channels
    assert restored.n_levels == original.n_levels
    assert envelopes_match(original, restored)


def test_every_pyramid_level_survives_the_round_trip(tmp_path: Path) -> None:
    data = noise(30_000, channels=1)
    path = tmp_path / "mono.wav"
    save_audio(path, AudioBuffer(data, SAMPLE_RATE), subtype="FLOAT")
    # A tiny base decimation forces the pyramid to stack several levels.
    original = PeakPyramid(data, base_decimation=2)
    assert original.n_levels > 2

    peaks_cache.write(path, original)
    restored = peaks_cache.read(path, samples=data)

    assert restored is not None
    assert [lvl.decimation for lvl in restored.levels] == [
        lvl.decimation for lvl in original.levels
    ]
    for got, want in zip(restored.levels, original.levels, strict=True):
        assert np.array_equal(got.minimum, want.minimum)
        assert np.array_equal(got.maximum, want.maximum)
        assert np.array_equal(got.sumsq, want.sumsq)
        assert np.array_equal(got.counts, want.counts)


def test_an_empty_clip_round_trips_without_levels(tmp_path: Path) -> None:
    path = tmp_path / "empty.wav"
    data = np.zeros((0, 2), dtype=np.float32)
    save_audio(path, AudioBuffer(data, SAMPLE_RATE), subtype="FLOAT")

    peaks_cache.write(path, PeakPyramid(data))
    restored = peaks_cache.read(path, samples=data)

    assert restored is not None
    assert restored.n_frames == 0
    assert restored.n_levels == 0
    assert np.all(restored.envelope(0, 0, 16).maximum == 0.0)


def test_a_pyramid_restored_without_samples_still_bounds_the_waveform(
    audio_file: tuple[Path, np.ndarray],
) -> None:
    """Without the source frames the finest level caps how far zoom resolves."""
    path, data = audio_file
    peaks_cache.write(path, PeakPyramid(data))

    restored = peaks_cache.read(path)

    assert restored is not None
    assert not restored.has_samples
    zoomed = restored.envelope(1_000, 1_100, 100)
    assert zoomed.n_bins == 100
    assert np.all(zoomed.minimum <= zoomed.maximum + 1e-7)
    assert zoomed.maximum.max() <= data.max() + 1e-6


# ----------------------------------------------------------------- cache keys


def test_touching_the_source_invalidates_the_cache(
    audio_file: tuple[Path, np.ndarray],
) -> None:
    path, data = audio_file
    peaks_cache.write(path, PeakPyramid(data))
    assert peaks_cache.read(path, samples=data) is not None

    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))

    assert peaks_cache.read(path, samples=data) is None


def test_rewriting_the_source_at_a_new_length_invalidates_the_cache(
    audio_file: tuple[Path, np.ndarray],
) -> None:
    path, data = audio_file
    peaks_cache.write(path, PeakPyramid(data))

    save_audio(path, AudioBuffer(data[:10_000], SAMPLE_RATE), subtype="FLOAT")

    assert peaks_cache.read(path) is None


def test_content_keys_survive_a_touch_but_not_an_edit(
    audio_file: tuple[Path, np.ndarray], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, data = audio_file
    monkeypatch.setenv(peaks_cache.ENV_KEY_MODE, "content")
    peaks_cache.write(path, PeakPyramid(data))
    assert peaks_cache.cache_key(path).startswith("h1:")

    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 5_000_000_000))
    assert peaks_cache.read(path, samples=data) is not None

    edited = data.copy()
    edited[:100] = 0.9
    save_audio(path, AudioBuffer(edited, SAMPLE_RATE), subtype="FLOAT")
    assert peaks_cache.read(path) is None


def test_stat_keys_track_size_and_modification_time(
    audio_file: tuple[Path, np.ndarray],
) -> None:
    path, _ = audio_file
    stat = path.stat()

    key = peaks_cache.cache_key(path)

    assert key == f"s1:{stat.st_size}:{stat.st_mtime_ns}"


def test_an_unknown_key_mode_is_rejected(audio_file: tuple[Path, np.ndarray]) -> None:
    with pytest.raises(ValueError, match="unknown cache key mode"):
        peaks_cache.cache_key(audio_file[0], mode="fingerprint")


# ------------------------------------------------------------- corrupt inputs


def test_a_foreign_file_with_the_right_extension_is_a_miss(
    audio_file: tuple[Path, np.ndarray],
) -> None:
    path, _ = audio_file
    peaks_cache.sidecar_path(path).write_bytes(b"definitely not a pyramid")

    assert peaks_cache.read(path) is None
    with pytest.raises(peaks_cache.PeakCacheError, match="not a peak cache file"):
        peaks_cache.decode(b"definitely not a pyramid")


def test_a_truncated_cache_is_a_miss(audio_file: tuple[Path, np.ndarray]) -> None:
    path, data = audio_file
    sidecar = peaks_cache.write(path, PeakPyramid(data))
    payload = sidecar.read_bytes()
    sidecar.write_bytes(payload[: len(payload) // 2])

    assert peaks_cache.read(path, samples=data) is None
    with pytest.raises(peaks_cache.PeakCacheError):
        peaks_cache.decode(payload[: len(payload) // 2])


def test_a_future_format_version_is_a_miss(audio_file: tuple[Path, np.ndarray]) -> None:
    path, data = audio_file
    sidecar = peaks_cache.write(path, PeakPyramid(data))
    payload = bytearray(sidecar.read_bytes())
    struct.pack_into("<H", payload, len(peaks_cache.MAGIC), peaks_cache.FORMAT_VERSION + 1)
    sidecar.write_bytes(bytes(payload))

    assert peaks_cache.read(path, samples=data) is None


def test_a_cache_whose_geometry_disagrees_with_the_audio_is_a_miss(
    audio_file: tuple[Path, np.ndarray],
) -> None:
    """Nothing may draw a two-channel envelope over a one-channel clip."""
    path, data = audio_file
    peaks_cache.write(path, PeakPyramid(data))

    assert peaks_cache.read(path, samples=data[:, :1]) is None


def test_the_header_records_the_key_and_the_geometry(
    audio_file: tuple[Path, np.ndarray],
) -> None:
    path, data = audio_file
    sidecar = peaks_cache.write(path, PeakPyramid(data))

    payload = sidecar.read_bytes()
    offset = len(peaks_cache.MAGIC) + struct.calcsize("<HI")
    _, header_len = struct.unpack_from("<HI", payload, len(peaks_cache.MAGIC))
    header = json.loads(payload[offset : offset + header_len])

    assert header["key"] == peaks_cache.cache_key(path)
    assert header["n_frames"] == data.shape[0]
    assert header["n_channels"] == data.shape[1]
    assert header["source"] == "clip.wav"


# ------------------------------------------------------------- atomic writing


def test_a_failed_write_leaves_the_previous_cache_and_no_debris(
    audio_file: tuple[Path, np.ndarray], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, data = audio_file
    sidecar = peaks_cache.write(path, PeakPyramid(data))
    intact = sidecar.read_bytes()

    def explode(*_args: object, **_kwargs: object) -> None:
        raise OSError("no space left on device")

    monkeypatch.setattr(peaks_cache.os, "replace", explode)
    assert peaks_cache.write(path, PeakPyramid(data * 0.5)) is None

    assert sidecar.read_bytes() == intact
    assert sorted(p.name for p in path.parent.iterdir()) == ["clip.wav", "clip.wav.pk"]


def test_writing_over_an_existing_cache_replaces_it(
    audio_file: tuple[Path, np.ndarray],
) -> None:
    path, data = audio_file
    peaks_cache.write(path, PeakPyramid(data))

    quieter = data * 0.25
    peaks_cache.write(path, PeakPyramid(quieter), key=peaks_cache.cache_key(path))
    restored = peaks_cache.read(path, samples=quieter)

    assert restored is not None
    assert envelopes_match(PeakPyramid(quieter), restored)
    assert sorted(p.name for p in path.parent.iterdir()) == ["clip.wav", "clip.wav.pk"]


def test_a_read_only_directory_does_not_break_the_build(
    audio_file: tuple[Path, np.ndarray], tmp_path: Path
) -> None:
    path, data = audio_file
    read_only = tmp_path / "read-only"
    read_only.mkdir()
    read_only.chmod(0o500)
    try:
        assert peaks_cache.write(path, PeakPyramid(data), cache_dir=read_only) is None
        pyramid = peaks_cache.cached_pyramid(path, data, cache_dir=read_only)
    finally:
        read_only.chmod(0o700)

    assert pyramid.n_frames == data.shape[0]


# ------------------------------------------------------------------ placement


def test_a_cache_directory_keeps_sidecars_out_of_the_audio_folder(
    audio_file: tuple[Path, np.ndarray], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, data = audio_file
    store = tmp_path / "cache"
    monkeypatch.setenv(peaks_cache.ENV_DIR, str(store))

    peaks_cache.write(path, PeakPyramid(data))

    assert not path.with_name("clip.wav.pk").exists()
    assert len(list(store.glob(f"clip-*{peaks_cache.SUFFIX}"))) == 1
    assert peaks_cache.read(path, samples=data) is not None


def test_same_named_files_in_different_folders_do_not_collide(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = tmp_path / "cache"
    monkeypatch.setenv(peaks_cache.ENV_DIR, str(store))
    first, second = tmp_path / "a", tmp_path / "b"
    for folder, amplitude in ((first, 0.9), (second, 0.2)):
        folder.mkdir()
        save_audio(
            folder / "take.wav", AudioBuffer(noise() * amplitude, SAMPLE_RATE), subtype="FLOAT"
        )

    loud = peaks_cache.cached_pyramid(first / "take.wav", lambda: noise() * 0.9)
    quiet = peaks_cache.cached_pyramid(second / "take.wav", lambda: noise() * 0.2)

    assert len(list(store.glob(f"*{peaks_cache.SUFFIX}"))) == 2
    assert peaks_cache.sidecar_path(first / "take.wav") != peaks_cache.sidecar_path(
        second / "take.wav"
    )
    assert loud.envelope(0, loud.n_frames, 32).maximum.max() > quiet.envelope(
        0, quiet.n_frames, 32
    ).maximum.max()


def test_discard_removes_the_sidecar(audio_file: tuple[Path, np.ndarray]) -> None:
    path, data = audio_file
    peaks_cache.write(path, PeakPyramid(data))

    assert peaks_cache.discard(path) is True
    assert peaks_cache.discard(path) is False
    assert peaks_cache.read(path) is None


# --------------------------------------------------------------- front door


def test_cached_pyramid_builds_once_and_reuses_the_result(
    audio_file: tuple[Path, np.ndarray],
) -> None:
    path, data = audio_file
    builds = 0

    def build() -> np.ndarray:
        nonlocal builds
        builds += 1
        return data

    first = peaks_cache.cached_pyramid(path, build)
    second = peaks_cache.cached_pyramid(path, build)

    assert builds == 1  # the second call never touched the samples
    assert second is not first
    # A hit off a callable carries no samples, so the levels are compared at a
    # zoom the pyramid answers from the mip-map either way.
    assert not second.has_samples
    assert envelopes_match(first, second, n_bins=64)


def test_cached_pyramid_keeps_the_samples_it_was_handed(
    audio_file: tuple[Path, np.ndarray],
) -> None:
    path, data = audio_file
    peaks_cache.cached_pyramid(path, data)

    hit = peaks_cache.cached_pyramid(path, data)

    assert hit.has_samples
    zoomed = hit.envelope(1_000, 1_100, 100)
    assert np.allclose(zoomed.maximum[:, 0], data[1_000:1_100, 0], atol=1e-6)


def test_the_env_switch_disables_reads_and_writes(
    audio_file: tuple[Path, np.ndarray], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, data = audio_file
    monkeypatch.setenv(peaks_cache.ENV_ENABLED, "0")

    assert not peaks_cache.cache_enabled()
    peaks_cache.cached_pyramid(path, data)
    assert not peaks_cache.sidecar_path(path).exists()

    # A cache left over from an enabled run must be ignored, not read.
    monkeypatch.delenv(peaks_cache.ENV_ENABLED)
    peaks_cache.cached_pyramid(path, data)
    assert peaks_cache.sidecar_path(path).is_file()

    monkeypatch.setenv(peaks_cache.ENV_ENABLED, "off")
    builds = 0

    def build() -> np.ndarray:
        nonlocal builds
        builds += 1
        return data

    peaks_cache.cached_pyramid(path, build)
    assert builds == 1


def test_the_enabled_argument_overrides_the_environment(
    audio_file: tuple[Path, np.ndarray], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, data = audio_file
    monkeypatch.setenv(peaks_cache.ENV_ENABLED, "0")

    peaks_cache.cached_pyramid(path, data, enabled=True)

    assert peaks_cache.sidecar_path(path).is_file()


def test_a_pathless_clip_is_simply_not_cached(tmp_path: Path) -> None:
    data = noise(5_000, channels=1)

    pyramid = peaks_cache.cached_pyramid(None, data)
    missing = peaks_cache.cached_pyramid(tmp_path / "never-written.wav", data)

    assert pyramid.n_frames == 5_000
    assert missing.n_frames == 5_000
    assert not (tmp_path / "never-written.wav.pk").exists()


# ------------------------------------------------------------------- engine


def test_loading_a_file_writes_and_then_reuses_its_sidecar(
    audio_file: tuple[Path, np.ndarray], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, data = audio_file
    engine = AudioEngine(NullOutput(realtime=False), block_size=256)
    try:
        engine.load(path)
        assert engine.pyramid is not None
        first = engine.pyramid.envelope(0, engine.pyramid.n_frames, 128)
        assert peaks_cache.sidecar_path(path).is_file()

        monkeypatch.setattr(peaks_cache, "PeakPyramid", UnbuildablePyramid)
        engine.load(path)
    finally:
        engine.shutdown()

    assert engine.pyramid is not None
    assert np.array_equal(engine.pyramid.envelope(0, data.shape[0], 128).maximum, first.maximum)


def test_streaming_a_cached_file_skips_the_extra_decode_pass(
    audio_file: tuple[Path, np.ndarray], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, data = audio_file
    peaks_cache.write(path, PeakPyramid(data))
    engine = AudioEngine(NullOutput(realtime=False), block_size=256)

    monkeypatch.setattr(peaks_cache, "PeakPyramid", UnbuildablePyramid)
    try:
        engine.open_stream(path, build_pyramid=True)

        assert engine.pyramid is not None
        assert engine.pyramid.n_frames == data.shape[0]
    finally:
        engine.shutdown()


def test_a_project_bundle_records_the_sidecar_for_each_media_copy(
    loaded_clip: LoadedAudio, tmp_path: Path
) -> None:
    root = save_multitrack_project(tmp_path / "session.hlproj", loaded_clip)

    snapshot = load_project(root)
    entry = snapshot.multitrack["media"][0]
    pyramid = load_media_pyramid(entry, root)

    assert entry["peaks"] == f"{entry['path']}{peaks_cache.SUFFIX}"
    assert (root / entry["peaks"]).is_file()
    assert pyramid is not None
    assert pyramid.n_frames == loaded_clip.buffer.n_frames
    assert envelopes_match(PeakPyramid(loaded_clip.buffer.data), pyramid, n_bins=64)


def test_a_bundle_saved_without_peak_caching_still_opens(
    loaded_clip: LoadedAudio, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The key is optional, so a reader must cope with it being absent."""
    monkeypatch.setenv(peaks_cache.ENV_ENABLED, "0")
    root = save_multitrack_project(tmp_path / "session.hlproj", loaded_clip)

    entry = load_project(root).multitrack["media"][0]

    assert "peaks" not in entry
    assert not list((root / "media").glob(f"*{peaks_cache.SUFFIX}"))
    monkeypatch.delenv(peaks_cache.ENV_ENABLED)
    assert load_media_pyramid(entry, root) is None


def test_a_stale_media_sidecar_is_not_restored(
    loaded_clip: LoadedAudio, tmp_path: Path
) -> None:
    root = save_multitrack_project(tmp_path / "session.hlproj", loaded_clip)
    entry = load_project(root).multitrack["media"][0]
    media = root / str(entry["path"])

    stat = media.stat()
    os.utime(media, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))

    assert load_media_pyramid(entry, root) is None


def test_the_engine_honours_a_disabled_cache(
    audio_file: tuple[Path, np.ndarray], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = audio_file
    monkeypatch.setenv(peaks_cache.ENV_ENABLED, "0")
    engine = AudioEngine(NullOutput(realtime=False), block_size=256)
    try:
        engine.load(path)
    finally:
        engine.shutdown()

    assert not peaks_cache.sidecar_path(path).exists()
