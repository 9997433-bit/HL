"""Optional native window wrapper around the local dashboard."""

from __future__ import annotations

import threading

from ..exceptions import OpenFEMLabError

__all__ = ["open_desktop_window", "desktop_available"]


def desktop_available() -> bool:
    """Return whether the optional ``pywebview`` dependency is importable."""
    try:
        import webview  # noqa: F401
    except ImportError:
        return False
    return True


def open_desktop_window(url: str, *, title: str = "OpenFEMLab") -> None:
    """Open the dashboard URL in a native window via ``pywebview``."""
    try:
        import webview
    except ImportError as exc:
        raise OpenFEMLabError(
            "the desktop viewer requires pywebview; install with "
            "'pip install pywebview' or omit --desktop"
        ) from exc

    webview.create_window(title, url)
    webview.start()


def run_dashboard_in_thread(server) -> threading.Thread:
    """Serve ``server`` on a daemon thread until the desktop window closes."""
    thread = threading.Thread(target=server.serve_forever, name="openfemlab-dashboard", daemon=True)
    thread.start()
    return thread
