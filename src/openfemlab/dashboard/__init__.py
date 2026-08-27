"""Local Web dashboard for correlation and correction artifacts."""

from .desktop import desktop_available, open_desktop_window
from .server import serve_dashboard

__all__ = ["serve_dashboard", "desktop_available", "open_desktop_window"]
