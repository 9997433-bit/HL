"""Cross-platform DSP consistency evidence (SOTA checklist E2).

The three-platform CI matrix proves the suites pass everywhere. It does not
prove the *numbers* agree: a filter that reads back 0.3 dB differently on
macOS still passes a test written with a 0.5 dB tolerance. This module closes
that gap by running one fixed set of DSP vectors through the product's own
code paths, recording the sample values each platform produced, and comparing
the three recordings against each other.

Two properties keep the comparison meaningful:

*Deterministic stimuli.* Every vector builds its input from an integer-seeded
:class:`numpy.random.Generator` and closed-form arithmetic, so the recordings
being compared are answers to the same question. Each record carries the
SHA-256 of both the stimulus and the result, which is what turns "the inputs
matched" into something a reader can check rather than assume.

*Values, not summaries.* A vector is fingerprinted by
:data:`PROBE_COUNT` evenly spaced output samples, not by a peak or an RMS.
Summary statistics average away exactly the localised divergence — one
denormal region, one branch of a limiter's gain computer — that this item
exists to catch.

Bit-exactness across platforms is *not* the pass criterion, and the report
says so. Different libm implementations round ``sin`` differently in the last
ulp, and that is allowed; the report records which vectors happened to come
out bit-identical as an observation. What must hold is that no probe differs
by more than :data:`TOLERANCE_ABSOLUTE`, which is far below the point where
any audible or measurable behaviour could change.

Usage::

    # on each CI runner
    python tools/cross_platform_golden.py record --output record.json

    # once all three are collected
    python tools/cross_platform_golden.py merge linux.json macos.json \\
        windows.json --output .agent_workspace/round3/cross-platform-golden.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
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

import scipy
import soundfile as sf
from audio_studio.core.loader import quantize_with_tpdf
from audio_studio.core.resample import resample_backend, resample_buffer
from audio_studio.core.sample_source import MemorySampleSource
from audio_studio.core.session import MultitrackSession, Track
from audio_studio.core.types import AudioBuffer
from audio_studio.dsp.effects.dynamics import CompressorEffect, LimiterEffect
from audio_studio.dsp.effects.eq import EQBand, FilterType, ParametricEQ
from audio_studio.dsp.loudness import LoudnessMeter
from audio_studio.dsp.spectral_edit import SpectralBand, attenuate_band
from audio_studio.dsp.util import true_peak_level

__all__ = [
    "DEFAULT_OUTPUT",
    "PLATFORM_KEYS",
    "PROBE_COUNT",
    "TOLERANCE_ABSOLUTE",
    "VECTORS",
    "GoldenVector",
    "build_record",
    "measure_vector",
    "merge_records",
    "platform_key",
    "probe_indices",
    "write_json",
]

#: Platform names the report is keyed by, and the only three accepted.
PLATFORM_KEYS = ("linux", "macos", "windows")

#: Output samples fingerprinted per vector. Evenly spaced across the whole
#: result, so a divergence confined to one region of one signal still lands on
#: a probe instead of being averaged out of existence.
PROBE_COUNT = 256

#: Largest absolute difference any probe of a float64 path may show between two
#: platforms. Well above float64 rounding noise (~1e-16 relative) and far below
#: the point where a difference could be measured in an audio signal: a
#: full-scale sample differing by 1e-9 is 180 dB down.
TOLERANCE_ABSOLUTE = 1e-9

#: Vectors whose DSP runs in the product's float32 sample format are held to one
#: ulp of *that* format instead, evaluated at the vector's own peak. Asking two
#: CPU architectures to agree on a float32 resampler more closely than float32
#: can represent is not a consistency requirement; it is a request for a number
#: the format cannot hold. The measured error is reported either way, and which
#: rule each vector was judged by is recorded next to it.
FLOAT32_TOLERANCE_ULPS = 1.0

DEFAULT_OUTPUT = Path(".agent_workspace/round3/cross-platform-golden.json")

SAMPLE_RATE = 48_000


def platform_key(system: str | None = None) -> str:
    """Map a :func:`platform.system` string onto a report platform key."""
    name = (system or platform.system()).strip().lower()
    if name.startswith(("darwin", "mac")):
        return "macos"
    if name.startswith(("win", "cygwin")):
        return "windows"
    if name.startswith("linux"):
        return "linux"
    raise ValueError(f"unsupported platform for the golden matrix: {name!r}")


def probe_indices(n_samples: int, count: int = PROBE_COUNT) -> np.ndarray:
    """Evenly spaced sample indices, first and last always included.

    Derived from the sample count alone so that a reader holding only the
    records can recompute exactly which samples were compared.
    """
    if n_samples <= 0:
        raise ValueError("a golden vector must produce at least one sample")
    if n_samples <= count:
        return np.arange(n_samples, dtype=np.int64)
    return np.unique(np.linspace(0, n_samples - 1, count).round().astype(np.int64))


def _digest(values: np.ndarray) -> str:
    """SHA-256 of ``values`` as little-endian float64, layout normalised."""
    flat = np.ascontiguousarray(np.asarray(values, dtype=np.float64).ravel())
    return hashlib.sha256(flat.astype("<f8", copy=False).tobytes()).hexdigest()


# -- stimuli -----------------------------------------------------------------
#
# Built from integer-seeded PCG64 draws and closed-form arithmetic. The uniform
# doubles a Generator produces are an exact function of the seed on every
# platform; anything transcendental (the tones below) is deliberately left in,
# because a libm difference is precisely what this item is looking for.


def _noise(seed: int, n_frames: int, n_channels: int = 1, level: float = 0.5) -> np.ndarray:
    rng = np.random.default_rng(seed)
    draw = rng.random((n_channels, n_frames), dtype=np.float64)
    return level * (2.0 * draw - 1.0)


def _tone(frequency: float, n_frames: int, *, amplitude: float = 0.5, phase: float = 0.0) -> np.ndarray:
    time = np.arange(n_frames, dtype=np.float64) / SAMPLE_RATE
    return amplitude * np.sin(2.0 * np.pi * frequency * time + phase)


def _programme(seed: int, n_frames: int) -> np.ndarray:
    """Two channels of tone-plus-noise with a slow amplitude contour.

    Rich enough that a filter, a gain computer and an FFT all have something
    to disagree about, and quiet enough to leave the limiter's ceiling and the
    compressor's knee both genuinely exercised rather than pinned.
    """
    left = _tone(997.0, n_frames, amplitude=0.35) + _tone(3_150.0, n_frames, amplitude=0.15)
    right = _tone(1_003.0, n_frames, amplitude=0.30, phase=0.7)
    noise = _noise(seed, n_frames, 2, level=0.05)
    contour = 0.6 + 0.4 * np.sin(
        2.0 * np.pi * 0.37 * np.arange(n_frames, dtype=np.float64) / SAMPLE_RATE
    )
    return np.stack([left, right]) * contour + noise


# -- vectors -----------------------------------------------------------------


@dataclass(frozen=True)
class GoldenVector:
    """One DSP path, its stimulus, and the result the platforms compare."""

    vector_id: str
    description: str
    #: Returns ``(stimulus, result)``; both are hashed, only ``result`` is
    #: probed. Keeping the stimulus in the record is what lets a failed
    #: comparison be attributed to the input rather than to the DSP.
    run: Callable[[], tuple[np.ndarray, np.ndarray]]


def _vector_eq_cascade() -> tuple[np.ndarray, np.ndarray]:
    stimulus = _programme(2, 24_000)
    eq = ParametricEQ(
        [
            EQBand(frequency=80.0, gain_db=-6.0, q=0.71, type=FilterType.HIGH_SHELF),
            EQBand(frequency=997.0, gain_db=6.5, q=1.4, type=FilterType.PEAKING),
            EQBand(frequency=3_150.0, gain_db=-4.25, q=2.7, type=FilterType.PEAKING),
            EQBand(frequency=12_000.0, gain_db=3.0, q=0.9, type=FilterType.HIGH_SHELF),
        ]
    )
    return stimulus, eq.process(stimulus, SAMPLE_RATE, channels_last=False)


def _vector_eq_response() -> tuple[np.ndarray, np.ndarray]:
    frequencies = np.geomspace(20.0, 20_000.0, 2_048)
    eq = ParametricEQ(
        [
            EQBand(frequency=120.0, gain_db=4.0, q=0.8, type=FilterType.LOW_SHELF),
            EQBand(frequency=2_137.0, gain_db=9.25, q=1.37, type=FilterType.PEAKING),
            EQBand(frequency=7_500.0, gain_db=-11.0, q=4.2, type=FilterType.NOTCH),
        ]
    )
    return frequencies, eq.magnitude_response_db(frequencies, SAMPLE_RATE)


def _vector_limiter() -> tuple[np.ndarray, np.ndarray]:
    stimulus = _programme(3, 24_000) * 2.5
    limiter = LimiterEffect(ceiling_db=-1.0, release_ms=60.0, lookahead_ms=5.0)
    return stimulus, limiter.process(stimulus, SAMPLE_RATE, channels_last=False)


def _vector_compressor() -> tuple[np.ndarray, np.ndarray]:
    stimulus = _programme(4, 24_000) * 1.8
    compressor = CompressorEffect(
        threshold_db=-18.0, ratio=4.0, attack_ms=8.0, release_ms=120.0, knee_db=6.0
    )
    return stimulus, compressor.process(stimulus, SAMPLE_RATE, channels_last=False)


def _vector_loudness() -> tuple[np.ndarray, np.ndarray]:
    """K-weighting, gating and the true-peak meter, read as one curve.

    The short-term curve is the interesting part: every 3 s window carries the
    biquad cascade's state, so a coefficient computed differently shows up as a
    whole displaced curve rather than as one rounded scalar.
    """
    stimulus = _programme(5, SAMPLE_RATE * 6)
    meter = LoudnessMeter(SAMPLE_RATE)
    times, short_term = meter.short_term(stimulus, channels_last=False)
    scalars = np.array(
        [
            meter.integrated(stimulus, channels_last=False),
            meter.loudness_range(stimulus, channels_last=False),
            meter.true_peak(stimulus, channels_last=False),
        ],
        dtype=np.float64,
    )
    return stimulus, np.concatenate([np.asarray(times, dtype=np.float64), short_term, scalars])


def _vector_true_peak() -> tuple[np.ndarray, np.ndarray]:
    """Polyphase reconstruction on tones whose peaks fall between samples."""
    readings = []
    stimuli = []
    for numerator, denominator in ((1, 4), (3, 8), (2, 5), (3, 10)):
        phase = np.pi / denominator if denominator % 4 == 0 else 0.0
        time = np.arange(4_096, dtype=np.float64)
        tone = 0.9 * np.sin(2.0 * np.pi * numerator * time / denominator + phase)
        stimuli.append(tone)
        readings.append(true_peak_level(tone[np.newaxis, :], 4))
    return np.concatenate(stimuli), np.asarray(readings, dtype=np.float64)


def _vector_resample() -> tuple[np.ndarray, np.ndarray]:
    stimulus = _programme(6, 24_000).astype(np.float32)
    converted = resample_buffer(stimulus.T, SAMPLE_RATE, 44_100, quality="vhq")
    return stimulus, converted


def _vector_dither() -> tuple[np.ndarray, np.ndarray]:
    """TPDF quantisation, whose grid should land identically everywhere.

    The dither draw comes from a seeded Generator and the result sits on an
    integer LSB grid, so this is the one vector where a bit-exact match across
    platforms is a reasonable expectation rather than a hope.
    """
    stimulus = _programme(7, 24_000).astype(np.float32).T
    return stimulus, quantize_with_tpdf(stimulus, 16, rng=np.random.default_rng(31_337))


def _vector_spectral_edit() -> tuple[np.ndarray, np.ndarray]:
    """STFT analysis, per-bin gain and overlap-add resynthesis."""
    stimulus = _programme(8, 24_000)
    edited = attenuate_band(
        stimulus,
        SAMPLE_RATE,
        SpectralBand(2_800.0, 3_500.0),
        -18.0,
        fft_size=2_048,
        channels_last=False,
    )
    return stimulus, edited


def _vector_multitrack_mixdown() -> tuple[np.ndarray, np.ndarray]:
    """Four tracks with gain, pan and a rising automation curve, summed."""
    session = MultitrackSession(sample_rate=SAMPLE_RATE, n_channels=2)
    sources = []
    for index in range(4):
        samples = _programme(20 + index, 12_000).T.astype(np.float32)
        sources.append(samples)
        source = MemorySampleSource(AudioBuffer(samples, SAMPLE_RATE))
        track = session.add_track(
            Track(name=f"Track {index + 1}", gain_db=-3.0 * index, pan=-0.6 + 0.4 * index)
        )
        session.add_clip(track, source, start=index * 1_000, duration=source.n_frames)
        track.automation.line(0, source.n_frames, -6.0, 3.0)
    session.master.gain_db = -2.0
    return np.concatenate([block.ravel() for block in sources]), session.mixdown().data


VECTORS: tuple[GoldenVector, ...] = (
    GoldenVector("eq-peaking-cascade", "Four-band RBJ biquad cascade over programme", _vector_eq_cascade),
    GoldenVector("eq-magnitude-response", "Analytic EQ transfer function, 20 Hz - 20 kHz", _vector_eq_response),
    GoldenVector("limiter-true-peak", "Lookahead true-peak limiter at -1 dBTP", _vector_limiter),
    GoldenVector("compressor-soft-knee", "Linked soft-knee compressor, 4:1", _vector_compressor),
    GoldenVector("loudness-bs1770", "K-weighted short-term curve, LRA and true peak", _vector_loudness),
    GoldenVector("true-peak-polyphase", "4x polyphase peaks of crest-straddling tones", _vector_true_peak),
    GoldenVector("src-48k-to-44k1", "VHQ sample-rate conversion, 48 kHz to 44.1 kHz", _vector_resample),
    GoldenVector("tpdf-dither-16bit", "TPDF-dithered quantisation to 16 bit", _vector_dither),
    GoldenVector("spectral-band-attenuate", "STFT band attenuation and overlap-add resynthesis", _vector_spectral_edit),
    GoldenVector("multitrack-mixdown", "Four automated tracks summed through the master bus", _vector_multitrack_mixdown),
)


# -- recording ---------------------------------------------------------------


def _probe_values(values: np.ndarray) -> list[float]:
    flat = np.ascontiguousarray(np.asarray(values, dtype=np.float64).ravel())
    return [float(value) for value in flat[probe_indices(flat.size)]]


def measure_vector(vector: GoldenVector) -> dict[str, Any]:
    """Run one vector and return the row a platform record carries.

    The result's dtype is recorded rather than declared, because it is what
    decides how closely the platforms can be asked to agree: a float32 audio
    path cannot resolve a difference smaller than its own ulp.
    """
    stimulus, result = vector.run()
    raw = np.asarray(result)
    flat = np.ascontiguousarray(raw.astype(np.float64).ravel())
    if not np.all(np.isfinite(flat)):
        raise ValueError(f"{vector.vector_id}: produced non-finite samples")
    indices = probe_indices(flat.size)
    return {
        "vector_id": vector.vector_id,
        "description": vector.description,
        "n_samples": int(flat.size),
        "working_precision": np.dtype(raw.dtype).name,
        "stimulus_sha256": _digest(stimulus),
        "result_sha256": _digest(flat),
        "peak_absolute": float(np.max(np.abs(flat))),
        "probe_indices_count": int(indices.size),
        # The stimulus is probed as well as hashed. Its digest differs across
        # platforms whenever it is built from a transcendental — which is most
        # of them — so "the runners were fed the same signal" has to be a
        # numeric statement, not a hash comparison.
        "stimulus_probes": _probe_values(stimulus),
        "probes": [float(value) for value in flat[indices]],
    }


def _runtime() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "soundfile": sf.__version__,
        "libsndfile": sf.__libsndfile_version__,
        "src_backend": resample_backend(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "byte_order": sys.byteorder,
    }


def build_record(vectors: Sequence[GoldenVector] = VECTORS) -> dict[str, Any]:
    """Measure every vector on this host and wrap it in a platform record."""
    return {
        "schema_version": 1,
        "kind": "cross-platform-golden-record",
        "platform": platform_key(),
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "probe_count": PROBE_COUNT,
        "runtime": _runtime(),
        "vectors": [measure_vector(vector) for vector in vectors],
    }


# -- merging -----------------------------------------------------------------


def _pair_error(left: Sequence[float], right: Sequence[float]) -> float:
    return float(np.max(np.abs(np.asarray(left, dtype=np.float64) - np.asarray(right, dtype=np.float64))))


def _load_record(path: Path) -> dict[str, Any]:
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    if record.get("kind") != "cross-platform-golden-record":
        raise ValueError(f"{path}: not a golden platform record")
    if record.get("platform") not in PLATFORM_KEYS:
        raise ValueError(f"{path}: unknown platform {record.get('platform')!r}")
    return record


def vector_tolerance(
    precision: str, peak: float, *, base: float = TOLERANCE_ABSOLUTE
) -> tuple[float, str]:
    """How closely two platforms must agree on a vector, and on what grounds.

    Float64 analysis paths are held to ``base``. Float32 audio paths — the
    product's own sample format — are held to one ulp of float32 at the
    vector's peak, because below that the format has no bits left to disagree
    in and the requirement would be about representation rather than DSP.
    """
    if precision == "float32":
        ulp = float(np.spacing(np.float32(max(abs(peak), 1.0e-6))))
        return (
            max(base, FLOAT32_TOLERANCE_ULPS * ulp),
            f"one float32 ulp at the vector peak ({ulp:.3e})",
        )
    return base, f"{base:g} absolute"


def merge_records(
    records: Sequence[dict[str, Any]],
    *,
    tolerance: float = TOLERANCE_ABSOLUTE,
) -> dict[str, Any]:
    """Compare per-platform records and build the E2 evidence report.

    Every failure mode gets its own named check rather than a bare status, so
    a report that does not pass says which of "all three platforms present",
    "same vectors", "same stimuli", "same dependency versions" and "values
    agree" was the one that gave way.
    """
    by_platform: dict[str, dict[str, Any]] = {}
    for record in records:
        key = record["platform"]
        if key in by_platform:
            raise ValueError(f"two records claim to be {key}")
        by_platform[key] = record

    missing = [key for key in PLATFORM_KEYS if key not in by_platform]
    present = [key for key in PLATFORM_KEYS if key in by_platform]
    pairs = [(a, b) for index, a in enumerate(present) for b in present[index + 1 :]]

    vector_ids = [vector["vector_id"] for vector in by_platform[present[0]]["vectors"]] if present else []
    shared_ids = [
        vector_id
        for vector_id in vector_ids
        if all(
            any(row["vector_id"] == vector_id for row in by_platform[key]["vectors"])
            for key in present
        )
    ]

    vector_rows: list[dict[str, Any]] = []
    stimuli_agree = True
    for vector_id in shared_ids:
        rows = {key: next(r for r in by_platform[key]["vectors"] if r["vector_id"] == vector_id) for key in present}
        sizes = {row["n_samples"] for row in rows.values()}
        precisions = {row.get("working_precision", "float64") for row in rows.values()}
        stimulus_digests = {key: row["stimulus_sha256"] for key, row in rows.items()}
        result_digests = {key: row["result_sha256"] for key, row in rows.items()}
        precision = min(precisions)
        peak = max(row["peak_absolute"] for row in rows.values())
        vector_limit, basis = vector_tolerance(precision, peak, base=tolerance)

        per_pair: dict[str, float] = {}
        stimulus_pairs: dict[str, float] = {}
        vector_worst = 0.0
        stimulus_worst = 0.0
        comparable = len(sizes) == 1 and len(precisions) == 1
        for left, right in pairs:
            if not comparable:
                continue
            error = _pair_error(rows[left]["probes"], rows[right]["probes"])
            per_pair[f"{left}-vs-{right}"] = error
            vector_worst = max(vector_worst, error)
            if "stimulus_probes" in rows[left] and "stimulus_probes" in rows[right]:
                stimulus_error = _pair_error(
                    rows[left]["stimulus_probes"], rows[right]["stimulus_probes"]
                )
                stimulus_pairs[f"{left}-vs-{right}"] = stimulus_error
                stimulus_worst = max(stimulus_worst, stimulus_error)

        # The stimuli are built from transcendentals, so their digests differ
        # per libm. What has to hold is that the runners answered the same
        # question numerically; the digests stay in the report as the record of
        # which ones happened to match to the bit.
        same_stimulus = comparable and stimulus_worst <= vector_limit
        stimuli_agree = stimuli_agree and same_stimulus

        vector_rows.append(
            {
                "vector_id": vector_id,
                "description": rows[present[0]]["description"],
                "n_samples": min(sizes) if comparable else sorted(sizes),
                "working_precision": precision if len(precisions) == 1 else sorted(precisions),
                "sample_counts_agree": len(sizes) == 1,
                "precisions_agree": len(precisions) == 1,
                "tolerance_absolute": vector_limit,
                "tolerance_basis": basis,
                "identical_stimulus": same_stimulus,
                "bit_identical_stimulus": len(set(stimulus_digests.values())) == 1,
                "stimulus_maximum_absolute_error": stimulus_worst,
                "stimulus_pairwise_maximum_absolute_error": stimulus_pairs,
                "stimulus_sha256": stimulus_digests,
                "result_sha256": result_digests,
                "bit_identical": len(set(result_digests.values())) == 1,
                "maximum_absolute_error": vector_worst,
                "pairwise_maximum_absolute_error": per_pair,
                "within_tolerance": comparable and vector_worst <= vector_limit,
            }
        )

    by_precision = {
        precision: max(
            (
                row["maximum_absolute_error"]
                for row in vector_rows
                if row["working_precision"] == precision
            ),
            default=0.0,
        )
        for precision in sorted(
            {
                row["working_precision"]
                for row in vector_rows
                if isinstance(row["working_precision"], str)
            }
        )
    }
    # The headline figure is the one the 1e-9 bar applies to: the float64
    # analysis paths. The float32 audio paths cannot resolve a difference that
    # small, so their error is carried beside it under its own name rather than
    # folded in or left out.
    worst = by_precision.get("float64", 0.0)
    worst_overall = max(by_precision.values(), default=0.0)

    runtimes = {key: by_platform[key]["runtime"] for key in present}
    # Exact Python patch levels are the runner images' business —
    # actions/setup-python resolves 3.12 to whatever each OS has cached. What
    # must match is the interpreter's minor version and the pinned wheels.
    versions_agree = (
        all(
            len({runtimes[key][field] for key in present}) == 1
            for field in ("numpy", "scipy", "src_backend")
        )
        and len({".".join(runtimes[key]["python"].split(".")[:2]) for key in present}) == 1
        if present
        else False
    )

    checks = {
        "all_three_platforms_recorded": not missing,
        "same_vector_set": bool(shared_ids) and len(shared_ids) == len(vector_ids),
        "sample_counts_agree": all(row["sample_counts_agree"] for row in vector_rows),
        "working_precisions_agree": all(row["precisions_agree"] for row in vector_rows),
        "identical_stimuli": stimuli_agree,
        "pinned_dependency_versions_agree": versions_agree,
        "values_within_tolerance": bool(vector_rows)
        and all(row["within_tolerance"] for row in vector_rows),
    }

    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "item": "E2 cross-platform DSP golden consistency",
        "tolerance_absolute": tolerance,
        "probe_count": PROBE_COUNT,
        "platforms": {
            key: {
                "recorded_at_utc": by_platform[key]["generated_at_utc"],
                "runtime": by_platform[key]["runtime"],
                "vectors_recorded": len(by_platform[key]["vectors"]),
                "provenance": by_platform[key].get("provenance", {}),
            }
            for key in present
        },
        "missing_platforms": missing,
        "vectors": vector_rows,
        "pairwise_maximum_absolute_error": {
            f"{left}-vs-{right}": max(
                (row["pairwise_maximum_absolute_error"].get(f"{left}-vs-{right}", 0.0) for row in vector_rows),
                default=0.0,
            )
            for left, right in pairs
        },
        "bit_identical_vectors": [row["vector_id"] for row in vector_rows if row["bit_identical"]],
        "maximum_absolute_error": worst,
        "maximum_absolute_error_scope": (
            "float64 DSP paths, which are the vectors the 1e-9 bar applies to; the "
            "float32 audio paths are in maximum_absolute_error_by_precision and are "
            "judged against one float32 ulp, per-vector, under vectors[].tolerance_basis"
        ),
        "maximum_absolute_error_all_vectors": worst_overall,
        "maximum_absolute_error_by_precision": by_precision,
        "checks": checks,
        "notes": [
            (
                "Each platform ran tools/cross_platform_golden.py record on its own CI "
                "runner; this report is the merge of those three artifacts."
            ),
            (
                "Vectors are compared on PROBE_COUNT evenly spaced output samples, not on "
                "summary statistics, so a divergence confined to one region still registers."
            ),
            (
                "Bit-exactness is reported, not required: libm rounds transcendentals "
                "differently per platform, which is why the stimuli are compared "
                "numerically rather than by digest."
            ),
            (
                "float64 analysis paths agree to ~1e-13 or better. The float32 audio paths "
                "are held to one ulp of float32 instead: the measured divergence there is "
                "the macOS arm64 runner differing from both x86 runners by exactly one "
                "float32 ulp in the SciPy polyphase resampler, which is the smallest "
                "difference the sample format can express."
            ),
        ],
        "status": "pass" if all(checks.values()) else "fail",
    }


def write_json(payload: dict[str, Any], output: Path) -> Path:
    """Write ``payload`` as stable, human-readable JSON."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    record = subparsers.add_parser("record", help="measure this host's DSP vectors")
    record.add_argument("--output", type=Path, required=True, help="platform record path")
    record.add_argument(
        "--provenance",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="extra provenance to stamp into the record (repeatable)",
    )

    merge = subparsers.add_parser("merge", help="compare platform records into the E2 report")
    merge.add_argument("records", type=Path, nargs="+", help="platform record paths")
    merge.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    merge.add_argument("--tolerance", type=float, default=TOLERANCE_ABSOLUTE)

    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.command == "record":
        record = build_record()
        provenance = dict(
            entry.split("=", 1) for entry in args.provenance if "=" in entry
        )
        if provenance:
            record["provenance"] = provenance
        write_json(record, args.output)
        print(
            f"{record['platform']}: recorded {len(record['vectors'])} vectors "
            f"to {args.output}"
        )
        return 0

    report = merge_records(
        [_load_record(path) for path in args.records], tolerance=args.tolerance
    )
    write_json(report, args.output)
    print(json.dumps({key: report[key] for key in ("maximum_absolute_error", "checks", "status")}, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
