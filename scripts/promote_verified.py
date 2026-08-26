#!/usr/bin/env python3
"""Promote acceptance criteria from ``implemented`` to ``verified``.

Section 1.5 of ``docs/ACCEPTANCE_CRITERIA.md`` defines the last status
transition as "test passing in CI on the default branch", and
``tests/acceptance/test_registry_ci.py`` keeps every promoted row honest by
re-running its tagged tests as a gate. This script is the other half: it
performs the promotion itself, so a status flip is the recorded outcome of a
green gate run rather than a hand edit of the registry.

The gate is the ``--criterion``/``--criterion-report`` selection of
``tests/conftest.py`` — the same one CI runs. Either let this script run it
(``--run``) or hand it a report a previous run wrote (``--report``); a
criterion is promoted only when that report shows every one of its collected
tests passing, in the suite the registry names, in a run that exited zero.

Typical use::

    python scripts/promote_verified.py --run --apply AC-DYN-001 AC-DYN-002

Nothing is written without ``--apply``: the default is a plan on stdout. The
exit status is 0 when every requested criterion ends up ``verified``, 1 when
any of them is blocked, and 2 for a usage or I/O error.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = Path("tests/acceptance/test_criteria_registry.py")
DEFAULT_ACCEPTANCE_DIR = Path("tests/acceptance")

#: The status a criterion must hold to be promotable, and its successor.
PROMOTABLE_FROM = "implemented"
PROMOTED_TO = "verified"

#: Positional signature of the registry's ``_c(...)`` row constructor.
ROW_FIELDS = ("test_id", "title", "priority", "method", "spec_ref", "test_file", "status")

#: Actions a criterion can be assigned by :func:`evaluate`.
PROMOTE = "promote"
ALREADY_VERIFIED = "already-verified"
BLOCKED = "blocked"


class PromotionError(RuntimeError):
    """Registry, report, or gate problem that stops the tool before it writes."""


@dataclass(frozen=True)
class RegistryRow:
    """One ``_c(...)`` row of the registry, with the source span of its status."""

    test_id: str
    priority: str
    test_file: str
    status: str
    line: int              # 1-based line holding the status literal
    start_column: int      # byte columns, as reported by ``ast``
    end_column: int


@dataclass(frozen=True)
class Decision:
    """What the tool will do with one requested criterion, and why."""

    test_id: str
    action: str
    reason: str
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def blocked(self) -> bool:
        return self.action == BLOCKED

    def as_dict(self) -> dict[str, Any]:
        return {
            "test_id": self.test_id,
            "action": self.action,
            "reason": self.reason,
            "evidence": self.evidence,
        }


# ---------------------------------------------------------------------------
# Registry parsing and rewriting
# ---------------------------------------------------------------------------


def _row_arguments(call: ast.Call) -> dict[str, ast.expr]:
    arguments = dict(zip(ROW_FIELDS, call.args, strict=False))
    for keyword in call.keywords:
        if keyword.arg in ROW_FIELDS:
            arguments[keyword.arg] = keyword.value
    return arguments


def _string_constants(tree: ast.Module) -> dict[str, str]:
    """Module-level ``NAME = "..."`` bindings, e.g. the shared suite paths."""
    constants: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Constant):
            continue
        if not isinstance(node.value.value, str):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                constants[target.id] = node.value.value
    return constants


def _literal(node: ast.expr | None, symbols: dict[str, str] | None = None) -> str | None:
    """The string a row argument carries, directly or through a module constant."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name) and symbols is not None:
        return symbols.get(node.id)
    return None


def _registry_calls(tree: ast.Module) -> list[ast.Call]:
    """The ``_c(...)`` calls of the ``REGISTRY`` tuple, in source order."""
    for node in tree.body:
        target = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target = node.target.id
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            first = node.targets[0]
            target = first.id if isinstance(first, ast.Name) else None
        if target != "REGISTRY" or node.value is None:
            continue
        if not isinstance(node.value, ast.Tuple | ast.List):
            raise PromotionError("REGISTRY is not a tuple/list literal")
        return [
            element
            for element in node.value.elts
            if isinstance(element, ast.Call)
            and isinstance(element.func, ast.Name)
            and element.func.id == "_c"
        ]
    raise PromotionError("no REGISTRY assignment found")


