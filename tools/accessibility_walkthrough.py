#!/usr/bin/env python3
"""Live Linux screen-reader walkthrough (AT-SPI + Orca) for checklist D4.

Unlike ``tools/screen_reader_probe.py`` — which introspects the Qt
accessibility tree in-process and honestly records
``screen_reader_platforms_passed: 0`` — this tool runs a real assistive
technology stack and lets it observe the real application over the
accessibility bus:

1. An isolated headless X server (Xvfb) and a private D-Bus session bus are
   started, so the walkthrough cannot cross wires with any desktop session
   that happens to be running on the host.
2. ``org.a11y.Bus.GetAddress`` activates ``at-spi-bus-launcher`` on that
   private session bus, creating a dedicated AT-SPI accessibility bus.  Its
   address is pinned via ``AT_SPI_BUS_ADDRESS`` for every process below.
3. The real :class:`MainWindow` is launched on the ``xcb`` platform with
   ``QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1``, so Qt's AT-SPI adaptor publishes
   the application to the accessibility bus.
4. Orca — the Linux screen reader — is started against that bus with debug
   logging.  Orca subscribes to the application's events exactly as it would
   for a sighted-assistance session.
5. An AT-SPI client (pyatspi, the same client library Orca is built on)
   walks the application's accessible tree *over the bus* and verifies every
   control in the D4 inventory publishes its expected name, then records the
   ``object:state-changed:focused`` events emitted while the application
   walks keyboard focus through its focusable controls.
6. Orca's debug log is parsed for the ``SPEECH OUTPUT:`` utterances it
   generated for those focus changes: the report requires every focusable
   control's accessible name to have been spoken by Orca.

What this proves: Orca, running live against the real application, received
the application's accessibility events and generated correct spoken
announcements for its controls.  What it does not prove: audio hardware
delivery of that speech (the host is headless), or NVDA/VoiceOver behaviour
on Windows/macOS — those platforms are reported ``not-run``, not passed.

Writes ``.agent_workspace/round3/accessibility-report.json``.  Run from the
repository root with the project virtualenv::

    python tools/accessibility_walkthrough.py

Requires system packages: ``xvfb``, ``dbus``, ``at-spi2-core``, ``orca``,
``python3-pyatspi`` (the AT-SPI client may run under the system Python when
the virtualenv has no ``pyatspi``).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
AUDIO_STUDIO_ROOT = REPOSITORY_ROOT / "audio-studio"
OUTPUT_PATH = REPOSITORY_ROOT / ".agent_workspace/round3/accessibility-report.json"

for import_root in (REPOSITORY_ROOT, AUDIO_STUDIO_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from tools.screen_reader_probe import CONTROL_INVENTORY

APPLICATION_NAME = "audio-studio"

#: AT-SPI role names the interactive inventory controls must expose on the
#: bus.  These are the roles Orca keys its announcements on ("Record check
#: box not checked", "Output gain slider"); a wrong role is a wrong
#: announcement even when the name is right.
ATSPI_ROLE_EXPECTATIONS: dict[str, set[str]] = {
    "Record": {"check box"},
    "Play or pause": {"push button"},
    "Stop": {"push button"},
    "Go to start": {"push button"},
    "Go to end": {"push button"},
    "Loop playback": {"check box"},
    "Output gain": {"slider"},
    "Marker and region list": {"tree", "tree table"},
}

MAX_FOCUS_TARGETS = 14
FOCUS_INTERVAL_MS = 700
FOCUS_PASSES = 2
SPEECH_LINE = re.compile(r"SPEECH OUTPUT:")


# --------------------------------------------------------------------------
# --app mode: the application under test
# --------------------------------------------------------------------------


def _resolve(window: Any, path: str) -> Any:
    widget = window
    for attribute in path.split("."):
        widget = getattr(widget, attribute)
    return widget


def run_app(duration_s: int) -> int:
    """Show the real MainWindow and, on request, walk keyboard focus."""
    from audio_studio.core.engine import AudioEngine
    from audio_studio.core.output import NullOutput
    from audio_studio.ui.main_window import MainWindow
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtWidgets import QApplication, QWidget

    app = QApplication([APPLICATION_NAME])
    app.setApplicationName(APPLICATION_NAME)
    window = MainWindow(AudioEngine(NullOutput(realtime=False), block_size=256))
    window.show()
    window.raise_()
    window.activateWindow()

    def _accepts_tab_focus(widget: QWidget) -> bool:
        return bool(widget.focusPolicy() & Qt.FocusPolicy.TabFocus)

    targets: list[tuple[str, QWidget]] = []
    seen: set[str] = set()

    def _add(widget: QWidget) -> None:
        name = widget.accessibleName()
        if not name or name in seen:
            return
        if not (widget.isVisible() and widget.isEnabled() and _accepts_tab_focus(widget)):
            return
        seen.add(name)
        targets.append((name, widget))

    # Inventory controls first, then any other named focusable widget the
    # window exposes, deterministically capped so the session stays bounded.
    for path in CONTROL_INVENTORY:
        try:
            _add(_resolve(window, path))
        except AttributeError:
            pass
    for widget in window.findChildren(QWidget):
        if len(targets) >= MAX_FOCUS_TARGETS:
            break
        _add(widget)

    print("FOCUS_TARGETS " + json.dumps([name for name, _ in targets]), flush=True)
    print("APP READY", flush=True)

    walk_requested = threading.Event()

    def _watch_stdin() -> None:
        for line in sys.stdin:
            if line.strip() == "WALK":
                walk_requested.set()

    threading.Thread(target=_watch_stdin, daemon=True).start()

    sequence = [entry for _ in range(FOCUS_PASSES) for entry in targets]
    cursor = 0
    walk_timer = QTimer()
    walk_timer.setInterval(FOCUS_INTERVAL_MS)

    def _step() -> None:
        nonlocal cursor
        if cursor >= len(sequence):
            walk_timer.stop()
            print("WALK DONE", flush=True)
            return
        name, widget = sequence[cursor]
        cursor += 1
        widget.setFocus(Qt.FocusReason.TabFocusReason)
        print(f"FOCUSED {name}", flush=True)

    walk_timer.timeout.connect(_step)

    poll = QTimer()
    poll.setInterval(200)

    def _maybe_start() -> None:
        if walk_requested.is_set():
            poll.stop()
            window.activateWindow()
            walk_timer.start()

    poll.timeout.connect(_maybe_start)
    poll.start()

    QTimer.singleShot(duration_s * 1000, app.quit)
    app.exec()
    window.close()
    return 0


# --------------------------------------------------------------------------
# --atspi-client mode: bus-side introspection, the view Orca gets
# --------------------------------------------------------------------------


def run_atspi_client(expected_focus_names: list[str], watch_seconds: int) -> int:
    import pyatspi
    from gi.repository import GLib

    def _find_application() -> Any:
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            desktop = pyatspi.Registry.getDesktop(0)
            for candidate in desktop:
                if candidate is not None and candidate.name == APPLICATION_NAME:
                    return candidate
            time.sleep(0.5)
        return None

    application = _find_application()
    result: dict[str, Any] = {"app_found": application is not None}
    if application is None:
        print("RESULT " + json.dumps(result), flush=True)
        return 1

    def _snapshot(node: Any) -> tuple[str, str, list[Any]] | None:
        """Name, role and children of a node, or None if it vanished mid-walk."""
        try:
            return (
                node.name,
                node.getRoleName(),
                [node.getChildAtIndex(index) for index in range(node.childCount)],
            )
        except GLib.GError:
            return None

    # A name may appear more than once with different roles ("Stop" is both
    # the transport button and a Transport-menu item), so collect every role.
    named_nodes: dict[str, list[str]] = {}
    node_count = 0
    stack = [application]
    while stack and node_count < 5000:
        snapshot = _snapshot(stack.pop())
        node_count += 1
        if snapshot is None:
            continue
        name, role, children = snapshot
        if name:
            roles = named_nodes.setdefault(name, [])
            if role not in roles:
                roles.append(role)
        stack.extend(child for child in children if child is not None)

    result["tree_nodes"] = node_count
    result["named_nodes"] = named_nodes

    focus_events: list[dict[str, str]] = []
    focus_names_seen: set[str] = set()
    expected = set(expected_focus_names)

    def _on_focus(event: Any) -> None:
        if not event.detail1:
            return
        try:
            name = event.source.name
            role = event.source.getRoleName()
        except GLib.GError:
            return
        focus_events.append({"name": name, "role": role})
        if name:
            focus_names_seen.add(name)
        if expected and expected <= focus_names_seen:
            pyatspi.Registry.stop()

    pyatspi.Registry.registerEventListener(_on_focus, "object:state-changed:focused")
    print("CLIENT READY", flush=True)

    def _timeout() -> bool:
        pyatspi.Registry.stop()
        return False

    GLib.timeout_add_seconds(watch_seconds, _timeout)
    pyatspi.Registry.start()
    pyatspi.Registry.deregisterEventListener(_on_focus, "object:state-changed:focused")

    result["focus_events"] = focus_events
    print("RESULT " + json.dumps(result), flush=True)
    return 0


# --------------------------------------------------------------------------
# Orchestrator
# --------------------------------------------------------------------------


class _LineReader:
    """Collects a subprocess's stdout lines on a background thread."""

    def __init__(self, process: subprocess.Popen) -> None:
        self._process = process
        self.lines: list[str] = []
        self._condition = threading.Condition()
        self._thread = threading.Thread(target=self._pump, daemon=True)
        self._thread.start()

    def _pump(self) -> None:
        for raw in self._process.stdout:
            with self._condition:
                self.lines.append(raw.rstrip("\n"))
                self._condition.notify_all()

    def wait_for(self, prefix: str, timeout: float) -> str | None:
        deadline = time.monotonic() + timeout
        with self._condition:
            while True:
                for line in self.lines:
                    if line.startswith(prefix):
                        return line
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self._condition.wait(remaining)


