"""LSCF / poly-reference curve fitting entry points (spec MS-10.2..MS-10.4).

Spec-first placeholders (GAP-06): every callable carries the exact MS-10.6
signature but raises :class:`NotImplementedError` naming its spec anchor and
acceptance criterion. Nothing here claims an implemented gate — all AC-MPE
rows are ``specified``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from .types import MPEResult, PoleEstimate, StabilizationDiagram

if TYPE_CHECKING:  # pragma: no cover
    from openfemlab.solver.dynamics import FrequencyResponse

__all__ = ["fit_lscf", "stabilization_diagram", "extract_shapes", "extract_modes"]


def fit_lscf(
    frf: FrequencyResponse,
    order: int,
    *,
    band: tuple[float, float] | None = None,
    weighting: str = "unity",
) -> tuple[PoleEstimate, ...]:
    """Poles of one weighted LSCF / poly-reference fit at ``order`` (MS-10.2).

    Not implemented — M9 is spec-first (AC-MPE-001).
    """
    raise NotImplementedError(
        "fit_lscf is specified (MS-10.2, AC-MPE-001) but not implemented; "
        "M9/GAP-06 is spec-first"
    )


def stabilization_diagram(
    frf: FrequencyResponse,
    orders: Sequence[int],
    *,
    band: tuple[float, float] | None = None,
    freq_tol: float = 0.01,
    damp_tol: float = 0.05,
    mac_tol: float = 0.95,
) -> StabilizationDiagram:
    """Fit over ``orders`` and classify poles across them (MS-10.3).

    Not implemented — M9 is spec-first (AC-MPE-003).
    """
    raise NotImplementedError(
        "stabilization_diagram is specified (MS-10.3, AC-MPE-003) but not "
        "implemented; M9/GAP-06 is spec-first"
    )


def extract_shapes(
    frf: FrequencyResponse,
    poles: Sequence[PoleEstimate],
    *,
    band: tuple[float, float] | None = None,
    residuals: str = "both",
) -> MPEResult:
    """LSFD residue/shape estimation with the poles frozen (MS-10.4).

    Not implemented — M9 is spec-first (AC-MPE-002).
    """
    raise NotImplementedError(
        "extract_shapes is specified (MS-10.4, AC-MPE-002) but not "
        "implemented; M9/GAP-06 is spec-first"
    )


def extract_modes(
    frf: FrequencyResponse,
    orders: Sequence[int],
    *,
    band: tuple[float, float] | None = None,
    min_count: int = 3,
    **tolerances: Any,
) -> MPEResult:
    """One-call driver: stabilization diagram, automatic pick, LSFD
    (MS-10.6). Not implemented — M9 is spec-first (AC-MPE-004)."""
    raise NotImplementedError(
        "extract_modes is specified (MS-10.6, AC-MPE-004) but not "
        "implemented; M9/GAP-06 is spec-first"
    )
