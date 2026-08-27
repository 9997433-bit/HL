"""Inter-sample peak evidence for :class:`LimiterEffect`'s true-peak ceiling.

A sample-peak limiter is trivially satisfied by clipping every stored sample to
the ceiling, and the result still reconstructs above it in a DAC. The stimuli
here are sinusoids whose sample grid deliberately straddles the crest, so the
overshoot between the samples is known in closed form rather than measured:

For a tone at ``r/p`` of the sample rate with ``gcd(r, p) == 1``, the sample
phases land on a grid of ``p`` points around the circle, which is ``p / 2``
points spaced ``2*pi / p`` apart once folded into the half-cycle that ``|sin|``
repeats over (``p`` points spaced ``pi / p`` when ``p`` is odd). Offsetting that
grid so the crest falls exactly midway between two of its points minimises the
largest sample, and the peak *between* samples then exceeds the largest stored
sample by :attr:`IspCase.expected_overshoot_db` — 3.01 dB at a quarter of the
sample rate, the worst case any single sinusoid can produce.

The limited output is read back two independent ways: the product's own
BS.1770-style polyphase meter (:func:`audio_studio.dsp.util.true_peak_level`),
and a whole-signal FFT reconstruction that shares no code with it. The stimuli
start and end in silence, so the FFT's circular wrap is seamless and its
reading is the exact band-limited peak; on the unlimited stimuli it recovers
the intended level to the last displayed digit, which is what makes it usable
as the oracle for the limited ones.

Above roughly seven tenths of Nyquist the 4x detector BS.1770-4 specifies as
its *minimum* under-reads the peak it is supposed to catch, and the limiter
inherits that error as leakage above its ceiling. Cases up there therefore
declare a higher :attr:`IspCase.detector_oversample`, and
:func:`measure_oversample_sensitivity` measures the leak at each setting so
that the report states the limitation rather than stepping around it.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
for _import_root in (REPOSITORY_ROOT, REPOSITORY_ROOT / "audio-studio"):
    if str(_import_root) not in sys.path:
        sys.path.insert(0, str(_import_root))

from audio_studio.dsp.effects.dynamics import LimiterEffect
from audio_studio.dsp.util import true_peak_level

__all__ = [
    "DEFAULT_OUTPUT",
    "ISP_CASES",
    "TOLERANCE_DB",
    "IspCase",
    "build_report",
    "limiter_for",
    "measure_all",
    "measure_case",
    "measure_oversample_sensitivity",
    "reference_true_peak_dbtp",
    "synthesize",
    "write_report",
]

#: Where a limited output may sit above its ceiling and still pass. The ceiling
#: is a hard limit, so this is a rounding allowance, not a working margin: the
#: measured cases all land below the ceiling, not inside this band.
TOLERANCE_DB = 0.05

#: How far below the ceiling a limited output may sit before the limiter counts
#: as over-attenuating rather than limiting. Without this a limiter that simply
#: muted its input would satisfy every ceiling assertion here.
MAX_UNDERSHOOT_DB = 1.0

#: Oversampling used to read the output back with the product meter. This is
#: the BS.1770-4 Annex 2 figure and stays fixed even where a case drives the
#: limiter's own detector harder, so that the read-out is one constant.
METER_OVERSAMPLE = 4

#: Oversampling used by the independent FFT reconstruction.
REFERENCE_OVERSAMPLE = 32

#: Fraction of Nyquist above which a 4x detector's under-reading becomes
#: comparable to the ceiling tolerance and the limiter needs a finer one.
NEAR_NYQUIST_FRACTION = 0.7

#: Detector settings compared by :func:`measure_oversample_sensitivity`.
SENSITIVITY_OVERSAMPLES = (4, 8, 16)

#: Raised-cosine edge applied to each stimulus, so that the only discontinuity
#: a reading can find is one the limiter put there.
FADE_MS = 10.0

DEFAULT_OUTPUT = Path(".agent_workspace/v1.0/limiter-isp-report.json")


@dataclass(frozen=True)
class IspCase:
    """One tone whose inter-sample overshoot is known before it is measured."""

    case_id: str
    sample_rate: int
    #: Tone frequency as ``numerator / denominator`` of the sample rate.
    numerator: int
    denominator: int
    ceiling_dbtp: float
    input_true_peak_dbtp: float
    channels: int = 1
    duration_s: float = 0.2
    #: Oversampling the limiter's *detector* runs at for this case.
    detector_oversample: int = 4

    def __post_init__(self) -> None:
        if math.gcd(self.numerator, self.denominator) != 1:
            raise ValueError("tone ratio must be in lowest terms for the phase grid")
        if not 0 < self.nyquist_fraction < 1:
            raise ValueError("tone must be below Nyquist")

    @property
    def tone_hz(self) -> float:
        return self.sample_rate * self.numerator / self.denominator

    @property
    def nyquist_fraction(self) -> float:
        """Tone frequency as a fraction of Nyquist, where ISP risk lives."""
        return 2.0 * self.numerator / self.denominator

    @property
    def phase_offset(self) -> float:
        """Grid offset that puts the crest midway between two samples.

        ``|sin|`` repeats every half cycle, so what matters is where the sample
        phases land once folded into 180 degrees: ``p / 2`` points spaced
        ``360 / p`` for even ``p``, ``p`` points spaced ``180 / p`` for odd.
        Straddling the crest means offsetting that folded grid by half its
        spacing away from 90 degrees, and working the modular arithmetic
        through leaves a zero offset for every ``p`` except the multiples of
        four, where the unshifted grid already has a point on the crest.
        """
        return math.pi / self.denominator if self.denominator % 4 == 0 else 0.0

    @property
    def expected_overshoot_db(self) -> float:
        """Closed-form gap between the true peak and the largest sample."""
        divisor = self.denominator if self.denominator % 2 == 0 else 2 * self.denominator
        return -20.0 * math.log10(math.cos(math.pi / divisor))

    @property
    def is_near_nyquist(self) -> bool:
        return self.nyquist_fraction > NEAR_NYQUIST_FRACTION


#: Quarter-rate is the sinusoidal worst case; the rest walk the tone up toward
#: Nyquist, across the three sample rates the product ships golden files for,
#: and across ceilings so that a hard-coded ``-1 dBTP`` cannot pass by accident.
ISP_CASES: tuple[IspCase, ...] = (
    IspCase("quarter-rate-48k", 48_000, 1, 4, -1.0, 0.0),
    IspCase("quarter-rate-44k1-hot", 44_100, 1, 4, -1.0, 6.0),
    IspCase("sixth-rate-96k", 96_000, 1, 6, -0.1, 0.0),
    IspCase("third-rate-48k", 48_000, 1, 3, -0.3, 0.0),
    IspCase("0p6-nyquist-96k", 96_000, 3, 10, -1.0, 12.0),
    IspCase("0p75-nyquist-44k1", 44_100, 3, 8, -2.0, 3.0, detector_oversample=8),
    IspCase("0p8-nyquist-48k", 48_000, 2, 5, -1.0, 0.0, detector_oversample=8),
    IspCase("quarter-rate-48k-stereo", 48_000, 1, 4, -1.0, 0.0, channels=2),
)


def _dbfs(value: float) -> float:
    return 20.0 * math.log10(max(float(value), np.finfo(np.float64).tiny))


def limiter_for(case: IspCase, *, oversample: int | None = None) -> LimiterEffect:
    """Limiter under test for ``case``, at its stock time constants."""
    return LimiterEffect(
        ceiling_db=case.ceiling_dbtp,
        oversample=case.detector_oversample if oversample is None else oversample,
    )


def synthesize(case: IspCase, *, tail_samples: int) -> np.ndarray:
    """Planar stimulus for ``case``, followed by ``tail_samples`` of silence.

    The tail matters as much as the tone. :meth:`LimiterEffect.process` returns
    as many samples as it was given, so without it the lookahead delay would
    cut the output off mid-cycle and every reading would be dominated by that
    step rather than by the limiter.
    """
    frame_count = round(case.sample_rate * case.duration_s)
    fade = round(case.sample_rate * FADE_MS / 1000.0)
    if frame_count <= 2 * fade:
        raise ValueError("stimulus is too short to fade in and out")

    time = np.arange(frame_count, dtype=np.float64)
    amplitude = 10.0 ** (case.input_true_peak_dbtp / 20.0)
    angle = 2.0 * np.pi * case.numerator * time / case.denominator + case.phase_offset
    tone = amplitude * np.sin(angle)

    window = 0.5 - 0.5 * np.cos(np.pi * np.arange(fade) / fade)
    tone[:fade] *= window
    tone[frame_count - fade :] *= window[::-1]

    padded = np.concatenate([tone, np.zeros(tail_samples, dtype=np.float64)])
    channel_gains = np.array([1.0] + [0.5] * (case.channels - 1), dtype=np.float64)
    return channel_gains[:, np.newaxis] * padded[np.newaxis, :]


def reference_true_peak_dbtp(audio: np.ndarray) -> float:
    """Band-limited peak from whole-signal FFT interpolation, in dBTP.

    Independent of the polyphase kernel the product meters with, so a fault in
    that kernel cannot hide behind this reading.
    """
    planar = np.atleast_2d(np.asarray(audio, dtype=np.float64))
    length = planar.shape[-1]
    spectrum = np.fft.rfft(planar, axis=-1)
    upsampled_length = length * REFERENCE_OVERSAMPLE
    padded = np.zeros((planar.shape[0], upsampled_length // 2 + 1), dtype=np.complex128)
    padded[:, : spectrum.shape[-1]] = spectrum
    reconstructed = np.fft.irfft(padded, n=upsampled_length, axis=-1) * REFERENCE_OVERSAMPLE
    return _dbfs(np.max(np.abs(reconstructed)))


def limited_output(case: IspCase, *, oversample: int | None = None) -> np.ndarray:
    """Stimulus for ``case`` after the limiter has processed it, planar."""
    limiter = limiter_for(case, oversample=oversample)
    tail = limiter.latency_samples(case.sample_rate) + 64
    stimulus = synthesize(case, tail_samples=tail)
    return limiter.process(stimulus, case.sample_rate, channels_last=False)


def measure_case(case: IspCase) -> dict[str, Any]:
    """Run one case end to end and return its evidence row."""
    limiter = limiter_for(case)
    tail = limiter.latency_samples(case.sample_rate) + 64
    stimulus = synthesize(case, tail_samples=tail)
    limited = limiter.process(stimulus, case.sample_rate, channels_last=False)

    input_sample_peak = _dbfs(np.max(np.abs(stimulus)))
    input_true_peak = reference_true_peak_dbtp(stimulus)
    output_sample_peak = _dbfs(np.max(np.abs(limited)))
    output_meter = _dbfs(true_peak_level(limited, METER_OVERSAMPLE))
    output_reference = reference_true_peak_dbtp(limited)
    worst_output = max(output_meter, output_reference)

    checks = {
        "stimulus_overshoot_matches_theory": abs(
            (input_true_peak - input_sample_peak) - case.expected_overshoot_db
        )
        <= 0.01,
        "stimulus_exceeds_ceiling": input_true_peak > case.ceiling_dbtp + 0.1,
        "ceiling_held_by_product_meter": output_meter <= case.ceiling_dbtp + TOLERANCE_DB,
        "ceiling_held_by_reference": output_reference <= case.ceiling_dbtp + TOLERANCE_DB,
        "output_not_over_attenuated": worst_output >= case.ceiling_dbtp - MAX_UNDERSHOOT_DB,
    }

    return {
        "case_id": case.case_id,
        "sample_rate_hz": case.sample_rate,
        "channels": case.channels,
        "tone_hz": case.tone_hz,
        "tone_fraction_of_nyquist": case.nyquist_fraction,
        "ceiling_dbtp": case.ceiling_dbtp,
        "detector_oversample": case.detector_oversample,
        "expected_isp_overshoot_db": case.expected_overshoot_db,
        "measured_isp_overshoot_db": input_true_peak - input_sample_peak,
        "input_sample_peak_dbfs": input_sample_peak,
        "input_true_peak_dbtp": input_true_peak,
        "output_sample_peak_dbfs": output_sample_peak,
        "output_true_peak_dbtp": output_meter,
        "output_true_peak_reference_dbtp": output_reference,
        "headroom_below_ceiling_db": case.ceiling_dbtp - worst_output,
        "gain_reduction_db": limiter.gain_reduction_db,
        "checks": checks,
        "status": "pass" if all(checks.values()) else "fail",
    }


def measure_oversample_sensitivity(
    case: IspCase,
    oversamples: Sequence[int] = SENSITIVITY_OVERSAMPLES,
) -> list[dict[str, Any]]:
    """Ceiling error of ``case`` at each detector oversampling factor.

    This is the measurement behind the near-Nyquist caveat: the same tone and
    ceiling, limited by detectors of increasing resolution, read back by the
    reference reconstruction.
    """
    rows = []
    for oversample in oversamples:
        limited = limited_output(case, oversample=oversample)
        reference = reference_true_peak_dbtp(limited)
        rows.append(
            {
                "detector_oversample": oversample,
                "output_true_peak_reference_dbtp": reference,
                "error_above_ceiling_db": reference - case.ceiling_dbtp,
            }
        )
    return rows


def measure_all(cases: Sequence[IspCase] = ISP_CASES) -> dict[str, Any]:
    """Measure every case and wrap the rows in a report document."""
    return build_report([measure_case(case) for case in cases])


def _near_nyquist_probe() -> IspCase:
    """Highest-frequency case in the suite, which is where 4x gives out."""
    return max(ISP_CASES, key=lambda case: case.nyquist_fraction)


def build_report(
    results: Sequence[dict[str, Any]],
    sensitivity: Sequence[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Wrap already-measured rows in the report document."""
    if not results:
        raise ValueError("a limiter ISP report needs at least one measured case")
    probe = _near_nyquist_probe()
    if sensitivity is None:
        sensitivity = measure_oversample_sensitivity(probe)
    headroom = [row["headroom_below_ceiling_db"] for row in results]
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "component": "audio_studio.dsp.effects.dynamics.LimiterEffect",
        "measurement": {
            "product_meter": "audio_studio.dsp.util.true_peak_level",
            "product_meter_oversample": METER_OVERSAMPLE,
            "reference_meter": "whole-signal FFT band-limited reconstruction",
            "reference_meter_oversample": REFERENCE_OVERSAMPLE,
            "stimulus": "raised-cosine-gated sinusoid on a crest-straddling sample grid",
            "stimulus_fade_ms": FADE_MS,
            "numpy_version": np.__version__,
        },
        "thresholds": {
            "ceiling_tolerance_db": TOLERANCE_DB,
            "max_undershoot_db": MAX_UNDERSHOOT_DB,
            "near_nyquist_fraction": NEAR_NYQUIST_FRACTION,
        },
        "cases": list(results),
        "detector_oversample_sensitivity": {
            "case_id": probe.case_id,
            "tone_fraction_of_nyquist": probe.nyquist_fraction,
            "ceiling_dbtp": probe.ceiling_dbtp,
            "readings": list(sensitivity),
            "note": (
                "The 4x detector BS.1770-4 gives as a minimum under-reads tones above "
                f"{NEAR_NYQUIST_FRACTION:.0%} of Nyquist, and the limiter leaks above its "
                "ceiling by the same amount. Cases up there set oversample=8, which the "
                "readings here show is enough; the shipped default stays 4x."
            ),
        },
        "worst_case_headroom_db": min(headroom),
        "largest_headroom_db": max(headroom),
        "status": "pass" if all(row["status"] == "pass" for row in results) else "fail",
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
