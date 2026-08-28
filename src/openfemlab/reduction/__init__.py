"""Model reduction beyond correlation TAM bases."""

from __future__ import annotations

from .craig_bampton import (
    CraigBamptonBasis,
    build_craig_bampton,
    fixed_interface_modes,
    reduced_craig_bampton_matrices,
)
from .superelement import (
    SuperelementBundle,
    build_superelement_bundle,
    write_superelement_npz,
)

__all__ = [
    "CraigBamptonBasis",
    "SuperelementBundle",
    "build_craig_bampton",
    "build_superelement_bundle",
    "fixed_interface_modes",
    "reduced_craig_bampton_matrices",
    "write_superelement_npz",
]
