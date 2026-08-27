"""Checks that the hardware certification runbook and its runner stay honest.

docs/HARDWARE_CERTIFICATION.md tells a person at a bench how to upgrade the C4
evidence from a server loopback to a physical USB interface, and
scripts/run-hardware-certification.sh is the one-command form of the same
procedure. Documentation rots in two ways: the paths it names stop existing,
and the automation it describes drifts away from what it says. Both failure
modes are checked here.

The static checks read the two files and hold them to each other: every
repository path the runbook links to must exist, the steps it promises (kernel
modules, default device, ``--require-physical``, republishing alongside the
loopback evidence) must be present, and the script must run the same probes
with the same gate and publish to the same place the runbook says it does.

The functional check runs the script on this host. This host has no sound
card, which is exactly the case the script must handle honestly: exit 1, an
honest ``not-certified`` inventory published, and no round-trip report — a
runner that measured a null sink and called it hardware would defeat the point
of the whole procedure. On a host that does have a card the check is skipped
rather than half-run: a real certification needs a loopback cable no test can
plug in.
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
from pathlib import Path

import pytest

from benchmarks import usb_audio_probe as probe

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "HARDWARE_CERTIFICATION.md"
SCRIPT = REPO_ROOT / "scripts" / "run-hardware-certification.sh"

USB_PROBE = "benchmarks/usb_audio_probe.py"
ROUNDTRIP_PROBE = "benchmarks/roundtrip_latency_probe.py"

#: Where the hardware evidence goes: alongside the loopback evidence, never in
#: place of it. The runbook, the script and this test all name the same place.
HARDWARE_REPORT_DIR = ".agent_workspace/v1.0/hardware"
HARDWARE_REPORTS = ("usb-audio-probe-report.json", "roundtrip-latency-report.json")

#: The loopback evidence the hardware run must leave untouched.
LOOPBACK_EVIDENCE = (
    ".agent_workspace/v1.0/usb-audio-probe-report.json",
    ".agent_workspace/round3/roundtrip-latency-report.json",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC.is_file(), f"the runbook is missing: {DOC.relative_to(REPO_ROOT)}"
    return DOC.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def script_text() -> str:
    assert SCRIPT.is_file(), f"the runner is missing: {SCRIPT.relative_to(REPO_ROOT)}"
    return SCRIPT.read_text(encoding="utf-8")


# ------------------------------------------------------------------ the runbook


def test_runbook_walks_through_the_procedure(doc_text: str) -> None:
    """The steps the task promises have to actually be in the document."""
    # Load the kernel modules and verify each layer the probe reads.
    assert "snd-usb-audio" in doc_text or "snd_usb_audio" in doc_text
    assert "modprobe" in doc_text
    assert "/proc/asound/cards" in doc_text
    assert "/dev/snd" in doc_text
    # Set the default device and unmute it.
    assert "set-default-sink" in doc_text
    assert "set-default-source" in doc_text
    # Run both probes gated on physical hardware.
    assert doc_text.count("--require-physical") >= 2
    assert USB_PROBE in doc_text
    assert ROUNDTRIP_PROBE in doc_text
    # Republish the reports alongside the loopback evidence.
    assert HARDWARE_REPORT_DIR in doc_text
    for name in HARDWARE_REPORTS:
        assert f"{HARDWARE_REPORT_DIR}/{name}" in doc_text
    assert "alongside" in doc_text


def test_runbook_names_a_worked_example_interface(doc_text: str) -> None:
    """'Focusrite etc' means a concrete interface a reader can buy and follow."""
    assert "Focusrite" in doc_text
    assert "Scarlett" in doc_text
    # And the physical loop it needs, with the trap that silently corrupts the
    # measurement called out by name.
    assert "Direct Monitor" in doc_text


def test_runbook_keeps_the_loopback_evidence_in_place(doc_text: str) -> None:
    """Hardware evidence is published alongside the CI host's honest negative."""
    for path in LOOPBACK_EVIDENCE:
        assert path in doc_text, f"the runbook should name the loopback evidence at {path}"
        assert (REPO_ROOT / path).is_file(), f"the loopback evidence at {path} is gone"


