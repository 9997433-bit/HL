"""Locate solver output artifacts and load displacement fields."""

from __future__ import annotations

from os import PathLike
from pathlib import Path

from ._common import FormatError
from .external_result import ExternalResult
from .frd import read_frd

__all__ = [
    "ResultLocator",
    "locate_results",
    "read_solver_result",
]

_PRIORITY = (
    ("op2", (".op2",)),
    ("frd", (".frd",)),
    ("rst", (".rst",)),
    ("odb", (".odb",)),
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

    def load(self, kind: str | None = None) -> ExternalResult:
        """Load the best matching displacement result in ``directory``."""
        if kind is None:
            for key, _ in _PRIORITY:
                path = self.get(key)
                if path is not None:
                    return read_solver_result(path)
            raise FileNotFoundError(f"no supported result file under {self.directory}")
        return read_solver_result(self.require(kind))

    def to_dict(self) -> dict[str, str]:
        return {key: str(path) for key, path in self.matches.items()}


def locate_results(directory: str | PathLike[str]) -> ResultLocator:
    """Return a :class:`ResultLocator` for ``directory``."""
    return ResultLocator(directory)


def read_solver_result(source: str | PathLike[str]) -> ExternalResult:
    """Read nodal displacements from FRD/RST/ODB (or ODB sidecar NPZ)."""
    path = Path(source).resolve()
    suffix = path.suffix.lower()
    if suffix == ".frd":
        frd = read_frd(path)
        return ExternalResult(
            node_ids=frd.node_ids,
            coordinates=frd.coordinates,
            displacements=frd.displacements,
            format=frd.meta.get("format", "calculix-frd"),
            meta=dict(frd.meta),
        )
    if suffix == ".rst":
        from .rst import read_rst

        return read_rst(path)
    if suffix in {".odb", ".npz"} or path.name.endswith(".odb.openfemlab.npz"):
        from .odb import read_odb

        return read_odb(path)
    raise FormatError(
        f"unsupported solver result {path.name!r}; expected .frd, .rst, .odb or .npz"
    )
