"""``openfemlab sdm`` — structural dynamics modification (SDM) tools."""

from __future__ import annotations

import argparse
from typing import Any

import numpy as np

from ...solver.modal import ModalSolver
from ...solver.sdm import scan_stiffness_springs
from ..console import Column, Reporter, format_number
from ..spec import build_model, load_spec

NAME = "sdm"
HELP = "structural dynamics modification (SDM) scans and predictions"


def add_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        NAME,
        help=HELP,
        description=(
            "Fast re-analysis in the modal domain: scan how added springs shift "
            "natural frequencies without rebuilding the full FE model."
        ),
    )
    sdm_sub = parser.add_subparsers(dest="sdm_command", metavar="SUBCOMMAND", required=True)
    scan_parser = sdm_sub.add_parser(
        "scan",
        help="scan a mode frequency vs. added spring stiffness at one DOF",
        description=(
            "Assemble the model, extract a retained modal basis, and predict how "
            "the selected mode frequency changes as a spring of increasing stiffness "
            "is added at one free DOF."
        ),
    )
    scan_parser.add_argument("model", help="path to the model specification (JSON or YAML)")
    scan_parser.add_argument(
        "--dof-index",
        type=int,
        required=True,
        metavar="I",
        help="free-DOF index where the spring is added (0-based)",
    )
    scan_parser.add_argument(
        "--stiffness",
        required=True,
        metavar="VALUES",
        help="comma-separated added spring stiffness values (same units as the model)",
    )
    scan_parser.add_argument(
        "-n",
        "--modes",
        type=int,
        default=6,
        help="number of modes retained in the SDM basis (default: 6)",
    )
    scan_parser.add_argument(
        "--mode-index",
        type=int,
        default=0,
        metavar="I",
        help="mode index whose frequency is reported (default: 0, the lowest mode)",
    )
    scan_parser.add_argument(
        "--format",
        choices=("table", "json", "yaml"),
        default="table",
        help="how to render the scan summary (default: table)",
    )
    scan_parser.set_defaults(func=_run_scan)
    parser.set_defaults(func=_dispatch)
    return parser


def _dispatch(args: argparse.Namespace, reporter: Reporter) -> int:
    return int(args.func(args, reporter))


def _run_scan(args: argparse.Namespace, reporter: Reporter) -> int:
    spec = load_spec(args.model)
    model = build_model(spec)
    solver = ModalSolver(model)
    result = solver.solve(num_modes=args.modes, sparse=False)
    stiffness, mass = solver.system.reduced()
    mode_shapes = result.mode_shapes[solver.system.free_dofs, : args.modes]
    stiffness_values = _parse_stiffness_values(args.stiffness)
    frequencies = scan_stiffness_springs(
        _dense(stiffness),
        _dense(mass),
        mode_shapes,
        dof_index=args.dof_index,
        stiffness_values=stiffness_values,
        mode_index=args.mode_index,
        num_modes=args.modes,
    )
    report = build_report(
        model=model,
        result=result,
        source=str(args.model),
        dof_index=args.dof_index,
        mode_index=args.mode_index,
        stiffness_values=stiffness_values,
        frequencies=frequencies,
    )

    if args.format == "table":
        render(report, reporter)
    else:
        reporter.document(report, format=args.format)
    return 0


def build_report(
    *,
    model,
    result,
    source: str,
    dof_index: int,
    mode_index: int,
    stiffness_values: list[float],
    frequencies: np.ndarray,
) -> dict[str, Any]:
    """Assemble the JSON-ready summary of one SDM stiffness scan."""
    baseline = float(result.frequencies[mode_index]) if result.num_modes else float("nan")
    scan = [
        {
            "stiffness": float(stiffness),
            "frequency_hz": float(frequency),
            "delta_hz": float(frequency - baseline),
        }
        for stiffness, frequency in zip(stiffness_values, frequencies, strict=True)
    ]
    return {
        "command": f"{NAME} scan",
        "source": source,
        "model": {
            "name": model.name,
            "nodes": model.num_nodes,
            "elements": model.num_elements,
            "dofs": model.num_dofs,
            "free_dofs": int(model.free_dofs.size),
            "constrained_dofs": int(model.constrained_dofs.size),
        },
        "analysis": {
            "num_modes": result.num_modes,
            "mode_index": mode_index,
            "baseline_frequency_hz": baseline,
            "dof_index": dof_index,
        },
        "scan": scan,
    }


def render(report: dict[str, Any], reporter: Reporter) -> None:
    model = report["model"]
    analysis = report["analysis"]
    reporter.heading(f"SDM stiffness scan: {model['name']}")
    reporter.fields(
        {
            "source": report["source"],
            "DOFs": f"{model['dofs']} ({model['free_dofs']} free, "
            f"{model['constrained_dofs']} constrained)",
            "retained modes": analysis["num_modes"],
            "reported mode": analysis["mode_index"] + 1,
            "spring DOF index": analysis["dof_index"],
            "baseline f": format_number(analysis["baseline_frequency_hz"]),
        }
    )
    columns = (
        Column("stiffness"),
        Column("f [Hz]"),
        Column("Δf [Hz]"),
    )
    rows = [
        (
            format_number(point["stiffness"]),
            format_number(point["frequency_hz"]),
            format_number(point["delta_hz"], 4),
        )
        for point in report["scan"]
    ]
    reporter.table(columns, rows)


def _parse_stiffness_values(raw: str) -> list[float]:
    parts = [part.strip() for part in str(raw).split(",") if part.strip()]
    if not parts:
        raise ValueError("stiffness list must not be empty")
    return [float(part) for part in parts]


def _dense(matrix) -> np.ndarray:
    array = matrix.toarray() if hasattr(matrix, "toarray") else np.asarray(matrix)
    return np.asarray(array, dtype=np.float64)
