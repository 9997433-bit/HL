"""``openfemlab correlate-frf`` -- measured versus synthesized FRF correlation.

The command surface over :mod:`openfemlab.correlation.frf`: it reads a measured
FRF column (UFF dataset 58, or the JSON/YAML equivalent), synthesizes the same
column from a damped model specification, and reports the FRAC vector, the FDAC
matrix and the scalars a CI gate reads. Both sides are resolved onto the
measured frequency line and channel set, so the comparison is the one MS-7.4
defines rather than an ad-hoc alignment.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from ...core.model import DOF
from ...exceptions import OpenFEMLabError
from ...solver.dynamics import RESPONSE_TYPES, RayleighDamping, modal_frf
from ..analysis import solve_spec
from ..console import Column, Reporter, format_fixed, format_number
from ..spec import SpecError
from .correlate import CORRELATION_FAILED

NAME = "correlate-frf"
HELP = "correlate a measured FRF against one synthesized from a damped model"

#: Extensions routed to the UFF/UNV dataset-58 reader instead of the JSON/YAML one.
UFF_SUFFIXES = (".uff", ".unv")

#: Modal damping ratio used when neither the command line nor the spec names one.
DEFAULT_DAMPING = 0.02

#: Two frequency lines count as the same line within this relative tolerance.
FREQUENCY_RTOL = 1.0e-9

#: UFF direction codes are 1-based over the same order as :class:`DOF`.
_UFF_DIRECTIONS = {1: DOF.UX, 2: DOF.UY, 3: DOF.UZ, 4: DOF.RX, 5: DOF.RY, 6: DOF.RZ}


def add_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        NAME,
        help=HELP,
        description=(
            "Compare a measured FRF column against a second measurement or against "
            "one synthesized from a damped model specification, and report FRAC per "
            "response channel plus the FDAC matrix over the frequency line. The "
            "measured side may be a UFF/UNV dataset-58 file or a JSON/YAML FRF "
            "document; the comparison side may be either of those or a model spec, "
            "which is then solved and synthesized on the measured frequency line."
        ),
    )
    parser.add_argument("measured", help="measured FRF (UFF/UNV dataset 58, JSON or YAML)")
    parser.add_argument(
        "comparison", help="model specification to synthesize from, or a second FRF file"
    )
    parser.add_argument(
        "-n",
        "--modes",
        type=int,
        default=10,
        help="number of modes retained in the synthesis (default: 10)",
    )
    damping = parser.add_mutually_exclusive_group()
    damping.add_argument(
        "--damping",
        type=float,
        default=None,
        metavar="ZETA",
        help=f"uniform modal damping ratio (default: the spec's block, else {DEFAULT_DAMPING})",
    )
    damping.add_argument(
        "--rayleigh",
        type=float,
        nargs=2,
        default=None,
        metavar=("ALPHA", "BETA"),
        help="proportional damping C = alpha M + beta K",
    )
    parser.add_argument(
        "--response-type",
        choices=RESPONSE_TYPES,
        default=None,
        help=(
            "response quantity the measured ordinate carries; the synthesis is "
            "generated in the same type (default: as declared, else receptance)"
        ),
    )
    parser.add_argument(
        "--excitation",
        default=None,
        metavar="NODE:DOF",
        help="exciter DOF, e.g. 1:UZ (default: the reference DOF of the measurement)",
    )
    parser.add_argument(
        "--no-fdac",
        dest="fdac",
        action="store_false",
        help="skip the FDAC matrix, which is quadratic in the number of frequency lines",
    )
    parser.add_argument(
        "--matrix", action="store_true", help="also print the full FDAC matrix"
    )
    parser.add_argument(
        "--require-frac",
        type=float,
        default=None,
        metavar="FRAC",
        help=f"exit with status {CORRELATION_FAILED} when a channel FRAC falls below this",
    )
    parser.add_argument(
        "--require-fdac",
        type=float,
        default=None,
        metavar="FDAC",
        help=f"exit with status {CORRELATION_FAILED} when an FDAC diagonal falls below this",
    )
    parser.add_argument(
        "--format",
        choices=("table", "json", "yaml"),
        default="table",
        help="how to render the report (default: table)",
    )
    parser.add_argument(
        "-o", "--output", default=None, metavar="PATH", help="write the report to a JSON/YAML file"
    )
    parser.set_defaults(func=run)
    return parser


def run(args: argparse.Namespace, reporter: Reporter) -> int:
    from ...correlation import frf_correlation

    reference = load_measured(
        args.measured, response_type=args.response_type, excitation=args.excitation
    )
    comparison = load_comparison(args.comparison, reference, args)

    correlation = frf_correlation(
        reference.values,
        aligned_values(reference, comparison),
        frequencies=reference.frequencies,
        channels=reference.labels,
        response_type=reference.response_type,
        with_fdac=args.fdac,
        meta={"reference": reference.source, "comparison": comparison.source},
    )
    correlation.excitation = reference.excitation_label

    report = build_report(correlation, reference=reference, comparison=comparison)
    if args.format == "table":
        render(report, reporter, show_matrix=args.matrix)
    else:
        reporter.document(report, format=args.format)

    if args.output:
        from ...io import write_data

        write_data(report, args.output)
        reporter.note(f"FRF correlation report written to {args.output}")

    return _acceptance(correlation, args, reporter)


# ================================================================== FRF input


@dataclass
class ChannelSet:
    """One FRF column: every response channel driven by a single exciter.

    ``values[f, c]`` is the response of ``dofs[c]`` at ``frequencies[f]`` [Hz].
    The ``(node, DOF)`` pairs are what ties a measured channel to a model
    equation, so both an imported measurement and a synthesis carry them.
    """

    source: str
    frequencies: np.ndarray
    values: np.ndarray
    dofs: tuple[tuple[int, DOF], ...]
    excitation: tuple[int, DOF]
    response_type: str = "receptance"
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.frequencies = np.asarray(self.frequencies, dtype=float).ravel()
        self.values = np.asarray(self.values, dtype=complex)
        if self.values.ndim == 1:
            self.values = self.values[:, None]
        expected = (self.frequencies.size, len(self.dofs))
        if self.values.shape != expected:
            raise SpecError(
                f"{self.source}: FRF data {self.values.shape} does not match {expected}"
            )

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(_label(node, dof) for node, dof in self.dofs)

    @property
    def excitation_label(self) -> str:
        return _label(*self.excitation)


def load_measured(
    source: str,
    *,
    response_type: str | None = None,
    excitation: str | None = None,
) -> ChannelSet:
    """Read the measured FRF column from a UFF/UNV or JSON/YAML source."""
    override = None if excitation is None else parse_dof(excitation)
    if Path(str(source)).suffix.lower() in UFF_SUFFIXES:
        return from_uff(source, response_type=response_type, excitation=override)

    from ...io import read_data

    document = read_data(source)
    if not isinstance(document, Mapping):
        raise SpecError(f"{source}: an FRF document must be a mapping")
    return from_document(
        document, source=str(source), response_type=response_type, excitation=override
    )


def load_comparison(source: str, reference: ChannelSet, args: argparse.Namespace) -> ChannelSet:
    """Read the comparison side, synthesizing it when it is a model spec."""
    if Path(str(source)).suffix.lower() in UFF_SUFFIXES:
        return from_uff(source, response_type=reference.response_type)

    from ...io import read_data

    document = read_data(source)
    if not isinstance(document, Mapping):
        raise SpecError(f"{source}: expected a mapping document")
    if is_frf_document(document):
        return from_document(document, source=str(source), response_type=reference.response_type)
    return synthesize(document, reference, source=str(source), args=args)


def is_frf_document(document: Mapping[str, Any]) -> bool:
    """True when a JSON/YAML document holds an FRF rather than a model spec."""
    declared = str(document.get("object_type", document.get("type", ""))).lower()
    if declared:
        return declared in {"frf", "frequency_response"}
    return "channels" in document


def from_uff(
    source: str,
    *,
    response_type: str | None = None,
    excitation: tuple[int, DOF] | None = None,
) -> ChannelSet:
    """Assemble one FRF column from the dataset-58 functions of a UFF file."""
    from ...io import read_uff_functions

    functions = read_uff_functions(source)
    if not functions:
        raise SpecError(f"{source}: the file holds no dataset-58 function")

    line = np.asarray(functions[0].frequencies_hz, dtype=float)
    dofs: list[tuple[int, DOF]] = []
    columns: list[np.ndarray] = []
    references: set[tuple[int, DOF]] = set()
    for function in functions:
        other = np.asarray(function.frequencies_hz, dtype=float)
        if other.size != line.size or not np.allclose(other, line, rtol=FREQUENCY_RTOL, atol=0.0):
            raise SpecError(
                f"{source}: dataset-58 functions are sampled on different frequency lines; "
                "resample them onto a common line before correlating"
            )
        dofs.append(
            (int(function.response_node), _uff_direction(function.response_direction, source))
        )
        columns.append(np.asarray(function.values, dtype=complex))
        if function.reference_node:
            references.add(
                (int(function.reference_node), _uff_direction(function.reference_direction, source))
            )

    return ChannelSet(
        source=str(source),
        frequencies=line,
        values=np.column_stack(columns),
        dofs=tuple(dofs),
        excitation=_resolve_excitation(excitation, references, source),
        response_type=response_type or "receptance",
        meta={"kind": "measured", "format": "uff-58"},
    )


def from_document(
    document: Mapping[str, Any],
    *,
    source: str,
    response_type: str | None = None,
    excitation: tuple[int, DOF] | None = None,
) -> ChannelSet:
    """Read the JSON/YAML FRF document, the portable form of one FRF column.

    ``channels`` lists one entry per response DOF, each with its ``node``,
    ``direction`` and the ``real``/``imag`` parts of the ordinate::

        object_type: frf
        response_type: receptance
        frequencies_hz: [10.0, 11.0]
        excitation: {node: 1, direction: UZ}
        channels:
          - {node: 3, direction: UZ, real: [...], imag: [...]}
    """
    line = document.get("frequencies_hz", document.get("frequencies"))
    if line is None:
        raise SpecError(f"{source}: an FRF document needs 'frequencies_hz'")
    entries = document.get("channels")
    if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes)) or not entries:
        raise SpecError(f"{source}: an FRF document needs a non-empty 'channels' sequence")

    dofs: list[tuple[int, DOF]] = []
    columns: list[np.ndarray] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            raise SpecError(f"{source}: channel {index} must be a mapping")
        dofs.append(_document_dof(entry, source, f"channel {index}"))
        columns.append(_document_column(entry, source, index))

    declared = document.get("excitation")
    if excitation is None and declared is not None:
        excitation = (
            parse_dof(declared)
            if isinstance(declared, str)
            else _document_dof(declared, source, "excitation")
        )
    if excitation is None:
        raise SpecError(f"{source}: no exciter DOF; add 'excitation' or pass --excitation NODE:DOF")

    return ChannelSet(
        source=source,
        frequencies=np.asarray(line, dtype=float),
        values=np.column_stack(columns),
        dofs=tuple(dofs),
        excitation=excitation,
        response_type=response_type or str(document.get("response_type", "receptance")),
        meta={"kind": "measured", "format": "document"},
    )


# ================================================================== synthesis


def synthesize(
    spec: Mapping[str, Any],
    reference: ChannelSet,
    *,
    source: str,
    args: argparse.Namespace,
) -> ChannelSet:
    """Solve ``spec`` and synthesize the reference column from its damped modes."""
    model, result = solve_spec(spec, num_modes=args.modes)
    damping, provenance = resolve_damping(args, spec)
    response_dofs = [_model_dof(model, node, dof) for node, dof in reference.dofs]
    excitation_dof = _model_dof(model, *reference.excitation)

    response = modal_frf(
        reference.frequencies,
        result,
        damping,
        response_dofs=response_dofs,
        excitation_dofs=[excitation_dof],
        response_type=reference.response_type,
    )
    return ChannelSet(
        source=source,
        frequencies=reference.frequencies,
        values=response.data[:, :, 0],
        dofs=reference.dofs,
        excitation=reference.excitation,
        response_type=reference.response_type,
        meta={
            "kind": "synthesized",
            "model": model.name,
            "modes": int(result.num_modes),
            "damping": provenance,
        },
    )


def resolve_damping(
    args: argparse.Namespace, spec: Mapping[str, Any]
) -> tuple[Any, dict[str, Any]]:
    """Damping for the synthesis: the command line first, then the spec block."""
    if args.rayleigh is not None:
        alpha, beta = (float(value) for value in args.rayleigh)
        return RayleighDamping(alpha=alpha, beta=beta), {
            "model": "rayleigh",
            "alpha": alpha,
            "beta": beta,
        }
    if args.damping is not None:
        return float(args.damping), {"model": "modal", "ratio": float(args.damping)}
    return damping_from_spec(spec)


def damping_from_spec(spec: Mapping[str, Any]) -> tuple[Any, dict[str, Any]]:
    """Read the optional ``damping`` block of a model specification."""
    entry = spec.get("damping")
    if entry is None:
        return DEFAULT_DAMPING, {"model": "modal", "ratio": DEFAULT_DAMPING, "source": "default"}
    if not isinstance(entry, Mapping):
        ratio = _number(entry, "damping")
        return ratio, {"model": "modal", "ratio": ratio, "source": "spec"}
    if "alpha" in entry or "beta" in entry:
        alpha = _number(entry.get("alpha", 0.0), "damping.alpha")
        beta = _number(entry.get("beta", 0.0), "damping.beta")
        return RayleighDamping(alpha=alpha, beta=beta), {
            "model": "rayleigh",
            "alpha": alpha,
            "beta": beta,
            "source": "spec",
        }
    if "ratios" in entry:
        ratios = [_number(value, "damping.ratios") for value in entry["ratios"]]
        return np.asarray(ratios), {"model": "modal", "ratios": ratios, "source": "spec"}
    if "ratio" in entry:
        ratio = _number(entry["ratio"], "damping.ratio")
        return ratio, {"model": "modal", "ratio": ratio, "source": "spec"}
    raise SpecError("a damping block needs 'ratio', 'ratios', or 'alpha'/'beta'")


# =================================================================== reporting


def aligned_values(reference: ChannelSet, comparison: ChannelSet) -> np.ndarray:
    """The comparison ordinate on the reference frequency line and channel order."""
    if reference.frequencies.size != comparison.frequencies.size or not np.allclose(
        reference.frequencies, comparison.frequencies, rtol=FREQUENCY_RTOL, atol=0.0
    ):
        raise SpecError(
            "the two FRF sets are sampled on different frequency lines; "
            "resample them onto a common line before correlating"
        )
    if comparison.labels == reference.labels:
        return comparison.values
    position = {label: index for index, label in enumerate(comparison.labels)}
    missing = [label for label in reference.labels if label not in position]
    if missing:
        raise SpecError(
            f"{comparison.source} has no channel for {', '.join(missing)}; "
            f"available: {', '.join(comparison.labels)}"
        )
    return comparison.values[:, [position[label] for label in reference.labels]]


def build_report(correlation, *, reference: ChannelSet, comparison: ChannelSet) -> dict[str, Any]:
    """Wrap the :class:`~openfemlab.correlation.frf.FRFCorrelation` block for the CLI."""
    from ...correlation import SCHEMA_VERSION

    return {
        "command": NAME,
        "schema_version": SCHEMA_VERSION,
        "reference": {
            "source": reference.source,
            "channels": len(reference.dofs),
            "frequencies": int(reference.frequencies.size),
            "excitation": reference.excitation_label,
            "response_type": reference.response_type,
            **dict(reference.meta),
        },
        "comparison": {"source": comparison.source, **dict(comparison.meta)},
        "frf": correlation.as_dict(),
    }


def render(report: dict[str, Any], reporter: Reporter, *, show_matrix: bool = False) -> None:
    block = report["frf"]
    reference, comparison = report["reference"], report["comparison"]
    reporter.heading("FRF correlation")
    fields = {
        "measured": f"{reference['channels']} channels from {reference['source']}",
        "comparison": f"{comparison['kind']} from {comparison['source']}",
        "excitation": reference["excitation"],
        "response type": block["response_type"],
        "frequency lines": reference["frequencies"],
    }
    if "damping" in comparison:
        fields["damping"] = _damping_text(comparison["damping"])
    if "modes" in comparison:
        fields["synthesis modes"] = comparison["modes"]
    reporter.fields(fields)

    labels = block["channels"] or [f"channel {index}" for index in range(block["n_channels"])]
    reporter.table(
        (Column("channel", justify="left"), Column("FRAC")),
        [(label, format_fixed(value)) for label, value in zip(labels, block["frac"], strict=True)],
    )

    worst = int(np.argmin(block["frac"]))
    summary = {
        "mean / min FRAC": f"{format_fixed(block['mean_frac'])} / "
        f"{format_fixed(block['min_frac'])}",
        "worst channel": f"{labels[worst]} ({format_fixed(block['frac'][worst])})",
    }
    if block["min_fdac_diagonal"] is not None:
        summary["min FDAC diagonal"] = format_fixed(block["min_fdac_diagonal"])
    reporter.fields(summary, title="Summary")

    if show_matrix and block["fdac"] is not None:
        matrix = np.asarray(block["fdac"], dtype=float)
        columns = (Column("f_ref \\ f_cmp", justify="left"),) + tuple(
            Column(format_number(value, 4)) for value in block["frequencies"]
        )
        rows = [
            (format_number(block["frequencies"][index], 4), *(format_fixed(v, 3) for v in row))
            for index, row in enumerate(matrix)
        ]
        reporter.table(columns, rows, title="FDAC matrix")


def _acceptance(correlation, args: argparse.Namespace, reporter: Reporter) -> int:
    """Apply the ``--require-*`` gates and translate them into an exit code."""
    failures = []
    if args.require_frac is not None and correlation.min_frac < args.require_frac:
        index, value = correlation.worst_channel()
        failures.append(
            f"lowest FRAC {format_fixed(value)} on {correlation.channel_label(index)} is "
            f"below the required {format_fixed(args.require_frac)}"
        )
    if args.require_fdac is not None:
        worst = correlation.min_fdac_diagonal
        if worst is None:
            failures.append("--require-fdac needs the FDAC matrix, which --no-fdac suppressed")
        elif worst < args.require_fdac:
            failures.append(
                f"lowest FDAC diagonal {format_fixed(worst)} is below the required "
                f"{format_fixed(args.require_fdac)}"
            )
    for message in failures:
        reporter.error(message)
    return CORRELATION_FAILED if failures else 0


# ===================================================================== helpers


def parse_dof(text: str) -> tuple[int, DOF]:
    """Parse a ``NODE:DOF`` reference such as ``12:UZ``."""
    parts = str(text).replace("/", ":").split(":")
    if len(parts) != 2:
        raise SpecError(f"{text!r} is not a NODE:DOF reference, e.g. 12:UZ")
    try:
        node = int(parts[0])
    except ValueError as exc:
        raise SpecError(f"{text!r} does not start with an integer node id") from exc
    return node, DOF.parse(parts[1].strip())


def _label(node: int, dof: DOF) -> str:
    return f"{node}:{dof.name}"


def _uff_direction(code: int, source: str) -> DOF:
    """Map a UFF direction code (sign carries orientation, not identity)."""
    try:
        return _UFF_DIRECTIONS[abs(int(code))]
    except KeyError as exc:
        raise SpecError(f"{source}: {code} is not a UFF direction code (1..6)") from exc


def _resolve_excitation(
    override: tuple[int, DOF] | None,
    references: set[tuple[int, DOF]],
    source: str,
) -> tuple[int, DOF]:
    if override is not None:
        return override
    if len(references) == 1:
        return next(iter(references))
    if not references:
        raise SpecError(
            f"{source}: the functions name no reference DOF; pass --excitation NODE:DOF"
        )
    named = ", ".join(sorted(_label(node, dof) for node, dof in references))
    raise SpecError(
        f"{source}: the functions mix the exciters {named}; correlate one column at a "
        "time and select it with --excitation NODE:DOF"
    )


def _document_dof(entry: Mapping[str, Any], source: str, description: str) -> tuple[int, DOF]:
    if "node" not in entry:
        raise SpecError(f"{source}: {description} needs a 'node'")
    direction = entry.get("direction", entry.get("dof"))
    if direction is None:
        raise SpecError(f"{source}: {description} needs a 'direction'")
    try:
        node = int(entry["node"])
    except (TypeError, ValueError) as exc:
        raise SpecError(f"{source}: {description} has a non-integer node id") from exc
    return node, DOF.parse(direction)


def _document_column(entry: Mapping[str, Any], source: str, index: int) -> np.ndarray:
    if "real" not in entry:
        raise SpecError(f"{source}: channel {index} needs a 'real' ordinate")
    real = np.asarray(entry["real"], dtype=float).ravel()
    imaginary = np.asarray(entry.get("imag", np.zeros(real.size)), dtype=float).ravel()
    if imaginary.size != real.size:
        raise SpecError(
            f"{source}: channel {index} has {real.size} real and {imaginary.size} "
            "imaginary samples"
        )
    return real + 1j * imaginary


def _model_dof(model, node: int, dof: DOF) -> int:
    try:
        return model.dof_index(node, dof)
    except OpenFEMLabError as exc:
        raise SpecError(
            f"channel {_label(node, dof)} has no counterpart in the model: {exc}"
        ) from exc


def _number(value: Any, description: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise SpecError(f"{description} must be a number, got {value!r}") from exc


def _damping_text(provenance: Mapping[str, Any]) -> str:
    if provenance.get("model") == "rayleigh":
        return (
            f"Rayleigh alpha={format_number(provenance['alpha'], 4)}, "
            f"beta={format_number(provenance['beta'], 4)}"
        )
    if "ratios" in provenance:
        return f"modal, {len(provenance['ratios'])} ratios"
    return f"modal, zeta={format_number(provenance['ratio'], 4)}"
