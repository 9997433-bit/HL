"""Contract tests for the Linux and Windows release workflows."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
LINUX_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "release-linux.yml"
WINDOWS_WORKFLOW_PATH = (
    REPO_ROOT / ".github" / "workflows" / "release-windows.yml"
)


def _load_workflow(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_release_workflow_has_required_triggers_and_linux_job() -> None:
    workflow = _load_workflow(LINUX_WORKFLOW_PATH)

    assert workflow["on"]["push"]["tags"] == ["v*"]
    assert "workflow_dispatch" in workflow["on"]
    assert workflow["jobs"]["build-linux"]["runs-on"] == "ubuntu-latest"


def test_linux_job_builds_and_uploads_the_bundle() -> None:
    steps = _load_workflow(LINUX_WORKFLOW_PATH)["jobs"]["build-linux"]["steps"]

    assert any(step.get("uses", "").startswith("actions/checkout@") for step in steps)
    assert any(step.get("uses", "").startswith("actions/setup-python@") for step in steps)

    commands = "\n".join(step.get("run", "") for step in steps)
    assert 'python -m pip install "./audio-studio[installer]"' in commands
    assert "scripts/build-linux.sh --install-deps --no-smoke" in commands
    assert "tools/generate_sbom.py" in commands

    upload = next(
        step for step in steps if step.get("uses", "").startswith("actions/upload-artifact@")
    )
    assert upload["with"]["name"] == "audio-studio-linux-x64"
    assert upload["with"]["path"] == "dist/audio-studio/"


def test_windows_release_workflow_has_required_triggers_and_job() -> None:
    workflow = _load_workflow(WINDOWS_WORKFLOW_PATH)

    assert workflow["on"]["push"]["tags"] == ["v*"]
    assert "workflow_dispatch" in workflow["on"]
    assert workflow["permissions"]["contents"] == "read"
    assert workflow["jobs"]["build-windows"]["runs-on"] == "windows-latest"


def test_windows_job_builds_and_uploads_the_bundle() -> None:
    steps = _load_workflow(WINDOWS_WORKFLOW_PATH)["jobs"]["build-windows"]["steps"]

    assert any(step.get("uses", "").startswith("actions/checkout@") for step in steps)
    assert any(step.get("uses", "").startswith("actions/setup-python@") for step in steps)

    commands = "\n".join(step.get("run", "") for step in steps)
    assert 'python -m pip install "./audio-studio[installer]"' in commands
    assert "./scripts/build-windows.ps1 -InstallDeps" in commands

    build = next(step for step in steps if "build-windows.ps1" in step.get("run", ""))
    assert build["shell"] == "pwsh"

    upload = next(
        step for step in steps if step.get("uses", "").startswith("actions/upload-artifact@")
    )
    assert upload["with"]["name"] == "audio-studio-windows-x64"
    assert upload["with"]["path"] == "dist/audio-studio/"
    assert upload["with"]["if-no-files-found"] == "error"
