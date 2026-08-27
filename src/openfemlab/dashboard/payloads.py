"""Dashboard-ready JSON payloads for FRF and stabilization views."""

from __future__ import annotations

from typing import Any

import numpy as np

__all__ = [
    "frf_overlay_payload",
    "stabilization_diagram_payload",
]


def frf_overlay_payload(
    frequencies: Any,
    measured: Any,
    synthesized: Any,
    *,
    measured_label: str = "Measured",
    synthesized_label: str = "Synthesized",
) -> dict[str, object]:
    """Build a dashboard ``frf_overlay`` block from two complex FRF lines."""
    freq = np.asarray(frequencies, dtype=np.float64).ravel()
    measured_values = np.asarray(measured, dtype=np.complex128).ravel()
    synthesized_values = np.asarray(synthesized, dtype=np.complex128).ravel()
    if measured_values.shape != freq.shape or synthesized_values.shape != freq.shape:
        raise ValueError("frequency and FRF vectors must have the same length")
    return {
        "frequencies": freq.tolist(),
        "measured_magnitude": np.abs(measured_values).tolist(),
        "synthesized_magnitude": np.abs(synthesized_values).tolist(),
        "measured_label": measured_label,
        "synthesized_label": synthesized_label,
    }


def stabilization_diagram_payload(diagram: Any) -> dict[str, object]:
    """Serialize a :class:`~openfemlab.mpe.StabilizationDiagram` for the dashboard."""
    orders = [int(order) for order in getattr(diagram, "orders", ())]
    pole_levels = getattr(diagram, "poles", ())
    serialized_levels = []
    for level in pole_levels:
        serialized_levels.append(
            [
                {
                    "frequency_hz": float(pole.frequency_hz),
                    "damping_ratio": float(pole.damping_ratio),
                    "label": str(getattr(pole, "label", "new")),
                }
                for pole in level
            ]
        )
    return {
        "orders": orders,
        "poles": serialized_levels,
        "settings": dict(getattr(diagram, "settings", {})),
    }
