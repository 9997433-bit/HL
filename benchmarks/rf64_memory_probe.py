#!/usr/bin/env python3
"""Headless RF64 streaming-memory probe: 4 GB of audio through a bounded RSS.

SOTA checklist item B3 asks for evidence that a >4 GB RF64 capture streams
with the process staying under 1 GiB resident. A real multi-gigabyte fixture
cannot live in the repository, so this probe manufactures the next best
thing and measures the real code path against it:

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

Either way the probe then drives ``read_into`` over the full declared frame
count with one reused block buffer — the feeder thread's exact access
pattern — sampling the resident set as it goes, and writes a JSON report.

This is a headless *proxy*, not formal hardware evidence: the content is
silence and the host is shared, so the JSON records
``formal_slo_verified: false`` unless ``--formal`` is passed (which is only
honest on dedicated hardware against a real capture). The B3 verifier in
``tests/acceptance/test_sota_checklist.py`` accepts this report as the pass
signal only when ``formal_slo_verified`` is true; until then B3 stays an
xfail with the proxy numbers on the record.

Examples::

    python3 benchmarks/rf64_memory_probe.py                 # full 4.4 GB pass
    python3 benchmarks/rf64_memory_probe.py --mode mock     # no disk involved
    python3 benchmarks/rf64_memory_probe.py --frames 100000000  # quick smoke
"""

from __future__ import annotations

import argparse
import contextlib
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

DEFAULT_REPORT_PATH = REPOSITORY_ROOT / ".agent_workspace/v1.0/rf64-memory-report.json"


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Headless RF64 4GB streaming RSS probe (SOTA B3 proxy).",
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "sparse", "mock"),
        default="auto",
        help="sparse: real libsndfile decode of a sparse >4GB RF64 file; "
        "mock: synthesised handle, no disk; auto: sparse with mock fallback",
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
        "--max-rss-bytes",
        type=int,
        default=PEAK_RSS_MAX_BYTES,
        help="fail when the peak resident set exceeds this (default 1 GiB)",
    )
    parser.add_argument(
        "--scratch-dir",
        type=Path,
        default=None,
        help="where the sparse fixture is created (default: a temp dir)",
    )
    parser.add_argument(
        "--formal",
        action="store_true",
        help="record formal_slo_verified: true — only defensible on dedicated "
        "hardware against a real (non-sparse) capture",
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
    return parser.parse_args(argv)


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


# ---------------------------------------------------- the sparse RF64 file


def write_sparse_rf64(
    path: Path, *, n_frames: int, channels: int, sample_rate: int
) -> int:
    """Assemble a PCM_16 RF64 header and extend the file to size with a hole.

    Chunk sizes past 4 GiB live in the ``ds64`` chunk (EBU Tech 3306); the
    RIFF-level and data-level 32-bit size fields carry the 0xFFFFFFFF
    sentinel exactly as a real writer would emit them. Returns the apparent
    file size in bytes.
    """
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

    with open(path, "wb") as handle:
        handle.write(bytes(header))
    os.truncate(path, len(header) + data_size)
    return len(header) + data_size


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
    sf.SoundFile = lambda path, mode="r": handle  # noqa: ARG005 - path unused
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
    if mode == "sparse":
        scratch = (
            tempfile.TemporaryDirectory(prefix="rf64-probe-")
            if args.scratch_dir is None
            else contextlib.nullcontext(str(args.scratch_dir))
        )
        with scratch as scratch_dir:
            fixture = Path(scratch_dir) / "sparse-4gb.rf64"
            file_size = write_sparse_rf64(
                fixture,
                n_frames=args.frames,
                channels=args.channels,
                sample_rate=args.sample_rate,
            )
            _progress(
                args.quiet,
                f"sparse fixture: {file_size / 2**30:.2f} GiB apparent, "
                f"{os.stat(fixture).st_blocks * 512 / 2**10:.0f} KiB on disk",
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
    evidence = "direct" if args.formal else "headless-proxy"
    limitation = (
        "real hardware run declared formal by the operator"
        if args.formal
        else (
            "zero-filled fixture on a shared host: the decode path, block "
            "cache and RSS ceiling are real, but the content is synthetic "
            "and no dedicated-hardware capture was involved."
        )
    )
    result = {
        "slo_id": "rf64-4gb-rss",
        "title": (
            f"{file_size / 2**30:.1f} GiB RF64 streaming read loop under "
            f"{args.max_rss_bytes / 2**30:g} GiB RSS ({mode} proxy)"
        ),
        "status": "pass" if passed else "fail",
        "threshold_pass": passed,
        "evidence": evidence,
        "formal_slo_verified": bool(args.formal),
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
        },
        # Top-level copies of what the B3 verifier reads.
        "file_size_bytes": file_size,
        "peak_rss_bytes": measured["peak_rss_bytes"],
        "status": result["status"],
        "formal_slo_verified": result["formal_slo_verified"],
        "results": [result],
        "summary": {
            "proxy_passed": int(passed),
            "proxy_failed": int(not passed),
            "formal_slos_verified": int(passed and args.formal),
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
    return 0 if report["results"][0]["threshold_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