def test_every_repository_path_the_runbook_links_to_exists(doc_text: str) -> None:
    """A runbook that links to files that do not exist has already rotted."""
    targets = re.findall(r"\]\(([^)]+?)(?:#[^)]*)?\)", doc_text)
    repo_targets = [target for target in targets if not target.startswith(("http", "mailto"))]
    assert repo_targets, "the runbook should link to the files it talks about"
    for target in repo_targets:
        resolved = (DOC.parent / target).resolve()
        assert resolved.exists(), f"the runbook links to {target}, which does not exist"


def test_runbook_and_script_reference_each_other(doc_text: str, script_text: str) -> None:
    assert "scripts/run-hardware-certification.sh" in doc_text
    assert "docs/HARDWARE_CERTIFICATION.md" in script_text


# ------------------------------------------------------------------- the runner


def test_runner_is_executable_and_fails_fast(script_text: str) -> None:
    mode = SCRIPT.stat().st_mode
    assert mode & stat.S_IXUSR, "the runner has to be executable"
    assert script_text.startswith("#!/usr/bin/env bash")
    assert "set -Eeuo pipefail" in script_text


def test_runner_runs_both_probes_with_the_physical_gate(script_text: str) -> None:
    assert USB_PROBE in script_text
    assert ROUNDTRIP_PROBE in script_text
    assert script_text.count("--require-physical") >= 2


def test_runner_publishes_where_the_runbook_says(script_text: str) -> None:
    """The script's default report directory is the one the runbook documents."""
    assert HARDWARE_REPORT_DIR in script_text
    for name in HARDWARE_REPORTS:
        assert name in script_text
    # And it must not write over the loopback evidence at the default paths.
    for path in LOOPBACK_EVIDENCE:
        assert path not in script_text, (
            f"the runner must not touch the loopback evidence at {path}"
        )


def test_runner_help_describes_the_procedure() -> None:
    completed = subprocess.run(
        [str(SCRIPT), "--help"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0
    assert USB_PROBE in completed.stdout
    assert ROUNDTRIP_PROBE in completed.stdout
    assert "--require-physical" in completed.stdout


def test_runner_rejects_arguments_it_does_not_understand() -> None:
    completed = subprocess.run(
        [str(SCRIPT), "--frobnicate"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 2
    assert "unknown argument" in completed.stderr


def test_runner_exits_honestly_when_there_is_no_hardware(tmp_path: Path) -> None:
    """On a host with no sound card the runner refuses, and shows its evidence.

    Exit code 1, the usb probe's honest ``not-certified`` inventory written to
    the report directory, and no round-trip report: nothing was measured, and
    the artifacts say so rather than staying quiet.
    """
    if probe.scan_kernel().cards:
        pytest.skip("this host has a sound card; the no-hardware path cannot be exercised")

    environment = dict(os.environ)
    environment["HARDWARE_REPORT_DIR"] = str(tmp_path)
    completed = subprocess.run(
        [str(SCRIPT)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=environment,
        timeout=300,
        check=False,
    )

    assert completed.returncode == 1
    assert "no physical audio device" in completed.stderr

    usb_report_path = tmp_path / "usb-audio-probe-report.json"
    assert usb_report_path.is_file(), "the honest negative inventory must still be published"
    report = json.loads(usb_report_path.read_text(encoding="utf-8"))
    assert report["status"] == "not-certified"
    assert report["physical_hardware_present"] is False
    assert report["certification"]["require_physical_requested"] is True

    assert not (tmp_path / "roundtrip-latency-report.json").exists(), (
        "nothing was measured, so no round-trip report may exist"
    )
