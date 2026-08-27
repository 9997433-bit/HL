"""AES17-style THD+N measurement of Audio Studio's core signal paths.

AES17 measures total harmonic distortion plus noise by driving the device
under test with a 997 Hz sine, removing the fundamental with a notch, and
reading the residual through a 20 Hz - 20 kHz measurement bandwidth. 997 Hz is
the standard's choice because it is incommensurate with common sample rates,
so successive samples exercise different converter codes instead of repeating
a short pattern.

This tool applies that method to the signal paths a mastering session actually
runs audio through: the float32 gain stage, the parametric EQ, the true-peak
limiter passing untouched audio, TPDF-dithered word-length reduction, and the
full save/load PCM export round trip. Hardware converters are out of scope —
each case names the software component it measured, and nothing here claims an
acoustic or electrical measurement.

Two deliberate substitutions, both stricter than the standard's analog
provisions:

* The notch is a least-squares fit of the 997 Hz fundamental (sine, cosine and
  DC terms) subtracted from the output. A fitted notch has zero bandwidth, so
  unlike the standard's analog notch (whose Q the standard has to constrain)
  it removes none of the residual it is trying to expose.
* The 20 Hz - 20 kHz bandwidth limit is applied on the residual's discrete
  spectrum via Parseval's theorem rather than with a filter, which has no
  passband ripple to bias the reading.

The analyzer is validated in-band: a hard-clipped control tone must read the
THD its clipping implies, so a broken notch or band limit cannot silently
report transparency (see :func:`measure_control`).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
for _import_root in (REPOSITORY_ROOT, REPOSITORY_ROOT / "audio-studio"):
    if str(_import_root) not in sys.path:
        sys.path.insert(0, str(_import_root))

from audio_studio.core.loader import load_audio, quantize_with_tpdf, save_audio
from audio_studio.core.types import SAMPLE_DTYPE, AudioBuffer
from audio_studio.dsp.effects import (
    EQBand,
    FilterType,
    GainEffect,
    LimiterEffect,
    ParametricEQ,
)

__all__ = [
    "AES17_CASES",
    "ANALYSIS_SECONDS",
    "BAND_HIGH_HZ",
    "BAND_LOW_HZ",
    "DEFAULT_OUTPUT",
    "FUNDAMENTAL_HZ",
    "Aes17Case",
    "build_report",
    "measure_all",
    "measure_case",
    "measure_control",
    "measure_thd_plus_n",
    "synthesize_stimulus",
    "tpdf_expected_thd_plus_n_db",
    "write_report",
]

#: AES17 standard measurement frequency.
FUNDAMENTAL_HZ = 997.0

#: AES17 standard measurement bandwidth.
BAND_LOW_HZ = 20.0
BAND_HIGH_HZ = 20_000.0

#: Stimulus runs longer than the analysis window so that fades, filter
#: transients and limiter lookahead delay all fall outside what is measured.
TOTAL_SECONDS = 1.4
ANALYSIS_SECONDS = 1.0
FADE_MS = 10.0

#: How far a measured dither figure may sit from its closed-form expectation
#: before the measurement, not the dither, is suspect.
THEORY_TOLERANCE_DB = 1.0

#: How far the recovered fundamental may sit from the stimulus level. The
#: paths measured here are gain-transparent at 997 Hz, so a larger deviation
#: means the case is not measuring what it claims to.
FUNDAMENTAL_TOLERANCE_DB = 0.1

#: The clipped control tone must read at least this THD+N or the analyzer is
#: not detecting distortion at all.
CONTROL_MINIMUM_THD_DB = -30.0

DEFAULT_OUTPUT = Path(".agent_workspace/round3/aes17-report.json")

#: ``dut(stimulus_float32, sample_rate) -> processed`` — one measured path.
DeviceUnderTest = Callable[[np.ndarray, int], np.ndarray]


def _dbfs(value: float) -> float:
    return 20.0 * math.log10(max(float(value), np.finfo(np.float64).tiny))


def tpdf_expected_thd_plus_n_db(
    bit_depth: int, sample_rate: int, level_dbfs: float
) -> float:
    """Closed-form THD+N of ideal TPDF-dithered quantization, in-band.

    Quantization with full-LSB TPDF dither produces a white total error of
    ``LSB / 2`` RMS (variance ``LSB^2/12`` from quantization plus
    ``2 * LSB^2/12`` from the two uniform dither variates). White noise spread
    to Nyquist loses the fraction outside 20 Hz - 20 kHz to the measurement
    bandwidth, and the ratio is taken against the stimulus sine's RMS.
    """
    lsb = 1.0 / float(1 << (bit_depth - 1))
    error_rms = lsb / 2.0
    nyquist = sample_rate / 2.0
    band_fraction = (min(BAND_HIGH_HZ, nyquist) - BAND_LOW_HZ) / nyquist
    in_band_rms = error_rms * math.sqrt(band_fraction)
    signal_rms = 10.0 ** (level_dbfs / 20.0) / math.sqrt(2.0)
    return _dbfs(in_band_rms / signal_rms)


@dataclass(frozen=True)
class Aes17Case:
    """One signal path measured against an explicit THD+N limit."""

    case_id: str
    component: str
    sample_rate: int
    stimulus_level_dbfs: float
    #: Pass gate. Every limit is set from the physics of the path (float32
    #: rounding, dither theory), not tuned to whatever a run produced.
    limit_db: float
    dut: DeviceUnderTest
    #: Closed-form expectation, for the dithered quantization paths where one
    #: exists. Those cases must also land within THEORY_TOLERANCE_DB of it.
    expected_db: float | None = None


def synthesize_stimulus(
    sample_rate: int,
    level_dbfs: float,
    *,
    total_seconds: float = TOTAL_SECONDS,
    fade_ms: float = FADE_MS,
) -> np.ndarray:
    """997 Hz sine at ``level_dbfs``, raised-cosine gated, float64 mono."""
    frame_count = round(sample_rate * total_seconds)
    fade = round(sample_rate * fade_ms / 1000.0)
    time = np.arange(frame_count, dtype=np.float64) / sample_rate
    amplitude = 10.0 ** (level_dbfs / 20.0)
    tone = amplitude * np.sin(2.0 * np.pi * FUNDAMENTAL_HZ * time)
    window = 0.5 - 0.5 * np.cos(np.pi * np.arange(fade) / fade)
    tone[:fade] *= window
    tone[frame_count - fade :] *= window[::-1]
    return tone


def _analysis_window(output: np.ndarray, sample_rate: int) -> np.ndarray:
    """The centred ``ANALYSIS_SECONDS`` of ``output``, clear of every edge."""
    frames = round(sample_rate * ANALYSIS_SECONDS)
    start = (output.size - frames) // 2
    if start <= 0:
        raise ValueError("output is too short for the analysis window")
    return np.asarray(output[start : start + frames], dtype=np.float64)


def _notch_fundamental(window: np.ndarray, sample_rate: int) -> tuple[np.ndarray, float]:
    """Remove the best-fit 997 Hz fundamental; return (residual, its RMS)."""
    time = np.arange(window.size, dtype=np.float64) / sample_rate
    angle = 2.0 * np.pi * FUNDAMENTAL_HZ * time
    basis = np.column_stack((np.sin(angle), np.cos(angle), np.ones_like(time)))
    coefficients, *_ = np.linalg.lstsq(basis, window, rcond=None)
    residual = window - basis @ coefficients
    fundamental_rms = math.hypot(coefficients[0], coefficients[1]) / math.sqrt(2.0)
    return residual, fundamental_rms


def _band_limited_rms(residual: np.ndarray, sample_rate: int) -> float:
    """RMS of ``residual`` restricted to 20 Hz - 20 kHz, via Parseval."""
    spectrum = np.fft.rfft(residual)
    frequencies = np.fft.rfftfreq(residual.size, d=1.0 / sample_rate)
    in_band = (frequencies >= BAND_LOW_HZ) & (frequencies <= BAND_HIGH_HZ)
    power = np.abs(spectrum[in_band]) ** 2
    # One-sided spectrum: interior bins carry both halves of the energy.
    doubled = 2.0 * float(np.sum(power))
    nyquist_bin = residual.size // 2 if residual.size % 2 == 0 else None
    if nyquist_bin is not None and in_band[nyquist_bin]:
        doubled -= float(power[-1])  # Nyquist bin has no mirror
    return math.sqrt(doubled) / residual.size


def measure_thd_plus_n(
    dut: DeviceUnderTest, sample_rate: int, level_dbfs: float
) -> dict[str, float]:
    """Drive ``dut`` with the AES17 stimulus and read its THD+N."""
    stimulus = synthesize_stimulus(sample_rate, level_dbfs).astype(SAMPLE_DTYPE)
    output = np.asarray(dut(stimulus, sample_rate), dtype=np.float64)
    if output.ndim != 1 or output.size != stimulus.size:
        raise ValueError("device under test changed the stimulus shape")

    window = _analysis_window(output, sample_rate)
    residual, fundamental_rms = _notch_fundamental(window, sample_rate)
    residual_rms = _band_limited_rms(residual, sample_rate)
    return {
        "fundamental_dbfs": _dbfs(fundamental_rms * math.sqrt(2.0)),
        "residual_rms_dbfs": _dbfs(residual_rms),
        "thd_plus_n_db": _dbfs(residual_rms / fundamental_rms),
    }


# --------------------------------------------------------------------- paths


def _gain_stage(stimulus: np.ndarray, sample_rate: int) -> np.ndarray:
    """A +3 dB stage into a -3 dB stage: two real float32 multiplies."""
    boosted = GainEffect(gain_db=3.0).process(stimulus, sample_rate)
    return GainEffect(gain_db=-3.0).process(boosted, sample_rate)


def _parametric_eq(stimulus: np.ndarray, sample_rate: int) -> np.ndarray:
    """An engaged peaking band well away from the fundamental."""
    eq = ParametricEQ(
        [EQBand(frequency=10_000.0, gain_db=2.0, q=1.0, type=FilterType.PEAKING)]
    )
    return eq.process(stimulus, sample_rate)


def _transparent_limiter(stimulus: np.ndarray, sample_rate: int) -> np.ndarray:
    """The true-peak limiter passing a tone that never reaches its ceiling."""
    return LimiterEffect(ceiling_db=-0.5).process(stimulus, sample_rate)


def _tpdf_quantizer(bit_depth: int, seed: int) -> DeviceUnderTest:
    def quantize(stimulus: np.ndarray, _sample_rate: int) -> np.ndarray:
        return quantize_with_tpdf(
            stimulus, bit_depth, rng=np.random.default_rng(seed)
        )

    return quantize


def _export_roundtrip(stimulus: np.ndarray, sample_rate: int) -> np.ndarray:
    """The full dithered PCM-24 export path: save_audio then load_audio."""
    with tempfile.TemporaryDirectory() as scratch:
        target = Path(scratch) / "aes17-export.wav"
        save_audio(
            target,
            AudioBuffer(stimulus[:, np.newaxis], sample_rate),
            subtype="PCM_24",
            dither=True,
        )
        return load_audio(target).buffer.data[:, 0]


#: Float paths carry limits an order of magnitude above their float32 rounding
#: floors (measured in the -130s to -150s); dithered paths must additionally
#: agree with the closed-form dither figure to THEORY_TOLERANCE_DB.
AES17_CASES: tuple[Aes17Case, ...] = (
    Aes17Case(
        "gain-stage-48k",
        "audio_studio.dsp.effects.GainEffect (+3 dB then -3 dB)",
        48_000,
        -1.0,
        -120.0,
        _gain_stage,
    ),
    Aes17Case(
        "eq-peaking-48k",
        "audio_studio.dsp.effects.ParametricEQ (peaking 10 kHz +2 dB Q1)",
        48_000,
        -1.0,
        -110.0,
        _parametric_eq,
    ),
    Aes17Case(
        "limiter-transparent-48k",
        "audio_studio.dsp.effects.LimiterEffect (ceiling -0.5 dBTP, untouched)",
        48_000,
        -6.0,
        -110.0,
        _transparent_limiter,
    ),
    Aes17Case(
        "pcm24-tpdf-48k",
        "audio_studio.core.loader.quantize_with_tpdf (24 bit)",
        48_000,
        -1.0,
        -138.0,
        _tpdf_quantizer(24, seed=997),
        expected_db=tpdf_expected_thd_plus_n_db(24, 48_000, -1.0),
    ),
    Aes17Case(
        "pcm16-tpdf-44k1",
        "audio_studio.core.loader.quantize_with_tpdf (16 bit)",
        44_100,
        -1.0,
        -91.0,
        _tpdf_quantizer(16, seed=1770),
        expected_db=tpdf_expected_thd_plus_n_db(16, 44_100, -1.0),
    ),
    Aes17Case(
        "export-roundtrip-pcm24-96k",
        "audio_studio.core.loader.save_audio/load_audio (PCM_24, dithered)",
        96_000,
        -1.0,
        -140.0,
        _export_roundtrip,
        expected_db=tpdf_expected_thd_plus_n_db(24, 96_000, -1.0),
    ),
)


def measure_case(case: Aes17Case) -> dict[str, Any]:
    """Run one case end to end and return its evidence row."""
    reading = measure_thd_plus_n(case.dut, case.sample_rate, case.stimulus_level_dbfs)
    checks = {
        "meets_limit": reading["thd_plus_n_db"] <= case.limit_db,
        "fundamental_at_stimulus_level": abs(
            reading["fundamental_dbfs"] - case.stimulus_level_dbfs
        )
        <= FUNDAMENTAL_TOLERANCE_DB,
    }
    if case.expected_db is not None:
        checks["matches_dither_theory"] = (
            abs(reading["thd_plus_n_db"] - case.expected_db) <= THEORY_TOLERANCE_DB
        )
    return {
        "case_id": case.case_id,
        "component": case.component,
        "sample_rate_hz": case.sample_rate,
        "stimulus_level_dbfs": case.stimulus_level_dbfs,
        "thd_plus_n_db": reading["thd_plus_n_db"],
        "thd_plus_n_limit_db": case.limit_db,
        "expected_thd_plus_n_db": case.expected_db,
        "fundamental_dbfs": reading["fundamental_dbfs"],
        "residual_rms_dbfs": reading["residual_rms_dbfs"],
        "checks": checks,
        "status": "pass" if all(checks.values()) else "fail",
    }


def measure_control() -> dict[str, Any]:
    """Prove the analyzer reads distortion when distortion is really there.

    The control clips the stimulus at 70 % of its own peak — gross, known
    distortion. An analyzer whose notch swallowed the residual, or whose band
    limit removed the harmonics, would read this as clean, so the report
    refuses to pass unless the control reads at least
    :data:`CONTROL_MINIMUM_THD_DB`.
    """

    def clipped(stimulus: np.ndarray, _sample_rate: int) -> np.ndarray:
        ceiling = 0.7 * float(np.max(np.abs(stimulus)))
        return np.clip(stimulus, -ceiling, ceiling)

    reading = measure_thd_plus_n(clipped, 48_000, -1.0)
    detected = reading["thd_plus_n_db"] >= CONTROL_MINIMUM_THD_DB
    return {
        "case_id": "analyzer-control-clipped",
        "component": "hard clip at 70 % of peak (deliberate distortion)",
        "thd_plus_n_db": reading["thd_plus_n_db"],
        "minimum_expected_db": CONTROL_MINIMUM_THD_DB,
        "distortion_detected": detected,
        "status": "pass" if detected else "fail",
    }


def measure_all(cases: Sequence[Aes17Case] = AES17_CASES) -> dict[str, Any]:
    """Measure every case plus the analyzer control; wrap into the report."""
    return build_report([measure_case(case) for case in cases], measure_control())


def build_report(
    results: Sequence[dict[str, Any]], control: dict[str, Any]
) -> dict[str, Any]:
    """Wrap already-measured rows in the report document."""
    if not results:
        raise ValueError("an AES17 report needs at least one measured case")
    passed = all(row["status"] == "pass" for row in results)
    return {
        "schema_version": 1,
        "artifact": "aes17-report",
        "checklist_item": "A8",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "standard": "AES17 THD+N method (997 Hz, notch, 20 Hz - 20 kHz bandwidth)",
        "scope": (
            "software signal paths only: gain stage, parametric EQ, transparent "
            "limiter, TPDF word-length reduction, dithered PCM export round "
            "trip. No converter or electrical measurement is claimed."
        ),
        "measurement": {
            "stimulus": "997 Hz raised-cosine-gated sine",
            "stimulus_total_seconds": TOTAL_SECONDS,
            "analysis_window_seconds": ANALYSIS_SECONDS,
            "notch": "least-squares 997 Hz sin/cos/DC fit subtracted (zero-width)",
            "bandwidth": "20 Hz - 20 kHz applied on the residual spectrum (Parseval)",
            "numpy_version": np.__version__,
        },
        "thresholds": {
            "theory_tolerance_db": THEORY_TOLERANCE_DB,
            "fundamental_tolerance_db": FUNDAMENTAL_TOLERANCE_DB,
            "control_minimum_thd_db": CONTROL_MINIMUM_THD_DB,
        },
        "cases": list(results),
        "analyzer_control": control,
        "worst_thd_plus_n_margin_db": min(
            row["thd_plus_n_limit_db"] - row["thd_plus_n_db"] for row in results
        ),
        "status": "pass" if passed and control["status"] == "pass" else "fail",
    }


def write_report(report: dict[str, Any], output: Path = DEFAULT_OUTPUT) -> Path:
    """Write ``report`` as stable, human-readable JSON."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"JSON output path (default: {DEFAULT_OUTPUT})",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    report = measure_all()
    write_report(report, args.output)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
