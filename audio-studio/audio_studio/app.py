"""Application bootstrap: argument parsing, Qt setup, window creation."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import __app_name__, __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="audio-studio",
        description=f"{__app_name__} — professional audio editing and analysis workstation.",
    )
    parser.add_argument("file", nargs="?", help="audio file to open on start-up")
    parser.add_argument(
        "--null-audio",
        action="store_true",
        help="use the simulated output backend instead of a hardware device",
    )
    parser.add_argument(
        "--wasapi-exclusive",
        action="store_true",
        help="request WASAPI exclusive-mode output for lower latency "
        "(Windows only; other platforms ignore it)",
    )
    parser.add_argument(
        "--offscreen",
        action="store_true",
        help="render with the Qt offscreen platform plugin (headless smoke tests)",
    )
    parser.add_argument(
        "--exit-after",
        type=float,
        metavar="SECONDS",
        help="quit automatically after N seconds (used by CI smoke tests)",
    )
    parser.add_argument("--version", action="version", version=f"{__app_name__} {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for ``python -m audio_studio`` and the console script."""
    args = build_parser().parse_args(argv)

    if args.offscreen:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    # Imported after the platform plugin is chosen so Qt picks it up.
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from .core.engine import AudioEngine
    from .core.output import WASAPI_EXCLUSIVE_ENV_VAR, NullOutput, create_output
    from .ui.main_window import MainWindow

    app = QApplication(sys.argv[:1] + (argv or []))
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("Audio Studio")

    # Must land before the engine builds its output; create_output() reads it.
    if args.wasapi_exclusive:
        os.environ[WASAPI_EXCLUSIVE_ENV_VAR] = "1"

    output = NullOutput() if args.null_audio else create_output()
    engine = AudioEngine(output)
    window = MainWindow(engine)
    window.show()

    if args.file:
        path = Path(args.file).expanduser()
        if not window.open_file(path):
            return 2

    if args.exit_after is not None:
        QTimer.singleShot(int(args.exit_after * 1000), app.quit)

    try:
        return app.exec()
    finally:
        engine.shutdown()


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
