#!/usr/bin/env python3
"""RBE2 rigid patch on a collinear rod model.

Two truss segments share a master node; the tip node is tied to the master in
axial translation so the pair behaves like a single bar with combined stiffness.
"""

from __future__ import annotations

from openfemlab import DOF, Material, ModalSolver, Model, Section
from openfemlab.core.elements import TrussElement

STEEL = Material(E=2.1e11, density=7850.0)
ROD = Section(area=1e-4)


def build_patch() -> Model:
    model = Model(dofs=(DOF.UX,), name="rbe2_patch")
    model.add_nodes([(1, 0.0), (2, 1.0), (3, 2.0)])
    model.add_element(TrussElement((1, 2), STEEL, ROD))
    model.add_element(TrussElement((2, 3), STEEL, ROD))
    model.fix(1)
    model.tie_rbe2(2, [3], components=(DOF.UX,))
    return model


def main() -> None:
    result = ModalSolver(build_patch()).solve(num_modes=3)
    print("RBE2 rod patch — first three modes [Hz]:")
    for index, frequency in enumerate(result.frequencies, start=1):
        print(f"  mode {index}: {frequency:.4f}")


if __name__ == "__main__":
    main()
