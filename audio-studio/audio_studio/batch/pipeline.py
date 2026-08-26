"""Offline batch processing of audio files.

A :class:`BatchJob` names the files to read (a glob pattern), the directory to
write into, and the operations to run on each file in between. Everything is
built from parts that already exist elsewhere in the package — decoding and
encoding go through :mod:`audio_studio.core.loader`, level changes through
:class:`~audio_studio.dsp.effects.gain.GainEffect`, fades through
:func:`~audio_studio.dsp.effects.fade.apply_fade` and loudness measurement
through :class:`~audio_studio.dsp.loudness.LoudnessMeter` — so a batch render
produces exactly what the editor would have produced one file at a time.

Examples
--------
>>> job = BatchJob(                                          # doctest: +SKIP
...     input_glob="stems/*.wav",
...     output_dir="out",
...     operations=(NormalizeLoudness(-16.0), Fade(fade_out_s=0.5)),
...     export_format="flac",
... )
>>> report = run_batch(job, log=print)                       # doctest: +SKIP
"""

from __future__ import annotations

import glob as _glob
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from ..core.loader import SUPPORTED_EXTENSIONS, AudioLoadError, load_audio, save_audio
from ..core.types import AudioBuffer
from ..dsp.effects.fade import FadeShape, apply_fade
from ..dsp.effects.gain import GainEffect
from ..dsp.loudness import LoudnessMeter

__all__ = [
    "ApplyGain",
    "BatchJob",
    "BatchReport",
    "Fade",
    "FileResult",
    "NormalizeLoudness",
    "Operation",
    "process_file",
    "run_batch",
]


class Operation(Protocol):
    """One offline transformation of a decoded buffer."""

    def apply(self, buffer: AudioBuffer) -> AudioBuffer:
        """Return a new buffer; the input is never modified."""
        ...

    def describe(self) -> str:
        """One-line human description, used by progress logging."""
        ...


@dataclass(frozen=True, slots=True)
class NormalizeLoudness:
    """Bring the BS.1770 integrated loudness onto ``target_lufs``.

    Loudness normalisation is a single global gain: the whole file is measured
    with :class:`~audio_studio.dsp.loudness.LoudnessMeter` and scaled by the
    difference to the target. With ``max_true_peak_dbtp`` set, the gain is
    additionally capped so the reconstructed (4x oversampled) peak stays under
    that ceiling — a file that cannot reach the target without clipping comes
    out quieter rather than clipped.

    Material the standard cannot gate — silence, or clips shorter than one
    400 ms gating block — is passed through untouched.
    """

    target_lufs: float
    max_true_peak_dbtp: float | None = None

    def apply(self, buffer: AudioBuffer) -> AudioBuffer:
        meter = LoudnessMeter(buffer.sample_rate)
        measured = meter.integrated(buffer.data, channels_last=True)
        if not math.isfinite(measured):
            return buffer

        gain_db = self.target_lufs - measured
        if self.max_true_peak_dbtp is not None:
            true_peak = meter.true_peak(buffer.data, channels_last=True)
            if math.isfinite(true_peak):
                gain_db = min(gain_db, self.max_true_peak_dbtp - true_peak)

        out = GainEffect(gain_db=gain_db, ramp_ms=0.0).process(
            buffer.data, buffer.sample_rate, channels_last=True
        )
        return AudioBuffer(out, buffer.sample_rate)

    def describe(self) -> str:
        text = f"normalize integrated loudness to {self.target_lufs:g} LUFS"
        if self.max_true_peak_dbtp is not None:
            text += f" (true peak <= {self.max_true_peak_dbtp:g} dBTP)"
        return text


@dataclass(frozen=True, slots=True)
class ApplyGain:
    """Apply a constant gain in dB."""

    gain_db: float

    def apply(self, buffer: AudioBuffer) -> AudioBuffer:
        out = GainEffect(gain_db=self.gain_db, ramp_ms=0.0).process(
            buffer.data, buffer.sample_rate, channels_last=True
        )
        return AudioBuffer(out, buffer.sample_rate)

    def describe(self) -> str:
        return f"apply gain {self.gain_db:+g} dB"


@dataclass(frozen=True, slots=True)
class Fade:
    """Fade the head and/or tail of each file."""

    fade_in_s: float = 0.0
    fade_out_s: float = 0.0
    shape: str = FadeShape.LINEAR.value

    def apply(self, buffer: AudioBuffer) -> AudioBuffer:
        out = apply_fade(
            buffer.data,
            buffer.sample_rate,
            fade_in_s=self.fade_in_s,
            fade_out_s=self.fade_out_s,
            shape=self.shape,
            channels_last=True,
        )
        return AudioBuffer(out, buffer.sample_rate)

    def describe(self) -> str:
        return (
            f"fade in {self.fade_in_s:g} s / out {self.fade_out_s:g} s "
            f"({FadeShape.coerce(self.shape).value})"
        )


