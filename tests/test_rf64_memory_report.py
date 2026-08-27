"""Schema and honesty checks for the SOTA B3 RF64 memory evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmarks import rf64_memory_probe

REPORT_PATH = (
    Path(__file__).resolve().parents[1]
    / ".agent_workspace"
    / "v1.0"
    / "rf64-memory-report.json"
)


def _load_report() -> dict:
    assert REPORT_PATH.is_file(), (
        "run `python3 benchmarks/rf64_memory_probe.py --mode dense --formal` "
        "to publish the B3 report"
    )
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def test_rf64_memory_report_schema() -> None:
    report = _load_report()

    assert report["schema_version"] == 1
    assert report["harness"] == "benchmarks/rf64_memory_probe.py"
    assert report["checklist_item"] == "B3"
    assert report["mode"] in {"dense", "sparse", "mock"}
    assert isinstance(report["formal_requested"], bool)
    assert isinstance(report["formal_slo_verified"], bool)
    assert {"python", "platform", "processor"} <= set(report["environment"])

    config = report["config"]
    assert config["frames"] > 0
    assert config["channels"] > 0
    assert config["sample_rate"] > 0
    assert config["subtype"] == "PCM_16"
    assert config["block_frames"] > 0
    assert config["cache_blocks"] > 0
    assert config["rss_sample_every_blocks"] > 0
    assert config["write_chunk_frames"] > 0

    fixture = report["fixture"]
    assert fixture["file_size_bytes"] == report["file_size_bytes"]
    assert fixture["pcm_bytes_written"] >= 0
    assert fixture["allocated_bytes"] >= 0
    assert fixture["allocated_ratio"] >= 0.0
    assert isinstance(fixture["dense_allocation_verified"], bool)
    assert fixture["write_method"]
    assert fixture["pcm_content"]

    assert len(report["results"]) == 1
    result = report["results"][0]
    assert result["slo_id"] == "rf64-4gb-rss"
    assert result["status"] in {"pass", "fail"}
    assert isinstance(result["threshold_pass"], bool)
    assert result["formal_slo_verified"] is report["formal_slo_verified"]
    assert result["measured"]["file_size_bytes"] == report["file_size_bytes"]
    assert result["measured"]["peak_rss_bytes"] == report["peak_rss_bytes"]
    assert result["measured"]["frames_read"] <= result["measured"]["n_frames"]
    assert result["measured"]["blocks_read"] > 0
    assert result["measured"]["container"] == "RF64"
    assert result["measured"]["should_stream"] is True
    assert result["threshold"]["file_size_bytes_min"] == 4 * 1024**3
    assert result["threshold"]["peak_rss_bytes_max"] == 1024**3
    assert result["threshold_pass"] is (
        report["file_size_bytes"] > result["threshold"]["file_size_bytes_min"]
        and report["peak_rss_bytes"] < result["threshold"]["peak_rss_bytes_max"]
        and result["measured"]["frames_read"] == config["frames"]
    )
    assert result["status"] == ("pass" if result["threshold_pass"] else "fail")


def test_formal_claim_requires_dense_fully_allocated_passing_fixture() -> None:
    report = _load_report()
    result = report["results"][0]
    fixture = report["fixture"]
    config = report["config"]
    expected_pcm_bytes = config["frames"] * config["channels"] * 2

    formal_eligible = (
        report["mode"] == "dense"
        and fixture["dense_allocation_verified"] is True
        and fixture["allocated_ratio"] >= rf64_memory_probe.DENSE_ALLOCATION_MIN_RATIO
        and fixture["pcm_bytes_written"] == expected_pcm_bytes
        and isinstance(fixture["payload_sha256"], str)
        and len(fixture["payload_sha256"]) == 64
    )
    assert report["formal_slo_verified"] is (
        report["formal_requested"] and formal_eligible and result["threshold_pass"]
    )

    if report["formal_slo_verified"]:
        assert result["evidence"] == "direct-dense"
        assert result["status"] == "pass"
        assert report["summary"]["formal_slos_verified"] == 1


@pytest.mark.parametrize("mode", ["auto", "sparse", "mock"])
def test_non_dense_modes_reject_formal_claim(mode: str) -> None:
    with pytest.raises(SystemExit):
        rf64_memory_probe._parse_args(["--mode", mode, "--formal"])


def test_dense_writer_sequentially_writes_decodable_pcm(tmp_path: Path) -> None:
    fixture_path = tmp_path / "small-dense.rf64"
    n_frames = 4_097
    evidence = rf64_memory_probe.write_dense_rf64(
        fixture_path,
        n_frames=n_frames,
        channels=2,
        sample_rate=48_000,
        write_chunk_frames=257,
    )

    assert evidence["write_method"] == "sequential-chunked-write"
    assert evidence["pcm_bytes_written"] == n_frames * 2 * 2
    assert evidence["file_size_bytes"] == fixture_path.stat().st_size
    assert evidence["dense_allocation_verified"] is True
    assert evidence["allocated_ratio"] >= rf64_memory_probe.DENSE_ALLOCATION_MIN_RATIO
    assert isinstance(evidence["payload_sha256"], str)
    assert len(evidence["payload_sha256"]) == 64

    with rf64_memory_probe.StreamingSampleSource(fixture_path, block_frames=256) as source:
        block = source.read(0, n_frames)
    assert block.shape == (n_frames, 2)
    assert block.any()
