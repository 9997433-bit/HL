"""Terminal rendering shared by the CLI commands.

``rich`` (the optional ``[cli]`` extra) draws boxed tables and colour. Without
it the very same content is emitted as aligned plain text, so a CI log or a
piped report stays readable and diffable. Callers never pass rich markup;
:class:`Reporter` owns every styling decision so both back ends agree.
"""

from __future__ import annotations

import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, TextIO

__all__ = ["Column", "Reporter", "format_number", "format_percent"]

try:  # pragma: no cover - exercised by whichever branch the environment has
    from rich.console import Console as _RichConsole
    from rich.table import Table as _RichTable

    RICH_AVAILABLE = True
except ImportError:  # pragma: no cover - plain-text fallback
    RICH_AVAILABLE = False


@dataclass(frozen=True)
class Column:
    """One report column: a header plus its horizontal alignment."""

    header: str
    justify: str = "right"


def format_number(value: Any, digits: int = 6) -> str:
    """Format a scalar for a report cell, keeping ``inf``/``nan`` readable."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number != number:  # NaN
        return "nan"
    if number in (float("inf"), float("-inf")):
        return "inf" if number > 0 else "-inf"
    return f"{number:.{digits}g}"


def format_percent(value: Any, digits: int = 3) -> str:
    """Format a percentage with an explicit sign so trends read at a glance."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number != number or number in (float("inf"), float("-inf")):
        return format_number(number)
    return f"{number:+.{digits}f}"


class Reporter:
    """Writes command output as rich tables or aligned plain text.

    Parameters
    ----------
    stream:
        Destination, ``sys.stdout`` by default.
    color:
        Set to False to disable rich rendering entirely (``--no-color``).
    quiet:
        Suppress everything except tables and explicitly requested documents.
    """

    def __init__(
        self,
        stream: TextIO | None = None,
        *,
        color: bool = True,
        quiet: bool = False,
    ) -> None:
        self.stream = stream if stream is not None else sys.stdout
        self.quiet = quiet
        self._console = None
        if color and RICH_AVAILABLE:
            self._console = _RichConsole(file=self.stream, highlight=False, soft_wrap=True)

    @property
    def rich(self) -> bool:
        """True when output is rendered through rich."""
        return self._console is not None

    # ----------------------------------------------------------------- text

    def line(self, text: str = "") -> None:
        print(text, file=self.stream)

    def heading(self, text: str) -> None:
        if self.quiet:
            return
        if self._console is not None:
            self._console.rule(f"[bold]{text}[/bold]")
            return
        self.line()
        self.line(text)
        self.line("=" * len(text))

    def note(self, text: str) -> None:
        if self.quiet:
            return
        if self._console is not None:
            self._console.print(text, style="dim")
            return
        self.line(text)

    def warning(self, text: str) -> None:
        if self._console is not None:
            self._console.print(f"warning: {text}", style="yellow")
            return
        print(f"warning: {text}", file=self.stream)

    def error(self, text: str) -> None:
        target = sys.stderr
        if self._console is not None:
            _RichConsole(file=target, highlight=False).print(f"error: {text}", style="bold red")
            return
        print(f"error: {text}", file=target)

    # --------------------------------------------------------------- tables

    def table(
        self,
        columns: Sequence[Column],
        rows: Iterable[Sequence[str]],
        *,
        title: str | None = None,
        caption: str | None = None,
    ) -> None:
        """Render ``rows`` under ``columns``; cells must already be strings."""
        materialized = [list(row) for row in rows]
        if self._console is not None:
            table = _RichTable(title=title, caption=caption, header_style="bold cyan")
            for column in columns:
                table.add_column(column.header, justify=column.justify)
            for row in materialized:
                table.add_row(*row)
            self._console.print(table)
            return

        widths = [len(column.header) for column in columns]
        for row in materialized:
            for index, cell in enumerate(row):
                widths[index] = max(widths[index], len(cell))
        if title:
            self.line(title)
        self.line(
            "  ".join(
                _pad(c.header, w, "left") for c, w in zip(columns, widths, strict=False)
            )
        )
        self.line("  ".join("-" * width for width in widths))
        for row in materialized:
            self.line(
                "  ".join(
                    _pad(cell, width, column.justify)
                    for cell, width, column in zip(row, widths, columns, strict=False)
                )
            )
        if caption:
            self.line(caption)

    def fields(self, items: Mapping[str, Any], *, title: str | None = None) -> None:
        """Render a ``label: value`` block, e.g. a run summary."""
        if self.quiet:
            return
        pairs = [(str(key), str(value)) for key, value in items.items()]
        if not pairs:
            return
        if title:
            if self._console is None:
                self.line(title)
            else:
                self._console.print(f"[bold]{title}[/bold]")
        width = max(len(key) for key, _ in pairs)
        for key, value in pairs:
            text = f"{key.ljust(width)} : {value}"
            if self._console is not None:
                self._console.print(text)
            else:
                self.line(text)

    # ------------------------------------------------------------ documents

    def document(self, payload: Any, *, format: str) -> None:
        """Dump a report mapping as JSON or YAML on the output stream."""
        from openfemlab.io import write_data

        write_data(payload, self.stream, format=format)


def _pad(text: str, width: int, justify: str) -> str:
    if justify == "right":
        return text.rjust(width)
    if justify == "center":
        return text.center(width)
    return text.ljust(width)
