"""Subcommand implementations of the ``openfemlab`` console script.

Each module exposes ``add_parser(subparsers)`` to declare its arguments and
``run(args, reporter)`` to execute, so :mod:`openfemlab.cli.main` stays a
registry rather than a dispatcher full of analysis code.
"""

from __future__ import annotations

from . import correlate, modal, update

#: Registration order, which is also the order shown by ``openfemlab --help``.
COMMANDS = (modal, correlate, update)

__all__ = ["COMMANDS", "correlate", "modal", "update"]
