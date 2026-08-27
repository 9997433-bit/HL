"""Dashboard server and project scaffolding tests."""

from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path

import pytest

from openfemlab.cli.main import main
from openfemlab.dashboard.server import serve_dashboard


def test_project_init_creates_workspace(tmp_path: Path):
    assert main(["--no-color", "project", "init", str(tmp_path), "--name", "demo"]) == 0
    assert (tmp_path / "project.yaml").is_file()
    assert (tmp_path / "models").is_dir()
    assert (tmp_path / "measurements").is_dir()
    assert (tmp_path / "reports").is_dir()
    assert (tmp_path / "models" / "cantilever.yaml").is_file()


def test_dashboard_serves_index_and_report(tmp_path: Path):
    payload = {
        "schema_version": "1.1",
        "summary": {"mean_mac": 0.9, "min_mac": 0.85, "num_pairs": 1},
        "pairs": [],
        "mac_matrix": [[1.0, 0.2], [0.3, 0.95]],
    }
    report_path = tmp_path / "reports" / "corr.json"
    report_path.parent.mkdir(parents=True)
    report_path.write_text(json.dumps(payload), encoding="utf-8")

    port = 18765
    thread = threading.Thread(
        target=serve_dashboard,
        kwargs={"host": "127.0.0.1", "port": port, "root": tmp_path},
        daemon=True,
    )
    thread.start()

    for _ in range(50):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as response:
                html = response.read().decode("utf-8")
            break
        except OSError:
            threading.Event().wait(0.05)
    else:
        pytest.fail("dashboard did not start")

    assert "OpenFEMLab" in html

    with urllib.request.urlopen(
        f"http://127.0.0.1:{port}/api/report?path=reports/corr.json"
    ) as response:
        body = json.loads(response.read().decode("utf-8"))
    assert body["summary"]["min_mac"] == 0.85


def test_serve_invokes_dashboard(monkeypatch: pytest.MonkeyPatch):
    called: dict[str, object] = {}

    def fake_serve(**kwargs):
        called.update(kwargs)

    monkeypatch.setattr("openfemlab.cli.commands.serve.serve_dashboard", fake_serve)
    assert main(["--no-color", "serve", "--port", "9999", "--root", "/tmp"]) == 0
    assert called["port"] == 9999
    assert Path(called["root"]) == Path("/tmp")
