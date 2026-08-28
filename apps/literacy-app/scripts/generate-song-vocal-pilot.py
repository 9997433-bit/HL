#!/usr/bin/env python3
"""Render the sg5 offline “la” vocal guide from a pinned Piper voice.

This is a generation-only tool: neither Piper nor its voice model ships in the
application. The checked-in Ogg is the complete runtime asset.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
import tempfile
import wave
from array import array
from pathlib import Path


PIPER_VERSION = "1.7.0"
VOICE_ID = "sv_SE-nst-medium"
MODEL_REVISION = "2f8dbe0bb0dde986411632bf014a13cdbe6596e7"
CONFIG_REVISION = "9f800697ad9dfc9533f9e6191d04da0ecdd204f5"
MODEL_SHA256 = "df011f56825a59dd1efc080c38a65a1ef70407e60f63050e9246f43a3d7e471e"
CONFIG_SHA256 = "d45dd74cbb4eca58694bf04a97e243044092476f28a55ae26424f0653086980a"
SAMPLE_RATE = 22_050
BPM = 88
NOTE_HZ = {
    "C4": 261.63,
    "D4": 293.66,
    "E4": 329.63,
    "G4": 392.00,
    "A4": 440.00,
}
LINES = [
    ["C4", "D4", "E4", "G4", "A4"],
    ["A4", "G4", "E4", "D4", "C4"],
    ["E4", "E4", "G4", "G4", "A4"],
    ["G4", "E4", "D4", "E4", "C4"],
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_voice_files(model: Path, config: Path) -> None:
    expected = ((model, MODEL_SHA256), (config, CONFIG_SHA256))
    for path, expected_hash in expected:
        if not path.is_file():
            raise SystemExit(f"missing Piper voice file: {path}")
        actual = sha256(path)
        if actual != expected_hash:
            raise SystemExit(
                f"unexpected hash for {path.name}: {actual}; expected {expected_hash}"
            )

    metadata = json.loads(config.read_text(encoding="utf-8"))
    if metadata.get("audio", {}).get("sample_rate") != SAMPLE_RATE:
        raise SystemExit(f"{config.name} is not the pinned {VOICE_ID} configuration")


def estimate_pitch(seed: Path) -> float:
    """Estimate the seed's fundamental with normalized autocorrelation."""

    with wave.open(str(seed), "rb") as audio:
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2:
            raise SystemExit("Piper seed must be 16-bit mono PCM")
        sample_rate = audio.getframerate()
        samples = array("h", audio.readframes(audio.getnframes()))

    # The middle half avoids the /l/ attack and sentence-final release.
    start = len(samples) // 4
    stop = len(samples) * 3 // 4
    window = [float(value) for value in samples[start:stop]]
    mean = sum(window) / len(window)
    window = [value - mean for value in window]

    best_lag = 0
    best_score = -1.0
    for lag in range(round(sample_rate / 350), round(sample_rate / 70)):
        left = window[:-lag]
        right = window[lag:]
        dot = sum(a * b for a, b in zip(left, right))
        energy_left = sum(a * a for a in left)
        energy_right = sum(b * b for b in right)
        denominator = math.sqrt(energy_left * energy_right)
        score = dot / denominator if denominator else -1.0
        if score > best_score:
            best_lag, best_score = lag, score

    if not best_lag or best_score < 0.20:
        raise SystemExit(f"could not estimate a stable Piper seed pitch ({best_score:.3f})")
    return sample_rate / best_lag


def render_seed(model: Path, config: Path, output: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "piper",
            "--model",
            str(model),
            "--config",
            str(config),
            "--output-file",
            str(output),
            "--length-scale",
            "1.2",
            "--noise-scale",
            "0",
            "--noise-w-scale",
            "0",
            "--sentence-silence",
            "0",
        ],
        input="La.\n",
        text=True,
        check=True,
    )


def render_guide(seed: Path, seed_hz: float, output: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg with the rubberband filter is required")

    filters: list[str] = []
    labels: list[str] = []
    segments = sum(len(line) for line in LINES)
    filters.append(
        f"[0:a]aformat=sample_fmts=fltp:sample_rates={SAMPLE_RATE},"
        f"asplit={segments}" + "".join(f"[seed{i}]" for i in range(segments))
    )

    beat = 60 / BPM
    segment_index = 0
    for line_index, line in enumerate(LINES):
        for note_index, note in enumerate(line):
            duration = beat * (2 if note_index == len(line) - 1 else 1)
            # The source is a low male voice. An octave-down transposition keeps
            # the guide in a natural C3–C4 singing range while preserving melody.
            pitch = (NOTE_HZ[note] / 2) / seed_hz
            fade_out = max(0.02, duration - 0.08)
            filters.append(
                f"[seed{segment_index}]"
                f"rubberband=tempo={1 / duration:.8f}:pitch={pitch:.8f},"
                f"apad=pad_dur={duration:.8f},atrim=duration={duration:.8f},"
                f"afade=t=in:d=0.02,afade=t=out:st={fade_out:.8f}:d=0.08"
                f"[note{segment_index}]"
            )
            labels.append(f"[note{segment_index}]")
            segment_index += 1

        gap = beat * 0.5
        filters.append(f"aevalsrc=0:d={gap:.8f}:s={SAMPLE_RATE}[gap{line_index}]")
        labels.append(f"[gap{line_index}]")

    filters.append(
        "".join(labels)
        + f"concat=n={len(labels)}:v=0:a=1,"
        + f"loudnorm=I=-18:TP=-2:LRA=7,aresample={SAMPLE_RATE}[out]"
    )

    subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(seed),
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[out]",
            "-c:a",
            "libvorbis",
            "-q:a",
            "3",
            "-metadata",
            "artist=Happy Literacy project",
            "-metadata",
            f"comment=Offline la vocal guide; Piper {PIPER_VERSION}; {VOICE_ID}",
            str(output),
        ],
        check=True,
    )

    data = output.read_bytes()
    if len(data) < 10_240 or not data.startswith(b"OggS"):
        raise SystemExit(f"invalid vocal guide output: {len(data)} bytes")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "public"
        / "audio"
        / "songs"
        / "sg5-literacy-vocal-pilot.ogg",
    )
    args = parser.parse_args()

    assert_voice_files(args.model, args.config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        seed = Path(temp) / "piper-la.wav"
        render_seed(args.model, args.config, seed)
        seed_hz = estimate_pitch(seed)
        render_guide(seed, seed_hz, args.output)
    print(
        f"rendered {args.output} ({args.output.stat().st_size} bytes, "
        f"seed {seed_hz:.1f} Hz, model revision {MODEL_REVISION[:8]}, "
        f"config revision {CONFIG_REVISION[:8]})"
    )


if __name__ == "__main__":
    main()
