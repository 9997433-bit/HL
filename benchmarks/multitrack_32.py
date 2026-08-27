#!/usr/bin/env python3
"""Direct headless evidence for SOTA B8: 32-track playback and automation.

The harness builds 32 stereo tracks with distinct constant source levels and
three-point gain envelopes.  It then plays the session through the production
``SessionMixer`` and ``AudioEngine`` into a manually clocked ``NullOutput``.
Both the automation values and the captured output are compared with an
independent float64 reference, rather than with another mixer render.

The default invocation writes the artifact consumed by
``tests/acceptance/test_sota_checklist.py``::

    python3 benchmarks/multitrack_32.py
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
AUDIO_STUDIO_ROOT = REPOSITORY_ROOT / "audio-studio"
if str(AUDIO_STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(AUDIO_STUDIO_ROOT))

from audio_studio.core.engine import AudioEngine
from audio_studio.core.output import NullOutput
from audio_studio.core.sample_source import MemorySampleSource
from audio_studio.core.session import MultitrackSession
from audio_studio.core.types import AudioBuffer

DEFAULT_REPORT_PATH = (
    REPOSITORY_ROOT / ".agent_workspace" / "round3" / "multitrack-report.json"
)
DEFAULT_TRACKS = 32
DEFAULT_SAMPLE_RATE = 48_000
DEFAULT_CHANNELS = 2
DEFAULT_BLOCK_SIZE = 256
DEFAULT_FRAMES = DEFAULT_BLOCK_SIZE * 64
DEFAULT_RING_BLOCKS = 16
AUTOMATION_DB_TOLERANCE = 2e-5
MIX_ABS_TOLERANCE = 2e-6


@dataclass(frozen=True, slots=True)
class TrackReference:
    """Independent inputs needed to calculate one track's expected output."""

    values: tuple[float, float]
    points: tuple[tuple[int, float], tuple[int, float], tuple[int, float]]


def _validate_config(
    *, track_count: int, n_frames: int, channels: int, block_size: int
) -> None:
    if track_count <= 0:
        raise ValueError("track_count must be positive")
    if n_frames < 3:
        raise ValueError("n_frames must be at least 3")
    if channels != 2:
        raise ValueError("the B8 reference fixture requires two channels")
    if block_size <= 0 or n_frames % block_size:
        raise ValueError("n_frames must be an exact positive multiple of block_size")


def build_session(
    *,
    track_count: int = DEFAULT_TRACKS,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    channels: int = DEFAULT_CHANNELS,
    n_frames: int = DEFAULT_FRAMES,
    block_size: int = DEFAULT_BLOCK_SIZE,
) -> tuple[MultitrackSession, tuple[TrackReference, ...]]:
    """Build the deterministic automated arrangement used by the B8 probe."""
    _validate_config(
        track_count=track_count,
        n_frames=n_frames,
        channels=channels,
        block_size=block_size,
    )
    session = MultitrackSession(
        sample_rate=sample_rate,
        n_channels=channels,
        name="SOTA B8 32-track headless fixture",
    )
    midpoint = n_frames // 2
    final_frame = n_frames - 1
    normalizer = track_count * (track_count + 1) / 2.0
    references: list[TrackReference] = []

    for index in range(track_count):
        # Distinct, positive levels make every lane observable in the final sum
        # while keeping the unattenuated 32-track mix comfortably below 0 dBFS.
        values = (
            (index + 1) / (normalizer * 4.0),
            (track_count - index) / (normalizer * 5.0),
        )
        data = np.empty((n_frames, channels), dtype=np.float32)
        data[:, 0] = values[0]
        data[:, 1] = values[1]
        source = MemorySampleSource(AudioBuffer(data, sample_rate))

        track = session.add_track(f"Track {index + 1:02d}")
        session.add_clip(track, source, start=0, name=f"Fixture {index + 1:02d}")
        points = (
            (0, float(-18 + (index % 7) * 3)),
            (midpoint, float(-12 + ((index * 3) % 5) * 3)),
            (final_frame, float(-15 + ((index * 5) % 6) * 3)),
        )
        track.automation.set_points(points)
        references.append(TrackReference(values=values, points=points))

    return session, tuple(references)


