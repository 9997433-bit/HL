"""``openfemlab pipeline`` — six-stage simulation correction workflow (S1–S6)."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from ...updating import ScalingModel, UpdatableParameter
from ...workflow import HoldoutSpec, SensorMap, ValidationGates, run_correction
from ..console import Column, Reporter, format_fixed, format_number, format_percent
from ..spec import SpecError, load_spec

NAME = "pipeline"
HELP = "run the S1–S6 simulation-correction workflow"


def add_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        NAME,
        help=HELP,
        description=(
            "Orchestrate baseline analysis, pairing, diagnosis, updating, "
            "re-analysis and validation in one auditable correction run."
        ),
    )
    pipeline_sub = parser.add_subparsers(
        dest="pipeline_command", metavar="SUBCOMMAND", required=True
    )
    run_parser = pipeline_sub.add_parser(
        "run",
        help="execute the correction pipeline from a configuration file",
    )
    run_parser.add_argument("config", help="pipeline configuration (JSON or YAML)")
    run_parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="random seed recorded in the report (default: config value or 0)",
    )
    run_parser.add_argument(
        "--format",
        choices=("table", "json", "yaml"),
        default="table",
        help="how to render the summary (default: table)",
    )
    run_parser.add_argument(
        "-o",
        "--output",
        default=None,
        metavar="PATH",
        help="write the full CorrectionReport to a JSON/YAML file",
    )
    run_parser.add_argument(
        "--strict",
        action="store_true",
        help="exit with status 1 when the pipeline does not PASS",
    )
    run_parser.set_defaults(func=_run_pipeline)
    parser.set_defaults(func=_dispatch)
    return parser


def _dispatch(args: argparse.Namespace, reporter: Reporter) -> int:
    return int(args.func(args, reporter))


def _run_pipeline(args: argparse.Namespace, reporter: Reporter) -> int:
    config = load_spec(args.config)
    model = _build_model(config, str(args.config))
    measurement = _build_measurement(model, config, str(args.config))
    parameters = _build_parameters(config)
    gates = _build_gates(config.get("gates"))
    holdout = _build_holdout(config.get("holdout"))
    sensor_map = _build_sensor_map(config.get("sensor_map"))
    seed = int(args.seed if args.seed is not None else config.get("seed", 0))

    report = run_correction(
        model,
        measurement,
        sensor_map,
        parameters,
        gates=gates,
        holdout=holdout,
        seed=seed,
    )
    payload = report.to_dict(include_timing=args.format != "json")

    if args.format == "table":
        render(payload, reporter)
    else:
        reporter.document(payload, format=args.format)

    if args.output:
        from ...io import write_data

        write_data(payload, args.output)
        reporter.note(f"correction report written to {args.output}")

    if args.strict and not report.passed:
        reason = report.failure or {"stage": report.failed_stage}
        reporter.error(f"pipeline did not pass: {reason}")
        return 1
    return 0 if report.passed else 1


def render(report: Mapping[str, Any], reporter: Reporter) -> None:
    reporter.heading("Correction pipeline")
    reporter.fields(
        {
            "status": report["status"],
            "schema": report["schema_version"],
            "seed": report["environment"]["seed"],
            "wall time [s]": format_number(
                sum(stage.get("wall_time_s", 0.0) for stage in report["stages"]), 4
            ),
        }
    )

    columns = (Column("stage"), Column("status"), Column("wall [s]"))
    rows = [
        (
            stage["stage"],
            stage["status"],
            format_number(stage.get("wall_time_s", 0.0), 4),
        )
        for stage in report["stages"]
    ]
    reporter.table(columns, rows, title="Stages")

    final = report.get("final_correlation")
    if final is not None:
        summary = final["summary"]
        reporter.table(
            (Column("metric", justify="left"), Column("value", justify="right")),
            [
                ("paired modes", str(summary["n_paired"])),
                ("min MAC", format_fixed(summary["min_mac"])),
                ("max |Δf| %", format_percent(summary["max_abs_freq_error_pct"])),
            ],
            title="Final correlation",
        )

    if report.get("parameters"):
        reporter.table(
            (
                Column("parameter", justify="left"),
                Column("initial", justify="right"),
                Column("final", justify="right"),
            ),
            [
                (
                    entry["name"],
                    format_fixed(entry["initial"], 4),
                    format_fixed(entry["final"], 4),
                )
                for entry in report["parameters"]
            ],
            title="Parameters",
        )

    if report["status"] != "PASS" and report.get("failure"):
        reporter.warning(f"Failed at {report['failure']['stage']}: {report['failure']['reason']}")


def _build_model(config: Mapping[str, Any], source: str) -> ScalingModel:
    preset = str(config.get("preset", "chain")).strip().lower()
    if preset != "chain":
        raise SpecError(f"{source}: unsupported pipeline preset {preset!r}; expected 'chain'")
    num_masses = int(config.get("num_masses", 10))
    num_modes = int(config.get("num_modes", 6))
    stiffness_groups = _group_lists(config.get("stiffness_groups"), "stiffness_groups")
    mass_groups = _group_lists(config.get("mass_groups"), "mass_groups")
    stiffness_parts, mass_parts = _chain_parts(num_masses, stiffness_groups, mass_groups)
    return ScalingModel(
        stiffness_parts,
        base_mass=sum(mass_parts.values()),
        num_modes=num_modes,
        use_solver=False,
    )


def _build_measurement(model: ScalingModel, config: Mapping[str, Any], source: str):
    measurement = config.get("measurement")
    if not isinstance(measurement, Mapping):
        raise SpecError(f"{source}: the configuration needs a 'measurement' section")
    truth = measurement.get("truth")
    if not isinstance(truth, Mapping) or not truth:
        raise SpecError(f"{source}: 'measurement.truth' must name the synthetic detuning factors")
    values = {str(key): float(value) for key, value in truth.items()}
    return model.modal_data(values)


def _build_parameters(config: Mapping[str, Any]) -> list[UpdatableParameter]:
    entries = config.get("parameters")
    if not entries:
        raise SpecError("the configuration needs at least one entry under 'parameters'")
    parameters: list[UpdatableParameter] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise SpecError("each parameter must be a mapping")
        name = str(entry.get("name", "")).strip()
        if not name:
            raise SpecError("each parameter needs a 'name'")
        parameters.append(
            UpdatableParameter(
                name=name,
                value=1.0,
                lower=float(entry.get("lower", 0.5)),
                upper=float(entry.get("upper", 2.0)),
                kind=str(entry.get("kind", "stiffness")),
            )
        )
    return parameters


def _build_gates(raw: Any) -> ValidationGates | None:
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise SpecError("'gates' must be a mapping when provided")
    return ValidationGates(
        mac_min=float(raw.get("mac_min", 0.95)),
        freq_tolerance_pct=float(raw.get("freq_tolerance_pct", 1.0)),
        min_pairs=int(raw.get("min_pairs", 3)),
        pairing_mac_min=float(raw.get("pairing_mac_min", 0.5)),
        parameter_change_warning_pct=float(raw.get("parameter_change_warning_pct", 50.0)),
        holdout_mac_min=float(raw.get("holdout_mac_min", 0.9)),
        require_holdout_improvement=bool(raw.get("require_holdout_improvement", True)),
    )


def _build_holdout(raw: Any) -> HoldoutSpec | None:
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise SpecError("'holdout' must be a mapping when provided")
    modes = raw.get("modes")
    highest = raw.get("highest_paired")
    if modes is None and highest is None:
        return None
    return HoldoutSpec(
        modes=tuple(int(index) for index in modes or ()),
        highest_paired=int(highest) if highest is not None else 0,
    )


def _build_sensor_map(raw: Any) -> SensorMap | None:
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise SpecError("'sensor_map' must be a mapping when provided")
    rows = raw.get("rows")
    if rows is None:
        return None
    return SensorMap(rows=tuple(int(index) for index in rows))


def _group_lists(raw: Any, field: str) -> list[tuple[int, ...]]:
    if not isinstance(raw, Sequence) or not raw:
        raise SpecError(f"the configuration needs non-empty '{field}'")
    groups: list[tuple[int, ...]] = []
    for group in raw:
        if not isinstance(group, Sequence) or not group:
            raise SpecError(f"each entry of '{field}' must be a non-empty list")
        groups.append(tuple(int(value) for value in group))
    return groups


def _chain_parts(
    num_masses: int,
    stiffness_groups: Sequence[Sequence[int]],
    mass_groups: Sequence[Sequence[int]],
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Grouped unit fixed-free chain contributions for :class:`ScalingModel`."""
    stiffness_parts: dict[str, np.ndarray] = {}
    for index, springs in enumerate(stiffness_groups, start=1):
        part = np.zeros((num_masses, num_masses))
        for spring in springs:
            dof = spring - 1
            part[dof, dof] += 1.0
            if spring > 1:
                part[dof - 1, dof - 1] += 1.0
                part[dof - 1, dof] -= 1.0
                part[dof, dof - 1] -= 1.0
        stiffness_parts[f"k{index}"] = part

    mass_parts: dict[str, np.ndarray] = {}
    for index, masses in enumerate(mass_groups, start=1):
        part = np.zeros((num_masses, num_masses))
        for mass in masses:
            part[mass - 1, mass - 1] += 1.0
        mass_parts[f"m{index}"] = part
    return stiffness_parts, mass_parts
