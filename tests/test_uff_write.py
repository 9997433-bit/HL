"""Round-trip coverage for the UFF 55/58 writer."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import numpy as np
import pytest

from openfemlab.io import FormatError, format_uff, read_uff, write_uff
from openfemlab.io.uff import UFFFunction, UFFMode

_ID_LINES = ("synthetic export", "dataset test", "26-AUG-26", "OpenFEMLab", "round trip")


def _mode(*, complex_shape: bool = False) -> UFFMode:
    shape = np.array([[1.0, 0.0, -0.5], [0.25, 2.0, 0.75], [-1.5, 0.125, 3.0]])
    if complex_shape:
        shape = shape + 1j * np.array([[0.5, -0.25, 0.0], [1.0, 0.0, -2.0], [0.75, 3.5, 0.25]])
    return UFFMode(
        frequency_hz=12.5,
        mode_number=3,
        node_ids=np.array([10, 20, 31], dtype=np.int64),
        values=shape,
        load_case=7,
        modal_mass=2.75,
        viscous_damping=0.012,
        hysteretic_damping=0.004,
        id_lines=_ID_LINES,
    )


def _function(
    *,
    frequencies: np.ndarray | None = None,
    values: np.ndarray | None = None,
) -> UFFFunction:
    if frequencies is None:
        frequencies = np.linspace(10.0, 20.0, 5)
    if values is None:
        values = np.array([1.0 - 0.5j, 2.0 + 0.25j, -3.0 + 4.0j, 0.5 + 0.0j, -0.125 - 6.0j])
    return UFFFunction(
        frequencies_hz=frequencies,
        values=values,
        function_id=17,
        load_case=9,
        response_entity="RESP",
        response_node=101,
        response_direction=2,
        reference_entity="REF",
        reference_node=202,
        reference_direction=-1,
        ordinate_label="Receptance",
        ordinate_units="m/N",
        id_lines=_ID_LINES,
    )


def _round_trip(dataset: UFFMode | UFFFunction) -> UFFMode | UFFFunction:
    datasets = read_uff(StringIO(format_uff(dataset)))
    assert len(datasets) == 1
    return datasets[0]


def test_dataset_55_real_mode_round_trips_through_a_file(tmp_path: Path) -> None:
    path = tmp_path / "modes.unv"
    original = _mode()

    write_uff(original, path)
    recovered = read_uff(path)[0]

    assert isinstance(recovered, UFFMode)
    assert recovered.frequency_hz == pytest.approx(original.frequency_hz)
    assert recovered.mode_number == original.mode_number
    assert recovered.load_case == original.load_case
    assert recovered.modal_mass == pytest.approx(original.modal_mass)
    assert recovered.viscous_damping == pytest.approx(original.viscous_damping)
    assert recovered.hysteretic_damping == pytest.approx(original.hysteretic_damping)
    assert recovered.data_characteristic == original.data_characteristic
    assert recovered.specific_data_type == original.specific_data_type
    assert recovered.id_lines == _ID_LINES
    np.testing.assert_array_equal(recovered.node_ids, original.node_ids)
    np.testing.assert_allclose(recovered.mode_shape, original.values, rtol=1e-5)


def test_dataset_55_complex_mode_round_trips() -> None:
    original = _mode(complex_shape=True)

    recovered = _round_trip(original)

    assert isinstance(recovered, UFFMode)
    assert np.iscomplexobj(recovered.values)
    np.testing.assert_allclose(recovered.values, original.values, rtol=1e-5)


def test_dataset_58_even_complex_function_round_trips_through_a_file(tmp_path: Path) -> None:
    path = tmp_path / "frf.unv"
    original = _function()

    write_uff([original], path)
    recovered = read_uff(path)[0]

    assert isinstance(recovered, UFFFunction)
    assert recovered.function_type == 4
    assert recovered.function_id == 17
    assert recovered.load_case == 9
    assert recovered.response_entity == "RESP"
    assert recovered.response_node == 101
    assert recovered.response_direction == 2
    assert recovered.reference_entity == "REF"
    assert recovered.reference_node == 202
    assert recovered.reference_direction == -1
    assert recovered.abscissa_label == "Frequency"
    assert recovered.abscissa_units == "Hz"
    assert recovered.ordinate_label == "Receptance"
    assert recovered.ordinate_units == "m/N"
    assert recovered.id_lines == _ID_LINES
    np.testing.assert_allclose(recovered.frequencies_hz, original.frequencies_hz)
    np.testing.assert_allclose(recovered.values, original.values)


def test_dataset_58_real_ordinates_round_trip() -> None:
    original = _function(values=np.array([1.0, -2.5, 3.25, 0.0, 7.5]))

    recovered = _round_trip(original)

    assert isinstance(recovered, UFFFunction)
    assert not np.iscomplexobj(recovered.values)
    np.testing.assert_allclose(recovered.values, original.values)
    np.testing.assert_allclose(recovered.frequencies_hz, original.frequencies_hz)


def test_evenly_spaced_abscissa_uses_the_compact_header() -> None:
    text = format_uff(_function())

    data_form = text.splitlines()[8]

    assert data_form.split()[:3] == ["6", "5", "1"]


def test_irregular_abscissa_falls_back_to_explicit_values() -> None:
    frequencies = np.array([1.0, 2.0, 4.0, 8.0, 16.0])
    original = _function(frequencies=frequencies)

    text = format_uff(original)
    recovered = read_uff(StringIO(text))[0]

    assert text.splitlines()[8].split()[:3] == ["6", "5", "0"]
    assert isinstance(recovered, UFFFunction)
    np.testing.assert_allclose(recovered.frequencies_hz, frequencies)
    np.testing.assert_allclose(recovered.values, original.values)


def test_single_point_function_round_trips() -> None:
    original = _function(frequencies=np.array([42.0]), values=np.array([1.5 - 2.5j]))

    recovered = _round_trip(original)

    assert isinstance(recovered, UFFFunction)
    np.testing.assert_allclose(recovered.frequencies_hz, [42.0])
    np.testing.assert_allclose(recovered.values, [1.5 - 2.5j])


def test_mixed_datasets_keep_their_order_and_records_stay_within_80_columns() -> None:
    stream = StringIO()

    write_uff([_mode(), _function(), _mode(complex_shape=True)], stream)
    text = stream.getvalue()
    datasets = read_uff(StringIO(text))

    assert [type(dataset) for dataset in datasets] == [UFFMode, UFFFunction, UFFMode]
    assert text.count("    -1\n") == 6
    assert max(len(line) for line in text.splitlines()) <= 80


def test_written_datasets_use_the_documented_default_header_fields() -> None:
    minimal = UFFMode(
        frequency_hz=5.0,
        mode_number=1,
        node_ids=np.array([1]),
        values=np.array([[1.0, 2.0, 3.0]]),
    )

    recovered = _round_trip(minimal)

    assert isinstance(recovered, UFFMode)
    assert recovered.load_case == 0
    assert recovered.data_characteristic == 2
    assert recovered.specific_data_type == 8
    assert recovered.id_lines == ("NONE",) * 5


def test_format_uff_returns_an_empty_document_for_no_datasets() -> None:
    assert format_uff([]) == ""


def test_write_rejects_a_non_uff_object() -> None:
    with pytest.raises(FormatError, match="cannot write int as a UFF dataset"):
        format_uff([_mode(), 55])  # type: ignore[list-item]


def test_write_rejects_duplicate_node_numbers() -> None:
    mode = UFFMode(
        frequency_hz=1.0,
        mode_number=1,
        node_ids=np.array([7, 7]),
        values=np.ones((2, 3)),
    )

    with pytest.raises(FormatError, match="dataset 55.*duplicate node numbers"):
        format_uff(mode)


def test_write_rejects_a_node_count_that_disagrees_with_the_values() -> None:
    mode = UFFMode(
        frequency_hz=1.0,
        mode_number=1,
        node_ids=np.array([1, 2, 3]),
        values=np.ones((2, 3)),
    )

    with pytest.raises(FormatError, match="3 node numbers for 2 rows of values"):
        format_uff(mode)


def test_write_rejects_non_finite_mode_shape_values() -> None:
    mode = UFFMode(
        frequency_hz=1.0,
        mode_number=1,
        node_ids=np.array([1]),
        values=np.array([[1.0, np.nan, 0.0]]),
    )

    with pytest.raises(FormatError, match="mode-shape values contain non-finite entries"):
        format_uff(mode)


def test_write_rejects_an_abscissa_that_does_not_match_the_ordinates() -> None:
    function = UFFFunction(
        frequencies_hz=np.array([1.0, 2.0, 3.0]),
        values=np.array([1.0, 2.0]),
    )

    with pytest.raises(FormatError, match="3 abscissa values for 2 ordinate values"):
        format_uff(function)


def test_write_rejects_an_empty_function() -> None:
    function = UFFFunction(frequencies_hz=np.array([]), values=np.array([]))

    with pytest.raises(FormatError, match="requires at least one data point"):
        format_uff(function)


def test_write_rejects_an_entity_name_that_overflows_its_field() -> None:
    function = _function()
    overlong = UFFFunction(
        frequencies_hz=function.frequencies_hz,
        values=function.values,
        response_entity="A" * 11,
    )

    with pytest.raises(FormatError, match="response entity .* exceeds the 10-character field"):
        format_uff(overlong)


def test_write_rejects_a_free_text_record_that_looks_like_a_delimiter() -> None:
    mode = UFFMode(
        frequency_hz=1.0,
        mode_number=1,
        node_ids=np.array([1]),
        values=np.ones((1, 3)),
        id_lines=("first", "  -1  ", "third", "fourth", "fifth"),
    )

    with pytest.raises(FormatError, match="cannot be the -1 block delimiter"):
        format_uff(mode)


def test_write_reports_the_position_of_the_offending_dataset() -> None:
    broken = UFFMode(
        frequency_hz=-1.0,
        mode_number=1,
        node_ids=np.array([1]),
        values=np.ones((1, 3)),
    )

    with pytest.raises(FormatError, match="dataset 55 at position 1: frequency must be finite"):
        format_uff([_function(), broken])


def test_write_reports_an_unwritable_destination(tmp_path: Path) -> None:
    with pytest.raises(FormatError, match="cannot write UFF file"):
        write_uff(_mode(), tmp_path / "missing" / "modes.unv")