def parse_registry(path: Path) -> dict[str, RegistryRow]:
    """Rows of the registry keyed by criterion ID, with rewritable status spans.

    The registry is read as source rather than imported: the tool has to know
    *where* each status literal sits to rewrite it, and parsing keeps it usable
    against a registry copy that is not on ``sys.path``.
    """
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PromotionError(f"cannot read registry {path}: {exc}") from exc
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise PromotionError(f"cannot parse registry {path}: {exc}") from exc

    symbols = _string_constants(tree)
    rows: dict[str, RegistryRow] = {}
    for call in _registry_calls(tree):
        arguments = _row_arguments(call)
        test_id = _literal(arguments.get("test_id"), symbols)
        if test_id is None:
            raise PromotionError(f"{path}: a registry row has a non-literal ID")
        status_node = arguments.get("status")
        status = _literal(status_node)
        if status_node is None:
            # No status argument: the row defaults to ``specified`` and has no
            # literal to rewrite. Recorded so requests for it are refused.
            status, line, start, end = "specified", call.lineno, -1, -1
        elif status is None:
            raise PromotionError(f"{path}: {test_id} has a non-literal status")
        else:
            if status_node.lineno != status_node.end_lineno:
                raise PromotionError(f"{path}: {test_id} status spans several lines")
            line = status_node.lineno
            start = status_node.col_offset
            end = status_node.end_col_offset or start
        if test_id in rows:
            raise PromotionError(f"{path}: duplicate registry row {test_id}")
        rows[test_id] = RegistryRow(
            test_id=test_id,
            priority=_literal(arguments.get("priority"), symbols) or "",
            test_file=_literal(arguments.get("test_file"), symbols) or "",
            status=status,
            line=line,
            start_column=start,
            end_column=end,
        )
    if not rows:
        raise PromotionError(f"{path}: REGISTRY has no rows")
    return rows


def rewrite_statuses(source: str, rows: Iterable[RegistryRow], status: str) -> str:
    """Return ``source`` with the status literal of each row replaced.

    Only the quoted status literals change; every other byte of the file —
    comments, spacing, row order — is preserved, so the promotion diff is
    exactly the claim it makes.
    """
    lines = source.splitlines(keepends=True)
    replacement = f'"{status}"'.encode()
    for row in rows:
        if row.start_column < 0:
            raise PromotionError(f"{row.test_id} has no status literal to rewrite")
        index = row.line - 1
        if not 0 <= index < len(lines):
            raise PromotionError(f"{row.test_id}: status line {row.line} is out of range")
        encoded = lines[index].encode("utf-8")
        current = encoded[row.start_column : row.end_column].decode("utf-8")
        if current.strip("\"'") != row.status:
            raise PromotionError(
                f"{row.test_id}: expected status {row.status!r} at line {row.line}, "
                f"found {current!r} — the registry changed under the tool"
            )
        lines[index] = (
            encoded[: row.start_column] + replacement + encoded[row.end_column :]
        ).decode("utf-8")
    return "".join(lines)


# ---------------------------------------------------------------------------
# Gate evidence
# ---------------------------------------------------------------------------


def gate_command(
    criteria: Sequence[str],
    report_path: Path,
    acceptance_dir: Path,
    python: str = sys.executable,
) -> list[str]:
    """The pytest invocation whose report backs a promotion."""
    command = [
        python,
        "-m",
        "pytest",
        str(acceptance_dir),
        "-p",
        "no:cacheprovider",
        "--criterion-report",
        str(report_path),
    ]
    for test_id in criteria:
        command += ["--criterion", test_id]
    return command


def _gate_environment(repo_root: Path) -> dict[str, str]:
    environment = dict(os.environ)
    # A gate must not inherit the caller's pytest flags (``-x``, ``-k``, ...).
    environment.pop("PYTEST_ADDOPTS", None)
    source = str(repo_root / "src")
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        source if not existing else os.pathsep.join([source, existing])
    )
    return environment


