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
        "--open",
        action="store_true",
        help="open the dashboard in the default browser",
    )
    parser.set_defaults(func=run)
    return parser


def run(args: argparse.Namespace, reporter: Reporter) -> int:
    root = Path(args.root).resolve()
    preset = args.file
    if preset:
        preset_path = (root / preset).resolve()
        if not preset_path.is_file():
            reporter.error(f"file not found under root: {preset}")
            return 1

    reporter.heading("OpenFEMLab dashboard")
    reporter.note(f"http://{args.host}:{args.port}/")
    reporter.hint("Upload JSON or load reports/corr.json from the toolbar.")

    try:
        serve_dashboard(
            host=args.host,
            port=args.port,
            root=root,
            open_browser=args.open,
            preset_file=preset,
        )
    except OSError as exc:
        reporter.error(f"cannot start server: {exc}")
        return 1
    return 0
