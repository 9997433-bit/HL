#!/usr/bin/env python3
"""Real PortAudio/PulseAudio recording soak for SOTA checklist item C2.

The formal run records at least 60 wall-clock minutes and 60 minutes of audio
at 48 kHz stereo through ``SoundDeviceRecorder``.  The input is the monitor of
a 48 kHz PulseAudio null sink fed by PulseAudio's sine generator.  This keeps
the source deterministic while retaining the real PortAudio callback,
``AudioRecorder`` accumulation, streamed PCM-24 BWF writer, flush/fsync, stop,
and atomic-publish paths used by the product.

There is deliberately no accelerated mode.  A PulseAudio monitor is paced by
the server clock, and manually invoking a callback or pumping ``NullRecorder``
would not demonstrate one hour of stable real callback scheduling.

Examples::

    python3 benchmarks/recording_stability_soak.py --formal
    python3 benchmarks/recording_stability_soak.py --duration-seconds 10
    python3 benchmarks/recording_stability_soak.py --formal --work-dir /var/tmp/soak
"""

from __future__ import annotations

import argparse
import gc
import json
import math
import os
import platform
import resource
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
AUDIO_STUDIO_ROOT = REPOSITORY_ROOT / "audio-studio"
if str(AUDIO_STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(AUDIO_STUDIO_ROOT))

from audio_studio.core.recorder import SoundDeviceRecorder

SAMPLE_RATE = 48_000
CHANNELS = 2
FORMAL_DURATION_SECONDS = 3_600.0
DEFAULT_BLOCK_SIZE = 1_024
SOURCE_FREQUENCY_HZ = 997
DEFAULT_REPORT_PATH = (
    REPOSITORY_ROOT / ".agent_workspace/round3/recording-stability-report.json"
)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--duration-seconds",
        type=float,
        default=FORMAL_DURATION_SECONDS,
        help="minimum wall-clock and captured-audio duration (default: 3600)",
    )
    parser.add_argument(
        "--block-size",
        type=int,
        default=DEFAULT_BLOCK_SIZE,
        help="PortAudio input callback block size (default: 1024)",
    )
    parser.add_argument(
        "--device",
        default="pulse",
        help="sounddevice input device index/name (default: pulse)",
    )
    parser.add_argument(
        "--max-xruns",
        type=int,
        default=0,
        help="maximum accepted PortAudio input under/overflow callbacks (default: 0)",
    )
    parser.add_argument(
        "--max-overrun-seconds",
        type=float,
        default=300.0,
        help="extra wall time allowed to collect the requested frames (default: 300)",
    )
    parser.add_argument(
        "--formal",
        action="store_true",
        help="request formal C2 evidence; requires a passing 3600-second 48k/stereo run",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=None,
        help="retain the recorded BWF in this directory (default: temporary directory)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help=f"JSON report path (default: {DEFAULT_REPORT_PATH})",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress progress lines on stderr",
    )
    return parser.parse_args(argv)


def _progress(quiet: bool, message: str) -> None:
    if not quiet:
        print(f"[recording-soak] {message}", file=sys.stderr, flush=True)


def _command(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, capture_output=True, check=False, text=True)
    if check and completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
        raise RuntimeError(f"{' '.join(command)} failed: {detail}")
    return completed


def _pactl(*arguments: str, check: bool = True) -> str:
    return _command(["pactl", *arguments], check=check).stdout.strip()


def _pulse_info() -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in _pactl("info").splitlines():
        key, separator, value = line.partition(":")
        if separator:
            fields[key.strip()] = value.strip()
    return fields


