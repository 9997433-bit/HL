"""Acceptance-gate selection and reporting for the criteria registry.

Acceptance tests are tagged with the registry ID they verify
(``tests/acceptance/_support.py::criterion`` attaches
``pytest.mark.criterion("AC-...")``). Marker *arguments* cannot be selected
with ``-m``, so this plugin adds the two options the Round-2 exit gate needs:

``--criterion AC-<MODULE>-NNN[a-z]?`` (repeatable)
    Run only the tests tagged with the given criterion IDs.
``--criterion-report PATH``
    Write a JSON per-criterion outcome summary to ``PATH``.

Both are used by the CI ``gates`` job and by
``tests/acceptance/test_registry_ci.py``, which re-runs the criteria the
registry marks ``verified`` and fails the claim if that run is not green.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest

#: Outcome counters tracked per criterion.
_COUNTERS = ("tests", "passed", "failed", "skipped", "errors")


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("acceptance", "acceptance-criteria gates")
    group.addoption(
        "--criterion",
        action="append",
        default=[],
        metavar="AC_ID",
        help="run only tests tagged with this acceptance-criterion ID (repeatable)",
    )
    group.addoption(
        "--criterion-report",
        action="store",
        default=None,
        metavar="PATH",
        help="write a JSON per-criterion outcome summary to PATH",
    )


def pytest_configure(config: pytest.Config) -> None:
    if config.getoption("--criterion-report"):
        config.pluginmanager.register(_CriterionReporter(config), "criterion-reporter")


def criterion_ids(item: pytest.Item) -> set[str]:
    """Registry IDs a collected test claims through its ``criterion`` marks."""
    return {mark.args[0] for mark in item.iter_markers(name="criterion") if mark.args}


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    requested = set(config.getoption("--criterion"))
    if not requested:
        return
    kept, dropped = [], []
    for item in items:
        (kept if criterion_ids(item) & requested else dropped).append(item)
    if dropped:
        config.hook.pytest_deselected(items=dropped)
    items[:] = kept


class _CriterionReporter:
    """Accumulate per-criterion outcomes and write them as JSON.

    Registered only when ``--criterion-report`` is given, so a normal run
    carries no bookkeeping.
    """

    def __init__(self, config: pytest.Config) -> None:
        self._path = Path(config.getoption("--criterion-report"))
        self._requested = sorted(set(config.getoption("--criterion")))
        self._ids_by_node: dict[str, set[str]] = {}
        self._counts: dict[str, dict[str, int]] = defaultdict(
            lambda: dict.fromkeys(_COUNTERS, 0)
        )
        self._nodes: dict[str, set[str]] = defaultdict(set)

    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(self, items: list[pytest.Item]) -> None:
        for item in items:
            ids = criterion_ids(item)
            if not ids:
                continue
            self._ids_by_node[item.nodeid] = ids
            for test_id in ids:
                self._counts[test_id]["tests"] += 1
                self._nodes[test_id].add(item.nodeid)

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        ids = self._ids_by_node.get(report.nodeid)
        if not ids:
            return
        if report.passed and report.when == "call":
            outcome = "passed"
        elif report.failed:
            outcome = "failed" if report.when == "call" else "errors"
        elif report.skipped and report.when in ("setup", "call"):
            outcome = "skipped"
        else:
            return
        for test_id in ids:
            self._counts[test_id][outcome] += 1

    def pytest_sessionfinish(self, exitstatus: int) -> None:
        criteria: dict[str, Any] = {}
        for test_id in sorted(self._counts):
            entry = dict(self._counts[test_id])
            entry["node_ids"] = sorted(self._nodes[test_id])
            criteria[test_id] = entry
        totals = {
            counter: sum(entry[counter] for entry in self._counts.values())
            for counter in _COUNTERS
        }
        document = {
            "exit_status": int(exitstatus),
            "requested": self._requested,
            "criteria": criteria,
            "totals": totals,
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
