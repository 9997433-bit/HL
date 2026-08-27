"""Subcommand implementations of the ``openfemlab`` console script.

Each module exposes ``add_parser(subparsers)`` to declare its arguments and
``run(args, reporter)`` to execute, so :mod:`openfemlab.cli.main` stays a
registry rather than a dispatcher full of analysis code.
"""

from __future__ import annotations

from . import (
    correlate,
    correlate_frf,
    modal,
    project,
    quickstart,
    report,
    serve,
    update,
    wizard,
)

#: Registration order, which is also the order shown by ``openfemlab --help``.
COMMANDS = (
    quickstart,
    wizard,
    project,
    serve,
    modal,
    correlate,
    correlate_frf,
    update,
    report,
)

__all__ = [
    "COMMANDS",
    "correlate",
    "correlate_frf",
    "modal",
    "project",
    "quickstart",
    "report",
    "serve",
    "update",
    "wizard",
]
