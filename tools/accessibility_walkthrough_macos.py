#!/usr/bin/env python3
"""Gated macOS/VoiceOver accessibility walkthrough roadmap.

This stub requires macOS + VoiceOver.  It deliberately cannot pass D4 yet.
VoiceOver has no supported machine-readable speech transcript API comparable
to NVDA Speech Viewer or Orca debug output, so an AX tree walk by itself would
not prove that VoiceOver announced the focused controls.

Run on an interactive macOS desktop with VoiceOver enabled:

    python3 tools/accessibility_walkthrough_macos.py

The gate checks the Darwin host, a running VoiceOver process, and macOS
Accessibility permission via ``AXIsProcessTrusted``.  It then writes an honest
``not-run`` report whose roadmap names the AX APIs the completed driver must
use.  A future live harness must:

1. launch Audio Studio with null audio and retain its PID;
2. call ``AXUIElementCreateApplication`` and recursively read
   ``kAXChildrenAttribute``, names, roles, values, and focusability;
3. focus each named control through ``kAXFocusedAttribute``;
4. collect contemporaneous VoiceOver utterances through a documented
   operator protocol or a supported Apple API if one becomes available; and
5. mark pass only when every focus target is present in that evidence.

Output follows ``REPORT_SCHEMA`` from ``tools.accessibility_report_schema`` and
defaults to ``.agent_workspace/v1.0/accessibility-report-macos.json``.  It never
overwrites the committed Linux/Orca artifact.
"""

from __future__ import annotations

import argparse
import ctypes
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPOSITORY_ROOT / ".agent_workspace/v1.0/accessibility-report-macos.json"
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from tools.accessibility_report_schema import (
    PLATFORM_SCHEMA,
    REPORT_SCHEMA,
    build_platform_report,
    write_report,
)

__all__ = ["PLATFORM_SCHEMA", "REPORT_SCHEMA", "build_gated_report", "main"]

GENERATED_BY = "tools/accessibility_walkthrough_macos.py"
AX_API_ROADMAP = [
    "AXIsProcessTrusted",
    "AXUIElementCreateApplication",
    "AXUIElementCopyAttributeValue(kAXChildrenAttribute)",
    "AXUIElementCopyAttributeValue(kAXTitleAttribute/kAXRoleAttribute/kAXValueAttribute)",
    "AXUIElementSetAttributeValue(kAXFocusedAttribute)",
    "operator-confirmed VoiceOver utterance capture until Apple exposes a supported API",
]
METHODOLOGY = (
    "Gate execution to an interactive macOS host, require a running VoiceOver "
    "process, and query AXIsProcessTrusted. The planned driver will walk the real "
    "application through AXUIElement APIs and move accessibility focus. This stub "
    "does not perform or claim the walk because there is no implemented, supported "
    "VoiceOver utterance capture path."
)
LIMITATIONS = (
    "Requires macOS + VoiceOver and user-granted Accessibility permission. This is "
    "a roadmap stub, not a live screen-reader test: AX inspection alone cannot prove "
    "VoiceOver speech, and VoiceOver exposes no supported transcript API. The report "
    "therefore remains not-run even when host gates pass. NVDA and Orca are outside "
    "this host run."
)


def _voiceover_running() -> bool:
    result = subprocess.run(
        ["pgrep", "-x", "VoiceOver"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    return result.returncode == 0 and bool(result.stdout.strip())


def _ax_is_process_trusted() -> bool:
    framework = ctypes.CDLL(
        "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
    )
    function = framework.AXIsProcessTrusted
    function.argtypes = []
    function.restype = ctypes.c_bool
    return bool(function())


def _voiceover_version() -> str:
    result = subprocess.run(
        [
            "defaults",
            "read",
            "/System/Library/CoreServices/VoiceOver.app/Contents/Info",
            "CFBundleShortVersionString",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    return result.stdout.strip() or "unknown"


def prerequisite_errors() -> list[str]:
    """Return gates that prevent an eventual AX/VoiceOver walkthrough."""
    if sys.platform != "darwin":
        return ["requires macOS + VoiceOver; current host is not macOS"]
    if not _voiceover_running():
        return ["VoiceOver is not running (toggle it with Command-F5)"]
    try:
        trusted = _ax_is_process_trusted()
    except OSError as exc:
        return [f"could not load the macOS Accessibility framework: {exc}"]
    if not trusted:
        return [
            "Accessibility permission is not granted to this terminal/Python process"
        ]
    return []


def _environment() -> dict[str, Any]:
    return {
        "platform": sys.platform,
        "macos_version": platform.mac_ver()[0] or None,
        "python": platform.python_version(),
        "desktop_required": "interactive user session",
        "ax_permission_required": True,
    }


def build_gated_report(errors: list[str]) -> dict[str, Any]:
    """Create the schema-valid report; this stub always remains not-run."""
    host_is_macos = sys.platform == "darwin"
    voiceover_running = host_is_macos and _voiceover_running()
    ax_trusted = False
    if voiceover_running:
        try:
            ax_trusted = _ax_is_process_trusted()
        except OSError:
            pass

    reason = "; ".join(errors)
    if not reason:
        reason = (
            "host gates passed, but AX focus driving and supported VoiceOver "
            "utterance capture are not implemented"
        )
    return build_platform_report(
        generated_by=GENERATED_BY,
        target_platform="macos",
        status="not-run",
        session=None,
        reason=reason,
        methodology=METHODOLOGY,
        environment={**_environment(), "ax_api_roadmap": AX_API_ROADMAP},
        checks={
            "macos_host": host_is_macos,
            "voiceover_process_running": voiceover_running,
            "ax_permission_granted": ax_trusted,
            "ax_focus_driver_implemented": False,
            "voiceover_utterances_captured": False,
        },
        limitations=LIMITATIONS,
        screen_reader_version=_voiceover_version() if voiceover_running else None,
        evidence={
            "kind": "roadmap-only",
            "ax_api_roadmap": AX_API_ROADMAP,
            "live_screen_reader_session": False,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()

    errors = prerequisite_errors()
    report = build_gated_report(errors)
    write_report(report, args.output)
    print(f"not-run: {report['platforms'][2]['reason']}")
    print(f"wrote {args.output}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
