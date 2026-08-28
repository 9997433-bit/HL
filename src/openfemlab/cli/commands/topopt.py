"""``openfemlab topopt`` -- SIMP topology optimization (compliance, OC updates)."""

from __future__ import annotations

import argparse
from typing import Any

from ...optimization.topology import run_simp_topology
from ..console import Column, Reporter, format_number
from ..spec import build_model, load_spec

NAME = "topopt"
HELP = "run SIMP topology optimization on a loaded structural model"


def add_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        NAME,
        help=HELP,
        description=(
            "Minimize static compliance with Solid Isotropic Material with "
            "Penalization (SIMP) and optimality-criteria updates."
        ),
    )
    parser.add_argument("model", help="path to the model specification (JSON or YAML)")
    parser.add_argument(
        "--vol-frac",
        type=float,
        default=0.4,
        help="target volume fraction in (0, 1] (default: 0.4)",
    )
    parser.add_argument(
        "--penalty",
        type=float,
        default=3.0,
        help="SIMP penalization exponent (default: 3)",
    )
    parser.add_argument(
        "--max-iter",
        type=int,
        default=50,
        help="maximum OC iterations (default: 50)",
    )
    parser.add_argument(
        "--move",
        type=float,
        default=0.2,
        help="OC move limit (default: 0.2)",
    )
    parser.add_argument(
        "--format",
        choices=("table", "json", "yaml"),
        default="table",
        help="render format (default: table)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        metavar="PATH",
        help="write final element densities to JSON/YAML",
    )
    parser.set_defaults(func=run)
    return parser


def run(args: argparse.Namespace, reporter: Reporter) -> int:
    spec = load_spec(args.model)
    model = build_model(spec)
    result = run_simp_topology(
        model,
        vol_frac=args.vol_frac,
        penalization=args.penalty,
        max_iter=args.max_iter,
        move=args.move,
    )
    report = build_report(model, result, source=str(args.model))
    if args.format == "table":
        render(report, reporter)
    else:
        reporter.document(report, format=args.format)
    if args.output:
        from ...io import write_data

        write_data(report, args.output)
        reporter.note(f"topology result written to {args.output}")
    return 0


def build_report(model, result, *, source: str) -> dict[str, Any]:
    return {
        "kind": "topology",
        "source": source,
        "model": model.name,
        "summary": {
            "iterations": result.iterations,
            "mean_density": result.mean_density,
            "final_compliance": (
                result.compliance_history[-1] if result.compliance_history else None
            ),
            "final_volume_fraction": result.volume_history[-1] if result.volume_history else None,
            "num_elements": int(result.densities.size),
        },
        "densities": [
            {"element": index, "density": float(value)}
            for index, value in enumerate(result.densities)
        ],
        "compliance_history": [float(value) for value in result.compliance_history],
        "volume_history": [float(value) for value in result.volume_history],
        "meta": dict(result.meta),
    }


def render(report: dict[str, Any], reporter: Reporter) -> None:
    summary = report["summary"]
    reporter.heading(f"SIMP topology — {report['model']}")
    reporter.fields(
        {
            "source": report["source"],
            "iterations": summary["iterations"],
            "mean density": format_number(summary["mean_density"]),
            "compliance": format_number(summary["final_compliance"]),
            "volume fraction": format_number(summary["final_volume_fraction"]),
        }
    )
    rows = sorted(report["densities"], key=lambda row: row["density"], reverse=True)[:12]
    if rows:
        reporter.table(
            (Column("element", justify="right"), Column("rho", justify="right")),
            [(row["element"], format_number(row["density"])) for row in rows],
        )
