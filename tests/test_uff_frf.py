"""Tests for UFF FRF bridge and MPE CLI."""

from __future__ import annotations

import numpy as np

from openfemlab.io.uff import UFFFunction
from openfemlab.io.uff_frf import uff_function_to_frf, uff_functions_to_frf


def test_uff_function_to_frf_contract():
    frequencies = np.linspace(10.0, 100.0, 5)
    values = 1.0 / (1.0 + 1j * frequencies)
    function = UFFFunction(frequencies_hz=frequencies, values=values)
    frf = uff_function_to_frf(function)
    assert frf.num_frequencies == frequencies.size
    assert frf.num_response_dofs == 1
    np.testing.assert_allclose(frf.data[:, 0, 0], values)


def test_uff_functions_stack():
    frequencies = np.linspace(10.0, 100.0, 4)
    first = UFFFunction(frequencies_hz=frequencies, values=np.ones(4))
    second = UFFFunction(frequencies_hz=frequencies, values=2 * np.ones(4))
    frf = uff_functions_to_frf([first, second], response_dofs=(3, 7))
    assert frf.num_response_dofs == 2
    assert frf.response_dofs.tolist() == [3, 7]
