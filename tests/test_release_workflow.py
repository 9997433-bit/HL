"""Contract tests for the macOS release bundle workflow and its build script.

The Linux and Windows equivalents of this file were folded into
tests/test_publish_release_workflow.py when the per-platform release workflows
became one tag-triggered publish workflow. What is left here is the part that
has no equivalent there: `.github/workflows/release-macos.yml`, which builds a
macOS bundle on demand, and `scripts/build-macos.sh`, which both that workflow
and the publish workflow use.

Two properties are worth pinning. The first is honesty about the artifact: its
name states an architecture, and the build has to be told to enforce that same
architecture, so a rename cannot quietly turn an arm64 bundle into a universal
one. The second is that the macOS build runs the licence gates the Linux build
runs, and that neither the script nor the workflow claims a notarisation this
project cannot perform.
"""

from __future__ import annotations

import platform
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
MACOS_WORKFLOW_PATH = WORKFLOW_DIR / "release-macos.yml"
PUBLISH_WORKFLOW_PATH = WORKFLOW_DIR / "publish-release.yml"
MACOS_BUILD_SCRIPT = REPO_ROOT / "scripts" / "build-macos.sh"

#: Tools that would attach or staple an Apple notarisation ticket. This
#: repository has no Apple ID and no Developer ID certificate, so invoking any
#: of them would be a claim it cannot back.
NOTARIZATION_COMMANDS = ("notarytool", "altool", "stapler")


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _macos_job(path: Path = MACOS_WORKFLOW_PATH) -> dict:
    return _load(path)["jobs"]["build-macos"]


def _commands(job: dict) -> str:
    return "\n".join(step.get("run", "") for step in job["steps"])


def _upload_step(job: dict) -> dict:
    return next(
        step for step in job["steps"] if step.get("uses", "").startswith("actions/upload-artifact@")
    )


# --------------------------------------------------------------------------
# release-macos.yml
# --------------------------------------------------------------------------


def test_macos_workflow_runs_on_apple_silicon_without_stealing_the_tag_trigger() -> None:
    workflow = _load(MACOS_WORKFLOW_PATH)
    triggers = workflow["on"]

    assert "workflow_dispatch" in triggers
    # publish-release.yml owns `v*`; a second tag-triggered build would produce
    # a second, differently named macOS artifact for the same release.
    assert "tags" not in triggers.get("push", {})
    assert "scripts/build-macos.sh" in triggers["pull_request"]["paths"]

    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["jobs"]["build-macos"]["runs-on"] == "macos-latest"


def test_macos_workflow_builds_through_the_gated_script() -> None:
    job = _macos_job()
    steps = job["steps"]

    assert any(step.get("uses", "").startswith("actions/checkout@") for step in steps)
    assert any(step.get("uses", "").startswith("actions/setup-python@") for step in steps)

    commands = _commands(job)
    assert 'python -m pip install "./audio-studio[installer]"' in commands
    assert "scripts/build-macos.sh --install-deps" in commands
    assert "python -m PyInstaller" not in commands, "the licence gates are being bypassed"
    assert _upload_step(job)["with"]["if-no-files-found"] == "error"


def test_macos_artifact_name_states_the_architecture_the_build_enforces() -> None:
    """Renaming the artifact without moving the gate has to break this test."""
    job = _macos_job()
    name = _upload_step(job)["with"]["name"]

    match = re.fullmatch(r"audio-studio-macos-(arm64|x86_64|universal)", name)
    assert match, f"the artifact name says nothing checkable about the architecture: {name}"

    claimed = match.group(1)
    enforced = "universal2" if claimed == "universal" else claimed
    assert f"--expect-arch {enforced}" in _commands(job), (
        f"the artifact is published as {claimed} but the build does not enforce {enforced}"
    )


def test_macos_artifact_is_a_tarball_so_the_bundle_survives_the_round_trip() -> None:
    """A zipped one-dir bundle loses its exec bits and framework symlinks."""
    job = _macos_job()
    upload = _upload_step(job)
    path = upload["with"]["path"]

    assert path == f"{upload['with']['name']}.tar.gz"
    assert f"tar -czf {path}" in _commands(job)


def test_macos_workflow_does_not_sign_or_claim_notarization() -> None:
    workflow = _load(MACOS_WORKFLOW_PATH)
    text = MACOS_WORKFLOW_PATH.read_text(encoding="utf-8")

    for command in NOTARIZATION_COMMANDS:
        assert command not in text, f"the workflow invokes or mentions {command} as if it could"

    # Unsigned by statement rather than by omission: a hosted runner has no
    # Developer ID keychain, and CODESIGN_IDENTITY is what would change that.
    assert workflow["env"]["CODESIGN_IDENTITY"] == ""
    assert "not notarised" in _commands(workflow["jobs"]["build-macos"])


