"""Tests for ``scripts/promote_verified.py`` — the registry promotion tool.

The tool is what turns a green acceptance-gate run into an ``implemented`` ->
``verified`` status flip in ``tests/acceptance/test_criteria_registry.py``, so
these tests check both halves of that claim: that a real gate run over a
synthetic registry promotes exactly the criteria it covers, and that every way
the evidence can fall short — a red run, a skip, a missing or partial result,
evidence from another suite, a row that was never implemented — blocks the
promotion and leaves the registry byte-for-byte unchanged.

The gate is simulated by running pytest, in a subprocess, over a synthetic
registry and suite built in ``tmp_path`` with a copy of the repository's
``tests/conftest.py`` plugin. Only the fixture is synthetic: the pytest run,
the criterion report it writes, and the rewriting of the registry source are
the real ones.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from .acceptance.test_criteria_registry import REGISTRY as REAL_REGISTRY

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "promote_verified.py"
REAL_REGISTRY_PATH = REPO_ROOT / "tests" / "acceptance" / "test_criteria_registry.py"
REAL_CONFTEST = REPO_ROOT / "tests" / "conftest.py"


def _load_script():
    """Import the script by path; ``scripts/`` is deliberately not a package."""
    spec = importlib.util.spec_from_file_location("promote_verified", SCRIPT)
    assert spec is not None and spec.loader is not None, SCRIPT
    module = importlib.util.module_from_spec(spec)
    # ``dataclass`` resolves annotations through ``sys.modules``.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


promote_verified = _load_script()

MINI_SUITE = "tests/acceptance/test_gates.py"
OTHER_SUITE = "tests/acceptance/test_other.py"

#: The slice a green gate run is expected to promote.
GREEN_SLICE = (
    "AC-MINI-001",
    "AC-MINI-002",
    "AC-MINI-003",
    "AC-MINI-004",
    "AC-MINI-005",
)

MINI_REGISTRY_SOURCE = '''"""Synthetic acceptance-criteria registry."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AcceptanceCriterion:
    test_id: str
    title: str
    priority: str
    method: str
    spec_ref: str
    test_file: str
    status: str = "specified"


def _c(test_id, title, priority, method, spec_ref, test_file, status="specified"):
    return AcceptanceCriterion(
        test_id, title, priority, method, spec_ref, test_file, status
    )


_SUITE = "tests/acceptance/test_gates.py"
_OTHER = "tests/acceptance/test_other.py"

REGISTRY: tuple[AcceptanceCriterion, ...] = (
    # --- the slice a green gate covers ---------------------------------------
    _c("AC-MINI-001", "first", "P0", "oracle", "MS-1.1", _SUITE, "implemented"),
    _c("AC-MINI-002", "second", "P0", "property", "MS-1.2", _SUITE, "implemented"),
    _c("AC-MINI-003", "third", "P0", "contract", "MS-1.3", _SUITE, "implemented"),
    _c("AC-MINI-004", "fourth", "P1", "twin", "MS-1.4", _SUITE, "implemented"),
    _c("AC-MINI-005", "fifth", "P0", "oracle", "MS-1.5", _SUITE, "implemented"),
    # --- rows whose evidence does not support a promotion --------------------
    _c("AC-MINI-006", "skipping", "P0", "oracle", "MS-1.6", _SUITE, "implemented"),
    _c("AC-MINI-007", "failing", "P0", "oracle", "MS-1.7", _SUITE, "implemented"),
    _c("AC-MINI-008", "not implemented", "P1", "twin", "MS-1.8", _SUITE),
    _c("AC-MINI-009", "promoted earlier", "P0", "contract", "MS-1.9", _SUITE, "verified"),
    _c("AC-MINI-010", "misfiled", "P0", "oracle", "MS-1.10", _OTHER, "implemented"),
)
'''

MINI_SUITE_SOURCE = '''"""Synthetic acceptance suite tagged like the real ones."""

import pytest


@pytest.mark.criterion("AC-MINI-001")
def test_first():
    assert True


@pytest.mark.criterion("AC-MINI-002")
def test_second():
    assert True


@pytest.mark.criterion("AC-MINI-003")
def test_third():
    assert True


@pytest.mark.criterion("AC-MINI-004")
def test_fourth():
    assert True


@pytest.mark.criterion("AC-MINI-005")
@pytest.mark.parametrize("case", [1, 2])
def test_fifth(case):
    assert case


