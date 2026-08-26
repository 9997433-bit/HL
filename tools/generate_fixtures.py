#!/usr/bin/env python3
"""Generate deterministic PCM WAV fixtures for audio tests."""

from __future__ import annotations

import argparse
import math
import random
import struct
import wave
from collections.abc import Callable
from pathlib import Path

DEFAULT_SAMPLE_RATES = (44_100, 48_000)
DEFAULT_DURATION_SECONDS = 1.0
PCM_WIDTH_BYTES = 2

MonoSignal = Callable[[float, random.Random], float]


def _sine_sweep(duration: float) -> MonoSignal:
    start_hz = 20.0
    end_hz = 20_000.0
    slope = (end_hz - start_hz) / duration

    def sample(t: float, _rng: random.Random) -> float:
        phase = 2.0 * math.pi * (start_hz * t + 0.5 * slope * t * t)
        return 0.8 * math.sin(phase)

    return sample


def _white_noise(_t: float, rng: random.Random) -> float:
    return 0.5 * rng.uniform(-1.0, 1.0)


def _silence(_t: float, _rng: random.Random) -> float:
    return 0.0


def _clipping(t: float, _rng: random.Random) -> float:
    # Deliberately exceeds full scale; quantization creates flat clipped peaks.
    return 1.6 * math.sin(2.0 * math.pi * 997.0 * t)


def _multi_frequency(t: float, _rng: random.Random) -> float:
    frequencies = (110.0, 440.0, 1_000.0, 7_500.0, 15_000.0)
    return 0.18 * sum(math.sin(2.0 * math.pi * hz * t) for hz in frequencies)


def _pcm16(value: float) -> int:
    clipped = max(-1.0, min(1.0, value))
    if clipped <= -1.0:
        return -32_768
    return round(clipped * 32_767)


def _write_mono(
    path: Path,
    sample_rate: int,
    duration: float,
    signal: MonoSignal,
    seed: int,
) -> None:
    frame_count = round(sample_rate * duration)
    rng = random.Random(seed)
    payload = bytearray()
    for frame in range(frame_count):
        payload.extend(struct.pack("<h", _pcm16(signal(frame / sample_rate, rng))))
    _write_wav(path, sample_rate, channels=1, payload=payload)


def _write_stereo_phase(path: Path, sample_rate: int, duration: float) -> None:
    frame_count = round(sample_rate * duration)
    payload = bytearray()
    for frame in range(frame_count):
        t = frame / sample_rate
        left = 0.8 * math.sin(2.0 * math.pi * 1_000.0 * t)
        right = 0.8 * math.sin(2.0 * math.pi * 1_000.0 * t + math.pi / 2.0)
        payload.extend(struct.pack("<hh", _pcm16(left), _pcm16(right)))
    _write_wav(path, sample_rate, channels=2, payload=payload)


def _write_wav(
    path: Path, sample_rate: int, channels: int, payload: bytes | bytearray
) -> None:
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    with wave.open(str(temporary_path), "wb") as output:
        output.setnchannels(channels)
        output.setsampwidth(PCM_WIDTH_BYTES)
        output.setframerate(sample_rate)
        output.writeframes(payload)
    temporary_path.replace(path)


def generate_fixtures(
    output_dir: Path,
    sample_rates: tuple[int, ...] = DEFAULT_SAMPLE_RATES,
    duration: float = DEFAULT_DURATION_SECONDS,
) -> list[Path]:
    """Generate all fixture variants and return their paths."""
    if duration <= 0:
        raise ValueError("duration must be positive")
    if not sample_rates or any(rate <= 0 for rate in sample_rates):
        raise ValueError("sample rates must be positive")

    output_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []
    mono_signals: tuple[tuple[str, MonoSignal], ...] = (
        ("sine_sweep", _sine_sweep(duration)),
        ("white_noise", _white_noise),
        ("silence", _silence),
        ("clipping", _clipping),
        ("multi_frequency", _multi_frequency),
    )

    for sample_rate in sample_rates:
        for fixture_index, (name, signal) in enumerate(mono_signals):
            path = output_dir / f"{name}_{sample_rate}hz.wav"
            seed = sample_rate * 100 + fixture_index
            _write_mono(path, sample_rate, duration, signal, seed)
            generated.append(path)

        stereo_path = output_dir / f"stereo_phase_90deg_{sample_rate}hz.wav"
        _write_stereo_phase(stereo_path, sample_rate, duration)
        generated.append(stereo_path)

    return generated


def _parse_args() -> argparse.Namespace:
    repository_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=repository_root / "tests" / "fixtures",
        help="fixture destination (default: tests/fixtures)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=DEFAULT_DURATION_SECONDS,
        help="duration of each fixture in seconds",
    )
    parser.add_argument(
        "--sample-rates",
        type=int,
        nargs="+",
        default=list(DEFAULT_SAMPLE_RATES),
        help="sample rates to generate",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    generated = generate_fixtures(
        args.output_dir.resolve(),
        sample_rates=tuple(args.sample_rates),
        duration=args.duration,
    )
    for path in generated:
        print(path)
    print(f"Generated {len(generated)} deterministic WAV fixtures.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
