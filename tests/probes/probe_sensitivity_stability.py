#!/usr/bin/env python3
"""Compare analytic modal-frequency sensitivities with central differences."""

from __future__ import annotations

import argparse
import json
import math
from typing import Any, Sequence


DEFAULT_STEPS = (1.0e-4, 1.0e-5, 1.0e-6)


def _model_matrices() -> tuple[Any, Any, Any]:
    import numpy as np

    stiffness = np.array(
        [[5.0, -2.0, 0.0], [-2.0, 4.0, -1.0], [0.0, -1.0, 3.0]],
        dtype=float,
    )
    mass = np.diag([2.0, 1.5, 1.0])
    stiffness_derivative = np.array(
        [[1.0, -1.0, 0.0], [-1.0, 1.0, 0.0], [0.0, 0.0, 0.25]],
        dtype=float,
    )
    return stiffness, mass, stiffness_derivative


def run_probe(steps: Sequence[float] = DEFAULT_STEPS) -> dict[str, Any]:
    """Evaluate first-order frequency derivatives over several FD step sizes."""
    if not steps or any(step <= 0.0 for step in steps):
        raise ValueError("all finite-difference steps must be positive")

    try:
        import numpy as np
        from scipy.linalg import eigh
    except (ImportError, OSError) as exc:
        return {
            "probe": "sensitivity_stability",
            "status": "fail",
            "error": f"{type(exc).__name__}: {exc}",
        }

    stiffness, mass, derivative = _model_matrices()
    eigenvalues, eigenvectors = eigh(
        stiffness, mass, check_finite=True, driver="gvd"
    )
    frequencies = np.sqrt(eigenvalues) / (2.0 * math.pi)

    eigenvalue_derivative = np.diag(eigenvectors.T @ derivative @ eigenvectors)
    analytic_frequency_derivative = eigenvalue_derivative / (
        4.0 * math.pi * np.sqrt(eigenvalues)
    )

    finite_difference: dict[str, list[float]] = {}
    relative_errors: dict[str, float] = {}
    derivative_rows = []
    scale = np.maximum(np.abs(analytic_frequency_derivative), 1.0e-12)
    for step in steps:
        plus_values = eigh(
            stiffness + step * derivative,
            mass,
            eigvals_only=True,
            check_finite=True,
            driver="gvd",
        )
        minus_values = eigh(
            stiffness - step * derivative,
            mass,
            eigvals_only=True,
            check_finite=True,
            driver="gvd",
        )
        plus_frequency = np.sqrt(plus_values) / (2.0 * math.pi)
        minus_frequency = np.sqrt(minus_values) / (2.0 * math.pi)
        fd_derivative = (plus_frequency - minus_frequency) / (2.0 * step)
        step_label = f"{step:.0e}"
        finite_difference[step_label] = fd_derivative.tolist()
        relative_errors[step_label] = float(
            np.max(np.abs(fd_derivative - analytic_frequency_derivative) / scale)
        )
        derivative_rows.append(fd_derivative)

    derivative_matrix = np.vstack(derivative_rows)
    step_spread = np.ptp(derivative_matrix, axis=0)
    maximum_step_spread_relative = float(np.max(step_spread / scale))
    maximum_relative_error = max(relative_errors.values())

    thresholds = {
        "maximum_relative_error": 1.0e-5,
        "maximum_step_spread_relative": 1.0e-5,
    }
    metrics = {
        "maximum_relative_error": maximum_relative_error,
        "maximum_step_spread_relative": maximum_step_spread_relative,
    }
    checks = {
        name: bool(metrics[name] <= threshold)
        for name, threshold in thresholds.items()
    }
    checks["positive_eigenvalues"] = bool(np.all(eigenvalues > 0.0))
    checks["finite_derivatives"] = bool(np.all(np.isfinite(derivative_matrix)))

    return {
        "probe": "sensitivity_stability",
        "status": "pass" if all(checks.values()) else "fail",
        "steps": list(steps),
        "eigenvalues": eigenvalues.tolist(),
        "frequencies_hz": frequencies.tolist(),
        "analytic_frequency_derivative": analytic_frequency_derivative.tolist(),
        "finite_difference_frequency_derivative": finite_difference,
        "relative_errors": relative_errors,
        "metrics": metrics,
        "thresholds": thresholds,
        "checks": checks,
    }


def _print_human(report: dict[str, Any]) -> None:
    print(f"sensitivity stability probe: {report['status'].upper()}")
    if "error" in report:
        print(f"  Error: {report['error']}")
        return
    for step, error in report["relative_errors"].items():
        print(f"  central difference h={step}: max relative error {error:.3e}")
    print(
        "  maximum step spread: "
        f"{report['metrics']['maximum_step_spread_relative']:.3e}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--steps",
        nargs="+",
        type=float,
        default=list(DEFAULT_STEPS),
        help="positive central-difference step sizes",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    args = parser.parse_args(argv)

    try:
        report = run_probe(args.steps)
    except ValueError as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_human(report)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