def _normalise_extension(fmt: str) -> str:
    ext = fmt.strip().lower()
    if not ext.startswith("."):
        ext = "." + ext
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"unsupported export format {fmt!r}; known: "
            + ", ".join(e.lstrip(".") for e in SUPPORTED_EXTENSIONS)
        )
    return ext


@dataclass(slots=True)
class BatchJob:
    """Everything one batch render needs.

    Parameters
    ----------
    input_glob:
        Glob pattern selecting the input files, ``**`` supported. Matches with
        an extension :func:`~audio_studio.core.loader.load_audio` cannot read
        are ignored rather than failed.
    output_dir:
        Directory the processed files are written into (created on demand).
        File names are kept; only the extension changes with ``export_format``.
    operations:
        Applied in order to each decoded file.
    export_format:
        Target extension (``"flac"`` or ``".flac"``). ``None`` keeps each
        file's own container.
    subtype:
        libsndfile subtype override (e.g. ``"PCM_16"``, ``"FLOAT"``); ``None``
        picks the loader's per-container default.
    """

    input_glob: str
    output_dir: Path
    operations: tuple[Operation, ...] = ()
    export_format: str | None = None
    subtype: str | None = None

    def __post_init__(self) -> None:
        self.output_dir = Path(self.output_dir)
        self.operations = tuple(self.operations)
        if self.export_format is not None:
            self.export_format = _normalise_extension(self.export_format)

    def resolve_inputs(self) -> list[Path]:
        """Files matched by the glob that look decodable, sorted and unique."""
        matches = {
            Path(match).resolve()
            for match in _glob.glob(self.input_glob, recursive=True)
        }
        return sorted(
            path
            for path in matches
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        )

    def output_path_for(self, input_path: Path) -> Path:
        extension = self.export_format or input_path.suffix.lower()
        return self.output_dir / (input_path.stem + extension)


@dataclass(frozen=True, slots=True)
class FileResult:
    """Outcome of processing one input file."""

    input_path: Path
    output_path: Path | None = None
    error: str | None = None
    duration_s: float = 0.0

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass(frozen=True, slots=True)
class BatchReport:
    """Outcome of a whole batch run."""

    results: tuple[FileResult, ...] = field(default_factory=tuple)

    @property
    def succeeded(self) -> int:
        return sum(1 for result in self.results if result.ok)

    @property
    def failed(self) -> int:
        return len(self.results) - self.succeeded

    @property
    def all_ok(self) -> bool:
        return self.failed == 0

    def summary(self) -> str:
        return f"{self.succeeded} succeeded, {self.failed} failed"


def process_file(job: BatchJob, input_path: Path) -> FileResult:
    """Decode one file, run the job's operations and encode the result."""
    output_path = job.output_path_for(input_path)
    if output_path.resolve() == input_path.resolve():
        return FileResult(
            input_path, error=f"output {output_path} would overwrite the input"
        )
    try:
        buffer = load_audio(input_path).buffer
        for operation in job.operations:
            buffer = operation.apply(buffer)
        save_audio(output_path, buffer, subtype=job.subtype)
    except (AudioLoadError, ValueError) as exc:
        return FileResult(input_path, error=str(exc))
    return FileResult(input_path, output_path=output_path, duration_s=buffer.duration)


def run_batch(
    job: BatchJob, log: Callable[[str], None] | None = None
) -> BatchReport:
    """Process every file the job matches, logging progress as it goes.

    ``log`` receives one line per event (``print`` gives CLI-style progress on
    stdout); passing ``None`` runs silently. Per-file failures are recorded in
    the report rather than raised, so one unreadable file does not abort the
    rest of the batch.
    """
    emit = log if log is not None else (lambda message: None)
    inputs = job.resolve_inputs()
    emit(f"{len(inputs)} file(s) matched {job.input_glob!r}")
    for operation in job.operations:
        emit(f"  - {operation.describe()}")

    results: list[FileResult] = []
    for index, path in enumerate(inputs, start=1):
        result = process_file(job, path)
        if result.ok:
            emit(f"[{index}/{len(inputs)}] {path.name} -> {result.output_path}")
        else:
            emit(f"[{index}/{len(inputs)}] {path.name} FAILED: {result.error}")
        results.append(result)
    return BatchReport(tuple(results))
