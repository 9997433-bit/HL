"""``openfemlab mpe extract`` -- experimental modal extraction from measured FRFs."""

from __future__ import annotations

import argparse

from ...io.uff import read_uff_functions
from ...io.uff_frf import uff_functions_to_frf
from ...mpe import extract_modes
from ..console import Column, Reporter, format_number

NAME = "mpe"
HELP = "experimental modal parameter extraction from measured FRF data"


def add_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(NAME, help=HELP, description=HELP)
    sub = parser.add_subparsers(dest="mpe_command", metavar="SUBCOMMAND", required=True)
    extract = sub.add_parser(
        "extract",
        help="fit modal parameters from a UFF/UNV dataset-58 file",
    )
    extract.add_argument("frf", help="measured FRF file (UFF/UNV dataset 58)")
    extract.add_argument(
        "--orders",
        default="4:18:2",
        help="model-order sweep as start:stop:step (default: 4:18:2)",
    )
    extract.add_argument(
        "--band",
        nargs=2,
        type=float,
        metavar=("F_LO", "F_HI"),
        default=None,
        help="physical frequency band in Hz",
    )
    extract.add_argument(
        "--format",
        choices=("table", "json", "yaml"),
        default="table",
        help="render format (default: table)",
    )
    extract.add_argument(
        "-o",
        "--output",
        default=None,
        metavar="PATH",
        help="write extracted modal model as JSON/YAML",
    )
    extract.set_defaults(func=run_extract)
    return parser


def run_extract(args: argparse.Namespace, reporter: Reporter) -> int:
    functions = read_uff_functions(args.frf)
    if not functions:
        raise ValueError(f"no dataset-58 records found in {args.frf}")
    frf = uff_functions_to_frf(functions)
    orders = _parse_orders(args.orders)
    band = tuple(args.band) if args.band is not None else None
    result = extract_modes(frf, orders, band=band)
    report = {
        "kind": "mpe",
        "source": str(args.frf),
        "num_functions": len(functions),
        "orders": list(orders),
        "band_hz": list(band) if band is not None else None,
        "poles": [
            {
                "frequency_hz": float(pole.frequency_hz),
                "damping_ratio": float(pole.damping_ratio),
                "stable": bool(getattr(pole, "stable", True)),
            }
            for pole in result.poles
        ],
    }
    if args.format == "table":
        reporter.heading("MPE extraction")
        reporter.fields(
            {
                "source": report["source"],
                "functions": report["num_functions"],
                "poles": len(report["poles"]),
            }
        )
        if report["poles"]:
            reporter.table(
                (
                    Column("mode", justify="right"),
                    Column("f [Hz]", justify="right"),
                    Column("zeta", justify="right"),
                ),
                [
                    (
                        index + 1,
                        format_number(row["frequency_hz"]),
                        format_number(row["damping_ratio"]),
                    )
                    for index, row in enumerate(report["poles"])
                ],
            )
    else:
        reporter.document(report, format=args.format)
    if args.output:
        from ...io import write_data

        write_data(report, args.output)
        reporter.note(f"MPE report written to {args.output}")
    return 0


def _parse_orders(spec: str) -> range:
    parts = [int(token) for token in str(spec).split(":")]
    if len(parts) == 1:
        return range(parts[0], parts[0] + 1)
    if len(parts) == 2:
        start, stop = parts
        return range(start, stop + 1)
    start, stop, step = parts
    return range(start, stop + 1, step)
