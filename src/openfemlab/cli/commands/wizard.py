"""``openfemlab wizard`` — interactive menu for common workflows."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..console import Reporter

NAME = "wizard"
HELP = "guided menu for modal analysis, correlation, and HTML reports"


def add_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        NAME,
        help=HELP,
        description=(
            "A text menu for engineers who prefer prompts over memorizing subcommands. "
            "Each choice runs the same CLI you would type manually, so scripts and CI "
            "stay unchanged."
        ),
    )
    parser.set_defaults(func=run)
    return parser


def run(args: argparse.Namespace, reporter: Reporter) -> int:
    reporter.heading("OpenFEMLab wizard")
    reporter.note("Pick a workflow — empty input cancels.")

    while True:
        reporter.line()
        reporter.line("  1  Run the 60-second quickstart demo")
        reporter.line("  2  Modal analysis (YAML/JSON model file)")
        reporter.line("  3  Correlate model vs measured modal data")
        reporter.line("  4  Update model parameters from measurements")
        reporter.line("  5  Build an HTML report from a JSON artifact")
        reporter.line("  6  Show command cheat sheet")
        reporter.line("  0  Exit")
        choice = _prompt("Choice", reporter)

        if choice in ("0", "q", "quit", "exit"):
            reporter.success("Goodbye.")
            return 0
        if choice == "1":
            return _delegate(["quickstart"], reporter)
        if choice == "2":
            model = _prompt("Model spec path", reporter)
            if not model:
                continue
            modes = _prompt("Number of modes [6]", reporter) or "6"
            return _delegate(["modal", model, "-n", modes], reporter)
        if choice == "3":
            model = _prompt("Model spec path", reporter)
            test = _prompt("Measured data path", reporter)
            if not model or not test:
                continue
            out = _prompt("Save correlation JSON (optional)", reporter)
            cmd = ["correlate", model, test, "--format", "json"]
            if out:
                cmd.extend(["-o", out])
            code = _delegate(cmd, reporter)
            if code == 0 and out:
                reporter.hint(f"openfemlab report {out} -o {Path(out).stem}.html")
            return code
        if choice == "4":
            spec = _prompt("Updating spec path", reporter)
            if not spec:
                continue
            out = _prompt("Output model spec (optional)", reporter)
            cmd = ["update", spec]
            if out:
                cmd.extend(["-o", out])
            return _delegate(cmd, reporter)
        if choice == "5":
            source = _prompt("Report JSON path", reporter)
            if not source:
                continue
            dest = _prompt("HTML output path", reporter) or f"{Path(source).stem}.html"
            return _delegate(["report", source, "-o", dest], reporter)
        if choice == "6":
            _cheat_sheet(reporter)
            continue
        reporter.warning(f"Unknown choice: {choice!r}")


def _prompt(label: str, reporter: Reporter) -> str:
    print(f"{label}: ", end="", file=reporter.stream, flush=True)
    try:
        return input().strip()
    except EOFError:
        reporter.line()
        return ""


def _delegate(argv: list[str], reporter: Reporter) -> int:
    from ..main import main as cli_main

    reporter.note(f"Running: openfemlab {' '.join(argv)}")
    return int(cli_main(argv))


def _cheat_sheet(reporter: Reporter) -> None:
    reporter.heading("CLI cheat sheet")
    lines = [
        "openfemlab quickstart",
        "openfemlab modal model.yaml -n 8",
        "openfemlab correlate model.yaml measured.yaml",
        "openfemlab correlate model.yaml measured.yaml -o report.json --format json",
        "openfemlab report report.json -o report.html",
        "openfemlab update updating.yaml -o model.updated.yaml",
        "openfemlab correlate-frf measured.unv model.yaml",
        "openfemlab info",
        "pip install 'openfemlab[cli,plot,io]'  # rich + matplotlib + meshio",
    ]
    for line in lines:
        reporter.line(f"  {line}")
