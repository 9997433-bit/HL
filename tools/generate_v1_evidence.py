#!/usr/bin/env python3
"""Generate the measured v1.0 SOTA evidence artifacts.

Produces, under ``.agent_workspace/v1.0/``:

- ``tpdf-spectrum-report.json`` (checklist A7): quantization-error spectrum of
  ``quantize_with_tpdf`` at 16 bits — error RMS against the LSB/2 theoretical
  figure, spectral flatness/whiteness, the absence of harmonic spurs that the
  undithered quantizer shows, plus the silence-tail metrics mirrored from
  ``tests/test_dither.py``.
- ``plugin-host-report.json`` (checklist B6): the plugin-host lifecycle driven
  with in-process mock ``PluginHost`` implementations (``evidence_type:
  mock-host`` — no real VST3 binaries exist in CI): load/process, state-blob
  save/restore, and a sample-exact PDC null test through ``EffectPreview``.
- ``batch-loudness-report.json`` (checklist B7): the real batch CLI
  (``audio_studio.batch.cli``) run over 10 synthesized WAV files with
  ``--lufs -16 --format flac``, each output re-measured with the BS.1770 meter.

Run from the repository root::

    python tools/generate_v1_evidence.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from scipy.signal import welch

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
AUDIO_STUDIO_ROOT = REPOSITORY_ROOT / "audio-studio"
if str(AUDIO_STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(AUDIO_STUDIO_ROOT))

OUTPUT_DIR = REPOSITORY_ROOT / ".agent_workspace/v1.0"

SAMPLE_RATE = 48_000
BIT_DEPTH = 16
LSB = 1.0 / float(1 << (BIT_DEPTH - 1))


def _dbfs(value: float) -> float:
    return 20.0 * float(np.log10(max(value, 1e-30)))


def _write(name: str, payload: dict[str, Any]) -> None:
    path = OUTPUT_DIR / name
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path.relative_to(REPOSITORY_ROOT)} (status: {payload['status']})")


# -- A7: TPDF dither spectrum --------------------------------------------------


def _spur_above_median_db(error: np.ndarray) -> float:
    """Largest PSD bin over the median, in dB, on a Welch-averaged spectrum.

    With ~60 averaged segments a white spectrum keeps this figure under ~2 dB;
    the periodic error of an undithered quantizer shows tens of dB.
    """
    _freqs, psd = welch(error, fs=SAMPLE_RATE, nperseg=8_192)
    interior = psd[1:-1]
    return 10.0 * float(np.log10(interior.max() / np.median(interior)))


def _spectral_flatness(error: np.ndarray) -> float:
    _freqs, psd = welch(error, fs=SAMPLE_RATE, nperseg=8_192)
    interior = psd[1:-1]
    return float(np.exp(np.mean(np.log(interior))) / np.mean(interior))


def _silence_tail_metrics() -> dict[str, float]:
    """The `tests/test_dither.py` scenario, measured rather than asserted."""
    from audio_studio.core.loader import save_audio
    from audio_studio.core.types import AudioBuffer

    tone_frames, tail_frames = 4_800, 8_192
    time = np.arange(tone_frames, dtype=np.float32) / SAMPLE_RATE
    tone = 0.25 * np.sin(2.0 * np.pi * 997.0 * time)
    data = np.concatenate((tone, np.zeros(tail_frames, dtype=np.float32)))

    with tempfile.TemporaryDirectory() as scratch:
        target = Path(scratch) / "dithered.wav"
        save_audio(target, AudioBuffer(data[:, np.newaxis], SAMPLE_RATE), subtype="PCM_16")
        rendered, _sr = sf.read(target, dtype="float32", always_2d=True)

    tail = rendered[-tail_frames:, 0].astype(np.float64)
    return {
        "silence_tail_peak_lsb": float(np.max(np.abs(tail))) / LSB,
        "silence_tail_rms_dbfs": _dbfs(float(np.sqrt(np.mean(np.square(tail))))),
        "silence_tail_nonzero_samples": int(np.count_nonzero(tail)),
    }


def generate_tpdf_spectrum_report() -> None:
    from audio_studio.core.loader import quantize_with_tpdf

    n_samples = 1 << 18
    time = np.arange(n_samples, dtype=np.float64) / SAMPLE_RATE
    amplitude = 10.0 ** (-60.0 / 20.0)
    signal = amplitude * np.sin(2.0 * np.pi * 997.0 * time)

    rng = np.random.default_rng(1770)
    dithered = quantize_with_tpdf(signal.astype(np.float32), BIT_DEPTH, rng=rng)
    undithered = np.rint(signal / LSB) * LSB

    dithered_error = dithered.astype(np.float64) - signal
    undithered_error = undithered - signal

    error_rms_dbfs = _dbfs(float(np.sqrt(np.mean(np.square(dithered_error)))))
    # TPDF adds two uniform LSB variates to the LSB/sqrt(12) quantization
    # noise: sqrt(1/12 + 2/12) LSB = LSB/2 total error RMS.
    expected_error_rms_dbfs = _dbfs(LSB / 2.0)

    metrics: dict[str, Any] = {
        "error_rms_dbfs": round(error_rms_dbfs, 3),
        "expected_error_rms_dbfs": round(expected_error_rms_dbfs, 3),
        "spectral_flatness": round(_spectral_flatness(dithered_error), 4),
        "dithered_max_spur_above_median_db": round(
            _spur_above_median_db(dithered_error), 3
        ),
        "undithered_max_spur_above_median_db": round(
            _spur_above_median_db(undithered_error), 3
        ),
    }
    tail = _silence_tail_metrics()
    metrics.update({key: round(value, 4) for key, value in tail.items()})

    checks = {
        "error_rms_within_1db_of_theory": abs(
            metrics["error_rms_dbfs"] - metrics["expected_error_rms_dbfs"]
        )
        < 1.0,
        "error_spectrum_is_white": metrics["spectral_flatness"] > 0.9
        and metrics["dithered_max_spur_above_median_db"] < 3.0,
        "dither_removes_harmonic_spurs": metrics["undithered_max_spur_above_median_db"]
        - metrics["dithered_max_spur_above_median_db"]
        > 10.0,
        "silence_tail_noise_bounded_to_one_lsb": 0.0
        < metrics["silence_tail_peak_lsb"] <= 1.0,
    }

    _write(
        "tpdf-spectrum-report.json",
        {
            "artifact": "tpdf-spectrum-report",
            "checklist_item": "A7",
            "generated_by": "tools/generate_v1_evidence.py",
            "status": "pass" if all(checks.values()) else "fail",
            "method": (
                "997 Hz sine at -60 dBFS, 2^18 samples at 48 kHz, quantized to "
                "16 bits with quantize_with_tpdf; quantization-error spectrum "
                "via Welch PSD (nperseg=8192) against the undithered np.rint "
                "quantizer; silence-tail metrics mirror tests/test_dither.py"
            ),
            "sample_rate": SAMPLE_RATE,
            "bit_depth": BIT_DEPTH,
            **metrics,
            "checks": checks,
            "unit_suite": "tests/test_dither.py",
        },
    )


# -- B6: plugin host with mock evidence -----------------------------------------


def generate_plugin_host_report() -> None:
    from audio_studio.core.output import NullOutput
    from audio_studio.dsp.effects import EffectChain, GainEffect
    from audio_studio.dsp.preview import EffectPreview
    from audio_studio.plugins import PluginEffectAdapter, PluginHost

    class MockVst3Host(PluginHost):
        """Transparent host with honest latency and writable parameters."""

        def __init__(self, path: str, latency: int, parameters: dict[str, float]) -> None:
            self._path = Path(path)
            self._latency = int(latency)
            self._parameters = dict(parameters)
            self._tail: np.ndarray | None = None

        @property
        def name(self) -> str:
            return self._path.stem

        @property
        def plugin_path(self) -> Path:
            return self._path

        def prepare(self, sample_rate: float, n_channels: int) -> None:
            self._tail = None

        def reset(self) -> None:
            self._tail = None

        def process_block(self, block: np.ndarray, sample_rate: float) -> np.ndarray:
            audio = np.asarray(block, dtype=np.float32)
            if self._latency <= 0 or audio.shape[-1] == 0:
                return audio
            tail_shape = (*audio.shape[:-1], self._latency)
            if self._tail is None or self._tail.shape != tail_shape:
                self._tail = np.zeros(tail_shape, dtype=np.float32)
            joined = np.concatenate([self._tail, audio], axis=-1)
            self._tail = joined[..., audio.shape[-1] :]
            return joined[..., : audio.shape[-1]]

        def latency_samples(self) -> int:
            return self._latency

        def parameters(self) -> dict[str, float]:
            return dict(self._parameters)

        def set_parameter(self, name: str, value: float) -> None:
            if name not in self._parameters:
                raise KeyError(name)
            self._parameters[name] = value

    catalog = (
        ("/plugins/MockLinearPhaseEQ.vst3", 37, {"low_gain_db": 1.5, "high_gain_db": -2.0}),
        ("/plugins/MockLookaheadLimiter.vst3", 64, {"ceiling_dbtp": -1.0, "release_ms": 50.0}),
        ("/plugins/MockSaturator.vst3", 0, {"drive": 0.25, "mix": 1.0}),
    )

    def stream(preview: EffectPreview, signal: np.ndarray, block: int = 64) -> np.ndarray:
        blocks = [
            preview.process_block(signal[start : start + block], SAMPLE_RATE)
            for start in range(0, signal.shape[0], block)
        ]
        return np.concatenate(blocks)

    plugin_results = []
    for path, latency, parameters in catalog:
        adapter = PluginEffectAdapter(MockVst3Host(path, latency, parameters))

        # Load/process: the adapter reports the host's latency and hands
        # audio through the effect-rack interface without error.
        signal = np.arange(1, 513, dtype=np.float32)[:, np.newaxis]
        processed = adapter.process(signal, SAMPLE_RATE, channels_last=True)
        loaded_ok = processed.shape == signal.shape and adapter.latency_samples() == latency

        # State: mutate a parameter, snapshot, restore into a fresh instance.
        mutated = dict(parameters)
        first_key = next(iter(mutated))
        mutated[first_key] = 0.987
        saved = PluginEffectAdapter(MockVst3Host(path, latency, mutated))
        fresh = PluginEffectAdapter(MockVst3Host(path, latency, parameters))
        blob = saved.state_blob()
        restored_ok = (
            blob is not None
            and fresh.restore_state(blob) is True
            and fresh.plugin_parameters() == mutated
        )

        plugin_results.append(
            {
                "plugin": Path(path).name,
                "latency_samples": latency,
                "load_and_process": "pass" if loaded_ok else "fail",
                "state_restore": "pass" if restored_ok else "fail",
            }
        )

    # PDC null test: an active latent plugin against its bypassed (padded)
    # twin — with compensation on, the two streams must null sample-exactly.
    latency = 37
    signal = np.repeat(
        np.arange(1, 513, dtype=np.float32)[:, np.newaxis], 2, axis=1
    )

    def make_preview(bypass: bool) -> EffectPreview:
        adapter = PluginEffectAdapter(
            MockVst3Host("/plugins/MockLinearPhaseEQ.vst3", latency, {"mix": 1.0})
        )
        adapter.bypass = bypass
        chain = EffectChain([GainEffect(gain_db=0.0, ramp_ms=0.0), adapter])
        return EffectPreview(NullOutput(realtime=False), chain, pdc_enabled=True)

    wet = stream(make_preview(bypass=False), signal)
    dry = stream(make_preview(bypass=True), signal)
    max_null_error = float(np.max(np.abs(wet - dry)))

    expected = np.concatenate(
        [np.zeros((latency, 2), dtype=np.float32), signal]
    )[: signal.shape[0]]
    alignment_error = float(np.max(np.abs(wet - expected)))

    passed = sum(
        1
        for result in plugin_results
        if result["load_and_process"] == "pass" and result["state_restore"] == "pass"
    )
    state_ok = all(result["state_restore"] == "pass" for result in plugin_results)
    pdc_ok = max_null_error == 0.0 and alignment_error == 0.0

    _write(
        "plugin-host-report.json",
        {
            "artifact": "plugin-host-report",
            "checklist_item": "B6",
            "generated_by": "tools/generate_v1_evidence.py",
            "status": "pass" if passed >= 3 and state_ok and pdc_ok else "fail",
            "evidence_type": "mock-host",
            "backend_note": (
                "in-process mock PluginHost implementations; the pedalboard "
                "VST3 backend is not exercised because no plugin binaries "
                "exist in CI — real-plugin compatibility evidence is still open"
            ),
            "mock_plugins_passed": passed,
            "plugins": plugin_results,
            "state_restore": "pass" if state_ok else "fail",
            "pdc_null_test": "pass" if pdc_ok else "fail",
            "pdc_max_null_error": max_null_error,
            "pdc_alignment_error": alignment_error,
            "unit_suites": [
                "audio-studio/tests/test_vst3_host.py",
                "audio-studio/tests/test_plugin_pdc.py",
                "audio-studio/tests/test_plugin_scanner.py",
                "audio-studio/tests/test_plugin_panel.py",
            ],
        },
    )


# -- B7: 10-file -16 LUFS FLAC batch ---------------------------------------------


def generate_batch_loudness_report() -> None:
    from audio_studio.batch.cli import main as batch_main
    from audio_studio.core.loader import load_audio
    from audio_studio.dsp.loudness import LoudnessMeter

    n_files = 10
    duration_s = 3.0
    frames = int(duration_s * SAMPLE_RATE)
    time = np.arange(frames, dtype=np.float64) / SAMPLE_RATE

    with tempfile.TemporaryDirectory() as scratch:
        source_dir = Path(scratch) / "in"
        output_dir = Path(scratch) / "out"
        source_dir.mkdir()

        input_levels_dbfs = []
        for index in range(n_files):
            frequency = 110.0 * (index + 1)
            level_dbfs = -30.0 + 2.0 * index  # -30 .. -12 dBFS
            input_levels_dbfs.append(level_dbfs)
            tone = (10.0 ** (level_dbfs / 20.0)) * np.sin(2.0 * np.pi * frequency * time)
            channels = 1 if index % 2 == 0 else 2
            data = np.repeat(tone[:, np.newaxis], channels, axis=1).astype(np.float32)
            sf.write(source_dir / f"take-{index:02d}.wav", data, SAMPLE_RATE)

        argv = [
            "--input",
            str(source_dir / "*.wav"),
            "--output",
            str(output_dir),
            "--lufs",
            "-16",
            "--format",
            "flac",
        ]
        exit_code = batch_main(argv)

        outputs = sorted(output_dir.glob("*.flac"))
        integrated_lufs = []
        for path in outputs:
            buffer = load_audio(path).buffer
            meter = LoudnessMeter(buffer.sample_rate)
            integrated_lufs.append(
                round(float(meter.integrated(buffer.data, channels_last=True)), 3)
            )

    max_error = max(abs(value + 16.0) for value in integrated_lufs) if integrated_lufs else float("inf")
    ok = (
        exit_code == 0
        and len(outputs) == n_files
        and max_error <= 0.1
    )

    _write(
        "batch-loudness-report.json",
        {
            "artifact": "batch-loudness-report",
            "checklist_item": "B7",
            "generated_by": "tools/generate_v1_evidence.py",
            "status": "pass" if ok else "fail",
            "cli": "python -m audio_studio.batch.cli " + " ".join(argv),
            "exit_code": exit_code,
            "input_files": n_files,
            "input_levels_dbfs": input_levels_dbfs,
            "output_files": len(outputs),
            "output_format": "flac",
            "target_lufs": -16.0,
            "integrated_lufs": integrated_lufs,
            "max_abs_error_lu": round(max_error, 4),
            "unit_suites": [
                "audio-studio/tests/test_batch.py",
                "audio-studio/tests/test_loudness_effect.py",
            ],
        },
    )


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    generate_tpdf_spectrum_report()
    generate_plugin_host_report()
    generate_batch_loudness_report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
