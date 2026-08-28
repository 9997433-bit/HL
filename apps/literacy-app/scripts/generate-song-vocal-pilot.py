#!/usr/bin/env python3
"""Render an offline vowel vocal guide from a pinned voice source.

The legacy mode uses the pinned Piper voice from Round 12/13. Round 14 can
instead use a hash-pinned VocalSet recording made by a professional human
singer. Generation dependencies and source WAVs do not ship in the
application; the checked-in Ogg is the complete runtime asset.
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
VOCALSET_VERSION = "1.2"
VOCALSET_DOI = "10.5281/zenodo.1442513"
VOCALSET_MIRROR = "Bill13579/vocalset-mirror default/train row 55"
VOCALSET_SOURCE_SHA256 = (
    "451381cd80d9006251a3af694251abb9c756bafa5051130635142abbc210f3de"
)
VOCALSET_SOURCE_SAMPLE_RATE = 44_100
NOTE_HZ = {
    "C4": 261.63,
    "D4": 293.66,
    "E4": 329.63,
    "G4": 392.00,
    "A4": 440.00,
    "C5": 523.25,
}
VOCALSET_SEGMENTS = {
    # The source is a straight-vowel C-major arpeggio. Keep the central,
    # steady part of each ascending note and use the nearest sample for D/A.
    "C4": (0.55, 0.55),
    "E4": (1.50, 0.55),
    "G4": (2.10, 0.55),
    "C5": (3.10, 0.55),
}
VOCALSET_NOTE_SOURCE = {
    "C4": "C4",
    "D4": "C4",
    "E4": "E4",
    "G4": "G4",
    "A4": "G4",
    "C5": "C5",
}
GUIDES = {
    "sg1": {
        "asset": "sg1-climb-vocal-guide.ogg",
        "bpm": 96,
        "lines": [
            ["C4", "D4", "E4", "G4", "G4", "E4"],
            ["D4", "E4", "G4", "E4", "D4", "C4"],
            ["E4", "G4", "A4", "C5", "C5", "A4"],
            ["G4", "E4", "D4", "E4", "D4", "C4"],
        ],
    },
    "sg3": {
        "asset": "sg3-wash-hands-vocal-guide.ogg",
        "bpm": 92,
        "lines": [
            ["E4", "E4", "G4", "G4", "A4", "G4", "E4"],
            ["D4", "D4", "E4", "E4", "G4", "E4", "D4"],
            ["C5", "A4", "G4", "A4", "G4", "E4"],
            ["G4", "E4", "D4", "C4", "E4", "D4", "C4"],
        ],
    },
    "sg4": {
        "asset": "sg4-tree-bird-vocal-human.ogg",
        "bpm": 104,
        "lines": [
            ["C4", "E4", "G4", "E4", "D4", "C4"],
            ["E4", "G4", "A4", "G4", "E4", "D4", "C4"],
            ["G4", "A4", "C5", "A4", "G4", "E4"],
            ["E4", "G4", "E4", "D4", "E4", "D4", "C4"],
        ],
    },
    "sg5": {
        "asset": "sg5-literacy-vocal-pilot.ogg",
        "bpm": 88,
        "lines": [
            ["C4", "D4", "E4", "G4", "A4"],
            ["A4", "G4", "E4", "D4", "C4"],
            ["E4", "E4", "G4", "G4", "A4"],
            ["G4", "E4", "D4", "E4", "C4"],
        ],
    },
    "sg6": {
        "asset": "sg6-hello-thanks-vocal-human.ogg",
        "bpm": 90,
        "lines": [
            ["G4", "E4", "G4", "A4", "C5"],
            ["A4", "G4", "E4", "D4", "C4"],
            ["E4", "G4", "A4", "G4", "E4"],
            ["D4", "E4", "D4", "C4", "C4"],
        ],
    },
    "sg7": {
        "asset": "sg7-four-seasons-vocal-human.ogg",
        "bpm": 84,
        "lines": [
            ["C4", "E4", "G4", "A4", "G4"],
            ["E4", "G4", "C5", "A4", "G4"],
            ["A4", "G4", "E4", "D4", "E4"],
            ["G4", "E4", "D4", "C4", "C4"],
        ],
    },
    "sg8": {
        "asset": "sg8-family-vocal-human.ogg",
        "bpm": 94,
        "lines": [
            ["C4", "C4", "D4", "D4", "E4", "G4"],
            ["E4", "E4", "G4", "G4", "A4", "G4", "E4"],
            ["G4", "A4", "C5", "A4", "G4", "E4", "D4"],
            ["E4", "G4", "E4", "D4", "D4", "C4"],
        ],
    },
    "sg9": {
        "asset": "sg9-mothers-hands-vocal-human.ogg",
        "bpm": 82,
        "lines": [
            ["C4", "D4", "E4", "G4", "A4", "G4", "E4"],
            ["D4", "E4", "D4", "C4", "C4"],
            ["E4", "G4", "A4", "C5", "A4", "G4", "E4"],
            ["G4", "E4", "D4", "E4", "D4", "C4", "C4"],
        ],
    },
    "sg10": {
        "asset": "sg10-hands-feet-vocal-human.ogg",
        "bpm": 98,
        "lines": [
            ["C4", "D4", "E4", "G4", "A4"],
            ["A4", "G4", "E4", "D4", "C4"],
            ["E4", "G4", "A4", "C5", "C5"],
            ["A4", "G4", "E4", "D4", "C4"],
        ],
    },
    "sg11": {
        "asset": "sg11-countdown-vocal-human.ogg",
        "bpm": 86,
        "lines": [
            ["C5", "A4", "G4", "E4", "D4"],
            ["A4", "G4", "E4", "D4", "C4"],
            ["C4", "D4", "E4", "G4", "A4"],
            ["G4", "E4", "D4", "E4", "C4"],
        ],
    },
    "sg12": {
        "asset": "sg12-wood-character-vocal-human.ogg",
        "bpm": 90,
        "lines": [
            ["C4", "D4", "E4", "G4", "A4", "G4"],
            ["E4", "G4", "A4", "C5", "A4", "G4"],
            ["G4", "A4", "C5", "A4", "G4", "E4"],
            ["E4", "G4", "E4", "D4", "E4", "D4", "C4"],
        ],
    },
    "sg13": {
        "asset": "sg13-sorry-vocal-human.ogg",
        "bpm": 88,
        "lines": [
            ["G4", "A4", "G4", "E4", "D4", "C4"],
            ["C4", "D4", "E4", "G4", "A4", "G4", "E4"],
            ["E4", "G4", "A4", "C5", "A4", "G4", "E4"],
            ["G4", "E4", "D4", "C4", "C4"],
        ],
    },
}


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


def assert_human_source(source: Path) -> None:
    if not source.is_file():
        raise SystemExit(f"missing VocalSet source file: {source}")
    actual = sha256(source)
    if actual != VOCALSET_SOURCE_SHA256:
        raise SystemExit(
            f"unexpected hash for {source.name}: {actual}; "
            f"expected {VOCALSET_SOURCE_SHA256}"
        )
    with wave.open(str(source), "rb") as audio:
        if (
            audio.getnchannels() != 1
            or audio.getsampwidth() != 2
            or audio.getframerate() != VOCALSET_SOURCE_SAMPLE_RATE
        ):
            raise SystemExit("VocalSet source must be the pinned 44.1kHz 16-bit mono WAV")


def wave_duration(source: Path) -> float:
    with wave.open(str(source), "rb") as audio:
        return audio.getnframes() / audio.getframerate()


def extract_wave_segment(source: Path, output: Path, start: float, duration: float) -> None:
    with wave.open(str(source), "rb") as audio:
        rate = audio.getframerate()
        audio.setpos(round(start * rate))
        frames = audio.readframes(round(duration * rate))
        channels = audio.getnchannels()
        width = audio.getsampwidth()

    with wave.open(str(output), "wb") as target:
        target.setnchannels(channels)
        target.setsampwidth(width)
        target.setframerate(rate)
        target.writeframes(frames)


def estimate_pitch(seed: Path, expected_hz: float | None = None) -> float:
    """Estimate the seed's fundamental with normalized autocorrelation."""

    with wave.open(str(seed), "rb") as audio:
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2:
            raise SystemExit("vocal seed must be 16-bit mono PCM")
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
    if expected_hz:
        first_lag = round(sample_rate / (expected_hz * 1.08))
        last_lag = round(sample_rate / (expected_hz * 0.92))
    else:
        first_lag = round(sample_rate / 350)
        last_lag = round(sample_rate / 70)
    for lag in range(first_lag, last_lag + 1):
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
        raise SystemExit(f"could not estimate a stable vocal seed pitch ({best_score:.3f})")
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


