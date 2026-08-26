"""Analysis plumbing shared by the CLI commands.

Attaches a :class:`~openfemlab.core.dofs.DofMap` and provenance to the
:class:`~openfemlab.core.results.ModalResult` the solver returns, which is the
form ``openfemlab.io`` persists and ``openfemlab.correlation`` consumes.

Numerical correlation intentionally does not live here: CLI commands delegate
MAC calculation, mode pairing, and reporting to :mod:`openfemlab.correlation`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..core.model import Model
from ..core.results import ModalResult
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
) -> tuple[Model, ModalResult]:
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
    result: ModalResult,
    *,
    meta: Mapping[str, Any] | None = None,
) -> ModalResult:
    """Attach ``model``'s DOF map and solver provenance to ``result``."""
    provenance: dict[str, Any] = {
        "solver": "openfemlab.solver.modal.ModalSolver",
        "normalization": result.normalization,
        "model": model.name,
    }
    if meta:
        provenance.update(meta)
    return result.with_dof_map(dof_map_of(model), meta=provenance)
