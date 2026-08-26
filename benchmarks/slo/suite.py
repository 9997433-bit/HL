"""Executable headless probes for the key fable §7 SLOs.

Hardware/device SLOs cannot be certified in a cloud VM.  Each result therefore
states whether it is a direct measurement or a headless proxy; proxy failures
are still useful escape-hatch signals, while proxy passes are not presented as
hardware certification.
"""

from __future__ import annotations

import platform
import statistics
import sys
import time
import wave
from pathlib import Path
from typing import Any, Callable

import numpy as np

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
AUDIO_STUDIO_ROOT = REPOSITORY_ROOT / "audio-studio"
if str(AUDIO_STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(AUDIO_STUDIO_ROOT))

from audio_studio.core.loader import load_audio  # noqa: E402
from audio_studio.core.ring_buffer import RingBuffer  # noqa: E402
from audio_studio.dsp.effects import EffectChain, GainEffect, ThreeBandEQ  # noqa: E402
from audio_studio.dsp.spectral import SpectralAnalyzer, SpectralConfig  # noqa: E402

SAMPLE_RATE = 48_000
BLOCK_FRAMES = 128
BLOCK_PERIOD_MS = BLOCK_FRAMES / SAMPLE_RATE * 1_000.0


def _measure(
    operation: Callable[[], object],
    repetitions: int,
    *,
    warmups: int = 1,
) -> list[float]:
    for _ in range(warmups):
        operation()
    elapsed_ms: list[float] = []
    for _ in range(repetitions):
        started = time.perf_counter_ns()
        operation()
        elapsed_ms.append((time.perf_counter_ns() - started) / 1_000_000.0)
    return elapsed_ms


def _distribution(elapsed_ms: list[float]) -> dict[str, float]:
    return {
        "minimum_ms": round(min(elapsed_ms), 6),
        "median_ms": round(statistics.median(elapsed_ms), 6),
        "p95_ms": round(float(np.percentile(elapsed_ms, 95)), 6),
        "p99_ms": round(float(np.percentile(elapsed_ms, 99)), 6),
        "maximum_ms": round(max(elapsed_ms), 6),
    }


def _result(
    slo_id: str,
    title: str,
    measured: dict[str, Any],
    threshold: dict[str, Any],
    passed: bool,
    *,
    evidence: str,
    limitation: str,
) -> dict[str, Any]:
    return {
        "slo_id": slo_id,
        "title": title,
        "status": "pass" if passed else "fail",
        "threshold_pass": bool(passed),
        "evidence": evidence,
        "formal_slo_verified": evidence == "direct",
        "measured": measured,
        "threshold": threshold,
        "limitation": limitation,
    }


def _benchmark_l1_ring(repetitions: int) -> dict[str, Any]:
    ring = RingBuffer(BLOCK_FRAMES * 4, channels=2)
    block = np.full((BLOCK_FRAMES, 2), 0.25, dtype=np.float32)
    underruns = 0
    elapsed_ms: list[float] = []
    for _ in range(repetitions):
        ring.write(block)
        available = ring.available_read
        started = time.perf_counter_ns()
        rendered = ring.read(BLOCK_FRAMES, pad=True)
        elapsed_ms.append((time.perf_counter_ns() - started) / 1_000_000.0)
        underruns += int(available < BLOCK_FRAMES or rendered.shape != block.shape)
    underrun_rate = underruns / repetitions
    measured = {
        "buffer_frames": BLOCK_FRAMES,
        "nominal_output_latency_ms": round(BLOCK_PERIOD_MS, 6),
        "simulated_callbacks": repetitions,
        "underruns": underruns,
        "underrun_rate_percent": round(underrun_rate * 100.0, 6),
        "callback_read_timing": _distribution(elapsed_ms),
    }
    return _result(
        "L1",
        "128-frame output and underrun rate",
        measured,
        {"buffer_frames_max": 128, "underrun_rate_percent_max": 0.1},
        BLOCK_FRAMES <= 128 and underrun_rate < 0.001,
        evidence="headless-proxy",
        limitation="In-memory SPSC queue; no audio device and shorter than the 10-minute SLO.",
    )


