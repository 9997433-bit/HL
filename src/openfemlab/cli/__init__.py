"""Command-line interface layer (L4).

Entry point of the ``openfemlab`` console script declared in
``pyproject.toml``. Built on stdlib ``argparse`` for structure and ``rich``
(the optional ``[cli]`` extra) for presentation, with a plain-text fallback so
CI logs stay usable when rich is absent.

The CLI reads a declarative model specification (see
:mod:`openfemlab.cli.spec`) rather than a Python script, which is what makes a
modal run, a correlation report and an updating session reproducible from a
single version-controlled file.
"""

from openfemlab.cli.main import build_parser, main

__all__ = ["build_parser", "main"]
