"""Optional external Nastran driver loop with OP2 readback (AC-IO-015).

When ``OPENFEMLAB_NASTRAN_EXE`` (or ``NASTRAN_EXE`` / ``NASTRAN`` / a
``nastran`` binary on ``PATH``) is available, this script writes a minimal rod
BDF, invokes the external solver, and — if an ``.op2`` appears in the work
directory — reads its modes back through ``openfemlab.io.op2``.  Without a
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


def _find_op2(work_dir: Path) -> Path | None:
    candidates = sorted(work_dir.glob("*.op2"))
    return candidates[0] if candidates else None


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

    op2_path = _find_op2(out_dir)
    if op2_path is None:
        print("note: no .op2 produced in the work directory; skipping mode readback")
        return 0 if result.exit_code == 0 else 2

    try:
        from openfemlab.io.op2 import read_op2_modes
    except ImportError:
        print(f"found OP2 {op2_path.name} but openfemlab.io.op2 is unavailable")
        return 0 if result.exit_code == 0 else 2

    try:
        modes = read_op2_modes(op2_path)
    except Exception as exc:  # noqa: BLE001 — optional licence-local path
        print(f"OP2 readback failed for {op2_path.name}: {exc}", file=sys.stderr)
        return 0 if result.exit_code == 0 else 2

    n_modes = getattr(modes, "n_modes", None)
    if n_modes is None and hasattr(modes, "frequencies"):
        n_modes = len(modes.frequencies)
    print(f"OP2 readback: {op2_path.name} → {n_modes} mode(s)")
    return 0 if result.exit_code == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
