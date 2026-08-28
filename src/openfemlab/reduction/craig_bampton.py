"""Craig-Bampton component mode synthesis skeleton (Round 17)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from openfemlab.correlation.reduction import ReductionBasis, guyan_reduction

__all__ = ["CraigBamptonBasis", "build_craig_bampton"]


@dataclass(frozen=True, slots=True)
class CraigBamptonBasis:
    """CMS basis built from interface Guyan modes and optional fixed-interface modes."""

    interface_dofs: np.ndarray
    guyan: ReductionBasis
    fixed_interface_modes: np.ndarray | None
    num_modes: int

    @property
    def transformation(self) -> np.ndarray:
        """Primary reduction matrix ``T`` (Guyan when ``num_modes == 0``)."""
        return np.asarray(self.guyan.transformation, dtype=float)


def build_craig_bampton(
    stiffness,
    mass,
    interface_dofs,
    *,
    num_modes: int = 0,
) -> CraigBamptonBasis:
    """Build a Craig-Bampton skeleton via static condensation onto interface DOFs.

    When ``num_modes == 0`` the basis reduces to pure Guyan constraint modes on
    the interface partition.  Positive ``num_modes`` reserves the extension
    point for fixed-interface normal modes in a later release.
    """
    interface = np.asarray(interface_dofs, dtype=np.intp).reshape(-1)
    if interface.size == 0:
        raise ValueError("interface_dofs must be non-empty")
    if num_modes < 0:
        raise ValueError("num_modes must be >= 0")
    if num_modes > 0:
        raise NotImplementedError(
            "fixed-interface normal modes are reserved for a future release; "
            "use num_modes=0 for the Guyan constraint-mode skeleton"
        )
    _ = mass
    guyan = guyan_reduction(stiffness, interface)
    return CraigBamptonBasis(
        interface_dofs=interface,
        guyan=guyan,
        fixed_interface_modes=None,
        num_modes=int(num_modes),
    )
