"""Craig-Bampton superelement export for downstream assembly."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .craig_bampton import CraigBamptonBasis

__all__ = ["SuperelementBundle", "build_superelement_bundle", "write_superelement_npz"]


def build_superelement_bundle(
    basis: CraigBamptonBasis,
    stiffness,
    mass,
    *,
    model_name: str = "",
    source: str = "",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Package reduced Craig-Bampton matrices and basis metadata."""
    from .craig_bampton import reduced_craig_bampton_matrices

    k_red, m_red = reduced_craig_bampton_matrices(basis, stiffness, mass)
    transform = np.asarray(basis.transformation, dtype=float)
    return {
        "kind": "craig_bampton_superelement",
        "model": model_name,
        "source": source,
        "K_red": k_red,
        "M_red": m_red,
        "T": transform,
        "interface_dofs": np.asarray(basis.interface_dofs, dtype=np.intp),
        "fixed_interface_frequencies_hz": np.asarray(
            basis.fixed_interface_frequencies_hz, dtype=float
        ),
        "n_constraint_modes": basis.n_constraint_modes,
        "n_fixed_interface_modes": basis.n_fixed_interface_modes,
        "meta": dict(meta or {}),
    }


def write_superelement_npz(
    path: str | Path,
    basis: CraigBamptonBasis,
    stiffness,
    mass,
    *,
    model_name: str = "",
    source: str = "",
    meta: dict[str, Any] | None = None,
) -> None:
    """Write a Craig-Bampton superelement bundle to NumPy ``.npz`` format."""
    bundle = build_superelement_bundle(
        basis,
        stiffness,
        mass,
        model_name=model_name,
        source=source,
        meta=meta,
    )
    payload = {
        key: value
        for key, value in bundle.items()
        if isinstance(value, np.ndarray)
    }
    payload["kind"] = np.array(bundle["kind"])
    payload["model"] = np.array(bundle["model"])
    payload["source"] = np.array(bundle["source"])
    payload["n_constraint_modes"] = np.array(bundle["n_constraint_modes"])
    payload["n_fixed_interface_modes"] = np.array(bundle["n_fixed_interface_modes"])
    if bundle["meta"]:
        for key, value in bundle["meta"].items():
            if isinstance(value, (list, tuple)):
                payload[f"meta_{key}"] = np.asarray(value)
            elif isinstance(value, np.ndarray):
                payload[f"meta_{key}"] = value
            else:
                payload[f"meta_{key}"] = np.array(value)
    np.savez_compressed(path, **payload)


class SuperelementBundle:
    """In-memory view of a superelement exported to ``.npz``."""

    def __init__(self, path: str | Path) -> None:
        with np.load(path, allow_pickle=False) as archive:
            self.path = Path(path)
            self.kind = str(archive["kind"])
            self.model = str(archive["model"])
            self.source = str(archive["source"])
            self.K_red = np.asarray(archive["K_red"], dtype=float)
            self.M_red = np.asarray(archive["M_red"], dtype=float)
            self.T = np.asarray(archive["T"], dtype=float)
            self.interface_dofs = np.asarray(archive["interface_dofs"], dtype=np.intp)
            self.fixed_interface_frequencies_hz = np.asarray(
                archive["fixed_interface_frequencies_hz"], dtype=float
            )
            self.n_constraint_modes = int(archive["n_constraint_modes"])
            self.n_fixed_interface_modes = int(archive["n_fixed_interface_modes"])
