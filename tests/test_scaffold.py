"""Smoke tests for the benchmark and example entry points."""

from __future__ import annotations

import runpy
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parents[1]


def load_script(relative_path: str) -> dict[str, object]:
    """Load a repository script without running its command-line entry point."""
    return runpy.run_path(str(ROOT / relative_path))


def test_modal_benchmark_model_has_sorted_positive_frequencies() -> None:
    script = load_script("benchmarks/bench_modal.py")
    stiffness, mass = script["build_spring_chain"](10)
    frequencies = script["modal_frequencies"](stiffness, mass, modes=4)

    assert frequencies.shape == (4,)
    assert np.all(frequencies > 0.0)
    assert np.all(np.diff(frequencies) > 0.0)


def test_updating_loop_reduces_modal_frequency_error() -> None:
    script = load_script("benchmarks/bench_updating.py")
    result = script["run_updating_loop"](dof=30, iterations=5)

    assert result.final_relative_rms < result.initial_relative_rms
    assert result.parameters.shape == (4,)


def test_cantilever_example_has_sorted_positive_frequencies() -> None:
    script = load_script("examples/01_cantilever_modal.py")
    frequencies = script["cantilever_frequencies"](elements=6, modes=4)

    assert frequencies.shape == (4,)
    assert np.all(frequencies > 0.0)
    assert np.all(np.diff(frequencies) > 0.0)
