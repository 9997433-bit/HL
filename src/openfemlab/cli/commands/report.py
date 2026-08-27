"""``openfemlab report`` — browser-ready HTML from JSON correlation/correction artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from openfemlab.report.html import write_html_report

from ..console import Reporter

NAME = "report"
HELP = "render a correlation or correction JSON file as a self-contained HTML report"


def add_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        NAME,
        help=HELP,
        description=(
            "Turn a correlation or correction JSON artifact into a single HTML file "
            "you can open in a browser or attach to a review. No server required."
        ),
    )
    parser.add_argument("source", help="path to a correlation or correction JSON document")
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        metavar="PATH",
        help="where to write the HTML report",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="open the report in the default browser after writing (best-effort)",
    )
    parser.add_argument(
        "--no-plots",
        dest="plots",
        action="store_false",
        help=(
            "render the MAC matrix as an HTML table instead of an embedded "
            "Matplotlib PNG (the default when matplotlib is missing anyway)"
        ),
    )
    parser.set_defaults(func=run, plots=None)
    return parser


def run(args: argparse.Namespace, reporter: Reporter) -> int:
    source = Path(args.source)
    if not source.is_file():
        reporter.error(f"file not found: {source}")
        return 1
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        reporter.error("report JSON must be an object at the top level")
        return 1

    destination = Path(args.output)
    kind = write_html_report(payload, destination, embed_plots=args.plots)
    reporter.success(f"Wrote {kind} report → {destination}")
    reporter.hint("Share the HTML file or open it locally for review.")

    if args.open:
        import webbrowser

        webbrowser.open(destination.resolve().as_uri())

    return 0
