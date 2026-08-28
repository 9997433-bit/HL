"""``openfemlab static`` -- linear static analysis of a model specification."""

from __future__ import annotations

import argparse
from typing import Any

import numpy as np

from ..analysis import as_static_result, solve_static_spec
from ..console import Column, Reporter, format_number
from ..spec import load_spec

NAME = "static"
HELP = "run a linear static analysis on a model specification"


def add_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        NAME,
        help=HELP,
        description=(
            "Assemble the model described by a JSON/YAML specification, apply "
            "nodal loads and recover the static displacement field."
        ),
    )
    parser.add_argument("model", help="path to the model specification (JSON or YAML)")
    parser.add_argument(
        "--format",
        choices=("table", "json", "yaml"),
        default="table",
        help="how to render the summary (default: table)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        metavar="PATH",
        help="write the full static result (displacements, DOF map) to JSON/YAML",
    )
    parser.set_defaults(func=run)
    return parser


def run(args: argparse.Namespace, reporter: Reporter) -> int:
    spec = load_spec(args.model)
    model, result = solve_static_spec(spec)
    report = build_report(model, result, source=str(args.model))

    if args.format == "table":
        render(report, reporter)
    else:
        reporter.document(report, format=args.format)

    if args.output:
        from ...io import write_static_result

        write_static_result(
            as_static_result(model, result, meta={"source": str(args.model)}), args.output
        )
        reporter.note(f"static result written to {args.output}")
    return 0


def build_report(model, result, *, source: str) -> dict[str, Any]:
    displacements = result.displacements
    peak = float(np.max(np.abs(displacements))) if displacements.size else 0.0
    peak_index = int(np.argmax(np.abs(displacements))) if displacements.size else 0
    peak_node, peak_dof = model.describe_dof(peak_index)
    load_norm = float(np.linalg.norm(result.load_vector))
    energy = float(result.strain_energy) if result.system is not None else None
    rows = []
    for index, value in enumerate(displacements):
        if abs(value) <= 1e-12:
            continue
        node_id, dof = model.describe_dof(index)
        rows.append(
            {
                "node": str(node_id),
                "dof": dof.name,
                "displacement": float(value),
            }
        )
    rows.sort(key=lambda row: abs(row["displacement"]), reverse=True)
    return {
        "kind": "static",
        "source": source,
        "model": model.name,
        "summary": {
            "num_dofs": int(model.num_dofs),
            "num_free_dofs": int(result.free_dofs.size if result.free_dofs is not None else 0),
            "load_norm": load_norm,
            "max_abs_displacement": peak,
            "max_displacement_node": str(peak_node),
            "max_displacement_dof": peak_dof.name,
            "strain_energy": energy,
        },
        "displacements": rows[:32],
    }


def render(report: dict[str, Any], reporter: Reporter) -> None:
    summary = report["summary"]
    reporter.heading(f"Static analysis — {report['model']}")
    reporter.fields(
        {
            "source": report["source"],
            "load ‖f‖": format_number(summary["load_norm"]),
            "max |u|": format_number(summary["max_abs_displacement"]),
            "peak location": (
                f"{summary['max_displacement_node']}:{summary['max_displacement_dof']}"
            ),
            "strain energy": (
                format_number(summary["strain_energy"])
                if summary["strain_energy"] is not None
                else "n/a"
            ),
        }
    )
    rows = report["displacements"]
    if not rows:
        reporter.note("all displacements are zero (no loads or fully constrained model)")
        return
    reporter.table(
        (
            Column("node", justify="left"),
            Column("dof", justify="left"),
            Column("u", justify="right"),
        ),
        [(row["node"], row["dof"], format_number(row["displacement"])) for row in rows[:16]],
    )
