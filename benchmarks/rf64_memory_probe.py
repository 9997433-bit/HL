#!/usr/bin/env python3
"""RF64 streaming-memory probe: >4 GiB of audio through a bounded RSS.

SOTA checklist item B3 asks for evidence that a >4 GB RF64 capture streams
with the process staying under 1 GiB resident. A multi-gigabyte fixture cannot
live in the repository, so this probe creates one locally and measures the
real code path against it:

* **dense**: sequentially writes every byte of a non-silent PCM_16 payload,
  flushes it to disk, verifies that at least 95% of the apparent file size is
  physically allocated, and streams the whole file through
  :class:`StreamingSampleSource`. This is the only mode eligible for
  ``--formal`` because it exercises actual storage I/O rather than holes.
* **sparse** (default): hand-assembles a syntactically real RF64 header
  (EBU Tech 3306 ``ds64`` chunk carrying the 64-bit sizes) and extends the
  file to its full declared size with ``os.truncate``, so the filesystem
  backs the >4 GiB of PCM with a hole. libsndfile parses and decodes it
  exactly as it would a real capture — every block goes through the same
  seek/read/convert machinery :class:`StreamingSampleSource` uses in
  production — while the disk stores a few kilobytes.
* **mock**: no file at all. A stand-in libsndfile handle synthesises
  zero blocks with the same call signature, for hosts whose libsndfile
  lacks RF64 or whose filesystem cannot hold the sparse fixture.

Every mode then drives ``read_into`` over the full declared frame
count with one reused block buffer — the feeder thread's exact access
pattern — sampling the resident set as it goes, and writes a JSON report.

Sparse and mock runs are headless proxies and always record
``formal_slo_verified: false``. A formal run must explicitly select dense
mode; the report remains honest that its PCM is generated rather than a live
input capture. B3 is a file-size/RSS SLO, so source provenance does not alter
the measured storage/decode path, while physical allocation does.

Examples::

    python3 benchmarks/rf64_memory_probe.py --mode dense --formal
    python3 benchmarks/rf64_memory_probe.py                 # sparse proxy
    python3 benchmarks/rf64_memory_probe.py --mode mock     # no disk involved
    python3 benchmarks/rf64_memory_probe.py --frames 100000000  # quick smoke
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import platform
import struct
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
AUDIO_STUDIO_ROOT = REPOSITORY_ROOT / "audio-studio"
if str(AUDIO_STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(AUDIO_STUDIO_ROOT))

from audio_studio.core.large_file import should_stream, sniff_container
from audio_studio.core.sample_source import (
    DEFAULT_BLOCK_FRAMES,
    DEFAULT_CACHE_BLOCKS,
    StreamingSampleSource,
)

#: The B3 thresholds: the container must exceed 4 GB and the process must
#: stay under 1 GiB resident while streaming it.
FILE_SIZE_MIN_BYTES: int = 4 * 1024**3
PEAK_RSS_MAX_BYTES: int = 1024**3

#: Default fixture: 16-bit stereo at 48 kHz, ~6.4 hours. The PCM payload is
#: 4.4 GB — comfortably past the 4 GiB RIFF horizon that RF64 exists for.
DEFAULT_FRAMES: int = 1_100_000_000
DEFAULT_CHANNELS: int = 2
DEFAULT_SAMPLE_RATE: int = 48_000
BYTES_PER_SAMPLE_PCM16: int = 2
DEFAULT_WRITE_CHUNK_FRAMES: int = 1_048_576
DENSE_ALLOCATION_MIN_RATIO: float = 0.95

DEFAULT_REPORT_PATH = REPOSITORY_ROOT / ".agent_workspace/v1.0/rf64-memory-report.json"


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Headless RF64 4GB streaming RSS probe (SOTA B3 proxy).",
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "dense", "sparse", "mock"),
        default="auto",
        help="dense: sequentially write and decode every PCM byte; sparse: "
        "decode a sparse >4GB RF64 file; mock: synthesised handle, no disk; "
        "auto: sparse with mock fallback",
    )
    parser.add_argument("--frames", type=int, default=DEFAULT_FRAMES)
    parser.add_argument("--channels", type=int, default=DEFAULT_CHANNELS)
    parser.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE)
    parser.add_argument(
        "--block-frames",
        type=int,
        default=DEFAULT_BLOCK_FRAMES,
        help="frames per streaming block (the production default)",
    )
    parser.add_argument(
        "--cache-blocks",
        type=int,
        default=DEFAULT_CACHE_BLOCKS,
        help="LRU depth of the streaming source (the production default)",
    )
    parser.add_argument(
        "--rss-sample-every",
        type=int,
        default=64,
        help="sample the resident set every N blocks read",
    )
    parser.add_argument(
        "--write-chunk-frames",
        type=int,
        default=DEFAULT_WRITE_CHUNK_FRAMES,
        help="frames per sequential write when creating a dense fixture",
    )
    parser.add_argument(
        "--max-rss-bytes",
        type=int,
        default=PEAK_RSS_MAX_BYTES,
        help="fail when the peak resident set exceeds this (default 1 GiB)",
    )
    parser.add_argument(
        "--scratch-dir",
        type=Path,
        default=None,
        help="where the on-disk fixture is created (default: a temp dir)",
    )
    parser.add_argument(
        "--formal",
        action="store_true",
        help="request formal evidence; requires --mode dense and only verifies "
        "after the dense-allocation and SLO checks pass",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help=f"JSON report path (default: {DEFAULT_REPORT_PATH})",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="suppress progress lines on stderr"
    )
    args = parser.parse_args(argv)
    if args.formal and args.mode != "dense":
        parser.error("--formal requires --mode dense; sparse/mock fixtures cannot be formal")
    if args.frames <= 0 or args.channels <= 0 or args.sample_rate <= 0:
        parser.error("--frames, --channels, and --sample-rate must be positive")
    if args.block_frames <= 0 or args.cache_blocks <= 0:
        parser.error("--block-frames and --cache-blocks must be positive")
    if args.rss_sample_every <= 0 or args.write_chunk_frames <= 0:
        parser.error("--rss-sample-every and --write-chunk-frames must be positive")
    return args


def _progress(quiet: bool, message: str) -> None:
    if not quiet:
        print(f"[rf64-probe] {message}", file=sys.stderr, flush=True)


# --------------------------------------------------------------------- RSS


def _current_rss_bytes() -> int:
    """The process's resident set right now, in bytes."""
    try:
        with open("/proc/self/statm", encoding="ascii") as handle:
            return int(handle.read().split()[1]) * os.sysconf("SC_PAGE_SIZE")
    except (OSError, ValueError):
        return _high_water_rss_bytes()  # non-Linux: the high-water mark stands in


