"""``openfemlab update`` -- sensitivity-based model updating driven by a config file.

Two estimators share the command.  Without a ``prior`` or a ``noise`` section
the run is the deterministic Levenberg-Marquardt loop of
:mod:`openfemlab.updating.updater`.  With either of them it is the MS-3.5
maximum-a-posteriori loop of :mod:`openfemlab.updating.bayesian`, and the
report gains the resolved prior, the noise model, and the Laplace posterior
whose diagonal is the per-parameter σ_post::

    prior:
      std: 0.05             # scalar, per-parameter list, or {name: value}
      mean: {stiffness: 1.0}
    noise:
      std: 0.005            # over the assembled residual entries

``std``, ``variance`` and ``covariance`` are three ways of writing the same
block; exactly one of them may appear.  Both live in the updater's *design*
space, so a ``log_scaled`` parameter takes its prior on ``log(factor)``.
"""

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
    from ...updating import BayesianUpdater, ModelUpdater, ParameterSet, UpdatingOptions

    config = load_spec(args.config)
    model_spec = _model_spec(config, args.config)
    declarations = _declarations(config, model_spec)
    statistics = _statistics(config, declarations)
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
    updater: ModelUpdater
    if statistics is None:
        updater = ModelUpdater(
            evaluate, parameters, target_frequencies, target_shapes, options=options
        )
    else:
        reporter.note(f"maximum-a-posteriori estimator: {statistics.description}")
        updater = BayesianUpdater(
            evaluate,
            parameters,
            target_frequencies,
            target_shapes,
            prior=statistics.prior,
            noise_covariance=statistics.noise_covariance,
            options=options,
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
        statistics=statistics,
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


# -------------------------------------------------- prior and noise (MS-3.5)

#: The three interchangeable ways of writing one dispersion block.
DISPERSION_KEYS = ("std", "variance", "covariance")


@dataclass(frozen=True)
class Statistics:
    """The resolved MS-3.5 inputs of a MAP run, plus their report blocks."""

    prior: Any
    noise_covariance: Any
    prior_block: dict[str, Any] | None
    noise_block: dict[str, Any] | None

    @property
    def description(self) -> str:
        parts = []
        if self.prior_block is not None:
            parts.append(f"prior by {self.prior_block['given_as']}")
        if self.noise_block is not None:
            parts.append(f"noise by {self.noise_block['given_as']}")
        return ", ".join(parts)


def _statistics(config: Mapping[str, Any], declarations: list[Declaration]) -> Statistics | None:
    """Read the ``prior`` and ``noise`` sections; ``None`` keeps the LM estimator."""
    from ...updating import GaussianPrior

    prior_raw = config.get("prior")
    noise_raw = config.get("noise", config.get("noise_covariance"))
    if prior_raw is None and noise_raw is None:
        return None

    names = [declaration.name for declaration in declarations]
    prior, prior_block = _prior(prior_raw, declarations)
    noise_spec, noise_block = _noise(noise_raw)
    return Statistics(
        prior=GaussianPrior.uninformative(names) if prior is None else prior,
        noise_covariance=noise_spec,
        prior_block=prior_block,
        noise_block=noise_block,
    )


def _numbers(raw: Any, names: list[str] | None, label: str) -> np.ndarray:
    """One dispersion entry as an array: scalar, vector, matrix or ``{name: value}``."""
    if isinstance(raw, Mapping):
        if names is None:
            raise SpecError(f"{label}: a per-parameter mapping only applies to the prior")
        unknown = sorted({str(key) for key in raw} - set(names))
        if unknown:
            raise SpecError(f"{label}: no such parameter: {', '.join(unknown)}")
        missing = [name for name in names if name not in raw]
        if missing:
            raise SpecError(f"{label}: no entry for {', '.join(missing)}")
        raw = [raw[name] for name in names]
    try:
        array = np.asarray(raw, dtype=float)
    except (TypeError, ValueError) as exc:
        raise SpecError(f"{label}: expected a number, a list or a matrix") from exc
    if not np.all(np.isfinite(array)):
        raise SpecError(f"{label}: every entry must be finite")
    return array


def _dispersion(
    block: Any, label: str, names: list[str] | None
) -> tuple[np.ndarray, str]:
    """Covariance specification of one block, plus the key it was written with."""
    if not isinstance(block, Mapping):
        raise SpecError(f"'{label}' must be a mapping")
    given = [key for key in DISPERSION_KEYS if key in block]
    if not given:
        raise SpecError(f"'{label}' needs one of {', '.join(DISPERSION_KEYS)}")
    if len(given) > 1:
        raise SpecError(f"'{label}' sets {' and '.join(given)}; give exactly one")
    key = given[0]
    values = _numbers(block[key], names, f"{label}.{key}")
    if key == "std":
        if np.any(values <= 0.0):
            raise SpecError(f"{label}.std: standard deviations must be positive")
        return values**2, key
    return values, key


def _prior(raw: Any, declarations: list[Declaration]) -> tuple[Any, dict[str, Any] | None]:
    """Resolve the ``prior`` section against the declared parameters."""
    from ...updating import GaussianPrior

    if raw is None:
        return None, None
    names = [declaration.name for declaration in declarations]
    size = len(names)
    unknown = sorted(set(raw) - {*DISPERSION_KEYS, "mean"}) if isinstance(raw, Mapping) else []
    if unknown:
        raise SpecError(f"unknown keys in 'prior': {', '.join(unknown)}")
    covariance, given_as = _dispersion(raw, "prior", names)

    mean: np.ndarray | None = None
    if raw.get("mean") is not None:
        mean = _numbers(raw["mean"], names, "prior.mean")
        mean = np.full(size, float(mean)) if mean.ndim == 0 else mean.ravel()
        if mean.size != size:
            raise SpecError(f"prior.mean: expected {size} entries, got {mean.size}")

    prior = GaussianPrior(covariance=covariance, mean=mean, names=tuple(names))
    try:
        matrix = prior.matrix(size)
        sigma = prior.std(size)
    except ValueError as exc:
        raise SpecError(f"prior: {exc}") from exc
    # An unset mean anchors on the run's starting point, which is the unit
    # scaling factor mapped into each parameter's own design space.
    start = np.array(
        [0.0 if declaration.log_scaled else 1.0 for declaration in declarations], dtype=float
    )
    block = {
        "given_as": given_as,
        "space": "design",
        "names": names,
        "std": [float(value) for value in sigma],
        "mean": [float(value) for value in prior.center(size, start)],
        "covariance": [[float(value) for value in row] for row in matrix],
    }
    return prior, block


def _noise(raw: Any) -> tuple[np.ndarray | None, dict[str, Any] | None]:
    """Resolve the ``noise`` section; its size is the residual's, known only at run time."""
    if raw is None:
        return None, None
    unknown = sorted(set(raw) - set(DISPERSION_KEYS)) if isinstance(raw, Mapping) else []
    if unknown:
        raise SpecError(f"unknown keys in 'noise': {', '.join(unknown)}")
    covariance, given_as = _dispersion(raw, "noise", None)
    if covariance.ndim > 2:
        raise SpecError("noise: expected a number, a list of variances or a matrix")
    if np.any(covariance <= 0.0) and covariance.ndim < 2:
        raise SpecError("noise: variances must be positive")
    block: dict[str, Any] = {
        "given_as": given_as,
        "space": "residual",
        "std": _sigma_of(covariance),
    }
    if covariance.ndim == 2:
        block["covariance"] = [[float(value) for value in row] for row in covariance]
    return covariance, block


def _sigma_of(covariance: np.ndarray) -> float | list[float]:
    """σ of a covariance specification: scalar in, scalar out; diagonal otherwise."""
    if covariance.ndim == 0:
        return float(np.sqrt(covariance))
    diagonal = np.diag(covariance) if covariance.ndim == 2 else covariance
    return [float(value) for value in np.sqrt(np.clip(diagonal, 0.0, None))]


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
    statistics: Statistics | None = None,
) -> dict[str, Any]:
    """Assemble the JSON-ready summary of one updating run."""
    from ...updating import posterior_sigma

    sigma_post = posterior_sigma(result)
    sigma_prior = _prior_sigma(statistics)
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
                # Both spreads are design-space quantities, like the factor
                # itself for a linear parameter and like its logarithm for a
                # log-scaled one.
                "sigma_post": _finite(sigma_post.get(declaration.name)),
                "sigma_prior": _finite(sigma_prior.get(declaration.name)),
            }
        )

    report: dict[str, Any] = {
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
            "estimator": "least-squares" if statistics is None else "map",
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
        # Null for a deterministic run; the MS-3.5 inputs and the Laplace
        # posterior they produce for a MAP one.
        "bayesian": (
            None
            if statistics is None
            else {
                "prior": statistics.prior_block,
                "noise": statistics.noise_block,
                "posterior": _posterior(result),
            }
        ),
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
    return report


def _prior_sigma(statistics: Statistics | None) -> dict[str, float]:
    """Per-parameter σ_prior, empty unless an informative prior was configured."""
    if statistics is None or statistics.prior_block is None:
        return {}
    block = statistics.prior_block
    return dict(zip(block["names"], block["std"], strict=True))


def _posterior(result) -> dict[str, Any] | None:
    """The Laplace posterior of a MAP run, in the updater's design space."""
    posterior = getattr(result, "posterior", None)
    if posterior is None:  # pragma: no cover - run() always reports modal data
        return None
    return {
        "space": "design",
        "names": list(posterior.names),
        "mean": [float(value) for value in posterior.mean],
        "sigma_post": [float(value) for value in posterior.std],
        "sigma_prior": [_finite(value) for value in posterior.prior_std],
        "covariance": [[float(value) for value in row] for row in posterior.covariance],
    }


def _finite(value: float | None) -> float | None:
    """JSON-safe scalar; ``None`` stands in for an absent or infinite spread."""
    if value is None:
        return None
    number = float(value)
    return number if np.isfinite(number) else None


def _spread(value: float | None) -> str:
    """Table cell for a standard deviation the run could not put a number on."""
    return "-" if value is None else format_number(value, 3)


def render(report: dict[str, Any], reporter: Reporter) -> None:
    reporter.heading("Sensitivity-based model updating")
    cost = report["cost"]
    reporter.fields(
        {
            "estimator": report["analysis"]["estimator"],
            "converged": f"{report['converged']} ({report['message']})",
            "iterations": report["iterations"],
            "model evaluations": report["analysis"]["evaluations"],
            "cost": f"{format_number(cost['initial'])} -> {format_number(cost['final'])} "
            f"({100.0 * cost['reduction']:.2f}% reduction)",
        }
    )

    # σ_prior only says something once a prior has been configured; σ_post is
    # the Laplace posterior for a MAP run and the least-squares estimate
    # otherwise, so it is worth showing either way.
    with_prior = any(p["sigma_prior"] is not None for p in report["parameters"])
    reporter.table(
        (
            Column("parameter", justify="left"),
            Column("target", justify="left"),
            Column("nominal"),
            Column("updated"),
            Column("factor"),
            Column("change [%]"),
            Column("sigma_post"),
            *([Column("sigma_prior")] if with_prior else []),
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
                _spread(parameter["sigma_post"]),
                *([_spread(parameter["sigma_prior"])] if with_prior else []),
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