def test_macos_workflow_says_the_sbom_is_not_generated() -> None:
    """The Linux generator is not run here, and silence would read as parity."""
    commands = _commands(_macos_job())
    assert "generate_sbom.py" in commands
    assert "without an SBOM" in commands


def test_published_macos_release_asset_is_built_and_named_the_same_way() -> None:
    """The tag path in publish-release.yml must not diverge from this one."""
    job = _macos_job(PUBLISH_WORKFLOW_PATH)
    commands = _commands(job)

    assert "scripts/build-macos.sh" in commands
    assert "--expect-arch arm64" in commands
    assert "--bundle macos-arm64" in commands, "the released zip hides its architecture"


# --------------------------------------------------------------------------
# scripts/build-macos.sh
# --------------------------------------------------------------------------


def run_build_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(MACOS_BUILD_SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=120,
        check=False,
    )


def test_macos_build_script_is_executable_and_fails_fast() -> None:
    assert MACOS_BUILD_SCRIPT.is_file()
    assert MACOS_BUILD_SCRIPT.stat().st_mode & stat.S_IXUSR, "the script is not executable"

    lines = MACOS_BUILD_SCRIPT.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "#!/usr/bin/env bash"
    assert "set -Eeuo pipefail" in lines


def test_macos_build_script_parses() -> None:
    result = subprocess.run(
        ["bash", "-n", str(MACOS_BUILD_SCRIPT)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_macos_build_script_shellcheck_is_clean() -> None:
    shellcheck = shutil.which("shellcheck")
    if shellcheck is None:
        pytest.skip("shellcheck is not installed")
    result = subprocess.run(
        [shellcheck, "--severity=warning", str(MACOS_BUILD_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_macos_build_script_avoids_bash_4_only_builtins() -> None:
    """/bin/bash on macOS is 3.2, where mapfile would fail at runtime."""
    text = MACOS_BUILD_SCRIPT.read_text(encoding="utf-8")
    assert not re.search(r"^\s*(mapfile|readarray)\b", text, flags=re.MULTILINE)


def test_macos_build_script_runs_the_same_licence_gates_as_linux() -> None:
    text = MACOS_BUILD_SCRIPT.read_text(encoding="utf-8")

    # The GPL refusal, with the same escape hatch and the same default.
    assert 'ALLOW_GPL="${ALLOW_GPL:-0}"' in text
    assert "pedalboard" in text
    # The notices have to be in the bundle, and the LGPL objects separate.
    assert "THIRD_PARTY_LICENSES.md" in text
    assert "LGPL-RELINKING.txt" in text
    assert "libQt6Core*.dylib" in text
    assert "QtCore.framework" in text
    assert "onefile" in text, "nothing refuses a flattened build"


def test_macos_build_script_makes_signing_optional_and_never_notarizes() -> None:
    text = MACOS_BUILD_SCRIPT.read_text(encoding="utf-8")

    assert 'CODESIGN_IDENTITY="${CODESIGN_IDENTITY:-}"' in text, "signing is not opt-in"
    pattern = re.compile(rf"^\s*(?:sudo\s+|xcrun\s+)?({'|'.join(NOTARIZATION_COMMANDS)})\b")
    offenders = [line for line in text.splitlines() if pattern.match(line)]
    assert not offenders, f"the script notarises: {offenders}"


def test_macos_build_script_help_exits_cleanly() -> None:
    result = run_build_script("--help")
    assert result.returncode == 0, result.stderr
    assert "Usage:" in result.stdout
    assert "--expect-arch" in result.stdout


def test_macos_build_script_rejects_an_unknown_option() -> None:
    result = run_build_script("--not-an-option")
    assert result.returncode == 2, result.stdout + result.stderr


def test_macos_build_script_rejects_an_unknown_architecture() -> None:
    result = run_build_script("--expect-arch", "ppc64")
    assert result.returncode != 0
    assert "ppc64" in result.stderr


def test_macos_build_script_refuses_to_run_off_macos() -> None:
    if platform.system() == "Darwin":
        pytest.skip("this host is macOS, so the refusal path is not exercised")

    result = run_build_script("--no-smoke")
    assert result.returncode != 0
    assert "must be built on macOS" in result.stderr
    assert "build-linux.sh" in result.stderr
