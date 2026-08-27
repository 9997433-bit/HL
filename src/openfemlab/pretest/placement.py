"""Effective Independence sensor placement (MS-11.2) — Round-3 implementation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
import numpy.typing as npt

from ..correlation.mac import automac
from ..exceptions import PretestError

if TYPE_CHECKING:  # pragma: no cover - the MS-2.1 bridge type, import-cycle free
    from openfemlab.workflow.sensors import SensorMap

__all__ = [
    "PlacementQuality",
    "PlacementResult",
    "ei_leverage",
    "select_sensors",
    "modal_kinetic_energy",
    "rank_excitation_dofs",
    "prune_sensors_by_automac",
    "iterative_guyan_placement",
    "placement_quality",
    "to_sensor_map",
]

_TIE_TOL = 1e-12
_RANK_TOL = 1e-10


def _as_shapes(shapes: Any, name: str = "shapes") -> npt.NDArray[np.float64]:
    array = np.asarray(shapes, dtype=float)
    if array.ndim != 2:
        raise ValueError(f"{name} must be a 2-D array, got shape {array.shape!r}")
    if array.shape[0] == 0 or array.shape[1] == 0:
        raise PretestError(f"{name} must be non-empty to define sensor placement")
    return array


def _mass_sqrt(mass: Any, n_rows: int) -> npt.NDArray[np.float64] | None:
    if mass is None:
        return None
    array = np.asarray(mass, dtype=float)
    if array.ndim == 0:
        return np.full(n_rows, float(np.sqrt(array)), dtype=float)
    if array.ndim == 1:
        if array.shape[0] != n_rows:
            raise ValueError(f"mass diagonal length {array.shape[0]} != {n_rows} rows")
        return np.sqrt(array)
    if array.ndim == 2:
        if array.shape != (n_rows, n_rows):
            raise ValueError(f"mass matrix shape {array.shape} != ({n_rows}, {n_rows})")
        try:
            return np.linalg.cholesky(array)
        except np.linalg.LinAlgError as error:
            raise PretestError("mass matrix is not positive definite") from error
    raise ValueError("mass must be a scalar, diagonal vector, or square matrix")


def _weight_shapes(
    shapes: npt.NDArray[np.float64],
    mass: Any,
) -> npt.NDArray[np.float64]:
    weight = _mass_sqrt(mass, shapes.shape[0])
    if weight is None:
        return shapes
    if weight.ndim == 1:
        return shapes * weight[:, np.newaxis]
    return weight @ shapes


def _fim_det(shapes: npt.NDArray[np.float64]) -> float:
    gram = shapes.T @ shapes
    sign, logdet = np.linalg.slogdet(gram)
    if sign <= 0.0:
        raise PretestError("sensor partition is rank deficient")
    return float(np.exp(logdet))


def _check_full_rank(shapes: npt.NDArray[np.float64]) -> None:
    _, singular, _ = np.linalg.svd(shapes, full_matrices=False)
    if singular.size == 0 or singular[-1] <= _RANK_TOL * max(singular[0], 1.0):
        raise PretestError("target mode partition is rank deficient on the candidate set")


def ei_leverage(shapes: Any, *, mass: Any = None) -> npt.NDArray[np.float64]:
    """Effective Independence leverage of every row of ``shapes`` (MS-11.2)."""
    phi = _weight_shapes(_as_shapes(shapes), mass)
    _check_full_rank(phi)
    gram = phi.T @ phi
    projector = phi @ np.linalg.inv(gram) @ phi.T
    return np.diag(projector).astype(float, copy=False)


def _pick_removal(
    active: list[int],
    leverages: npt.NDArray[np.float64],
    keep: set[int],
) -> int:
    removable = [
        (row, float(leverages[index]))
        for index, row in enumerate(active)
        if row not in keep
    ]
    if not removable:
        raise PretestError("cannot eliminate further rows while honoring keep=")
    minimum = min(value for _, value in removable)
    tied = [row for row, value in removable if value <= minimum + _TIE_TOL]
    return max(tied)


def select_sensors(
    shapes: Any,
    num_sensors: int,
    *,
    mass: Any = None,
    candidates: Sequence[int] | None = None,
    keep: Sequence[int] = (),
    method: str = "ei",
) -> PlacementResult:
    """Choose ``num_sensors`` DOF rows by Effective Independence (MS-11.2)."""
    if method != "ei":
        raise PretestError(f"unsupported placement method {method!r}; only 'ei' is implemented")

    phi = _as_shapes(shapes)
    n_rows, num_modes = phi.shape
    num_sensors = int(num_sensors)
    if num_sensors < num_modes:
        raise PretestError(
            f"requested {num_sensors} sensors for {num_modes} target modes; need s >= m"
        )

    pool = tuple(range(n_rows)) if candidates is None else tuple(int(row) for row in candidates)
    if len(set(pool)) != len(pool):
        raise PretestError("candidate rows must be unique")
    if any(row < 0 or row >= n_rows for row in pool):
        raise PretestError("candidate rows fall outside the shape partition")

    keep_rows = tuple(int(row) for row in keep)
    keep_set = set(keep_rows)
    if len(keep_set) != len(keep_rows):
        raise PretestError("keep rows must be unique")
    if any(row not in pool for row in keep_rows):
        raise PretestError("every keep row must appear in candidates")
    if num_sensors < len(keep_rows):
        raise PretestError("num_sensors is smaller than the number of keep rows")

    active = list(pool)
    phi_pool = _weight_shapes(phi[list(active), :], _subset_mass(mass, active))
    _check_full_rank(phi_pool)

    eliminated: list[int] = []
    det_history = [_fim_det(phi_pool)]

    while len(active) > num_sensors:
        phi_active = _weight_shapes(phi[active, :], _subset_mass(mass, active))
        leverages = ei_leverage(phi_active)
        remove = _pick_removal(active, leverages, keep_set)
        active.remove(remove)
        eliminated.append(remove)
        phi_active = _weight_shapes(phi[active, :], _subset_mass(mass, active))
        det_history.append(_fim_det(phi_active))

    selected = tuple(sorted(active))
    final_shapes = phi[list(selected), :]
    final_leverage = ei_leverage(final_shapes, mass=_subset_mass(mass, selected))
    quality = placement_quality(phi, selected)

    return PlacementResult(
        selected=selected,
        eliminated=tuple(eliminated),
        leverage=final_leverage,
        det_fim=quality.det_fim,
        det_history=np.asarray(det_history, dtype=float),
        quality=quality,
        diagnostics={
            "method": method,
            "mass_weighted": mass is not None,
            "candidates": pool,
            "keep": keep_rows,
            "num_modes": num_modes,
        },
    )


def _subset_mass(mass: Any, rows: Sequence[int]) -> Any:
    if mass is None:
        return None
    array = np.asarray(mass, dtype=float)
    indices = list(rows)
    if array.ndim == 0:
        return array
    if array.ndim == 1:
        return array[np.array(indices, dtype=int)]
    return array[np.ix_(indices, indices)]


def modal_kinetic_energy(shapes: Any, mass: Any) -> npt.NDArray[np.float64]:
    """Per-DOF, per-mode kinetic energy ``MKE_di = M_dd Φ_di²`` (MS-11.3)."""
    phi = _as_shapes(shapes)
    array = np.asarray(mass, dtype=float)
    if array.ndim == 0:
        diagonal = np.full(phi.shape[0], float(array))
    elif array.ndim == 1:
        if array.shape[0] != phi.shape[0]:
            raise ValueError(
                f"mass diagonal length {array.shape[0]} != {phi.shape[0]} rows"
            )
        diagonal = array
    elif array.ndim == 2:
        if array.shape != (phi.shape[0], phi.shape[0]):
            raise ValueError(f"mass matrix shape {array.shape} != ({phi.shape[0]}, {phi.shape[0]})")
        diagonal = np.diag(array)
    else:
        raise ValueError("mass must be a scalar, diagonal vector, or square matrix")
    return (diagonal[:, np.newaxis] * phi * phi).astype(float, copy=False)


def rank_excitation_dofs(
    shapes: Any,
    mass: Any,
    *,
    mode_index: int | None = None,
) -> tuple[npt.NDArray[np.intp], npt.NDArray[np.float64]]:
    """Rank DOF rows for exciter or hanging-point placement by MKE (MS-11.3 ADPR)."""
    phi = _as_shapes(shapes)
    mke = modal_kinetic_energy(phi, mass)
    if mode_index is not None:
        scores = mke[:, int(mode_index)]
    else:
        scores = np.sum(mke, axis=1)
    order = np.argsort(scores)[::-1].astype(np.intp, copy=False)
    return order, scores.astype(float, copy=False)


def prune_sensors_by_automac(
    shapes: Any,
    selected: Sequence[int],
    *,
    threshold: float = 0.15,
) -> tuple[int, ...]:
    """Remove sensors until the AutoMAC off-diagonal peak falls below ``threshold``."""
    phi = _as_shapes(shapes)
    rows = [int(row) for row in selected]
    minimum_sensors = phi.shape[1]
    if len(rows) < minimum_sensors:
        raise PretestError(
            f"cannot prune below {minimum_sensors} sensors for {minimum_sensors} target modes"
        )
    while len(rows) > minimum_sensors:
        quality = placement_quality(phi, rows)
        if quality.automac_off_diagonal <= float(threshold):
            break
        best_row: int | None = None
        best_off = float("inf")
        for row in rows:
            trial = [item for item in rows if item != row]
            trial_quality = placement_quality(phi, trial)
            if trial_quality.automac_off_diagonal < best_off:
                best_off = trial_quality.automac_off_diagonal
                best_row = row
        if best_row is None:
            break
        rows.remove(best_row)
    return tuple(sorted(rows))


def iterative_guyan_placement(
    stiffness: Any,
    shapes: Any,
    num_sensors: int,
    *,
    mass: Any = None,
    candidates: Sequence[int] | None = None,
    keep: Sequence[int] = (),
    max_iterations: int = 4,
) -> PlacementResult:
    """EI placement refined with Guyan-expanded shapes (MS-11.7 iterative pretest)."""
    from openfemlab.correlation.reduction import guyan_reduction

    phi = _as_shapes(shapes)
    pool = (
        tuple(range(phi.shape[0]))
        if candidates is None
        else tuple(int(row) for row in candidates)
    )
    placement = select_sensors(
        phi,
        num_sensors,
        mass=mass,
        candidates=pool,
        keep=keep,
    )
    best = placement
    for _ in range(int(max_iterations)):
        basis = guyan_reduction(stiffness, best.selected)
        expanded = basis.expand(basis.reduce_shapes(phi))
        candidate = select_sensors(
            expanded,
            num_sensors,
            mass=mass,
            candidates=pool,
            keep=keep,
        )
        if candidate.quality.automac_off_diagonal <= best.quality.automac_off_diagonal:
            best = candidate
            break
        best = candidate
    return PlacementResult(
        selected=best.selected,
        eliminated=best.eliminated,
        leverage=best.leverage,
        det_fim=best.det_fim,
        det_history=best.det_history,
        quality=best.quality,
        diagnostics={**best.diagnostics, "iterative_guyan": True},
    )


def placement_quality(shapes: Any, selected: Sequence[int]) -> PlacementQuality:
    """Grade a sensor layout on the four MS-11.4 observability metrics."""
    phi = _as_shapes(shapes)
    rows = tuple(int(row) for row in selected)
    if not rows:
        raise ValueError("selected must contain at least one row")
    if len(set(rows)) != len(rows):
        raise ValueError("selected rows must be unique")
    if any(row < 0 or row >= phi.shape[0] for row in rows):
        raise ValueError("selected rows fall outside the shape partition")

    partition = phi[list(rows), :]
    gram = partition.T @ partition
    det_fim = float(np.linalg.det(gram))
    singular = np.linalg.svd(partition, compute_uv=False)
    min_sv = float(singular[-1]) if singular.size else 0.0
    condition = float(singular[0] / min_sv) if min_sv > 0.0 else float("inf")
    mac = automac(partition)
    off_diagonal = mac.copy()
    np.fill_diagonal(off_diagonal, 0.0)
    automac_off = float(np.max(np.abs(off_diagonal))) if off_diagonal.size else 0.0

    return PlacementQuality(
        det_fim=det_fim,
        condition=condition,
        min_singular_value=min_sv,
        automac_off_diagonal=automac_off,
    )


def to_sensor_map(
    placement: PlacementResult,
    *,
    labels: Sequence[str] | None = None,
) -> SensorMap:
    """Bridge a placement to the ``SensorMap`` the M2/M4 chain consumes (MS-2.1)."""
    from openfemlab.workflow.sensors import SensorMap

    label_tuple = None if labels is None else tuple(str(label) for label in labels)
    if label_tuple is not None and len(label_tuple) != len(placement.selected):
        raise ValueError("labels must have one entry per selected sensor")
    return SensorMap(rows=placement.selected, labels=label_tuple)


@dataclass(frozen=True)
class PlacementQuality:
    """Observability metrics of one sensor layout (MS-11.4)."""

    det_fim: float
    condition: float
    min_singular_value: float
    automac_off_diagonal: float


@dataclass(frozen=True)
class PlacementResult:
    """Outcome of a sensor-placement run (MS-11.5)."""

    selected: tuple[int, ...]
    eliminated: tuple[int, ...]
    leverage: npt.NDArray[np.float64]
    det_fim: float
    det_history: npt.NDArray[np.float64]
    quality: PlacementQuality
    diagnostics: dict[str, Any] = field(default_factory=dict)
