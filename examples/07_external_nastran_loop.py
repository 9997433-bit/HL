"""Optional external Nastran driver loop (AC-IO-015).

When ``OPENFEMLAB_NASTRAN_EXE`` (or ``NASTRAN_EXE`` / ``NASTRAN`` / a
``nastran`` binary on ``PATH``) is available, this script writes a minimal rod
BDF, invokes the external solver, and reports the batch exit code.  Without a
solver the script still validates the BDF export path and prints a skip notice
so CI and laptops without Nastran licences stay green.

Run::

    python examples/07_external_nastran_loop.py
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

from openfemlab.io import FormatError, read_bdf, write_bdf
from openfemlab.io.drivers.nastran import resolve_nastran_executable, run_nastran

BDF_TEXT = """\
GRID,11,,0.,0.,0.
GRID,22,,1.,0.,0.
MAT1,7,2.1+11,,0.3,7850.
PROD,40,7,1.0-4
CROD,100,40,11,22
ENDDATA
"""


def main() -> int:
    neutral = read_bdf(io.StringIO(BDF_TEXT))
    out_dir = Path("nastran_run")
    out_dir.mkdir(exist_ok=True)
    deck = out_dir / "rod_export.bdf"
    write_bdf(neutral, deck)
    print(f"exported BDF: {deck} ({deck.stat().st_size} bytes)")

    exe = resolve_nastran_executable()
    if exe is None:
        print(
            "skip: no Nastran executable found "
            "(set OPENFEMLAB_NASTRAN_EXE to run the external batch step)"
        )
        return 0

    print(f"running external Nastran: {exe}")
    try:
        result = run_nastran(deck, work_dir=out_dir, executable=exe, timeout_s=120.0)
    except FormatError as exc:
        print(f"driver error: {exc}", file=sys.stderr)
        return 1

    print(f"exit code: {result.exit_code}")
    if result.stdout.strip():
        print("--- stdout (tail) ---")
        print("\n".join(result.stdout.strip().splitlines()[-8:]))
    if result.stderr.strip():
        print("--- stderr (tail) ---")
        print("\n".join(result.stderr.strip().splitlines()[-8:]))
    return 0 if result.exit_code == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
