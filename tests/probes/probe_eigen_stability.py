#!/usr/bin/env python3
"""Check repeated symmetric generalized eigenvalue solves for drift."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from typing import Any

DEFAULT_REPEATS = 25


def _benchmark_matrices() -> tuple[Any, Any]:
    import numpy as np

    stiffness = np.array(
        [
            [6.0, -2.0, 0.0, 0.0],
            [-2.0, 5.0, -1.0, 0.0],
            [0.0, -1.0, 4.0, -1.0],
            [0.0, 0.0, -1.0, 2.5],
        ],
        dtype=float,
    )
    mass = np.diag([2.0, 1.5, 1.0, 0.75])
    return stiffness, mass


def run_probe(repeats: int = DEFAULT_REPEATS) -> dict[str, Any]:
    """Solve one well-conditioned problem repeatedly and compare all results."""
    if repeats < 2:
        raise ValueError("repeats must be at least 2")

    try:
        import numpy as np
        from scipy.linalg import eigh
    except (ImportError, OSError) as exc:
        return {
            "probe": "eigen_stability",
            "status": "fail",
            "error": f"{type(exc).__name__}: {exc}",
        }

    stiffness, mass = _benchmark_matrices()
    baseline_values, baseline_vectors = eigh(
        stiffness, mass, check_finite=True, driver="gvd"
    )

    max_eigenvalue_relative_drift = 0.0
    max_eigenvector_absolute_drift = 0.0
    max_residual = 0.0
    max_mass_orthogonality_error = 0.0

    for _ in range(repeats):
        values, vectors = eigh(stiffness, mass, check_finite=True, driver="gvd")
        value_scale = np.maximum(np.abs(baseline_values), 1.0)
        max_eigenvalue_relative_drift = max(
            max_eigenvalue_relative_drift,
            float(np.max(np.abs(values - baseline_values) / value_scale)),
        )

        signs = np.where(
            np.sum(baseline_vectors * vectors, axis=0) < 0.0, -1.0, 1.0
        )
        aligned_vectors = vectors * signs
        max_eigenvector_absolute_drift = max(
            max_eigenvector_absolute_drift,
            float(np.max(np.abs(aligned_vectors - baseline_vectors))),
        )

        residual = stiffness @ vectors - (mass @ vectors) * values[np.newaxis, :]
        residual_scale = (
            np.linalg.norm(stiffness, ord=2)
            + np.max(np.abs(values)) * np.linalg.norm(mass, ord=2)
        )
        max_residual = max(
            max_residual,
            float(np.linalg.norm(residual, ord=2) / residual_scale),
        )
        mass_gram = vectors.T @ mass @ vectors
        max_mass_orthogonality_error = max(
            max_mass_orthogonality_error,
            float(np.max(np.abs(mass_gram - np.eye(len(values))))),
        )

    thresholds = {
        "eigenvalue_relative_drift": 1.0e-12,
        "eigenvector_absolute_drift": 1.0e-10,
        "normalized_residual": 1.0e-12,
        "mass_orthogonality_error": 1.0e-12,
    }
    metrics = {
        "eigenvalue_relative_drift": max_eigenvalue_relative_drift,
        "eigenvector_absolute_drift": max_eigenvector_absolute_drift,
        "normalized_residual": max_residual,
        "mass_orthogonality_error": max_mass_orthogonality_error,
    }
    checks = {
        name: bool(metrics[name] <= threshold)
        for name, threshold in thresholds.items()
    }
    checks["positive_eigenvalues"] = bool(np.all(baseline_values > 0.0))

    return {
        "probe": "eigen_stability",
        "status": "pass" if all(checks.values()) else "fail",
        "repeats": repeats,
        "eigenvalues": baseline_values.tolist(),
        "metrics": metrics,
        "thresholds": thresholds,
        "checks": checks,
    }


def _print_human(report: dict[str, Any]) -> None:
    print(f"eigen stability probe: {report['status'].upper()}")
    if "error" in report:
        print(f"  Error: {report['error']}")
        return
    print(f"  repeated solves: {report['repeats']}")
    for metric, value in report["metrics"].items():
        threshold = report["thresholds"][metric]
        print(f"  {metric}: {value:.3e} (limit {threshold:.1e})")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    args = parser.parse_args(argv)

    try:
        report = run_probe(args.repeats)
    except ValueError as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_human(report)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