def _high_water_rss_bytes() -> int:
    """The kernel's own peak-RSS accounting (ru_maxrss)."""
    import resource

    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak) if sys.platform == "darwin" else int(peak) * 1024


# --------------------------------------------------------- the RF64 fixture


def _rf64_header(*, n_frames: int, channels: int, sample_rate: int) -> bytes:
    """Return an EBU Tech 3306 PCM_16 RF64 header."""
    if n_frames <= 0 or channels <= 0 or sample_rate <= 0:
        raise ValueError("n_frames, channels, and sample_rate must be positive")

    block_align = channels * BYTES_PER_SAMPLE_PCM16
    data_size = n_frames * block_align
    riff_size = 4 + (8 + 28) + (8 + 16) + (8 + data_size)

    header = bytearray()
    header += b"RF64" + struct.pack("<I", 0xFFFFFFFF) + b"WAVE"
    header += b"ds64" + struct.pack("<I", 28)
    header += struct.pack("<Q", riff_size)  # riffSize
    header += struct.pack("<Q", data_size)  # dataSize
    header += struct.pack("<Q", n_frames)  # sampleCount
    header += struct.pack("<I", 0)  # tableLength: no oversized aux chunks
    header += b"fmt " + struct.pack(
        "<IHHIIHH",
        16,  # fmt chunk size
        1,  # WAVE_FORMAT_PCM
        channels,
        sample_rate,
        sample_rate * block_align,
        block_align,
        BYTES_PER_SAMPLE_PCM16 * 8,
    )
    header += b"data" + struct.pack("<I", 0xFFFFFFFF)
    return bytes(header)