def _benchmark_t2_ring_callback(repetitions: int) -> dict[str, Any]:
    ring = RingBuffer(BLOCK_FRAMES * 4, channels=2)
    block = np.full((BLOCK_FRAMES, 2), 0.125, dtype=np.float32)

    def callback_path() -> np.ndarray:
        ring.write(block)
        return ring.read(BLOCK_FRAMES, pad=True)

    elapsed_ms = _measure(callback_path, repetitions, warmups=10)
    p99_ms = float(np.percentile(elapsed_ms, 99))
    ceiling_ms = BLOCK_PERIOD_MS * 0.5
    return _result(
        "T2",
        "Callback queue p99",
        {
            **_distribution(elapsed_ms),
            "block_period_ms": round(BLOCK_PERIOD_MS, 6),
            "p99_block_utilization_percent": round(p99_ms / BLOCK_PERIOD_MS * 100.0, 3),
        },
        {"p99_ms_max": round(ceiling_ms, 6), "block_utilization_percent_max": 50.0},
        p99_ms < ceiling_ms,
        evidence="headless-proxy",
        limitation="Measures the current ring-buffer path, not device wake-up jitter or a full graph.",
    )


def _make_effect_chain() -> EffectChain:
    return EffectChain(
        [
            ThreeBandEQ(low_gain_db=1.0, mid_gain_db=-1.0, high_gain_db=0.5),
            GainEffect(gain_db=-0.5, ramp_ms=0.0),
            GainEffect(gain_db=0.25, ramp_ms=0.0),
            GainEffect(gain_db=-0.25, ramp_ms=0.0),
        ]
    )


def _benchmark_t1_mix(repetitions: int) -> dict[str, Any]:
    rng = np.random.default_rng(7)
    tracks = rng.normal(0.0, 0.03, size=(32, BLOCK_FRAMES, 2)).astype(np.float32)
    chains = [_make_effect_chain() for _ in range(32)]
    checksum = 0.0

    def render_block() -> np.ndarray:
        nonlocal checksum
        mixed = np.zeros((BLOCK_FRAMES, 2), dtype=np.float32)
        for track, chain in zip(tracks, chains, strict=True):
            mixed += chain.process_block(track, SAMPLE_RATE, channels_last=True)
        checksum += float(mixed[0, 0])
        return mixed

    elapsed_ms = _measure(render_block, repetitions, warmups=2)
    p99_ms = float(np.percentile(elapsed_ms, 99))
    utilization = p99_ms / BLOCK_PERIOD_MS * 100.0
    return _result(
        "T1",
        "32 stereo tracks × 4 effects mix proxy",
        {
            **_distribution(elapsed_ms),
            "tracks": 32,
            "effects_per_track": 4,
            "block_frames": BLOCK_FRAMES,
            "single_core_block_utilization_percent": round(utilization, 3),
            "checksum": round(checksum, 8),
        },
        {"reference_cpu_percent_max": 60.0},
        utilization < 60.0,
        evidence="headless-proxy",
        limitation="Single Python worker proxy; fable T1 requires CPU telemetry on a 4-core host.",
    )


def _benchmark_t3_offline(repetitions: int) -> dict[str, Any]:
    seconds = 2.0
    rng = np.random.default_rng(8)
    audio = rng.normal(0.0, 0.03, size=(int(SAMPLE_RATE * seconds), 2)).astype(np.float32)

    def render() -> np.ndarray:
        return _make_effect_chain().process(audio, SAMPLE_RATE, channels_last=True)

    elapsed_ms = _measure(render, repetitions)
    median_seconds = statistics.median(elapsed_ms) / 1_000.0
    realtime_factor = seconds / median_seconds
    return _result(
        "T3",
        "Typical four-effect offline render",
        {
            **_distribution(elapsed_ms),
            "audio_seconds": seconds,
            "realtime_factor": round(realtime_factor, 3),
        },
        {"realtime_factor_min": 10.0},
        realtime_factor >= 10.0,
        evidence="headless-proxy",
        limitation="Two-second synthetic clip; formal SLO uses a representative 10-minute programme.",
    )


