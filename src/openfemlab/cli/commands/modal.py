"""``openfemlab modal`` -- normal-mode analysis of a model specification."""

from __future__ import annotations

import argparse
from typing import Any

import numpy as np

from ...core.model import DOF
from ...solver.modal import NORMALIZATIONS
from ..analysis import as_modal_result, solve_spec
from ..console import Column, Reporter, format_number
from ..spec import load_spec

NAME = "modal"
HELP = "run a normal-mode analysis on a model specification"


def add_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        NAME,
        help=HELP,
        description=(
            "Assemble the model described by a JSON/YAML specification, extract its "
            "lowest normal modes and report frequencies, generalized masses and "
            "effective modal masses."
        ),
    )
    parser.add_argument("model", help="path to the model specification (JSON or YAML)")
    parser.add_argument(
        "-n", "--modes", type=int, default=6, help="number of modes to extract (default: 6)"
    )
    parser.add_argument(
        "--max-frequency",
        type=float,
        default=None,
        metavar="HZ",
        help="discard modes above this frequency",
    )
    parser.add_argument(
        "--normalization",
        choices=NORMALIZATIONS,
        default="mass",
        help="mode shape scaling (default: mass)",
    )
    parser.add_argument(
        "--direction",
        default=None,
        metavar="DOF",
        help="direction for participation factors, e.g. UX (default: first translational DOF)",
    )
    backend = parser.add_mutually_exclusive_group()
    backend.add_argument(
        "--sparse", dest="sparse", action="store_true", default=None, help="force the Lanczos path"
    )
    backend.add_argument(
        "--dense", dest="sparse", action="store_false", help="force the dense LAPACK path"
    )
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
        help="write the full modal result (frequencies, shapes, DOF map) to a JSON/YAML file",
    )
    parser.set_defaults(func=run)
    return parser


def run(args: argparse.Namespace, reporter: Reporter) -> int:
    spec = load_spec(args.model)
    model, result = solve_spec(
        spec,
        num_modes=args.modes,
        normalization=args.normalization,
        max_frequency=args.max_frequency,
        sparse=args.sparse,
    )
    direction = _direction(model, result, args.direction)
    report = build_report(model, result, direction=direction, source=str(args.model))

    if args.format == "table":
        render(report, reporter)
    else:
        reporter.document(report, format=args.format)

    if args.output:
        from ...io import write_modal_result

        write_modal_result(
            as_modal_result(model, result, meta={"source": str(args.model)}), args.output
        )
        reporter.note(f"modal result written to {args.output}")
    return 0


def build_report(model, result, *, direction: DOF, source: str) -> dict[str, Any]:
    """Assemble the JSON-ready summary of one modal run."""
    modal_masses = result.modal_masses
    participation = result.participation_factors(direction)
    effective = result.effective_masses(direction)
    total_mass = result.system.total_mass if result.system is not None else 0.0
    cumulative = np.cumsum(effective)
    rigid = result.rigid_body_modes

    modes = [
        {
            "mode": index + 1,
            "frequency_hz": float(result.frequencies[index]),
            "angular_frequency_rad_s": float(result.angular_frequencies[index]),
            "period_s": float(result.periods[index]),
            "eigenvalue": float(result.eigenvalues[index]),
            "modal_mass": float(modal_masses[index]),
            "participation_factor": float(participation[index]),
            "effective_mass": float(effective[index]),
            "cumulative_mass_fraction": _fraction(cumulative[index], total_mass),
            "rigid_body": bool(rigid[index]),
        }
        for index in range(result.num_modes)
    ]

    return {
        "command": NAME,
        "source": source,
        "model": {
            "name": model.name,
            "nodes": model.num_nodes,
            "elements": model.num_elements,
            "dofs": model.num_dofs,
            "free_dofs": int(model.free_dofs.size),
            "constrained_dofs": int(model.constrained_dofs.size),
            "dof_signature": [dof.name for dof in model.dofs],
            "total_mass": float(total_mass),
        },
        "analysis": {
            "num_modes": result.num_modes,
            "normalization": result.normalization,
            "direction": direction.name,
            "condensed_dofs": int(result.num_condensed_dofs),
            "orthogonality_error": float(result.orthogonality_error()),
        },
        "modes": modes,
    }


def render(report: dict[str, Any], reporter: Reporter) -> None:
    model = report["model"]
    analysis = report["analysis"]
    reporter.heading(f"Modal analysis: {model['name']}")
    reporter.fields(
        {
            "nodes / elements": f"{model['nodes']} / {model['elements']}",
            "DOFs": f"{model['dofs']} ({model['free_dofs']} free, "
            f"{model['constrained_dofs']} constrained)",
            "signature": " ".join(model["dof_signature"]),
            "total mass": format_number(model["total_mass"]),
            "normalization": analysis["normalization"],
        }
    )

    columns = (
        Column("mode"),
        Column("f [Hz]"),
        Column("omega [rad/s]"),
        Column("period [s]"),
        Column("modal mass"),
        Column(f"L_{analysis['direction']}"),
        Column("eff. mass"),
        Column("cum. [%]"),
    )
    rows = [
        (
            f"{mode['mode']}{'*' if mode['rigid_body'] else ''}",
            format_number(mode["frequency_hz"]),
            format_number(mode["angular_frequency_rad_s"]),
            format_number(mode["period_s"], 4),
            format_number(mode["modal_mass"], 4),
            format_number(mode["participation_factor"], 4),
            format_number(mode["effective_mass"], 4),
            format_number(100.0 * mode["cumulative_mass_fraction"], 4),
        )
        for mode in report["modes"]
    ]
    caption = None
    if any(mode["rigid_body"] for mode in report["modes"]):
        caption = "* rigid-body mode (zero frequency)"
    reporter.table(columns, rows, caption=caption)

    if analysis["condensed_dofs"]:
        reporter.note(
            f"{analysis['condensed_dofs']} massless DOFs were statically condensed"
        )


def _direction(model, result, requested: str | None) -> DOF:
    """Participation direction: the requested one, else the most excited axis.

    Defaulting to the first DOF would report a near-zero effective mass for a
    bending model, so the direction capturing the most modal mass is picked.
    """
    if requested is not None:
        return DOF.parse(requested)
    candidates = model.translational_dofs or model.dofs
    return max(candidates, key=lambda dof: float(np.sum(result.effective_masses(dof))))


def _fraction(value: float, total: float) -> float:
    return float(value / total) if total > 0.0 else 0.0