def _allocation_evidence(path: Path) -> tuple[int, float]:
    """Return allocated bytes and their ratio to apparent file size."""
    stat = path.stat()
    if hasattr(stat, "st_blocks"):
        allocated_bytes = int(stat.st_blocks) * 512
    elif os.name == "nt":
        # Windows exposes sparse/compressed allocation through this API rather
        # than os.stat(). GetCompressedFileSizeW returns the physical byte
        # count even when the file itself is not compressed.
        import ctypes
        from ctypes import wintypes

        high = wintypes.DWORD()
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        get_size = kernel32.GetCompressedFileSizeW
        get_size.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
        get_size.restype = wintypes.DWORD
        ctypes.set_last_error(0)
        low = get_size(str(path), ctypes.byref(high))
        error = ctypes.get_last_error()
        if low == 0xFFFFFFFF and error:
            raise OSError(error, "GetCompressedFileSizeW failed", str(path))
        allocated_bytes = (int(high.value) << 32) | int(low)
    else:
        # Unknown allocation is deliberately ineligible for formal evidence.
        allocated_bytes = 0
    ratio = allocated_bytes / stat.st_size if stat.st_size else 0.0
    return allocated_bytes, ratio


def write_sparse_rf64(
    path: Path, *, n_frames: int, channels: int, sample_rate: int
) -> dict[str, Any]:
    """Assemble an RF64 header and extend the PCM payload with a hole."""
    header = _rf64_header(
        n_frames=n_frames,
        channels=channels,
        sample_rate=sample_rate,
    )
    data_size = n_frames * channels * BYTES_PER_SAMPLE_PCM16

    with open(path, "wb") as handle:
        handle.write(header)
    os.truncate(path, len(header) + data_size)
    allocated_bytes, allocated_ratio = _allocation_evidence(path)
    return {
        "file_size_bytes": len(header) + data_size,
        "pcm_bytes_written": 0,
        "write_method": "sparse-truncate",
        "write_chunk_frames": None,
        "payload_sha256": None,
        "allocated_bytes": allocated_bytes,
        "allocated_ratio": round(allocated_ratio, 6),
        "dense_allocation_verified": False,
        "pcm_content": "zero-filled sparse hole",
    }


