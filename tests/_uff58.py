"""ASCII UFF dataset-58 writer used by the test suite.

:mod:`openfemlab.io.uff` reads dataset 58 but does not write it — UFF *writing*
is R2-T05 scope — so the records a test needs are formatted here instead of in
the library, once, rather than once per test module.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

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
    """One complex, evenly spaced dataset-58 record (11 header records + data)."""
    frequencies = np.asarray(frequencies, dtype=float)
    values = np.asarray(values, dtype=complex)
    if frequencies.size != values.size:
        raise ValueError(f"{frequencies.size} abscissa values for {values.size} ordinates")
    if len(id_lines) != 5:
        raise ValueError("dataset 58 opens with exactly five free-text records")

    increment = float(frequencies[1] - frequencies[0])
    identification = (
        f"{4:5d}{1:10d}{0:5d}{0:10d} "
        f"{'NONE':>10}{int(response_node):10d}{int(response_direction):4d} "
        f"{'NONE':>10}{int(reference_node):10d}{int(reference_direction):4d}"
    )
    data_form = (
        f"{6:10d}{frequencies.size:10d}{1:10d}"
        f"{float(frequencies[0]):13.5E}{increment:13.5E}{0.0:13.5E}"
    )
    abscissa = f"{18:10d}{0:5d}{0:5d}{0:5d} {'Frequency':<20} {'Hz':<20}"
    ordinate = f"{8:10d}{0:5d}{0:5d}{0:5d} {ordinate_label:<20} {ordinate_units:<20}"
    unused = f"{0:10d}{0:5d}{0:5d}{0:5d} {'NONE':<20} {'NONE':<20}"

    interleaved = np.empty(2 * values.size)
    interleaved[0::2] = values.real
    interleaved[1::2] = values.imag
    data = [
        " ".join(f"{value:.12E}" for value in interleaved[start : start + 4])
        for start in range(0, interleaved.size, 4)
    ]
    records = [
        *id_lines,
        identification,
        data_form,
        abscissa,
        ordinate,
        unused,
        unused,
        *data,
    ]
    return "\n".join(["    -1", f"{58:6d}", *records, "    -1", ""])