def _benchmark_stft(repetitions: int) -> dict[str, Any]:
    seconds = 10.0
    rng = np.random.default_rng(9)
    audio = rng.normal(0.0, 0.03, size=(int(SAMPLE_RATE * seconds), 2)).astype(np.float32)
    config = SpectralConfig(
        sample_rate=SAMPLE_RATE,
        fft_size=4096,
        hop_size=1024,
        center=False,
        fft_workers=1,
    )
    analyzer = SpectralAnalyzer(config)

    def transform() -> np.ndarray:
        return analyzer.stft(audio, channels_last=True)

    elapsed_ms = _measure(transform, repetitions)
    median_seconds = statistics.median(elapsed_ms) / 1_000.0
    frame_count = config.n_frames(audio.shape[0])
    frame_throughput = frame_count / median_seconds
    realtime_factor = seconds / median_seconds
    return _result(
        "U2/U3",
        "10-second STFT 4096 throughput",
        {
            **_distribution(elapsed_ms),
            "audio_seconds": seconds,
            "stft_frames": frame_count,
            "frames_per_wall_second": round(frame_throughput, 3),
            "audio_realtime_factor": round(realtime_factor, 3),
        },
        {"frames_per_wall_second_min": 30.0, "audio_realtime_factor_min": 10.0},
        frame_throughput >= 30.0 and realtime_factor >= 10.0,
        evidence="headless-proxy",
        limitation="Measures STFT computation, not Qt painting, scrolling, or display refresh cadence.",
    )


def _write_load_fixture(path: Path, seconds: int = 60) -> None:
    sample_numbers = np.arange(SAMPLE_RATE, dtype=np.float64)
    mono = 0.25 * np.sin(2.0 * np.pi * 997.0 * sample_numbers / SAMPLE_RATE)
    pcm = np.clip(np.rint(mono * 32767.0), -32768, 32767).astype("<i2")
    stereo_chunk = np.repeat(pcm[:, np.newaxis], 2, axis=1).tobytes()
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        for _ in range(seconds):
            output.writeframesraw(stereo_chunk)


def _benchmark_loading(work_dir: Path, repetitions: int) -> dict[str, Any]:
    fixture = work_dir / "load-60s-stereo-pcm16.wav"
    _write_load_fixture(fixture)

    def load() -> object:
        return load_audio(fixture)

    elapsed_ms = _measure(load, repetitions)
    median_ms = statistics.median(elapsed_ms)
    return _result(
        "U1",
        "WAV decode/load latency",
        {
            **_distribution(elapsed_ms),
            "fixture_duration_seconds": 60,
            "fixture_size_bytes": fixture.stat().st_size,
        },
        {"visible_latency_ms_max": 2_000.0},
        median_ms < 2_000.0,
        evidence="headless-proxy",
        limitation="One-minute decode only; the one-hour waveform-visible SLO remains unverified.",
    )


def run_slo_suite(work_dir: str | Path, *, quick: bool = False) -> dict[str, Any]:
    """Run all headless probes and return a JSON-serializable result."""
    target = Path(work_dir)
    target.mkdir(parents=True, exist_ok=True)
    repetitions = {
        "ring": 300 if quick else 2_000,
        "mix": 5 if quick else 20,
        "offline": 2 if quick else 5,
        "stft": 2 if quick else 5,
        "load": 2 if quick else 5,
    }
    results = [
        _benchmark_l1_ring(repetitions["ring"]),
        _benchmark_t2_ring_callback(repetitions["ring"]),
        _benchmark_t1_mix(repetitions["mix"]),
        _benchmark_t3_offline(repetitions["offline"]),
        _benchmark_stft(repetitions["stft"]),
        _benchmark_loading(target, repetitions["load"]),
    ]
    return {
        "schema_version": 1,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor() or "unknown",
        },
        "quick": quick,
        "results": results,
        "summary": {
            "proxy_passed": sum(item["threshold_pass"] for item in results),
            "proxy_failed": sum(not item["threshold_pass"] for item in results),
            "formal_slos_verified": sum(item["formal_slo_verified"] for item in results),
        },
    }
