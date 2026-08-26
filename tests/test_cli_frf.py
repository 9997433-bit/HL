"""End-to-end coverage of ``openfemlab correlate-frf``.

The command is the CLI surface over :mod:`openfemlab.correlation.frf`, and the
headline case is the Round-2 exit-bar demo: a measured UFF dataset-58 column
compared against one synthesized from the same damped model, which must
correlate at FRAC = 1. The remaining tests pin the input resolution (UFF versus
JSON/YAML document, model spec versus second measurement), the channel and
frequency-line alignment, and the ``--require-*`` gates CI reads.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from openfemlab.cli.analysis import solve_spec
from openfemlab.cli.commands import correlate_frf
from openfemlab.cli.main import build_parser, main
from openfemlab.cli.spec import SpecError
from openfemlab.core.model import DOF
from openfemlab.io import write_data
from openfemlab.solver.dynamics import RayleighDamping, modal_frf

from ._uff58 import dataset_58

#: Response channels of the synthetic measurement (chain node ids, all UX).
CHANNEL_NODES = (1, 3, 5)

#: Node the synthetic exciter sits on.
EXCITER_NODE = 1

#: Frequency line spanning the chain spectrum without sitting on a resonance.
FREQUENCIES = 0.5 + np.arange(48) * 0.25

#: Rayleigh coefficients of the "measured" data: a few percent over the band.
ALPHA, BETA = 0.02, 0.004

#: The same damping as a spec block, so a synthesis needs no command-line flag.
RAYLEIGH = {"alpha": ALPHA, "beta": BETA}

#: Every mode of the 6-DOF chain, so a matching synthesis is exact.
MODES = 6

#: Budget for a self-correlation carried through the 12-digit UFF interchange.
EXACT = 1.0e-9


def chain_spec(*, stiffness: float = 1000.0, mass: float = 1.0, damping=RAYLEIGH) -> dict:
    """Fixed-fixed spring-mass chain: nodes 1..6 carry the mass, node 0 is ground."""
    spec = {
        "name": "chain",
        "mesh": {
            "type": "chain",
            "num_masses": MODES,
            "stiffness": stiffness,
            "mass": mass,
            "fixed_end": True,
        },
    }
    if damping is not None:
        spec["damping"] = damping
    return spec


def synthesize(spec: dict, *, damping=None, nodes=CHANNEL_NODES) -> np.ndarray:
    """``(n_frequencies, n_channels)`` receptance column of ``spec``."""
    model, result = solve_spec(spec, num_modes=MODES)
    return modal_frf(
        FREQUENCIES,
        result,
        RayleighDamping(alpha=ALPHA, beta=BETA) if damping is None else damping,
        response_dofs=[model.dof_index(node, DOF.UX) for node in nodes],
        excitation_dofs=[model.dof_index(EXCITER_NODE, DOF.UX)],
    ).data[:, :, 0]


def write_uff(path, values: np.ndarray, *, nodes=CHANNEL_NODES, reference_node=EXCITER_NODE):
    """Write one dataset-58 record per response channel."""
    path.write_text(
        "".join(
            dataset_58(
                FREQUENCIES,
                values[:, column],
                response_node=node,
                response_direction=1,
                reference_node=reference_node,
                reference_direction=1,
            )
            for column, node in enumerate(nodes)
        ),
        encoding="utf-8",
    )
    return path


def write_document(path, values: np.ndarray, *, nodes=CHANNEL_NODES, frequencies=FREQUENCIES):
    """Write the JSON form of the same FRF column."""
    write_data(
        {
            "object_type": "frf",
            "response_type": "receptance",
            "frequencies_hz": np.asarray(frequencies, dtype=float).tolist(),
            "excitation": {"node": EXCITER_NODE, "direction": "UX"},
            "channels": [
                {
                    "node": node,
                    "direction": "UX",
                    "real": values[:, column].real.tolist(),
                    "imag": values[:, column].imag.tolist(),
                }
                for column, node in enumerate(nodes)
            ],
        },
        path,
    )
    return path


@pytest.fixture
def measured(tmp_path):
    """The synthetic measurement, as a UFF file, plus its model specification."""
    spec = chain_spec()
    spec_path = tmp_path / "chain.yaml"
    write_data(spec, spec_path)
    return write_uff(tmp_path / "measured.unv", synthesize(spec)), spec_path


def document_of(capsys) -> dict:
    return json.loads(capsys.readouterr().out)


# ------------------------------------------------------------ command surface


def test_the_command_is_registered_with_its_defaults() -> None:
    args = build_parser().parse_args(["correlate-frf", "measured.unv", "chain.yaml"])
    assert args.command == "correlate-frf"
    assert args.func is correlate_frf.run
    assert (args.measured, args.comparison) == ("measured.unv", "chain.yaml")
    assert args.fdac is True
    assert (args.damping, args.rayleigh, args.require_frac) == (None, None, None)


def test_modal_and_frf_correlation_share_the_failure_exit_code() -> None:
    from openfemlab.cli.commands import correlate

    assert correlate_frf.CORRELATION_FAILED == correlate.CORRELATION_FAILED


# ------------------------------------------------------- the exit-bar demo


def test_measured_uff_correlates_perfectly_with_its_own_model(measured, capsys) -> None:
    """A UFF-58 measurement versus the synthesis of the model that produced it."""
    uff, spec = measured
    code = main(
        [
            "--no-color",
            "correlate-frf",
            str(uff),
            str(spec),
            "-n",
            str(MODES),
            "--rayleigh",
            str(ALPHA),
            str(BETA),
            "--format",
            "json",
        ]
    )
    assert code == 0

    report = document_of(capsys)
    assert report["command"] == "correlate-frf"
    assert report["schema_version"] == "1.1"
    assert report["reference"]["excitation"] == "1:UX"
    assert report["comparison"]["kind"] == "synthesized"
    assert report["comparison"]["modes"] == MODES
    assert report["comparison"]["damping"] == {
        "model": "rayleigh",
        "alpha": ALPHA,
        "beta": BETA,
    }

    block = report["frf"]
    assert block["channels"] == ["1:UX", "3:UX", "5:UX"]
    assert block["response_type"] == "receptance"
    assert block["n_frequencies"] == FREQUENCIES.size
    assert block["frac"] == pytest.approx([1.0, 1.0, 1.0], abs=EXACT)
    assert block["min_fdac_diagonal"] == pytest.approx(1.0, abs=EXACT)
    assert np.asarray(block["fdac"]).shape == (FREQUENCIES.size, FREQUENCIES.size)
    assert block["frequencies"] == pytest.approx(FREQUENCIES, rel=EXACT)


def test_a_softened_model_fails_the_frac_gate(measured, capsys, tmp_path) -> None:
    uff, _ = measured
    softened = tmp_path / "softened.yaml"
    write_data(chain_spec(stiffness=600.0), softened)

    code = main(
        [
            "--no-color",
            "correlate-frf",
            str(uff),
            str(softened),
            "-n",
            str(MODES),
            "--require-frac",
            "0.99",
        ]
    )
    captured = capsys.readouterr()
    assert code == correlate_frf.CORRELATION_FAILED
    assert "FRAC" in captured.err


def test_the_fdac_gate_reports_a_suppressed_matrix(measured, capsys) -> None:
    uff, spec = measured
    code = main(
        [
            "--no-color",
            "correlate-frf",
            str(uff),
            str(spec),
            "-n",
            str(MODES),
            "--no-fdac",
            "--require-fdac",
            "0.9",
            "--format",
            "json",
        ]
    )
    captured = capsys.readouterr()
    assert code == correlate_frf.CORRELATION_FAILED
    assert "--no-fdac" in captured.err

    block = json.loads(captured.out)["frf"]
    assert block["fdac"] is None
    assert block["min_fdac_diagonal"] is None
    assert block["frac"] == pytest.approx([1.0, 1.0, 1.0], abs=EXACT)


# --------------------------------------------------------------- input forms


def test_two_frf_documents_correlate_channel_by_channel(tmp_path, capsys) -> None:
    """A second measurement is aligned onto the reference channel order."""
    values = synthesize(chain_spec())
    reference = write_document(tmp_path / "reference.json", values)
    reversed_nodes = tuple(reversed(CHANNEL_NODES))
    comparison = write_document(
        tmp_path / "comparison.json", values[:, ::-1], nodes=reversed_nodes
    )

    assert (
        main(
            ["--no-color", "correlate-frf", str(reference), str(comparison), "--format", "json"]
        )
        == 0
    )
    block = document_of(capsys)["frf"]
    assert block["channels"] == ["1:UX", "3:UX", "5:UX"]
    assert block["frac"] == pytest.approx([1.0, 1.0, 1.0], abs=1e-12)


def test_a_missing_comparison_channel_is_named(tmp_path, capsys) -> None:
    values = synthesize(chain_spec())
    reference = write_document(tmp_path / "reference.json", values)
    comparison = write_document(
        tmp_path / "comparison.json", values[:, :2], nodes=CHANNEL_NODES[:2]
    )

    assert main(["--no-color", "correlate-frf", str(reference), str(comparison)]) == 1
    assert "5:UX" in capsys.readouterr().err


def test_frequency_lines_must_agree(tmp_path, capsys) -> None:
    values = synthesize(chain_spec())
    reference = write_document(tmp_path / "reference.json", values)
    comparison = write_document(
        tmp_path / "comparison.json", values, frequencies=FREQUENCIES + 0.1
    )

    assert main(["--no-color", "correlate-frf", str(reference), str(comparison)]) == 1
    assert "frequency lines" in capsys.readouterr().err


def test_a_channel_outside_the_model_is_named(tmp_path, capsys) -> None:
    spec = chain_spec()
    spec_path = tmp_path / "chain.yaml"
    write_data(spec, spec_path)
    values = synthesize(spec)
    measured = write_document(tmp_path / "measured.json", values, nodes=(1, 3, 99))

    assert main(["--no-color", "correlate-frf", str(measured), str(spec_path), "-n", "6"]) == 1
    assert "99:UX" in capsys.readouterr().err


def test_an_unnamed_exciter_must_be_supplied(tmp_path, capsys) -> None:
    spec = chain_spec()
    spec_path = tmp_path / "chain.yaml"
    write_data(spec, spec_path)
    uff = write_uff(tmp_path / "measured.unv", synthesize(spec), reference_node=0)

    common = ["--no-color", "correlate-frf", str(uff), str(spec_path), "-n", str(MODES)]
    assert main(common) == 1
    assert "--excitation" in capsys.readouterr().err

    assert main([*common, "--excitation", "1:UX", "--format", "json"]) == 0
    assert document_of(capsys)["reference"]["excitation"] == "1:UX"


def test_parse_dof_rejects_a_malformed_reference() -> None:
    assert correlate_frf.parse_dof("12:uz") == (12, DOF.UZ)
    with pytest.raises(SpecError):
        correlate_frf.parse_dof("UZ")
    with pytest.raises(SpecError):
        correlate_frf.parse_dof("tip:UZ")


# ------------------------------------------------------------------- damping


def test_the_spec_damping_block_drives_the_synthesis(measured, capsys) -> None:
    uff, spec = measured
    assert (
        main(
            [
                "--no-color",
                "correlate-frf",
                str(uff),
                str(spec),
                "-n",
                str(MODES),
                "--format",
                "json",
            ]
        )
        == 0
    )
    report = document_of(capsys)
    assert report["comparison"]["damping"] == {
        "model": "rayleigh",
        "alpha": ALPHA,
        "beta": BETA,
        "source": "spec",
    }
    assert report["frf"]["min_frac"] == pytest.approx(1.0, abs=EXACT)


def test_uniform_modal_damping_is_the_fallback(tmp_path, capsys) -> None:
    spec = chain_spec(damping=None)
    spec_path = tmp_path / "chain.yaml"
    write_data(spec, spec_path)
    uff = write_uff(tmp_path / "measured.unv", synthesize(spec, damping=0.01))

    common = ["--no-color", "correlate-frf", str(uff), str(spec_path), "-n", str(MODES)]
    assert main([*common, "--damping", "0.01", "--format", "json"]) == 0
    report = document_of(capsys)
    assert report["comparison"]["damping"] == {"model": "modal", "ratio": 0.01}
    assert report["frf"]["min_frac"] == pytest.approx(1.0, abs=EXACT)

    assert main([*common, "--format", "json"]) == 0
    assert document_of(capsys)["comparison"]["damping"] == {
        "model": "modal",
        "ratio": correlate_frf.DEFAULT_DAMPING,
        "source": "default",
    }


def test_per_mode_damping_ratios_are_read_from_the_spec(tmp_path, capsys) -> None:
    ratios = [0.005 * (index + 1) for index in range(MODES)]
    spec = chain_spec(damping={"ratios": ratios})
    spec_path = tmp_path / "chain.yaml"
    write_data(spec, spec_path)
    uff = write_uff(tmp_path / "measured.unv", synthesize(spec, damping=np.asarray(ratios)))

    assert (
        main(
            [
                "--no-color",
                "correlate-frf",
                str(uff),
                str(spec_path),
                "-n",
                str(MODES),
                "--format",
                "json",
            ]
        )
        == 0
    )
    report = document_of(capsys)
    assert report["comparison"]["damping"]["ratios"] == pytest.approx(ratios)
    assert report["frf"]["min_frac"] == pytest.approx(1.0, abs=EXACT)


# -------------------------------------------------------------- presentation


def test_the_table_renders_channels_and_the_fdac_matrix(measured, capsys) -> None:
    uff, spec = measured
    assert (
        main(["--no-color", "correlate-frf", str(uff), str(spec), "-n", "6", "--matrix"]) == 0
    )
    out = capsys.readouterr().out
    assert "FRF correlation" in out
    assert "1:UX" in out and "5:UX" in out
    assert "mean / min FRAC" in out
    assert "FDAC matrix" in out


def test_the_report_can_be_written_to_a_file(measured, tmp_path) -> None:
    uff, spec = measured
    destination = tmp_path / "frf-correlation.json"
    assert (
        main(
            [
                "--no-color",
                "--quiet",
                "correlate-frf",
                str(uff),
                str(spec),
                "-n",
                "6",
                "--no-fdac",
                "-o",
                str(destination),
            ]
        )
        == 0
    )
    written = json.loads(destination.read_text(encoding="utf-8"))
    assert written["command"] == "correlate-frf"
    assert written["frf"]["channels"] == ["1:UX", "3:UX", "5:UX"]
    assert written["frf"]["min_frac"] == pytest.approx(1.0, abs=EXACT)
