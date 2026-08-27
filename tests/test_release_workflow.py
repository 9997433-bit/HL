"""Contract tests for the Linux release workflow."""

from pathlib import Path

import yaml

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[1] / ".github" / "workflows" / "release-linux.yml"
)


def _load_workflow() -> dict:
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def test_release_workflow_has_required_triggers_and_linux_job() -> None:
    workflow = _load_workflow()

    assert workflow["on"]["push"]["tags"] == ["v*"]
    assert "workflow_dispatch" in workflow["on"]
    assert workflow["jobs"]["build-linux"]["runs-on"] == "ubuntu-latest"


def test_linux_job_builds_and_uploads_the_bundle() -> None:
    steps = _load_workflow()["jobs"]["build-linux"]["steps"]

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
