"""Benchmark sparse modal extraction for fixed-free spring chains."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from rich.console import Console
from rich.table import Table

from openfemlab.bench import ModalBenchmark, benchmark_modal_sizes, build_spring_chain
from openfemlab.bench.modal import modal_frequencies


def render_results(results: Sequence[ModalBenchmark]) -> None:
    """Print benchmark results as a terminal table."""
    table = Table(title="Spring-chain modal solve")
    table.add_column("DOF", justify="right")
    table.add_column("Modes", justify="right")
    table.add_column("Before (ms)", justify="right")
    table.add_column("After (ms)", justify="right")
    table.add_column("Speedup", justify="right")
    table.add_column("First mode (Hz)", justify="right")
    for result in results:
        table.add_row(
            str(result.dof),
            str(result.modes),
            f"{result.uncached_median_seconds * 1_000:.3f}",
            f"{result.median_seconds * 1_000:.3f}",
            f"{result.factorization_speedup:.2f}x",
            f"{result.first_frequency_hz:.6f}",
        )
    Console().print(table)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=5, help="timed solves per model")
    args = parser.parse_args()
    render_results(benchmark_modal_sizes(repeats=args.repeats))


if __name__ == "__main__":
    main()
