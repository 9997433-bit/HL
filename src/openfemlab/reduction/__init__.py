"""Model reduction beyond correlation TAM bases."""

from __future__ import annotations

from .craig_bampton import (
    CraigBamptonBasis,
    build_craig_bampton,
    fixed_interface_modes,
    reduced_craig_bampton_matrices,
)

__all__ = [
    "CraigBamptonBasis",
    "build_craig_bampton",
    "fixed_interface_modes",
    "reduced_craig_bampton_matrices",
]
