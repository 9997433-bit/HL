"""``openfemlab desktop`` — native desktop CAE shell."""

from __future__ import annotations

import argparse
from pathlib import Path

from openfemlab.dashboard import desktop_available, serve_dashboard

from ..console import Reporter

NAME = "desktop"
HELP = "launch the OpenFEMLab desktop CAE shell (project tree + workflows + viewer)"


def add_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        NAME,
        help=HELP,
        description=(
            "Open the OpenFEMLab desktop application: a native window with a project "
            "navigator, one-click workflows (modal, correlate, update, topopt), a job "
            "console, and the existing 3D results viewer."
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
        help="project root (default: current directory)",
    )
    parser.add_argument(
        "-f",
        "--file",
        metavar="PATH",
        help="relative JSON report to open on startup (under --root)",
    )
    parser.add_argument(
        "-m",
        "--model",
        metavar="PATH",
        help="relative model spec for the 3D viewer on startup",
    )
    parser.add_argument(
        "--browser",
        action="store_true",
        help="open the desktop UI in a browser instead of a native window",
    )
    parser.set_defaults(func=run)
    return parser


def run(args: argparse.Namespace, reporter: Reporter) -> int:
    if not args.browser and not desktop_available():
        reporter.error(
            "desktop mode requires pywebview; install with "
            "'pip install openfemlab[gui]' or pass --browser"
        )
        return 1

    root = Path(args.root).resolve()
    for label, relative in (("file", args.file), ("model", args.model)):
        if relative and not (root / relative).resolve().is_file():
            reporter.error(f"{label} not found under root: {relative}")
            return 1

    reporter.heading("OpenFEMLab desktop")
    reporter.note(f"Project root: {root}")
    reporter.hint("Use the sidebar to run modal → correlate → update workflows.")
    if not (root / "project.yaml").is_file():
        reporter.hint("Tip: run 'openfemlab project init' in this folder first.")

    try:
        serve_dashboard(
            host=args.host,
            port=args.port,
            root=root,
            open_browser=args.browser,
            desktop=not args.browser,
            preset_file=args.file,
            preset_model=args.model,
        )
    except OSError as exc:
        reporter.error(f"cannot start desktop shell: {exc}")
        return 1
    return 0
