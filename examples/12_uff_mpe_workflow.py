"""Round 13: UFF FRF -> MPE -> correlate workflow (no DAQ hardware)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from openfemlab import Material, ModalSolver, Section
from openfemlab.io import write_uff
from openfemlab.io.uff import UFFFunction
from openfemlab.io.uff_frf import uff_functions_to_frf
from openfemlab.mesh.simple import bar_mesh
from openfemlab.mpe import extract_modes
from openfemlab.solver.dynamics import RayleighDamping, modal_frf


def main() -> None:
    model = bar_mesh(1.0, 12, Material(2.1e11, 7850.0), Section(1e-4))
    model.fix(0)
    modal = ModalSolver(model).solve(num_modes=4)
    damping = RayleighDamping(alpha=0.0, beta=1e-4)
    frequencies = np.linspace(20.0, 400.0, 120)
    frf = modal_frf(modal, frequencies, damping=damping, response_dofs=(11,), excitation_dofs=(11,))
    function = UFFFunction(
        frequencies_hz=frequencies,
        values=frf.data[:, 0, 0],
        response_node=12,
        response_direction=1,
        reference_node=12,
        reference_direction=1,
        ordinate_label="Receptance",
    )
    uff_path = Path("example12_measured.uff")
    write_uff(function, uff_path)
    mpe_input = uff_functions_to_frf([function])
    mpe = extract_modes(mpe_input, range(4, 13, 2), band=(frequencies[0], frequencies[-1]))
    print(f"synthesized FRF -> UFF -> MPE extracted {len(mpe.poles)} poles")
    for index, pole in enumerate(mpe.poles, start=1):
        print(f"  mode {index}: {pole.frequency_hz:.2f} Hz, zeta={pole.damping_ratio:.4f}")


if __name__ == "__main__":
    main()
