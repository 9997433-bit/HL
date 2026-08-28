#!/usr/bin/env python3
"""RBE3 weighted interpolation on a collinear rod patch.

Independent nodes 1 and 2 carry the structural path; dependent tip node 3 is
tied by RBE3 so its UX is the average of the two independents.
"""

from __future__ import annotations

from openfemlab import DOF, Material, ModalSolver, Model, Section
from openfemlab.core.elements import TrussElement

STEEL = Material(E=2.1e11, density=7850.0)
ROD = Section(area=1e-4)


def build_patch() -> Model:
    model = Model(dofs=(DOF.UX,), name="rbe3_patch")
    model.add_nodes([(1, 0.0), (2, 1.0), (3, 0.5)])
    model.add_element(TrussElement((1, 2), STEEL, ROD))
    model.fix(1)
    model.tie_rbe3(3, [1, 2], components=(DOF.UX,), weight=1.0)
    return model


def main() -> None:
    result = ModalSolver(build_patch()).solve(num_modes=2)
    shape = result.mode_shapes[:, 0]
    model = build_patch()
    print("RBE3 rod patch — first mode [Hz]:", f"{result.frequencies[0]:.4f}")
    print(
        "dependent UX vs mean(independents):",
        f"{shape[model.dof_index(3, DOF.UX)]:.6f}",
        "vs",
        f"{0.5 * (shape[model.dof_index(1, DOF.UX)] + shape[model.dof_index(2, DOF.UX)]):.6f}",
    )


if __name__ == "__main__":
    main()
