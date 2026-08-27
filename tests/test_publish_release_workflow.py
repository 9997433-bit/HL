"""Contract tests for the unified GitHub Release workflow."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
WORKFLOW_PATH = WORKFLOWS_DIR / "publish-release.yml"

EXPECTED_ASSETS = {
    "release-assets/audio-studio-linux.zip",
    "release-assets/audio-studio-windows.zip",
    "release-assets/audio-studio-macos.zip",
    "release-assets/audio-studio-sbom.json",
    "release-assets/SHA256SUMS",
}


def _load(path: Path = WORKFLOW_PATH) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _triggers(workflow: dict) -> dict:
    # PyYAML 1.1 interprets an unquoted `on` key as True. Accommodate other
    # workflows while keeping this workflow's key explicitly quoted.
    return workflow.get("on", workflow.get(True, {}))


def _commands(job: dict) -> str:
    return "\n".join(step.get("run", "") for step in job["steps"])


def test_publish_release_trigger_and_permissions() -> None:
    workflow = _load()

    assert _triggers(workflow) == {"push": {"tags": ["v*"]}}
    assert workflow["permissions"]["contents"] == "write"
    assert workflow["jobs"]["publish"]["permissions"]["contents"] == "write"


def test_workflow_builds_all_platforms_and_prepares_assets() -> None:
    jobs = _load()["jobs"]
    expected_runners = {
        "build-linux": "ubuntu-latest",
        "build-windows": "windows-latest",
        "build-macos": "macos-latest",
    }

    for job_name, runner in expected_runners.items():
        job = jobs[job_name]
        assert job["runs-on"] == runner
        assert job["permissions"]["contents"] == "read"
        assert any(
            step.get("uses", "").startswith("actions/checkout@") for step in job["steps"]
        )
        assert any(
            step.get("uses", "").startswith("actions/setup-python@")
            for step in job["steps"]
        )
        assert 'python -m pip install "./audio-studio[installer]"' in _commands(job)
        assert "scripts/prepare-release-assets.sh" in _commands(job)

    assert "scripts/build-linux.sh" in _commands(jobs["build-linux"])
    assert "tools/generate_sbom.py" in _commands(jobs["build-linux"])
    assert "scripts/build-windows.ps1" in _commands(jobs["build-windows"])
    assert "python -m PyInstaller" in _commands(jobs["build-macos"])

    artifact_names = {
        next(
            step
            for step in jobs[job_name]["steps"]
            if step.get("uses", "").startswith("actions/upload-artifact@")
        )["with"]["name"]
        for job_name in expected_runners
    }
    assert artifact_names == {"release-linux", "release-windows", "release-macos"}


def test_publish_job_downloads_builds_and_attaches_complete_asset_set() -> None:
    publish = _load()["jobs"]["publish"]

    assert set(publish["needs"]) == {"build-linux", "build-windows", "build-macos"}
    download = next(
        step
        for step in publish["steps"]
        if step.get("uses", "").startswith("actions/download-artifact@")
    )
    assert download["with"] == {
        "pattern": "release-*",
        "path": "release-assets",
        "merge-multiple": True,
    }
    assert "--checksums" in _commands(publish)

    release = next(
        step
        for step in publish["steps"]
        if step.get("uses", "").startswith("softprops/action-gh-release@")
    )
    assert set(release["with"]["files"].splitlines()) == EXPECTED_ASSETS


def test_publish_release_is_the_only_tag_triggered_release_workflow() -> None:
    tag_workflows = []
    for path in WORKFLOWS_DIR.glob("*.yml"):
        push = _triggers(_load(path)).get("push", {})
        if isinstance(push, dict) and push.get("tags"):
            tag_workflows.append(path.name)

    assert tag_workflows == ["publish-release.yml"]
