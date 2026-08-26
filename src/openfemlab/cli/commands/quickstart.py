"""``openfemlab quickstart`` — a zero-file demo of modal → correlate → update."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from typing import Any

from openfemlab import ModalSolver, UpdatableParameter, correlation_summary, update_model
from openfemlab.mesh.simple import spring_mass_chain

from ..console import Column, Reporter, format_fixed, format_percent

NAME = "quickstart"
HELP = "run a 60-second demo without preparing any input files"


def add_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        NAME,
        help=HELP,
        description=(
            "Solve a tiny two-DOF spring-mass chain, correlate it against a softer "
            "'measurement', update stiffness, and print before/after metrics. "
            "No YAML files required — ideal for first contact with the toolchain."
        ),
    )
    parser.set_defaults(func=run)
    return parser


def run(args: argparse.Namespace, reporter: Reporter) -> int:
    num_modes = 2
    nominal_k = 1_000.0
    true_scale = 0.81

    reporter.heading("OpenFEMLab quickstart")
    reporter.note("Two-DOF chain · synthetic test at 81% stiffness · ~10 seconds")

    def solve(scale: float):
        model = spring_mass_chain(
            num_masses=num_modes,
            stiffness=nominal_k * scale,
            mass=1.0,
        )
        return ModalSolver(model).solve(num_modes=num_modes)

    reporter.hint("Step 1/3 — baseline modal analysis")
    measured = solve(true_scale)
    baseline = solve(1.0)
    reporter.table(
        (
            Column("mode", justify="right"),
            Column("baseline [Hz]", justify="right"),
            Column("measured [Hz]", justify="right"),
        ),
        [
            (
                str(index + 1),
                format_fixed(baseline.frequencies[index], 4),
                format_fixed(measured.frequencies[index], 4),
            )
            for index in range(num_modes)
        ],
        title="Frequencies",
    )

    def correlate(fe_modes, test_modes):
        return correlation_summary(
            test_frequencies=test_modes.frequencies,
            fe_frequencies=fe_modes.frequencies,
            test_shapes=test_modes.mode_shapes,
            fe_shapes=fe_modes.mode_shapes,
            method="optimal",
        )

    reporter.hint("Step 2/3 — correlate baseline vs measurement")
    before = correlate(baseline, measured)
    _print_correlation_summary(reporter, before, title="Before update")

    reporter.hint("Step 3/3 — sensitivity-based model updating")
    def evaluate(parameters: Mapping[str, float]):
        return solve(parameters["stiffness_scale"])

    result = update_model(
        evaluate,
        [UpdatableParameter("stiffness_scale", lower=0.5, upper=1.5)],
        measured.frequencies,
        measured.mode_shapes,
        max_iterations=15,
        shape_weight=0.25,
        parameter_tolerance=1.0e-10,
    )
    scale = result.parameters["stiffness_scale"]
    after = correlate(solve(scale), measured)
    _print_correlation_summary(reporter, after, title="After update")

    reporter.fields(
        {
            "stiffness scale": f"1.0000 → {scale:.4f}",
            "iterations": result.iterations,
            "converged": result.converged,
        },
        title="Update",
    )

    if after.min_mac >= 0.99 and after.max_abs_freq_error_pct <= 1.0:
        reporter.success("Demo complete — correlation gates look good.")
    else:
        reporter.warning("Demo finished; try a longer update run on your own models.")

    reporter.hint("Next: openfemlab modal your_model.yaml -n 8")
    reporter.hint("Then: openfemlab correlate your_model.yaml measured.yaml")
    reporter.hint("Docs: examples/05_five_minute_workflow.py and docs/USER_GUIDE_zh.md")
    return 0


def _print_correlation_summary(reporter: Reporter, summary: Any, *, title: str) -> None:
    reporter.table(
        (
            Column("metric", justify="left"),
            Column("value", justify="right"),
        ),
        [
            ("min MAC", format_fixed(summary.min_mac)),
            ("mean MAC", format_fixed(summary.mean_mac)),
            ("max |Δf| %", format_percent(summary.max_abs_freq_error_pct)),
            ("paired modes", str(summary.n_paired)),
        ],
        title=title,
    )
