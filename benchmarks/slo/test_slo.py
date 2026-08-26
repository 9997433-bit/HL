"""Pytest entry points for the fable §7 headless SLO probes."""

from __future__ import annotations

import math
import os

import pytest

from benchmarks.slo import run_slo_suite

EXPECTED_SLOS = {"L1", "T1", "T2", "T3", "U1", "U2/U3"}


@pytest.fixture(scope="session")
def slo_report(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_slo_suite(tmp_path_factory.mktemp("slo"), quick=True)


def test_suite_covers_key_latency_throughput_and_loading_slos(slo_report: dict) -> None:
    assert {result["slo_id"] for result in slo_report["results"]} == EXPECTED_SLOS


@pytest.mark.parametrize("slo_id", sorted(EXPECTED_SLOS))
def test_slo_probe_returns_finite_measurements(slo_report: dict, slo_id: str) -> None:
    result = next(item for item in slo_report["results"] if item["slo_id"] == slo_id)
    assert result["status"] in {"pass", "fail"}
    timing = result["measured"].get("median_ms")
    if timing is None:
        timing = result["measured"]["callback_read_timing"]["median_ms"]
    assert math.isfinite(timing)
    assert timing >= 0.0


def test_proxy_thresholds_when_explicitly_enforced(slo_report: dict) -> None:
    """Set SLO_ENFORCE=1 on a controlled reference host to make proxies gating."""
    if os.environ.get("SLO_ENFORCE") != "1":
        pytest.skip("proxy thresholds are observational unless SLO_ENFORCE=1")
    failures = [
        f"{item['slo_id']}: {item['measured']}"
        for item in slo_report["results"]
        if not item["threshold_pass"]
    ]
    assert not failures, "\n".join(failures)