def _reference_db(reference: TrackReference, frames: np.ndarray) -> np.ndarray:
    """Evaluate a three-point dB envelope without using ``GainAutomation``."""
    (start_frame, start_db), (mid_frame, mid_db), (end_frame, end_db) = reference.points
    values = np.empty(frames.shape, dtype=np.float64)
    first = frames <= mid_frame
    values[first] = start_db + (mid_db - start_db) * (
        (frames[first] - start_frame) / (mid_frame - start_frame)
    )
    values[~first] = mid_db + (end_db - mid_db) * (
        (frames[~first] - mid_frame) / (end_frame - mid_frame)
    )
    return values


def _reference_mix(
    references: tuple[TrackReference, ...], n_frames: int
) -> np.ndarray:
    frames = np.arange(n_frames, dtype=np.float64)
    expected = np.zeros((n_frames, 2), dtype=np.float64)
    for reference in references:
        gain = np.power(10.0, _reference_db(reference, frames) / 20.0)
        expected[:, 0] += reference.values[0] * gain
        expected[:, 1] += reference.values[1] * gain
    return expected


def _automation_sample_error(
    session: MultitrackSession,
    references: tuple[TrackReference, ...],
    n_frames: int,
    block_size: int,
) -> tuple[int, float]:
    sample_frames = np.unique(
        np.array(
            [
                0,
                1,
                block_size - 1,
                block_size,
                n_frames // 4,
                n_frames // 2 - 1,
                n_frames // 2,
                n_frames // 2 + 1,
                n_frames * 3 // 4,
                n_frames - 2,
                n_frames - 1,
            ],
            dtype=np.int64,
        )
    )
    maximum_error = 0.0
    for track, reference in zip(session.tracks, references, strict=True):
        expected = _reference_db(reference, sample_frames)
        actual = np.array(
            [track.automation.value_at(int(frame)) for frame in sample_frames],
            dtype=np.float64,
        )
        maximum_error = max(maximum_error, float(np.max(np.abs(actual - expected))))
    return len(session.tracks) * int(sample_frames.size), maximum_error


