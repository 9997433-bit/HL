"""Coverage for the shell, solid and bar cards of the Nastran BDF reader.

The ``GRID``/``CROD``/``MAT1`` core the reader started from is exercised in
``tests/test_nastran_io.py``; this module covers the cards layered on top of it
-- ``CQUAD4``, ``CTETRA``, ``CHEXA``, ``CBAR``, ``PSHELL`` and ``PSOLID`` --
together with the continuation-line handling a ``CHEXA`` forces on the reader.
"""

from __future__ import annotations

from io import StringIO

import numpy as np
import pytest

from openfemlab.core.elements import Hex8Element, Quad4Element, Tet4Element
from openfemlab.core.model import Material, Section
from openfemlab.core.neutral import ElementType
from openfemlab.io import FormatError, neutral_to_model, read_bdf, read_nastran

#: Unit cube, grids 1-4 on ``z=0`` counter-clockwise and 5-8 above them in the
#: same order, which is both the CHEXA and the :class:`Hex8Element` ordering.
#: Grid 9 sits off the cube so a bar and a rod have somewhere to go.
_GRIDS = [
    "GRID,1,,0.,0.,0.",
    "GRID,2,,1.,0.,0.",
    "GRID,3,,1.,1.,0.",
    "GRID,4,,0.,1.,0.",
    "GRID,5,,0.,0.,1.",
    "GRID,6,,1.,0.,1.",
    "GRID,7,,1.,1.,1.",
    "GRID,8,,0.,1.,1.",
    "GRID,9,,0.,0.,2.",
]

_STEEL = "MAT1,1,2.1+11,,.3,7850."


def bdf(*lines: str) -> StringIO:
    """One BDF deck per line, so a card's reported line number is its index."""

    return StringIO("\n".join(lines) + "\n")


def small_field(card: str, *fields: object) -> str:
    return f"{card:<8}" + "".join(f"{field!s:>8}" for field in fields)


def test_read_every_supported_block_from_one_deck() -> None:
    model = read_bdf(
        bdf(
            *_GRIDS,
            _STEEL,
            "PSHELL,10,1,0.0025",
            "PSOLID,20,1",
            "CQUAD4,100,10,1,2,3,4",
            "CTETRA,200,20,1,2,3,5",
            "CHEXA,300,20,1,2,3,4,5,6",
            ",7,8",
            "CBAR,400,30,5,9,0.,1.,0.",
            "CROD,500,40,1,9",
            "ENDDATA",
        )
    )

    np.testing.assert_array_equal(model.elements[ElementType.QUAD4], [[1, 2, 3, 4]])
    np.testing.assert_array_equal(model.elements[ElementType.TET4], [[1, 2, 3, 5]])
    np.testing.assert_array_equal(
        model.elements[ElementType.HEX8], [[1, 2, 3, 4, 5, 6, 7, 8]]
    )
    np.testing.assert_array_equal(model.elements[ElementType.BEAM2], [[5, 9]])
    np.testing.assert_array_equal(model.elements[ElementType.ROD2], [[1, 9]])

    np.testing.assert_array_equal(model.element_property_ids[ElementType.QUAD4], [10])
    np.testing.assert_array_equal(model.element_property_ids[ElementType.TET4], [20])
    np.testing.assert_array_equal(model.element_property_ids[ElementType.HEX8], [20])
    np.testing.assert_array_equal(model.element_property_ids[ElementType.BEAM2], [30])
    np.testing.assert_array_equal(model.element_property_ids[ElementType.ROD2], [40])

    assert model.n_elements == 5
    assert model.meta["element_ids"] == {
        "rod2": [500],
        "beam2": [400],
        "quad4": [100],
        "tet4": [200],
        "hex8": [300],
    }


def test_pshell_and_psolid_land_in_the_property_table() -> None:
    model = read_bdf(
        bdf(
            *_GRIDS[:4],
            "MAT1,7,7.+10,,.33,2700.",
            "PSHELL,10,7,0.0025,7,,7",
            "PSOLID,20,7,0,THREE,GRID,FULL,SMECH",
            "CQUAD4,1,10,1,2,3,4",
        )
    )

    shell = model.properties[10]
    assert shell.material_id == 7
    assert shell.name == "PSHELL"
    assert shell.values == pytest.approx({"t": 0.0025})

    solid = model.properties[20]
    assert solid.material_id == 7
    assert solid.name == "PSOLID"
    assert solid.values == {}


