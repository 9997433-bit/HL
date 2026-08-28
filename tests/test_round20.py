"""Tests for Round 20 desktop GUI shell."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from openfemlab.cli.main import main
from openfemlab.dashboard.jobs import JobManager, build_workflow_argv
from openfemlab.dashboard.server import serve_dashboard


def _start(root: Path, port: int) -> None:
    thread = threading.Thread(
        target=serve_dashboard,
        kwargs={"host": "127.0.0.1", "port": port, "root": root},
        daemon=True,
    )
    thread.start()
    for _ in range(50):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/desktop").close()
            return
        except OSError:
            threading.Event().wait(0.05)
    pytest.fail("desktop dashboard did not start")


def _get(port: int, path: str) -> dict:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}") as response:
        return json.loads(response.read().decode("utf-8"))


def _post(port: int, path: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def test_build_workflow_argv_modal():
    argv, outputs = build_workflow_argv("modal", {"model": "models/a.yaml"})
    assert argv[0] == "modal"
    assert "models/a.yaml" in argv
    assert outputs == ["reports/modes.json"]


def test_desktop_shell_serves_project_and_list(tmp_path: Path):
    assert main(["--no-color", "project", "init", str(tmp_path), "--name", "gui-demo"]) == 0
    port = 18771
    _start(tmp_path, port)

    project = _get(port, "/api/project")
    assert project["name"] == "gui-demo"
    assert project["has_project_file"] is True

    listing = _get(port, "/api/list?path=.")
    names = {entry["name"] for entry in listing["entries"]}
    assert {"models", "measurements", "reports"}.issubset(names)

    with urllib.request.urlopen(f"http://127.0.0.1:{port}/desktop.css") as response:
        assert response.status == 200


def test_desktop_run_quickstart_job(tmp_path: Path):
    assert main(["--no-color", "project", "init", str(tmp_path), "--name", "job-demo"]) == 0
    port = 18772
    _start(tmp_path, port)

    job = _post(port, "/api/run", {"workflow": "quickstart"})
    assert job["status"] == "running"

    for _ in range(120):
        status = _get(port, f"/api/job?id={job['id']}")
        if status["status"] != "running":
            break
        threading.Event().wait(0.1)
    else:
        pytest.fail("quickstart job did not finish")

    assert status["status"] == "success"
    assert any("quickstart" in line.lower() or "OpenFEMLab" in line for line in status["log"])


def test_job_manager_rejects_unknown_command(tmp_path: Path):
    manager = JobManager(tmp_path)
    with pytest.raises(ValueError, match="unsupported"):
        manager.start(["unknown-cmd"])


def test_serve_dashboard_desktop_path(monkeypatch, tmp_path: Path) -> None:
    opened: list[str] = []

    def fake_open(url: str, *, title: str = "OpenFEMLab") -> None:
        opened.append(url)

    monkeypatch.setattr("openfemlab.dashboard.desktop.open_desktop_window", fake_open)

    port = 18773
    serve_dashboard(host="127.0.0.1", port=port, root=tmp_path, desktop=True)

    assert opened == [f"http://127.0.0.1:{port}/desktop"]
