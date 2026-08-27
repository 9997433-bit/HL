"""``openfemlab serve`` — local Web dashboard for correlation/correction JSON."""

from __future__ import annotations

import argparse
from pathlib import Path

from openfemlab.dashboard import serve_dashboard

from ..console import Reporter

NAME = "serve"
HELP = "open a local Web viewer for correlation and correction reports"
ALIASES = ("gui",)


def add_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        NAME,
        aliases=ALIASES,
        help=HELP,
        description=(
            "Start a small local Web server so you can review MAC matrices, mode pairing "
            "tables and correction summaries in a browser — similar to a CAE post-processor "
            "results pane. Upload a JSON file or load one from the project tree."
        ),
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="bind address (default: 127.0.0.1)",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8765,
        help="listen port (default: 8765)",
    )
    parser.add_argument(
        "--root",
        default=".",
        metavar="DIR",
        help="project root for server-side JSON paths (default: current directory)",
    )
    parser.add_argument(
        "-f",
        "--file",
        metavar="PATH",
        help="relative JSON path to open on startup (under --root)",
    )
    parser.add_argument(
        "-m",
        "--model",
        metavar="PATH",
        help="relative model spec path whose geometry backs the 3D mode-shape viewer",
    )
    parser.add_argument(
        "--desktop",
        action="store_true",
        help="open the dashboard in a native window (requires pywebview)",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="open the dashboard in the default browser",
    )
    parser.set_defaults(func=run)
    return parser


def run(args: argparse.Namespace, reporter: Reporter) -> int:
    root = Path(args.root).resolve()
    preset = args.file
    for label, relative in (("file", args.file), ("model", args.model)):
        if relative and not (root / relative).resolve().is_file():
            reporter.error(f"{label} not found under root: {relative}")
            return 1

    reporter.heading("OpenFEMLab dashboard")
    reporter.note(f"http://{args.host}:{args.port}/")
    reporter.hint("Upload JSON or load reports/corr.json from the toolbar.")
    if args.model:
        reporter.hint(f"3D mode shapes will use the geometry of {args.model}.")

    try:
        serve_dashboard(
            host=args.host,
            port=args.port,
            root=root,
            open_browser=args.open,
            desktop=args.desktop,
            preset_file=preset,
            preset_model=args.model,
        )
    except OSError as exc:
        reporter.error(f"cannot start server: {exc}")
        return 1
    return 0
