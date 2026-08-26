"""Effective Independence sensor placement (MS-10.2) — Round-3 API stubs.

Every public name below is the binding surface of ``docs/MODULE_SPEC.md``
MS-10.5, pinned ahead of the implementation (GAP-07, spec-first): signatures,
result fields, and failure modes are the contract the AC-PRETEST criteria of
``docs/ACCEPTANCE_CRITERIA.md`` section 10 will gate, and the function bodies
raise :class:`NotImplementedError` naming their spec anchor until the Round-3
implementation replaces them.

The method being specified, for orientation: Kammer's Effective Independence
ranks each candidate DOF by its leverage — the diagonal of the orthogonal
projector onto the column space of the target-mode partition — and eliminates
the smallest contributor until the requested sensor count remains. Each
removal multiplies ``det(Φ_Sᵀ Φ_S)`` by exactly ``1 − E_d``, so the greedy rule
is "lose the least Fisher information per step" (MS-10.1). What it optimizes
is target-mode observability; test-analysis-model orthogonality at the chosen
placement (AC-CORR-009) stays a separate check, a distinction MS-10.1 records
with measured numbers.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
import numpy.typing as npt

if TYPE_CHECKING:  # pragma: no cover - the MS-2.1 bridge type, import-cycle free
    from openfemlab.workflow.sensors import SensorMap

__all__ = [
    "PlacementQuality",
    "PlacementResult",
    "ei_leverage",
    "select_sensors",
    "modal_kinetic_energy",
    "placement_quality",
    "to_sensor_map",
]

_SPEC_FIRST = (
    "is specified but not yet implemented (GAP-07, Round 3): "
    "see docs/MODULE_SPEC.md {anchor} for the binding contract"
)


def _not_implemented(name: str, anchor: str) -> NotImplementedError:
    return NotImplementedError(
        f"openfemlab.pretest.{name} " + _SPEC_FIRST.format(anchor=anchor)
    )


@dataclass(frozen=True)
class PlacementQuality:
    """Observability metrics of one sensor layout (MS-10.4).

    Attributes
    ----------
    det_fim:
        ``det(Φ_Sᵀ Φ_S)`` — volume of the information ellipsoid.
    condition:
        ``σ_max / σ_min`` of ``Φ_S`` — worst-direction observability loss.
    min_singular_value:
        ``σ_min(Φ_S)`` — margin to an unobservable target mode.
    automac_off_diagonal:
        Largest off-diagonal of ``correlation.automac(Φ_S)`` — spatial
        aliasing between target modes on the selected channels (the MS-2.2
        kernel, not a re-implementation).
    """

    det_fim: float
    condition: float
    min_singular_value: float
    automac_off_diagonal: float


@dataclass(frozen=True)
class PlacementResult:
    """Outcome of a sensor-placement run (MS-10.5).

    Attributes
    ----------
    selected:
        Retained candidate rows, ascending.
    eliminated:
        Removal order, first removed first — replaying it against
        ``det_history`` reproduces the ``(1 − E_d)`` downdates of MS-10.2.
    leverage:
        ``(s,)`` EI leverage of the retained rows at the final step.
    det_fim:
        ``det(Φ_Sᵀ Φ_S)`` of the selection.
    det_history:
        ``det(FIM)`` after each elimination, full candidate set first.
    quality:
        The MS-10.4 metrics of the selection.
    diagnostics:
        Method, weighting, candidate/keep sets, wall time (MS-0.3).
    """

    selected: tuple[int, ...]
    eliminated: tuple[int, ...]
    leverage: npt.NDArray[np.float64]
    det_fim: float
    det_history: npt.NDArray[np.float64]
    quality: PlacementQuality
    diagnostics: dict[str, Any] = field(default_factory=dict)


def ei_leverage(shapes: Any, *, mass: Any = None) -> npt.NDArray[np.float64]:
    """Effective Independence leverage of every row of ``shapes`` (MS-10.2).

    ``E_d = [Φ (ΦᵀΦ)⁻¹ Φᵀ]_dd`` — the diagonal of the orthogonal projector
    onto the column space of the target modes, so ``E_d ∈ [0, 1]`` and
    ``Σ E_d = m`` exactly (AC-PRETEST-001). With ``mass`` given, the shapes
    are reweighted to ``M^(1/2) Φ`` first.

    Parameters
    ----------
    shapes:
        ``(n, m)`` target mode partition, e.g. ``ModalResult.mode_shapes``
        rows restricted to the candidate DOFs.
    mass:
        Optional mass matrix (diagonal applied exactly, consistent via
        Cholesky) for kinetic-energy weighting; ``M = c·I`` changes nothing.

    Raises
    ------
    PretestError
        If the mode partition is rank deficient (no leverage is defined on
        modes the candidates cannot observe).
    """
    raise _not_implemented("ei_leverage", "MS-10.2")


def select_sensors(
    shapes: Any,
    num_sensors: int,
    *,
    mass: Any = None,
    candidates: Sequence[int] | None = None,
    keep: Sequence[int] = (),
    method: str = "ei",
) -> PlacementResult:
    """Choose ``num_sensors`` DOF rows by Effective Independence (MS-10.2).

    Backward elimination: remove the candidate with the smallest leverage,
    recompute, repeat. Ties within ``1e-12`` drop the highest row index so
    repeated runs are bitwise identical (AC-PRETEST-004); each removal
    multiplies ``det(FIM)`` by exactly ``1 − E_d``, recorded in
    ``det_history``.

    Parameters
    ----------
    shapes:
        ``(n, m)`` target mode set, mass-normalized (MS-1.3).
    num_sensors:
        Channels to retain; must satisfy ``num_sensors >= m``.
    mass:
        Optional MS-10.2 kinetic-energy weighting.
    candidates:
        Rows the sensors may occupy (default: all ``n``).
    keep:
        Rows that are never eliminated (already-mounted channels).
    method:
        ``"ei"`` (Round 3). ``"adpr"`` exciter ranking is the MS-10.3 P2
        outline and is reserved, not accepted.

    Raises
    ------
    PretestError
        For ``num_sensors < m``, a rank-deficient candidate partition, or
        ``keep``/``candidates`` requests that cannot be honored.
    """
    raise _not_implemented("select_sensors", "MS-10.2")


def modal_kinetic_energy(shapes: Any, mass: Any) -> npt.NDArray[np.float64]:
    """Per-DOF, per-mode kinetic energy ``MKE_di = M_dd Φ_di²`` (MS-10.3).

    The classical cross-check that a placement has not landed on low-signal
    DOFs; on the uniform fixed-free chain the mode-1 column is strictly
    increasing toward the free end (AC-PRETEST-005).

    Parameters
    ----------
    shapes:
        ``(n, m)`` target mode set.
    mass:
        Mass matrix; the diagonal is what MKE reads.
    """
    raise _not_implemented("modal_kinetic_energy", "MS-10.3")


def placement_quality(shapes: Any, selected: Sequence[int]) -> PlacementQuality:
    """Grade a sensor layout on the four MS-10.4 observability metrics.

    Works for any placement — EI-selected or externally given — so competing
    layouts are compared on numbers: on the AC-CORR-009 chain twin the metrics
    rank the spread layout above the adversarial one on every axis, the same
    verdict the Guyan-TAM gate reaches (AC-PRETEST-003).

    Parameters
    ----------
    shapes:
        ``(n, m)`` target mode set.
    selected:
        Rows the layout instruments.
    """
    raise _not_implemented("placement_quality", "MS-10.4")


def to_sensor_map(
    placement: PlacementResult,
    *,
    labels: Sequence[str] | None = None,
) -> SensorMap:
    """Bridge a placement to the ``SensorMap`` the M2/M4 chain consumes (MS-2.1).

    Channels observe ``placement.selected`` in ascending order with positive
    orientation; ``labels`` names them for reports and COMAC tables.
    """
    raise _not_implemented("to_sensor_map", "MS-10.5")
