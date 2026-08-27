"""``openfemlab bench`` — performance probes for modal extraction."""

from __future__ import annotations

import argparse
import time

from ..console import Reporter

NAME = "bench"
HELP = "run built-in performance benchmarks"


def add_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        NAME,
        help=HELP,
        description="Measure modal solver throughput on spring-chain models.",
    )
    bench_sub = parser.add_subparsers(dest="bench_command", metavar="SUBCOMMAND", required=True)
    modal_parser = bench_sub.add_parser("modal", help="benchmark sparse modal extraction")
    modal_parser.add_argument(
        "--sizes",
        default="100,1000,5000",
        help="comma-separated DOF counts (default: 100,1000,5000)",
    )
    modal_parser.add_argument(
        "--modes",
        type=int,
        default=6,
        help="modes to extract per size (default: 6)",
    )
    modal_parser.add_argument(
        "--repeats",
        type=int,
        default=3,
        help="timed repeats after warm-up (default: 3)",
    )
    modal_parser.set_defaults(func=_run_modal)
    parser.set_defaults(func=_dispatch)
    return parser


def _dispatch(args: argparse.Namespace, reporter: Reporter) -> int:
    return int(args.func(args, reporter))


def _parse_sizes(raw: str) -> list[int]:
    sizes = [int(part.strip()) for part in raw.split(",") if part.strip()]
    if not sizes:
        raise ValueError("at least one size is required")
    return sizes


def _run_modal(args: argparse.Namespace, reporter: Reporter) -> int:
    from openfemlab.bench import benchmark_modal_sizes

    try:
        sizes = _parse_sizes(args.sizes)
    except ValueError as exc:
        reporter.error(str(exc))
        return 1

    reporter.heading("Modal benchmark")
    started = time.perf_counter()
    results = benchmark_modal_sizes(sizes, repeats=args.repeats, modes=args.modes)
    elapsed = time.perf_counter() - started

    from ..console import Column

    reporter.table(
        (Column("DOF", justify="right"), Column("modes", justify="right"),
         Column("median s", justify="right"), Column("cached s", justify="right"),
         Column("speedup", justify="right"), Column("f1 Hz", justify="right")),
        [
            (
                str(row.dof),
                str(row.modes),
                f"{row.median_seconds:.4f}",
                f"{row.uncached_median_seconds:.4f}",
                f"{row.factorization_speedup:.2f}x",
                f"{row.first_frequency_hz:.3f}",
            )
            for row in results
        ],
    )
    reporter.success(f"Finished {len(results)} sizes in {elapsed:.2f} s")
    return 0
