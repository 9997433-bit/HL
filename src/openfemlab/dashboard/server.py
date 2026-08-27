"""Threading HTTP server for the local results dashboard."""

from __future__ import annotations

import json
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

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

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/report":
            query = parse_qs(parsed.query)
            relative = query.get("path", [""])[0]
            if not relative:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "missing path query parameter"})
                return
            try:
                path = _resolve_under_root(self.root, relative)
                payload = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("report JSON must be an object")
                self._send_json(HTTPStatus.OK, payload)
            except FileNotFoundError:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": f"file not found: {relative}"})
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
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
    preset_file: str | None = None,
) -> None:
    """Start the dashboard until interrupted."""
    root_path = Path(root).resolve()
    handler_class = type(
        "BoundDashboardHandler",
        (_DashboardHandler,),
        {"root": root_path},
    )
    server = ThreadingHTTPServer((host, port), handler_class)
    url = f"http://{host}:{port}/"
    if preset_file:
        url += f"?file={preset_file}"

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
