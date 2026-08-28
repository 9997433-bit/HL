"""Tests for FRD reader and result locator."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from openfemlab.io.frd import read_frd
from openfemlab.io.results_locator import locate_results


def test_read_frd_displacements(tmp_path: Path):
    frd = tmp_path / "job.frd"
    frd.write_text(
        "\n".join(
            [
                "2C  1  0.0",
                " -2  COORDINATES",
                " -1         1    0.000000E+00    0.000000E+00    0.000000E+00",
                " -1         2    1.000000E+00    0.000000E+00    0.000000E+00",
                " -2  DISP",
                " -1         1    1.000000E-03    0.000000E+00    0.000000E+00",
                " -1         2    2.000000E-03    0.000000E+00    0.000000E+00",
            ]
        )
    )
    result = read_frd(frd)
    assert result.num_nodes == 2
    np.testing.assert_allclose(result.displacements[1, 0], 2e-3, rtol=1e-6)


def test_locate_results_prefers_known_suffixes(tmp_path: Path):
    (tmp_path / "model.frd").write_text("stub")
    (tmp_path / "model.op2").write_bytes(b"stub")
    locator = locate_results(tmp_path)
    assert locator.get("frd") is not None
    assert locator.get("op2") is not None