def test_pshell_thickness_reaches_the_bound_quad() -> None:
    neutral = read_bdf(
        bdf(
            *_GRIDS[:4],
            "MAT1,7,7.+10,,.33,2700.",
            "PSHELL,10,7,0.003",
            "CQUAD4,44,10,1,2,3,4",
        )
    )

    # thickness= is the fallback for an unresolved property; PSHELL must win.
    element = neutral_to_model(neutral, thickness=1.0).elements[0]

    assert isinstance(element, Quad4Element)
    assert element.thickness == pytest.approx(0.003)
    assert element.material.E == pytest.approx(7.0e10)
    assert element.id == 44


def test_psolid_material_reaches_the_bound_solids() -> None:
    neutral = read_bdf(
        bdf(
            *_GRIDS,
            "MAT1,7,7.+10,,.33,2700.",
            "PSOLID,20,7",
            "CTETRA,11,20,1,2,3,5",
            "CHEXA,12,20,1,2,3,4,5,6,7,8",
        )
    )

    elements = neutral_to_model(neutral).elements

    assert [type(element) for element in elements] == [Tet4Element, Hex8Element]
    for element in elements:
        assert element.material.E == pytest.approx(7.0e10)
        assert element.material.density == pytest.approx(2700.0)
    assert [element.id for element in elements] == [11, 12]


def test_cbar_becomes_a_beam2_needing_a_section_because_pbar_is_out_of_subset() -> None:
    neutral = read_bdf(bdf(*_GRIDS[:2], _STEEL, "CBAR,1,30,1,2,0.,0.,1."))
    steel = Material(E=2.1e11, density=7850.0, nu=0.3)

    assert neutral.properties == {}
    with pytest.raises(FormatError, match="beam2 property 30 defines no cross-section"):
        neutral_to_model(neutral, material=steel)

    model = neutral_to_model(
        neutral,
        material=steel,
        section=Section(area=1e-4, inertia_z=1e-8, inertia_y=1e-8, torsion_constant=2e-8),
    )

    assert model.elements[0].node_ids == (1, 2)
    assert model.elements[0].id == 1


def test_cbar_orientation_fields_are_not_connectivity() -> None:
    """``X1``/``X2``/``X3`` -- or a ``G0`` grid -- sit where a third node would."""

    model = read_bdf(bdf(*_GRIDS[:3], "CBAR,1,2,1,2,0.,0.,1.,GGG", "CBAR,2,2,2,3,3"))

    np.testing.assert_array_equal(model.elements[ElementType.BEAM2], [[1, 2], [2, 3]])
    assert model.meta["element_ids"]["beam2"] == [1, 2]


def test_cquad4_theta_and_zoffs_are_not_connectivity() -> None:
    model = read_bdf(bdf(*_GRIDS[:4], "CQUAD4,1,2,1,2,3,4,30.,0.5"))

    np.testing.assert_array_equal(model.elements[ElementType.QUAD4], [[1, 2, 3, 4]])


