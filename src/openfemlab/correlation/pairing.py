"""Automatic FE/test mode pairing (MS-2.3).

Correlation and model updating are only meaningful between *paired* modes, and
the pairing is not the identity: the FE model usually predicts more modes than
were measured, and it reorders them as parameters change during updating.

The pairing score is the cross-MAC when both shape sets are available and
frequency proximity otherwise.  Two assignment strategies are offered:
``"greedy"`` (repeatedly accept the globally best remaining candidate, what
classic tools do) and ``"optimal"`` (Hungarian assignment maximising the total
score, which avoids the greedy pass locking in an early bad match).

Convention: the *test* set indexes rows, the *FE* set indexes columns.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import numpy.typing as npt

from .mac import mac
from .metrics import frequency_error_matrix


def _json_float(value: float | None) -> float | None:
    """Map a non-finite scalar onto ``null``.

    RFC 8259 has no ``NaN`` or ``Infinity`` literal, and Python's ``json``
    emits those bare tokens by default -- an artifact only Python can read
    back. Both arise here legitimately: an unscored pair carries ``nan`` and a
    pair against a 0 Hz mode carries an infinite percentage error.
    """
    if value is None or not np.isfinite(value):
        return None
    return float(value)

__all__ = [
    "ModePair",
    "ModePairing",
    "pair_modes",
    "pair_modes_clustered",
]


@dataclass(frozen=True)
class ModePair:
    """A single correlated test/FE mode pair."""

    test_index: int
    fe_index: int
    mac: float
    test_frequency: float | None = None
    fe_frequency: float | None = None

    @property
    def absolute_frequency_error(self) -> float | None:
        if self.test_frequency is None or self.fe_frequency is None:
            return None
        return self.fe_frequency - self.test_frequency

    @property
    def frequency_error_pct(self) -> float | None:
        if self.test_frequency is None or self.fe_frequency is None:
            return None
        if self.test_frequency == 0.0:
            return float("inf")
        return 100.0 * (self.fe_frequency - self.test_frequency) / self.test_frequency

    def as_dict(self) -> dict[str, Any]:
        """One row of the pairing table, derived frequency error included."""
        return {
            "test_index": self.test_index,
            "fe_index": self.fe_index,
            "mac": _json_float(self.mac),
            "test_frequency": self.test_frequency,
            "fe_frequency": self.fe_frequency,
            "frequency_error_pct": _json_float(self.frequency_error_pct),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ModePair:
        """Inverse of :meth:`as_dict`; the frequency error is recomputed."""
        test_frequency = payload["test_frequency"]
        fe_frequency = payload["fe_frequency"]
        mac_value = payload["mac"]
        return cls(
            test_index=int(payload["test_index"]),
            fe_index=int(payload["fe_index"]),
            # A frequency-only pairing has no shapes to score, so it carries
            # ``nan``; ``as_dict`` writes that as ``null`` to stay inside JSON.
            mac=float("nan") if mac_value is None else float(mac_value),
            test_frequency=None if test_frequency is None else float(test_frequency),
            fe_frequency=None if fe_frequency is None else float(fe_frequency),
        )


@dataclass
class ModePairing:
    """Result of automatic test/FE mode pairing."""

    pairs: list[ModePair] = field(default_factory=list)
    unpaired_test: list[int] = field(default_factory=list)
    unpaired_fe: list[int] = field(default_factory=list)
    mac_matrix: np.ndarray | None = None
    method: str = "greedy"

    def __len__(self) -> int:
        return len(self.pairs)

    def __iter__(self) -> Iterator[ModePair]:
        return iter(self.pairs)

    @property
    def test_indices(self) -> np.ndarray:
        return np.array([p.test_index for p in self.pairs], dtype=int)

    @property
    def fe_indices(self) -> np.ndarray:
        return np.array([p.fe_index for p in self.pairs], dtype=int)

    @property
    def mac_values(self) -> np.ndarray:
        return np.array([p.mac for p in self.pairs], dtype=float)

    @property
    def frequency_errors_pct(self) -> np.ndarray:
        return np.array(
            [
                np.nan if p.frequency_error_pct is None else p.frequency_error_pct
                for p in self.pairs
            ],
            dtype=float,
        )

    def as_tuples(self) -> list[tuple[int, int]]:
        """The pairing as ``(test_index, fe_index)`` tuples."""
        return [(p.test_index, p.fe_index) for p in self.pairs]

    def as_dict(self) -> dict[str, Any]:
        """Plain-Python view of the pairing (JSON ready, no NumPy scalars)."""
        return {
            "pairs": [pair.as_dict() for pair in self.pairs],
            "unpaired_test": list(self.unpaired_test),
            "unpaired_fe": list(self.unpaired_fe),
            "mac_matrix": None if self.mac_matrix is None else self.mac_matrix.tolist(),
            "method": self.method,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ModePairing:
        """Inverse of :meth:`as_dict`."""
        matrix = payload["mac_matrix"]
        return cls(
            pairs=[ModePair.from_dict(row) for row in payload["pairs"]],
            unpaired_test=[int(i) for i in payload["unpaired_test"]],
            unpaired_fe=[int(j) for j in payload["unpaired_fe"]],
            mac_matrix=None if matrix is None else np.asarray(matrix, dtype=float),
            method=str(payload["method"]),
        )

    def table(self) -> str:
        """Human readable correlation table (FEMtools-style pair listing)."""
        header = (
            f"{'test':>5} {'fe':>5} {'f_test [Hz]':>12} {'f_fe [Hz]':>12} "
            f"{'err [%]':>9} {'MAC':>7}"
        )
        lines = [header, "-" * len(header)]
        for pair in self.pairs:
            f_test = "-" if pair.test_frequency is None else f"{pair.test_frequency:12.4f}"
            f_fe = "-" if pair.fe_frequency is None else f"{pair.fe_frequency:12.4f}"
            err = "-" if pair.frequency_error_pct is None else f"{pair.frequency_error_pct:9.3f}"
            lines.append(
                f"{pair.test_index:>5} {pair.fe_index:>5} {f_test:>12} {f_fe:>12} "
                f"{err:>9} {pair.mac:7.4f}"
            )
        return "\n".join(lines)


def _greedy_assignment(score: np.ndarray, threshold: float) -> list[tuple[int, int]]:
    """Greedily take the globally best remaining score above ``threshold``."""
    work = np.array(score, dtype=float, copy=True)
    assignments: list[tuple[int, int]] = []
    while np.isfinite(work).any():
        flat = int(np.argmax(np.where(np.isfinite(work), work, -np.inf)))
        row, col = np.unravel_index(flat, work.shape)
        best = work[row, col]
        if not np.isfinite(best) or best < threshold:
            break
        assignments.append((int(row), int(col)))
        work[row, :] = -np.inf
        work[:, col] = -np.inf
    return assignments


def _optimal_assignment(score: np.ndarray, threshold: float) -> list[tuple[int, int]]:
    """Total-score maximising assignment (Hungarian); falls back to greedy."""
    try:
        from scipy.optimize import linear_sum_assignment
    except ImportError:  # pragma: no cover - exercised only without SciPy
        return _greedy_assignment(score, threshold)

    penalised = np.where(np.isfinite(score), score, -1.0e6)
    rows, cols = linear_sum_assignment(-penalised)
    return [
        (int(r), int(c))
        for r, c in zip(rows, cols, strict=True)
        if np.isfinite(score[r, c]) and score[r, c] >= threshold
    ]


def pair_modes(
    test_shapes: Any = None,
    fe_shapes: Any = None,
    test_frequencies: Any = None,
    fe_frequencies: Any = None,
    *,
    method: str = "greedy",
    mac_threshold: float = 0.0,
    frequency_tolerance_pct: float | None = None,
    freq_penalty: float = 0.0,
    weights: Any = None,
    max_pairs: int | None = None,
) -> ModePairing:
    """Pair test modes with FE modes.

    Parameters
    ----------
    test_shapes, fe_shapes:
        ``(ndof, m)`` shape sets on a common DOF set.  When both are given the
        cross-MAC drives the pairing.
    test_frequencies, fe_frequencies:
        Frequencies in Hz.  Required when no shapes are available (the score is
        then frequency proximity) and used for reporting otherwise.
    method:
        ``"greedy"``, ``"optimal"`` (Hungarian, needs SciPy) or ``"frequency"``
        to force frequency pairing even when shapes are available.
    mac_threshold, frequency_tolerance_pct:
        Candidate filters.  Modes left without an acceptable partner are
        reported in ``unpaired_test`` / ``unpaired_fe`` rather than forced into
        a bad pair.
    freq_penalty:
        Weight ``β`` of the relative frequency distance in the MAC score
        (MS-2.3 suggests 0.1), which separates candidates whose shapes are
        nearly as similar as each other.  The score stays MAC-only at the
        default 0, and the filters above always act on the raw MAC.
    max_pairs:
        Keep only the ``max_pairs`` best-scoring pairs.
    """
    if method not in {"greedy", "optimal", "frequency"}:
        raise ValueError(f"unknown pairing method {method!r}")
    if freq_penalty < 0.0:
        raise ValueError("freq_penalty must be non-negative")

    test_freq = None if test_frequencies is None else np.asarray(test_frequencies, float).ravel()
    fe_freq = None if fe_frequencies is None else np.asarray(fe_frequencies, float).ravel()
    have_shapes = test_shapes is not None and fe_shapes is not None
    use_shapes = have_shapes and method != "frequency"

    macs = mac(test_shapes, fe_shapes, weights) if have_shapes else None
    if use_shapes:
        n_test, n_fe = macs.shape  # type: ignore[union-attr]
        score = np.array(macs, dtype=float, copy=True)
    else:
        if test_freq is None or fe_freq is None:
            raise ValueError(
                "pairing requires either both mode shape sets or both frequency vectors"
            )
        n_test, n_fe = test_freq.size, fe_freq.size
        score = -np.abs(frequency_error_matrix(test_freq, fe_freq))

    if test_freq is not None and test_freq.size != n_test:
        raise ValueError("test frequencies and test mode shapes disagree on the mode count")
    if fe_freq is not None and fe_freq.size != n_fe:
        raise ValueError("FE frequencies and FE mode shapes disagree on the mode count")

    if frequency_tolerance_pct is not None:
        if test_freq is None or fe_freq is None:
            raise ValueError("frequency_tolerance_pct requires both frequency vectors")
        outside = np.abs(frequency_error_matrix(test_freq, fe_freq)) > frequency_tolerance_pct
        score[outside] = -np.inf

    threshold = -np.inf
    if use_shapes:
        # Filters act on the raw MAC, so a frequency penalty can never turn an
        # acceptable candidate into a rejected one -- it only ranks candidates.
        numerical_floor = 100.0 * np.finfo(float).eps
        minimum_mac = max(float(mac_threshold), numerical_floor)
        score[macs < minimum_mac] = -np.inf  # type: ignore[operator]
        if freq_penalty > 0.0:
            if test_freq is None or fe_freq is None:
                raise ValueError("freq_penalty requires both frequency vectors")
            distance = np.abs(frequency_error_matrix(test_freq, fe_freq)) / 100.0
            score = score - freq_penalty * np.where(np.isfinite(distance), distance, np.inf)

    if method == "optimal" and use_shapes:
        assignments = _optimal_assignment(score, threshold)
    else:
        assignments = _greedy_assignment(score, threshold)

    if max_pairs is not None:
        assignments = sorted(assignments, key=lambda rc: score[rc], reverse=True)[:max_pairs]
    assignments.sort(key=lambda rc: rc[0])

    pairs = [
        ModePair(
            test_index=r,
            fe_index=c,
            mac=float(macs[r, c]) if macs is not None else float("nan"),
            test_frequency=None if test_freq is None else float(test_freq[r]),
            fe_frequency=None if fe_freq is None else float(fe_freq[c]),
        )
        for r, c in assignments
    ]
    paired_test = {p.test_index for p in pairs}
    paired_fe = {p.fe_index for p in pairs}
    return ModePairing(
        pairs=pairs,
        unpaired_test=[i for i in range(n_test) if i not in paired_test],
        unpaired_fe=[j for j in range(n_fe) if j not in paired_fe],
        mac_matrix=macs,
        method=method if use_shapes else "frequency",
    )


def _cluster_indices(frequencies: npt.NDArray[np.float64], tolerance_pct: float) -> list[list[int]]:
    """Group mode indices whose frequencies lie within ``tolerance_pct`` of a cluster member."""
    if frequencies.size == 0:
        return []
    order = np.argsort(frequencies)
    clusters: list[list[int]] = []
    current = [int(order[0])]
    for index in order[1:]:
        reference = frequencies[current[-1]]
        relative = abs(frequencies[index] - reference) / max(reference, 1e-12) * 100.0
        if relative <= tolerance_pct:
            current.append(int(index))
        else:
            clusters.append(current)
            current = [int(index)]
    clusters.append(current)
    return clusters


def pair_modes_clustered(
    test_shapes: Any,
    fe_shapes: Any,
    test_frequencies: Any,
    fe_frequencies: Any,
    *,
    cluster_tolerance_pct: float = 1.0,
    mac_threshold: float = 0.0,
    freq_penalty: float = 0.1,
) -> ModePairing:
    """Pair modes with frequency clustering for near-duplicate (double-root) bands.

    Modes are grouped into frequency clusters on each side.  Clusters are matched
    by nearest centre frequency, then optimal MAC assignment runs inside each
    matched cluster pair (MS-2.7, AC-CORR-012).
    """
    if cluster_tolerance_pct < 0.0:
        raise ValueError("cluster_tolerance_pct must be non-negative")
    test_freq = np.asarray(test_frequencies, dtype=float).ravel()
    fe_freq = np.asarray(fe_frequencies, dtype=float).ravel()
    macs = mac(test_shapes, fe_shapes)
    n_test, n_fe = macs.shape

    test_clusters = _cluster_indices(test_freq, cluster_tolerance_pct)
    fe_clusters = _cluster_indices(fe_freq, cluster_tolerance_pct)

    assignments: list[tuple[int, int]] = []
    minimum_mac = max(float(mac_threshold), 100.0 * np.finfo(float).eps)
    available_fe = list(fe_clusters)

    for test_cluster in test_clusters:
        if not available_fe:
            break
        centre_test = float(np.mean(test_freq[test_cluster]))
        fe_cluster = min(
            available_fe,
            key=lambda cluster: abs(float(np.mean(fe_freq[cluster])) - centre_test),
        )
        available_fe.remove(fe_cluster)
        sub = macs[np.ix_(test_cluster, fe_cluster)]
        score = np.array(sub, dtype=float, copy=True)
        if freq_penalty > 0.0:
            distance = np.abs(
                frequency_error_matrix(test_freq[test_cluster], fe_freq[fe_cluster])
            ) / 100.0
            score = score - freq_penalty * distance
        score[sub < minimum_mac] = -np.inf
        local = _optimal_assignment(score, -np.inf)
        for row, col in local:
            test_index = test_cluster[row]
            fe_index = fe_cluster[col]
            if macs[test_index, fe_index] >= minimum_mac:
                assignments.append((test_index, fe_index))

    assignments.sort(key=lambda pair: pair[0])
    pairs = [
        ModePair(
            test_index=r,
            fe_index=c,
            mac=float(macs[r, c]),
            test_frequency=float(test_freq[r]),
            fe_frequency=float(fe_freq[c]),
        )
        for r, c in assignments
    ]
    paired_test = {pair.test_index for pair in pairs}
    paired_fe = {pair.fe_index for pair in pairs}
    return ModePairing(
        pairs=pairs,
        unpaired_test=[index for index in range(n_test) if index not in paired_test],
        unpaired_fe=[index for index in range(n_fe) if index not in paired_fe],
        mac_matrix=macs,
        method="clustered",
    )