def write_dense_rf64(
    path: Path,
    *,
    n_frames: int,
    channels: int,
    sample_rate: int,
    write_chunk_frames: int = DEFAULT_WRITE_CHUNK_FRAMES,
) -> dict[str, Any]:
    """Sequentially write a physically allocated, non-silent PCM_16 RF64.

    The bounded deterministic PCM chunk is reused so fixture creation does not
    scale resident memory with file size. ``fsync`` precedes allocation
    accounting so delayed writes cannot make a sparse file look dense.
    """
    if write_chunk_frames <= 0:
        raise ValueError("write_chunk_frames must be positive")
    header = _rf64_header(
        n_frames=n_frames,
        channels=channels,
        sample_rate=sample_rate,
    )
    block_align = channels * BYTES_PER_SAMPLE_PCM16
    data_size = n_frames * block_align
    pattern_frames = min(write_chunk_frames, n_frames)
    sample_indexes = np.arange(pattern_frames * channels, dtype=np.uint32)
    pattern = ((sample_indexes * 1103 + 12345) & 0xFFFF).astype("<u2").view("<i2")
    pattern_bytes = pattern.tobytes()
    del pattern, sample_indexes

    payload_digest = hashlib.sha256()
    pcm_bytes_written = 0
    frames_written = 0
    started = time.perf_counter()
    with open(path, "wb", buffering=4 * 1024**2) as handle:
        handle.write(header)
        while frames_written < n_frames:
            take_frames = min(pattern_frames, n_frames - frames_written)
            chunk = pattern_bytes[: take_frames * block_align]
            written = handle.write(chunk)
            if written != len(chunk):
                raise OSError(f"short RF64 fixture write: {written} of {len(chunk)} bytes")
            payload_digest.update(chunk)
            pcm_bytes_written += written
            frames_written += take_frames
        handle.flush()
        os.fsync(handle.fileno())

    stat = path.stat()
    expected_size = len(header) + data_size
    if stat.st_size != expected_size or pcm_bytes_written != data_size:
        raise OSError(
            "dense RF64 fixture size mismatch: "
            f"file={stat.st_size}, expected={expected_size}, "
            f"PCM written={pcm_bytes_written}, expected PCM={data_size}"
        )
    allocated_bytes, allocated_ratio = _allocation_evidence(path)
    return {
        "file_size_bytes": stat.st_size,
        "pcm_bytes_written": pcm_bytes_written,
        "write_method": "sequential-chunked-write",
        "write_chunk_frames": write_chunk_frames,
        "write_wall_clock_seconds": round(time.perf_counter() - started, 3),
        "payload_sha256": payload_digest.hexdigest(),
        "allocated_bytes": allocated_bytes,
        "allocated_ratio": round(allocated_ratio, 6),
        "dense_allocation_verified": allocated_ratio >= DENSE_ALLOCATION_MIN_RATIO,
        "pcm_content": "deterministic non-silent generated PCM_16",
    }


# ---------------------------------------------------------- the mock handle


class _MockRF64Handle:
    """A libsndfile handle stand-in that synthesises silence on demand.

    Implements exactly the surface :class:`StreamingSampleSource` touches, so
    the source's own block/cache/clamping machinery is still what is being
    measured — only the decode itself is simulated.
    """

    def __init__(self, *, n_frames: int, channels: int, sample_rate: int) -> None:
        self.frames = n_frames
        self.channels = channels
        self.samplerate = sample_rate
        self.subtype = "PCM_16"
        self.format = "RF64"
        self._position = 0

    def seek(self, frames: int) -> int:
        self._position = max(0, min(int(frames), self.frames))
        return self._position

    def read(
        self,
        frames: int,
        dtype: str = "float32",
        always_2d: bool = True,
        fill_value: float | None = None,
    ) -> np.ndarray:
        del dtype, always_2d, fill_value  # signature parity with soundfile
        take = max(0, min(int(frames), self.frames - self._position))
        self._position += take
        # A fresh array per call, matching the binding's own allocation.
        return np.zeros((take, self.channels), dtype=np.float32)

    def close(self) -> None:
        return


@contextlib.contextmanager
def _mock_soundfile(handle: _MockRF64Handle):
    """Route StreamingSampleSource's ``sf.SoundFile(...)`` to the mock."""
    import soundfile as sf

    real = sf.SoundFile
    sf.SoundFile = lambda path, mode="r": handle
    try:
        yield
    finally:
        sf.SoundFile = real


# ------------------------------------------------------------ the read loop


