"""Import a meshio QUAD4 plate, bind shell elements, and solve its modes.

Install the optional mesh reader before running this example:

    python -m pip install -e ".[io]"
    python examples/04_imported_shell_modal.py
"""

from __future__ import annotations

from os import PathLike
from pathlib import Path

import numpy as np

from openfemlab import Material, ModalSolver
from openfemlab.io import neutral_to_model, read_meshio

MESH_FILE = Path(__file__).with_name("data") / "04_plate_quad.vtk"
ALUMINUM = Material(E=70.0e9, nu=0.33, density=2700.0, name="aluminum")


def solve_imported_plate(
    mesh_file: str | PathLike[str] = MESH_FILE,
    *,
    num_modes: int = 6,
):
    """Return the neutral mesh, solver model, and plate modal result."""

    neutral = read_meshio(mesh_file)
    model = neutral_to_model(
        neutral,
        material=ALUMINUM,
        thickness=4.0e-3,
        quad4_as="shell",
        name="imported-cantilever-plate",
    )

    # Mesh formats do not carry OpenFEMLab supports. Clamp the x-min edge.
    root_x = float(np.min(neutral.nodes[:, 0]))
    root_nodes = [
        int(node_id)
        for node_id, coordinates in zip(neutral.node_ids, neutral.nodes, strict=True)
        if np.isclose(coordinates[0], root_x)
    ]
    model.fix_nodes(root_nodes)

    result = ModalSolver(model).solve(num_modes=num_modes)
    return neutral, model, result


def main() -> None:
    neutral, model, result = solve_imported_plate()
    print(
        f"Imported {neutral.n_nodes} nodes and {neutral.n_elements} QUAD4 elements; "
        f"bound {model.num_elements} shell elements."
    )
    for mode, frequency in enumerate(result.frequencies, start=1):
        print(f"mode {mode}: {frequency:.3f} Hz")


if __name__ == "__main__":
    main()
