#!/usr/bin/env python3
"""Render all thirteen original song melodies as compact Ogg assets."""

from __future__ import annotations

import argparse
import math
import shutil
import struct
import subprocess
import tempfile
import wave
from pathlib import Path


SAMPLE_RATE = 22_050
NOTE_HZ = {
    "C4": 261.63,
    "D4": 293.66,
    "E4": 329.63,
    "G4": 392.00,
    "A4": 440.00,
    "C5": 523.25,
}
SONGS = {
    "sg1-climb-melody": (
        96,
        [
            ["C4", "D4", "E4", "G4", "G4", "E4"],
            ["D4", "E4", "G4", "E4", "D4", "C4"],
            ["E4", "G4", "A4", "C5", "C5", "A4"],
            ["G4", "E4", "D4", "E4", "D4", "C4"],
        ],
    ),
    "sg2-raindrop-melody": (
        100,
        [
            ["G4", "A4", "G4", "E4", "E4", "D4"],
            ["C4", "D4", "E4", "G4", "A4", "G4", "E4"],
            ["E4", "G4", "A4", "C5", "A4", "G4", "E4"],
            ["G4", "E4", "D4", "C4", "D4", "E4", "C4"],
        ],
    ),
    "sg3-wash-hands-melody": (
        92,
        [
            ["E4", "E4", "G4", "G4", "A4", "G4", "E4"],
            ["D4", "D4", "E4", "E4", "G4", "E4", "D4"],
            ["C5", "A4", "G4", "A4", "G4", "E4"],
            ["G4", "E4", "D4", "C4", "E4", "D4", "C4"],
        ],
    ),
    "sg4-tree-bird-melody": (
        104,
        [
            ["C4", "E4", "G4", "E4", "D4", "C4"],
            ["E4", "G4", "A4", "G4", "E4", "D4", "C4"],
            ["G4", "A4", "C5", "A4", "G4", "E4"],
            ["E4", "G4", "E4", "D4", "E4", "D4", "C4"],
        ],
    ),
    "sg5-literacy-melody": (
        88,
        [
            ["C4", "D4", "E4", "G4", "A4"],
            ["A4", "G4", "E4", "D4", "C4"],
            ["E4", "E4", "G4", "G4", "A4"],
            ["G4", "E4", "D4", "E4", "C4"],
        ],
    ),
    "sg6-hello-thanks-melody": (
        90,
        [
            ["G4", "E4", "G4", "A4", "C5"],
            ["A4", "G4", "E4", "D4", "C4"],
            ["E4", "G4", "A4", "G4", "E4"],
            ["D4", "E4", "D4", "C4", "C4"],
        ],
    ),
    "sg7-four-seasons-melody": (
        84,
        [
            ["C4", "E4", "G4", "A4", "G4"],
            ["E4", "G4", "C5", "A4", "G4"],
            ["A4", "G4", "E4", "D4", "E4"],
            ["G4", "E4", "D4", "C4", "C4"],
        ],
    ),
    "sg8-family-melody": (
        94,
        [
            ["C4", "C4", "D4", "D4", "E4", "G4"],
            ["E4", "E4", "G4", "G4", "A4", "G4", "E4"],
            ["G4", "A4", "C5", "A4", "G4", "E4", "D4"],
            ["E4", "G4", "E4", "D4", "D4", "C4"],
        ],
    ),
    "sg9-mothers-hands-melody": (
        82,
        [
            ["C4", "D4", "E4", "G4", "A4", "G4", "E4"],
            ["D4", "E4", "D4", "C4", "C4"],
            ["E4", "G4", "A4", "C5", "A4", "G4", "E4"],
            ["G4", "E4", "D4", "E4", "D4", "C4", "C4"],
        ],
    ),
    "sg10-hands-feet-melody": (
        98,
        [
            ["C4", "D4", "E4", "G4", "A4"],
            ["A4", "G4", "E4", "D4", "C4"],
            ["E4", "G4", "A4", "C5", "C5"],
            ["A4", "G4", "E4", "D4", "C4"],
        ],
    ),
    "sg11-countdown-melody": (
        86,
        [
            ["C5", "A4", "G4", "E4", "D4"],
            ["A4", "G4", "E4", "D4", "C4"],
            ["C4", "D4", "E4", "G4", "A4"],
            ["G4", "E4", "D4", "E4", "C4"],
        ],
    ),
    "sg12-wood-character-melody": (
        90,
        [
            ["C4", "D4", "E4", "G4", "A4", "G4"],
            ["E4", "G4", "A4", "C5", "A4", "G4"],
            ["G4", "A4", "C5", "A4", "G4", "E4"],
            ["E4", "G4", "E4", "D4", "E4", "D4", "C4"],
        ],
    ),
    "sg13-sorry-melody": (
        88,
        [
            ["G4", "A4", "G4", "E4", "D4", "C4"],
            ["C4", "D4", "E4", "G4", "A4", "G4", "E4"],
            ["E4", "G4", "A4", "C5", "A4", "G4", "E4"],
            ["G4", "E4", "D4", "C4", "C4"],
        ],
    ),
}


def envelope(position: float, duration: float) -> float:
    attack = min(1.0, position / 0.025)
    release = min(1.0, max(0.0, duration - position) / 0.10)
    return attack * release


def render_note(samples: list[float], frequency: float, duration: float) -> None:
    count = round(duration * SAMPLE_RATE)
    for index in range(count):
        at = index / SAMPLE_RATE
        # A warm, bell-like additive voice; all frequencies and score are project-original.
        voice = (
            math.sin(2 * math.pi * frequency * at)
            + 0.24 * math.sin(2 * math.pi * frequency * 2 * at)
            + 0.09 * math.sin(2 * math.pi * frequency * 3 * at)
        )
        samples.append(0.24 * envelope(at, duration) * voice)


def render_song(bpm: int, lines: list[list[str]]) -> bytes:
    beat = 60 / bpm
    samples: list[float] = []
    for line in lines:
        for index, note in enumerate(line):
            duration = beat * (2 if index == len(line) - 1 else 1)
            render_note(samples, NOTE_HZ[note], duration)
        samples.extend([0.0] * round(beat * 0.5 * SAMPLE_RATE))
    return b"".join(
        struct.pack("<h", max(-32_767, min(32_767, round(sample * 32_767))))
        for sample in samples
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--song",
        action="append",
        choices=sorted(SONGS),
        help="render only this asset name (repeatable); default: render all",
    )
    args = parser.parse_args()

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg is required to encode the Ogg assets")

    output_dir = Path(__file__).resolve().parents[1] / "public" / "audio" / "songs"
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp:
        names = args.song or SONGS
        for name in names:
            bpm, lines = SONGS[name]
            wav_path = Path(temp) / f"{name}.wav"
            with wave.open(str(wav_path), "wb") as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(SAMPLE_RATE)
                audio.writeframes(render_song(bpm, lines))

            subprocess.run(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(wav_path),
                    "-c:a",
                    "libvorbis",
                    "-q:a",
                    "1",
                    "-metadata",
                    "artist=Happy Literacy project",
                    "-metadata",
                    "comment=Original project melody; generated from src/data/songs.js",
                    str(output_dir / f"{name}.ogg"),
                ],
                check=True,
            )


if __name__ == "__main__":
    main()
