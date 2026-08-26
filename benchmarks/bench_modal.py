"""Benchmark sparse modal extraction for fixed-free spring chains."""

from __future__ import annotations

import argparse
import statistics
import time
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from rich.console import Console
from rich.table import Table
from scipy.sparse import csr_matrix, diags
from scipy.sparse.linalg import eigsh

from openfemlab.solver.modal import ModalSolver


@dataclass(frozen=True)
class ModalBenchmark:
    """Timing summary for one spring-chain size."""

    dof: int
    modes: int
    minimum_seconds: float
    median_seconds: float
    uncached_median_seconds: float
    factorization_speedup: float
    first_frequency_hz: float


def build_spring_chain(
    dof: int,
    *,
    stiffness: float = 1.0e6,
    mass: float = 1.0,
) -> tuple[csr_matrix, csr_matrix]:
    """Build stiffness and mass matrices for a fixed-free uniform chain."""
    if dof < 2:
        raise ValueError("dof must be at least 2")
    if stiffness <= 0.0 or mass <= 0.0:
        raise ValueError("stiffness and mass must be positive")

    diagonal = np.full(dof, 2.0)
    diagonal[-1] = 1.0
    stiffness_matrix = stiffness * diags(
        (-np.ones(dof - 1), diagonal, -np.ones(dof - 1)),
        offsets=(-1, 0, 1),
        format="csr",
    )
    mass_matrix = diags(np.full(dof, mass), format="csr")
    return stiffness_matrix, mass_matrix


def modal_frequencies(
    stiffness_matrix: csr_matrix,
    mass_matrix: csr_matrix,
    *,
    modes: int = 6,
) -> np.ndarray:
    """Return the lowest natural frequencies in hertz."""
    dof = stiffness_matrix.shape[0]
    if stiffness_matrix.shape != (dof, dof) or mass_matrix.shape != (dof, dof):
        raise ValueError("stiffness and mass matrices must be square and equally sized")
    if not 1 <= modes < dof:
        raise ValueError("modes must be between 1 and dof - 1")

    eigenvalues = eigsh(
        stiffness_matrix,
        k=modes,
        M=mass_matrix,
        sigma=0.0,
        which="LM",
        return_eigenvectors=False,
        tol=1.0e-9,
    )
    angular_frequencies = np.sqrt(np.clip(np.sort(eigenvalues), 0.0, None))
    return angular_frequencies / (2.0 * np.pi)


def benchmark_modal_sizes(
    sizes: Sequence[int] = (10, 100, 1000),
    *,
    repeats: int = 5,
    modes: int = 6,
) -> list[ModalBenchmark]:
    """Benchmark modal extraction after one untimed warm-up per size."""
    if repeats < 1:
        raise ValueError("repeats must be positive")

    results = []
    for dof in sizes:
        stiffness_matrix, mass_matrix = build_spring_chain(dof)
        mode_count = min(modes, dof - 1)
        solver = ModalSolver.from_matrices(stiffness_matrix, mass_matrix)
        solver.solve(num_modes=mode_count, sparse=True)

        uncached_elapsed = []
        cached_elapsed = []
        frequencies = np.empty(mode_count)
        for _ in range(repeats):
            started = time.perf_counter()
            uncached = solver.solve(
                num_modes=mode_count,
                sparse=True,
                cache_factorization=False,
            )
            uncached_elapsed.append(time.perf_counter() - started)

            started = time.perf_counter()
            cached = solver.solve(num_modes=mode_count, sparse=True)
            cached_elapsed.append(time.perf_counter() - started)
            frequencies = cached.frequencies
            np.testing.assert_allclose(cached.eigenvalues, uncached.eigenvalues, rtol=1.0e-9)

        uncached_median = statistics.median(uncached_elapsed)
        cached_median = statistics.median(cached_elapsed)
        results.append(
            ModalBenchmark(
                dof=dof,
                modes=mode_count,
                minimum_seconds=min(cached_elapsed),
                median_seconds=cached_median,
                uncached_median_seconds=uncached_median,
                factorization_speedup=uncached_median / cached_median,
                first_frequency_hz=float(frequencies[0]),
            )
        )
    return results


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