def _isolated_environment(display: str) -> dict[str, str]:
    """The host's environment minus anything that leaks a desktop session."""
    strip = (
        "DISPLAY",
        "WAYLAND_DISPLAY",
        "DBUS_SESSION_BUS_ADDRESS",
        "DBUS_SESSION_BUS_PID",
        "AT_SPI_BUS_ADDRESS",
        "XDG_RUNTIME_DIR",
        "XAUTHORITY",
        "QT_QPA_PLATFORM",
        "QT_ACCESSIBILITY",
    )
    environment = {key: value for key, value in os.environ.items() if key not in strip}
    environment["DISPLAY"] = display
    return environment


def _free_display() -> str:
    for number in range(91, 191):
        if not Path(f"/tmp/.X11-unix/X{number}").exists():
            return f":{number}"
    raise RuntimeError("no free X display number between :91 and :190")


def _client_python() -> str:
    """A Python interpreter that can import pyatspi (Orca's client library)."""
    candidates = [sys.executable, "/usr/bin/python3", shutil.which("python3")]
    for candidate in candidates:
        if not candidate:
            continue
        check = subprocess.run(
            [candidate, "-c", "import pyatspi"],
            capture_output=True,
            timeout=60,
            check=False,
        )
        if check.returncode == 0:
            return candidate
    raise SystemExit(
        "no Python interpreter with pyatspi found; install python3-pyatspi"
    )


