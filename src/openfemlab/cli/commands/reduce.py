"""``openfemlab reduce cms`` -- Craig-Bampton component mode synthesis."""

from __future__ import annotations

import argparse
from typing import Any

import numpy as np

from ...core.assembly import assemble_stiffness, assemble_system
from ...reduction import build_craig_bampton, reduced_craig_bampton_matrices
from ..console import Reporter
from ..spec import build_model, load_spec

NAME = "reduce"
HELP = "model reduction utilities"


def add_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(NAME, help=HELP)
    sub = parser.add_subparsers(dest="reduce_command", required=True)
    cms = sub.add_parser("cms", help="build a Craig-Bampton basis from a model spec")
    cms.add_argument("model", help="path to the model specification (JSON or YAML)")
    cms.add_argument(
        "--interface-dofs",
        type=int,
        nargs="+",
        required=True,
        metavar="I",
        help="global DOF indices defining the interface partition",
    )
    cms.add_argument(
        "--modes",
        type=int,
        default=6,
        help="number of fixed-interface normal modes to retain (default: 6)",
    )
    cms.add_argument(
        "--format",
        choices=("table", "json", "yaml"),
        default="table",
        help="render format (default: table)",
    )
    cms.set_defaults(func=run_cms)
    return parser


def run(args: argparse.Namespace, reporter: Reporter) -> int:
    if args.reduce_command == "cms":
        return run_cms(args, reporter)
    reporter.error(f"unknown reduce command {args.reduce_command!r}")
    return 2


def run_cms(args: argparse.Namespace, reporter: Reporter) -> int:
    model = build_model(load_spec(args.model))
    system = assemble_system(model)
    stiffness = assemble_stiffness(model)
    k_dense = stiffness.toarray() if hasattr(stiffness, "toarray") else np.asarray(stiffness)
    m_dense = system.mass.toarray() if hasattr(system.mass, "toarray") else np.asarray(system.mass)
    basis = build_craig_bampton(
        k_dense,
        m_dense,
        args.interface_dofs,
        num_modes=args.modes,
    )
    k_red, m_red = reduced_craig_bampton_matrices(basis, k_dense, m_dense)
    report = build_report(model, basis, k_red, m_red, source=str(args.model))
    if args.format == "table":
        render(report, reporter)
    else:
        reporter.document(report, format=args.format)
    return 0


def build_report(model, basis, k_red, m_red, *, source: str) -> dict[str, Any]:
    return {
        "kind": "craig_bampton",
        "source": source,
        "model": model.name,
        "summary": {
            "n_constraint_modes": basis.n_constraint_modes,
            "n_fixed_interface_modes": basis.n_fixed_interface_modes,
            "basis_size": int(basis.transformation.shape[1]),
            "reduced_dofs": int(k_red.shape[0]),
        },
        "fixed_interface_frequencies_hz": [
            float(value) for value in basis.fixed_interface_frequencies_hz
        ],
        "reduced_stiffness_shape": list(k_red.shape),
        "reduced_mass_shape": list(m_red.shape),
        "meta": {"interface_dofs": [int(value) for value in basis.interface_dofs]},
    }


def render(report: dict[str, Any], reporter: Reporter) -> None:
    summary = report["summary"]
    reporter.heading(f"Craig-Bampton CMS — {report['model']}")
    reporter.fields(
        {
            "source": report["source"],
            "constraint modes": summary["n_constraint_modes"],
            "fixed-interface modes": summary["n_fixed_interface_modes"],
            "basis size": summary["basis_size"],
            "reduced dofs": summary["reduced_dofs"],
        }
    )
    freqs = report.get("fixed_interface_frequencies_hz") or []
    if freqs:
        reporter.line("fixed-interface frequencies (Hz):")
        for index, value in enumerate(freqs, start=1):
            reporter.line(f"  {index:>2}  {value:.4g}")
