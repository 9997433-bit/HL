#!/usr/bin/env python3
"""Headless screen-reader-readiness evidence for checklist D4.

Builds the real :class:`MainWindow` on Qt's ``offscreen`` platform and
introspects it with ``QAccessible.queryAccessibleInterface`` — the same
name/role tree the platform accessibility bridges (UIA on Windows,
NSAccessibility on macOS, AT-SPI on Linux) hand to NVDA, VoiceOver and Orca.

This is an honest proxy, not a certification.  It proves the application
publishes worded accessible names and sensible roles for its controls; it
does not prove a live screen reader announced them.  The report therefore
records ``evidence: headless-proxy``, ``live_screen_reader_session: false``
and ``screen_reader_platforms_passed: 0``.

Writes ``.agent_workspace/v1.0/screen-reader-evidence.json``.  Run from the
repository root::

    python tools/screen_reader_probe.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
AUDIO_STUDIO_ROOT = REPOSITORY_ROOT / "audio-studio"
if str(AUDIO_STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(AUDIO_STUDIO_ROOT))

OUTPUT_PATH = REPOSITORY_ROOT / ".agent_workspace/v1.0/screen-reader-evidence.json"

#: Application controls a screen-reader user needs to identify by name. Keys
#: are attribute paths under the window; values are the announced name.
CONTROL_INVENTORY: dict[str, str] = {
    "transport_bar": "Transport controls",
    "transport_bar.record_button": "Record",
    "transport_bar.play_button": "Play or pause",
    "transport_bar.stop_button": "Stop",
    "transport_bar.start_button": "Go to start",
    "transport_bar.end_button": "Go to end",
    "transport_bar.loop_button": "Loop playback",
    "transport_bar.volume_slider": "Output gain",
    "transport_bar.position_label": "Playback position",
    "level_meter": "Output level meter",
    "track_panel": "Waveform editor",
    "track_panel.waveform": "Waveform display",
    "multitrack_view": "Multitrack arranger",
    "spectrum_panel": "Spectral frequency display",
    "effect_rack": "Effects rack",
    "plugin_panel": "VST3 plugins",
    "marker_panel": "Markers",
    "marker_panel.tree": "Marker and region list",
}


def _resolve(window: Any, path: str) -> Any:
    widget = window
    for attribute in path.split("."):
        widget = getattr(widget, attribute)
    return widget


def _walk(interface: Any) -> tuple[int, int]:
    """(nodes visited, nodes with a non-empty name) below ``interface``."""
    from PySide6.QtGui import QAccessible

    visited = named = 0
    stack = [interface]
    while stack:
        node = stack.pop()
        if node is None or not node.isValid():
            continue
        visited += 1
        if node.text(QAccessible.Text.Name):
            named += 1
        for index in range(node.childCount()):
            stack.append(node.child(index))
    return visited, named


def probe() -> dict[str, Any]:
    from audio_studio.core.engine import AudioEngine
    from audio_studio.core.output import NullOutput
    from audio_studio.ui.main_window import MainWindow
    from PySide6 import __version__ as pyside_version
    from PySide6.QtGui import QAccessible
    from PySide6.QtWidgets import QAbstractButton, QApplication, QSlider

    if QApplication.instance() is None:
        QApplication([])
    window = MainWindow(AudioEngine(NullOutput(realtime=False), block_size=256))
    try:
        controls = []
        for path, expected_name in CONTROL_INVENTORY.items():
            widget = _resolve(window, path)
            interface = QAccessible.queryAccessibleInterface(widget)
            valid = interface is not None and interface.isValid()
            name = interface.text(QAccessible.Text.Name) if valid else ""
            role = interface.role().name if valid else "none"
            controls.append(
                {
                    "control": path,
                    "widget": type(widget).__name__,
                    "accessible_name": name,
                    "expected_name": expected_name,
                    "role": role,
                    "status": "pass" if valid and name == expected_name else "fail",
                }
            )

        # Window-wide invariants over every interactive control, not just the
        # inventory. Qt's own chrome (objectName "qt_*" overflow chevrons) is
        # excluded: it is not application UI.
        glyph_buttons = []
        for button in window.findChildren(QAbstractButton):
            if button.objectName().startswith("qt_"):
                continue
            interface = QAccessible.queryAccessibleInterface(button)
            name = interface.text(QAccessible.Text.Name) if interface else ""
            if not re.search(r"[A-Za-z]", name):
                glyph_buttons.append(f"{type(button).__name__}:{name!r}")
        unnamed_sliders = []
        for slider in window.findChildren(QSlider):
            interface = QAccessible.queryAccessibleInterface(slider)
            if not (interface and interface.text(QAccessible.Text.Name)):
                unnamed_sliders.append(type(slider.parent()).__name__)

        tree_nodes, tree_named = _walk(
            QAccessible.queryAccessibleInterface(window)
        )
    finally:
        window.close()

    checks = {
        "inventory_names_and_roles_published": all(
            entry["status"] == "pass" for entry in controls
        ),
        "no_application_button_announces_a_bare_glyph": not glyph_buttons,
        "every_slider_announces_its_parameter": not unnamed_sliders,
        "accessible_tree_walkable_from_window": tree_nodes
        >= len(CONTROL_INVENTORY),
    }

    return {
        "artifact": "screen-reader-evidence",
        "checklist_item": "D4",
        "generated_by": "tools/screen_reader_probe.py",
        "status": "pass" if all(checks.values()) else "fail",
        "evidence": "headless-proxy",
        "method": (
            "MainWindow built on the Qt offscreen platform; every control in "
            "the inventory introspected with QAccessible."
            "queryAccessibleInterface — the tree UIA/NSAccessibility/AT-SPI "
            "bridges hand to NVDA, VoiceOver and Orca — plus window-wide "
            "invariants (no glyph-only button names, no unnamed sliders) and "
            "a full parent-to-child tree walk"
        ),
        "qt_platform": os.environ.get("QT_QPA_PLATFORM", ""),
        "pyside6_version": pyside_version,
        "controls": controls,
        "accessible_tree_nodes": tree_nodes,
        "accessible_tree_named_nodes": tree_named,
        "glyph_only_buttons": glyph_buttons,
        "unnamed_sliders": unnamed_sliders,
        "checks": checks,
        # Honest limits: introspection is not an assistive-technology session.
        "live_screen_reader_session": False,
        "screen_reader_platforms_passed": 0,
        "limitations": (
            "No NVDA, VoiceOver or Orca session was run. Passing proves the "
            "application publishes worded names and roles to Qt's "
            "accessibility layer, which is what the platform bridges read; "
            "it does not prove a screen reader announced them correctly."
        ),
        "unit_suite": "audio-studio/tests/test_accessibility.py::TestScreenReaderReadiness",
    }


def main() -> int:
    report = probe()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {OUTPUT_PATH.relative_to(REPOSITORY_ROOT)} "
        f"(status: {report['status']})"
    )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
