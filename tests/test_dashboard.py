"""Dashboard server and project scaffolding tests."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from openfemlab.cli.main import main
from openfemlab.core.model import Material, Section
from openfemlab.dashboard.geometry import geometry_payload
from openfemlab.dashboard.server import serve_dashboard
from openfemlab.mesh.simple import beam_mesh, hex_block_mesh

_SPEC = """\
name: cantilever
materials:
  steel: {E: 2.1e11, density: 7850.0, nu: 0.3}
sections:
  strip: {area: 1.0e-4, inertia_z: 8.333e-10}
mesh:
  type: beam
  length: 1.0
  num_elements: 4
  support: cantilever
  material: steel
  section: strip
"""


def _start(root: Path, port: int) -> None:
    thread = threading.Thread(
        target=serve_dashboard,
        kwargs={"host": "127.0.0.1", "port": port, "root": root},
        daemon=True,
    )
    thread.start()
    for _ in range(50):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/").close()
            return
        except OSError:
            threading.Event().wait(0.05)
    pytest.fail("dashboard did not start")


def _get(port: int, path: str) -> dict:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}") as response:
        return json.loads(response.read().decode("utf-8"))


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


def test_serve_rejects_a_missing_model_preset(tmp_path: Path):
    assert main(["--no-color", "serve", "--root", str(tmp_path), "--model", "nope.yaml"]) == 1


# ------------------------------------------------------------------- geometry


def test_geometry_payload_carries_the_wireframe_and_dof_layout():
    model = beam_mesh(
        1.0,
        4,
        Material(E=2.1e11, density=7850.0, name="steel"),
        Section(area=1.0e-4, inertia_z=8.333e-10, name="strip"),
    )
    payload = geometry_payload(model)

    assert len(payload["nodes"]) == 5
    assert payload["edges"] == [[0, 1], [1, 2], [2, 3], [3, 4]]
    assert payload["dofs"] == ["UX", "UY", "RZ"]
    assert payload["num_dofs"] == 15
    assert len(payload["dof_map"]["node_ids"]) == payload["num_dofs"]
    assert payload["dof_map"]["dof_types"][:3] == ["UX", "UY", "RZ"]
    assert payload["constrained_dofs"] == [0, 1, 2]
    assert payload["bounds"]["max"][0] == pytest.approx(1.0)


def test_geometry_payload_deduplicates_shared_solid_edges():
    """Two bricks sharing a face must not draw that face's edges twice."""
    model = hex_block_mesh(2.0, 1.0, 1.0, 2, 1, 1, Material(E=2.1e11, density=7850.0))
    payload = geometry_payload(model)

    edges = {tuple(sorted(edge)) for edge in payload["edges"]}
    assert len(edges) == len(payload["edges"])
    assert len(edges) == 20  # 12 per brick, 4 shared by the common face


def test_geometry_endpoint_serves_a_model_spec(tmp_path: Path):
    (tmp_path / "models").mkdir()
    (tmp_path / "models" / "cantilever.yaml").write_text(_SPEC, encoding="utf-8")
    port = 18767
    _start(tmp_path, port)

    payload = _get(port, "/api/geometry?path=models/cantilever.yaml")

    assert payload["name"] == "cantilever"
    assert payload["num_dofs"] == 15
    assert payload["edges"][0] == [0, 1]


def test_geometry_endpoint_reports_a_broken_spec(tmp_path: Path):
    (tmp_path / "broken.yaml").write_text("mesh: {type: nonsense}\n", encoding="utf-8")
    port = 18768
    _start(tmp_path, port)

    with pytest.raises(urllib.error.HTTPError) as excinfo:
        _get(port, "/api/geometry?path=broken.yaml")
    assert excinfo.value.code == 400
    assert "unknown mesh type" in json.loads(excinfo.value.read())["error"]

    with pytest.raises(urllib.error.HTTPError) as missing:
        _get(port, "/api/geometry?path=absent.yaml")
    assert missing.value.code == 404


def test_index_ships_the_three_js_viewer():
    port = 18769
    _start(Path("."), port)

    with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as response:
        page = response.read().decode("utf-8")

    assert "three.module.js" in page
    assert "/api/geometry" in page
    assert "viewer-canvas" in page


def test_desktop_available_reports_optional_dependency() -> None:
    from openfemlab.dashboard import desktop_available

    assert isinstance(desktop_available(), bool)


def test_serve_dashboard_desktop_path(monkeypatch, tmp_path: Path) -> None:
    opened: list[str] = []

    def fake_open(url: str, *, title: str = "OpenFEMLab") -> None:
        opened.append(url)

    monkeypatch.setattr("openfemlab.dashboard.desktop.open_desktop_window", fake_open)

    port = 18770
    serve_dashboard(host="127.0.0.1", port=port, root=tmp_path, desktop=True)

    assert opened == [f"http://127.0.0.1:{port}/"]


def test_open_desktop_window_raises_without_pywebview(monkeypatch) -> None:
    import builtins

    from openfemlab.dashboard.desktop import open_desktop_window
    from openfemlab.exceptions import OpenFEMLabError

    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "webview":
            raise ImportError("pywebview not installed")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(OpenFEMLabError, match="pywebview"):
        open_desktop_window("http://127.0.0.1:8765/")
