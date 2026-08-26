"""``openfemlab correlate`` -- FE versus test modal correlation report."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from typing import Any

import numpy as np

from ..analysis import as_modal_result, solve_spec
from ..console import Column, Reporter, format_number, format_percent
from ..spec import SpecError

NAME = "correlate"
HELP = "correlate FE modes against measured test data"

PAIRING_METHODS = ("greedy", "optimal", "frequency")

#: Exit code used when the acceptance gates are not met, so CI can act on it.
CORRELATION_FAILED = 3


def add_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        NAME,
        help=HELP,
        description=(
            "Pair FE modes with measured modes on the DOFs their maps share and "
            "report MAC values, frequency deviations and COMAC. The FE side may be "
            "a native modal result file or a model specification, which is then "
            "solved first."
        ),
    )
    parser.add_argument("fe", help="FE modal result file, or a model specification to solve")
    parser.add_argument("test", help="measured modal data (JSON or YAML)")
    parser.add_argument(
        "-n",
        "--modes",
        type=int,
        default=10,
        help="number of FE modes to extract when 'fe' is a model spec (default: 10)",
    )
    parser.add_argument(
        "--pairing",
        choices=PAIRING_METHODS,
        default="greedy",
        help="mode matching strategy (default: greedy)",
    )
    parser.add_argument(
        "--mac-threshold",
        type=float,
        default=0.0,
        help="reject pairs whose MAC falls below this value (default: 0.0)",
    )
    parser.add_argument(
        "--frequency-tolerance",
        type=float,
        default=None,
        metavar="PCT",
        help="reject pairs deviating by more than this percentage",
    )
    parser.add_argument(
        "--freq-penalty",
        type=float,
        default=0.0,
        help="weight of the frequency distance in the pairing score (MS-2.3 suggests 0.1)",
    )
    parser.add_argument(
        "--partial-dofs",
        action="store_true",
        help="tolerate test channels that have no counterpart in the model",
    )
    parser.add_argument(
        "--matrix", action="store_true", help="also print the full MAC matrix"
    )
    parser.add_argument(
        "--require-mac",
        type=float,
        default=None,
        metavar="MAC",
        help=f"exit with status {CORRELATION_FAILED} when a paired MAC falls below this",
    )
    parser.add_argument(
        "--require-frequency",
        type=float,
        default=None,
        metavar="PCT",
        help=f"exit with status {CORRELATION_FAILED} when a frequency error exceeds this",
    )
    parser.add_argument(
        "--format",
        choices=("table", "json", "yaml"),
        default="table",
        help="how to render the report (default: table)",
    )
    parser.add_argument(
        "-o", "--output", default=None, metavar="PATH", help="write the report to a JSON/YAML file"
    )
    parser.set_defaults(func=run)
    return parser


def run(args: argparse.Namespace, reporter: Reporter) -> int:
    from ...correlation import correlate_modal_data
    from ...io import read_test_data

    fe = load_fe_modes(args.fe, num_modes=args.modes)
    test = read_test_data(args.test)

    correlation = correlate_modal_data(
        fe,
        test,
        strict=not args.partial_dofs,
        method=args.pairing,
        mac_threshold=args.mac_threshold,
        frequency_tolerance_pct=args.frequency_tolerance,
        freq_penalty=args.freq_penalty,
    )
    report = build_report(
        correlation, fe_source=str(args.fe), test_source=str(args.test), fe=fe, test=test
    )

    if args.format == "table":
        render(report, reporter, show_matrix=args.matrix)
    else:
        reporter.document(report, format=args.format)

    if args.output:
        from ...io import write_data

        write_data(report, args.output)
        reporter.note(f"correlation report written to {args.output}")

    return _acceptance(correlation, args, reporter)


def load_fe_modes(source: str, *, num_modes: int):
    """Read FE modes from a native result file, or solve a model spec for them."""
    from ...io import modal_result_from_dict, read_data

    document = read_data(source)
    if not isinstance(document, Mapping):
        raise SpecError(f"{source}: expected a mapping document")
    if _is_modal_result(document):
        return modal_result_from_dict(document)
    model, result = solve_spec(dict(document), num_modes=num_modes)
    return as_modal_result(model, result, meta={"source": source})


def _is_modal_result(document: Mapping[str, Any]) -> bool:
    object_type = str(document.get("object_type", document.get("type", ""))).lower()
    if object_type:
        return object_type in {"modal", "modal_result"}
    if "analytical" in document:
        return True
    return "frequencies_hz" in document or "frequencies" in document


def build_report(correlation, *, fe_source: str, test_source: str, fe, test) -> dict[str, Any]:
    """Wrap a :class:`~openfemlab.correlation.report.CorrelationReport` for the CLI."""
    document = correlation.to_dict()
    document.update(
        {
            "command": NAME,
            "fe": {
                "source": fe_source,
                "modes": int(fe.frequencies.size),
                "dofs": int(fe.dof_map.ndof),
            },
            "test": {
                "source": test_source,
                "modes": int(test.frequencies.size),
                "dofs": int(test.dof_map.ndof),
            },
        }
    )
    return document


def render(report: dict[str, Any], reporter: Reporter, *, show_matrix: bool = False) -> None:
    summary = report["summary"]
    meta = report.get("meta", {})
    reporter.heading("FE / test correlation")
    reporter.fields(
        {
            "FE modes": f"{report['fe']['modes']} from {report['fe']['source']}",
            "test modes": f"{report['test']['modes']} from {report['test']['source']}",
            "correlation DOFs": meta.get("n_correlation_dofs", "-"),
            "pairing": report["pairing_method"],
        }
    )

    columns = (
        Column("test"),
        Column("f_test [Hz]"),
        Column("FE"),
        Column("f_FE [Hz]"),
        Column("df [%]"),
        Column("MAC"),
    )
    rows = [
        (
            str(pair["test_index"] + 1),
            format_number(pair["test_frequency"]),
            str(pair["fe_index"] + 1),
            format_number(pair["fe_frequency"]),
            format_percent(pair["frequency_error_pct"]),
            format_number(pair["mac"], 4),
        )
        for pair in report["pairs"]
    ]
    if rows:
        reporter.table(columns, rows)
    else:
        reporter.warning("no mode pair satisfied the pairing criteria")

    reporter.fields(
        {
            "paired modes": summary["n_paired"],
            "mean / min MAC": f"{format_number(summary['mean_mac'], 4)} / "
            f"{format_number(summary['min_mac'], 4)}",
            "mean |df| [%]": format_number(summary["mean_abs_freq_error_pct"], 4),
            "max |df| [%]": format_number(summary["max_abs_freq_error_pct"], 4),
            "rms df [%]": format_number(summary["rms_freq_error_pct"], 4),
            "worst off-diagonal MAC": format_number(summary["max_off_diagonal_mac"], 4),
        },
        title="Summary",
    )
    for label, unpaired in (("test", report["unpaired_test"]), ("FE", report["unpaired_fe"])):
        if unpaired:
            reporter.warning(
                f"unpaired {label} modes: {', '.join(str(index + 1) for index in unpaired)}"
            )

    comac = report.get("comac")
    if comac:
        worst = int(np.argmin(comac))
        labels = report.get("dof_labels")
        name = labels[worst] if labels else f"dof {worst}"
        reporter.note(f"worst COMAC DOF: {name} ({format_number(comac[worst], 4)})")

    if show_matrix and report.get("mac_matrix") is not None:
        macs = np.asarray(report["mac_matrix"], dtype=float)
        matrix_columns = (Column("test \\ FE", justify="left"),) + tuple(
            Column(str(j + 1)) for j in range(macs.shape[1])
        )
        matrix_rows = [
            (str(i + 1), *(format_number(value, 3) for value in macs[i, :]))
            for i in range(macs.shape[0])
        ]
        reporter.table(matrix_columns, matrix_rows, title="MAC matrix")


def _acceptance(correlation, args: argparse.Namespace, reporter: Reporter) -> int:
    """Apply the ``--require-*`` gates and translate them into an exit code."""
    summary = correlation.summary
    failures = []
    if args.require_mac is not None:
        if summary.n_paired == 0 or summary.min_mac < args.require_mac:
            failures.append(
                f"lowest paired MAC {format_number(summary.min_mac, 4)} is below the "
                f"required {format_number(args.require_mac, 4)}"
            )
    if args.require_frequency is not None:
        if summary.n_paired == 0 or summary.max_abs_freq_error_pct > args.require_frequency:
            failures.append(
                f"largest frequency error {format_number(summary.max_abs_freq_error_pct, 4)}% "
                f"exceeds the allowed {format_number(args.require_frequency, 4)}%"
            )
    for message in failures:
        reporter.error(message)
    return CORRELATION_FAILED if failures else 0
