"""Internal FE solver layer (L2): elements, assembly, boundary conditions.

The internal solver is *one producer* of results among many — the platform
also consumes matrices/results imported through ``openfemlab.io``. All
outputs are ``scipy.sparse`` matrices ordered by the model's ``DofMap``.

Round 1 defines the extension seam; Round 2 implements ROD2/BEAM2 elements,
vectorized COO assembly of K and M, and penalty/elimination BCs. Shells and
solids follow in Round 3.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
import numpy.typing as npt
from scipy import sparse

from openfemlab.core.neutral import NeutralModel

from .dynamics import (
    ComplexModalResult,
    DampingModel,
    FrequencyResponse,
    ModalDamping,
    RayleighDamping,
    StructuralDamping,
    complex_modal_frf,
    complex_modes,
    direct_frf,
    harmonic_response,
    modal_frf,
)
from .modal import ModalResult, ModalSolver

__all__ = [
    "ComplexModalResult",
    "DampingModel",
    "ElementFormulation",
    "FrequencyResponse",
    "ModalDamping",
    "ModalResult",
    "ModalSolver",
    "RayleighDamping",
    "StructuralDamping",
    "assemble_km",
    "complex_modal_frf",
    "complex_modes",
    "direct_frf",
    "harmonic_response",
    "modal_frf",
]


class ElementFormulation(ABC):
    """Extension point: one element type's local matrices.

    Implementations are stateless; ``solver.assembly`` scatters the local
    matrices into the global sparse system. Third-party elements subclass
    this without touching assembly code.
    """

    #: DOFs per node this formulation carries (e.g. 6 for a 3-D beam).
    dofs_per_node: int

    @abstractmethod
    def local_stiffness(
        self,
        coords: npt.NDArray[np.float64],
        material: object,
        prop: object,
    ) -> npt.NDArray[np.float64]:
        """Element stiffness in global axes, shape ``(k, k)``."""

    @abstractmethod
    def local_mass(
        self,
        coords: npt.NDArray[np.float64],
        material: object,
        prop: object,
    ) -> npt.NDArray[np.float64]:
        """Consistent element mass in global axes, shape ``(k, k)``."""


def assemble_km(model: NeutralModel) -> tuple[sparse.csr_array, sparse.csr_array]:
    """Assemble global stiffness and mass matrices ``(K, M)``.

    Ordering follows ``model.dof_map``. Implemented in Round 2 via vectorized
    COO triplet accumulation (no per-element Python loops on hot paths).
    """
    raise NotImplementedError("internal solver assembly lands in Round 2")
