#!/usr/bin/env python3
"""Benchmark WAV loading, FFT throughput, latency, and memory use."""

from __future__ import annotations

import argparse
import json
import math
import platform
import resource
import statistics
import struct
import sys
import time
import tracemalloc
import wave
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MIN_SAMPLE_RATE = 8_000
MAX_SAMPLE_RATE = 384_000
MAX_CHANNELS = 32
DEFAULT_MAX_FRAMES = 100_000_000


class AudioProbeError(ValueError):
    """Raised when a WAV is invalid or exceeds a probe safety boundary."""


@dataclass(frozen=True)
class WavData:
    """Validated WAV metadata and interleaved PCM payload."""

    path: Path
    sample_rate: int
    channels: int
    sample_width: int
    frame_count: int
    payload: bytes

    @property
    def duration_seconds(self) -> float:
        return self.frame_count / self.sample_rate


def load_wav(path: Path, max_frames: int = DEFAULT_MAX_FRAMES) -> WavData:
    """Load a PCM WAV after checking metadata and declared allocation size."""
    path = Path(path)
    if max_frames <= 0:
        raise ValueError("max_frames must be positive")

    try:
        with wave.open(str(path), "rb") as source:
            channels = source.getnchannels()
            sample_width = source.getsampwidth()
            sample_rate = source.getframerate()
            frame_count = source.getnframes()
            compression = source.getcomptype()

            if compression != "NONE":
                raise AudioProbeError(f"{path}: compressed WAV is unsupported")
            if not 1 <= channels <= MAX_CHANNELS:
                raise AudioProbeError(f"{path}: invalid channel count {channels}")
            if sample_width not in (1, 2, 3, 4):
                raise AudioProbeError(
                    f"{path}: unsupported sample width {sample_width} bytes"
                )
            if not MIN_SAMPLE_RATE <= sample_rate <= MAX_SAMPLE_RATE:
                raise AudioProbeError(
                    f"{path}: sample rate {sample_rate} outside "
                    f"{MIN_SAMPLE_RATE}..{MAX_SAMPLE_RATE} Hz"
                )
            if frame_count > max_frames:
                raise AudioProbeError(
                    f"{path}: declared frame count {frame_count} exceeds "
                    f"safety limit {max_frames}"
                )

            expected_bytes = frame_count * channels * sample_width
            payload = source.readframes(frame_count)
            if len(payload) != expected_bytes:
                raise AudioProbeError(
                    f"{path}: truncated PCM payload "
                    f"({len(payload)} of {expected_bytes} bytes)"
                )
    except AudioProbeError:
        raise
    except (EOFError, OSError, struct.error, wave.Error) as error:
        raise AudioProbeError(f"{path}: invalid WAV: {error}") from error

    return WavData(
        path=path,
        sample_rate=sample_rate,
        channels=channels,
        sample_width=sample_width,
        frame_count=frame_count,
        payload=payload,
    )


def _fft(samples: list[float]) -> list[complex]:
    """Compute an in-place-style radix-2 FFT using only the standard library."""
    size = len(samples)
    if size == 0 or size & (size - 1):
        raise ValueError("FFT input length must be a non-zero power of two")

    values = [complex(sample, 0.0) for sample in samples]
    target = 0
    for source in range(1, size):
        bit = size >> 1
        while target & bit:
            target ^= bit
            bit >>= 1
        target ^= bit
        if source < target:
            values[source], values[target] = values[target], values[source]

    width = 2
    while width <= size:
        angle = -2.0 * math.pi / width
        root = complex(math.cos(angle), math.sin(angle))
        half = width // 2
        for start in range(0, size, width):
            twiddle = 1.0 + 0.0j
            for offset in range(half):
                even = values[start + offset]
                odd = values[start + offset + half] * twiddle
                values[start + offset] = even + odd
                values[start + offset + half] = even - odd
                twiddle *= root
        width *= 2
    return values


