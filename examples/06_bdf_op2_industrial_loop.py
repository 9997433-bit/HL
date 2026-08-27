"""Industrial interchange loop: BDF import, OP2 round-trip, update, BDF export.

Demonstrates the Round 8 closure path documented in MS-4.5:

1. Read a Nastran bulk-data rod chain.
2. Solve nominal modes and cross-check a synthetic OP2 built from the same labels.
3. Correlate against a detuned twin and recover the stiffness scale factor.
4. Export the updated deck with ``write_bdf(material_scales=...)``.

Run::

    python examples/06_bdf_op2_industrial_loop.py
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

from openfemlab import ModalSolver
from openfemlab.cli.analysis import as_modal_result
from openfemlab.core.dofs import DofMap, DofType
from openfemlab.core.model import DOF, Material, Section
from openfemlab.core.results import TestData
from openfemlab.correlation import correlate_modal_data
from openfemlab.io import neutral_to_model, read_bdf, write_bdf
from openfemlab.io.op2 import read_op2, read_op2_modes
from openfemlab.updating import Parameter, ParameterType, update_model
from openfemlab.updating.resolver import resolve_scaling_spec

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests import _op2  # noqa: E402

BDF_TEXT = """\
GRID,11,,0.,0.,0.
GRID,22,,1.,0.,0.
GRID,33,,2.,0.,0.
GRID,44,,3.,0.,0.
MAT1,7,2.1+11,,0.3,7850.
PROD,40,7,1.0-4
CROD,100,40,11,22
CROD,200,40,22,33
CROD,300,40,33,44
"""

TRUTH_E_FACTOR = 0.85
NUM_MODES = 3


def build_model():
    neutral = read_bdf(io.StringIO(BDF_TEXT))
    material = Material(
        E=float(neutral.materials[7].E),
        density=float(neutral.materials[7].rho),
        nu=float(neutral.materials[7].nu),
    )
    section = Section(area=1.0e-4)
    model = neutral_to_model(neutral, dofs=(DOF.UX,), material=material, section=section)
    model.fix_nodes([11], (DOF.UX,))
    return neutral, model


def main() -> None:
    neutral, model = build_model()
    parameter = Parameter(
        "E.all",
        "materials.*.E",
        reference=float(model.elements[0].material.E),
        lower=0.5,
        upper=2.0,
        kind=ParameterType.STIFFNESS,
    )
    spec = resolve_scaling_spec(model, [parameter], num_modes=NUM_MODES, use_solver=False)

    nominal = ModalSolver(model).solve(num_modes=NUM_MODES)
    target = spec.scaling_model({"E.all": TRUTH_E_FACTOR})
    measurement = TestData(
        frequencies=target.frequencies,
        shapes=target.mode_shapes,
        dof_map=DofMap([22, 33, 44], [int(DofType.UX)] * 3),
    )

    grids = [
        _op2.Grid(id=11, xyz=(0.0, 0.0, 0.0)),
        _op2.Grid(id=22, xyz=(1.0, 0.0, 0.0)),
        _op2.Grid(id=33, xyz=(2.0, 0.0, 0.0)),
        _op2.Grid(id=44, xyz=(3.0, 0.0, 0.0)),
    ]
    rods = [
        _op2.Rod(id=100, property_id=40, grids=(11, 22)),
        _op2.Rod(id=200, property_id=40, grids=(22, 33)),
        _op2.Rod(id=300, property_id=40, grids=(33, 44)),
    ]
    op2_modes = read_op2_modes(
        io.BytesIO(
            _op2.modes_file(
                [
                    _op2.Mode(
                        number=index,
                        frequency_hz=float(frequency),
                        shape={
                            grid: tuple(
                                float(nominal.mode_shapes[model.dof_index(grid, DOF.UX), index - 1])
                                if dof == DOF.UX
                                else 0.0
                                for dof in (DOF.UX, DOF.UY, DOF.UZ, DOF.RX, DOF.RY, DOF.RZ)
                            )
                            for grid in (11, 22, 33, 44)
                        },
                    )
                    for index, frequency in enumerate(nominal.frequencies, start=1)
                ],
                grids=grids,
            )
        )
    )
    geometry = read_op2(
        io.BytesIO(
            _op2.geometry_file(
                grids,
                rods=rods,
                materials=[_op2.Mat1(id=7, E=parameter.reference, nu=0.3, rho=7850.0)],
                properties=[_op2.Prod(id=40, material_id=7, area=1.0e-4)],
            )
        )
    )

    before = correlate_modal_data(as_modal_result(model, nominal), measurement, strict=False)
    print(f"baseline max |df| = {before.max_abs_freq_error_pct:.2f} %")
    print(f"OP2 geometry nodes = {list(geometry.node_ids)}")
    print(f"OP2 mode-1 frequency = {op2_modes.frequencies[0]:.3f} Hz")

    result = update_model(
        spec.scaling_model,
        spec.parameter_set(),
        target.frequencies,
        target.mode_shapes,
    )
    print(f"recovered E scale = {result.parameters['E.all']:.4f} (truth {TRUTH_E_FACTOR})")

    updated_path = "updated_rod.bdf"
    write_bdf(neutral, updated_path, material_scales={7: float(result.parameters["E.all"])})
    written = read_bdf(updated_path)
    print(f"exported MAT1 E = {written.materials[7].E:.3e} Pa")


if __name__ == "__main__":
    main()
