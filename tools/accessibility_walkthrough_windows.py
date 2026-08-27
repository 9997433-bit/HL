#!/usr/bin/env python3
"""Live Windows/NVDA accessibility walkthrough harness.

This harness requires Windows + NVDA.  It cannot certify NVDA from Linux,
Wine, Qt's offscreen backend, or a UI Automation tree alone.

Prerequisites on an interactive Windows desktop:

1. Install the project and ``pywinauto`` into the selected Python environment.
2. Start NVDA and enable NVDA Speech Viewer (NVDA+N, Tools, Speech Viewer).
3. Clear any private text from Speech Viewer; this harness clears it again.
4. Run ``py tools/accessibility_walkthrough_windows.py`` from the repository.

The harness launches the real application with null audio, uses pywinauto's
UIA backend to verify the D4 control inventory, moves keyboard focus through
named focusable controls, and reads only the new text displayed by NVDA Speech
Viewer.  A pass requires every walked name to appear in that live transcript.
Missing host, NVDA, pywinauto, or Speech Viewer prerequisites produce an honest
``not-run`` report and exit code 2.

Output follows ``REPORT_SCHEMA`` from ``tools.accessibility_report_schema`` and
defaults to ``.agent_workspace/v1.0/accessibility-report-windows.json``.  It is
a host result for later review/merge; it never overwrites the committed Linux
artifact automatically.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
AUDIO_STUDIO_ROOT = REPOSITORY_ROOT / "audio-studio"
OUTPUT_PATH = (
    REPOSITORY_ROOT / ".agent_workspace/v1.0/accessibility-report-windows.json"
)

for import_root in (REPOSITORY_ROOT, AUDIO_STUDIO_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from tools.accessibility_report_schema import (
    PLATFORM_SCHEMA,
    REPORT_SCHEMA,
    build_platform_report,
    write_report,
)
from tools.screen_reader_probe import CONTROL_INVENTORY

__all__ = ["PLATFORM_SCHEMA", "REPORT_SCHEMA", "build_gated_report", "main"]

GENERATED_BY = "tools/accessibility_walkthrough_windows.py"
METHODOLOGY = (
    "On an interactive Windows desktop with NVDA already running, launch the real "
    "Audio Studio window with null audio. Inspect its Microsoft UI Automation tree "
    "through pywinauto's UIA backend, require every D4 inventory name, clear NVDA "
    "Speech Viewer, move UIA keyboard focus through named focusable controls, and "
    "require the resulting live NVDA transcript to contain every walked name."
)
LIMITATIONS = (
    "Requires Windows + NVDA on an interactive desktop and pywinauto. Speech "
    "verification observes text emitted by NVDA Speech Viewer, not physical audio "
    "hardware. UIA inspection alone is never counted as a screen-reader pass. Orca "
    "and VoiceOver are outside this host run and remain not-run."
)


def _environment() -> dict[str, Any]:
    return {
        "platform": sys.platform,
        "windows_version": platform.platform(),
        "python": platform.python_version(),
        "uia_client": "pywinauto" if importlib.util.find_spec("pywinauto") else None,
        "desktop_required": "interactive (not a service/session-0 runner)",
    }


def build_gated_report(errors: list[str]) -> dict[str, Any]:
    """Create a schema-valid not-run report for missing prerequisites."""
    reason = "; ".join(errors) or "Windows/NVDA prerequisites were not evaluated"
    return build_platform_report(
        generated_by=GENERATED_BY,
        target_platform="windows",
        status="not-run",
        session=None,
        reason=reason,
        methodology=METHODOLOGY,
        environment=_environment(),
        checks={
            "windows_host": sys.platform == "win32",
            "pywinauto_available": importlib.util.find_spec("pywinauto") is not None,
            "nvda_process_running": False,
            "nvda_speech_viewer_available": False,
        },
        limitations=LIMITATIONS,
    )


def _powershell(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _nvda_running() -> bool:
    result = _powershell(
        "$p = Get-Process -Name nvda -ErrorAction SilentlyContinue; "
        "if ($null -ne $p) { 'running' }"
    )
    return result.returncode == 0 and "running" in result.stdout


def _nvda_version() -> str:
    result = _powershell(
        "$p = Get-Process -Name nvda -ErrorAction SilentlyContinue | "
        "Select-Object -First 1; if ($null -ne $p) { "
        "(Get-Item $p.Path).VersionInfo.ProductVersion }"
    )
    version = result.stdout.strip()
    return version or "unknown"


def _find_speech_viewer() -> Any | None:
    from pywinauto import Desktop

    candidates = Desktop(backend="uia").windows(title_re=r".*Speech Viewer.*")
    return candidates[0] if candidates else None


def prerequisite_errors() -> list[str]:
    """Return gates that prevent this run from being live NVDA evidence."""
    if sys.platform != "win32":
        return ["requires Windows + NVDA; current host is not Windows"]
    if importlib.util.find_spec("pywinauto") is None:
        return ["pywinauto is not installed (`py -m pip install pywinauto`)"]
    if not _nvda_running():
        return ["NVDA is not running"]
    if _find_speech_viewer() is None:
        return ["NVDA Speech Viewer is not open"]
    return []


def _uia_name(control: Any) -> str:
    try:
        return str(control.element_info.name or "").strip()
    except (AttributeError, RuntimeError):
        return ""


def _is_keyboard_focusable(control: Any) -> bool:
    try:
        return bool(control.is_keyboard_focusable())
    except (AttributeError, RuntimeError):
        try:
            return bool(control.element_info.element.CurrentIsKeyboardFocusable)
        except (AttributeError, RuntimeError):
            return False


def _speech_text(viewer: Any) -> str:
    """Read visible Speech Viewer UIA text without using NVDA internals."""
    values: list[str] = []
    seen: set[str] = set()
    for control in [viewer, *viewer.descendants()]:
        try:
            text = str(control.window_text() or "").strip()
        except (AttributeError, RuntimeError):
            continue
        if text and text not in seen and text != "Speech Viewer":
            seen.add(text)
            values.append(text)
    return "\n".join(values)


def _clear_speech_viewer(viewer: Any) -> None:
    from pywinauto.keyboard import send_keys

    viewer.set_focus()
    send_keys("^a{DELETE}", pause=0.05)
    time.sleep(0.5)


def _wcag_evidence() -> dict[str, Any]:
    # Reuse the same live-palette audit as the canonical Linux walkthrough.
    from tools.accessibility_walkthrough import _wcag_evidence as measure

    return measure()


def run_walkthrough(startup_timeout: int, focus_delay: float) -> dict[str, Any]:
    """Run the live UIA/focus/Speech Viewer path after all gates passed."""
    from pywinauto import Application

    viewer = _find_speech_viewer()
    if viewer is None:
        raise RuntimeError("NVDA Speech Viewer disappeared after prerequisite checks")

    app_environment = dict(os.environ)
    inherited_pythonpath = app_environment.get("PYTHONPATH", "")
    roots = [str(AUDIO_STUDIO_ROOT), str(REPOSITORY_ROOT)]
    if inherited_pythonpath:
        roots.append(inherited_pythonpath)
    app_environment["PYTHONPATH"] = os.pathsep.join(roots)

    process = subprocess.Popen(
        [sys.executable, "-m", "audio_studio", "--null-audio"],
        cwd=REPOSITORY_ROOT,
        env=app_environment,
    )
    try:
        application = Application(backend="uia").connect(
            process=process.pid, timeout=startup_timeout
        )
        window = application.top_window()
        window.wait("visible enabled ready", timeout=startup_timeout)

        descendants = window.descendants()
        named_controls: dict[str, Any] = {}
        uia_nodes: list[dict[str, str]] = []
        for control in descendants:
            name = _uia_name(control)
            if not name:
                continue
            named_controls.setdefault(name, control)
            control_type = str(getattr(control.element_info, "control_type", "unknown"))
            uia_nodes.append({"name": name, "control_type": control_type})

        expected_names = list(CONTROL_INVENTORY.values())
        missing_inventory = [
            expected_name
            for expected_name in expected_names
            if expected_name not in named_controls
        ]

        focus_targets: list[tuple[str, Any]] = []
        for name, control in named_controls.items():
            if _is_keyboard_focusable(control):
                focus_targets.append((name, control))
            if len(focus_targets) >= 20:
                break

        _clear_speech_viewer(viewer)
        focused: list[str] = []
        focus_errors: list[str] = []
        for name, control in focus_targets:
            try:
                control.set_focus()
                focused.append(name)
                time.sleep(focus_delay)
            except (AttributeError, RuntimeError) as exc:
                focus_errors.append(f"{name}: {exc}")
        time.sleep(1.0)
        transcript = _speech_text(viewer)
        unspoken = [name for name in focused if name.casefold() not in transcript.casefold()]

        wcag = _wcag_evidence()
        checks = {
            "uia_publishes_every_inventory_name": not missing_inventory,
            "named_focusable_controls_found": bool(focus_targets),
            "uia_focus_walk_completed": bool(focused) and not focus_errors,
            "nvda_speech_viewer_output_captured": bool(transcript),
            "nvda_spoke_every_focused_control": bool(focused) and not unspoken,
            "wcag_contrast_audit_passes": wcag["contrast_pass"] is True,
            "color_safe_colormap_available": wcag["color_safe_colormap"] is True,
        }
        passed = all(checks.values())
        reason = "" if passed else "one or more NVDA/UIA walkthrough checks failed"
        return build_platform_report(
            generated_by=GENERATED_BY,
            target_platform="windows",
            status="pass" if passed else "fail",
            session="live",
            reason=reason,
            methodology=METHODOLOGY,
            environment=_environment(),
            checks=checks,
            limitations=LIMITATIONS,
            screen_reader_version=_nvda_version(),
            wcag_evidence=wcag,
            evidence={
                "uia_nodes": len(uia_nodes),
                "inventory": [
                    {
                        "control": control_path,
                        "expected_name": expected_name,
                        "published_on_uia": expected_name in named_controls,
                    }
                    for control_path, expected_name in CONTROL_INVENTORY.items()
                ],
                "focusable_controls": [name for name, _control in focus_targets],
                "focus_events_requested": len(focus_targets),
                "focus_events_completed": len(focused),
                "focus_errors": focus_errors,
                "nvda_speech_characters_captured": len(transcript),
                "nvda_speech_transcript": transcript,
                "unspoken_controls": unspoken,
            },
        )
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--startup-timeout", type=int, default=45)
    parser.add_argument("--focus-delay", type=float, default=0.8)
    args = parser.parse_args()

    errors = prerequisite_errors()
    if errors:
        report = build_gated_report(errors)
        write_report(report, args.output)
        print(f"not-run: {'; '.join(errors)}")
        print(f"wrote {args.output}")
        return 2

    try:
        report = run_walkthrough(args.startup_timeout, args.focus_delay)
    # A harness must preserve unexpected UIA failures in its output artifact;
    # otherwise automation errors can be mistaken for an absent run.
    except Exception as exc:  # noqa: BLE001
        report = build_platform_report(
            generated_by=GENERATED_BY,
            target_platform="windows",
            status="fail",
            session="live",
            reason=f"walkthrough raised {type(exc).__name__}: {exc}",
            methodology=METHODOLOGY,
            environment=_environment(),
            checks={"walkthrough_completed_without_exception": False},
            limitations=LIMITATIONS,
            screen_reader_version=_nvda_version(),
            evidence={"exception_type": type(exc).__name__, "exception": str(exc)},
        )
    write_report(report, args.output)
    print(f"wrote {args.output} (status: {report['status']})")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
