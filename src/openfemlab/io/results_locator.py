"""Locate solver output artifacts in a working directory."""

from __future__ import annotations

from os import PathLike
from pathlib import Path

__all__ = [
    "ResultLocator",
    "locate_results",
]

_PRIORITY = (
    ("op2", (".op2",)),
    ("frd", (".frd",)),
    ("odb", (".odb",)),
    ("rst", (".rst",)),
    ("fil", (".fil",)),
)


class ResultLocator:
    """Best-effort discovery of external solver result files."""

    __slots__ = ("directory", "matches")

    def __init__(self, directory: str | PathLike[str]) -> None:
        root = Path(directory).resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"result directory not found: {root}")
        self.directory = root
        self.matches: dict[str, Path] = {}
        for stem in sorted(p for p in root.iterdir() if p.is_file()):
            lowered = stem.name.lower()
            for key, suffixes in _PRIORITY:
                if any(lowered.endswith(suffix) for suffix in suffixes):
                    self.matches.setdefault(key, stem)

    def get(self, kind: str) -> Path | None:
        return self.matches.get(kind.lower())

    def require(self, kind: str) -> Path:
        path = self.get(kind)
        if path is None:
            raise FileNotFoundError(
                f"no {kind.upper()} result found under {self.directory}"
            )
        return path

    def to_dict(self) -> dict[str, str]:
        return {key: str(path) for key, path in self.matches.items()}


def locate_results(directory: str | PathLike[str]) -> ResultLocator:
    """Return a :class:`ResultLocator` for ``directory``."""
    return ResultLocator(directory)