def test_chexa_continuation_in_small_fixed_field() -> None:
    cube = [
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (1.0, 1.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
        (1.0, 0.0, 1.0),
        (1.0, 1.0, 1.0),
        (0.0, 1.0, 1.0),
    ]
    model = read_nastran(
        bdf(
            *(
                small_field("GRID", index, "", *corner)
                for index, corner in enumerate(cube, start=1)
            ),
            small_field("PSOLID", 20, 1),
            small_field("CHEXA", 7, 20, 1, 2, 3, 4, 5, 6) + "+HEX",
            small_field("+HEX", 7, 8),
            "ENDDATA",
        )
    )

    np.testing.assert_array_equal(
        model.elements[ElementType.HEX8], [[1, 2, 3, 4, 5, 6, 7, 8]]
    )
    assert model.meta["element_ids"] == {"hex8": [7]}


def test_chexa_continuation_with_a_blank_marker_field() -> None:
    model = read_bdf(
        bdf(
            *(
                small_field("GRID", index, "", float(index), 0.0, 0.0)
                for index in range(1, 9)
            ),
            small_field("CHEXA", 7, 20, 1, 2, 3, 4, 5, 6),
            small_field("", 7, 8),
        )
    )

    np.testing.assert_array_equal(
        model.elements[ElementType.HEX8], [[1, 2, 3, 4, 5, 6, 7, 8]]
    )


def test_continuation_of_a_skipped_card_does_not_leak_into_the_next_card() -> None:
    model = read_bdf(
        bdf(
            *_GRIDS[:4],
            "PBEAM,3,1,1.-4,1.-8,1.-8,,2.-8",
            ",0.,0.,0.,1.",
            "CQUAD4,1,10,1,2,3,4",
        )
    )

    np.testing.assert_array_equal(model.elements[ElementType.QUAD4], [[1, 2, 3, 4]])
    assert model.properties == {}


def test_orphan_continuation_before_any_card_is_ignored() -> None:
    model = read_bdf(bdf(",1,2,3", "GRID,1,,0.,0.,0."))

    assert model.n_nodes == 1
    assert model.n_elements == 0


@pytest.mark.parametrize(
    ("card", "expected"),
    [
        ("CTETRA,1,20,1,2,3,5,6,7,8,9,2,3", "CTETRA 1 has more than 4 grid points"),
        (
            "CHEXA,1,20,1,2,3,4,5,6,7,8,9,2,3,4,5,6,7,8,9,3,4",
            "CHEXA 1 has more than 8 grid points",
        ),
    ],
)
def test_higher_order_solids_are_rejected_rather_than_truncated(
    card: str, expected: str
) -> None:
    with pytest.raises(FormatError, match=expected):
        read_bdf(bdf(*_GRIDS, card))


@pytest.mark.parametrize(
    ("card", "expected"),
    [
        ("CQUAD4,1,10,1,2,3,3", "CQUAD4 1 must reference 4 distinct GRID ids"),
        ("CTETRA,1,20,1,2,3,1", "CTETRA 1 must reference 4 distinct GRID ids"),
        ("CHEXA,1,20,1,2,3,4,5,6,7,1", "CHEXA 1 must reference 8 distinct GRID ids"),
        ("CBAR,1,30,4,4,0.,0.,1.", "CBAR 1 must reference 2 distinct GRID ids"),
    ],
)
def test_degenerate_connectivity_is_rejected(card: str, expected: str) -> None:
    with pytest.raises(FormatError, match=expected):
        read_bdf(bdf(*_GRIDS, card))


def test_solid_connectivity_reports_every_unknown_grid() -> None:
    with pytest.raises(FormatError, match=r"unknown GRID ids: 77, 88"):
        read_bdf(bdf(*_GRIDS[:6], "CHEXA,1,20,1,2,3,4,5,6", ",88,77"))


def test_duplicate_element_id_across_two_card_kinds_is_rejected() -> None:
    with pytest.raises(
        FormatError,
        match=r"CQUAD4 card on line 11: duplicate element id 5, already defined by a CROD card",
    ):
        read_bdf(bdf(*_GRIDS, "CROD,5,40,1,2", "CQUAD4,5,10,1,2,3,4"))


def test_duplicate_property_id_is_rejected() -> None:
    with pytest.raises(FormatError, match=r"PSOLID card on line 2: duplicate property id 10"):
        read_bdf(bdf("PSHELL,10,1,0.002", "PSOLID,10,1"))


@pytest.mark.parametrize(
    ("card", "expected"),
    [
        ("PSHELL,10,1", "missing required T field"),
        ("PSHELL,10,1,0.", "PSHELL T must be positive"),
        ("PSHELL,10,1,-0.002", "PSHELL T must be positive"),
        ("PSHELL,10,0,0.002", "PSHELL MID1 must be positive"),
        ("PSOLID,20", "missing required MID field"),
        ("CQUAD4,1,10,1,2,3", "missing required G4 field"),
        ("CTETRA,1,20,1,2,3,x", "CTETRA G4 is not a valid number"),
    ],
)
def test_malformed_cards_are_rejected(card: str, expected: str) -> None:
    with pytest.raises(FormatError, match=expected):
        read_bdf(bdf(*_GRIDS, card))


def test_missing_grid_field_reports_the_card_and_its_first_line() -> None:
    with pytest.raises(
        FormatError, match=r"CHEXA card on line 10: missing required G8 field"
    ):
        read_bdf(bdf(*_GRIDS, "CHEXA,1,20,1,2,3,4,5,6", ",7"))


def test_large_field_shell_card_is_rejected() -> None:
    with pytest.raises(FormatError, match=r"CQUAD4\* card on line 1.*large-field"):
        read_bdf(bdf("CQUAD4*,1,10,1,2"))


def test_blocks_come_out_in_a_stable_order_whatever_the_deck_order() -> None:
    cards = ["CHEXA,3,20,1,2,3,4,5,6,7,8", "CQUAD4,2,10,1,2,3,4", "CROD,1,40,1,9"]
    expected = [ElementType.ROD2, ElementType.QUAD4, ElementType.HEX8]

    first = read_bdf(bdf(*_GRIDS, *cards))
    second = read_bdf(bdf(*_GRIDS, *reversed(cards)))

    assert list(first.elements) == expected
    assert list(second.elements) == expected
    assert first.meta["element_ids"] == second.meta["element_ids"]
