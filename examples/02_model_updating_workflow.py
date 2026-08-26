"""End-to-end model updating workflow, driven exactly like the CLI drives it.

The script walks the full FEMtools-style loop on a steel cantilever:

1. write the *as-designed* model specification that ``openfemlab modal`` reads;
2. synthesise a modal test by perturbing the truth and measuring UY at a few
   sensor positions, the way an accelerometer grid samples a structure;
3. correlate the as-designed model against that test (MAC and frequency error);
4. update two dimensionless parameters -- a stiffness and a mass scaling --
   with the sensitivity-based updater;
5. correlate again and write the updated specification back out.

Every step is a thin wrapper around the same public API the CLI calls, so the
equivalent shell session is printed at the end.

Run with::

    python examples/02_model_updating_workflow.py [--output-dir DIR]
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from openfemlab.cli.analysis import as_modal_result, dof_map_of, solve_spec
from openfemlab.cli.spec import build_model, scaled
from openfemlab.core.dofs import DofMap, DofType
from openfemlab.core.results import TestData
from openfemlab.correlation import align_dof_maps, correlate_modal_data
from openfemlab.io import write_data, write_test_data
from openfemlab.solver.modal import ModalSolver
from openfemlab.updating import ModelUpdater, ParameterSet, UpdatableParameter, UpdatingOptions
from openfemlab.updating.sensitivity import ModalData

#: As-designed model, in the declarative form ``openfemlab modal`` consumes.
MODEL_SPEC: dict[str, Any] = {
    "name": "steel cantilever",
    "materials": {"steel": {"E": 2.1e11, "density": 7850.0, "nu": 0.3}},
    "sections": {"strip": {"area": 1.0e-4, "inertia_z": 8.3333333e-10}},
    "mesh": {
        "type": "beam",
        "length": 1.0,
        "num_elements": 20,
        "support": "cantilever",
        "material": "steel",
        "section": "strip",
    },
}

#: The "true" structure the test was measured on: softer and slightly heavier.
TRUE_FACTORS = {"materials.steel.E": 0.88, "sections.strip.area": 1.05}

#: Sensors: one accelerometer every fourth node, measuring the UY direction.
SENSOR_NODES = tuple(range(4, 21, 4))

NUM_MODES = 4


def synthesize_test_data(spec: dict[str, Any]) -> TestData:
    """Measure the perturbed structure on the sensor grid."""
    model = build_model(scaled(spec, TRUE_FACTORS))
    result = ModalSolver(model).solve(num_modes=NUM_MODES)
    rows = [dof_map_of(model).index_of(node, DofType.UY) for node in SENSOR_NODES]
    return TestData(
        frequencies=result.frequencies,
        shapes=result.mode_shapes[rows, :],
        dof_map=DofMap(SENSOR_NODES, [int(DofType.UY)] * len(SENSOR_NODES)),
        damping=np.full(NUM_MODES, 0.01),
        meta={"description": "synthetic modal test", "sensors": list(SENSOR_NODES)},
    )


def correlate(spec: dict[str, Any], test: TestData, label: str) -> None:
    """Print the FE/test correlation table for one model state."""
    model, result = solve_spec(spec, num_modes=NUM_MODES)
    report = correlate_modal_data(
        as_modal_result(model, result), test, strict=False, mac_threshold=0.1
    )
    print(f"\n--- correlation, {label} ---")
    print(report.pairing.table())
    print(
        f"mean MAC {report.mean_mac:.4f} | min MAC {report.min_mac:.4f} | "
        f"max |df| {report.max_abs_freq_error_pct:.3f} %"
    )


def run_updating(spec: dict[str, Any], test: TestData):
    """Tune the stiffness and mass scaling factors against the measured modes."""
    targets = {
        "youngs_modulus": "materials.steel.E",
        "cross_section": "sections.strip.area",
    }
    reference_model = build_model(spec)
    fe_rows, test_rows = align_dof_maps(dof_map_of(reference_model), test.dof_map, strict=False)

    def evaluate(factors) -> ModalData:
        patched = scaled(spec, {path: factors[name] for name, path in targets.items()})
        _, result = solve_spec(patched, num_modes=NUM_MODES)
        return ModalData(result.frequencies, result.mode_shapes[fe_rows, :])

    parameters = ParameterSet(
        [
            UpdatableParameter(name="youngs_modulus", lower=0.6, upper=1.5, kind="stiffness"),
            UpdatableParameter(name="cross_section", lower=0.8, upper=1.3, kind="mass"),
        ]
    )
    updater = ModelUpdater(
        evaluate,
        parameters,
        test.frequencies,
        test.shapes[test_rows, :],
        options=UpdatingOptions(max_iterations=25, shape_weight=1.0),
    )
    result = updater.run()
    return result, {name: result.parameters[name] for name in targets}, targets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--output-dir",
        default=None,
        help="where to write the generated files (default: a temporary directory)",
    )
    args = parser.parse_args(argv)
    directory = Path(args.output_dir or tempfile.mkdtemp(prefix="openfemlab-"))
    directory.mkdir(parents=True, exist_ok=True)

    model_path = directory / "cantilever.yaml"
    test_path = directory / "measured.yaml"
    config_path = directory / "updating.yaml"
    updated_path = directory / "cantilever.updated.yaml"

    write_data(MODEL_SPEC, model_path)
    test = synthesize_test_data(MODEL_SPEC)
    write_test_data(test, test_path)
    print(f"model spec  : {model_path}")
    print(f"measured    : {test_path}")
    print("test frequencies [Hz]:", np.round(test.frequencies, 4))

    correlate(MODEL_SPEC, test, "as designed")

    result, factors, targets = run_updating(MODEL_SPEC, test)
    print(f"\n--- updating: {result.message} after {result.iterations} iterations ---")
    print(
        f"cost {result.initial_cost:.4e} -> {result.final_cost:.4e} "
        f"({100.0 * result.cost_reduction:.2f} % reduction)"
    )
    for name, path in targets.items():
        print(f"{name:<16} {path:<22} factor {factors[name]:.4f}")
    truth = TRUE_FACTORS["materials.steel.E"] / TRUE_FACTORS["sections.strip.area"]
    found = factors["youngs_modulus"] / factors["cross_section"]
    print(
        f"\nBending frequencies only constrain E/A, so the recovered ratio is what "
        f"matters: {found:.4f} against the true {truth:.4f}."
    )

    updated_spec = scaled(MODEL_SPEC, {targets[name]: factors[name] for name in targets})
    write_data(updated_spec, updated_path)
    correlate(updated_spec, test, "after updating")
    print(f"\nupdated spec: {updated_path}")

    write_data(updating_config(model_path, test_path, targets), config_path)
    print(
        "\nThe same workflow from the shell:\n"
        f"  openfemlab modal {model_path} -n {NUM_MODES}\n"
        f"  openfemlab correlate {model_path} {test_path} --partial-dofs\n"
        f"  openfemlab update {config_path} -o {updated_path}\n"
        f"  openfemlab correlate {updated_path} {test_path} --partial-dofs --require-mac 0.99"
    )
    return 0


def updating_config(model_path: Path, test_path: Path, targets) -> dict[str, Any]:
    """The ``openfemlab update`` configuration equivalent to :func:`run_updating`."""
    bounds = {"youngs_modulus": (0.6, 1.5, "stiffness"), "cross_section": (0.8, 1.3, "mass")}
    return {
        "model": str(model_path),
        "parameters": [
            {
                "name": name,
                "target": path,
                "lower": bounds[name][0],
                "upper": bounds[name][1],
                "kind": bounds[name][2],
            }
            for name, path in targets.items()
        ],
        "target": {"file": str(test_path)},
        "modes": NUM_MODES,
        "partial_dofs": True,
        "options": {"max_iterations": 25, "shape_weight": 1.0},
    }


if __name__ == "__main__":
    raise SystemExit(main())