class _PulseMonitor:
    """Temporary real-time PulseAudio null sink and deterministic monitor input."""

    def __init__(self, sample_rate: int, channels: int) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.sink_name = f"audio_studio_soak_{os.getpid()}"
        self.source_name = f"{self.sink_name}.monitor"
        self._module_ids: list[int] = []
        self._previous_source = ""
        self._previous_sink = ""
        self._previous_source_env = os.environ.get("PULSE_SOURCE")
        self.server_started_by_harness = False

    def __enter__(self) -> _PulseMonitor:  # noqa: PYI034 - Python 3.10 has no typing.Self
        if _command(["pactl", "info"], check=False).returncode != 0:
            _command(["pulseaudio", "--start", "--exit-idle-time=-1"])
            self.server_started_by_harness = True
            for _ in range(50):
                if _command(["pactl", "info"], check=False).returncode == 0:
                    break
                time.sleep(0.1)
            else:
                raise RuntimeError("PulseAudio did not become ready")

        self._previous_source = _pactl("get-default-source")
        self._previous_sink = _pactl("get-default-sink")
        try:
            null_sink = _pactl(
                "load-module",
                "module-null-sink",
                f"sink_name={self.sink_name}",
                f"rate={self.sample_rate}",
                f"channels={self.channels}",
                "sink_properties=device.description=AudioStudioRecordingSoak",
            )
            self._module_ids.append(int(null_sink))
            sine = _pactl(
                "load-module",
                "module-sine",
                f"sink={self.sink_name}",
                f"frequency={SOURCE_FREQUENCY_HZ}",
            )
            self._module_ids.append(int(sine))
            _pactl("set-default-sink", self.sink_name)
            _pactl("set-default-source", self.source_name)
            os.environ["PULSE_SOURCE"] = self.source_name
            return self
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        if self._previous_source:
            _pactl("set-default-source", self._previous_source, check=False)
        if self._previous_sink:
            _pactl("set-default-sink", self._previous_sink, check=False)
        for module_id in reversed(self._module_ids):
            _pactl("unload-module", str(module_id), check=False)
        self._module_ids.clear()
        if self._previous_source_env is None:
            os.environ.pop("PULSE_SOURCE", None)
        else:
            os.environ["PULSE_SOURCE"] = self._previous_source_env

    def __exit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
        self.close()


def _device_details(device: str) -> dict[str, Any]:
    import sounddevice as sd

    selected: int | str = int(device) if device.lstrip("-").isdigit() else device
    info = sd.query_devices(selected, "input")
    host = sd.query_hostapis(int(info["hostapi"]))
    portaudio_version, portaudio_text = sd.get_portaudio_version()
    return {
        "requested": selected,
        "name": str(info["name"]),
        "host_api": str(host["name"]),
        "max_input_channels": int(info["max_input_channels"]),
        "default_sample_rate": float(info["default_samplerate"]),
        "default_low_input_latency_seconds": float(info["default_low_input_latency"]),
        "portaudio_version": int(portaudio_version),
        "portaudio_version_text": str(portaudio_text),
        "sounddevice_version": str(sd.__version__),
    }