@pytest.mark.criterion("AC-MINI-006")
def test_sixth():
    pytest.skip("nothing to run here")


@pytest.mark.criterion("AC-MINI-007")
def test_seventh():
    raise AssertionError("deliberately red")


@pytest.mark.criterion("AC-MINI-009")
def test_ninth():
    assert True


@pytest.mark.criterion("AC-MINI-010")
def test_tenth():
    assert True
'''

MINI_PYTEST_INI = """[pytest]
markers =
    acceptance: verifies a criterion of the synthetic registry
    criterion(test_id, priority): acceptance-criterion registry ID under test
"""


@dataclass(frozen=True)
class MiniRepo:
    """A throwaway checkout the promotion tool can be pointed at."""

    root: Path
    registry: Path

    def statuses(self) -> dict[str, str]:
        rows = promote_verified.parse_registry(self.registry)
        return {test_id: row.status for test_id, row in rows.items()}

    def source(self) -> str:
        return self.registry.read_text(encoding="utf-8")

    def arguments(self, *extra: str) -> list[str]:
        return [
            "--repo-root",
            str(self.root),
            "--registry",
            str(self.registry),
            *extra,
        ]


@pytest.fixture
def mini_repo(tmp_path: Path) -> MiniRepo:
    acceptance = tmp_path / "tests" / "acceptance"
    acceptance.mkdir(parents=True)
    (tmp_path / "tests" / "__init__.py").write_text("", encoding="utf-8")
    (acceptance / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pytest.ini").write_text(MINI_PYTEST_INI, encoding="utf-8")
    # The real plugin: --criterion selection and --criterion-report writing.
    (tmp_path / "tests" / "conftest.py").write_text(
        REAL_CONFTEST.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (acceptance / "test_gates.py").write_text(MINI_SUITE_SOURCE, encoding="utf-8")
    registry = acceptance / "test_criteria_registry.py"
    registry.write_text(MINI_REGISTRY_SOURCE, encoding="utf-8")
    return MiniRepo(root=tmp_path, registry=registry)


def green_report(
    *criteria: str, tests: int = 2, suite: str = MINI_SUITE, exit_status: int = 0
) -> dict:
    """A ``--criterion-report`` document in which every criterion passed."""
    return {
        "exit_status": exit_status,
        "requested": list(criteria),
        "criteria": {
            test_id: {
                "tests": tests,
                "passed": tests,
                "failed": 0,
                "skipped": 0,
                "errors": 0,
                "node_ids": [f"{suite}::test_{index}" for index in range(tests)],
            }
            for test_id in criteria
        },
    }


def write_report(tmp_path: Path, document: dict) -> Path:
    path = tmp_path / "gate.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def run(mini_repo: MiniRepo, report: Path, *extra: str) -> int:
    return promote_verified.main(
        mini_repo.arguments("--report", str(report), *extra)
    )


# ---------------------------------------------------------------------------
# The promotion a green gate run earns
# ---------------------------------------------------------------------------


def test_a_green_gate_run_promotes_five_implemented_criteria(mini_repo, capsys):
    """The headline flip: run the gate, and the five covered rows change status."""
    before = mini_repo.statuses()
    assert [before[test_id] for test_id in GREEN_SLICE] == ["implemented"] * 5

    exit_code = promote_verified.main(
        mini_repo.arguments("--run", "--apply", *GREEN_SLICE)
    )

    assert exit_code == 0, capsys.readouterr()
    after = mini_repo.statuses()
    assert [after[test_id] for test_id in GREEN_SLICE] == ["verified"] * 5
    assert sorted(test_id for test_id, s in after.items() if s == "verified") == [
        *GREEN_SLICE,
        "AC-MINI-009",
    ]
    # Rows outside the request keep the status they had.
    unchanged = ("AC-MINI-006", "AC-MINI-007", "AC-MINI-008", "AC-MINI-010")
    assert [after[test_id] for test_id in unchanged] == [
        before[test_id] for test_id in unchanged
    ]
    assert "5 to promote" in capsys.readouterr().out


def test_the_promotion_diff_is_only_the_status_literals(mini_repo):
    before = mini_repo.source()
    promote_verified.main(mini_repo.arguments("--run", "--apply", *GREEN_SLICE))
    after = mini_repo.source()

    changed = [
        (old, new)
        for old, new in zip(before.splitlines(), after.splitlines(), strict=True)
        if old != new
    ]
    assert len(changed) == len(GREEN_SLICE)
    for old, new in changed:
        assert new == old.replace('"implemented"', '"verified"')


def test_promotion_is_idempotent(mini_repo):
    first = promote_verified.main(mini_repo.arguments("--run", "--apply", *GREEN_SLICE))
    promoted = mini_repo.source()
    second = promote_verified.main(mini_repo.arguments("--run", "--apply", *GREEN_SLICE))

    assert (first, second) == (0, 0)
    assert mini_repo.source() == promoted


def test_all_implemented_promotes_every_covered_row_and_blocks_the_rest(
    mini_repo, tmp_path
):
    report = write_report(tmp_path, green_report(*GREEN_SLICE))
    exit_code = run(mini_repo, report, "--all-implemented", "--apply")

    after = mini_repo.statuses()
    assert exit_code == 1  # the rows without evidence are reported, not promoted
    assert [after[test_id] for test_id in GREEN_SLICE] == ["verified"] * 5
    assert after["AC-MINI-006"] == "implemented"
    assert after["AC-MINI-008"] == "specified"


# ---------------------------------------------------------------------------
# Evidence that does not earn a promotion
# ---------------------------------------------------------------------------


def test_a_dry_run_writes_nothing(mini_repo, tmp_path, capsys):
    report = write_report(tmp_path, green_report(*GREEN_SLICE))
    before = mini_repo.source()

    exit_code = run(mini_repo, report, *GREEN_SLICE)

    assert exit_code == 0
    assert mini_repo.source() == before
    assert "dry run" in capsys.readouterr().out


def test_a_red_gate_run_promotes_nothing(mini_repo, capsys):
    """One failing test in the run blocks every criterion it selected."""
    before = mini_repo.source()

    exit_code = promote_verified.main(
        mini_repo.arguments("--run", "--apply", "AC-MINI-001", "AC-MINI-007")
    )

    assert exit_code == 1
    assert mini_repo.source() == before
    assert "exited" in capsys.readouterr().out


def test_a_skipped_test_is_not_evidence(mini_repo, capsys):
    before = mini_repo.source()

    exit_code = promote_verified.main(
        mini_repo.arguments("--run", "--apply", "AC-MINI-006")
    )

    assert exit_code == 1
    assert mini_repo.source() == before
    assert "skip" in capsys.readouterr().out


def test_a_criterion_absent_from_the_report_is_blocked(mini_repo, tmp_path, capsys):
    report = write_report(tmp_path, green_report("AC-MINI-001"))

    exit_code = run(mini_repo, report, "--apply", "AC-MINI-002")

    assert exit_code == 1
    assert mini_repo.statuses()["AC-MINI-002"] == "implemented"
    assert "no evidence" in capsys.readouterr().out


def test_a_partially_run_criterion_is_blocked(mini_repo, tmp_path, capsys):
    document = green_report("AC-MINI-001", tests=3)
    document["criteria"]["AC-MINI-001"]["passed"] = 2
    report = write_report(tmp_path, document)

    exit_code = run(mini_repo, report, "--apply", "AC-MINI-001")

    assert exit_code == 1
    assert mini_repo.statuses()["AC-MINI-001"] == "implemented"
    assert "2 of 3" in capsys.readouterr().out


def test_evidence_from_another_suite_is_blocked(mini_repo, tmp_path, capsys):
    """AC-MINI-010 declares another suite; its passing tests are not its own."""
    report = write_report(tmp_path, green_report("AC-MINI-010", suite=MINI_SUITE))

    exit_code = run(mini_repo, report, "--apply", "AC-MINI-010")

    assert exit_code == 1
    assert mini_repo.statuses()["AC-MINI-010"] == "implemented"
    assert OTHER_SUITE in capsys.readouterr().out


def test_a_specified_criterion_cannot_skip_the_implemented_step(
    mini_repo, tmp_path, capsys
):
    report = write_report(tmp_path, green_report("AC-MINI-008"))

    exit_code = run(mini_repo, report, "--apply", "AC-MINI-008")

    assert exit_code == 1
    assert mini_repo.statuses()["AC-MINI-008"] == "specified"
    assert "'specified'" in capsys.readouterr().out


def test_an_unknown_criterion_is_blocked(mini_repo, tmp_path, capsys):
    report = write_report(tmp_path, green_report("AC-MINI-404"))

    exit_code = run(mini_repo, report, "--apply", "AC-MINI-404")

    assert exit_code == 1
    assert "not a registry criterion" in capsys.readouterr().out


def test_an_already_verified_criterion_is_a_no_op(mini_repo, tmp_path, capsys):
    report = write_report(tmp_path, green_report("AC-MINI-009"))
    before = mini_repo.source()

    exit_code = run(mini_repo, report, "--apply", "AC-MINI-009")

    assert exit_code == 0
    assert mini_repo.source() == before
    assert "already verified" in capsys.readouterr().out


def test_a_red_report_blocks_even_a_passing_criterion(mini_repo, tmp_path):
    """The run as a whole must be green, not just the criterion's own tests."""
    report = write_report(tmp_path, green_report("AC-MINI-001", exit_status=1))

    exit_code = run(mini_repo, report, "--apply", "AC-MINI-001")

    assert exit_code == 1
    assert mini_repo.statuses()["AC-MINI-001"] == "implemented"


# ---------------------------------------------------------------------------
# Usage and failure handling
# ---------------------------------------------------------------------------


def test_a_missing_report_exits_two(mini_repo, tmp_path, capsys):
    exit_code = run(mini_repo, tmp_path / "absent.json", "AC-MINI-001")

    assert exit_code == 2
    assert "promotion failed" in capsys.readouterr().err


def test_an_unparsable_registry_exits_two(mini_repo, tmp_path, capsys):
    mini_repo.registry.write_text("REGISTRY = (\n", encoding="utf-8")
    report = write_report(tmp_path, green_report("AC-MINI-001"))

    exit_code = run(mini_repo, report, "AC-MINI-001")

    assert exit_code == 2
    assert "cannot parse" in capsys.readouterr().err


def test_a_registry_without_rows_exits_two(mini_repo, tmp_path, capsys):
    mini_repo.registry.write_text("VALUES = (1, 2)\n", encoding="utf-8")
    report = write_report(tmp_path, green_report("AC-MINI-001"))

    exit_code = run(mini_repo, report, "AC-MINI-001")

    assert exit_code == 2
    assert "no REGISTRY assignment" in capsys.readouterr().err


def test_an_evidence_source_is_required(mini_repo):
    with pytest.raises(SystemExit) as failure:
        promote_verified.main(mini_repo.arguments("AC-MINI-001"))
    assert failure.value.code == 2


def test_a_criterion_selection_is_required(mini_repo, tmp_path):
    report = write_report(tmp_path, green_report("AC-MINI-001"))
    with pytest.raises(SystemExit) as failure:
        promote_verified.main(mini_repo.arguments("--report", str(report)))
    assert failure.value.code == 2


def test_json_output_reports_every_decision(mini_repo, tmp_path, capsys):
    report = write_report(tmp_path, green_report("AC-MINI-001"))

    exit_code = run(mini_repo, report, "--json", "AC-MINI-001", "AC-MINI-002")

    document = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert document["applied"] is False
    assert [entry["action"] for entry in document["decisions"]] == [
        "promote",
        "blocked",
    ]
    assert document["decisions"][0]["evidence"]["passed"] == 2


def test_the_gate_command_selects_only_the_requested_criteria(tmp_path):
    command = promote_verified.gate_command(
        ("AC-MINI-001", "AC-MINI-002"), tmp_path / "gate.json", tmp_path / "acceptance"
    )

    assert command.count("--criterion") == 2
    assert "--criterion-report" in command
    assert str(tmp_path / "acceptance") in command


# ---------------------------------------------------------------------------
# The tool against the registry it is meant to maintain
# ---------------------------------------------------------------------------


def test_the_real_registry_parses_to_the_rows_python_imports():
    """The tool's static view of the registry equals the imported truth."""
    rows = promote_verified.parse_registry(REAL_REGISTRY_PATH)

    assert set(rows) == {entry.test_id for entry in REAL_REGISTRY}
    for entry in REAL_REGISTRY:
        row = rows[entry.test_id]
        assert (row.status, row.priority, row.test_file) == (
            entry.status,
            entry.priority,
            entry.test_file,
        )


def test_the_real_verified_rows_are_recognized_as_promoted():
    """Re-promoting the checked-in ``verified`` slice is a no-op, not an edit."""
    rows = promote_verified.parse_registry(REAL_REGISTRY_PATH)
    verified = [entry.test_id for entry in REAL_REGISTRY if entry.status == "verified"]

    decisions = promote_verified.evaluate(rows, {"criteria": {}}, verified)

    assert verified, "the registry has no verified criterion to check"
    assert {decision.action for decision in decisions} == {"already-verified"}
