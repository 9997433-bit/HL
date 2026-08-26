"""Application bootstrap: argument parsing, Qt setup, window creation."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import MutableMapping
from pathlib import Path

from . import __app_name__, __version__

#: Qt reads this once, while ``QGuiApplication`` is being constructed, and
#: multiplies every logical pixel by it — so it has to be in the environment
#: before the first Qt object exists, not set through an API afterwards.
SCALE_FACTOR_ENV_VAR = "QT_SCALE_FACTOR"

#: Below 1.0 the chrome falls under the hit-target and text sizes the layout
#: was drawn for; above 2.0 the transport strip stops fitting a 1080p screen.
MIN_SCALE_FACTOR = 1.0
MAX_SCALE_FACTOR = 2.0


def scale_factor(value: str) -> float:
    """``argparse`` type for ``--scale-factor``: a float in ``[1.0, 2.0]``."""
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not a number") from None
    if not MIN_SCALE_FACTOR <= number <= MAX_SCALE_FACTOR:
        raise argparse.ArgumentTypeError(
            f"{number:g} is outside {MIN_SCALE_FACTOR:g}–{MAX_SCALE_FACTOR:g}"
        )
    return number


def apply_scale_factor(
    factor: float | None, environ: MutableMapping[str, str] = os.environ
) -> str | None:
    """Publish ``factor`` for Qt, returning the value it will read.

    An explicit flag wins; without one, a ``QT_SCALE_FACTOR`` inherited from
    the desktop session is left exactly as it is, so the platform's own
    display scaling keeps working.
    """
    if factor is not None:
        environ[SCALE_FACTOR_ENV_VAR] = f"{factor:g}"
    return environ.get(SCALE_FACTOR_ENV_VAR)


def configure_high_dpi() -> None:
    """Ask Qt for fractional HiDPI scaling. Must precede the ``QApplication``.

    Qt 6 enables high-DPI scaling itself, but rounds the platform's device
    pixel ratio to a whole number by default, which throws away a 125% or 150%
    desktop setting. ``PassThrough`` keeps the fraction, which is also what
    makes a ``--scale-factor 1.5`` land as 1.5 rather than as 1 or 2.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )


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
        "--scale-factor",
        type=scale_factor,
        metavar="FACTOR",
        help=(
            f"scale the whole interface by FACTOR "
            f"({MIN_SCALE_FACTOR:g}–{MAX_SCALE_FACTOR:g}); overrides QT_SCALE_FACTOR"
        ),
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
    apply_scale_factor(args.scale_factor)

    # Imported after the platform plugin is chosen so Qt picks it up.
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from .core.engine import AudioEngine
    from .core.output import WASAPI_EXCLUSIVE_ENV_VAR, NullOutput, create_output
    from .ui.main_window import MainWindow

    configure_high_dpi()
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