def run_gate(
    criteria: Sequence[str],
    repo_root: Path,
    acceptance_dir: Path,
    python: str = sys.executable,
    timeout: float = 1800.0,
) -> tuple[dict[str, Any], str]:
    """Run the gate for ``criteria`` and return ``(report, captured output)``."""
    if not criteria:
        raise PromotionError("--run needs at least one criterion to select")
    with tempfile.TemporaryDirectory(prefix="openfemlab-promote-") as directory:
        report_path = Path(directory) / "gate.json"
        command = gate_command(criteria, report_path, acceptance_dir, python)
        try:
            completed = subprocess.run(  # noqa: S603 - fixed command, no shell
                command,
                cwd=repo_root,
                env=_gate_environment(repo_root),
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PromotionError(f"gate run failed to complete: {exc}") from exc
        output = completed.stdout + completed.stderr
        if not report_path.is_file():
            raise PromotionError(f"the gate run wrote no report; output:\n{output}")
        report = load_report(report_path)
    return report, output


def load_report(path: Path) -> dict[str, Any]:
    """Read a ``--criterion-report`` JSON document."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise PromotionError(f"cannot read gate report {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise PromotionError(f"gate report {path} is not valid JSON: {exc}") from exc
    if not isinstance(document, dict) or "criteria" not in document:
        raise PromotionError(f"gate report {path} has no 'criteria' section")
    return document


# ---------------------------------------------------------------------------
# The promotion decision
# ---------------------------------------------------------------------------


def _counter(entry: dict[str, Any], name: str) -> int:
    value = entry.get(name, 0)
    return int(value) if isinstance(value, int) else 0


def _evidence_problem(row: RegistryRow, entry: dict[str, Any] | None) -> str | None:
    """Why the gate report does not verify ``row``, or ``None`` when it does."""
    if entry is None:
        return "no evidence in the gate report"
    tests = _counter(entry, "tests")
    passed = _counter(entry, "passed")
    failed = _counter(entry, "failed")
    errors = _counter(entry, "errors")
    skipped = _counter(entry, "skipped")
    if failed or errors:
        return f"the gate run is not green ({failed} failed, {errors} errors)"
    if skipped:
        return f"{skipped} of {tests} tagged tests skipped; a skip is not evidence"
    if passed < 1:
        return "no test passed for this criterion"
    if passed != tests:
        return f"only {passed} of {tests} collected tests reported passing"
    misplaced = [
        node_id
        for node_id in entry.get("node_ids", ())
        if not Path(str(node_id).split("::")[0]).as_posix().endswith(row.test_file)
    ]
    if misplaced:
        return f"evidence outside the declared suite {row.test_file}: {misplaced}"
    return None


def evaluate(
    rows: dict[str, RegistryRow],
    report: dict[str, Any],
    requested: Sequence[str],
) -> tuple[Decision, ...]:
    """Decide, per requested criterion, whether the report supports promotion."""
    criteria = report.get("criteria") or {}
    exit_status = int(report.get("exit_status", 0) or 0)
    decisions = []
    for test_id in requested:
        row = rows.get(test_id)
        if row is None:
            decisions.append(Decision(test_id, BLOCKED, "not a registry criterion"))
            continue
        entry = criteria.get(test_id)
        evidence = {
            key: _counter(entry or {}, key)
            for key in ("tests", "passed", "failed", "skipped", "errors")
        }
        if row.status == PROMOTED_TO:
            decisions.append(
                Decision(test_id, ALREADY_VERIFIED, "already verified", evidence)
            )
            continue
        if row.status != PROMOTABLE_FROM:
            decisions.append(
                Decision(
                    test_id,
                    BLOCKED,
                    f"status {row.status!r}: only {PROMOTABLE_FROM!r} rows can be "
                    "promoted (tag a test for it first)",
                    evidence,
                )
            )
            continue
        if exit_status != 0:
            decisions.append(
                Decision(
                    test_id,
                    BLOCKED,
                    f"the gate run exited {exit_status}; a red run promotes nothing",
                    evidence,
                )
            )
            continue
        problem = _evidence_problem(row, entry)
        if problem is not None:
            decisions.append(Decision(test_id, BLOCKED, problem, evidence))
            continue
        decisions.append(
            Decision(
                test_id,
                PROMOTE,
                f"{PROMOTABLE_FROM} -> {PROMOTED_TO}",
                evidence,
            )
        )
    return tuple(decisions)


def promote(
    registry_path: Path,
    decisions: Sequence[Decision],
    rows: dict[str, RegistryRow],
) -> str:
    """Write the promotions of ``decisions`` into the registry and return the source."""
    promoted = [rows[d.test_id] for d in decisions if d.action == PROMOTE]
    source = registry_path.read_text(encoding="utf-8")
    if not promoted:
        return source
    updated = rewrite_statuses(source, promoted, PROMOTED_TO)
    registry_path.write_text(updated, encoding="utf-8")
    return updated


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def _requested_ids(
    args: argparse.Namespace, rows: dict[str, RegistryRow]
) -> tuple[str, ...]:
    if args.all_implemented:
        implemented = tuple(
            test_id for test_id, row in rows.items() if row.status == PROMOTABLE_FROM
        )
        return tuple(dict.fromkeys(implemented + tuple(args.criteria)))
    return tuple(dict.fromkeys(args.criteria))


def _print_plan(
    decisions: Sequence[Decision], registry_path: Path, report_source: str, applied: bool
) -> None:
    print(f"registry: {registry_path}")
    print(f"evidence: {report_source}")
    width = max((len(d.test_id) for d in decisions), default=0)
    for decision in decisions:
        counters = decision.evidence
        passed = f"{counters.get('passed', 0)}/{counters.get('tests', 0)} passed"
        print(
            f"  {decision.action:<16} {decision.test_id:<{width}}  "
            f"{decision.reason} ({passed})"
        )
    counts = {
        action: sum(1 for d in decisions if d.action == action)
        for action in (PROMOTE, ALREADY_VERIFIED, BLOCKED)
    }
    tail = "written" if applied else "dry run — pass --apply to write"
    print(
        f"{counts[PROMOTE]} to promote, {counts[ALREADY_VERIFIED]} already verified, "
        f"{counts[BLOCKED]} blocked ({tail})"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Promote acceptance criteria to 'verified' on green gate evidence.",
    )
    parser.add_argument(
        "criteria",
        nargs="*",
        metavar="AC_ID",
        help="criterion IDs to promote (e.g. AC-DYN-001)",
    )
    parser.add_argument(
        "--all-implemented",
        action="store_true",
        help="consider every 'implemented' row of the registry",
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--run",
        action="store_true",
        help="run the acceptance gate for the requested criteria and use its report",
    )
    source.add_argument(
        "--report",
        type=Path,
        help="use an existing --criterion-report JSON document as evidence",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write the promotions (default: print the plan and change nothing)",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    parser.add_argument(
        "--repo-root", type=Path, default=ROOT, help="repository root (default: this checkout)"
    )
    parser.add_argument(
        "--registry",
        type=Path,
        help=f"registry module to rewrite (default: <repo root>/{DEFAULT_REGISTRY})",
    )
    args = parser.parse_args(argv)

    repo_root: Path = args.repo_root
    registry_path: Path = args.registry or repo_root / DEFAULT_REGISTRY
    if not args.criteria and not args.all_implemented:
        parser.error("name at least one criterion, or pass --all-implemented")
    if not args.run and args.report is None:
        parser.error("choose an evidence source: --run or --report PATH")

    try:
        rows = parse_registry(registry_path)
        requested = _requested_ids(args, rows)
        if args.run:
            report, output = run_gate(
                requested, repo_root, repo_root / DEFAULT_ACCEPTANCE_DIR
            )
            report_source = "gate run"
        else:
            report, output = load_report(args.report), ""
            report_source = str(args.report)
        decisions = evaluate(rows, report, requested)
        applied = args.apply and any(d.action == PROMOTE for d in decisions)
        if args.apply:
            promote(registry_path, decisions, rows)
    except PromotionError as exc:
        print(f"promotion failed: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(
            json.dumps(
                {
                    "registry": str(registry_path),
                    "evidence": report_source,
                    "applied": applied,
                    "decisions": [d.as_dict() for d in decisions],
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        _print_plan(decisions, registry_path, report_source, applied)
        if any(d.blocked for d in decisions) and output:
            print(output, file=sys.stderr)
    return 1 if any(d.blocked for d in decisions) else 0


if __name__ == "__main__":
    raise SystemExit(main())
