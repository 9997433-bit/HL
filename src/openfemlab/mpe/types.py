"""Result types of the M9 modal-parameter-extraction module (spec MS-10).

Spec-first placeholders (GAP-06): the dataclasses carry the exact fields
MS-10.6 binds so downstream code can already be typed against them, but the
one behavior they promise — :meth:`MPEResult.to_test_data` and
:meth:`StabilizationDiagram.select` — raises :class:`NotImplementedError`
naming its spec anchor. All AC-MPE rows are ``specified``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
import numpy.typing as npt

if TYPE_CHECKING:  # pragma: no cover
    from openfemlab.core.dofs import DofMap
    from openfemlab.core.results import TestData

__all__ = ["PoleEstimate", "StabilizationDiagram", "MPEResult"]

#: Stabilization labels of MS-10.3, in increasing order of stability.
POLE_LABELS = ("new", "freq", "damp", "stable")


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
        """Automatic pole pick of MS-10.3 (lowest-order fully stable member
        of every alignment fully stable over ``min_count`` consecutive
        orders). Not implemented — M9 is spec-first (AC-MPE-003)."""
        raise NotImplementedError(
            "StabilizationDiagram.select is specified (MS-10.3, AC-MPE-003) "
            "but not implemented; M9/GAP-06 is spec-first"
        )


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

    def to_test_data(self, dof_map: DofMap) -> TestData:
        """Bridge to the M2 correlation input (MS-10.5): a ``TestData`` with
        ``damping`` populated and ``meta`` provenance. Not implemented — M9
        is spec-first (AC-MPE-004)."""
        raise NotImplementedError(
            "MPEResult.to_test_data is specified (MS-10.5, AC-MPE-004) but "
            "not implemented; M9/GAP-06 is spec-first"
        )
