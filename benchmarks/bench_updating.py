"""Benchmark a five-iteration sensitivity-based model-updating loop."""

from __future__ import annotations

import argparse
import statistics
import time
from dataclasses import dataclass

import numpy as np
from rich.console import Console
from rich.table import Table
from scipy.sparse import csr_matrix, diags
from scipy.sparse.linalg import eigsh

from openfemlab.updating.sensitivity import frequency_sensitivity


@dataclass(frozen=True)
class UpdateRun:
    """Result from one model-updating loop."""

    elapsed_seconds: float
    initial_relative_rms: float
    final_relative_rms: float
    parameters: np.ndarray


@dataclass(frozen=True)
class UpdatingBenchmark:
    """Aggregate timing for repeated model-updating loops."""

    dof: int
    iterations: int
    repeats: int
    minimum_seconds: float
    median_seconds: float
    baseline_minimum_seconds: float
    baseline_median_seconds: float
    speedup: float
    initial_relative_rms: float
    final_relative_rms: float


def chain_incidence(dof: int) -> csr_matrix:
    """Return the spring-to-displacement incidence matrix for a fixed-free chain."""
    if dof < 2:
        raise ValueError("dof must be at least 2")

    incidence = np.zeros((dof, dof))
    incidence[0, 0] = 1.0
    spring = np.arange(1, dof)
    incidence[spring, spring - 1] = -1.0
    incidence[spring, spring] = 1.0
    return csr_matrix(incidence)


