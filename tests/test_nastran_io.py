"""Coverage for the minimal Nastran GRID/CROD/MAT1 reader."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import numpy as np
import pytest

from openfemlab.core.neutral import ElementType, NeutralModel
from openfemlab.io import FormatError, read_bdf, read_nastran


def _small_field(card: str, *fields: object) -> str:
    return f"{card:<8}" + "".join(f"{str(field):>8}" for field in fields)


def test_read_free_field_bdf_as_neutral_model(tmp_path: Path) -> None:
    path = tmp_path / "rod.bdf"
    path.write_text(
        """SOL 103
CEND
BEGIN BULK
$ Implicit Nastran exponents are deliberately exercised.
GRID,10,,0.,0.,0.
GRID,20,0,2.5,0.,0. $ inline comment
MAT1,3,2.1+11,,.3,7.85+3
CROD,100,7,10,20
ENDDATA
GRID,999,,9.,9.,9.
""",
        encoding="utf-8",
    )

    model = read_bdf(path)

    assert isinstance(model, NeutralModel)
    np.testing.assert_array_equal(model.node_ids, [10, 20])
    np.testing.assert_allclose(model.nodes, [[0.0, 0.0, 0.0], [2.5, 0.0, 0.0]])
    np.testing.assert_array_equal(model.elements[ElementType.ROD2], [[10, 20]])
    np.testing.assert_array_equal(model.element_property_ids[ElementType.ROD2], [7])
    assert model.properties == {}
    assert model.materials[3].E == pytest.approx(2.1e11)
    assert model.materials[3].nu == pytest.approx(0.3)
    assert model.materials[3].rho == pytest.approx(7850.0)
    assert model.meta["format"] == "nastran-bdf"
    assert model.meta["source"] == str(path)
    assert model.meta["element_ids"] == {"rod2": [100]}


def test_read_small_fixed_field_bdf_and_derive_youngs_modulus() -> None:
    source = StringIO(
        "\n".join(
            [
                _small_field("GRID", 1, "", 0.0, 0.0, 0.0),
                _small_field("GRID", 2, 0, 1.0, 2.0, 3.0),
                _small_field("MAT1", 8, "", "2.7+10", ".3", "2700."),
                _small_field("CROD", 42, 12, 1, 2),
                "ENDDATA",
            ]
        )
    )

    model = read_nastran(source)

    np.testing.assert_allclose(model.nodes[1], [1.0, 2.0, 3.0])
    assert model.materials[8].E == pytest.approx(7.02e10)
    assert model.materials[8].nu == pytest.approx(0.3)
    assert model.materials[8].rho == pytest.approx(2700.0)
    np.testing.assert_array_equal(model.elements[ElementType.ROD2], [[1, 2]])


def test_unsupported_cards_are_ignored() -> None:
    model = read_bdf(
        StringIO(
            """BEGIN BULK
PARAM,POST,-1
GRID,1,,1.,2.,3.
PROD,4,9,0.005
ENDDATA
"""
        )
    )

    assert model.n_nodes == 1
    assert model.n_elements == 0
    assert model.materials == {}


def test_crod_rejects_unknown_grid_reference() -> None:
    source = StringIO("GRID,1,,0.,0.,0.\nCROD,2,3,1,99\n")

    with pytest.raises(FormatError, match="unknown GRID ids: 99"):
        read_bdf(source)


def test_grid_rejects_unresolved_coordinate_system() -> None:
    source = StringIO("GRID,1,17,0.,0.,0.\n")

    with pytest.raises(FormatError, match=r"line 1.*unsupported coordinate system CP=17"):
        read_bdf(source)


def test_malformed_supported_card_reports_card_and_line() -> None:
    source = StringIO("$ comment\nGRID,1,,0.,0.,0.\nMAT1,5,210000.\n")

    with pytest.raises(FormatError, match=r"MAT1 card on line 3.*at least two"):
        read_bdf(source)
