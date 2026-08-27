"""Regression coverage for the CLI-to-correlation kernel seam."""

from __future__ import annotations

from io import StringIO
from types import SimpleNamespace

import numpy as np

from openfemlab.cli.commands import correlate
from openfemlab.cli.console import Reporter


def test_correlate_command_delegates_to_public_kernel(monkeypatch) -> None:
    modal_data = SimpleNamespace(
        frequencies=np.array([10.0]),
        dof_map=SimpleNamespace(ndof=1),
    )
    summary = SimpleNamespace(
        n_paired=1,
        min_mac=1.0,
        max_abs_freq_error_pct=0.0,
    )
    correlation = SimpleNamespace(
        summary=summary,
        to_dict=lambda: {"summary": {"n_paired": 1}},
    )
    calls = []

    def canonical_kernel(fe, test, **settings):
        calls.append((fe, test, settings))
        return correlation

    monkeypatch.setattr(correlate, "load_fe_modes", lambda source, num_modes: modal_data)
    monkeypatch.setattr("openfemlab.io.read_test_data", lambda source: modal_data)
    monkeypatch.setattr("openfemlab.correlation.correlate_modal_data", canonical_kernel)

    args = SimpleNamespace(
        fe="fe.yaml",
        test="test.yaml",
        modes=4,
        partial_dofs=False,
        pairing="optimal",
        mac_threshold=0.8,
        frequency_tolerance=2.0,
        freq_penalty=0.1,
        format="json",
        output=None,
        require_mac=None,
        require_frequency=None,
    )

    assert correlate.run(args, Reporter(StringIO(), color=False)) == 0
    assert calls == [
        (
            modal_data,
            modal_data,
            {
                "strict": True,
                "method": "optimal",
                "mac_threshold": 0.8,
                "frequency_tolerance_pct": 2.0,
                "freq_penalty": 0.1,
            },
        )
    ]