def parameterized_stiffness(
    incidence: csr_matrix,
    parameters: np.ndarray,
    *,
    base_stiffness: float = 1.0e6,
) -> csr_matrix:
    """Assemble chain stiffness with contiguous spring parameter groups."""
    dof = incidence.shape[1]
    if parameters.ndim != 1 or not 1 <= parameters.size <= dof:
        raise ValueError("parameters must be a one-dimensional array no longer than dof")
    if np.any(parameters <= 0.0):
        raise ValueError("all stiffness multipliers must be positive")

    group = np.minimum(np.arange(dof) * parameters.size // dof, parameters.size - 1)
    spring_stiffness = base_stiffness * parameters[group]
    matrix = incidence.T @ diags(spring_stiffness) @ incidence
    return matrix.tocsr()


def lowest_frequencies(
    stiffness_matrix: csr_matrix,
    mass_matrix: csr_matrix,
    *,
    modes: int,
) -> np.ndarray:
    """Extract the lowest frequencies in hertz."""
    eigenvalues = eigsh(
        stiffness_matrix,
        k=modes,
        M=mass_matrix,
        sigma=0.0,
        which="LM",
        return_eigenvectors=False,
        tol=1.0e-9,
    )
    return np.sqrt(np.clip(np.sort(eigenvalues), 0.0, None)) / (2.0 * np.pi)


def lowest_modes(
    stiffness_matrix: csr_matrix,
    mass_matrix: csr_matrix,
    *,
    modes: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Extract sorted eigenvalues and mass-normalized eigenvectors."""
    eigenvalues, mode_shapes = eigsh(
        stiffness_matrix,
        k=modes,
        M=mass_matrix,
        sigma=0.0,
        which="LM",
        tol=1.0e-9,
    )
    order = np.argsort(eigenvalues)
    return np.clip(eigenvalues[order], 0.0, None), mode_shapes[:, order]


def grouped_stiffness_derivatives(
    incidence: csr_matrix,
    parameter_count: int,
    *,
    base_stiffness: float = 1.0e6,
) -> list[csr_matrix]:
    """Exact ``dK/dp`` matrices for contiguous spring parameter groups."""
    dof = incidence.shape[0]
    groups = np.minimum(np.arange(dof) * parameter_count // dof, parameter_count - 1)
    return [
        (incidence.T @ diags(base_stiffness * (groups == group)) @ incidence).tocsr()
        for group in range(parameter_count)
    ]


def relative_rms(computed: np.ndarray, target: np.ndarray) -> float:
    """Return RMS frequency error normalized by target values."""
    return float(np.sqrt(np.mean(np.square((computed - target) / target))))


def run_updating_loop(
    *,
    dof: int = 100,
    iterations: int = 5,
    parameter_count: int = 4,
    modes: int = 6,
    finite_difference_step: float = 1.0e-3,
    damping: float = 0.8,
    sensitivity_method: str = "vectorized",
) -> UpdateRun:
    """Fit grouped chain stiffnesses to synthetic modal test data."""
    if iterations < 1:
        raise ValueError("iterations must be positive")
    if not 1 <= modes < dof:
        raise ValueError("modes must be between 1 and dof - 1")
    if not 1 <= parameter_count <= dof:
        raise ValueError("parameter_count must be between 1 and dof")
    if sensitivity_method not in {"finite-difference", "vectorized"}:
        raise ValueError("sensitivity_method must be 'finite-difference' or 'vectorized'")

    incidence = chain_incidence(dof)
    mass_matrix = diags(np.ones(dof), format="csr")
    target_pattern = np.array((0.90, 1.05, 1.15, 0.95))
    target_parameters = np.resize(target_pattern, parameter_count)
    target_frequencies = lowest_frequencies(
        parameterized_stiffness(incidence, target_parameters),
        mass_matrix,
        modes=modes,
    )

    parameters = np.ones(parameter_count)
    initial_frequencies = lowest_frequencies(
        parameterized_stiffness(incidence, parameters),
        mass_matrix,
        modes=modes,
    )
    initial_error = relative_rms(initial_frequencies, target_frequencies)
    derivatives = grouped_stiffness_derivatives(incidence, parameter_count)

    started = time.perf_counter()
    for _ in range(iterations):
        current_stiffness = parameterized_stiffness(incidence, parameters)
        if sensitivity_method == "vectorized":
            eigenvalues, mode_shapes = lowest_modes(
                current_stiffness,
                mass_matrix,
                modes=modes,
            )
            current_frequencies = np.sqrt(eigenvalues) / (2.0 * np.pi)
            sensitivity = frequency_sensitivity(
                mode_shapes,
                eigenvalues,
                derivatives,
            )
        else:
            current_frequencies = lowest_frequencies(
                current_stiffness,
                mass_matrix,
                modes=modes,
            )
            sensitivity = np.empty((modes, parameter_count))
            for column in range(parameter_count):
                perturbed = parameters.copy()
                step = finite_difference_step * max(abs(parameters[column]), 1.0)
                perturbed[column] += step
                perturbed_frequencies = lowest_frequencies(
                    parameterized_stiffness(incidence, perturbed),
                    mass_matrix,
                    modes=modes,
                )
                sensitivity[:, column] = (
                    perturbed_frequencies - current_frequencies
                ) / step

        correction, *_ = np.linalg.lstsq(
            sensitivity,
            target_frequencies - current_frequencies,
            rcond=None,
        )
        parameters = np.clip(parameters + damping * correction, 0.2, 3.0)
    elapsed = time.perf_counter() - started

    final_frequencies = lowest_frequencies(
        parameterized_stiffness(incidence, parameters),
        mass_matrix,
        modes=modes,
    )
    return UpdateRun(
        elapsed_seconds=elapsed,
        initial_relative_rms=initial_error,
        final_relative_rms=relative_rms(final_frequencies, target_frequencies),
        parameters=parameters,
    )


def benchmark_updating(*, repeats: int = 3, dof: int = 100) -> UpdatingBenchmark:
    """Benchmark repeated five-iteration updating runs."""
    if repeats < 1:
        raise ValueError("repeats must be positive")

    run_updating_loop(dof=dof, sensitivity_method="finite-difference")
    run_updating_loop(dof=dof, sensitivity_method="vectorized")
    baseline_runs = [
        run_updating_loop(dof=dof, sensitivity_method="finite-difference")
        for _ in range(repeats)
    ]
    runs = [
        run_updating_loop(dof=dof, sensitivity_method="vectorized")
        for _ in range(repeats)
    ]
    baseline_elapsed = [run.elapsed_seconds for run in baseline_runs]
    elapsed = [run.elapsed_seconds for run in runs]
    baseline_median = statistics.median(baseline_elapsed)
    optimized_median = statistics.median(elapsed)
    return UpdatingBenchmark(
        dof=dof,
        iterations=5,
        repeats=repeats,
        minimum_seconds=min(elapsed),
        median_seconds=optimized_median,
        baseline_minimum_seconds=min(baseline_elapsed),
        baseline_median_seconds=baseline_median,
        speedup=baseline_median / optimized_median,
        initial_relative_rms=runs[-1].initial_relative_rms,
        final_relative_rms=runs[-1].final_relative_rms,
    )


def render_result(result: UpdatingBenchmark) -> None:
    """Print benchmark result as a terminal table."""
    table = Table(title="Sensitivity-based model updating")
    table.add_column("DOF", justify="right")
    table.add_column("Iterations", justify="right")
    table.add_column("Repeats", justify="right")
    table.add_column("Before (ms)", justify="right")
    table.add_column("After (ms)", justify="right")
    table.add_column("Speedup", justify="right")
    table.add_column("Initial RMS", justify="right")
    table.add_column("Final RMS", justify="right")
    table.add_row(
        str(result.dof),
        str(result.iterations),
        str(result.repeats),
        f"{result.baseline_median_seconds * 1_000:.3f}",
        f"{result.median_seconds * 1_000:.3f}",
        f"{result.speedup:.2f}x",
        f"{result.initial_relative_rms:.3e}",
        f"{result.final_relative_rms:.3e}",
    )
    Console().print(table)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=3, help="timed updating loops")
    parser.add_argument("--dof", type=int, default=100, help="spring-chain DOF")
    args = parser.parse_args()
    render_result(benchmark_updating(repeats=args.repeats, dof=args.dof))


if __name__ == "__main__":
    main()
