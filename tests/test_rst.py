"""Tests for Ansys RST reader."""

from __future__ import annotations

import pytest

pytest.importorskip("ansys.mapdl.reader")

from ansys.mapdl.reader import examples

from openfemlab.io.rst import read_rst


def test_read_rst_example_displacements():
    result = read_rst(examples.rstfile, step=0)
    assert result.num_nodes > 0
    assert result.displacements.shape[0] == result.num_nodes
    assert result.displacements.shape[1] == 3
    assert result.format == "ansys-rst"
