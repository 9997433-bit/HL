"""``openfemlab update``: the MAP estimator and the σ_post its report carries.

The command has two estimators behind one interface. Without a ``prior`` or a
``noise`` section it is the deterministic Levenberg-Marquardt loop; with either
of them it is the MS-3.5 maximum-a-posteriori loop, and the emitted document
grows a ``bayesian`` block holding the resolved prior, the noise model and the
Laplace posterior. What is checked here is the *document*: which keys appear
for which configuration, that the three ways of writing a covariance agree,
that the posterior contracts against the prior it was given (AC-UPD-006b seen
from the CLI), and that every malformed block is refused with a message naming
the offending key rather than a traceback.
"""

from __future__ import annotations

import json
from itertools import count
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from openfemlab.cli.main import main
from openfemlab.core.dofs import DofMap, DofType
from openfemlab.core.results import TestData as ModalTestData
from openfemlab.io import write_data, write_test_data
from openfemlab.solver.modal import ModalSolver

# A short steel strip: enough modes to identify two parameters, small enough
# that a dozen updating runs stay cheap.
CANTILEVER: dict[str, Any] = {
    "name": "steel cantilever",
    "materials": {"steel": {"E": 2.1e11, "density": 7850.0, "nu": 0.3}},
    "sections": {"strip": {"area": 1.0e-4, "inertia_z": 8.3333333e-10}},
    "mesh": {
        "type": "beam",
        "length": 1.0,
        "num_elements": 8,
        "support": "cantilever",
        "material": "steel",
        "section": "strip",
    },
}

SENSOR_NODES = (2, 4, 6, 8)
NUM_MODES = 3

#: The structure the synthetic measurement is taken on: 12% softer, 5% heavier.
TRUTH = {"materials.steel.E": 0.88, "sections.strip.area": 1.05}


@pytest.fixture(scope="module")
def fixtures(tmp_path_factory) -> dict[str, Path]:
    """The model specification and the measured mode set every run reads."""
    from openfemlab.cli.analysis import dof_map_of
    from openfemlab.cli.spec import build_model, scaled

    directory = tmp_path_factory.mktemp("cli-update")
    model_file = directory / "cantilever.yaml"
    write_data(CANTILEVER, model_file)

    model = build_model(scaled(CANTILEVER, TRUTH))
    solved = ModalSolver(model).solve(num_modes=NUM_MODES)
    rows = [dof_map_of(model).index_of(node, DofType.UY) for node in SENSOR_NODES]
    test_file = directory / "measured.yaml"
    write_test_data(
        ModalTestData(
            frequencies=solved.frequencies,
            shapes=solved.mode_shapes[rows, :],
            dof_map=DofMap(SENSOR_NODES, [int(DofType.UY)] * len(SENSOR_NODES)),
        ),
        test_file,
    )
    return {"model": model_file, "test": test_file}


def config_for(fixtures: dict[str, Path], **sections: Any) -> dict[str, Any]:
    """The base updating configuration plus whatever sections a test adds."""
    return {
        "model": str(fixtures["model"]),
        "parameters": [
            {"name": "stiffness", "target": "materials.steel.E", "lower": 0.6, "upper": 1.5},
            {
                "name": "mass",
                "target": "sections.strip.area",
                "lower": 0.8,
                "upper": 1.3,
                "kind": "mass",
            },
        ],
        "target": {"file": str(fixtures["test"])},
        "modes": NUM_MODES,
        "partial_dofs": True,
        "options": {"max_iterations": 20, "shape_weight": 0.0},
        **sections,
    }


_RUNS = count()


