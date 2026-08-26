#!/usr/bin/env python3
"""Throughput benchmark for the spectral analysis and effects layers.

The headline case is the one from the module spec: one minute of 48 kHz stereo
audio through a full STFT. Everything is reported as a *realtime factor* — how
many seconds of audio are processed per second of wall clock — because that is
the number that decides whether a feature can run live or has to be offline.

Usage::

    python benchmarks/bench_stft.py                 # default suite
    python benchmarks/bench_stft.py --duration 300  # 5 minutes of audio
    python benchmarks/bench_stft.py --json out.json # machine-readable output
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from audio_studio.dsp import (  # noqa: E402
    EffectChain,
    FadeEffect,
    NormalizeEffect,
    RealtimeSpectrum,
    SpectralAnalyzer,
    ThreeBandEQ,
)

SAMPLE_RATE = 48_000
DEFAULT_DURATION_S = 60.0


@dataclass
class Result:
    """One measured operation."""

    group: str
    name: str
    audio_seconds: float
    median_s: float
    best_s: float
    stdev_s: float
    runs: int
    detail: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def realtime_factor(self) -> float:
        """Seconds of audio processed per second of wall clock."""
        return self.audio_seconds / self.median_s if self.median_s > 0 else float("inf")

    @property
    def ms_per_audio_second(self) -> float:
        return self.median_s * 1000.0 / self.audio_seconds if self.audio_seconds else 0.0


def timeit(
    function: Callable[[], object],
    runs: int = 5,
    warmup: int = 1,
) -> tuple[float, float, float]:
    """Return ``(median, best, stdev)`` wall-clock seconds over ``runs`` calls."""
    for _ in range(warmup):
        function()
    samples = []
    for _ in range(runs):
        start = time.perf_counter()
        function()
        samples.append(time.perf_counter() - start)
    return (
        statistics.median(samples),
        min(samples),
        statistics.stdev(samples) if len(samples) > 1 else 0.0,
    )


def make_signal(duration_s: float, channels: int = 2, dtype=np.float32) -> np.ndarray:
    """Broadband stereo test material, planar ``(channels, samples)``."""
    n = int(duration_s * SAMPLE_RATE)
    t = np.arange(n, dtype=np.float64) / SAMPLE_RATE
    rng = np.random.default_rng(7)
    base = (
        0.3 * np.sin(2 * np.pi * 220.0 * t)
        + 0.2 * np.sin(2 * np.pi * 1_760.0 * t)
        + 0.1 * rng.standard_normal(n)
    )
    return np.stack([base * (1.0 - 0.1 * i) for i in range(channels)]).astype(dtype)


# ---------------------------------------------------------------------------
# benchmark groups
# ---------------------------------------------------------------------------


def bench_stft_sizes(audio: np.ndarray, duration_s: float, runs: int) -> list[Result]:
    """The headline case: STFT of 60 s stereo across FFT sizes."""
    results = []
    for fft_size in (512, 1024, 2048, 4096, 8192, 16384):
        analyzer = SpectralAnalyzer(
            sample_rate=SAMPLE_RATE, fft_size=fft_size, dtype=np.float32
        )
        median, best, stdev = timeit(lambda a=analyzer: a.stft(audio), runs=runs)
        frames = analyzer.config.n_frames(audio.shape[1])
        results.append(
            Result(
                group="STFT (stereo, float32, 75% overlap)",
                name=f"fft={fft_size}",
                audio_seconds=duration_s,
                median_s=median,
                best_s=best,
                stdev_s=stdev,
                runs=runs,
                detail=(
                    f"{frames} frames x {analyzer.n_bins} bins x2 ch, "
                    f"df={analyzer.config.frequency_resolution_hz:.1f} Hz"
                ),
                extra={"fft_size": fft_size, "frames": frames, "bins": analyzer.n_bins},
            )
        )
    return results


def bench_overlap(audio: np.ndarray, duration_s: float, runs: int) -> list[Result]:
    """Cost scales with frame count, so overlap is the biggest single lever."""
    results = []
    for overlap, hop in ((0.0, 2048), (0.5, 1024), (0.75, 512), (0.875, 256)):
        analyzer = SpectralAnalyzer(
            sample_rate=SAMPLE_RATE, fft_size=2048, hop_size=hop, dtype=np.float32
        )
        median, best, stdev = timeit(lambda a=analyzer: a.stft(audio), runs=runs)
        results.append(
            Result(
                group="Overlap (fft=2048, stereo, float32)",
                name=f"{overlap * 100:.1f}% overlap",
                audio_seconds=duration_s,
                median_s=median,
                best_s=best,
                stdev_s=stdev,
                runs=runs,
                detail=f"hop={hop}, {analyzer.config.n_frames(audio.shape[1])} frames",
                extra={"hop": hop, "overlap": overlap},
            )
        )
    return results


def bench_precision(audio: np.ndarray, duration_s: float, runs: int) -> list[Result]:
    """float32 versus float64 for the same transform."""
    results = []
    for dtype, label in ((np.float32, "float32"), (np.float64, "float64")):
        analyzer = SpectralAnalyzer(sample_rate=SAMPLE_RATE, fft_size=2048, dtype=dtype)
        buffer = audio.astype(dtype)
        median, best, stdev = timeit(lambda a=analyzer, b=buffer: a.stft(b), runs=runs)
        results.append(
            Result(
                group="Precision (fft=2048, stereo)",
                name=label,
                audio_seconds=duration_s,
                median_s=median,
                best_s=best,
                stdev_s=stdev,
                runs=runs,
                extra={"dtype": label},
            )
        )
    return results


def bench_threads(audio: np.ndarray, duration_s: float, runs: int) -> list[Result]:
    """scipy.fft worker threads. Diminishing past a few cores on this workload."""
    results = []
    for workers in (1, 2, 4, -1):
        analyzer = SpectralAnalyzer(
            sample_rate=SAMPLE_RATE, fft_size=2048, dtype=np.float32, fft_workers=workers
        )
        median, best, stdev = timeit(lambda a=analyzer: a.stft(audio), runs=runs)
        results.append(
            Result(
                group="FFT workers (fft=2048, stereo, float32)",
                name="all cores" if workers == -1 else f"{workers} worker(s)",
                audio_seconds=duration_s,
                median_s=median,
                best_s=best,
                stdev_s=stdev,
                runs=runs,
                extra={"workers": workers},
            )
        )
    return results


def bench_pipeline(audio: np.ndarray, duration_s: float, runs: int) -> list[Result]:
    """Whole-operation costs a caller actually pays."""
    results = []
    analyzer = SpectralAnalyzer(sample_rate=SAMPLE_RATE, fft_size=2048, dtype=np.float32)

    def spectrogram_db() -> None:
        analyzer.spectrogram(audio).to_db()

    operations = [
        ("stft only", lambda: analyzer.stft(audio)),
        ("spectrogram (calibrated)", lambda: analyzer.spectrogram(audio)),
        ("spectrogram -> dB", spectrogram_db),
        ("istft (resynthesis)", None),
    ]

    stft = analyzer.stft(audio)
    operations[-1] = ("istft (resynthesis)", lambda: analyzer.istft(stft, length=audio.shape[1]))

    for name, function in operations:
        median, best, stdev = timeit(function, runs=max(3, runs // 2))
        results.append(
            Result(
                group="Pipeline stages (fft=2048, stereo, float32)",
                name=name,
                audio_seconds=duration_s,
                median_s=median,
                best_s=best,
                stdev_s=stdev,
                runs=max(3, runs // 2),
            )
        )
    return results


def bench_effects(audio: np.ndarray, duration_s: float, runs: int) -> list[Result]:
    """Offline effect throughput on the same buffer."""
    chain = EffectChain([
        ThreeBandEQ(low_gain_db=3.0, mid_gain_db=-2.0, high_gain_db=4.0),
        NormalizeEffect(target_db=-1.0, mode="true_peak"),
        FadeEffect(fade_in_s=0.01, fade_out_s=0.05),
    ])
    operations = [
        ("3-band EQ", ThreeBandEQ(low_gain_db=3.0, mid_gain_db=-2.0, high_gain_db=4.0)),
        ("normalize (peak)", NormalizeEffect(target_db=-1.0, mode="peak")),
        ("normalize (true peak)", NormalizeEffect(target_db=-1.0, mode="true_peak")),
        ("fade in/out", FadeEffect(fade_in_s=0.01, fade_out_s=0.05)),
        ("full chain", chain),
    ]

    results = []
    for name, effect in operations:
        median, best, stdev = timeit(
            lambda e=effect: e.process(audio, SAMPLE_RATE), runs=max(3, runs // 2)
        )
        results.append(
            Result(
                group="Effects (stereo, float32, offline)",
                name=name,
                audio_seconds=duration_s,
                median_s=median,
                best_s=best,
                stdev_s=stdev,
                runs=max(3, runs // 2),
            )
        )
    return results


def bench_realtime(duration_s: float, runs: int) -> list[Result]:
    """Live metering path, measured block by block as a device would call it."""
    results = []
    audio = make_signal(min(duration_s, 10.0), channels=2)
    seconds = audio.shape[1] / SAMPLE_RATE

    for block_size in (128, 256, 512, 1024):
        blocks = [audio[:, i : i + block_size] for i in range(0, audio.shape[1], block_size)]

        def run(bs=blocks) -> None:
            realtime = RealtimeSpectrum(
                sample_rate=SAMPLE_RATE, fft_size=2048, hop_size=512, dtype=np.float32
            )
            for block in bs:
                realtime.push(block)

        median, best, stdev = timeit(run, runs=max(3, runs // 2))
        results.append(
            Result(
                group="Realtime spectrum (fft=2048, hop=512, stereo)",
                name=f"block={block_size}",
                audio_seconds=seconds,
                median_s=median,
                best_s=best,
                stdev_s=stdev,
                runs=max(3, runs // 2),
                detail=f"{block_size / SAMPLE_RATE * 1000:.1f} ms per callback",
                extra={"block_size": block_size},
            )
        )
    return results


def bench_render(runs: int) -> list[Result]:
    """Spectrogram-to-pixels cost, which sets the interactive frame rate."""
    try:
        from PySide6.QtWidgets import QApplication

        from audio_studio.ui.spectrogram_widget import SpectrogramWidget
    except ImportError:
        return []

    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    audio = make_signal(60.0, channels=1)[0]
    analyzer = SpectralAnalyzer(sample_rate=SAMPLE_RATE, fft_size=2048, dtype=np.float32)
    spectrum = analyzer.spectrogram(audio)

    widget = SpectrogramWidget()
    widget.set_spectrogram(spectrum)
    widget.set_db_range(-100.0, 0.0)

    def cold(width: int, height: int) -> None:
        """A first paint: the pooled pixel grid has to be built from the STFT."""
        widget._invalidate(data_changed=True)  # noqa: SLF001 - drop the render caches
        widget.render_image(width, height)

    results = []
    for width, height in ((640, 360), (1280, 720), (1920, 1080)):
        # Two very different costs share one entry point, and only reporting
        # the warm one would claim a frame rate the app never sees on new audio.
        for label, call in (
            ("first paint", lambda w=width, h=height: cold(w, h)),
            ("palette change", lambda w=width, h=height: widget.render_image(w, h)),
        ):
            median, best, stdev = timeit(call, runs=max(5, runs))
            results.append(
                Result(
                    group="Spectrogram render (60 s source, mono)",
                    name=f"{width}x{height} {label}",
                    audio_seconds=60.0,
                    median_s=median,
                    best_s=best,
                    stdev_s=stdev,
                    runs=max(5, runs),
                    detail=f"{1.0 / median:.0f} fps" if median > 0 else "",
                    extra={"fps": 1.0 / median if median > 0 else 0.0},
                )
            )
    del app
    return results


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------


def print_report(results: list[Result], duration_s: float) -> None:
    print()
    print("=" * 84)
    print("Audio Studio DSP benchmark")
    print("=" * 84)
    print(f"  python     {platform.python_version()} on {platform.system()} {platform.machine()}")
    print(f"  numpy      {np.__version__}")
    try:
        import scipy

        print(f"  scipy      {scipy.__version__}")
    except ImportError:
        print("  scipy      not installed (numpy FFT fallback)")
    print(f"  processor  {platform.processor() or 'unknown'}")
    print(f"  audio      {duration_s:g} s @ {SAMPLE_RATE} Hz stereo")
    print()

    current_group = None
    for result in results:
        if result.group != current_group:
            current_group = result.group
            print(f"  {current_group}")
            print(
                f"    {'case':<26}{'median':>10}{'best':>10}"
                f"{'x realtime':>13}   {'notes'}"
            )
            print("    " + "-" * 76)
        print(
            f"    {result.name:<26}"
            f"{result.median_s * 1000:>8.1f}ms"
            f"{result.best_s * 1000:>8.1f}ms"
            f"{result.realtime_factor:>12.0f}x   "
            f"{result.detail}"
        )
        if result is results[-1] or result.group != results[results.index(result) + 1].group:
            print()


def print_headline(results: list[Result], duration_s: float) -> None:
    headline = next(
        (
            r
            for r in results
            if r.group.startswith("STFT") and r.extra.get("fft_size") == 2048
        ),
        None,
    )
    if headline is None:
        return
    print("=" * 84)
    print("Headline: STFT of one minute of 48 kHz stereo (fft=2048, hop=512, Hann, float32)")
    print("=" * 84)
    print(f"    median      {headline.median_s * 1000:.1f} ms")
    print(f"    best        {headline.best_s * 1000:.1f} ms")
    print(f"    realtime    {headline.realtime_factor:.0f}x")
    print(f"    per second  {headline.ms_per_audio_second:.2f} ms of CPU per second of audio")
    print(f"    output      {headline.detail}")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--duration", type=float, default=DEFAULT_DURATION_S, help="seconds of audio to process"
    )
    parser.add_argument("--runs", type=int, default=5, help="timed repetitions per case")
    parser.add_argument("--json", type=Path, help="also write results to this JSON file")
    parser.add_argument("--quick", action="store_true", help="STFT sizes only")
    args = parser.parse_args(argv)

    audio = make_signal(args.duration, channels=2)
    duration_s = audio.shape[1] / SAMPLE_RATE

    results: list[Result] = bench_stft_sizes(audio, duration_s, args.runs)
    if not args.quick:
        results += bench_overlap(audio, duration_s, args.runs)
        results += bench_precision(audio, duration_s, args.runs)
        results += bench_threads(audio, duration_s, args.runs)
        results += bench_pipeline(audio, duration_s, args.runs)
        results += bench_effects(audio, duration_s, args.runs)
        results += bench_realtime(duration_s, args.runs)
        results += bench_render(args.runs)

    print_report(results, duration_s)
    print_headline(results, duration_s)

    if args.json:
        payload = {
            "platform": {
                "python": platform.python_version(),
                "system": platform.system(),
                "machine": platform.machine(),
                "numpy": np.__version__,
            },
            "sample_rate": SAMPLE_RATE,
            "duration_s": duration_s,
            "results": [
                {**asdict(r), "realtime_factor": r.realtime_factor} for r in results
            ],
        }
        args.json.write_text(json.dumps(payload, indent=2))
        print(f"  wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