def _tool_version(command: list[str]) -> str:
    try:
        output = subprocess.run(
            command, capture_output=True, text=True, timeout=30, check=False
        )
        return (output.stdout or output.stderr).strip().splitlines()[0]
    except (OSError, subprocess.TimeoutExpired, IndexError):
        return "unknown"


def _wcag_evidence() -> dict[str, Any]:
    """The automated WCAG 2.2 AA audit, measured live from the shipped theme."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from audio_studio.ui.colormaps import COLORMAP_NAMES
    from audio_studio.ui.theme import (
        GRAPHIC_PAIRS,
        PALETTE,
        TEXT_PAIRS,
        contrast_ratio,
        failing_pairs,
    )

    text_ratios = {
        f"{fg}/{bg}": round(contrast_ratio(PALETTE.color(fg), PALETTE.color(bg)), 2)
        for fg, bg in TEXT_PAIRS
    }
    graphic_ratios = {
        f"{fg}/{bg}": round(contrast_ratio(PALETTE.color(fg), PALETTE.color(bg)), 2)
        for fg, bg in GRAPHIC_PAIRS
    }
    failures = failing_pairs(PALETTE)
    return {
        "audit": "automated audit of the WCAG 2.2 AA success criteria that are "
        "machine-checkable in this codebase; not a human conformance review",
        "contrast_pass": not failures,
        "failing_pairs": [list(pair) for pair, _ratio, _floor in failures],
        "text_pair_ratios": text_ratios,
        "minimum_text_ratio": min(text_ratios.values()),
        "graphic_pair_ratios": graphic_ratios,
        "minimum_graphic_ratio": min(graphic_ratios.values()),
        "color_safe_colormap": "viridis" in COLORMAP_NAMES,
        "success_criteria": {
            "1.4.1 Use of Color": "clip state carries a CLIP label and accessible "
            "description, not colour alone (test_accessibility.py::TestStateIsNotColourAlone)",
            "1.4.3 Contrast (Minimum)": "every text pair >= 4.5:1, measured above",
            "1.4.4 Resize Text": "100-200% UI scaling via QT_SCALE_FACTOR "
            "(test_accessibility.py::TestScaleFactor, checklist D5)",
            "1.4.11 Non-text Contrast": "every graphic pair >= 3:1, measured above",
            "2.1.1 Keyboard": "every menu command keyboard-bound "
            "(test_accessibility.py::TestKeyboardReach, checklist D3)",
            "2.4.7 Focus Visible": "2px accent focus ring in the stylesheet "
            "(test_accessibility.py::TestPaletteContrast)",
            "4.1.2 Name, Role, Value": "verified over the live AT-SPI bus by "
            "this walkthrough and headlessly by tools/screen_reader_probe.py",
        },
        "unit_suites": [
            "audio-studio/tests/test_accessibility.py",
            "tests/acceptance/test_sota_checklist.py::test_sota_checklist_item[D4]",
        ],
    }


def _extract_speech_lines(debug_log: Path) -> list[str]:
    """The utterances Orca generated, without timestamps or voice metadata."""
    if not debug_log.is_file():
        return []
    utterance = re.compile(r"SPEECH OUTPUT: '(.*?)'(?: \{'established'|$)")
    lines = []
    for raw in debug_log.read_text(encoding="utf-8", errors="replace").splitlines():
        if not SPEECH_LINE.search(raw):
            continue
        match = utterance.search(raw)
        lines.append(match.group(1) if match else raw[raw.index("SPEECH OUTPUT:") :])
    return lines


def run_walkthrough(keep_temp: bool) -> int:
    display = _free_display()
    environment = _isolated_environment(display)
    client_python = _client_python()
    temp_root = Path(tempfile.mkdtemp(prefix="a11y-walkthrough-"))
    orca_debug_log = temp_root / "orca-debug.log"
    orca_prefs = temp_root / "orca-prefs"
    orca_prefs.mkdir()

    children: list[tuple[str, subprocess.Popen]] = []

    def _spawn(name: str, command: list[str], env: dict[str, str], **kwargs: Any) -> subprocess.Popen:
        process = subprocess.Popen(
            command,
            env=env,
            cwd=str(REPOSITORY_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            **kwargs,
        )
        children.append((name, process))
        return process

    checks: dict[str, bool] = {}
    failures: list[str] = []
    report: dict[str, Any] = {}

    def _check(name: str, passed: bool, detail: str = "") -> None:
        checks[name] = bool(passed)
        if not passed:
            failures.append(f"{name}: {detail}" if detail else name)

    try:
        print(f"[infra] Xvfb on {display}")
        _spawn(
            "xvfb",
            ["Xvfb", display, "-screen", "0", "1600x1000x24", "-nolisten", "tcp"],
            environment,
        )
        time.sleep(1.5)

        print("[infra] private D-Bus session bus")
        bus = _spawn(
            "dbus",
            ["dbus-daemon", "--session", "--nofork", "--print-address=1"],
            environment,
        )
        bus_address = bus.stdout.readline().strip()
        if not bus_address:
            raise RuntimeError("dbus-daemon printed no address")
        environment["DBUS_SESSION_BUS_ADDRESS"] = bus_address

        print("[infra] dedicated AT-SPI accessibility bus")
        get_address = subprocess.run(
            [
                "gdbus",
                "call",
                "--session",
                "--dest",
                "org.a11y.Bus",
                "--object-path",
                "/org/a11y/bus",
                "--method",
                "org.a11y.Bus.GetAddress",
            ],
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        match = re.search(r"'([^']+)'", get_address.stdout)
        if match is None:
            raise RuntimeError(f"org.a11y.Bus.GetAddress failed: {get_address.stderr}")
        a11y_address = match.group(1)
        environment["AT_SPI_BUS_ADDRESS"] = a11y_address

        print("[app] launching MainWindow on xcb with the AT-SPI adaptor on")
        app_environment = dict(environment)
        app_environment["QT_QPA_PLATFORM"] = "xcb"
        app_environment["QT_LINUX_ACCESSIBILITY_ALWAYS_ON"] = "1"
        app = _spawn(
            "app",
            [sys.executable, str(Path(__file__).resolve()), "--app"],
            app_environment,
            stdin=subprocess.PIPE,
        )
        app_reader = _LineReader(app)
        if app_reader.wait_for("APP READY", timeout=60) is None:
            raise RuntimeError("application did not become ready on the bus")
        targets_line = app_reader.wait_for("FOCUS_TARGETS ", timeout=10)
        focus_targets: list[str] = json.loads(
            targets_line.removeprefix("FOCUS_TARGETS ")
        )
        print(f"[app] focusable controls: {focus_targets}")

        print("[atspi] starting bus-side introspection client")
        client = _spawn(
            "atspi-client",
            [
                client_python,
                str(Path(__file__).resolve()),
                "--atspi-client",
                "--expect-names",
                json.dumps(focus_targets),
                "--watch-seconds",
                "90",
            ],
            environment,
        )
        client_reader = _LineReader(client)
        if client_reader.wait_for("CLIENT READY", timeout=60) is None:
            raise RuntimeError("AT-SPI client never finished the tree walk")

        print("[orca] starting Orca with debug logging")
        orca = _spawn(
            "orca",
            [
                "orca",
                "--replace",
                "--user-prefs",
                str(orca_prefs),
                "--debug-file",
                str(orca_debug_log),
            ],
            environment,
        )
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if orca_debug_log.is_file() and "SPEECH" in orca_debug_log.read_text(
                encoding="utf-8", errors="replace"
            ):
                break
            if orca.poll() is not None:
                raise RuntimeError("Orca exited during startup")
            time.sleep(1.0)
        time.sleep(3.0)  # let Orca finish subscribing to bus events

        print("[walk] driving keyboard focus through the controls")
        app.stdin.write("WALK\n")
        app.stdin.flush()
        walk_done = app_reader.wait_for("WALK DONE", timeout=120) is not None
        time.sleep(3.0)  # let Orca drain its announcement queue

        orca_alive_after_walk = orca.poll() is None

        result_line = client_reader.wait_for("RESULT ", timeout=120)
        if result_line is None:
            raise RuntimeError("AT-SPI client produced no result")
        client_result = json.loads(result_line.removeprefix("RESULT "))

        speech_lines = _extract_speech_lines(orca_debug_log)

        # ------------------------------------------------------------------
        # Evaluation
        # ------------------------------------------------------------------
        named_nodes: dict[str, list[str]] = client_result.get("named_nodes", {})
        inventory_rows = []
        for path, expected_name in CONTROL_INVENTORY.items():
            roles = named_nodes.get(expected_name)
            inventory_rows.append(
                {
                    "control": path,
                    "expected_name": expected_name,
                    "published_on_bus": roles is not None,
                    "atspi_roles": roles or [],
                }
            )
        _check(
            "atspi_bus_publishes_every_inventory_name",
            all(row["published_on_bus"] for row in inventory_rows),
            str([r["expected_name"] for r in inventory_rows if not r["published_on_bus"]]),
        )
        role_mismatches = {
            name: named_nodes.get(name, [])
            for name, accepted in ATSPI_ROLE_EXPECTATIONS.items()
            if not accepted & set(named_nodes.get(name, []))
        }
        _check("atspi_semantic_roles_match", not role_mismatches, str(role_mismatches))

        focus_event_names = {
            event["name"] for event in client_result.get("focus_events", [])
        }
        missing_focus = [n for n in focus_targets if n not in focus_event_names]
        _check(
            "focus_events_observed_for_every_focusable_control",
            walk_done and not missing_focus,
            f"walk_done={walk_done} missing={missing_focus}",
        )

        speech_blob = "\n".join(speech_lines)
        unspoken = [name for name in focus_targets if name not in speech_blob]
        _check(
            "orca_spoke_every_focusable_control",
            bool(speech_lines) and not unspoken,
            f"speech_lines={len(speech_lines)} unspoken={unspoken}",
        )
        _check("orca_ran_throughout_the_walkthrough", orca_alive_after_walk)

        wcag = _wcag_evidence()
        _check("wcag_contrast_audit_passes", wcag["contrast_pass"])
        _check("color_safe_colormap_available", wcag["color_safe_colormap"])

        orca_passed = all(
            checks[key]
            for key in (
                "atspi_bus_publishes_every_inventory_name",
                "atspi_semantic_roles_match",
                "focus_events_observed_for_every_focusable_control",
                "orca_spoke_every_focusable_control",
                "orca_ran_throughout_the_walkthrough",
            )
        )
        wcag_passed = wcag["contrast_pass"] and wcag["color_safe_colormap"]
        status = "pass" if orca_passed and wcag_passed else "fail"

        spoken_samples = [
            line
            for line in speech_lines
            if any(name in line for name in focus_targets)
        ]

        report = {
            "artifact": "accessibility-report",
            "checklist_item": "D4",
            "generated_by": "tools/accessibility_walkthrough.py",
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "status": status,
            "wcag_2_2_aa": "pass" if wcag_passed else "fail",
            "wcag_evidence": wcag,
            "screen_reader_platforms_passed": 1 if orca_passed else 0,
            "platforms": [
                {
                    "platform": "linux",
                    "screen_reader": "orca",
                    "screen_reader_version": _tool_version(["orca", "--version"]),
                    "session": "live",
                    "status": "pass" if orca_passed else "fail",
                    "evidence": {
                        "atspi_tree_nodes": client_result.get("tree_nodes", 0),
                        "inventory": inventory_rows,
                        "focusable_controls": focus_targets,
                        "focus_events_recorded": len(
                            client_result.get("focus_events", [])
                        ),
                        "orca_speech_lines_captured": len(speech_lines),
                        "orca_speech_samples": spoken_samples[:40],
                    },
                },
                {
                    "platform": "windows",
                    "screen_reader": "nvda",
                    "session": None,
                    "status": "not-run",
                    "reason": "no Windows host in this environment; not claimed",
                },
                {
                    "platform": "macos",
                    "screen_reader": "voiceover",
                    "session": None,
                    "status": "not-run",
                    "reason": "no macOS host in this environment; not claimed",
                },
            ],
            "methodology": (
                "Isolated Xvfb display and private D-Bus session with a "
                "dedicated AT-SPI accessibility bus. The real MainWindow ran "
                "on the xcb platform with Qt's AT-SPI adaptor enabled. Orca "
                f"{_tool_version(['orca', '--version'])} attached to the bus "
                "as a live screen reader with debug logging. A pyatspi "
                "client (the same client library Orca uses) verified every "
                "D4 inventory control publishes its accessible name over the "
                "bus and recorded focus events while the application walked "
                "keyboard focus through its focusable controls; Orca's debug "
                "log had to contain a SPEECH OUTPUT utterance naming every "
                "focused control. Transport buttons are deliberately "
                "NoFocus (their commands are global shortcuts), so they are "
                "verified via the bus tree walk rather than the focus walk."
            ),
            "environment": {
                "display_server": f"Xvfb (headless X11, {display})",
                "window_manager": "none",
                "qt_platform": "xcb",
                "at_spi": _tool_version(["dpkg-query", "-W", "-f=${Version}", "at-spi2-core"]),
                "atspi_client_python": client_python,
                "session_isolation": "private dbus-daemon; AT_SPI_BUS_ADDRESS pinned",
            },
            "checks": checks,
            "limitations": (
                "Live Orca session on Linux only: speech utterances were "
                "captured from Orca's debug log, which records exactly what "
                "Orca sends to speech-dispatcher; audible playback through "
                "audio hardware was not verified on this headless host. "
                "NVDA (Windows) and VoiceOver (macOS) were not run and are "
                "reported not-run. WCAG 2.2 AA is an automated audit of the "
                "machine-checkable success criteria, not a human conformance "
                "review."
            ),
            "headless_proxy_companion": ".agent_workspace/v1.0/screen-reader-evidence.json",
            "unit_suite": "audio-studio/tests/test_accessibility.py::TestLiveScreenReaderReport",
        }
    finally:
        for name, process in reversed(children):
            if process.poll() is None:
                process.terminate()
        deadline = time.monotonic() + 5
        for name, process in children:
            remaining = max(0.1, deadline - time.monotonic())
            try:
                process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                process.kill()
        if keep_temp:
            print(f"[debug] temp artifacts kept in {temp_root}")
        else:
            shutil.rmtree(temp_root, ignore_errors=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT_PATH.relative_to(REPOSITORY_ROOT)} (status: {report['status']})")
    for name, passed in checks.items():
        print(f"  {'PASS' if passed else 'FAIL'}  {name}")
    if failures:
        print("failures:")
        for failure in failures:
            print(f"  - {failure}")
    return 0 if report["status"] == "pass" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--atspi-client", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--expect-names", default="[]", help=argparse.SUPPRESS)
    parser.add_argument("--watch-seconds", type=int, default=90, help=argparse.SUPPRESS)
    parser.add_argument("--duration", type=int, default=180, help=argparse.SUPPRESS)
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="keep the Orca debug log and temp directory for inspection",
    )
    args = parser.parse_args()
    if args.app:
        return run_app(args.duration)
    if args.atspi_client:
        return run_atspi_client(json.loads(args.expect_names), args.watch_seconds)
    return run_walkthrough(args.keep_temp)


if __name__ == "__main__":
    raise SystemExit(main())
