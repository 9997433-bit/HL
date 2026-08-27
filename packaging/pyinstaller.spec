# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller recipe for the Audio Studio desktop bundle.

Build it with ``scripts/build-linux.sh``, which sets the paths this file
expects and runs the checks below afterwards; ``pyinstaller
packaging/pyinstaller.spec`` from the repository root also works.

Three choices here are licence obligations rather than preferences, and none of
them may be flipped for a smaller download:

* **One directory, never one file.** Qt (through PySide6 and Shiboken6) and
  libsndfile reach the application under the LGPL, which is only satisfied
  while a recipient can replace those libraries with their own compatible
  build. ``COLLECT`` leaves every ``.so``/``.dylib``/``.dll`` beside the
  launcher where it can be swapped. A ``--onefile`` build unpacks to a
  throwaway temporary directory each run, so a replaced library would be
  overwritten on the next launch.
* **No UPX.** Compressing a shared object rewrites it; a recipient can no
  longer drop in a stock build of the same soname, and Qt's plugin loader has
  historically broken outright on compressed libraries.
* **No pedalboard.** It is GPL-3.0 and bundling it would relicense the whole
  distribution (see ``THIRD_PARTY_LICENSES.md``). It is excluded here and the
  build script refuses to run when it is importable, because an exclusion that
  is only a list entry is one refactor away from not being one.

The matching source offer and relinking instructions ship inside the bundle as
``licenses/LGPL-RELINKING.txt``; keep that file and the third-party notices
together with any binary that leaves the building.
"""

from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent  # noqa: F821 - injected by PyInstaller
APP_DIR = ROOT / "audio-studio"
NAME = "audio-studio"

#: Never bundled: a GPL dependency here relicenses the whole artifact.
GPL_MODULES = ["pedalboard"]

#: Nothing in the application imports these; keeping them out of the analysis
#: keeps test and plotting stacks from riding along into a shipped build.
UNWANTED = [
    "IPython",
    "PyQt5",
    "PyQt6",
    "matplotlib",
    "pytest",
    "tkinter",
]

datas = [
    (str(ROOT / "THIRD_PARTY_LICENSES.md"), "licenses"),
    (str(ROOT / "packaging" / "LGPL-RELINKING.txt"), "licenses"),
]

a = Analysis(  # noqa: F821 - injected by PyInstaller
    [str(ROOT / "packaging" / "audio_studio_main.py")],
    pathex=[str(APP_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # Imported lazily behind a runtime probe, so the analysis cannot see
        # them from the import graph alone.
        "audio_studio.core.sounddevice_output",
        "audio_studio.ui.main_window",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[*GPL_MODULES, *UNWANTED],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)  # noqa: F821 - injected by PyInstaller

exe = EXE(  # noqa: F821 - injected by PyInstaller
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(  # noqa: F821 - injected by PyInstaller
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=NAME,
)
