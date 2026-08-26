"""``openfemlab update`` -- sensitivity-based model updating driven by a config file."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np

from ..analysis import dof_map_of, solve_spec
from ..console import Column, Reporter, format_fixed, format_number, format_percent
from ..spec import SpecError, build_model, load_spec, lookup, scaled

NAME = "update"
HELP = "run a sensitivity-based model-updating session"

#: Exit code used when the updating loop finishes without converging.
NOT_CONVERGED = 4


def add_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        NAME,
        help=HELP,
        description=(
            "Drive the Levenberg-Marquardt updater from a configuration file that "
            "names a model specification, the measured target, and the dimensionless "
            "parameters scaling individual numbers of that specification."
        ),
    )
    parser.add_argument("config", help="updating configuration (JSON or YAML)")
    parser.add_argument(
        "-n",
        "--modes",
        type=int,
        default=None,
        help="number of FE modes per evaluation (default: the config value, or the target count)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="override the iteration limit from the configuration",
    )
    parser.add_argument(
        "--format",
        choices=("table", "json", "yaml"),
        default="table",
        help="how to render the report (default: table)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        metavar="PATH",
        help="write the updated model specification, ready for 'openfemlab modal'",
    )
    parser.add_argument(
        "--report", default=None, metavar="PATH", help="write the run report to a JSON/YAML file"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=f"exit with status {NOT_CONVERGED} when the loop does not converge",
    )
    parser.set_defaults(func=run)
    return parser


@dataclass(frozen=True)
class Declaration:
    """One configured parameter: where it points in the spec and its bounds."""

    name: str
    target: str
    nominal: float
    lower: float
    upper: float
    kind: str
    step: float
    log_scaled: bool

    def to_updatable(self):
        from ...updating.parameters import UpdatableParameter

        return UpdatableParameter(
            name=self.name,
            value=1.0,
            lower=self.lower,
            upper=self.upper,
            kind=self.kind,
            targets=(self.target,),
            step=self.step,
            log_scaled=self.log_scaled,
        )


def run(args: argparse.Namespace, reporter: Reporter) -> int:
    from ...updating import ModelUpdater, ParameterSet, UpdatingOptions

    config = load_spec(args.config)
    model_spec = _model_spec(config, args.config)
    declarations = _declarations(config, model_spec)
    target_frequencies, target_shapes, target_source = _target(config, args.config)

    num_modes = int(args.modes or config.get("modes") or target_frequencies.size)
    options = UpdatingOptions(**_options(config, args.max_iterations))

    rows_fe = None
    if target_shapes is not None and options.shape_weight > 0.0:
        from ...correlation import align_dof_maps

        rows_fe, rows_test = align_dof_maps(
            dof_map_of(build_model(model_spec)),
            _target_dof_map(config, args.config),
            strict=not bool(config.get("partial_dofs", False)),
        )
        target_shapes = target_shapes[rows_test, :]
    else:
        target_shapes = None

    evaluate = _make_evaluator(model_spec, declarations, num_modes=num_modes, rows=rows_fe)
    parameters = ParameterSet([declaration.to_updatable() for declaration in declarations])

    reporter.note(
        f"updating {len(declarations)} parameters against {target_frequencies.size} "
        f"target frequencies ({num_modes} FE modes per evaluation)"
    )
    updater = ModelUpdater(
        evaluate, parameters, target_frequencies, target_shapes, options=options
    )
    result = updater.run()

    factors = {
        declaration.name: result.parameters[declaration.name] for declaration in declarations
    }
    updated_spec = scaled(model_spec, {d.target: factors[d.name] for d in declarations})
    report = build_report(
        result,
        declarations,
        updater=updater,
        config_source=str(args.config),
        target_source=target_source,
        target_frequencies=target_frequencies,
        updated_spec=updated_spec,
        num_modes=num_modes,
        shape_correlation=target_shapes is not None,
    )

    if args.format == "table":
        render(report, reporter)
    else:
        reporter.document(report, format=args.format)

    if args.output:
        from ...io import write_data

        write_data(updated_spec, args.output)
        reporter.note(f"updated model specification written to {args.output}")
    if args.report:
        from ...io import write_data

        write_data(report, args.report)
        reporter.note(f"updating report written to {args.report}")

    if args.strict and not result.converged:
        reporter.error(f"updating did not converge: {result.message}")
        return NOT_CONVERGED
    return 0


# ------------------------------------------------------------- configuration


def _model_spec(config: Mapping[str, Any], source: str) -> dict[str, Any]:
    raw = config.get("model")
    if raw is None:
        raise SpecError(f"{source}: the configuration needs a 'model' section")
    if isinstance(raw, str):
        return load_spec(raw)
    if not isinstance(raw, Mapping):
        raise SpecError(f"{source}: 'model' must be a mapping or a path to a model spec")
    if "path" in raw and "mesh" not in raw:
        return load_spec(raw["path"])
    return dict(raw)


def _declarations(config: Mapping[str, Any], model_spec: Mapping[str, Any]) -> list[Declaration]:
    entries = config.get("parameters")
    if not entries:
        raise SpecError("the configuration needs at least one entry under 'parameters'")
    declarations = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise SpecError("each parameter must be a mapping")
        target = str(entry.get("target", ""))
        if not target:
            raise SpecError("each parameter needs a 'target' dotted path into the model spec")
        nominal = lookup(model_spec, target)
        try:
            nominal = float(nominal)
        except (TypeError, ValueError) as exc:
            raise SpecError(f"parameter target {target} does not address a number") from exc
        declarations.append(
            Declaration(
                name=str(entry.get("name", target)),
                target=target,
                nominal=nominal,
                lower=float(entry.get("lower", 0.5)),
                upper=float(entry.get("upper", 2.0)),
                kind=str(entry.get("kind", "stiffness")),
                step=float(entry.get("step", 1.0e-4)),
                log_scaled=bool(entry.get("log_scaled", False)),
            )
        )
    return declarations


def _target(config: Mapping[str, Any], source: str) -> tuple[np.ndarray, np.ndarray | None, str]:
    target = config.get("target")
    if not isinstance(target, Mapping):
        raise SpecError(f"{source}: the configuration needs a 'target' section")
    path = target.get("file", target.get("path"))
    if path is not None:
        from ...io import read_test_data

        data = read_test_data(path)
        return data.frequencies, data.shapes, str(path)
    frequencies = target.get("frequencies_hz", target.get("frequencies"))
    if frequencies is None:
        raise SpecError(f"{source}: 'target' needs either a 'file' or a 'frequencies' list")
    return np.asarray(frequencies, dtype=float).ravel(), None, f"{source}:target"


def _target_dof_map(config: Mapping[str, Any], source: str):
    from ...io import read_test_data

    target = config.get("target", {})
    path = target.get("file", target.get("path")) if isinstance(target, Mapping) else None
    if path is None:
        raise SpecError(f"{source}: shape correlation needs a measured 'target.file'")
    return read_test_data(path).dof_map


def _options(config: Mapping[str, Any], max_iterations: int | None) -> dict[str, Any]:
    from ...updating import UpdatingOptions

    raw = config.get("options", {})
    if not isinstance(raw, Mapping):
        raise SpecError("'options' must be a mapping")
    options = dict(raw)
    if max_iterations is not None:
        options["max_iterations"] = max_iterations
    unknown = sorted(set(options) - set(UpdatingOptions.__dataclass_fields__))
    if unknown:
        raise SpecError(f"unknown updating options: {', '.join(unknown)}")
    return options


def _make_evaluator(model_spec, declarations, *, num_modes: int, rows):
    """Return the ``{parameter: factor} -> ModalData`` callable the updater drives."""
    from ...updating.sensitivity import ModalData

    targets = {declaration.name: declaration.target for declaration in declarations}

    def evaluate(factors: Mapping[str, float]) -> ModalData:
        patched = scaled(model_spec, {targets[name]: factors[name] for name in targets})
        _, result = solve_spec(patched, num_modes=num_modes)
        shapes = None if rows is None else result.mode_shapes[rows, :]
        return ModalData(result.frequencies, shapes)

    return evaluate


# ------------------------------------------------------------------ reporting


def build_report(
    result,
    declarations: list[Declaration],
    *,
    updater,
    config_source: str,
    target_source: str,
    target_frequencies: np.ndarray,
    updated_spec: Mapping[str, Any],
    num_modes: int,
    shape_correlation: bool,
) -> dict[str, Any]:
    """Assemble the JSON-ready summary of one updating run."""
    parameters = []
    for declaration in declarations:
        factor = float(result.parameters[declaration.name])
        parameters.append(
            {
                "name": declaration.name,
                "target": declaration.target,
                "factor": factor,
                "nominal": declaration.nominal,
                "updated": declaration.nominal * factor,
                "change_pct": 100.0 * (factor - 1.0),
                "bounds": [declaration.lower, declaration.upper],
            }
        )

    return {
        "command": NAME,
        "source": config_source,
        "target": {
            "source": target_source,
            "frequencies_hz": target_frequencies.tolist(),
            "modes": int(target_frequencies.size),
        },
        "analysis": {
            "num_modes": num_modes,
            "evaluations": updater.n_evaluations,
            "shape_correlation": shape_correlation,
        },
        "converged": bool(result.converged),
        "message": result.message,
        "iterations": int(result.iterations),
        "cost": {
            "initial": float(result.initial_cost),
            "final": float(result.final_cost),
            "reduction": float(result.cost_reduction),
        },
        "correlation": {
            "initial": _correlation(result.initial_correlation),
            "final": _correlation(result.final_correlation),
        },
        "parameters": parameters,
        "history": [
            {
                "iteration": record.iteration,
                "cost": float(record.cost),
                "mean_mac": float(record.mean_mac),
                "min_mac": float(record.min_mac),
                "max_abs_freq_error_pct": float(record.max_abs_freq_error_pct),
                "damping": float(record.damping),
                "step_norm": float(record.step_norm),
                "accepted": bool(record.accepted),
            }
            for record in result.history
        ],
        "updated_model": dict(updated_spec),
    }


def render(report: dict[str, Any], reporter: Reporter) -> None:
    reporter.heading("Sensitivity-based model updating")
    cost = report["cost"]
    reporter.fields(
        {
            "converged": f"{report['converged']} ({report['message']})",
            "iterations": report["iterations"],
            "model evaluations": report["analysis"]["evaluations"],
            "cost": f"{format_number(cost['initial'])} -> {format_number(cost['final'])} "
            f"({100.0 * cost['reduction']:.2f}% reduction)",
        }
    )

    reporter.table(
        (
            Column("parameter", justify="left"),
            Column("target", justify="left"),
            Column("nominal"),
            Column("updated"),
            Column("factor"),
            Column("change [%]"),
            Column("bounds"),
        ),
        [
            (
                parameter["name"],
                parameter["target"],
                format_number(parameter["nominal"]),
                format_number(parameter["updated"]),
                format_number(parameter["factor"], 5),
                format_percent(parameter["change_pct"], 2),
                f"[{format_number(parameter['bounds'][0], 3)}, "
                f"{format_number(parameter['bounds'][1], 3)}]",
            )
            for parameter in report["parameters"]
        ],
        title="Parameters",
    )

    initial, final = report["correlation"]["initial"], report["correlation"]["final"]
    indicators = [
        (
            "max |df| [%]",
            format_number(initial["max_abs_freq_error_pct"], 4),
            format_number(final["max_abs_freq_error_pct"], 4),
        )
    ]
    if report["analysis"]["shape_correlation"]:
        # Without measured shapes the MAC columns of the summary stay zero,
        # which would read as a correlation failure rather than as "not used".
        indicators = [
            ("mean MAC", format_fixed(initial["mean_mac"]), format_fixed(final["mean_mac"])),
            ("min MAC", format_fixed(initial["min_mac"]), format_fixed(final["min_mac"])),
            *indicators,
        ]
    reporter.table(
        (Column("indicator", justify="left"), Column("before"), Column("after")),
        indicators,
        title="Correlation",
    )

    history = report["history"]
    if not history:
        return
    with_mac = report["analysis"]["shape_correlation"]
    columns = [Column("iter"), Column("cost")]
    if with_mac:
        columns.append(Column("mean MAC"))
    columns += [
        Column("max |df| [%]"),
        Column("damping"),
        Column("step"),
        Column("accepted", justify="center"),
    ]
    reporter.table(
        columns,
        [
            (
                str(record["iteration"]),
                format_number(record["cost"], 4),
                *([format_fixed(record["mean_mac"])] if with_mac else []),
                format_number(record["max_abs_freq_error_pct"], 4),
                format_number(record["damping"], 3),
                format_number(record["step_norm"], 3),
                "yes" if record["accepted"] else "no",
            )
            for record in history
        ],
        title="Iteration history",
    )


def _correlation(summary) -> dict[str, Any]:
    return {
        "mean_mac": float(summary.mean_mac),
        "min_mac": float(summary.min_mac),
        "max_abs_freq_error_pct": float(summary.max_abs_freq_error_pct),
    }
