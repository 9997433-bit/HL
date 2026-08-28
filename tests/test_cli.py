"""End-to-end coverage of the ``openfemlab`` command-line interface."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from openfemlab.cli.main import main
from openfemlab.cli.spec import SpecError, build_model, lookup, scaled
from openfemlab.core.dofs import DofMap, DofType
from openfemlab.core.results import TestData as ModalTestData
from openfemlab.io import read_data, write_data, write_test_data
from openfemlab.solver.modal import ModalSolver

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_02 = REPOSITORY_ROOT / "examples" / "02_model_updating_workflow.py"
TOPOPT_TET_SPEC = REPOSITORY_ROOT / "examples" / "specs" / "topopt_tet_cantilever.yaml"
TOPOPT_PLATE_SPEC = REPOSITORY_ROOT / "examples" / "specs" / "topopt_plate_quad.yaml"

# Steel strip, 1 m long: the analytic first cantilever frequency is 8.3552 Hz.
CANTILEVER: dict[str, Any] = {
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

SENSOR_NODES = (4, 8, 12, 16, 20)


@pytest.fixture()
def model_file(tmp_path):
    path = tmp_path / "cantilever.yaml"
    write_data(CANTILEVER, path)
    return path


@pytest.fixture()
def test_file(tmp_path):
    """Synthetic modal test measured on a structure 12% softer and 5% heavier."""
    from openfemlab.cli.analysis import dof_map_of

    model = build_model(
        scaled(CANTILEVER, {"materials.steel.E": 0.88, "sections.strip.area": 1.05})
    )
    result = ModalSolver(model).solve(num_modes=4)
    rows = [dof_map_of(model).index_of(node, DofType.UY) for node in SENSOR_NODES]
    data = ModalTestData(
        frequencies=result.frequencies,
        shapes=result.mode_shapes[rows, :],
        dof_map=DofMap(SENSOR_NODES, [int(DofType.UY)] * len(SENSOR_NODES)),
    )
    path = tmp_path / "measured.yaml"
    write_test_data(data, path)
    return path


# ------------------------------------------------------------------ the spec


def test_named_material_and_section_tables_are_resolved():
    model = build_model(CANTILEVER)
    assert model.num_nodes == 21
    assert model.num_elements == 20
    assert model.constrained_dofs.size == 3  # the clamped root node


def test_custom_mesh_builds_springs_supports_and_point_masses():
    model = build_model(
        {
            "name": "two dof chain",
            "mesh": {
                "type": "custom",
                "dofs": ["UX"],
                "nodes": [[0, 0.0], [1, 1.0], [2, 2.0]],
                "elements": [
                    {"type": "spring", "nodes": [0, 1], "stiffness": 1000.0},
                    {"type": "spring", "nodes": [1, 2], "stiffness": 1000.0},
                ],
            },
            "supports": [{"node": 0}],
            "point_masses": [{"node": 1, "mass": 1.0}, {"node": 2, "mass": 1.0}],
        }
    )
    frequencies = ModalSolver(model).solve(num_modes=2).frequencies
    # Analytic fixed-free 2-DOF chain: omega = 2 sqrt(k/m) sin((2i-1) pi / 10).
    expected = 2.0 * np.sqrt(1000.0) * np.sin(np.array([1, 3]) * np.pi / 10.0) / (2.0 * np.pi)
    assert frequencies == pytest.approx(expected, rel=1e-10)


def test_scaled_multiplies_the_addressed_leaf_only():
    patched = scaled(CANTILEVER, {"materials.steel.E": 0.5})
    assert lookup(patched, "materials.steel.E") == pytest.approx(1.05e11)
    assert lookup(patched, "sections.strip.area") == lookup(CANTILEVER, "sections.strip.area")
    assert lookup(CANTILEVER, "materials.steel.E") == pytest.approx(2.1e11)


@pytest.mark.parametrize(
    ("spec", "message"),
    [
        ({"mesh": {"type": "wing"}}, "unknown mesh type"),
        ({"mesh": {"type": "beam", "length": 1.0, "material": "alu"}}, "unknown material"),
    ],
)
def test_malformed_specs_raise_spec_error(spec, message):
    with pytest.raises(SpecError, match=message):
        build_model(spec)


def test_lookup_reports_the_offending_path():
    with pytest.raises(SpecError, match="mesh.thickness"):
        lookup(CANTILEVER, "mesh.thickness")


def test_tet_block_spec_builds_solid_cantilever():
    model = build_model(read_data(TOPOPT_TET_SPEC))
    assert model.num_elements == 6
    assert model.num_dofs == model.num_nodes * 3
    assert model.load_vector().sum() != 0.0


def test_quad_plate_spec_builds_for_topopt():
    model = build_model(read_data(TOPOPT_PLATE_SPEC))
    assert model.num_elements == 2
    assert model.load_vector().sum() != 0.0


def test_topopt_runs_on_tet_block_spec(capsys):
    assert (
        main(
            [
                "--no-color",
                "topopt",
                str(TOPOPT_TET_SPEC),
                "--vol-frac",
                "0.5",
                "--max-iter",
                "10",
                "--filter-radius",
                "0.35",
                "--heaviside-beta",
                "8",
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "SIMP topology" in out
    assert "tet cantilever topopt" in out


def test_topopt_runs_on_quad_plate_spec(capsys):
    assert (
        main(
            [
                "--no-color",
                "topopt",
                str(TOPOPT_PLATE_SPEC),
                "--vol-frac",
                "0.5",
                "--max-iter",
                "10",
            ]
        )
        == 0
    )
    assert "quad plate topopt" in capsys.readouterr().out


# ----------------------------------------------------------------- the modal


def test_modal_prints_the_analytic_cantilever_frequency(model_file, capsys):
    assert main(["--no-color", "modal", str(model_file), "-n", "3"]) == 0
    out = capsys.readouterr().out
    assert "steel cantilever" in out
    assert "8.35517" in out


def test_modal_json_report_and_result_file(model_file, tmp_path, capsys):
    output = tmp_path / "modes.json"
    assert (
        main(
            [
                "--no-color",
                "modal",
                str(model_file),
                "-n",
                "4",
                "--format",
                "json",
                "-o",
                str(output),
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert [mode["mode"] for mode in report["modes"]] == [1, 2, 3, 4]
    assert report["modes"][0]["frequency_hz"] == pytest.approx(8.35517, rel=1e-5)
    assert report["model"]["free_dofs"] == 60

    from openfemlab.io import read_modal_result

    stored = read_modal_result(output)
    assert stored.n_modes == 4
    assert stored.shapes.shape == (63, 4)


def test_modal_defaults_to_the_most_excited_direction(model_file, capsys):
    main(["--no-color", "modal", str(model_file), "-n", "2", "--format", "json"])
    report = json.loads(capsys.readouterr().out)
    assert report["analysis"]["direction"] == "UY"


def test_modal_reports_a_missing_file_without_a_traceback(tmp_path, capsys):
    assert main(["--no-color", "modal", str(tmp_path / "absent.yaml")]) == 1
    assert "error:" in capsys.readouterr().err


# ------------------------------------------------------------- the correlate


def test_correlate_pairs_every_mode_and_reports_the_stiffness_bias(
    model_file, test_file, capsys
):
    assert (
        main(
            [
                "--no-color",
                "correlate",
                str(model_file),
                str(test_file),
                "-n",
                "6",
                "--partial-dofs",
                "--format",
                "json",
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["summary"]["n_paired"] == 4
    assert report["summary"]["min_mac"] == pytest.approx(1.0, abs=1e-9)
    # A uniform property change leaves the shapes intact and biases every
    # frequency by the same amount.
    assert report["summary"]["max_abs_freq_error_pct"] == pytest.approx(9.233, abs=1e-2)
    assert report["unpaired_fe"] == [4, 5]


def test_correlate_gate_fails_on_the_as_designed_model(model_file, test_file, capsys):
    code = main(
        [
            "--no-color",
            "correlate",
            str(model_file),
            str(test_file),
            "-n",
            "4",
            "--partial-dofs",
            "--require-frequency",
            "1.0",
        ]
    )
    assert code == 3
    assert "exceeds the allowed" in capsys.readouterr().err


def test_correlate_accepts_a_stored_modal_result(model_file, test_file, tmp_path, capsys):
    modes = tmp_path / "fe_modes.yaml"
    main(["--no-color", "--quiet", "modal", str(model_file), "-n", "4", "-o", str(modes)])
    capsys.readouterr()

    assert (
        main(
            [
                "--no-color",
                "correlate",
                str(modes),
                str(test_file),
                "--partial-dofs",
                "--format",
                "json",
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["fe"]["source"] == str(modes)
    assert report["summary"]["n_paired"] == 4


# ---------------------------------------------------------------- the update


def _updating_config(model_file, test_file, **options) -> dict[str, Any]:
    return {
        "model": str(model_file),
        "parameters": [
            {"name": "stiffness", "target": "materials.steel.E", "lower": 0.6, "upper": 1.5},
            {
                "name": "mass",
                "target": "sections.strip.area",
                "lower": 0.8,
                "upper": 1.3,
                "kind": "mass",
            },
        ],
        "target": {"file": str(test_file)},
        "modes": 4,
        "partial_dofs": True,
        "options": {"max_iterations": 25, "shape_weight": 0.0, **options},
    }


def test_update_recovers_the_identifiable_parameter_ratio(
    model_file, test_file, tmp_path, capsys
):
    config = tmp_path / "updating.yaml"
    write_data(_updating_config(model_file, test_file), config)
    updated = tmp_path / "cantilever.updated.yaml"

    assert (
        main(
            [
                "--no-color",
                "update",
                str(config),
                "-o",
                str(updated),
                "--format",
                "json",
                "--strict",
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["converged"] is True
    factors = {parameter["name"]: parameter["factor"] for parameter in report["parameters"]}
    # Bending frequencies only constrain E/A, so that ratio is what is
    # identifiable from a frequency-only run.
    assert factors["stiffness"] / factors["mass"] == pytest.approx(0.88 / 1.05, rel=1e-4)
    assert report["correlation"]["final"]["max_abs_freq_error_pct"] < 1e-4

    spec = read_data(updated)
    assert spec["materials"]["steel"]["E"] == pytest.approx(2.1e11 * factors["stiffness"])


def test_updated_specification_correlates_with_the_test(model_file, test_file, tmp_path, capsys):
    config = tmp_path / "updating.yaml"
    write_data(_updating_config(model_file, test_file, shape_weight=1.0), config)
    updated = tmp_path / "cantilever.updated.yaml"
    main(["--no-color", "--quiet", "update", str(config), "-o", str(updated), "--format", "json"])
    capsys.readouterr()

    assert (
        main(
            [
                "--no-color",
                "correlate",
                str(updated),
                str(test_file),
                "-n",
                "4",
                "--partial-dofs",
                "--require-mac",
                "0.99",
                "--require-frequency",
                "0.01",
            ]
        )
        == 0
    )


def test_update_rejects_an_unknown_option(model_file, test_file, tmp_path, capsys):
    config = tmp_path / "updating.yaml"
    write_data(_updating_config(model_file, test_file, relaxation=0.5), config)
    assert main(["--no-color", "update", str(config)]) == 1
    assert "unknown updating options: relaxation" in capsys.readouterr().err


def test_update_requires_a_numeric_parameter_target(model_file, test_file, tmp_path, capsys):
    config = _updating_config(model_file, test_file)
    config["parameters"][0]["target"] = "materials.steel"
    path = tmp_path / "updating.yaml"
    write_data(config, path)
    assert main(["--no-color", "update", str(path)]) == 1
    assert "does not address a number" in capsys.readouterr().err


# ----------------------------------------------------------- the real process


def _subprocess_environment() -> dict[str, str]:
    """Make child interpreters import this checkout, even with an editable install elsewhere."""
    environment = os.environ.copy()
    current = environment.get("PYTHONPATH")
    paths = [str(REPOSITORY_ROOT / "src")]
    if current:
        paths.append(current)
    environment["PYTHONPATH"] = os.pathsep.join(paths)
    return environment


@pytest.fixture(scope="module")
def example_02_fixtures(tmp_path_factory) -> Path:
    """Generate the model, test data, and updating config documented by example 02."""
    output_dir = tmp_path_factory.mktemp("example-02")
    completed = subprocess.run(
        [sys.executable, str(EXAMPLE_02), "--output-dir", str(output_dir)],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=_subprocess_environment(),
    )
    assert completed.returncode == 0, completed.stderr
    for name in ("cantilever.yaml", "measured.yaml", "updating.yaml"):
        assert (output_dir / name).is_file()
    return output_dir


def _run_cli(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "openfemlab.cli", "--no-color", *(str(arg) for arg in args)],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=_subprocess_environment(),
    )


def test_modal_subprocess_emits_json(example_02_fixtures):
    completed = _run_cli(
        "modal",
        example_02_fixtures / "cantilever.yaml",
        "-n",
        4,
        "--format",
        "json",
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["command"] == "modal"
    assert report["model"]["name"] == "steel cantilever"
    assert report["analysis"]["num_modes"] == 4
    assert report["modes"][0]["frequency_hz"] == pytest.approx(8.35517, rel=1e-5)


def test_correlate_subprocess_emits_json_and_gate_exit_code(example_02_fixtures):
    arguments = (
        "correlate",
        example_02_fixtures / "cantilever.yaml",
        example_02_fixtures / "measured.yaml",
        "-n",
        4,
        "--partial-dofs",
        "--format",
        "json",
    )
    completed = _run_cli(*arguments)

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["command"] == "correlate"
    assert report["summary"]["n_paired"] == 4
    assert report["summary"]["min_mac"] == pytest.approx(1.0, abs=1e-9)
    assert report["summary"]["max_abs_freq_error_pct"] == pytest.approx(9.233, abs=1e-2)

    rejected = _run_cli(*arguments, "--require-frequency", 1.0)
    assert rejected.returncode == 3
    assert json.loads(rejected.stdout)["command"] == "correlate"
    assert "exceeds the allowed" in rejected.stderr


def test_update_subprocess_emits_json(example_02_fixtures):
    updated = example_02_fixtures / "subprocess.updated.yaml"
    completed = _run_cli(
        "update",
        example_02_fixtures / "updating.yaml",
        "--output",
        updated,
        "--format",
        "json",
        "--strict",
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["command"] == "update"
    assert report["converged"] is True
    assert report["correlation"]["final"]["max_abs_freq_error_pct"] < 1e-4
    assert {parameter["name"] for parameter in report["parameters"]} == {
        "youngs_modulus",
        "cross_section",
    }
    assert updated.is_file()


# ------------------------------------------------------------------ the shell


def test_version_and_info(capsys):
    import openfemlab

    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == openfemlab.__version__

    assert main(["--no-color", "info"]) == 0
    assert "correlation" in capsys.readouterr().out


def test_help_lists_every_analysis_command(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    for command in ("modal", "correlate", "update"):
        assert command in out
