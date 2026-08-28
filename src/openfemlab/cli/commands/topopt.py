"""``openfemlab topopt`` -- SIMP topology optimization (compliance, OC updates)."""

from __future__ import annotations

import argparse
from typing import Any

from ...optimization.topology import run_simp_topology
from ..console import Column, Reporter, format_number
from ..spec import build_load_cases, build_model, load_spec

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
        "--filter-radius",
        type=float,
        default=None,
        metavar="R",
        help="Sigmund density filter radius in model length units (default: disabled)",
    )
    parser.add_argument(
        "--heaviside-beta",
        type=float,
        default=None,
        metavar="B",
        help="Heaviside projection sharpness (requires --filter-radius; default: disabled)",
    )
    parser.add_argument(
        "--heaviside-eta",
        type=float,
        default=0.5,
        help="Heaviside projection threshold eta in (0, 1) (default: 0.5)",
    )
    parser.add_argument(
        "--no-heaviside-continuation",
        action="store_true",
        help="use a fixed Heaviside beta instead of ramping across iterations",
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
    parser.add_argument(
        "--export-vtu",
        default=None,
        metavar="PATH",
        help="write projected/physical densities as VTU/VTK cell data",
    )
    parser.add_argument(
        "--export-projected",
        action="store_true",
        help="when exporting VTU, use projected densities instead of physical rho",
    )
    parser.add_argument(
        "--stress-limit",
        type=float,
        default=None,
        metavar="S",
        help="optional von Mises stress limit for p-norm constraint (Pa)",
    )
    parser.add_argument(
        "--stress-p",
        type=float,
        default=8.0,
        help="p-norm exponent for stress aggregation (default: 8)",
    )
    parser.set_defaults(func=run)
    return parser


def run(args: argparse.Namespace, reporter: Reporter) -> int:
    spec = load_spec(args.model)
    model = build_model(spec)
    load_cases = build_load_cases(spec, model)
    load_vectors = None
    load_weights = None
    if load_cases is not None:
        load_vectors, load_weights = load_cases
    result = run_simp_topology(
        model,
        vol_frac=args.vol_frac,
        penalization=args.penalty,
        max_iter=args.max_iter,
        move=args.move,
        filter_radius=args.filter_radius,
        heaviside_beta=args.heaviside_beta,
        heaviside_eta=args.heaviside_eta,
        heaviside_continuation=not args.no_heaviside_continuation,
        load_vectors=load_vectors,
        load_weights=load_weights,
        stress_limit=args.stress_limit,
        stress_p=args.stress_p,
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
    if args.export_vtu:
        from ...io.topology_export import write_topology_vtu

        projected = result.projected_densities if args.export_projected else None
        write_topology_vtu(
            model,
            result.densities,
            args.export_vtu,
            use_projected=projected,
        )
        reporter.note(f"topology VTU written to {args.export_vtu}")
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
        "projected_densities": (
            [
                {"element": index, "density": float(value)}
                for index, value in enumerate(result.projected_densities)
            ]
            if result.projected_densities is not None
            else None
        ),
        "compliance_history": [float(value) for value in result.compliance_history],
        "volume_history": [float(value) for value in result.volume_history],
        "stress_history": [float(value) for value in result.stress_history],
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
            [(str(row["element"]), format_number(row["density"])) for row in rows],
        )
