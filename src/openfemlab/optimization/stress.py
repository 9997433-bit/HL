"""Stress recovery helpers for topology optimization."""

from __future__ import annotations

import numpy as np

__all__ = [
    "element_von_mises_stresses",
    "stress_p_norm",
    "stress_constraint_sensitivity",
]


def _voigt_von_mises(voigt: np.ndarray) -> float:
    """Von Mises from engineering stress Voigt ``[sxx, syy, szz, sxy, syz, szx]``."""
    values = np.asarray(voigt, dtype=float).reshape(-1)
    if values.size == 6:
        sxx, syy, szz, sxy, syz, szx = values
    elif values.size == 3:
        sxx, syy, sxy = values
        szz = syz = szx = 0.0
    else:
        raise ValueError(f"expected 3 or 6 stress components, got {values.size}")
    return float(
        np.sqrt(
            0.5
            * (
                (sxx - syy) ** 2
                + (syy - szz) ** 2
                + (szz - sxx) ** 2
                + 6.0 * (sxy**2 + syz**2 + szx**2)
            )
        )
    )


def element_von_mises_stresses(model, displacements: np.ndarray) -> np.ndarray:
    """Per-element von Mises stress for elements exposing ``stress(...)``."""
    stresses = np.zeros(model.num_elements, dtype=float)
    u = np.asarray(displacements, dtype=float).reshape(-1)
    for index, element in enumerate(model.elements):
        if not hasattr(element, "stress"):
            continue
        coords = model.node_coords(element.node_ids)
        dofs = element.global_dofs(model)
        local = u[dofs]
        try:
            voigt = np.asarray(element.stress(coords, local), dtype=float).reshape(-1)
        except Exception:
            continue
        stresses[index] = _voigt_von_mises(voigt)
    return stresses


def stress_p_norm(
    stresses: np.ndarray,
    volumes: np.ndarray,
    *,
    limit: float,
    exponent: float = 8.0,
) -> float:
    """Global p-norm stress measure ``(sum V (sigma/limit)^p)^(1/p) - 1``."""
    limit = float(limit)
    if limit <= 0.0:
        raise ValueError("stress limit must be positive")
    sigma = np.maximum(np.asarray(stresses, dtype=float).reshape(-1), 0.0)
    vols = np.asarray(volumes, dtype=float).reshape(-1)
    total = float(vols.sum()) or 1.0
    ratio = sigma / limit
    aggregate = float(np.sum(vols * np.power(ratio, exponent)) / total) ** (1.0 / exponent)
    return aggregate - 1.0


def stress_constraint_sensitivity(
    stresses: np.ndarray,
    volumes: np.ndarray,
    design_densities: np.ndarray,
    *,
    limit: float,
    exponent: float = 8.0,
    penalization: float = 3.0,
) -> np.ndarray:
    """Approximate ``d g / d rho`` for the p-norm stress constraint."""
    limit = float(limit)
    rho = np.maximum(np.asarray(design_densities, dtype=float).reshape(-1), 1e-3)
    sigma = np.maximum(np.asarray(stresses, dtype=float).reshape(-1), 1e-12)
    vols = np.asarray(volumes, dtype=float).reshape(-1)
    total = float(vols.sum()) or 1.0
    ratio = sigma / limit
    g_inner = float(np.sum(vols * np.power(ratio, exponent)) / total)
    if g_inner <= 1e-30:
        return np.zeros_like(rho)
    prefactor = (g_inner ** (1.0 / exponent - 1.0)) * (exponent / total) / limit
    return (
        prefactor
        * vols
        * np.power(ratio, exponent - 1.0)
        * penalization
        * np.power(rho, penalization - 1.0)
        * sigma
    )
