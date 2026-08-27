"""Threading HTTP server for the local results dashboard.

Two read-only endpoints back the static viewer:

``/api/report?path=...``
    Any JSON document under the project root — a correlation report, a
    correction report, or a native modal result carrying mode shapes.
``/api/geometry?path=...``
    The wireframe and DOF layout of a model spec (see
    :mod:`openfemlab.dashboard.geometry`), which is what turns a mode-shape
    vector into something the 3D viewer can displace.
"""

from __future__ import annotations

import json
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

from ..exceptions import OpenFEMLabError

__all__ = ["serve_dashboard"]

_INDEX_NAME = "index.html"


def _package_static(name: str) -> bytes:
    return resources.files("openfemlab.dashboard.static").joinpath(name).read_bytes()


def _resolve_under_root(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    root_resolved = root.resolve()
    if not str(candidate).startswith(str(root_resolved)):
        raise ValueError("path escapes the project root")
    if not candidate.is_file():
        raise FileNotFoundError(relative)
    return candidate


class _DashboardHandler(BaseHTTPRequestHandler):
    root: Path

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_document(self, relative: str, load) -> None:
        """Run ``load`` on a project-root-relative file and answer with its JSON."""
        if not relative:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "missing path query parameter"})
            return
        try:
            payload = load(_resolve_under_root(self.root, relative))
            if not isinstance(payload, dict):
                raise ValueError("the document must be a JSON object")
            self._send_json(HTTPStatus.OK, payload)
        except FileNotFoundError:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": f"file not found: {relative}"})
        except (OSError, ValueError, OpenFEMLabError, json.JSONDecodeError) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": f"{relative}: {exc}"})

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if parsed.path == "/api/report":
            self._serve_document(
                query.get("path", [""])[0],
                lambda path: json.loads(path.read_text(encoding="utf-8")),
            )
            return

        if parsed.path == "/api/geometry":
            from .geometry import geometry_from_spec

            self._serve_document(query.get("path", [""])[0], geometry_from_spec)
            return

        if parsed.path in ("/", "/index.html"):
            body = _package_static(_INDEX_NAME)
            self._send_bytes(HTTPStatus.OK, body, "text/html; charset=utf-8")
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})


def serve_dashboard(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    root: str | Path = ".",
    open_browser: bool = False,
    desktop: bool = False,
    preset_file: str | None = None,
    preset_model: str | None = None,
) -> None:
    """Start the dashboard until interrupted.

    ``preset_file`` and ``preset_model`` are project-root-relative paths the
    viewer opens on startup: a report JSON and the model spec whose geometry
    backs the 3D mode-shape view.
    """
    root_path = Path(root).resolve()
    handler_class = type(
        "BoundDashboardHandler",
        (_DashboardHandler,),
        {"root": root_path},
    )
    server = ThreadingHTTPServer((host, port), handler_class)
    query = urlencode(
        {
            key: value
            for key, value in (("file", preset_file), ("model", preset_model))
            if value
        }
    )
    url = f"http://{host}:{port}/" + (f"?{query}" if query else "")

    if desktop:
        from .desktop import open_desktop_window, run_dashboard_in_thread

        run_dashboard_in_thread(server)
        print(f"OpenFEMLab desktop dashboard at {url}")
        print(f"Project root: {root_path}")
        try:
            open_desktop_window(url)
        finally:
            server.shutdown()
            server.server_close()
        return

    if open_browser:
        import webbrowser

        threading.Timer(0.35, lambda: webbrowser.open(url)).start()

    print(f"OpenFEMLab dashboard at {url}")
    print(f"Project root: {root_path}")
    print("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
