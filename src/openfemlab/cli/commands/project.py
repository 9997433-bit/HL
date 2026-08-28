"""``openfemlab project`` — CAE-style workspace scaffolding."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..console import Reporter

NAME = "project"
HELP = "create a FEMtools-style project workspace"


def add_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        NAME,
        help=HELP,
        description=(
            "Scaffold a project folder with models/, measurements/, and reports/ — "
            "the same layout most CAE workflows use (project → analysis → post)."
        ),
    )
    project_sub = parser.add_subparsers(dest="project_command", metavar="SUBCOMMAND", required=True)
    init_parser = project_sub.add_parser(
        "init",
        help="create models/, measurements/, reports/ and project.yaml",
    )
    init_parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="directory to initialize (default: current directory)",
    )
    init_parser.add_argument(
        "--name",
        default="my-project",
        help="project name stored in project.yaml",
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite project.yaml if it already exists",
    )
    init_parser.set_defaults(func=_run_init)
    parser.set_defaults(func=_dispatch)
    return parser


def _dispatch(args: argparse.Namespace, reporter: Reporter) -> int:
    return int(args.func(args, reporter))


def _run_init(args: argparse.Namespace, reporter: Reporter) -> int:
    root = Path(args.directory).resolve()
    root.mkdir(parents=True, exist_ok=True)

    for folder in ("models", "measurements", "reports"):
        (root / folder).mkdir(exist_ok=True)

    project_file = root / "project.yaml"
    if project_file.exists() and not args.force:
        reporter.error(f"{project_file} already exists — pass --force to overwrite")
        return 1

    project_yaml = (
        f"name: {args.name}\n"
        "schema_version: \"1.0\"\n"
        "description: OpenFEMLab CAE workspace (analysis → correlation → updating)\n"
        "paths:\n"
        "  models: models\n"
        "  measurements: measurements\n"
        "  reports: reports\n"
        "workflow:\n"
        "  - modal: openfemlab modal models/cantilever.yaml -n 8\n"
        "  - correlate: openfemlab correlate models/cantilever.yaml "
        "measurements/test.yaml -o reports/corr.json --format json\n"
        "  - update: openfemlab update models/updating.yaml -o models/cantilever.updated.yaml\n"
        "  - review: openfemlab serve --root . --file reports/corr.json --open\n"
    )
    project_file.write_text(project_yaml, encoding="utf-8")

    sample_model = root / "models" / "cantilever.yaml"
    if not sample_model.exists():
        sample_model.write_text(
            _SAMPLE_MODEL,
            encoding="utf-8",
        )

    sample_measurement = root / "measurements" / "test.yaml"
    if not sample_measurement.exists():
        _write_sample_measurement(sample_model, sample_measurement, reporter)

    reporter.success(f"Initialized workspace → {root}")
    reporter.line("  models/ · measurements/ · reports/ · project.yaml")
    reporter.hint(f"cd {root} && openfemlab desktop --root .")
    return 0


def _write_sample_measurement(model_path: Path, destination: Path, reporter: Reporter) -> None:
    """Synthesize a slightly softer reference measurement for the sample cantilever."""
    from openfemlab import ModalSolver
    from openfemlab.cli.analysis import dof_map_of
    from openfemlab.cli.spec import build_model, load_spec
    from openfemlab.core.results import TestData
    from openfemlab.io import write_test_data

    spec = load_spec(model_path)
    materials = spec.get("materials") or {}
    steel = materials.get("steel") or {}
    if isinstance(steel, dict) and "E" in steel:
        steel = dict(steel)
        steel["E"] = float(steel["E"]) * 0.92
        materials = dict(materials)
        materials["steel"] = steel
        spec = dict(spec)
        spec["materials"] = materials
    model = build_model(spec)
    result = ModalSolver(model).solve(num_modes=6)
    test = TestData(
        frequencies=result.frequencies,
        shapes=result.shapes,
        dof_map=dof_map_of(model),
        meta={"source": "sample-measurement"},
    )
    write_test_data(test, destination)
    reporter.note(f"sample measurement → {destination.name}")


_SAMPLE_MODEL = """\
name: cantilever
materials:
  steel: {E: 2.1e11, density: 7850.0, nu: 0.3}
sections:
  strip: {area: 1.0e-4, inertia_z: 8.333e-10}
mesh:
  type: beam
  length: 1.0
  num_elements: 20
  support: cantilever
  material: steel
  section: strip
"""
