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


def _write_sidecar_bdf(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
    _write_sidecar_bdf(
        path.with_suffix(".bdf"),
        [
            "GRID,11,,0.,0.,0.",
            "GRID,22,,1.,0.,0.",
            "CROD,100,40,11,22",
        ],
    )

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
    _write_sidecar_bdf(
        path.with_suffix(".bdf"),
        [
            "CORD2R,1,0,0.,0.,0.,0.,0.,1.,0.,1.,0.",
            "GRID,11,1,1.,0.,0.",
        ],
    )

    shell_geometry = op2_fixture.write_op2(
        [
            op2_fixture.geom1_block([op2_fixture.Grid(id=11, xyz=(0.0, 0.0, 0.0))]),
            op2_fixture.pshell_block(
                [op2_fixture.Pshell(id=10, material_id=7, thickness=0.0025)]
            ),
            op2_fixture.psolid_block([op2_fixture.Psolid(id=20, material_id=7)]),
            op2_fixture.mpt_block([op2_fixture.Mat1(id=7, E=2.0e11, nu=0.3, rho=7800.0)]),
        ]
    )
    path = target / "shell_properties.op2"
    path.write_bytes(shell_geometry)
    written.append(path)
    _write_sidecar_bdf(
        path.with_suffix(".bdf"),
        [
            "GRID,11,,0.,0.,0.",
            "PSHELL,10,7,0.0025",
            "PSOLID,20,7",
        ],
    )

    quad_grids = [
        op2_fixture.Grid(id=11, xyz=(0.0, 0.0, 0.0)),
        op2_fixture.Grid(id=22, xyz=(1.0, 0.0, 0.0)),
        op2_fixture.Grid(id=33, xyz=(1.0, 1.0, 0.0)),
        op2_fixture.Grid(id=44, xyz=(0.0, 1.0, 0.0)),
    ]
    quad_geometry = op2_fixture.write_op2(
        [
            op2_fixture.geom1_block(quad_grids),
            op2_fixture.geom2_quad4_block(
                [op2_fixture.Quad4(id=100, property_id=10, grids=(11, 22, 33, 44))]
            ),
        ]
    )
    path = target / "quad4_geometry.op2"
    path.write_bytes(quad_geometry)
    written.append(path)
    _write_sidecar_bdf(
        path.with_suffix(".bdf"),
        [
            "GRID,11,,0.,0.,0.",
            "GRID,22,,1.,0.,0.",
            "GRID,33,,1.,1.,0.",
            "GRID,44,,0.,1.,0.",
            "CQUAD4,100,10,11,22,33,44",
        ],
    )

    cbar_geometry = op2_fixture.geometry_file(
        [
            op2_fixture.Grid(id=11, xyz=(0.0, 0.0, 0.0)),
            op2_fixture.Grid(id=22, xyz=(1.0, 0.0, 0.0)),
            op2_fixture.Grid(id=33, xyz=(2.0, 0.5, 0.0)),
        ],
        cbars=[
            op2_fixture.CBar(id=300, property_id=50, grids=(11, 22), orientation=(0.0, 0.0, 1.0)),
            op2_fixture.CBar(id=400, property_id=50, grids=(22, 33), orientation=(0.0, 1.0, 0.0)),
        ],
    )
    path = target / "cbar_geometry.op2"
    path.write_bytes(cbar_geometry)
    written.append(path)
    _write_sidecar_bdf(
        path.with_suffix(".bdf"),
        [
            "GRID,11,,0.,0.,0.",
            "GRID,22,,1.,0.,0.",
            "GRID,33,,2.,0.5,0.",
            "CBAR,300,50,11,22,0.,0.,1.",
            "CBAR,400,50,22,33,0.,1.,0.",
        ],
    )
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
