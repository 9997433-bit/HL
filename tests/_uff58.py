"""ASCII UFF dataset-58 records for the test suite.

A thin wrapper over :func:`openfemlab.io.format_uff` that fixes the header
fields the FRF tests care about, so the call sites read as "an FRF at this
node pair" rather than as eleven UFF header records.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from openfemlab.io import format_uff
from openfemlab.io.uff import UFFFunction

#: The five free-text records every dataset-58 block opens with.
DEFAULT_ID_LINES = ("OpenFEMLab test FRF", "NONE", "26-AUG-26", "OpenFEMLab", "receptance")


def dataset_58(
    frequencies,
    values,
    *,
    response_node: int = 1,
    response_direction: int = 1,
    reference_node: int = 1,
    reference_direction: int = 1,
    ordinate_label: str = "Receptance",
    ordinate_units: str = "m/N",
    id_lines: Sequence[str] = DEFAULT_ID_LINES,
) -> str:
    """One complex dataset-58 record (11 header records + data)."""
    frequencies = np.asarray(frequencies, dtype=float)
    values = np.asarray(values, dtype=complex)
    if frequencies.size != values.size:
        raise ValueError(f"{frequencies.size} abscissa values for {values.size} ordinates")
    if len(id_lines) != 5:
        raise ValueError("dataset 58 opens with exactly five free-text records")

    return format_uff(
        UFFFunction(
            frequencies_hz=frequencies,
            values=values,
            response_node=response_node,
            response_direction=response_direction,
            reference_node=reference_node,
            reference_direction=reference_direction,
            ordinate_label=ordinate_label,
            ordinate_units=ordinate_units,
            id_lines=tuple(id_lines),
        )
    )