def _read_loop(
    source: StreamingSampleSource, args: argparse.Namespace
) -> dict[str, Any]:
    """Stream the whole source through one reused buffer, sampling RSS."""
    block = int(args.block_frames)
    out = np.empty((block, args.channels), dtype=np.float32)
    total = source.n_frames
    total_blocks = (total + block - 1) // block
    report_every = max(total_blocks // 10, 1)

    baseline_rss = _current_rss_bytes()
    peak_rss = baseline_rss
    frames_read = 0
    blocks_read = 0

    started = time.perf_counter()
    position = 0
    while position < total:
        got = source.read_into(out[: min(block, total - position)], position)
        if got == 0:
            break
        frames_read += got
        position += got
        blocks_read += 1
        if blocks_read % args.rss_sample_every == 0:
            peak_rss = max(peak_rss, _current_rss_bytes())
        if blocks_read % report_every == 0:
            _progress(
                args.quiet,
                f"{position / total * 100.0:5.1f}% "
                f"({position:,} frames), rss={peak_rss / 2**20:,.1f} MiB",
            )
    wall_seconds = time.perf_counter() - started
    # ru_maxrss sees allocation spikes the sampling loop can miss; take the
    # stricter of the two so the number cannot flatter the implementation.
    peak_rss = max(peak_rss, _current_rss_bytes(), _high_water_rss_bytes())

    audio_seconds = frames_read / args.sample_rate
    return {
        "n_frames": total,
        "frames_read": frames_read,
        "blocks_read": blocks_read,
        "audio_hours_read": round(audio_seconds / 3600.0, 3),
        "baseline_rss_bytes": baseline_rss,
        "peak_rss_bytes": peak_rss,
        "peak_rss_mib": round(peak_rss / 2**20, 1),
        "rss_growth_bytes": peak_rss - baseline_rss,
        "wall_clock_seconds": round(wall_seconds, 3),
        "realtime_factor": round(audio_seconds / wall_seconds, 1) if wall_seconds else None,
    }


def _sparse_supported() -> bool:
    try:
        import soundfile as sf

        return "RF64" in sf.available_formats()
    except Exception:  # noqa: BLE001 - a broken binding means: mock
        return False


def run_probe(args: argparse.Namespace) -> dict[str, Any]:
    """Run the probe and return the JSON-serializable report."""
    mode = args.mode
    if mode == "auto":
        mode = "sparse" if _sparse_supported() else "mock"

    pcm_bytes = args.frames * args.channels * BYTES_PER_SAMPLE_PCM16
    if mode in {"dense", "sparse"}:
        scratch = (
            tempfile.TemporaryDirectory(prefix="rf64-probe-")
            if args.scratch_dir is None
            else contextlib.nullcontext(str(args.scratch_dir))
        )
        with scratch as scratch_dir:
            fixture = Path(scratch_dir) / f"{mode}-4gb.rf64"
            fixture.parent.mkdir(parents=True, exist_ok=True)
            if mode == "dense":
                _progress(
                    args.quiet,
                    f"writing {pcm_bytes / 2**30:.2f} GiB dense PCM "
                    f"in {args.write_chunk_frames:,}-frame chunks",
                )
                fixture_evidence = write_dense_rf64(
                    fixture,
                    n_frames=args.frames,
                    channels=args.channels,
                    sample_rate=args.sample_rate,
                    write_chunk_frames=args.write_chunk_frames,
                )
            else:
                fixture_evidence = write_sparse_rf64(
                    fixture,
                    n_frames=args.frames,
                    channels=args.channels,
                    sample_rate=args.sample_rate,
                )
            file_size = fixture_evidence["file_size_bytes"]
            _progress(
                args.quiet,
                f"{mode} fixture: {file_size / 2**30:.2f} GiB apparent, "
                f"{fixture_evidence['allocated_bytes'] / 2**30:.2f} GiB allocated "
                f"({fixture_evidence['allocated_ratio']:.3f} ratio)",
            )
            container = sniff_container(fixture)
            streams = should_stream(fixture)
            with StreamingSampleSource(
                fixture,
                block_frames=args.block_frames,
                cache_blocks=args.cache_blocks,
            ) as source:
                measured = _read_loop(source, args)
    else:
        file_size = pcm_bytes  # the container the mock stands in for
        fixture_evidence = {
            "file_size_bytes": file_size,
            "pcm_bytes_written": 0,
            "write_method": "mock-no-file",
            "write_chunk_frames": None,
            "payload_sha256": None,
            "allocated_bytes": 0,
            "allocated_ratio": 0.0,
            "dense_allocation_verified": False,
            "pcm_content": "synthesised zero blocks",
        }
        container = "RF64"
        streams = True
        handle = _MockRF64Handle(
            n_frames=args.frames,
            channels=args.channels,
            sample_rate=args.sample_rate,
        )
        with _mock_soundfile(handle):
            source = StreamingSampleSource(
                "mock://sparse-4gb.rf64",
                block_frames=args.block_frames,
                cache_blocks=args.cache_blocks,
            )
        with source:
            measured = _read_loop(source, args)

    measured["container"] = container
    measured["should_stream"] = bool(streams)
    measured["file_size_bytes"] = file_size

    passed = (
        file_size > FILE_SIZE_MIN_BYTES
        and measured["peak_rss_bytes"] < args.max_rss_bytes
        and measured["frames_read"] == args.frames
        and container == "RF64"
    )
    formal_eligible = (
        mode == "dense"
        and fixture_evidence["dense_allocation_verified"] is True
        and fixture_evidence["pcm_bytes_written"] == pcm_bytes
        and fixture_evidence["payload_sha256"] is not None
    )
    formal_verified = bool(args.formal and formal_eligible and passed)
    evidence = "direct-dense" if mode == "dense" else "headless-proxy"
    if formal_verified:
        limitation = (
            "Direct isolated-VM measurement against fully allocated generated PCM; "
            "this proves the file-size/RSS streaming SLO, not live-input capture "
            "provenance."
        )
    elif mode == "dense":
        limitation = (
            "Dense direct measurement was not formalised because either --formal "
            "was absent, physical allocation was below 95%, or an SLO check failed."
        )
    else:
        limitation = (
            "zero-filled fixture on a shared host: the decode path, block "
            "cache and RSS ceiling are real, but the content is synthetic "
            "and physical storage I/O is not exercised."
        )
    result = {
        "slo_id": "rf64-4gb-rss",
        "title": (
            f"{file_size / 2**30:.1f} GiB RF64 streaming read loop under "
            f"{args.max_rss_bytes / 2**30:g} GiB RSS ({mode} fixture)"
        ),
        "status": "pass" if passed else "fail",
        "threshold_pass": passed,
        "evidence": evidence,
        "formal_slo_verified": formal_verified,
        "measured": measured,
        "threshold": {
            "file_size_bytes_min": FILE_SIZE_MIN_BYTES,
            "peak_rss_bytes_max": args.max_rss_bytes,
        },
        "limitation": limitation,
    }
    return {
        "schema_version": 1,
        "harness": "benchmarks/rf64_memory_probe.py",
        "checklist_item": "B3",
        "mode": mode,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor() or "unknown",
        },
        "config": {
            "frames": args.frames,
            "channels": args.channels,
            "sample_rate": args.sample_rate,
            "subtype": "PCM_16",
            "block_frames": args.block_frames,
            "cache_blocks": args.cache_blocks,
            "rss_sample_every_blocks": args.rss_sample_every,
            "write_chunk_frames": args.write_chunk_frames,
        },
        "fixture": fixture_evidence,
        "formal_requested": bool(args.formal),
        # Top-level copies of what the B3 verifier reads.
        "file_size_bytes": file_size,
        "peak_rss_bytes": measured["peak_rss_bytes"],
        "status": result["status"],
        "formal_slo_verified": result["formal_slo_verified"],
        "results": [result],
        "summary": {
            "passed": int(passed),
            "failed": int(not passed),
            "formal_slos_verified": int(formal_verified),
        },
    }


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = run_probe(args)
    rendered = json.dumps(report, indent=2)
    print(rendered)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
        _progress(args.quiet, f"report written to {args.output}")
    if args.formal:
        return 0 if report["formal_slo_verified"] else 1
    return 0 if report["results"][0]["threshold_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