def prepare_human_sources(source: Path, directory: Path) -> dict[str, tuple[Path, float, float]]:
    sources = {}
    for note, (start, duration) in VOCALSET_SEGMENTS.items():
        seed = directory / f"vocalset-{note.lower()}.wav"
        extract_wave_segment(source, seed, start, duration)
        sources[note] = (seed, estimate_pitch(seed, NOTE_HZ[note]), wave_duration(seed))
    return sources


def render_guide(
    sources: dict[str, tuple[Path, float, float]],
    note_sources: dict[str, str],
    output: Path,
    guide: dict[str, object],
    pitch_divisor: float,
    source_comment: str,
) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg with the rubberband filter is required")

    lines = guide["lines"]
    bpm = guide["bpm"]
    filters: list[str] = []
    labels: list[str] = []
    flat_notes = [note for line in lines for note in line]
    source_keys = [note_sources[note] for note in flat_notes]
    for input_index, key in enumerate(sources):
        indexes = [i for i, source_key in enumerate(source_keys) if source_key == key]
        split = (
            f",asplit={len(indexes)}" if len(indexes) > 1 else ""
        ) + "".join(f"[seed{i}]" for i in indexes)
        filters.append(
            f"[{input_index}:a]aformat=sample_fmts=fltp:sample_rates={SAMPLE_RATE}"
            f"{split}"
        )

    beat = 60 / bpm
    segment_index = 0
    for line_index, line in enumerate(lines):
        for note_index, note in enumerate(line):
            duration = beat * (2 if note_index == len(line) - 1 else 1)
            source_key = note_sources[note]
            _, source_hz, source_duration = sources[source_key]
            pitch = (NOTE_HZ[note] / pitch_divisor) / source_hz
            fade_out = max(0.02, duration - 0.08)
            filters.append(
                f"[seed{segment_index}]"
                f"rubberband=tempo={source_duration / duration:.8f}:pitch={pitch:.8f},"
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
            *[
                item
                for source, _, _ in sources.values()
                for item in ("-i", str(source))
            ],
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
            f"comment={source_comment}",
            str(output),
        ],
        check=True,
    )

    data = output.read_bytes()
    if len(data) < 10_240 or not data.startswith(b"OggS"):
        raise SystemExit(f"invalid vocal guide output: {len(data)} bytes")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument(
        "--human-source",
        type=Path,
        help=f"pinned VocalSet {VOCALSET_VERSION} WAV ({VOCALSET_MIRROR})",
    )
    parser.add_argument("--song", choices=sorted(GUIDES), default="sg5")
    parser.add_argument(
        "--output",
        type=Path,
    )
    args = parser.parse_args()

    guide = GUIDES[args.song]
    if args.human_source and (args.model or args.config):
        parser.error("--human-source cannot be combined with --model/--config")
    if args.human_source and "human" not in str(guide["asset"]):
        parser.error(f"{args.song} does not declare a Round 14 human-vocal asset")
    if not args.human_source and not (args.model and args.config):
        parser.error("provide --human-source or both --model and --config")

    output = args.output or (
        Path(__file__).resolve().parents[1]
        / "public"
        / "audio"
        / "songs"
        / guide["asset"]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        temp_dir = Path(temp)
        if args.human_source:
            assert_human_source(args.human_source)
            sources = prepare_human_sources(args.human_source, temp_dir)
            render_guide(
                sources,
                VOCALSET_NOTE_SOURCE,
                output,
                guide,
                pitch_divisor=1,
                source_comment=(
                    f"Human vowel guide; VocalSet {VOCALSET_VERSION}; "
                    f"doi:{VOCALSET_DOI}; CC BY 4.0; adapted"
                ),
            )
            source_summary = "VocalSet pitches " + ", ".join(
                f"{note}={source_hz:.1f}Hz"
                for note, (_, source_hz, _) in sources.items()
            )
        else:
            assert_voice_files(args.model, args.config)
            seed = temp_dir / "piper-la.wav"
            render_seed(args.model, args.config, seed)
            seed_hz = estimate_pitch(seed)
            sources = {"piper": (seed, seed_hz, wave_duration(seed))}
            render_guide(
                sources,
                {note: "piper" for note in NOTE_HZ},
                output,
                guide,
                pitch_divisor=2,
                source_comment=(
                    f"Offline la vocal guide; Piper {PIPER_VERSION}; {VOICE_ID}"
                ),
            )
            source_summary = (
                f"seed {seed_hz:.1f}Hz; model {MODEL_REVISION[:8]}; "
                f"config {CONFIG_REVISION[:8]}"
            )
    print(
        f"rendered {args.song} to {output} ({output.stat().st_size} bytes, "
        f"{source_summary})"
    )


if __name__ == "__main__":
    main()
