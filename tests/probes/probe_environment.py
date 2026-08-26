#!/usr/bin/env python3
"""Report and validate the numerical Python/BLAS environment."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import platform
import re
import warnings
from typing import Any, Sequence


DEFAULT_MIN_NUMPY = "1.24"
DEFAULT_MIN_SCIPY = "1.10"


def _version_key(version: str) -> tuple[int, ...]:
    """Return the numeric release prefix without requiring packaging."""
    parts = re.match(r"^(\d+(?:\.\d+)*)", version)
    return tuple(int(part) for part in parts.group(1).split(".")) if parts else ()


def _meets_minimum(actual: str, minimum: str) -> bool:
    actual_key = _version_key(actual)
    minimum_key = _version_key(minimum)
    width = max(len(actual_key), len(minimum_key))
    return actual_key + (0,) * (width - len(actual_key)) >= minimum_key + (0,) * (
        width - len(minimum_key)
    )


def _blas_vendor(config: str) -> str:
    lowered = config.lower()
    for vendor in ("openblas", "mkl", "blis", "accelerate", "atlas"):
        if vendor in lowered:
            return vendor
    return "unknown"


def run_probe(
    min_numpy: str = DEFAULT_MIN_NUMPY,
    min_scipy: str = DEFAULT_MIN_SCIPY,
) -> dict[str, Any]:
    """Run dependency, BLAS-configuration, and matrix-operation checks."""
    report: dict[str, Any] = {
        "probe": "environment",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "requirements": {
            "numpy": f">={min_numpy}",
            "scipy": f">={min_scipy}",
        },
        "checks": {},
        "status": "fail",
    }

    try:
        import numpy as np
        import scipy
    except (ImportError, OSError) as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        report["checks"]["imports"] = False
        return report

    config_buffer = io.StringIO()
    with warnings.catch_warnings(record=True) as config_warnings:
        warnings.simplefilter("always")
        with contextlib.redirect_stdout(config_buffer):
            np.show_config()
    blas_config = config_buffer.getvalue().strip()

    product = np.array([[1.0, 2.0], [3.0, 4.0]]) @ np.array([2.0, -1.0])
    matrix_operation_ok = bool(np.allclose(product, [0.0, 2.0]))
    checks = {
        "imports": True,
        "numpy_version": _meets_minimum(np.__version__, min_numpy),
        "scipy_version": _meets_minimum(scipy.__version__, min_scipy),
        "blas_configuration_present": bool(blas_config),
        "matrix_operation": matrix_operation_ok,
    }
    report.update(
        {
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "blas": {
                "vendor": _blas_vendor(blas_config),
                "configuration": blas_config,
                "warnings": [str(warning.message) for warning in config_warnings],
            },
            "checks": checks,
            "status": "pass" if all(checks.values()) else "fail",
        }
    )
    return report


def _print_human(report: dict[str, Any]) -> None:
    print(f"environment probe: {report['status'].upper()}")
    print(f"  Python: {report['python']}")
    if "numpy" in report:
        print(f"  NumPy:  {report['numpy']}")
        print(f"  SciPy:  {report['scipy']}")
        print(f"  BLAS:   {report['blas']['vendor']}")
    if "error" in report:
        print(f"  Error:  {report['error']}")
    for check, passed in report["checks"].items():
        print(f"  [{'ok' if passed else '!!'}] {check}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-numpy", default=DEFAULT_MIN_NUMPY)
    parser.add_argument("--min-scipy", default=DEFAULT_MIN_SCIPY)
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    args = parser.parse_args(argv)

    report = run_probe(args.min_numpy, args.min_scipy)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_human(report)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
