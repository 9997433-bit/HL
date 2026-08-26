"""Command-line front end for :mod:`audio_studio.batch.pipeline`.

Run as a module or through the ``audio-studio-batch`` console script::

    python -m audio_studio.batch.cli --input "*.wav" --output out/ --lufs -16
    audio-studio-batch --input "takes/**/*.flac" --output out/ \\
        --gain-db -3 --fade-in 0.05 --fade-out 0.5 --format wav

Operations run in a fixed order on each file: ``--gain-db`` first, then
``--lufs`` loudness normalisation, then the fades — so the fade tails are the
last thing shaped and the normalisation measures the gain-adjusted signal.
Progress is printed to stdout, one line per file. The exit code is ``0`` when
every file rendered, ``1`` when at least one failed and ``2`` when nothing
matched the input pattern at all.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from ..dsp.effects.fade import FadeShape
from .pipeline import ApplyGain, BatchJob, Fade, NormalizeLoudness, Operation, run_batch

__all__ = ["build_parser", "main"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="audio-studio-batch",
        description="Batch-process audio files: gain, loudness normalisation, "
        "fades and format conversion.",
    )
    parser.add_argument(
        "--input",
        required=True,
        metavar="GLOB",
        help='glob pattern selecting the input files, e.g. "stems/*.wav" '
        "(quote it so the shell does not expand it)",
    )
    parser.add_argument(
        "--output",
        required=True,
        metavar="DIR",
        help="directory the processed files are written into (created on demand)",
    )
    parser.add_argument(
        "--lufs",
        type=float,
        default=None,
        metavar="LUFS",
        help="normalise each file's BS.1770 integrated loudness to this target, "
        "e.g. -16",
    )
    parser.add_argument(
        "--true-peak",
        type=float,
        default=None,
        metavar="DBTP",
        help="with --lufs, cap the gain so the true peak stays under this "
        "ceiling (e.g. -1.0)",
    )
    parser.add_argument(
        "--gain-db",
        type=float,
        default=None,
        metavar="DB",
        help="constant gain applied before any normalisation",
    )
    parser.add_argument(
        "--fade-in",
        type=float,
        default=0.0,
        metavar="SECONDS",
        help="fade-in length at the head of each file",
    )
    parser.add_argument(
        "--fade-out",
        type=float,
        default=0.0,
        metavar="SECONDS",
        help="fade-out length at the tail of each file",
    )
    parser.add_argument(
        "--fade-shape",
        default=FadeShape.LINEAR.value,
        choices=[shape.value for shape in FadeShape],
        help="fade curve (default: %(default)s)",
    )
    parser.add_argument(
        "--format",
        default=None,
        metavar="EXT",
        help="re-encode into this container, e.g. wav or flac "
        "(default: keep each file's own)",
    )
    parser.add_argument(
        "--subtype",
        default=None,
        metavar="SUBTYPE",
        help="libsndfile encoding subtype, e.g. PCM_16, PCM_24 or FLOAT "
        "(default: per-container choice)",
    )
    return parser


def _operations(args: argparse.Namespace) -> tuple[Operation, ...]:
    operations: list[Operation] = []
    if args.gain_db is not None:
        operations.append(ApplyGain(args.gain_db))
    if args.lufs is not None:
        operations.append(NormalizeLoudness(args.lufs, args.true_peak))
    if args.fade_in > 0.0 or args.fade_out > 0.0:
        operations.append(Fade(args.fade_in, args.fade_out, args.fade_shape))
    return tuple(operations)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        job = BatchJob(
            input_glob=args.input,
            output_dir=args.output,
            operations=_operations(args),
            export_format=args.format,
            subtype=args.subtype,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not job.resolve_inputs():
        print(f"error: no supported audio files matched {args.input!r}", file=sys.stderr)
        return 2

    report = run_batch(job, log=print)
    print(report.summary())
    return 0 if report.all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
