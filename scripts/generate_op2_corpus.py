#!/usr/bin/env python3
"""Generate a synthetic OP2 corpus for opt-in reader validation.

Real Nastran output requires a licence, so CI uses files written by
``tests/_op2.py``.  Point ``OPENFEMLAB_OP2_CORPUS`` at the output directory
to run :mod:`tests.test_op2_corpus`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

import _op2 as op2_fixture  # noqa: E402


def build_corpus(target: Path) -> list[Path]:
    target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    rod_geometry = op2_fixture.geometry_file(
        [
            op2_fixture.Grid(id=11, xyz=(0.0, 0.0, 0.0)),
            op2_fixture.Grid(id=22, xyz=(1.0, 0.0, 0.0)),
        ],
        [op2_fixture.Rod(id=100, property_id=40, grids=(11, 22))],
        [op2_fixture.Mat1(id=7, E=2.0e11, nu=0.3, rho=7800.0)],
        properties=[op2_fixture.Prod(id=40, material_id=7, area=1.0e-4)],
    )
    path = target / "rod_geometry.op2"
    path.write_bytes(rod_geometry)
    written.append(path)

    modes = [
        op2_fixture.Mode(number=1, frequency_hz=12.5, shape={11: (0.0, 0.0, 1.0, 0.0, 0.0, 0.0)})
    ]
    rod_modes = op2_fixture.modes_file(
        modes,
        grids=[op2_fixture.Grid(id=11, xyz=(0.0, 0.0, 0.0))],
    )
    path = target / "rod_modes.op2"
    path.write_bytes(rod_modes)
    written.append(path)

    cord = op2_fixture.Cord2R(
        cid=1,
        origin=(0.0, 0.0, 0.0),
        z_point=(0.0, 0.0, 1.0),
        xz_point=(0.0, 1.0, 0.0),
    )
    rotated = op2_fixture.geometry_file(
        [op2_fixture.Grid(id=11, xyz=(1.0, 0.0, 0.0), cp=1, cd=0)],
        cords=[cord],
    )
    path = target / "rotated_grid.op2"
    path.write_bytes(rotated)
    written.append(path)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "directory",
        nargs="?",
        default=".corpus/op2",
        help="output directory (default: .corpus/op2)",
    )
    args = parser.parse_args()
    paths = build_corpus(Path(args.directory))
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
