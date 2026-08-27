"""Frozen-application entry point.

PyInstaller analyses a script, not a console-script entry point, so the
``audio-studio`` command is spelled out here once. Nothing but the call belongs
in this file: anything else would run in the bundle and not in a ``pip``
install, which is exactly the kind of difference that makes a shipped build
behave unlike the one that was tested.
"""

from __future__ import annotations

import multiprocessing
import sys

from audio_studio.app import main

if __name__ == "__main__":
    # A frozen child process re-executes this binary; without this it would
    # start a second copy of the application instead of a worker.
    multiprocessing.freeze_support()
    sys.exit(main())
