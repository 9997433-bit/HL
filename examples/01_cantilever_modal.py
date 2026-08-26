"""Modal analysis of a steel Euler-Bernoulli cantilever beam."""

from __future__ import annotations

import numpy as np
from rich.console import Console
from rich.table import Table
from scipy.linalg import eigh


def beam_element_matrices(
    *,
    length: float,
    elastic_modulus: float,
    second_moment: float,
    density: float,
    area: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Return bending stiffness and consistent mass matrices for one beam element."""
    stiffness = elastic_modulus * second_moment / length**3 * np.array(
        (
            (12.0, 6.0 * length, -12.0, 6.0 * length),
            (6.0 * length, 4.0 * length**2, -6.0 * length, 2.0 * length**2),
            (-12.0, -6.0 * length, 12.0, -6.0 * length),
            (6.0 * length, 2.0 * length**2, -6.0 * length, 4.0 * length**2),
        )
    )
    mass = density * area * length / 420.0 * np.array(
        (
            (156.0, 22.0 * length, 54.0, -13.0 * length),
            (22.0 * length, 4.0 * length**2, 13.0 * length, -3.0 * length**2),
            (54.0, 13.0 * length, 156.0, -22.0 * length),
            (-13.0 * length, -3.0 * length**2, -22.0 * length, 4.0 * length**2),
        )
    )
    return stiffness, mass


def cantilever_frequencies(
    *,
    elements: int = 10,
    modes: int = 5,
    length: float = 1.0,
    width: float = 0.05,
    height: float = 0.01,
    elastic_modulus: float = 210.0e9,
    density: float = 7_800.0,
) -> np.ndarray:
    """Assemble the cantilever and return its first bending frequencies."""
    if elements < 1:
        raise ValueError("elements must be positive")
    free_dof = 2 * elements
    if not 1 <= modes <= free_dof:
        raise ValueError("modes must not exceed the number of free DOF")

    area = width * height
    second_moment = width * height**3 / 12.0
    element_length = length / elements
    element_stiffness, element_mass = beam_element_matrices(
        length=element_length,
        elastic_modulus=elastic_modulus,
        second_moment=second_moment,
        density=density,
        area=area,
    )

    total_dof = 2 * (elements + 1)
    stiffness = np.zeros((total_dof, total_dof))
    mass = np.zeros_like(stiffness)
    for element in range(elements):
        indices = np.arange(2 * element, 2 * element + 4)
        stiffness[np.ix_(indices, indices)] += element_stiffness
        mass[np.ix_(indices, indices)] += element_mass

    # Remove the transverse displacement and rotation at the clamped root.
    eigenvalues = eigh(
        stiffness[2:, 2:],
        mass[2:, 2:],
        subset_by_index=(0, modes - 1),
        eigvals_only=True,
        check_finite=False,
    )
    return np.sqrt(np.clip(eigenvalues, 0.0, None)) / (2.0 * np.pi)


def main() -> None:
    frequencies = cantilever_frequencies()
    table = Table(title="Steel cantilever modal analysis")
    table.add_column("Mode", justify="right")
    table.add_column("Frequency (Hz)", justify="right")
    for mode, frequency in enumerate(frequencies, start=1):
        table.add_row(str(mode), f"{frequency:.3f}")
    Console().print(table)


if __name__ == "__main__":
    main()
