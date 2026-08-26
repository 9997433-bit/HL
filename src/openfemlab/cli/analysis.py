"""Analysis plumbing shared by the CLI commands.

Bridges the solver-side objects (:class:`openfemlab.core.model.Model`,
:class:`openfemlab.solver.modal.ModalResult`) to the DOF-mapped interchange
contracts of :mod:`openfemlab.core.results`, which is the form
``openfemlab.io`` persists and ``openfemlab.correlation`` consumes.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..core.model import Model
from ..solver.modal import ModalResult as SolverModalResult
from ..solver.modal import ModalSolver
from .spec import build_model

__all__ = ["as_modal_result", "dof_map_of", "solve_spec"]


def solve_spec(
    spec: Mapping[str, Any],
    *,
    num_modes: int,
    normalization: str = "mass",
    max_frequency: float | None = None,
    sparse: bool | None = None,
) -> tuple[Model, SolverModalResult]:
    """Build the model described by ``spec`` and extract its normal modes."""
    model = build_model(spec)
    result = ModalSolver(model).solve(
        num_modes=num_modes,
        normalization=normalization,
        max_frequency=max_frequency,
        sparse=sparse,
    )
    return model, result


def dof_map_of(model: Model):
    """DOF map of ``model`` in global equation order, for the io contracts."""
    from ..io import dof_map_from_labels

    return dof_map_from_labels(model.dof_labels)


def as_modal_result(
    model: Model,
    result: SolverModalResult,
    *,
    meta: Mapping[str, Any] | None = None,
):
    """Convert a solver result into the DOF-mapped :mod:`openfemlab.core.results` form."""
    from ..core.results import ModalResult

    provenance: dict[str, Any] = {
        "solver": "openfemlab.solver.modal.ModalSolver",
        "normalization": result.normalization,
        "model": model.name,
    }
    if meta:
        provenance.update(meta)
    return ModalResult(
        frequencies=result.frequencies,
        shapes=result.mode_shapes,
        dof_map=dof_map_of(model),
        meta=provenance,
    )
