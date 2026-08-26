"""Human-readable report rendering for correlation and correction artifacts."""

from .html import detect_report_kind, write_html_report

__all__ = ["detect_report_kind", "write_html_report"]
