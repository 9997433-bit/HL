"""Multi-model updating (MMU) — joint residuals across shared parameters (MS-3.2)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from ..correlation.pairing import pair_modes
from .parameters import ParameterSet, UpdatableParameter
from .scaling_model import ScalingModel
from .sensitivity import ModalData
from .updater import UpdatingResult, update_model

__all__ = [
    "MMUComponent",
    "mmu_frequency_residual",
    "update_model_mmu",
]


@dataclass(frozen=True)
class MMUComponent:
    """One submodel and its target modal dataset in a joint MMU problem."""

    model: ScalingModel
    target: ModalData
    weight: float = 1.0


def mmu_frequency_residual(
    components: Sequence[MMUComponent],
    parameters: Mapping[str, float],
) -> np.ndarray:
    """Stack relative frequency residuals from every MMU component."""
    if not components:
        raise ValueError("at least one MMU component is required")
    chunks: list[np.ndarray] = []
    for component in components:
        predicted = component.model.modal_data(parameters)
        pairing = pair_modes(
            component.target.mode_shapes,
            predicted.mode_shapes,
            component.target.frequencies,
            predicted.frequencies,
            method="optimal",
        )
        if not pairing.pairs:
            raise ValueError("MMU component produced no mode pairs")
        values = []
        for pair in pairing.pairs:
            reference = component.target.frequencies[pair.test_index]
            if reference == 0.0:
                raise ValueError("target frequency must be non-zero")
            delta = (
                predicted.frequencies[pair.fe_index] - reference
            ) / reference
            values.append(float(delta) * float(component.weight))
        chunks.append(np.asarray(values, dtype=np.float64))
    return np.concatenate(chunks)


def update_model_mmu(
    components: Sequence[MMUComponent],
    parameters: Sequence[UpdatableParameter] | ParameterSet,
    **kwargs: object,
) -> UpdatingResult:
    """Run modal updating with a target merged from every MMU component.

    Each component may use a different :class:`ScalingModel` as long as the
    parameter names agree.  The updater sees one widened target built by
    concatenating the per-component mode sets (MS-3.2 MMU).
    """
    if len(components) < 2:
        raise ValueError("MMU updating requires at least two components")
    reference_model = components[0].model
    for component in components[1:]:
        if set(component.model.parameter_names) != set(reference_model.parameter_names):
            raise ValueError("every MMU component must expose the same parameter names")
    frequencies = np.concatenate(
        [component.target.frequencies for component in components]
    )
    shapes = np.hstack([component.target.mode_shapes for component in components])
    return update_model(
        reference_model,
        parameters,
        frequencies,
        shapes,
        **kwargs,
    )