def _decode_first_channel_16bit(audio: WavData, count: int) -> list[float]:
    if audio.sample_width != 2:
        raise AudioProbeError("FFT benchmark currently requires 16-bit PCM")
    frame_width = audio.channels * audio.sample_width
    available = min(count, audio.frame_count)
    samples = []
    for frame in range(available):
        offset = frame * frame_width
        value = struct.unpack_from("<h", audio.payload, offset)[0]
        samples.append(value / 32_768.0)
    if not samples:
        raise AudioProbeError(f"{audio.path}: no samples available for FFT")
    while len(samples) < count:
        samples.extend(samples[: count - len(samples)])
    return samples


def _benchmark_loading(
    paths: list[Path], repetitions: int
) -> tuple[dict[str, Any], list[WavData]]:
    results: list[dict[str, Any]] = []
    loaded: list[WavData] = []
    for path in paths:
        elapsed_ms: list[float] = []
        audio: WavData | None = None
        for _ in range(repetitions):
            started = time.perf_counter_ns()
            audio = load_wav(path)
            elapsed_ms.append((time.perf_counter_ns() - started) / 1_000_000.0)
        assert audio is not None
        loaded.append(audio)
        size_bytes = path.stat().st_size
        median_ms = statistics.median(elapsed_ms)
        throughput = (
            (size_bytes / (1024 * 1024)) / (median_ms / 1_000.0)
            if median_ms
            else None
        )
        results.append(
            {
                "path": path.as_posix(),
                "size_bytes": size_bytes,
                "sample_rate_hz": audio.sample_rate,
                "channels": audio.channels,
                "frames": audio.frame_count,
                "duration_seconds": round(audio.duration_seconds, 6),
                "median_ms": round(median_ms, 6),
                "minimum_ms": round(min(elapsed_ms), 6),
                "throughput_mib_per_second": (
                    round(throughput, 3) if throughput is not None else None
                ),
            }
        )

    medians = [result["median_ms"] for result in results]
    return (
        {
            "repetitions_per_file": repetitions,
            "files": results,
            "aggregate": {
                "file_count": len(results),
                "total_bytes": sum(item["size_bytes"] for item in results),
                "median_of_file_medians_ms": round(statistics.median(medians), 6),
                "sum_of_file_medians_ms": round(sum(medians), 6),
            },
        },
        loaded,
    )


def _benchmark_fft(
    audio: WavData, fft_size: int, iterations: int
) -> tuple[dict[str, Any], list[float]]:
    samples = _decode_first_channel_16bit(audio, fft_size)
    _fft(samples)
    started = time.perf_counter()
    checksum = 0.0
    for _ in range(iterations):
        spectrum = _fft(samples)
        checksum += abs(spectrum[1])
    elapsed_seconds = time.perf_counter() - started
    transforms_per_second = iterations / elapsed_seconds
    return (
        {
            "implementation": "stdlib radix-2 Cooley-Tukey",
            "source": audio.path.as_posix(),
            "fft_size": fft_size,
            "iterations": iterations,
            "elapsed_seconds": round(elapsed_seconds, 6),
            "transforms_per_second": round(transforms_per_second, 3),
            "samples_per_second": round(transforms_per_second * fft_size, 3),
            "checksum": round(checksum, 6),
        },
        samples,
    )


def _estimate_playback_latency(
    audio_files: list[WavData],
    loading_report: dict[str, Any],
    buffer_frames: int,
) -> dict[str, Any]:
    load_by_path = {
        entry["path"]: entry["median_ms"] for entry in loading_report["files"]
    }
    estimates = []
    for sample_rate in sorted({audio.sample_rate for audio in audio_files}):
        matching = [
            load_by_path[audio.path.as_posix()]
            for audio in audio_files
            if audio.sample_rate == sample_rate
        ]
        median_load_ms = statistics.median(matching)
        buffer_ms = buffer_frames / sample_rate * 1_000.0
        estimates.append(
            {
                "sample_rate_hz": sample_rate,
                "buffer_frames": buffer_frames,
                "output_buffer_ms": round(buffer_ms, 6),
                "median_load_ms": round(median_load_ms, 6),
                "estimated_startup_ms": round(buffer_ms + median_load_ms, 6),
            }
        )
    return {
        "method": "median validated file load + one output callback buffer",
        "device_io_measured": False,
        "estimates": estimates,
    }


