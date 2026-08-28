"""Threading HTTP server for the local results dashboard."""

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
from .geometry import geometry_from_spec
from .jobs import JobManager, build_workflow_argv
from .project_api import list_directory, project_info, read_json_under_root, resolve_under_root

__all__ = ["serve_dashboard"]

_INDEX_NAME = "index.html"
_DESKTOP_NAME = "desktop.html"
_STATIC_FILES = frozenset(
    {"index.html", "desktop.html", "desktop.css", "desktop.js", "viewer-frame.js"}
)


def _package_static(name: str) -> bytes:
    return resources.files("openfemlab.dashboard.static").joinpath(name).read_bytes()


class _DashboardHandler(BaseHTTPRequestHandler):
    root: Path
    jobs: JobManager
    desktop_mode: bool

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

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            raise ValueError("request body is empty")
        raw = self.rfile.read(length)
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return payload

    def _serve_report(self, relative: str) -> None:
        if not relative:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "missing path query parameter"})
            return
        try:
            payload = read_json_under_root(self.root, relative)
            self._send_json(HTTPStatus.OK, payload)
        except FileNotFoundError:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": f"file not found: {relative}"})
        except (OSError, ValueError, OpenFEMLabError, json.JSONDecodeError) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": f"{relative}: {exc}"})

    def _serve_geometry(self, relative: str) -> None:
        if not relative:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "missing path query parameter"})
            return
        try:
            payload = geometry_from_spec(resolve_under_root(self.root, relative))
            self._send_json(HTTPStatus.OK, payload)
        except FileNotFoundError:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": f"file not found: {relative}"})
        except (OSError, ValueError, OpenFEMLabError, json.JSONDecodeError) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": f"{relative}: {exc}"})

    def _serve_static(self, name: str, content_type: str) -> None:
        if name not in _STATIC_FILES:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        body = _package_static(name)
        self._send_bytes(HTTPStatus.OK, body, content_type)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if parsed.path == "/api/report":
            self._serve_report(query.get("path", [""])[0])
            return

        if parsed.path == "/api/geometry":
            self._serve_geometry(query.get("path", [""])[0])
            return

        if parsed.path == "/api/list":
            relative = query.get("path", ["."])[0]
            try:
                payload = list_directory(self.root, relative)
                self._send_json(HTTPStatus.OK, payload)
            except FileNotFoundError:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": f"directory not found: {relative}"})
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if parsed.path == "/api/project":
            self._send_json(HTTPStatus.OK, project_info(self.root))
            return

        if parsed.path == "/api/jobs":
            limit = int(query.get("limit", ["20"])[0])
            self._send_json(HTTPStatus.OK, {"jobs": self.jobs.list_jobs(limit=limit)})
            return

        if parsed.path == "/api/job":
            job_id = query.get("id", [""])[0]
            job = self.jobs.get(job_id)
            if job is None:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": f"unknown job {job_id!r}"})
                return
            self._send_json(HTTPStatus.OK, job.to_dict())
            return

        if parsed.path in ("/desktop", "/desktop.html"):
            body = _package_static(_DESKTOP_NAME)
            self._send_bytes(HTTPStatus.OK, body, "text/html; charset=utf-8")
            return

        if parsed.path == "/desktop.css":
            self._serve_static("desktop.css", "text/css; charset=utf-8")
            return

        if parsed.path == "/desktop.js":
            self._serve_static("desktop.js", "application/javascript; charset=utf-8")
            return

        if parsed.path in ("/", "/index.html"):
            if self.desktop_mode and parsed.path == "/":
                body = _package_static(_DESKTOP_NAME)
                self._send_bytes(HTTPStatus.OK, body, "text/html; charset=utf-8")
                return
            body = _package_static(_INDEX_NAME)
            self._send_bytes(HTTPStatus.OK, body, "text/html; charset=utf-8")
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/api/run":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        try:
            payload = self._read_json_body()
        except (ValueError, json.JSONDecodeError) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        try:
            if "workflow" in payload:
                argv, outputs = build_workflow_argv(str(payload["workflow"]), payload)
            else:
                argv = [str(item) for item in payload.get("argv") or []]
                outputs = [str(item) for item in payload.get("outputs") or []]
            job = self.jobs.start(argv, outputs=outputs)
            self._send_json(HTTPStatus.ACCEPTED, job.to_dict())
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})


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
    """Start the dashboard until interrupted."""
    root_path = Path(root).resolve()
    jobs = JobManager(root_path)
    handler_class = type(
        "BoundDashboardHandler",
        (_DashboardHandler,),
        {"root": root_path, "jobs": jobs, "desktop_mode": desktop},
    )
    server = ThreadingHTTPServer((host, port), handler_class)
    query = urlencode(
        {
            key: value
            for key, value in (("file", preset_file), ("model", preset_model))
            if value
        }
    )
    base_path = "/desktop" if desktop else "/"
    url = f"http://{host}:{port}{base_path}" + (f"?{query}" if query else "")

    if desktop:
        from .desktop import open_desktop_window, run_dashboard_in_thread

        run_dashboard_in_thread(server)
        print(f"OpenFEMLab desktop at {url}")
        print(f"Project root: {root_path}")
        try:
            open_desktop_window(url, title=f"OpenFEMLab — {root_path.name}")
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
