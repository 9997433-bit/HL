"""Aggregated correlation quality indicators.

:mod:`~openfemlab.correlation.mac` and :mod:`~openfemlab.correlation.metrics`
produce per-mode arrays; this module reduces a pairing of those arrays to the
handful of scalars that decide whether a model is acceptable and that steer a
model updating run: mean/min diagonal MAC, frequency errors, and the worst
off-diagonal MAC (the mode-swapping indicator).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .pairing import ModePairing, pair_modes

__all__ = [
    "CorrelationSummary",
    "correlate",
    "correlation_summary",
    "normalized_frequency_residual",
    "off_diagonal_mac",
]


@dataclass
class CorrelationSummary:
    """Scalar summary of an FE/test correlation."""

    n_test_modes: int
    n_fe_modes: int
    n_paired: int
    mean_mac: float
    min_mac: float
    max_mac: float
    mean_abs_freq_error_pct: float
    max_abs_freq_error_pct: float
    rms_freq_error_pct: float
    mean_signed_freq_error_pct: float
    max_off_diagonal_mac: float
    mac_values: np.ndarray = field(default_factory=lambda: np.empty(0))
    freq_errors_pct: np.ndarray = field(default_factory=lambda: np.empty(0))
    pairing: ModePairing | None = None

    def is_correlated(self, mac_threshold: float = 0.9, freq_tolerance_pct: float = 2.0) -> bool:
        """True when every pair meets the MAC and frequency acceptance limits."""
        if self.n_paired == 0:
            return False
        return bool(self.min_mac >= mac_threshold) and bool(
            self.max_abs_freq_error_pct <= freq_tolerance_pct
        )

    def as_dict(self) -> dict[str, float | int]:
        return {
            "n_test_modes": self.n_test_modes,
            "n_fe_modes": self.n_fe_modes,
            "n_paired": self.n_paired,
            "mean_mac": self.mean_mac,
            "min_mac": self.min_mac,
            "max_mac": self.max_mac,
            "mean_abs_freq_error_pct": self.mean_abs_freq_error_pct,
            "max_abs_freq_error_pct": self.max_abs_freq_error_pct,
            "rms_freq_error_pct": self.rms_freq_error_pct,
            "mean_signed_freq_error_pct": self.mean_signed_freq_error_pct,
            "max_off_diagonal_mac": self.max_off_diagonal_mac,
        }

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, float | int],
        pairing: ModePairing | None = None,
    ) -> CorrelationSummary:
        """Inverse of :meth:`as_dict`.

        The per-mode arrays are deliberately absent from the payload — the
        pairing table already carries them — so they are restored from
        ``pairing`` when one is supplied and left empty otherwise.
        """
        return cls(
            n_test_modes=int(payload["n_test_modes"]),
            n_fe_modes=int(payload["n_fe_modes"]),
            n_paired=int(payload["n_paired"]),
            mean_mac=float(payload["mean_mac"]),
            min_mac=float(payload["min_mac"]),
            max_mac=float(payload["max_mac"]),
            mean_abs_freq_error_pct=float(payload["mean_abs_freq_error_pct"]),
            max_abs_freq_error_pct=float(payload["max_abs_freq_error_pct"]),
            rms_freq_error_pct=float(payload["rms_freq_error_pct"]),
            mean_signed_freq_error_pct=float(payload["mean_signed_freq_error_pct"]),
            max_off_diagonal_mac=float(payload["max_off_diagonal_mac"]),
            mac_values=np.empty(0) if pairing is None else pairing.mac_values,
            freq_errors_pct=np.empty(0) if pairing is None else pairing.frequency_errors_pct,
            pairing=pairing,
        )

    def report(self) -> str:
        lines = [
            f"paired modes            : {self.n_paired} "
            f"(test {self.n_test_modes}, FE {self.n_fe_modes})",
            f"mean / min MAC          : {self.mean_mac:.4f} / {self.min_mac:.4f}",
            f"mean |freq error| [%]   : {self.mean_abs_freq_error_pct:.3f}",
            f"max  |freq error| [%]   : {self.max_abs_freq_error_pct:.3f}",
            f"rms   freq error  [%]   : {self.rms_freq_error_pct:.3f}",
            f"max off-diagonal MAC    : {self.max_off_diagonal_mac:.4f}",
        ]
        if self.pairing is not None and self.pairing.pairs:
            lines.append("")
            lines.append(self.pairing.table())
        return "\n".join(lines)

    def __str__(self) -> str:  # pragma: no cover - convenience only
        return self.report()


def off_diagonal_mac(macs: np.ndarray | None, pairing: ModePairing) -> float:
    """Largest MAC value outside the correlated pairs (mode-swap indicator)."""
    if macs is None or macs.size == 0 or not pairing.pairs:
        return 0.0
    masked = np.array(macs, dtype=float, copy=True)
    for pair in pairing.pairs:
        masked[pair.test_index, pair.fe_index] = -np.inf
    finite = masked[np.isfinite(masked)]
    return float(finite.max()) if finite.size else 0.0


def correlation_summary(
    test_frequencies: Any = None,
    fe_frequencies: Any = None,
    test_shapes: Any = None,
    fe_shapes: Any = None,
    *,
    pairing: ModePairing | None = None,
    weights: Any = None,
    **pairing_kwargs: Any,
) -> CorrelationSummary:
    """Pair modes (unless a pairing is supplied) and summarise the correlation."""
    if pairing is None:
        pairing = pair_modes(
            test_shapes=test_shapes,
            fe_shapes=fe_shapes,
            test_frequencies=test_frequencies,
            fe_frequencies=fe_frequencies,
            weights=weights,
            **pairing_kwargs,
        )

    n_test = len(pairing.pairs) + len(pairing.unpaired_test)
    n_fe = len(pairing.pairs) + len(pairing.unpaired_fe)

    macs = pairing.mac_values
    macs = macs[np.isfinite(macs)]
    errors = pairing.frequency_errors_pct
    errors = errors[np.isfinite(errors)]

    return CorrelationSummary(
        n_test_modes=n_test,
        n_fe_modes=n_fe,
        n_paired=len(pairing.pairs),
        mean_mac=float(macs.mean()) if macs.size else 0.0,
        min_mac=float(macs.min()) if macs.size else 0.0,
        max_mac=float(macs.max()) if macs.size else 0.0,
        mean_abs_freq_error_pct=float(np.abs(errors).mean()) if errors.size else 0.0,
        max_abs_freq_error_pct=float(np.abs(errors).max()) if errors.size else 0.0,
        rms_freq_error_pct=float(np.sqrt(np.mean(errors**2))) if errors.size else 0.0,
        mean_signed_freq_error_pct=float(errors.mean()) if errors.size else 0.0,
        max_off_diagonal_mac=off_diagonal_mac(pairing.mac_matrix, pairing),
        mac_values=pairing.mac_values,
        freq_errors_pct=pairing.frequency_errors_pct,
        pairing=pairing,
    )


def correlate(
    test_frequencies: Any,
    fe_frequencies: Any,
    test_shapes: Any = None,
    fe_shapes: Any = None,
    **kwargs: Any,
) -> CorrelationSummary:
    """Convenience wrapper around :func:`correlation_summary`."""
    return correlation_summary(
        test_frequencies=test_frequencies,
        fe_frequencies=fe_frequencies,
        test_shapes=test_shapes,
        fe_shapes=fe_shapes,
        **kwargs,
    )


def normalized_frequency_residual(
    test_frequencies: Any,
    fe_frequencies: Any,
    pairing: ModePairing | None = None,
) -> np.ndarray:
    """Relative frequency residual ``(f_fe - f_test) / f_test`` for paired modes."""
    test = np.asarray(test_frequencies, dtype=float).ravel()
    fe = np.asarray(fe_frequencies, dtype=float).ravel()
    if pairing is None:
        if test.size != fe.size:
            raise ValueError("without a pairing both frequency vectors must have equal length")
        indices = list(zip(range(test.size), range(fe.size), strict=False))
    else:
        indices = pairing.as_tuples()
    if not indices:
        return np.empty(0)
    return np.array([(fe[j] - test[i]) / test[i] for i, j in indices], dtype=float)
