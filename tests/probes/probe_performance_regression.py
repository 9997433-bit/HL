#!/usr/bin/env python3
"""Measure optimized kernels against the pre-optimization reference paths."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from collections.abc import Callable, Sequence
from typing import Any

import numpy as np
import scipy.sparse as sp

from openfemlab.core.assembly import assemble_system
from openfemlab.mesh.simple import spring_mass_chain
from openfemlab.solver.modal import ModalSolver
from openfemlab.updating.sensitivity import eigenvalue_sensitivity


def _timing(function: Callable[[], object], repeats: int) -> float:
    function()
    samples = []
    for _ in range(repeats):
        started = time.perf_counter()
        function()
        samples.append(time.perf_counter() - started)
    return statistics.median(samples) * 1_000.0


def _legacy_accumulate(model, matrix_getter) -> sp.csr_matrix:
    """List-based, separate-pass assembly retained as a benchmark reference."""
    rows: list[np.ndarray] = []
    cols: list[np.ndarray] = []
    data: list[np.ndarray] = []
    for element in model.elements:
        coordinates = model.node_coords(element.node_ids)
        local = np.asarray(matrix_getter(element, coordinates), dtype=float)
        dofs = element.global_dofs(model)
        if local.any():
            rows.append(np.repeat(dofs, dofs.size))
            cols.append(np.tile(dofs, dofs.size))
            data.append(local.reshape(-1))
    if not rows:
        return sp.csr_matrix((model.num_dofs, model.num_dofs))
    return sp.coo_matrix(
        (np.concatenate(data), (np.concatenate(rows), np.concatenate(cols))),
        shape=(model.num_dofs, model.num_dofs),
    ).tocsr()


def _legacy_assemble_system(model) -> tuple[sp.csr_matrix, sp.csr_matrix]:
    stiffness = _legacy_accumulate(model, lambda element, coords: element.stiffness_matrix(coords))
    mass = _legacy_accumulate(model, lambda element, coords: element.mass_matrix(coords))
    diagonal = model.point_mass_vector()
    if diagonal.any():
        mass = mass + sp.diags(diagonal, format="csr")
    return (
        ((stiffness + stiffness.T) * 0.5).tocsr(),
        ((mass + mass.T) * 0.5).tocsr(),
    )


def _scalar_eigenvalue_sensitivity(
    mode_shapes: np.ndarray,
    eigenvalues: np.ndarray,
    derivatives: Sequence[np.ndarray],
) -> np.ndarray:
    sensitivity = np.empty((mode_shapes.shape[1], len(derivatives)))
    for parameter, derivative in enumerate(derivatives):
        for mode in range(mode_shapes.shape[1]):
            vector = mode_shapes[:, mode]
            sensitivity[mode, parameter] = np.real(np.vdot(vector, derivative @ vector))
    return sensitivity


def run_probe(*, dof: int = 2_000, repeats: int = 5) -> dict[str, Any]:
    """Return timings, speedups, and numerical-equivalence checks."""
    if dof < 50:
        raise ValueError("dof must be at least 50")
    if repeats < 1:
        raise ValueError("repeats must be positive")

    model = spring_mass_chain(dof, 1.0e6, 1.0)
    legacy_stiffness, legacy_mass = _legacy_assemble_system(model)
    assembled = assemble_system(model)
    assembly_before = _timing(lambda: _legacy_assemble_system(model), repeats)
    assembly_after = _timing(lambda: assemble_system(model), repeats)

    solver = ModalSolver(model)

    def cold_solve() -> object:
        solver.clear_cache()
        return solver.solve(num_modes=8, sparse=True)

    factorization_before = _timing(cold_solve, repeats)
    solver.clear_cache()
    reference_modes = solver.solve(num_modes=8, sparse=True)
    factorization_after = _timing(
        lambda: solver.solve(num_modes=8, sparse=True),
        repeats,
    )
    cached_modes = solver.solve(num_modes=8, sparse=True)

    rng = np.random.default_rng(42)
    sensitivity_dof, modes, parameters = 240, 24, 12
    mode_shapes, _ = np.linalg.qr(rng.normal(size=(sensitivity_dof, modes)))
    eigenvalues = np.linspace(1.0, 100.0, modes)
    derivatives = []
    for _ in range(parameters):
        factor = rng.normal(size=(sensitivity_dof, 16))
        derivatives.append(factor @ factor.T)
    scalar = _scalar_eigenvalue_sensitivity(mode_shapes, eigenvalues, derivatives)
    vectorized = eigenvalue_sensitivity(mode_shapes, eigenvalues, derivatives)
    sensitivity_before = _timing(
        lambda: _scalar_eigenvalue_sensitivity(mode_shapes, eigenvalues, derivatives),
        repeats,
    )
    sensitivity_after = _timing(
        lambda: eigenvalue_sensitivity(mode_shapes, eigenvalues, derivatives),
        repeats,
    )

    timings = {
        "sparse_assembly": {
            "before_ms": assembly_before,
            "after_ms": assembly_after,
            "speedup": assembly_before / assembly_after,
        },
        "repeated_sparse_solve": {
            "before_ms": factorization_before,
            "after_ms": factorization_after,
            "speedup": factorization_before / factorization_after,
        },
        "eigenvalue_sensitivity": {
            "before_ms": sensitivity_before,
            "after_ms": sensitivity_after,
            "speedup": sensitivity_before / sensitivity_after,
        },
    }
    thresholds = {
        "sparse_assembly_speedup": 1.10,
        "repeated_sparse_solve_speedup": 1.05,
        "eigenvalue_sensitivity_speedup": 1.25,
    }
    checks = {
        "stiffness_equivalent": bool(
            np.allclose(assembled.K.toarray(), legacy_stiffness.toarray())
        ),
        "mass_equivalent": bool(np.allclose(assembled.M.toarray(), legacy_mass.toarray())),
        "eigenvalues_equivalent": bool(
            np.allclose(cached_modes.eigenvalues, reference_modes.eigenvalues, rtol=1.0e-9)
        ),
        "sensitivity_equivalent": bool(np.allclose(vectorized, scalar, rtol=1.0e-12)),
        "factorization_cached": solver.factorization_cache_size == 1,
        "sparse_assembly_speedup": (
            timings["sparse_assembly"]["speedup"] >= thresholds["sparse_assembly_speedup"]
        ),
        "repeated_sparse_solve_speedup": (
            timings["repeated_sparse_solve"]["speedup"]
            >= thresholds["repeated_sparse_solve_speedup"]
        ),
        "eigenvalue_sensitivity_speedup": (
            timings["eigenvalue_sensitivity"]["speedup"]
            >= thresholds["eigenvalue_sensitivity_speedup"]
        ),
    }
    return {
        "probe": "performance_regression",
        "status": "pass" if all(checks.values()) else "fail",
        "configuration": {
            "assembly_dof": dof,
            "sensitivity_dof": sensitivity_dof,
            "modes": modes,
            "parameters": parameters,
            "repeats": repeats,
        },
        "timings": timings,
        "thresholds": thresholds,
        "checks": checks,
    }


def _print_human(report: dict[str, Any]) -> None:
    print(f"performance regression probe: {report['status'].upper()}")
    for name, timing in report["timings"].items():
        print(
            f"  {name}: {timing['before_ms']:.3f} ms -> "
            f"{timing['after_ms']:.3f} ms ({timing['speedup']:.2f}x)"
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dof", type=int, default=2_000, help="assembly/solver model size")
    parser.add_argument("--repeats", type=int, default=5, help="timed repetitions")
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    args = parser.parse_args(argv)
    try:
        report = run_probe(dof=args.dof, repeats=args.repeats)
    except ValueError as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_human(report)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
