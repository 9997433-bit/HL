"""Acceptance-criteria registry and consistency tests.

Machine-readable registry of every acceptance criterion defined in
``docs/ACCEPTANCE_CRITERIA.md`` (see its section 9 for the enforcement
contract). Implementation suites import ``REGISTRY`` / ``get_criterion`` to
tag themselves; the tests in this file guard that the registry, the criteria
document, and ``docs/MODULE_SPEC.md`` never drift apart.

Registry contract (ACCEPTANCE_CRITERIA.md sections 1 and 8):
- IDs follow ``AC-<MODULE>-NNN[a-z]?`` with MODULE in {MODAL, CORR, UPD,
  WORK, OPT, DYN, ELEM}; numbering is dense per module (no gaps); an optional
  lowercase suffix marks closely coupled sub-criteria sharing a number.
- ``priority`` in {P0, P1, P2} (P0 blocks Round-1, P1 blocks Round-2).
- ``method`` in {oracle, property, twin, contract, regression}.
- ``status`` lifecycle: specified -> implemented -> verified. A criterion may
  only leave ``specified`` once the suite named by ``test_file`` carries a test
  tagged ``@criterion("<ID>")`` (see ``tests/acceptance/_support.py``); it may
  only reach ``verified`` once the CI gate re-runs those tests green and
  reproducibly (``tests/acceptance/test_registry_ci.py``, CI job
  ``CI_GATE_JOB``), so the status set below is the promotion claim and that
  suite is its evidence.
- ``spec_ref`` anchors must exist in ``docs/MODULE_SPEC.md``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CRITERIA_DOC = REPO_ROOT / "docs" / "ACCEPTANCE_CRITERIA.md"
SPEC_DOC = REPO_ROOT / "docs" / "MODULE_SPEC.md"

#: Workflow and job that run the gate behind every ``verified`` status.
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
CI_GATE_JOB = "gates"

ID_REGEX = re.compile(r"AC-(?:MODAL|CORR|UPD|WORK|OPT|DYN|ELEM)-\d{3}[a-z]?")
ID_FULLMATCH = re.compile(r"^AC-(MODAL|CORR|UPD|WORK|OPT|DYN|ELEM)-(\d{3})([a-z]?)$")

VALID_MODULES = ("M1", "M2", "M3", "M4", "M5", "M6", "M7")
VALID_PRIORITIES = ("P0", "P1", "P2")
VALID_METHODS = ("oracle", "property", "twin", "contract", "regression")
VALID_STATUSES = ("specified", "implemented", "verified")

#: Statuses that assert an executable test exists for the criterion.
COVERED_STATUSES = ("implemented", "verified")

#: How an implementation suite tags a test with the criterion it verifies.
TAG_REGEX = re.compile(r"criterion\(\s*\"(AC-[A-Z]+-\d{3}[a-z]?)\"\s*\)")

FAMILY_TO_MODULE = {
    "MODAL": "M1", "CORR": "M2", "UPD": "M3", "WORK": "M4", "OPT": "M5",
    "DYN": "M6", "ELEM": "M7",
}
EXPECTED_CRITERIA_PER_FAMILY = {
    "MODAL": 9, "CORR": 9, "UPD": 9, "WORK": 5, "OPT": 4, "DYN": 5, "ELEM": 3,
}


@dataclass(frozen=True)
class AcceptanceCriterion:
    test_id: str
    module: str          # M1..M6
    title: str
    priority: str        # P0 | P1 | P2
    method: str          # oracle | property | twin | contract | regression
    spec_ref: str        # comma-separated MODULE_SPEC.md anchors
    test_file: str       # planned/actual implementation suite
    status: str = "specified"


def _c(test_id, title, priority, method, spec_ref, test_file,
       status="specified"):
    family = test_id.split("-")[1]
    return AcceptanceCriterion(test_id, FAMILY_TO_MODULE[family], title,
                               priority, method, spec_ref, test_file, status)


_MODAL_SUITE = "tests/acceptance/test_modal.py"
_CORR_SUITE = "tests/acceptance/test_correlation.py"
_UPD_SUITE = "tests/acceptance/test_updating.py"
_WORK_SUITE = "tests/acceptance/test_workflow.py"
_OPT_SUITE = "tests/acceptance/test_optimization.py"
_DYN_SUITE = "tests/acceptance/test_dynamics.py"
_ELEM_SUITE = "tests/acceptance/test_elements.py"

REGISTRY: tuple[AcceptanceCriterion, ...] = (
    # --- M1 Modal analysis (MS-1) -------------------------------------------
    _c("AC-MODAL-001", "Analytic eigenvalue accuracy",
       "P0", "oracle", "MS-1.1", _MODAL_SUITE, "implemented"),
    _c("AC-MODAL-002", "Backend consistency (dense/lanczos/lobpcg)",
       "P0", "property", "MS-1.2", _MODAL_SUITE, "implemented"),
    _c("AC-MODAL-003", "Mass-orthonormality of returned modes",
       "P0", "contract", "MS-1.3", _MODAL_SUITE, "verified"),
    _c("AC-MODAL-004", "Rigid-body mode detection",
       "P0", "oracle", "MS-1.2", _MODAL_SUITE, "implemented"),
    _c("AC-MODAL-005", "Sign convention & determinism",
       "P0", "contract", "MS-1.3", _MODAL_SUITE, "implemented"),
    _c("AC-MODAL-006", "Residual convergence guarantee",
       "P0", "contract", "MS-1.2", _MODAL_SUITE, "implemented"),
    _c("AC-MODAL-007", "Effective modal mass completeness",
       "P0", "oracle", "MS-1.4", _MODAL_SUITE, "implemented"),
    _c("AC-MODAL-008", "Frequency-window extraction + missed-mode guard",
       "P1", "oracle", "MS-1.2", _MODAL_SUITE),
    _c("AC-MODAL-009", "Input validation & typed failures",
       "P0", "contract", "MS-1.1", _MODAL_SUITE, "implemented"),
    # --- M2 Correlation (MS-2) ----------------------------------------------
    _c("AC-CORR-001", "Weighted MAC self-identity",
       "P0", "property", "MS-2.2", _CORR_SUITE, "verified"),
    _c("AC-CORR-002", "MAC scaling/sign invariance",
       "P0", "property", "MS-2.2", _CORR_SUITE, "verified"),
    _c("AC-CORR-003", "Pairing recovers ground truth",
       "P0", "twin", "MS-2.3", _CORR_SUITE, "implemented"),
    _c("AC-CORR-004", "COMAC localizes bad DOF",
       "P0", "twin", "MS-2.5", _CORR_SUITE, "implemented"),
    _c("AC-CORR-005", "Frequency-error sign convention",
       "P0", "oracle", "MS-2.4", _CORR_SUITE, "implemented"),
    _c("AC-CORR-006", "Reduction/expansion (SEREP) consistency",
       "P1", "twin", "MS-2.1", _CORR_SUITE, "verified"),
    _c("AC-CORR-007", "MAC range and complex-shape support",
       "P0", "property", "MS-2.2", _CORR_SUITE, "implemented"),
    _c("AC-CORR-008", "CorrelationReport JSON round-trip",
       "P0", "contract", "MS-2.6", _CORR_SUITE, "implemented"),
    _c("AC-CORR-009", "TAM pseudo-orthogonality",
       "P1", "twin", "MS-2.1, MS-2.2", _CORR_SUITE, "implemented"),
    # --- M3 Model updating (MS-3) --------------------------------------------
    _c("AC-UPD-001", "Eigenvalue sensitivity vs central FD",
       "P0", "oracle", "MS-3.3", _UPD_SUITE, "verified"),
    _c("AC-UPD-002", "Fox-Kapoor shape sensitivity vs central FD",
       "P0", "oracle", "MS-3.3", _UPD_SUITE, "implemented"),
    _c("AC-UPD-003", "Twin-experiment parameter recovery",
       "P0", "twin", "MS-3.4", _UPD_SUITE, "implemented"),
    _c("AC-UPD-004", "Convergence monitoring & divergence guard",
       "P0", "contract", "MS-3.4", _UPD_SUITE, "implemented"),
    _c("AC-UPD-005", "Ill-posed robustness (over-parameterized)",
       "P0", "property", "MS-3.4", _UPD_SUITE, "implemented"),
    _c("AC-UPD-006a", "Bayesian step -> GN limit (weak prior)",
       "P1", "property", "MS-3.5", _UPD_SUITE, "implemented"),
    _c("AC-UPD-006b", "Posterior contraction (tight prior)",
       "P1", "property", "MS-3.5", _UPD_SUITE, "implemented"),
    _c("AC-UPD-007", "Collinear parameter detection & freeze",
       "P0", "twin", "MS-3.6", _UPD_SUITE, "implemented"),
    _c("AC-UPD-008", "Mode switching handled by re-pairing",
       "P1", "twin", "MS-3.2", _UPD_SUITE),
    # --- M4 Simulation correction workflow (MS-4) -----------------------------
    _c("AC-WORK-001", "End-to-end correction passes gates",
       "P0", "twin", "MS-4.1, MS-4.2", _WORK_SUITE, "implemented"),
    _c("AC-WORK-002", "Deterministic reproducibility",
       "P0", "contract", "MS-4.3", _WORK_SUITE, "verified"),
    _c("AC-WORK-003", "Held-out validation detects overfitting",
       "P1", "twin", "MS-4.1", _WORK_SUITE),
    _c("AC-WORK-004", "Failed gate halts with typed reason",
       "P0", "contract", "MS-4.1", _WORK_SUITE, "implemented"),
    _c("AC-WORK-005", "CorrectionReport schema & versioning",
       "P0", "contract", "MS-4.3", _WORK_SUITE, "implemented"),
    # --- M5 Optimization hook (MS-5) ------------------------------------------
    _c("AC-OPT-001", "Analytic gradients vs central FD",
       "P0", "oracle", "MS-5.1", _OPT_SUITE, "implemented"),
    _c("AC-OPT-002", "Reference problem reaches known optimum",
       "P0", "oracle", "MS-5.2", _OPT_SUITE, "implemented"),
    _c("AC-OPT-003", "Box bounds never violated",
       "P0", "contract", "MS-5.2", _OPT_SUITE, "verified"),
    _c("AC-OPT-004", "Mode tracking across crossings",
       "P1", "twin", "MS-5.2", _OPT_SUITE, "implemented"),
    # --- M6 Damped dynamics and FRF (MS-7) ------------------------------------
    _c("AC-DYN-001", "Damped FRF vs closed form",
       "P0", "oracle", "MS-7.3", _DYN_SUITE, "implemented"),
    _c("AC-DYN-002", "Modal superposition matches direct inversion",
       "P0", "property", "MS-7.3", _DYN_SUITE, "implemented"),
    _c("AC-DYN-003", "Proportional damping yields real modes",
       "P0", "property", "MS-7.2", _DYN_SUITE, "implemented"),
    _c("AC-DYN-004", "FRAC/FDAC self-identity and scale invariance",
       "P0", "property", "MS-7.4", _DYN_SUITE, "verified"),
    _c("AC-DYN-005", "Synthesized FRF survives the UFF-58 round trip",
       "P1", "contract", "MS-7.4", _DYN_SUITE, "implemented"),
    # --- M7 Element library (MS-8) --------------------------------------------
    _c("AC-ELEM-001", "Patch test exact to machine precision",
       "P0", "oracle", "MS-8.3", _ELEM_SUITE, "verified"),
    _c("AC-ELEM-002", "Rigid-body invariance and zero-energy mode count",
       "P0", "property", "MS-8.3", _ELEM_SUITE, "implemented"),
    _c("AC-ELEM-003", "Quadratic h-convergence on the continuum oracle",
       "P1", "property", "MS-8.4", _ELEM_SUITE, "implemented"),
)

_BY_ID = {c.test_id: c for c in REGISTRY}


def get_criterion(test_id: str) -> AcceptanceCriterion:
    """Look up a criterion by ID (implementation suites tag tests with it)."""
    return _BY_ID[test_id]


def ids() -> tuple[str, ...]:
    return tuple(c.test_id for c in REGISTRY)


def verified_ids() -> tuple[str, ...]:
    """IDs claiming ``verified``; the gate suite re-runs exactly these."""
    return tuple(c.test_id for c in REGISTRY if c.status == "verified")


# ---------------------------------------------------------------------------
# Consistency tests (enforcement rules of ACCEPTANCE_CRITERIA.md section 9)
# ---------------------------------------------------------------------------

def test_registry_inventory_matches_documented_scope():
    counts = {
        family: sum(c.test_id.startswith(f"AC-{family}-") for c in REGISTRY)
        for family in EXPECTED_CRITERIA_PER_FAMILY
    }
    assert counts == EXPECTED_CRITERIA_PER_FAMILY
    assert len(REGISTRY) == 44


def test_ids_unique():
    all_ids = [c.test_id for c in REGISTRY]
    dupes = {i for i in all_ids if all_ids.count(i) > 1}
    assert not dupes, f"duplicate acceptance criterion IDs: {sorted(dupes)}"


def test_id_format():
    bad = [c.test_id for c in REGISTRY if not ID_FULLMATCH.match(c.test_id)]
    assert not bad, f"IDs not matching AC-<MODULE>-NNN[a-z]?: {bad}"


def test_fields_valid():
    for c in REGISTRY:
        assert c.module in VALID_MODULES, (c.test_id, c.module)
        assert c.priority in VALID_PRIORITIES, (c.test_id, c.priority)
        assert c.method in VALID_METHODS, (c.test_id, c.method)
        assert c.status in VALID_STATUSES, (c.test_id, c.status)
        assert c.title.strip(), c.test_id
        assert c.test_file.startswith("tests/"), (c.test_id, c.test_file)
        for anchor in (a.strip() for a in c.spec_ref.split(",")):
            assert re.fullmatch(r"MS-\d+(\.\d+)?", anchor), (
                c.test_id, c.spec_ref)


def test_module_family_consistent():
    for c in REGISTRY:
        family = ID_FULLMATCH.match(c.test_id).group(1)
        assert FAMILY_TO_MODULE[family] == c.module, (c.test_id, c.module)


def test_numbering_dense_per_module():
    """Base numbers are contiguous from 001 within each family (rule 2)."""
    families: dict[str, set[int]] = {}
    for c in REGISTRY:
        m = ID_FULLMATCH.match(c.test_id)
        families.setdefault(m.group(1), set()).add(int(m.group(2)))
    for family, nums in families.items():
        expected = set(range(1, max(nums) + 1))
        assert nums == expected, (
            f"AC-{family}: numbers {sorted(nums)} have gaps "
            f"(expected {sorted(expected)})"
        )


def test_every_module_has_blocking_criterion():
    """Each module M1..M7 carries at least one P0 criterion (rule 5)."""
    p0_modules = {c.module for c in REGISTRY if c.priority == "P0"}
    missing = set(VALID_MODULES) - p0_modules
    assert not missing, f"modules without a P0 criterion: {sorted(missing)}"


def _doc_ids(path: Path) -> set[str]:
    return set(ID_REGEX.findall(path.read_text(encoding="utf-8")))


def test_registry_matches_acceptance_criteria_doc():
    """Doc and registry define exactly the same ID set (rule 3)."""
    assert CRITERIA_DOC.is_file(), f"missing document: {CRITERIA_DOC}"
    doc_ids = _doc_ids(CRITERIA_DOC)
    reg_ids = set(ids())
    only_doc = sorted(doc_ids - reg_ids)
    only_reg = sorted(reg_ids - doc_ids)
    assert not only_doc and not only_reg, (
        f"doc-only IDs: {only_doc}; registry-only IDs: {only_reg}"
    )


def test_module_spec_references_resolve():
    """Every AC-* ID cited in MODULE_SPEC.md exists in the registry (rule 3)."""
    assert SPEC_DOC.is_file(), f"missing document: {SPEC_DOC}"
    dangling = sorted(_doc_ids(SPEC_DOC) - set(ids()))
    assert not dangling, f"MODULE_SPEC.md cites unknown criteria: {dangling}"


def _suite_paths() -> list[Path]:
    """Implementation suites in this package (the registry file excluded)."""
    here = Path(__file__).resolve()
    return sorted(p for p in here.parent.glob("test_*.py") if p != here)


def _tagged_ids(path: Path) -> set[str]:
    return set(TAG_REGEX.findall(path.read_text(encoding="utf-8")))


def test_covered_criteria_have_a_tagged_test():
    """``implemented``/``verified`` requires a tagged test in the named suite."""
    missing = []
    for c in REGISTRY:
        if c.status not in COVERED_STATUSES:
            continue
        suite = REPO_ROOT / c.test_file
        if not suite.is_file() or c.test_id not in _tagged_ids(suite):
            missing.append((c.test_id, c.test_file))
    assert not missing, f"criteria claiming coverage without a tagged test: {missing}"


def test_tagged_tests_match_the_registry():
    """Every tag resolves to a criterion that names that suite and is covered."""
    problems = []
    for suite in _suite_paths():
        relative = suite.relative_to(REPO_ROOT).as_posix()
        for test_id in sorted(_tagged_ids(suite)):
            entry = _BY_ID.get(test_id)
            if entry is None:
                problems.append(f"{relative} tags unknown criterion {test_id}")
            elif entry.test_file != relative:
                problems.append(
                    f"{relative} tags {test_id}, which the registry assigns to "
                    f"{entry.test_file}"
                )
            elif entry.status not in COVERED_STATUSES:
                problems.append(
                    f"{test_id} has a test in {relative} but is still {entry.status!r}"
                )
    assert not problems, problems


def test_verified_criteria_are_round_gates():
    """Promotion is reserved for blocking criteria (rule 7)."""
    stretch = [c.test_id for c in REGISTRY
               if c.status == "verified" and c.priority == "P2"]
    assert not stretch, f"P2 criteria promoted to verified: {stretch}"


def test_verified_criteria_span_every_module():
    """The promoted slice gates all of M1..M6, not one corner of the platform."""
    covered = {c.module for c in REGISTRY if c.status == "verified"}
    missing = sorted(set(VALID_MODULES) - covered)
    assert not missing, f"modules with no verified criterion: {missing}"


def test_verified_criteria_run_in_the_ci_gate_job():
    """A ``verified`` status is only meaningful if CI still runs the gate."""
    assert CI_WORKFLOW.is_file(), f"missing CI workflow: {CI_WORKFLOW}"
    jobs = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8")).get("jobs", {})
    assert CI_GATE_JOB in jobs, (
        f"{len(verified_ids())} criteria claim 'verified' but the workflow has "
        f"no {CI_GATE_JOB!r} job (jobs: {sorted(jobs)})"
    )


def test_module_spec_anchors_exist():
    """Every spec_ref anchor appears verbatim in MODULE_SPEC.md (rule 4)."""
    text = SPEC_DOC.read_text(encoding="utf-8")
    missing = [
        (c.test_id, anchor)
        for c in REGISTRY
        for anchor in (a.strip() for a in c.spec_ref.split(","))
        if anchor not in text
    ]
    assert not missing, f"spec anchors not found in MODULE_SPEC.md: {missing}"
