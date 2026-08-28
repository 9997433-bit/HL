"""Bridge UFF dataset-58 FRF records to the solver frequency-response contract."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from ..solver.dynamics import FrequencyResponse
from .uff import UFFFunction

__all__ = ["uff_function_to_frf", "uff_functions_to_frf"]


def uff_function_to_frf(
    function: UFFFunction,
    *,
    response_dof: int = 0,
    excitation_dof: int = 0,
) -> FrequencyResponse:
    """Wrap one dataset-58 record as a single-input single-output receptance."""
    data = np.asarray(function.values, dtype=complex).reshape(-1, 1, 1)
    return FrequencyResponse(
        frequencies=np.asarray(function.frequencies_hz, dtype=float),
        data=data,
        response_dofs=np.asarray([response_dof], dtype=int),
        excitation_dofs=np.asarray([excitation_dof], dtype=int),
        response_type="receptance",
    )


def uff_functions_to_frf(
    functions: Sequence[UFFFunction],
    *,
    response_dofs: Sequence[int] | None = None,
    excitation_dof: int = 0,
) -> FrequencyResponse:
    """Stack multiple dataset-58 records into one multi-output receptance matrix."""
    if not functions:
        raise ValueError("functions must not be empty")
    frequencies = np.asarray(functions[0].frequencies_hz, dtype=float)
    responses = []
    dof_ids = []
    for index, function in enumerate(functions):
        if function.frequencies_hz.shape != frequencies.shape or not np.allclose(
            function.frequencies_hz, frequencies
        ):
            raise ValueError("all UFF functions must share the same frequency line")
        responses.append(np.asarray(function.values, dtype=complex).reshape(-1))
        dof_ids.append(
            int(response_dofs[index])
            if response_dofs is not None
            else int(function.response_node * 10 + function.response_direction)
        )
    data = np.stack(responses, axis=1)[:, :, np.newaxis]
    return FrequencyResponse(
        frequencies=frequencies,
        data=data,
        response_dofs=np.asarray(dof_ids, dtype=int),
        excitation_dofs=np.asarray([excitation_dof], dtype=int),
        response_type="receptance",
    )
