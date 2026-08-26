"""``openfemlab`` console entry point.

Three analysis commands mirror the platform layers: ``modal`` extracts normal
modes from a model specification, ``correlate`` compares them against measured
data, and ``update`` closes the loop by tuning model parameters. ``version``
and ``info`` round out the interface for scripting and support.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

import openfemlab
from openfemlab.exceptions import OpenFEMLabError

from .commands import COMMANDS
from .console import RICH_AVAILABLE, Reporter

__all__ = ["build_parser", "main"]

_MODULES = (
    ("core", "model, elements, DOF maps and assembly"),
    ("mesh", "parametric bar, beam, truss and spring-mass meshes"),
    ("solver", "normal-mode extraction (dense and sparse)"),
    ("correlation", "MAC, COMAC, frequency metrics and mode pairing"),
    ("updating", "sensitivity-based parameter updating"),
    ("io", "schema-versioned JSON/YAML interchange"),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openfemlab",
        description="OpenFEMLab: modal analysis, FE-test correlation and model updating.",
        epilog=(
            "examples:\n"
            "  openfemlab modal cantilever.yaml -n 8\n"
            "  openfemlab correlate cantilever.yaml measured.yaml --mac-threshold 0.7\n"
            "  openfemlab update updating.yaml -o cantilever.updated.yaml"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"openfemlab {openfemlab.__version__}"
    )
    parser.add_argument("--no-color", action="store_true", help="disable rich formatting")
    parser.add_argument("-q", "--quiet", action="store_true", help="print results only")
    parser.add_argument(
        "--traceback", action="store_true", help="re-raise errors instead of reporting them"
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND", required=True)
    for module in COMMANDS:
        module.add_parser(subparsers)
    subparsers.add_parser("version", help="print the package version").set_defaults(
        func=_cmd_version
    )
    subparsers.add_parser("info", help="show the platform and module overview").set_defaults(
        func=_cmd_info
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    reporter = Reporter(
        color=not args.no_color,
        quiet=args.quiet,
        diagnostics_to_stderr=getattr(args, "format", "table") != "table",
    )
    try:
        return int(args.func(args, reporter))
    except OpenFEMLabError as exc:
        if args.traceback:
            raise
        reporter.error(str(exc))
        return 1
    except (OSError, ValueError) as exc:
        if args.traceback:
            raise
        reporter.error(f"{type(exc).__name__}: {exc}")
        return 1


def _cmd_version(args: argparse.Namespace, reporter: Reporter) -> int:
    reporter.line(openfemlab.__version__)
    return 0


def _cmd_info(args: argparse.Namespace, reporter: Reporter) -> int:
    reporter.heading(f"OpenFEMLab {openfemlab.__version__}")
    reporter.line("Solver-independent structural dynamics, correlation and model updating.")
    from .console import Column

    reporter.table(
        (Column("module", justify="left"), Column("purpose", justify="left")),
        [(name, purpose) for name, purpose in _MODULES],
    )
    reporter.fields(
        {
            "rich output": "available" if RICH_AVAILABLE else "not installed (pip install rich)",
            "architecture": "docs/ARCHITECTURE.md",
        }
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - module execution path
    sys.exit(main())