def run_update(config: dict[str, Any], directory: Path) -> dict[str, Any]:
    """Run one update and return the report, read back from ``--report``.

    Going through the file rather than stdout keeps the helper usable from
    module-scoped fixtures, where ``capsys`` is not available.
    """
    stem = f"run-{next(_RUNS):02d}"
    config_path = directory / f"{stem}.yaml"
    report_path = directory / f"{stem}.json"
    write_data(config, config_path)
    exit_code = main(
        ["--no-color", "--quiet", "update", str(config_path), "--report", str(report_path)]
    )
    assert exit_code == 0
    return json.loads(report_path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def reports(fixtures, tmp_path_factory) -> dict[str, dict[str, Any]]:
    """One run per estimator configuration, shared by the read-only assertions."""
    directory = tmp_path_factory.mktemp("cli-update-reports")
    variants = {
        "deterministic": {},
        "prior": {"prior": {"std": 0.05}},
        "noise": {"noise": {"std": 0.01}},
        "both": {
            "prior": {"std": {"stiffness": 0.05, "mass": 0.02}},
            "noise": {"std": 0.002},
        },
    }
    return {
        label: run_update(config_for(fixtures, **sections), directory)
        for label, sections in variants.items()
    }


def sigmas(report: dict[str, Any], key: str) -> dict[str, float | None]:
    return {entry["name"]: entry[key] for entry in report["parameters"]}


# --------------------------------------------------------------- the document


def test_a_deterministic_run_reports_no_bayesian_block(reports) -> None:
    report = reports["deterministic"]
    assert report["analysis"]["estimator"] == "least-squares"
    assert report["bayesian"] is None
    # σ_post still gets a number: the least-squares covariance the
    # CorrectionReport falls back to when no prior and no C_e were given.
    posterior = sigmas(report, "sigma_post")
    assert posterior.keys() == {"stiffness", "mass"}
    assert all(value >= 0.0 and np.isfinite(value) for value in posterior.values())
    assert set(sigmas(report, "sigma_prior").values()) == {None}


def test_a_prior_switches_the_command_to_the_map_estimator(reports) -> None:
    report = reports["prior"]
    assert report["analysis"]["estimator"] == "map"
    prior = report["bayesian"]["prior"]
    assert prior["given_as"] == "std"
    assert prior["space"] == "design"
    assert prior["names"] == ["stiffness", "mass"]
    assert prior["std"] == pytest.approx([0.05, 0.05])
    np.testing.assert_allclose(prior["covariance"], [[0.0025, 0.0], [0.0, 0.0025]])
    assert report["bayesian"]["noise"] is None


def test_a_noise_block_is_echoed_over_the_residual_space(reports) -> None:
    noise = reports["both"]["bayesian"]["noise"]
    assert noise == {"given_as": "std", "space": "residual", "std": pytest.approx(0.002)}


def test_an_absent_prior_mean_reports_the_starting_point(reports) -> None:
    # The prior is anchored on the run's starting point when the config does
    # not say otherwise, and for scaling factors that point is 1.0.
    assert reports["prior"]["bayesian"]["prior"]["mean"] == pytest.approx([1.0, 1.0])


def test_the_posterior_block_agrees_with_the_parameter_entries(reports) -> None:
    report = reports["both"]
    posterior = report["bayesian"]["posterior"]
    assert posterior["space"] == "design"
    assert posterior["names"] == ["stiffness", "mass"]
    assert posterior["mean"] == pytest.approx(
        [entry["factor"] for entry in report["parameters"]]
    )
    assert posterior["sigma_post"] == pytest.approx(
        list(sigmas(report, "sigma_post").values())
    )
    assert posterior["sigma_prior"] == pytest.approx(
        list(sigmas(report, "sigma_prior").values())
    )
    # σ_post is the square root of the posterior covariance diagonal.
    diagonal = np.diag(np.asarray(posterior["covariance"], dtype=float))
    assert posterior["sigma_post"] == pytest.approx(np.sqrt(diagonal))


def test_the_posterior_contracts_relative_to_the_prior(reports) -> None:
    """AC-UPD-006b seen from the CLI: a prior can only ever shrink σ."""
    report = reports["both"]
    post = sigmas(report, "sigma_post")
    prior = sigmas(report, "sigma_prior")
    assert post.keys() == prior.keys()
    for name in post:
        assert post[name] <= prior[name] + 1.0e-12, name


def test_a_noise_only_configuration_leaves_the_prior_uninformative(reports) -> None:
    report = reports["noise"]
    assert report["analysis"]["estimator"] == "map"
    assert report["bayesian"]["prior"] is None
    assert report["bayesian"]["noise"]["given_as"] == "std"
    # An improper flat prior has an infinite σ, which has no JSON spelling.
    assert set(sigmas(report, "sigma_prior").values()) == {None}
    assert report["bayesian"]["posterior"]["sigma_prior"] == [None, None]
    assert all(value > 0.0 for value in sigmas(report, "sigma_post").values())


@pytest.mark.parametrize("label", ["deterministic", "prior", "noise", "both"])
def test_every_report_is_strict_json(reports, label) -> None:
    # inf and nan are what a σ of an uninformative prior would otherwise be,
    # and json.dumps writes them as tokens no other parser accepts.
    json.dumps(reports[label], allow_nan=False)


def test_the_report_file_and_the_json_document_agree(fixtures, tmp_path, capsys) -> None:
    config = config_for(fixtures, prior={"std": 0.05}, noise={"std": 0.01})
    path = tmp_path / "updating.yaml"
    report_path = tmp_path / "report.json"
    write_data(config, path)

    exit_code = main(
        [
            "--no-color",
            "update",
            str(path),
            "--format",
            "json",
            "--report",
            str(report_path),
        ]
    )
    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == json.loads(
        report_path.read_text(encoding="utf-8")
    )


# ------------------------------------------------------- writing the sections


def test_variance_and_covariance_write_the_same_prior_as_std(fixtures, tmp_path) -> None:
    written = [
        {"std": 0.05},
        {"variance": 0.0025},
        {"covariance": [[0.0025, 0.0], [0.0, 0.0025]]},
    ]
    blocks = [
        run_update(config_for(fixtures, prior=prior), tmp_path)["bayesian"]
        for prior in written
    ]
    for block in blocks[1:]:
        assert block["prior"]["std"] == pytest.approx(blocks[0]["prior"]["std"])
        np.testing.assert_allclose(
            block["prior"]["covariance"], blocks[0]["prior"]["covariance"]
        )
        assert block["posterior"]["sigma_post"] == pytest.approx(
            blocks[0]["posterior"]["sigma_post"]
        )
    assert [block["prior"]["given_as"] for block in blocks] == [
        "std",
        "variance",
        "covariance",
    ]


def test_a_per_parameter_mapping_follows_the_declaration_order(fixtures, tmp_path) -> None:
    # Written back to front, so an implementation reading the mapping in
    # insertion order would swap the two standard deviations.
    prior = {"std": {"mass": 0.02, "stiffness": 0.05}}
    report = run_update(config_for(fixtures, prior=prior), tmp_path)
    assert sigmas(report, "sigma_prior") == pytest.approx({"stiffness": 0.05, "mass": 0.02})


def test_a_configured_prior_mean_is_resolved_into_the_block(fixtures, tmp_path) -> None:
    prior = {"std": 0.05, "mean": {"stiffness": 0.9, "mass": 1.1}}
    block = run_update(config_for(fixtures, prior=prior), tmp_path)["bayesian"]["prior"]
    assert block["mean"] == pytest.approx([0.9, 1.1])


def test_a_tighter_noise_model_sharpens_the_posterior(fixtures, tmp_path) -> None:
    # Without a prior the posterior is sigma_e^2 (J^T J)^-1, and a uniform
    # rescaling of C_e leaves the MAP point (hence J) alone, so sigma_post
    # must follow sigma_e exactly.
    loose = run_update(config_for(fixtures, noise={"std": 0.01}), tmp_path)
    tight = run_update(config_for(fixtures, noise={"std": 0.005}), tmp_path)
    for name, value in sigmas(tight, "sigma_post").items():
        assert value == pytest.approx(0.5 * sigmas(loose, "sigma_post")[name], rel=1e-6)


def test_noise_covariance_is_accepted_as_a_spelling_of_noise(fixtures, tmp_path) -> None:
    report = run_update(config_for(fixtures, noise_covariance={"variance": 1.0e-4}), tmp_path)
    assert report["analysis"]["estimator"] == "map"
    assert report["bayesian"]["noise"]["std"] == pytest.approx(0.01)


# -------------------------------------------------------- malformed sections


@pytest.mark.parametrize(
    ("sections", "message"),
    [
        ({"prior": {}}, "'prior' needs one of std, variance, covariance"),
        ({"prior": {"std": 0.1, "variance": 0.01}}, "'prior' sets std and variance"),
        ({"prior": {"std": 0.0}}, "prior.std: standard deviations must be positive"),
        ({"prior": {"std": {"stiffness": 0.1}}}, "prior.std: no entry for mass"),
        (
            {"prior": {"std": {"stiffness": 0.1, "mass": 0.1, "damping": 0.1}}},
            "prior.std: no such parameter: damping",
        ),
        ({"prior": {"std": 0.1, "centre": 1.0}}, "unknown keys in 'prior': centre"),
        ({"prior": 0.05}, "'prior' must be a mapping"),
        ({"prior": {"std": "tight"}}, "prior.std: expected a number, a list or a matrix"),
        (
            {"prior": {"std": 0.1, "mean": [1.0, 1.0, 1.0]}},
            "prior.mean: expected 2 entries, got 3",
        ),
        ({"prior": {"std": [0.1, 0.1, 0.1]}}, "prior: prior_covariance: expected 2 variances"),
        (
            {"prior": {"covariance": [[0.01, 0.02], [0.0, 0.01]]}},
            "prior: prior_covariance: covariance matrix must be symmetric",
        ),
        ({"noise": {"sigma": 0.1}}, "unknown keys in 'noise': sigma"),
        ({"noise": {"variance": 0.0}}, "noise: variances must be positive"),
        (
            {"noise": {"std": {"stiffness": 0.1}}},
            "noise.std: a per-parameter mapping only applies to the prior",
        ),
    ],
)
def test_a_malformed_block_is_refused_by_name(
    fixtures, tmp_path, capsys, sections, message
) -> None:
    path = tmp_path / "updating.yaml"
    write_data(config_for(fixtures, **sections), path)
    assert main(["--no-color", "update", str(path)]) == 1
    assert message in capsys.readouterr().err


def test_a_noise_vector_of_the_wrong_length_is_refused(fixtures, tmp_path, capsys) -> None:
    # The residual length is only known once the modes are paired, so this one
    # is caught by the updater rather than by the configuration reader.
    path = tmp_path / "updating.yaml"
    write_data(config_for(fixtures, noise={"std": [0.01, 0.01]}), path)
    assert main(["--no-color", "update", str(path)]) == 1
    assert "noise_covariance: expected 3 variances, got 2" in capsys.readouterr().err


# ----------------------------------------------------------------- the table


def test_the_table_carries_sigma_post_and_omits_sigma_prior_without_one(
    fixtures, tmp_path, capsys
) -> None:
    path = tmp_path / "updating.yaml"
    write_data(config_for(fixtures), path)
    assert main(["--no-color", "update", str(path)]) == 0
    out = capsys.readouterr().out
    assert "estimator" in out and "least-squares" in out
    assert "sigma_post" in out
    assert "sigma_prior" not in out


def test_the_table_carries_both_spreads_once_a_prior_is_given(
    fixtures, tmp_path, capsys
) -> None:
    path = tmp_path / "updating.yaml"
    write_data(config_for(fixtures, prior={"std": 0.05}), path)
    assert main(["--no-color", "update", str(path)]) == 0
    out = capsys.readouterr().out
    assert "sigma_post" in out
    assert "sigma_prior" in out
    assert "map" in out
