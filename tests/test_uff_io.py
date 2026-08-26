"""Synthetic coverage for the minimal UFF 55/58 reader."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import numpy as np
import pytest

from openfemlab.io import FormatError
from openfemlab.io.uff import UFFFunction, UFFMode, read_uff, read_uff_functions, read_uff_modes


def _block(dataset_number: int, records: list[str]) -> str:
    return "\n".join(["    -1", f"{dataset_number:6d}", *records, "    -1", ""])


def _mode_55() -> str:
    records = [
        "synthetic mode",
        "dataset 55",
        "26-AUG-26",
        "OpenFEMLab",
        "normal mode",
        f"{1:10d}{2:10d}{2:10d}{8:10d}{2:10d}{3:10d}",
        f"{2:10d}{4:10d}{7:10d}{3:10d}",
        "".join(f"{value:13.5E}" for value in (12.5, 2.75, 0.012, 0.0)),
        f"{10:10d}",
        "".join(f"{value:13.5E}" for value in (1.0, 0.0, -0.5)),
        f"{20:10d}",
        "".join(f"{value:13.5E}" for value in (0.25, 2.0, 0.75)),
    ]
    return _block(55, records)


def _function_58(*, spacing: int = 1) -> str:
    identification = (
        f"{4:5d}{17:10d}{1:5d}{9:10d} "
        f"{'RESP':>10}{101:10d}{2:4d} "
        f"{'REF':>10}{202:10d}{-1:4d}"
    )
    axis = f"{18:10d}{0:5d}{0:5d}{0:5d} {'Frequency':<20} {'Hz':<20}"
    other_axis = f"{0:10d}{0:5d}{0:5d}{0:5d} {'NONE':<20} {'NONE':<20}"
    if spacing:
        data_form = f"{6:10d}{3:10d}{1:10d}{10.0:13.5E}{2.5:13.5E}{0.0:13.5E}"
        raw = (1.0, -0.5, 2.0, 0.25, -3.0, 4.0)
    else:
        data_form = f"{4:10d}{2:10d}{0:10d}{0.0:13.5E}{0.0:13.5E}{0.0:13.5E}"
        raw = (3.0, 10.0, 7.5, -2.0)
    records = [
        "synthetic FRF",
        "dataset 58",
        "26-AUG-26",
        "OpenFEMLab",
        "frequency response",
        identification,
        data_form,
        axis,
        other_axis,
        other_axis,
        other_axis,
        " ".join(f"{value:.12E}" for value in raw),
    ]
    return _block(58, records)


def test_read_dataset_55_normal_mode(tmp_path: Path) -> None:
    path = tmp_path / "mode.unv"
    path.write_text(_mode_55(), encoding="utf-8")

    modes = read_uff_modes(path)

    assert len(modes) == 1
    mode = modes[0]
    assert isinstance(mode, UFFMode)
    assert mode.frequency_hz == pytest.approx(12.5)
    assert mode.mode_number == 3
    assert mode.load_case == 7
    assert mode.modal_mass == pytest.approx(2.75)
    assert mode.viscous_damping == pytest.approx(0.012)
    np.testing.assert_array_equal(mode.node_ids, [10, 20])
    np.testing.assert_allclose(mode.mode_shape, [[1.0, 0.0, -0.5], [0.25, 2.0, 0.75]])


def test_read_dataset_58_even_complex_frequency_response() -> None:
    functions = read_uff_functions(StringIO(_function_58()))

    assert len(functions) == 1
    function = functions[0]
    assert isinstance(function, UFFFunction)
    assert function.function_type == 4
    assert function.response_node == 101
    assert function.response_direction == 2
    assert function.reference_node == 202
    assert function.reference_direction == -1
    assert function.abscissa_label == "Frequency"
    assert function.abscissa_units == "Hz"
    np.testing.assert_allclose(function.frequencies_hz, [10.0, 12.5, 15.0])
    np.testing.assert_allclose(function.values, [1.0 - 0.5j, 2.0 + 0.25j, -3.0 + 4.0j])


def test_read_dataset_58_uneven_real_abscissa_and_mixed_file() -> None:
    unknown = _block(151, ["ignored model header"])
    datasets = read_uff(StringIO(unknown + _mode_55() + _function_58(spacing=0)))

    assert [type(dataset) for dataset in datasets] == [UFFMode, UFFFunction]
    function = datasets[1]
    assert isinstance(function, UFFFunction)
    np.testing.assert_allclose(function.x, [3.0, 7.5])
    np.testing.assert_allclose(function.data, [10.0, -2.0])


def test_dataset_58_rejects_incomplete_data_record() -> None:
    malformed = _function_58().replace(
        "1.000000000000E+00 -5.000000000000E-01", "1.000000000000E+00"
    )

    with pytest.raises(FormatError, match="dataset 58.*requires 6 numeric values"):
        read_uff(StringIO(malformed))


def test_binary_dataset_58_is_reported_as_unsupported() -> None:
    source = StringIO("    -1\n    58b     1\n")

    with pytest.raises(FormatError, match="58b is not supported"):
        read_uff(source)