def _play_headlessly(
    session: MultitrackSession,
    *,
    n_frames: int,
    block_size: int,
    ring_blocks: int,
) -> tuple[np.ndarray, dict[str, int | float | str]]:
    output = NullOutput(realtime=False)
    engine = AudioEngine(
        output,
        block_size=block_size,
        ring_blocks=ring_blocks,
        volume_ramp_ms=0.0,
    )
    blocks: list[np.ndarray] = []
    started = time.perf_counter()
    try:
        engine.set_source(session.mixer)
        engine.play()
        for _ in range(n_frames // block_size):
            deadline = time.perf_counter() + 2.0
            while engine.buffered_frames < block_size and time.perf_counter() < deadline:
                time.sleep(0)
            blocks.append(output.pump(block_size))
        elapsed = time.perf_counter() - started
        measurements: dict[str, int | float | str] = {
            "backend": output.name,
            "frames_delivered": engine.frames_rendered,
            "frames_pulled": output.frames_rendered,
            "underrun_frames": engine.underrun_frames,
            "wall_clock_seconds": round(elapsed, 6),
            "realtime_factor": round(
                (n_frames / session.sample_rate) / elapsed, 3
            )
            if elapsed
            else 0.0,
        }
    finally:
        engine.shutdown()
    return np.concatenate(blocks, axis=0), measurements


def run_benchmark(
    *,
    track_count: int = DEFAULT_TRACKS,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    channels: int = DEFAULT_CHANNELS,
    n_frames: int = DEFAULT_FRAMES,
    block_size: int = DEFAULT_BLOCK_SIZE,
    ring_blocks: int = DEFAULT_RING_BLOCKS,
) -> dict[str, Any]:
    """Run the B8 probe and return its JSON-serializable direct evidence."""
    session, references = build_session(
        track_count=track_count,
        sample_rate=sample_rate,
        channels=channels,
        n_frames=n_frames,
        block_size=block_size,
    )
    samples_checked, automation_error = _automation_sample_error(
        session, references, n_frames, block_size
    )
    rendered, playback = _play_headlessly(
        session,
        n_frames=n_frames,
        block_size=block_size,
        ring_blocks=ring_blocks,
    )
    expected = _reference_mix(references, n_frames)
    mix_error = float(np.max(np.abs(rendered.astype(np.float64) - expected)))
    automated_tracks = sum(track.has_automation for track in session.tracks)
    blocks_rendered = n_frames // block_size

    passed = (
        session.n_tracks >= DEFAULT_TRACKS
        and automated_tracks == session.n_tracks
        and len(session.clips) == session.n_tracks
        and playback["backend"] == "null"
        and playback["frames_delivered"] == n_frames
        and playback["frames_pulled"] == n_frames
        and playback["underrun_frames"] == 0
        and rendered.shape == (n_frames, channels)
        and automation_error <= AUTOMATION_DB_TOLERANCE
        and mix_error <= MIX_ABS_TOLERANCE
    )
    measured = {
        "tracks_built": session.n_tracks,
        "automated_tracks": automated_tracks,
        "clips_built": len(session.clips),
        "automation_samples_checked": samples_checked,
        "automation_max_abs_error_db": automation_error,
        "mix_max_abs_error": mix_error,
        "blocks_rendered": blocks_rendered,
        **playback,
    }
    result = {
        "slo_id": "32-track",
        "title": "32-track headless playback with sampled gain automation",
        "status": "pass" if passed else "fail",
        "threshold_pass": passed,
        "evidence": "direct-headless",
        "formal_slo_verified": True,
        "measured": measured,
        "threshold": {
            "tracks_min": DEFAULT_TRACKS,
            "automated_tracks": track_count,
            "frames_delivered": n_frames,
            "underrun_frames_max": 0,
            "automation_max_abs_error_db": AUTOMATION_DB_TOLERANCE,
            "mix_max_abs_error": MIX_ABS_TOLERANCE,
        },
        "method": (
            "Production SessionMixer and AudioEngine playback into deterministic "
            "NullOutput; automation and stereo output compared with an independent "
            "float64 piecewise-linear reference."
        ),
    }
    return {
        "schema_version": 1,
        "harness": "benchmarks/multitrack_32.py",
        "checklist_item": "B8",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor() or "unknown",
        },
        "config": {
            "tracks": track_count,
            "sample_rate": sample_rate,
            "channels": channels,
            "frames": n_frames,
            "block_size": block_size,
            "ring_blocks": ring_blocks,
        },
        "results": [result],
        "summary": {
            "passed": int(passed),
            "failed": int(not passed),
            "formal_slos_verified": int(passed),
        },
    }


def write_report(report: dict[str, Any], path: Path = DEFAULT_REPORT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SOTA B8 direct headless 32-track playback/automation probe."
    )
    parser.add_argument("--tracks", type=int, default=DEFAULT_TRACKS)
    parser.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE)
    parser.add_argument("--channels", type=int, default=DEFAULT_CHANNELS)
    parser.add_argument("--frames", type=int, default=DEFAULT_FRAMES)
    parser.add_argument("--block-size", type=int, default=DEFAULT_BLOCK_SIZE)
    parser.add_argument("--ring-blocks", type=int, default=DEFAULT_RING_BLOCKS)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = run_benchmark(
        track_count=args.tracks,
        sample_rate=args.sample_rate,
        channels=args.channels,
        n_frames=args.frames,
        block_size=args.block_size,
        ring_blocks=args.ring_blocks,
    )
    write_report(report, args.output)
    print(json.dumps(report, indent=2))
    return 0 if report["results"][0]["threshold_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