def _git_revision() -> str:
    completed = _command(
        ["git", "-C", str(REPOSITORY_ROOT), "rev-parse", "HEAD"],
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def _maximum_rss_mib() -> float:
    rss = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if sys.platform == "darwin":
        rss /= 1024.0
    return round(rss / 1024.0, 3)


def _signal_metrics(data: np.ndarray, sample_rate: int) -> dict[str, float]:
    window_frames = min(sample_rate, data.shape[0])
    first = data[:window_frames].astype(np.float64, copy=False)
    last = data[-window_frames:].astype(np.float64, copy=False)

    def peak(block: np.ndarray) -> float:
        return float(np.max(np.abs(block))) if block.size else 0.0

    def rms(block: np.ndarray) -> float:
        return float(np.sqrt(np.mean(np.square(block)))) if block.size else 0.0

    return {
        "window_seconds": round(window_frames / sample_rate, 6),
        "first_window_peak": round(peak(first), 8),
        "first_window_rms": round(rms(first), 8),
        "last_window_peak": round(peak(last), 8),
        "last_window_rms": round(rms(last), 8),
    }


def _record(
    args: argparse.Namespace,
    target: Path,
    pulse: _PulseMonitor,
) -> tuple[dict[str, Any], dict[str, Any]]:
    recorder = SoundDeviceRecorder(device=args.device)
    required_frames = math.ceil(args.duration_seconds * SAMPLE_RATE)
    stream_aborted = False
    captured = None
    try:
        recorder.open(
            SAMPLE_RATE,
            CHANNELS,
            block_size=args.block_size,
            target_path=target,
            description="Audio Studio C2 60-minute recording stability soak",
            originator="Audio Studio benchmark",
            flush_interval=1.0,
        )
        recorder.start()
        started = time.perf_counter()
        timeout_at = started + args.duration_seconds + args.max_overrun_seconds
        next_progress = started + min(300.0, max(1.0, args.duration_seconds / 10.0))
        progress_interval = min(300.0, max(1.0, args.duration_seconds / 10.0))
        while True:
            now = time.perf_counter()
            elapsed = now - started
            enough_wall_time = elapsed >= args.duration_seconds
            enough_frames = recorder.frame_count >= required_frames
            if enough_wall_time and enough_frames:
                break
            if now >= timeout_at:
                break
            if not recorder.stream_active:
                stream_aborted = True
                break
            if now >= next_progress:
                _progress(
                    args.quiet,
                    f"{elapsed / 60.0:5.1f} min wall, "
                    f"{recorder.duration / 60.0:5.1f} min captured, "
                    f"xruns={recorder.xruns}, callback_errors={recorder.callback_errors}",
                )
                next_progress += progress_interval
            time.sleep(0.1)

        recording_wall_seconds = time.perf_counter() - started
        finalize_started = time.perf_counter()
        captured = recorder.stop()
        finalization_seconds = time.perf_counter() - finalize_started
        recorder.close()

        file_info = sf.info(str(target))
        file_stat = target.stat()
        allocated_bytes = max(0, int(getattr(file_stat, "st_blocks", 0)) * 512)
        signal = _signal_metrics(captured.data, SAMPLE_RATE)
        measured = {
            "wall_clock_seconds": round(recording_wall_seconds, 6),
            "captured_frames": captured.n_frames,
            "captured_duration_seconds": round(captured.duration, 6),
            "required_frames": required_frames,
            "callback_count": recorder.callback_count,
            "callback_errors": recorder.callback_errors,
            "input_underflows": recorder.input_underflows,
            "input_overflows": recorder.input_overflows,
            "xruns": recorder.xruns,
            "stream_aborted": stream_aborted,
            "finalization_seconds": round(finalization_seconds, 6),
            "output_file_frames": int(file_info.frames),
            "output_file_sample_rate": int(file_info.samplerate),
            "output_file_channels": int(file_info.channels),
            "output_file_subtype": str(file_info.subtype),
            "output_file_bytes": file_stat.st_size,
            "output_file_allocated_bytes": allocated_bytes,
            "maximum_rss_mib": _maximum_rss_mib(),
            "source_signal": signal,
        }
        source = {
            "type": "pulseaudio-null-sink-monitor",
            "sink": pulse.sink_name,
            "monitor_source": pulse.source_name,
            "generator": "PulseAudio module-sine",
            "frequency_hz": SOURCE_FREQUENCY_HZ,
        }
        return measured, source
    finally:
        if recorder.is_open:
            recorder.close()
        del captured
        del recorder
        gc.collect()


def run_benchmark(args: argparse.Namespace, scratch: Path) -> dict[str, Any]:
    if not math.isfinite(args.duration_seconds) or args.duration_seconds <= 0.0:
        raise ValueError("duration_seconds must be positive and finite")
    if args.block_size <= 0:
        raise ValueError("block_size must be positive")
    if args.max_xruns < 0:
        raise ValueError("max_xruns must be non-negative")
    if not math.isfinite(args.max_overrun_seconds) or args.max_overrun_seconds <= 0.0:
        raise ValueError("max_overrun_seconds must be positive and finite")
    if args.formal and args.duration_seconds < FORMAL_DURATION_SECONDS:
        raise ValueError("--formal requires duration_seconds >= 3600")

    scratch.mkdir(parents=True, exist_ok=True)
    target = scratch / "recording-stability-48k-stereo-pcm24.wav"
    _progress(
        args.quiet,
        f"wall-clock recording: {args.duration_seconds / 60.0:g} min at "
        f"{SAMPLE_RATE} Hz / {CHANNELS} ch / {args.block_size} frames",
    )
    with _PulseMonitor(SAMPLE_RATE, CHANNELS) as pulse:
        pulse_server = _pulse_info()
        device = _device_details(str(args.device))
        measured, source = _record(args, target, pulse)
        pulse_started = pulse.server_started_by_harness

    signal = measured["source_signal"]
    duration_passed = (
        measured["wall_clock_seconds"] >= args.duration_seconds
        and measured["captured_frames"] >= measured["required_frames"]
        and measured["captured_duration_seconds"] >= args.duration_seconds
    )
    callbacks_passed = (
        measured["callback_count"] > 0
        and measured["callback_errors"] == 0
        and measured["xruns"] <= args.max_xruns
        and not measured["stream_aborted"]
    )
    file_passed = (
        measured["output_file_frames"] == measured["captured_frames"]
        and measured["output_file_sample_rate"] == SAMPLE_RATE
        and measured["output_file_channels"] == CHANNELS
        and measured["output_file_subtype"] == "PCM_24"
        and measured["output_file_bytes"] > measured["captured_frames"] * CHANNELS * 3
    )
    signal_passed = (
        signal["first_window_peak"] > 0.01
        and signal["first_window_rms"] > 0.001
        and signal["last_window_peak"] > 0.01
        and signal["last_window_rms"] > 0.001
    )
    threshold_passed = duration_passed and callbacks_passed and file_passed and signal_passed
    formal_eligible = (
        args.formal
        and args.duration_seconds >= FORMAL_DURATION_SECONDS
        and measured["required_frames"] >= FORMAL_DURATION_SECONDS * SAMPLE_RATE
        and device["host_api"] == "ALSA"
    )
    formal_verified = bool(formal_eligible and threshold_passed)
    result = {
        "slo_id": "recording-60m",
        "title": "60-minute 48 kHz stereo recording stability",
        "status": "pass" if threshold_passed else "fail",
        "threshold_pass": threshold_passed,
        "evidence": "direct-portaudio-pulseaudio",
        "formal_slo_verified": formal_verified,
        "measured": measured,
        "threshold": {
            "wall_clock_seconds_min": args.duration_seconds,
            "captured_frames_min": measured["required_frames"],
            "captured_duration_seconds_min": args.duration_seconds,
            "callback_count_min": 1,
            "callback_errors_max": 0,
            "xruns_max": args.max_xruns,
            "stream_aborted": False,
            "output_file_frames_equal_captured_frames": True,
            "source_window_peak_min": 0.01,
            "source_window_rms_min": 0.001,
        },
        "method": (
            "SoundDeviceRecorder captured a generated tone from a PulseAudio null-sink "
            "monitor through a real PortAudio callback into the product PCM-24 BWF "
            "writer; the run continued until both wall time and captured frames met "
            "the requested duration."
        ),
        "limitation": (
            "The input is a virtual PulseAudio monitor, not a physical ADC. This proves "
            "the real PortAudio/PulseAudio callback and product recording/file path on "
            "this Linux host, but not analog hardware or another operating system. "
            "No accelerated mode was used or claimed."
        ),
    }
    return {
        "schema_version": 1,
        "harness": "benchmarks/recording_stability_soak.py",
        "checklist_item": "C2",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "git_revision": _git_revision(),
        "mode": "wall-clock",
        "accelerated": False,
        "evidence": "direct-portaudio-pulseaudio",
        "formal_slo_verified": formal_verified,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor() or platform.machine() or "unknown",
            "backend": "SoundDeviceRecorder",
            "pulse_server_name": pulse_server.get("Server Name", "unknown"),
            "pulse_server_version": pulse_server.get("Server Version", "unknown"),
            "pulse_server_started_by_harness": pulse_started,
            "device": device,
        },
        "config": {
            "duration_seconds": args.duration_seconds,
            "sample_rate": SAMPLE_RATE,
            "channels": CHANNELS,
            "block_size": args.block_size,
            "max_xruns": args.max_xruns,
            "max_overrun_seconds": args.max_overrun_seconds,
            "formal_requested": bool(args.formal),
        },
        "source": source,
        "results": [result],
        "summary": {
            "passed": int(threshold_passed),
            "failed": int(not threshold_passed),
            "formal_slos_verified": int(formal_verified),
        },
    }


def _write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    output = args.output if args.output.is_absolute() else REPOSITORY_ROOT / args.output
    if args.work_dir is None:
        with tempfile.TemporaryDirectory(prefix="recording-stability-soak-") as directory:
            report = run_benchmark(args, Path(directory))
    else:
        work_dir = args.work_dir if args.work_dir.is_absolute() else REPOSITORY_ROOT / args.work_dir
        report = run_benchmark(args, work_dir)

    _write_report(report, output)
    print(json.dumps(report, indent=2))
    _progress(args.quiet, f"report written to {output}")
    result = report["results"][0]
    return 0 if result["threshold_pass"] and (not args.formal or result["formal_slo_verified"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
