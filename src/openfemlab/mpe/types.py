"""Result types of the M9 modal-parameter-extraction module (spec MS-10).

:class:`PoleEstimate` is one root of an MS-10.2 fit carrying its MS-10.3
stabilization label, :class:`StabilizationDiagram` collects those roots over
the fitted model orders and implements the automatic pole pick, and
:class:`MPEResult` is the MS-10.5 result contract together with the
``to_test_data`` bridge into the M2 correlation input.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
import numpy.typing as npt

from ..exceptions import MPEError

if TYPE_CHECKING:  # pragma: no cover
    from openfemlab.core.dofs import DofMap
    from openfemlab.core.results import TestData

__all__ = ["PoleEstimate", "StabilizationDiagram", "MPEResult"]

#: Stabilization labels of MS-10.3, in increasing order of stability.
POLE_LABELS = ("new", "freq", "damp", "stable")

#: The label a pole must carry to take part in an alignment (MS-10.3).
FULLY_STABLE = "stable"


@dataclass(frozen=True)
class PoleEstimate:
    """One pole of an MS-10.2 fit, classified per MS-10.3.

    ``pole`` is the continuous-time ``s_r = -zeta_r omega_r + i omega_d,r``
    already mapped back from the z-domain companion eigenvalue;
    ``participation`` is the reference participation column the
    poly-reference denominator carries (``None`` for the single-reference
    common-denominator path).
    """

    frequency_hz: float
    damping_ratio: float
    pole: complex
    order: int
    participation: npt.NDArray[np.complex128] | None = None
    label: str = "new"


@dataclass(frozen=True)
class StabilizationDiagram:
    """Per-order pole lists with MS-10.3 labels, plus the settings used.

    Serializable so a notebook or GUI renders it without refitting;
    ``poles[i]`` holds the classified poles fitted at ``orders[i]``.
    """

    orders: tuple[int, ...]
    poles: tuple[tuple[PoleEstimate, ...], ...]
    settings: dict[str, Any] = field(default_factory=dict)

    def select(self, *, min_count: int = 3) -> tuple[PoleEstimate, ...]:
        """Automatic pole pick of MS-10.3.

        An *alignment* is a chain of poles at consecutive orders, each linked
        to the nearest pole of the order below (the link the classification
        already established). The pick returns the lowest-order fully stable
        member of every alignment that stays fully stable over at least
        ``min_count`` consecutive orders, sorted by frequency.

        Raises :class:`~openfemlab.exceptions.MPEError` when no alignment
        qualifies — a diagram with nothing to pick from is a failure, not an
        empty answer.
        """
        if min_count < 1:
            raise MPEError(f"min_count must be >= 1, got {min_count}")
        runs = self._stable_runs()
        selected: dict[tuple[int, int], PoleEstimate] = {}
        for (level, index), length in runs.items():
            if length < min_count:
                continue
            if self._has_stable_child(runs, level, index):
                continue
            start = self._walk_back(level, index, length - 1)
            selected[start] = self.poles[start[0]][start[1]]
        if not selected:
            raise MPEError(
                f"no alignment stays fully stable over {min_count} consecutive "
                f"orders in a diagram of orders {list(self.orders)}; loosen the "
                "tolerances, widen the order range, or pick poles explicitly"
            )
        picked = sorted(selected.values(), key=lambda p: (p.frequency_hz, p.damping_ratio))
        return tuple(picked)

    # ------------------------------------------------------------- internals

    def _parent(self, level: int, index: int) -> int | None:
        """Index of the pole one order below this one was classified against."""
        links = self.settings.get("links", ())
        if level >= len(links):
            return None
        parent = links[level][index]
        return None if parent < 0 else int(parent)

    def _stable_runs(self) -> dict[tuple[int, int], int]:
        """Length of the fully stable run ending at each pole."""
        runs: dict[tuple[int, int], int] = {}
        for level, poles in enumerate(self.poles):
            for index, pole in enumerate(poles):
                if pole.label != FULLY_STABLE:
                    continue
                parent = self._parent(level, index)
                previous = runs.get((level - 1, parent), 0) if parent is not None else 0
                runs[(level, index)] = previous + 1
        return runs

    def _has_stable_child(
        self, runs: dict[tuple[int, int], int], level: int, index: int
    ) -> bool:
        """True when a pole one order up continues this alignment."""
        if level + 1 >= len(self.poles):
            return False
        return any(
            self._parent(level + 1, child) == index
            for child in range(len(self.poles[level + 1]))
            if (level + 1, child) in runs
        )

    def _walk_back(self, level: int, index: int, steps: int) -> tuple[int, int]:
        for _ in range(steps):
            parent = self._parent(level, index)
            if parent is None:  # pragma: no cover - run length guarantees a parent
                break
            level, index = level - 1, parent
        return level, index


@dataclass(frozen=True)
class MPEResult:
    """Extracted experimental modal model (MS-10.5 result contract).

    ``shapes`` lives in channel space (``s`` response channels x ``n``
    modes), ``participation`` in reference space (``e x n``), and ``frac``
    is the per-channel resynthesis quality of MS-10.4.
    """

    frequencies_hz: npt.NDArray[np.float64]
    damping_ratios: npt.NDArray[np.float64]
    poles: npt.NDArray[np.complex128]
    shapes: npt.NDArray[np.complex128]
    participation: npt.NDArray[np.complex128]
    frac: npt.NDArray[np.float64]
    diagnostics: dict[str, Any] = field(default_factory=dict)

    @property
    def num_modes(self) -> int:
        return int(self.frequencies_hz.size)

    def to_test_data(self, dof_map: DofMap) -> TestData:
        """Bridge to the M2 correlation input (MS-10.5).

        The returned :class:`~openfemlab.core.results.TestData` carries the
        extracted shapes on the channels ``dof_map`` names, the modal damping
        ratios, and a ``meta`` provenance record (method, orders, band,
        tolerances, scaling) so a measurement enters M2/M3/M4 exactly as a
        pre-extracted mode table does.
        """
        from ..core.results import TestData

        if dof_map is None or dof_map.ndof != self.shapes.shape[0]:
            found = "None" if dof_map is None else str(dof_map.ndof)
            raise MPEError(
                f"the DofMap names {found} DOFs but the extracted shapes span "
                f"{self.shapes.shape[0]} response channels"
            )
        meta = {
            "source": "openfemlab.mpe",
            "method": self.diagnostics.get("method", "pLSCF/LSFD"),
            "orders": self.diagnostics.get("orders", ()),
            "band_hz": self.diagnostics.get("band_hz"),
            "tolerances": self.diagnostics.get("tolerances", {}),
            "weighting": self.diagnostics.get("weighting"),
            "scaling": self.diagnostics.get("scaling"),
            "min_frac": float(np.min(self.frac)) if self.frac.size else 0.0,
        }
        return TestData(
            frequencies=self.frequencies_hz.copy(),
            shapes=self.shapes.copy(),
            dof_map=dof_map,
            damping=self.damping_ratios.copy(),
            meta=meta,
        )
