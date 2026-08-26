"""R2-T09 — the gate run that backs every ``verified`` registry status.

Section 1.5 of ``docs/ACCEPTANCE_CRITERIA.md`` defines the last status
transition as "test passing in CI on the default branch", which until now was
a promise no test could check: nothing re-ran a criterion's tests as a gate, so
nothing could tell a ``verified`` row from an ``implemented`` one.

This suite is the executable half of that definition. It re-runs, in clean
pytest subprocesses, exactly the tagged tests of the criteria the registry
marks ``verified`` — the same selection the CI ``gates`` job runs — and fails
if that run is not green, if it is not reproducible under a different hash
seed (section 1.4: a criterion is only verified if its test is deterministic),
if the evidence does not land in the suite the registry names, or if the
workflow stops running the gate. A ``verified`` row therefore cannot survive a
red, non-deterministic, or missing gate: the promotion has to be reverted
before the suite goes green again.

The two runs are launched concurrently, so the gate costs roughly one run of
the promoted criteria rather than two.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from functools import lru_cache
from json import loads
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import yaml

from .test_criteria_registry import (
    CI_GATE_JOB,
    CI_WORKFLOW,
    REPO_ROOT,
    get_criterion,
    verified_ids,
)

ACCEPTANCE_DIR = Path(__file__).resolve().parent

#: Wall-clock ceiling for one gate subprocess; the promoted slice runs in
#: seconds, so hitting this means the gate hung rather than ran slowly.
GATE_TIMEOUT_SECONDS = 900

#: Two interpreter hash seeds. Identical outcomes across both are the
#: determinism half of the section 1.4 rule; a criterion whose result depends
#: on iteration order fails here instead of flaking later in CI.
HASH_SEEDS = ("0", "104729")

#: Minimum size of the promoted slice (R2-T09 wires one gate per module).
MINIMUM_VERIFIED = 5


@dataclass(frozen=True)
class GateRun:
    """Outcome of one simulated CI gate run over the ``verified`` criteria."""

    seed: str
    exit_status: int
    report: dict
    output: str

    @property
    def criteria(self) -> dict[str, dict]:
        return self.report["criteria"]

    @property
    def totals(self) -> dict[str, int]:
        return self.report["totals"]

    def outcomes(self) -> dict[str, tuple[int, ...]]:
        """Per-criterion ``(tests, passed, failed, skipped, errors)`` tuples."""
        return {
            test_id: tuple(
                entry[counter]
                for counter in ("tests", "passed", "failed", "skipped", "errors")
            )
            for test_id, entry in self.criteria.items()
        }


def gate_command(report_path: Path) -> list[str]:
    """The pytest invocation CI runs for the ``verified`` criteria."""
    command = [
        sys.executable,
        "-m",
        "pytest",
        str(ACCEPTANCE_DIR),
        "-p",
        "no:cacheprovider",
        "--criterion-report",
        str(report_path),
    ]
    for test_id in verified_ids():
        command += ["--criterion", test_id]
    return command


#: Single-threaded BLAS keeps the reduction order of the linear algebra fixed,
#: so a difference between the two runs is the test's, not the thread pool's.
_SINGLE_THREAD = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
)


def _gate_environment(seed: str) -> dict[str, str]:
    environment = dict(os.environ)
    environment["PYTHONHASHSEED"] = seed
    environment.update(dict.fromkeys(_SINGLE_THREAD, "1"))
    # A gate must not inherit the parent run's flags (``-x``, ``-k``, ...).
    environment.pop("PYTEST_ADDOPTS", None)
    source = str(REPO_ROOT / "src")
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        source if not existing else os.pathsep.join([source, existing])
    )
    return environment


@lru_cache(maxsize=1)
def gate_runs() -> tuple[GateRun, ...]:
    """Run the gate once per hash seed, concurrently, and cache the outcome."""
    promoted = verified_ids()
    if not promoted:
        pytest.skip("no criterion is promoted to 'verified'")
    with TemporaryDirectory(prefix="openfemlab-gate-") as directory:
        reports = {
            seed: Path(directory) / f"gate-{seed}.json" for seed in HASH_SEEDS
        }
        processes = {
            seed: subprocess.Popen(  # noqa: S603 - fixed command, no shell
                gate_command(path),
                cwd=REPO_ROOT,
                env=_gate_environment(seed),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            for seed, path in reports.items()
        }
        runs = []
        for seed, process in processes.items():
            try:
                output = process.communicate(timeout=GATE_TIMEOUT_SECONDS)[0]
            except subprocess.TimeoutExpired:  # pragma: no cover - hung gate
                process.kill()
                output = process.communicate()[0]
                raise AssertionError(
                    f"gate run (seed {seed}) exceeded {GATE_TIMEOUT_SECONDS}s"
                ) from None
            path = reports[seed]
            if not path.is_file():  # pragma: no cover - gate failed to start
                raise AssertionError(
                    f"gate run (seed {seed}) wrote no report; output:\n{output}"
                )
            runs.append(
                GateRun(
                    seed=seed,
                    exit_status=process.returncode,
                    report=loads(path.read_text(encoding="utf-8")),
                    output=output,
                )
            )
    return tuple(runs)


def primary_run() -> GateRun:
    return gate_runs()[0]


# ---------------------------------------------------------------------------
# The promoted slice
# ---------------------------------------------------------------------------


def test_promoted_slice_is_at_least_the_round2_minimum():
    promoted = verified_ids()
    assert len(promoted) >= MINIMUM_VERIFIED, (
        f"R2-T09 promotes at least {MINIMUM_VERIFIED} criteria; "
        f"registry has {len(promoted)}: {list(promoted)}"
    )


def test_promoted_criteria_were_implemented_before_promotion():
    """A promotion may only lift a criterion that already had a tagged test."""
    orphans = [
        test_id
        for test_id in verified_ids()
        if not (REPO_ROOT / get_criterion(test_id).test_file).is_file()
    ]
    assert not orphans, f"verified criteria without their suite on disk: {orphans}"


# ---------------------------------------------------------------------------
# The simulated CI run
# ---------------------------------------------------------------------------


def test_gate_run_is_green():
    run = primary_run()
    assert run.exit_status == 0, (
        f"the gate run for the verified criteria failed:\n{run.output}"
    )
    totals = run.totals
    assert totals["failed"] == 0 and totals["errors"] == 0, totals
    assert totals["skipped"] == 0, (
        f"a skipped test cannot verify a criterion: {totals}\n{run.output}"
    )
    assert totals["tests"] > 0, totals


def test_gate_run_exercises_exactly_the_verified_criteria():
    run = primary_run()
    assert set(run.criteria) == set(verified_ids()), (
        f"gate ran {sorted(run.criteria)} for verified {sorted(verified_ids())}"
    )
    assert sorted(run.report["requested"]) == sorted(verified_ids())


def test_every_verified_criterion_has_passing_evidence():
    run = primary_run()
    weak = {
        test_id: entry
        for test_id, entry in run.criteria.items()
        if entry["passed"] < 1 or entry["failed"] or entry["errors"]
    }
    assert not weak, f"criteria promoted without passing evidence: {weak}"


def test_gate_evidence_lands_in_the_suite_the_registry_names():
    run = primary_run()
    misplaced = []
    for test_id, entry in run.criteria.items():
        declared = get_criterion(test_id).test_file
        for node_id in entry["node_ids"]:
            if not Path(node_id.split("::")[0]).as_posix().endswith(declared):
                misplaced.append((test_id, node_id, declared))
    assert not misplaced, f"gate evidence outside the declared suite: {misplaced}"


def test_gate_run_is_reproducible_under_a_different_hash_seed():
    first, second = gate_runs()[0], gate_runs()[1]
    assert second.exit_status == first.exit_status == 0, (
        f"seed {second.seed} run differs:\n{second.output}"
    )
    assert second.outcomes() == first.outcomes(), (
        "the gate is not deterministic across hash seeds: "
        f"{first.outcomes()} vs {second.outcomes()}"
    )


# ---------------------------------------------------------------------------
# The workflow that turns the simulation into a real CI run
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _workflow() -> dict:
    assert CI_WORKFLOW.is_file(), f"missing CI workflow: {CI_WORKFLOW}"
    return yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))


def _gate_job_commands() -> str:
    jobs = _workflow().get("jobs", {})
    assert CI_GATE_JOB in jobs, (
        f"CI workflow has no {CI_GATE_JOB!r} job; verified statuses would rest "
        f"on nothing. Jobs: {sorted(jobs)}"
    )
    steps = jobs[CI_GATE_JOB].get("steps", [])
    return "\n".join(str(step.get("run", "")) for step in steps)


@pytest.mark.parametrize(
    ("what", "fragment"),
    [
        ("import check", "import openfemlab"),
        ("lint", "ruff check"),
        ("registry consistency", "test_criteria_registry.py"),
        ("gate run", "test_registry_ci.py"),
        ("acceptance suites", "-m acceptance"),
    ],
)
def test_ci_gate_job_runs_the_round2_exit_checks(what, fragment):
    assert fragment in _gate_job_commands(), (
        f"the CI {CI_GATE_JOB!r} job no longer runs the {what} step ({fragment!r})"
    )


def test_ci_still_runs_the_full_suite_on_every_push():
    workflow = _workflow()
    triggers = workflow.get(True, workflow.get("on", {}))
    assert "push" in triggers and "pull_request" in triggers, triggers
    full_suite = [
        "\n".join(str(step.get("run", "")) for step in job.get("steps", []))
        for name, job in workflow.get("jobs", {}).items()
        if name != CI_GATE_JOB
    ]
    assert any("pytest" in commands for commands in full_suite), (
        "no job outside the gate job runs the full suite"
    )
