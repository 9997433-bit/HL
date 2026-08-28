"""Subcommand implementations of the ``openfemlab`` console script.

Each module exposes ``add_parser(subparsers)`` to declare its arguments and
``run(args, reporter)`` to execute, so :mod:`openfemlab.cli.main` stays a
registry rather than a dispatcher full of analysis code.
"""

from __future__ import annotations

from . import (
    align,
    bench,
    correlate,
    correlate_frf,
    modal,
    mpe,
    pipeline,
    project,
    quickstart,
    reduce,
    report,
    sdm,
    serve,
    static,
    topopt,
    update,
    wizard,
)

#: Registration order, which is also the order shown by ``openfemlab --help``.
COMMANDS = (
    quickstart,
    wizard,
    project,
    serve,
    bench,
    modal,
    static,
    topopt,
    reduce,
    mpe,
    sdm,
    pipeline,
    correlate,
    correlate_frf,
    align,
    update,
    report,
)

__all__ = [
    "COMMANDS",
    "align",
    "bench",
    "correlate",
    "correlate_frf",
    "modal",
    "mpe",
    "pipeline",
    "project",
    "quickstart",
    "reduce",
    "report",
    "sdm",
    "serve",
    "static",
    "topopt",
    "update",
    "wizard",
]