def _peak_rss_bytes() -> int:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Linux reports KiB and macOS reports bytes.
    return int(peak if sys.platform == "darwin" else peak * 1024)


def _benchmark_memory(audio_path: Path, samples: list[float]) -> dict[str, Any]:
    tracemalloc.start()
    try:
        audio = load_wav(audio_path)
        spectrum = _fft(samples)
        current_bytes, peak_bytes = tracemalloc.get_traced_memory()
        # Keep workload objects live until after the measurement.
        retained_bytes = len(audio.payload) + len(spectrum) * 16
    finally:
        tracemalloc.stop()
    return {
        "workload": "load largest fixture and compute one FFT",
        "python_current_bytes": current_bytes,
        "python_peak_bytes": peak_bytes,
        "estimated_payload_and_spectrum_bytes": retained_bytes,
        "process_peak_rss_bytes": _peak_rss_bytes(),
    }


def run_benchmark(
    fixtures_dir: Path,
    load_repetitions: int,
    fft_size: int,
    fft_iterations: int,
    buffer_frames: int,
) -> dict[str, Any]:
    """Run all benchmarks and return a JSON-serializable report."""
    if load_repetitions <= 0 or fft_iterations <= 0 or buffer_frames <= 0:
        raise ValueError("repetitions, iterations, and buffer frames must be positive")
    if fft_size == 0 or fft_size & (fft_size - 1):
        raise ValueError("fft_size must be a non-zero power of two")

    fixture_paths = sorted(fixtures_dir.glob("*.wav"))
    if not fixture_paths:
        raise FileNotFoundError(
            f"no WAV fixtures in {fixtures_dir}; run tools/generate_fixtures.py"
        )

    loading_report, audio_files = _benchmark_loading(
        fixture_paths, load_repetitions
    )
    fft_source = max(audio_files, key=lambda audio: audio.frame_count)
    fft_report, samples = _benchmark_fft(
        fft_source, fft_size=fft_size, iterations=fft_iterations
    )
    largest = max(fixture_paths, key=lambda path: path.stat().st_size)

    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor() or "unknown",
        },
        "configuration": {
            "fixtures_dir": fixtures_dir.as_posix(),
            "load_repetitions": load_repetitions,
            "fft_size": fft_size,
            "fft_iterations": fft_iterations,
            "buffer_frames": buffer_frames,
        },
        "file_loading": loading_report,
        "fft": fft_report,
        "playback_latency_estimate": _estimate_playback_latency(
            audio_files, loading_report, buffer_frames
        ),
        "memory": _benchmark_memory(largest, samples),
    }


def _parse_args() -> argparse.Namespace:
    repository_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        default=repository_root / "tests" / "fixtures",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repository_root
        / ".agent_workspace"
        / "round1"
        / "benchmark-baseline.json",
    )
    parser.add_argument("--load-repetitions", type=int, default=7)
    parser.add_argument("--fft-size", type=int, default=2_048)
    parser.add_argument("--fft-iterations", type=int, default=40)
    parser.add_argument("--buffer-frames", type=int, default=512)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report = run_benchmark(
        fixtures_dir=args.fixtures_dir.resolve(),
        load_repetitions=args.load_repetitions,
        fft_size=args.fft_size,
        fft_iterations=args.fft_iterations,
        buffer_frames=args.buffer_frames,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(args.output)
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"Wrote benchmark report to {args.output.resolve()}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
