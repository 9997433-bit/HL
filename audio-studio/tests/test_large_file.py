"""RF64/W64 large-file support: detection, 64-bit frame counts, the memory budget.

The containers exist because RIFF chunk sizes are 32-bit, so the properties
under test are policies rather than DSP: a 64-bit container is *recognised*
without decoding it, frame counts survive past 2**31 as plain Python ints, and
the full-decode path refuses (helpfully) what would not fit in memory. Real
multi-gigabyte fixtures are obviously out of the question, so the >2**31 cases
mock the header of a small file — which is faithful to the failure mode, since
the frame count lives in the header.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from audio_studio.core.large_file import (
    DEFAULT_MEMORY_BUDGET_BYTES,
    MemoryBudgetError,
    check_memory_budget,
    estimated_decoded_bytes,
    is_large_container,
    should_stream,
    sniff_container,
)
from audio_studio.core.loader import (
    SUPPORTED_EXTENSIONS,
    AudioLoadError,
    load_audio,
    probe,
    probe_frames,
    save_audio,
    supported_formats,
)
from audio_studio.core.sample_source import StreamingSampleSource
from audio_studio.core.types import AudioBuffer, TimeRange

SR = 48_000
N_FRAMES = 12_000

HAS_RF64 = "RF64" in sf.available_formats()
HAS_W64 = "W64" in sf.available_formats()

#: A frame count no real fixture can have: ~9.5 hours past the int32 horizon.
HUGE_FRAMES = 2**35


def ramp(n_frames: int = N_FRAMES, channels: int = 2) -> AudioBuffer:
    """Non-repeating float32 material, so a roundtrip mismatch cannot hide."""
    data = np.linspace(-0.9, 0.9, n_frames * channels, dtype=np.float32)
    return AudioBuffer(data.reshape(n_frames, channels), SR)


@pytest.fixture(scope="module")
def buffer() -> AudioBuffer:
    return ramp()


@pytest.fixture(scope="module")
def wav_file(tmp_path_factory: pytest.TempPathFactory, buffer: AudioBuffer) -> Path:
    path = tmp_path_factory.mktemp("large") / "plain.wav"
    save_audio(path, buffer, subtype="FLOAT")
    return path


@pytest.fixture(scope="module")
def rf64_file(tmp_path_factory: pytest.TempPathFactory, buffer: AudioBuffer) -> Path:
    if not HAS_RF64:
        pytest.skip("this libsndfile build cannot write RF64")
    path = tmp_path_factory.mktemp("large") / "capture.rf64"
    save_audio(path, buffer, subtype="FLOAT")
    return path


@pytest.fixture(scope="module")
def w64_file(tmp_path_factory: pytest.TempPathFactory, buffer: AudioBuffer) -> Path:
    if not HAS_W64:
        pytest.skip("this libsndfile build cannot write W64")
    path = tmp_path_factory.mktemp("large") / "capture.w64"
    save_audio(path, buffer, subtype="FLOAT")
    return path


# ---------------------------------------------------------------------------
# container detection
# ---------------------------------------------------------------------------


def test_sniff_identifies_each_container(wav_file: Path, rf64_file: Path, w64_file: Path) -> None:
    assert sniff_container(wav_file) is None  # plain RIFF is not a 64-bit container
    assert sniff_container(rf64_file) == "RF64"
    assert sniff_container(w64_file) == "W64"


def test_sniff_survives_unreadable_paths(tmp_path: Path) -> None:
    assert sniff_container(tmp_path / "missing.rf64") is None
    empty = tmp_path / "empty.w64"
    empty.write_bytes(b"")
    assert sniff_container(empty) is None


def test_bw64_magic_is_recognised(tmp_path: Path) -> None:
    """ITU-R BS.2088 files carry 'BW64' at offset 0 but are otherwise RF64."""
    path = tmp_path / "broadcast.wav"
    path.write_bytes(b"BW64" + b"\x00" * 28)
    assert sniff_container(path) == "BW64"
    assert is_large_container(path)


def test_the_header_identifies_a_large_container_whatever_the_name(
    rf64_file: Path, tmp_path: Path
) -> None:
    """An RF64 handed over as `.wav` must still be treated as RF64."""
    disguised = tmp_path / "innocent.wav"
    disguised.write_bytes(rf64_file.read_bytes())
    assert is_large_container(disguised)


def test_the_suffix_is_the_fallback_when_the_file_is_unreadable(tmp_path: Path) -> None:
    assert is_large_container(tmp_path / "missing.rf64")
    assert is_large_container(tmp_path / "missing.w64")
    assert not is_large_container(tmp_path / "missing.wav")


def test_a_plain_wav_is_not_a_large_container(wav_file: Path) -> None:
    assert not is_large_container(wav_file)


def test_rf64_and_w64_are_advertised_formats() -> None:
    assert ".rf64" in SUPPORTED_EXTENSIONS
    assert ".w64" in SUPPORTED_EXTENSIONS
    formats = supported_formats()
    assert ".rf64" in formats
    assert ".w64" in formats
    if HAS_RF64:
        assert formats[".rf64"]
    if HAS_W64:
        assert formats[".w64"]


def test_probe_reports_the_64_bit_containers(rf64_file: Path, w64_file: Path) -> None:
    assert probe(rf64_file).container == "RF64"
    assert probe(w64_file).container == "W64"


# ---------------------------------------------------------------------------
# 64-bit frame counts
# ---------------------------------------------------------------------------


def test_probe_frames_returns_a_python_int(wav_file: Path) -> None:
    frames = probe_frames(wav_file)
    assert frames == N_FRAMES
    assert type(frames) is int


def test_probe_frames_normalises_error_reporting(tmp_path: Path) -> None:
    with pytest.raises(AudioLoadError, match="Cannot read audio metadata"):
        probe_frames(tmp_path / "missing.wav")


class _HugeHeader:
    """Wrap a real libsndfile handle but lie about the frame count.

    This is exactly what a >4 GB RF64 looks like to the streaming source: the
    header says 2**35 frames, and nothing but the header has been read yet.
    The count is a numpy int64, as the binding may deliver, to prove that the
    source normalises it to a Python int.
    """

    def __init__(self, real: sf.SoundFile) -> None:
        self._real = real

    @property
    def frames(self) -> np.int64:
        return np.int64(HUGE_FRAMES)

    def __getattr__(self, name: str):  # noqa: ANN204 - pure passthrough
        return getattr(self._real, name)


def test_streaming_source_reports_frames_past_2_31(
    wav_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_ctor = sf.SoundFile
    monkeypatch.setattr(
        sf, "SoundFile", lambda path, mode="r": _HugeHeader(real_ctor(path, mode=mode))
    )

    with StreamingSampleSource(wav_file) as source:
        assert source.n_frames == HUGE_FRAMES
        assert source.n_frames > 2**31
        assert type(source.n_frames) is int  # not a numpy scalar that could wrap
        assert source.duration == pytest.approx(HUGE_FRAMES / SR)

        # The frames that physically exist still stream normally...
        head = source.read(0, 64)
        assert head.shape == (64, 2)

        # ...and a read far past them zero-fills through the never-raise
        # surface instead of blowing up the feeder thread.
        out = np.full((32, 2), 7.0, dtype=np.float32)
        delivered = source.read_into(out, 2**33)
        assert delivered == 0
        assert np.all(out == 0.0)


def test_mocked_giant_files_are_flagged_for_streaming(
    wav_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_info = sf.info

    class _HugeInfo:
        def __init__(self, path: str) -> None:
            self._real = real_info(path)

        @property
        def frames(self) -> np.int64:
            return np.int64(HUGE_FRAMES)

        def __getattr__(self, name: str):  # noqa: ANN204 - pure passthrough
            return getattr(self._real, name)

    monkeypatch.setattr(sf, "info", lambda path: _HugeInfo(path))

    estimate = estimated_decoded_bytes(wav_file)
    assert estimate == HUGE_FRAMES * 2 * 4  # frames * channels * float32
    assert estimate > DEFAULT_MEMORY_BUDGET_BYTES  # 256 GiB: far past any budget
    assert should_stream(wav_file)
    with pytest.raises(MemoryBudgetError):
        check_memory_budget(wav_file)


# ---------------------------------------------------------------------------
# the memory budget guard
# ---------------------------------------------------------------------------


def test_small_files_pass_the_budget(wav_file: Path) -> None:
    estimate = check_memory_budget(wav_file)
    assert estimate == N_FRAMES * 2 * 4
    assert estimate < DEFAULT_MEMORY_BUDGET_BYTES


def test_the_refusal_directs_to_streaming_playback(wav_file: Path) -> None:
    with pytest.raises(MemoryBudgetError, match="streaming playback"):
        check_memory_budget(wav_file, budget_bytes=1_024)
    with pytest.raises(MemoryBudgetError, match="open_stream"):
        check_memory_budget(wav_file, budget_bytes=1_024)


def test_the_budget_error_is_a_load_error(wav_file: Path) -> None:
    """Existing `except AudioLoadError` handling must catch the refusal."""
    with pytest.raises(AudioLoadError):
        check_memory_budget(wav_file, budget_bytes=1_024)


def test_degenerate_budgets_are_rejected(wav_file: Path) -> None:
    with pytest.raises(ValueError, match="budget_bytes must be positive"):
        check_memory_budget(wav_file, budget_bytes=0)


def test_should_stream_decides_by_decoded_size(wav_file: Path) -> None:
    assert not should_stream(wav_file)  # 96 kB decoded: nowhere near the budget
    assert should_stream(wav_file, budget_bytes=1_024)


def test_a_small_rf64_is_not_forced_to_stream(rf64_file: Path) -> None:
    """The container alone is not a size; only the decoded estimate is."""
    assert not should_stream(rf64_file)


def test_an_unreadable_large_container_is_presumed_large(tmp_path: Path) -> None:
    garbage = tmp_path / "torn.rf64"
    garbage.write_bytes(b"RF64" + b"\x00" * 12)  # a header libsndfile rejects
    assert should_stream(garbage)

    plain_garbage = tmp_path / "torn.wav"
    plain_garbage.write_bytes(b"\x00" * 16)
    assert not should_stream(plain_garbage)


# ---------------------------------------------------------------------------
# RF64 / W64 roundtrips through the real codec
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_RF64, reason="libsndfile lacks RF64")
def test_rf64_export_roundtrip(tmp_path: Path, buffer: AudioBuffer, wav_file: Path) -> None:
    exported = save_audio(tmp_path / "bounce.rf64", buffer, subtype="FLOAT")

    assert sniff_container(exported) == "RF64"
    assert probe(exported).container == "RF64"
    assert probe_frames(exported) == buffer.n_frames

    loaded = load_audio(exported)
    assert loaded.buffer.sample_rate == SR
    assert np.array_equal(loaded.buffer.data, buffer.data)


@pytest.mark.skipif(not HAS_W64, reason="libsndfile lacks W64")
def test_w64_streams_bit_exactly(w64_file: Path, buffer: AudioBuffer) -> None:
    with StreamingSampleSource(w64_file, block_frames=4_096) as source:
        assert source.audio_format().container == "W64"
        assert source.n_frames == buffer.n_frames
        assert type(source.n_frames) is int
        assert np.array_equal(source.read(0, source.n_frames), buffer.data)


@pytest.mark.skipif(not HAS_RF64, reason="libsndfile lacks RF64")
def test_rf64_streams_bit_exactly(rf64_file: Path, buffer: AudioBuffer) -> None:
    with StreamingSampleSource(rf64_file, block_frames=4_096) as source:
        assert source.audio_format().container == "RF64"
        assert np.array_equal(source.read(0, source.n_frames), buffer.data)


# ---------------------------------------------------------------------------
# the editor uses sparse overlays for what it should stream
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("qapp")
def test_main_window_opens_large_files_as_streaming_edits(
    wav_file: Path, buffer: AudioBuffer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Over-budget files get an editable streaming session and no full decode."""
    from audio_studio.core.edit_session import StreamingEditSession
    from audio_studio.core.engine import AudioEngine
    from audio_studio.core.output import NullOutput
    from audio_studio.core.peaks import PeakPyramid
    from audio_studio.core.peaks_cache import write as write_peaks
    from audio_studio.ui import main_window as mw
    from audio_studio.ui.main_window import MainWindow

    # Shrink the budget so the 12k-frame fixture counts as "large".
    monkeypatch.setattr(mw, "DEFAULT_MEMORY_BUDGET_BYTES", 1_024)
    write_peaks(wav_file, PeakPyramid(buffer.data))

    window = MainWindow(AudioEngine(NullOutput(realtime=False), block_size=256))
    try:
        assert window.open_file(wav_file)

        assert window.engine.is_streaming
        assert window.engine.has_clip
        assert window.engine.clip is None  # nothing was decoded into RAM
        assert window.engine.pyramid is not None  # overview came from the .pk sidecar
        assert not window.engine.pyramid.has_samples
        assert window.engine.n_frames == N_FRAMES
        assert isinstance(window._edit_session, StreamingEditSession)  # noqa: SLF001
        assert not window.action_undo.isEnabled()
        assert not window.action_cut.isEnabled()  # no selection yet
        window.engine.set_selection(TimeRange(100, 200))
        window._update_edit_actions()  # noqa: SLF001 - exercise menu wiring
        assert window.action_cut.isEnabled()
        assert window.action_gain.isEnabled()

        # Whole-file analysis would materialise the samples; the guard skips it.
        assert window.audio_range(0, window.engine.n_frames) is None
        small = window.audio_range(0, 128)  # 1 kB: within budget, still served
        assert small is not None and small.shape == (128, 2)

        assert "streaming editable" in window.status_format.text().lower()
    finally:
        window._mark_project_saved()  # noqa: SLF001 - avoid a blocking close prompt
        window.close()


@pytest.mark.usefixtures("qapp")
def test_main_window_still_decodes_small_files(wav_file: Path) -> None:
    """Within budget nothing changes: full decode, editable session."""
    from audio_studio.core.engine import AudioEngine
    from audio_studio.core.output import NullOutput
    from audio_studio.ui.main_window import MainWindow

    window = MainWindow(AudioEngine(NullOutput(realtime=False), block_size=256))
    try:
        assert window.open_file(wav_file)

        assert not window.engine.is_streaming
        assert window._edit_session is not None  # noqa: SLF001 - editing stays on
    finally:
        window._mark_project_saved()  # noqa: SLF001 - avoid a blocking close prompt
        window.close()
