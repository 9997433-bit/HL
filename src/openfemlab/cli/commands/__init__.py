"""Subcommand implementations of the ``openfemlab`` console script.

Each module exposes ``add_parser(subparsers)`` to declare its arguments and
``run(args, reporter)`` to execute, so :mod:`openfemlab.cli.main` stays a
registry rather than a dispatcher full of analysis code.
"""

from __future__ import annotations

from . import correlate, correlate_frf, modal, update

#: Registration order, which is also the order shown by ``openfemlab --help``.
COMMANDS = (modal, correlate, correlate_frf, update)

__all__ = ["COMMANDS", "correlate", "correlate_frf", "modal", "update"]
