"""Contract tests for the cross-platform release-signing scaffolds.

Three scripts sign three platforms and one aggregates their reports:

    scripts/sign-linux-artifact.sh       GPG detached signatures
    scripts/sign-macos-artifact.sh       codesign, optional notarytool
    scripts/sign-windows-artifact.ps1    Authenticode via signtool
    scripts/release-signing-manifest.sh  the union of the three reports

This project holds no Apple Developer ID and no Authenticode certificate, so
the path these tests can actually exercise end to end is the unsigned one, and
that is the path worth pinning down: it has to succeed, checksum everything,
and say in the report that nothing was signed and why. The tests below run the
macOS scaffold and the manifest for real, run the PowerShell scaffold for real
wherever pwsh exists, and check the three reports share one schema so a release
summary cannot read a missing field as a signature.

What no test here does is supply a certificate. A test that mocked codesign or
signtool into "succeeding" would be asserting that this repository can produce
a signature it cannot produce, so the signed branches are covered by reading
the sources instead: each one sets its signed flag only after the platform's
own verifier has accepted the artifact.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform as platform_module
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
SIGNING_LIB = SCRIPTS_DIR / "lib" / "release-signing.sh"
LINUX_SCRIPT = SCRIPTS_DIR / "sign-linux-artifact.sh"
MACOS_SCRIPT = SCRIPTS_DIR / "sign-macos-artifact.sh"
WINDOWS_SCRIPT = SCRIPTS_DIR / "sign-windows-artifact.ps1"
MANIFEST_SCRIPT = SCRIPTS_DIR / "release-signing-manifest.sh"

SHELL_SCRIPTS = (LINUX_SCRIPT, MACOS_SCRIPT, MANIFEST_SCRIPT)
SHELL_SOURCES = (*SHELL_SCRIPTS, SIGNING_LIB)

#: Every per-platform report carries these, whichever script wrote it.
REQUIRED_REPORT_KEYS = (
    "schema_version",
    "tool",
    "target_platform",
    "generated_at",
    "platform",
    "signing",
    "signed",
    "reason",
    "manifest",
    "artifacts",
    "artifact_count",
    "scope",
)
REQUIRED_ARTIFACT_KEYS = ("path", "size_bytes", "sha256", "signature", "signature_verified")
#: The claim surface. A summary that reads one of these as true when it is not
#: is the failure this whole scaffold exists to prevent.
SCOPE_KEYS = (
    "linux_gpg_detached_signature",
    "macos_codesign",
    "macos_notarization",
    "windows_authenticode",
    "note",
)

SCHEMA_VERSION = 1
DEFAULT_REPORTS = {
    MACOS_SCRIPT: "macos-signing-report.json",
    WINDOWS_SCRIPT: ".agent_workspace/v1.2/windows-signing-report.json",
    MANIFEST_SCRIPT: "release-signing-manifest.json",
}

COMMITTED_MANIFEST = REPO_ROOT / ".agent_workspace" / "v1.2" / "release-signing-manifest.json"


def run_script(
    script: Path, *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    # An inherited credential would send a run down a path this suite
    # deliberately never takes.
    for inherited in ("SIGNING_KEY", "MACOS_SIGNING_IDENTITY", "CODESIGN_IDENTITY"):
        environment.pop(inherited, None)
    environment.update(env or {})
    return subprocess.run(
        [str(script), *args],
        capture_output=True,
        text=True,
        env=environment,
        cwd=REPO_ROOT,
        timeout=300,
        check=False,
    )


def powershell() -> str:
    for candidate in ("pwsh", "powershell.exe", "powershell"):
        found = shutil.which(candidate)
        if found is not None:
            return found
    pytest.skip("no PowerShell interpreter (pwsh) on this host")


def run_windows_script(
    *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    interpreter = powershell()
    environment = dict(os.environ)
    # An inherited certificate would send the run down a path this suite
    # deliberately never takes.
    environment.pop("WINDOWS_SIGNING_CERT", None)
    environment.update(env or {})
    return subprocess.run(
        [interpreter, "-NoLogo", "-NoProfile", "-File", str(WINDOWS_SCRIPT), *args],
        capture_output=True,
        text=True,
        env=environment,
        cwd=REPO_ROOT,
        timeout=300,
        check=False,
    )


def assert_report_schema(report: dict, tool: str, target_platform: str) -> None:
    missing = [key for key in REQUIRED_REPORT_KEYS if key not in report]
    assert not missing, f"{tool} report is missing {missing}"
    assert report["schema_version"] == SCHEMA_VERSION
    assert report["tool"] == tool
    assert report["target_platform"] == target_platform
    assert isinstance(report["signed"], bool)
    assert report["reason"].strip(), "a report with no reason explains nothing"
    assert set(report["platform"]) >= {"system", "machine", "release"}
    assert report["artifact_count"] == len(report["artifacts"])

    for artifact in report["artifacts"]:
        artifact_missing = [key for key in REQUIRED_ARTIFACT_KEYS if key not in artifact]
        assert not artifact_missing, f"{tool} artifact record is missing {artifact_missing}"
        assert isinstance(artifact["signature_verified"], bool)
        if artifact["signature"] is None:
            assert artifact["signature_verified"] is False

    for key in SCOPE_KEYS:
        assert key in report["scope"], f"{tool} report never mentions {key}"
    for key in SCOPE_KEYS[:-1]:
        assert isinstance(report["scope"][key], bool)

    # signed=true with nothing verified is the shape of a fabricated claim.
    if report["signed"]:
        assert any(artifact["signature_verified"] for artifact in report["artifacts"])
    else:
        assert not any(artifact["signature_verified"] for artifact in report["artifacts"])


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


@pytest.fixture
def macos_artifacts(tmp_path: Path) -> tuple[Path, Path]:
    """A disk image and an .app bundle: a file and a directory to describe."""
    directory = tmp_path / "release-macos"
    directory.mkdir()
    disk_image = directory / "AudioStudio-1.1.0.dmg"
    disk_image.write_bytes(b"pretend disk image payload\n")

    bundle = directory / "Audio Studio.app"
    macos_dir = bundle / "Contents" / "MacOS"
    macos_dir.mkdir(parents=True)
    (macos_dir / "audio-studio").write_bytes(b"pretend Mach-O payload\n")
    (bundle / "Contents" / "Info.plist").write_text("<plist/>\n", encoding="utf-8")
    return disk_image, bundle


@pytest.fixture
def windows_artifact(tmp_path: Path) -> Path:
    directory = tmp_path / "release-windows"
    directory.mkdir()
    executable = directory / "audio-studio.exe"
    executable.write_bytes(b"MZ pretend portable executable\n")
    return executable


@pytest.fixture
def linux_artifact(tmp_path: Path) -> Path:
    directory = tmp_path / "release-linux"
    directory.mkdir()
    package = directory / "audio-studio_1.1.0-1_amd64.deb"
    package.write_bytes(b"pretend deb payload\n")
    return package


@pytest.fixture
def macos_report(macos_artifacts: tuple[Path, Path], tmp_path: Path) -> dict:
    report_path = tmp_path / "macos-signing-report.json"
    result = run_script(
        MACOS_SCRIPT,
        "--report",
        str(report_path),
        *[str(path) for path in macos_artifacts],
        env={"MACOS_SIGNING_IDENTITY": ""},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(report_path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# Static checks
# --------------------------------------------------------------------------


@pytest.mark.parametrize("script", SHELL_SCRIPTS, ids=lambda path: path.name)
def test_shell_scripts_are_executable_and_fail_fast(script: Path) -> None:
    assert script.is_file(), f"{script} is missing"
    assert script.stat().st_mode & stat.S_IXUSR, f"{script} is not executable"

    lines = script.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "#!/usr/bin/env bash"
    assert "set -Eeuo pipefail" in lines, f"{script.name} does not fail fast"


@pytest.mark.parametrize("source", SHELL_SOURCES, ids=lambda path: path.name)
def test_shell_sources_parse(source: Path) -> None:
    result = subprocess.run(
        ["bash", "-n", str(source)], capture_output=True, text=True, timeout=60, check=False
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("source", SHELL_SOURCES, ids=lambda path: path.name)
def test_shellcheck_is_clean(source: Path) -> None:
    shellcheck = shutil.which("shellcheck")
    if shellcheck is None:
        pytest.skip("shellcheck is not installed")
    result = subprocess.run(
        [shellcheck, "--severity=warning", str(source)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("script", (MACOS_SCRIPT, MANIFEST_SCRIPT), ids=lambda path: path.name)
def test_help_exits_cleanly(script: Path) -> None:
    result = run_script(script, "--help")
    assert result.returncode == 0, result.stderr
    assert "Usage:" in result.stdout


@pytest.mark.parametrize("script", (MACOS_SCRIPT, MANIFEST_SCRIPT), ids=lambda path: path.name)
def test_unknown_option_is_a_usage_error(script: Path) -> None:
    result = run_script(script, "--not-an-option")
    assert result.returncode == 2, result.stdout + result.stderr


def test_reports_default_into_the_v12_workspace() -> None:
    assert ".agent_workspace/v1.2" in SIGNING_LIB.read_text(encoding="utf-8")
    for script, expected in DEFAULT_REPORTS.items():
        assert expected in script.read_text(encoding="utf-8"), f"{script.name} lost its default"


def test_every_script_agrees_on_the_schema_version() -> None:
    assert f"RELEASE_SIGNING_SCHEMA_VERSION={SCHEMA_VERSION}" in SIGNING_LIB.read_text(
        encoding="utf-8"
    )
    assert f"$SchemaVersion = {SCHEMA_VERSION}" in WINDOWS_SCRIPT.read_text(encoding="utf-8")


def test_powershell_scaffold_is_strict_and_signtool_based() -> None:
    text = WINDOWS_SCRIPT.read_text(encoding="utf-8")
    assert "Set-StrictMode -Version Latest" in text
    assert '$ErrorActionPreference = "Stop"' in text
    assert "WINDOWS_SIGNING_CERT" in text
    # SHA-256 with an RFC 3161 countersignature, or the signature expires with
    # the certificate.
    assert "/fd" in text and "SHA256" in text
    assert "/tr" in text and "TimestampUrl" in text
    assert "signtool" in text


def test_powershell_scaffold_declares_the_shared_report_fields() -> None:
    """The Windows report is built in PowerShell, so its keys are checked here.

    Nothing else can compare the three schemas on a Linux runner without a
    PowerShell interpreter, and a Windows report that quietly dropped `scope`
    would be a report that stops denying the other platforms.
    """
    text = WINDOWS_SCRIPT.read_text(encoding="utf-8")
    for key in (*REQUIRED_REPORT_KEYS, *REQUIRED_ARTIFACT_KEYS, *SCOPE_KEYS):
        assert re.search(rf"^\s*{re.escape(key)}\s*=", text, flags=re.MULTILINE), (
            f"the Windows report never sets {key}"
        )


def test_powershell_reports_signed_only_after_signtool_verifies() -> None:
    text = WINDOWS_SCRIPT.read_text(encoding="utf-8")
    assignments = [
        match.start() for match in re.finditer(r"^\s*\$Signed\s*=\s*\$true", text, re.MULTILINE)
    ]
    assert len(assignments) == 1, "signed is set in more than one place"
    verification = text.index("verify /pa /v")
    authenticode = text.index("Get-AuthenticodeSignature")
    assert assignments[0] > verification > 0
    assert assignments[0] > authenticode > 0


def test_macos_scaffold_reports_signed_only_after_codesign_verifies() -> None:
    text = MACOS_SCRIPT.read_text(encoding="utf-8")
    assignments = [match.start() for match in re.finditer(r"^\s*SIGNED=1", text, re.MULTILINE)]
    assert len(assignments) == 1, "signed is set in more than one place"
    assert "codesign --verify failed" in text
    assert assignments[0] > text.index("verify_signature() {")
    assert "--options runtime" in text, "a Developer ID signature needs the hardened runtime"


def test_macos_scaffold_refuses_to_run_codesign_off_darwin() -> None:
    text = MACOS_SCRIPT.read_text(encoding="utf-8")
    assert 'HOST_SYSTEM="$(uname -s)"' in text
    assert '"${HOST_SYSTEM}" != "Darwin"' in text


# --------------------------------------------------------------------------
# macOS scaffold, unsigned path
# --------------------------------------------------------------------------


def test_macos_unsigned_run_is_honest_and_still_checksums(
    macos_artifacts: tuple[Path, Path], macos_report: dict
) -> None:
    assert_report_schema(macos_report, "scripts/sign-macos-artifact.sh", "macos")
    assert macos_report["signed"] is False
    assert macos_report["signing"]["identity_requested"] is False
    assert macos_report["signing"]["identity"] is None
    assert "MACOS_SIGNING_IDENTITY" in macos_report["reason"]
    assert macos_report["artifact_count"] == 2

    disk_image, bundle = macos_artifacts
    described = {Path(entry["path"]).name: entry for entry in macos_report["artifacts"]}

    image_record = described[disk_image.name]
    assert image_record["kind"] == "file"
    assert image_record["digest_scope"] == "file"
    assert image_record["sha256"] == hashlib.sha256(disk_image.read_bytes()).hexdigest()
    assert image_record["size_bytes"] == disk_image.stat().st_size

    bundle_record = described[bundle.name]
    assert bundle_record["kind"] == "bundle"
    assert bundle_record["digest_scope"] == "bundle-tree"
    assert bundle_record["size_bytes"] == sum(
        path.stat().st_size for path in bundle.rglob("*") if path.is_file()
    )


def test_macos_unsigned_run_leaves_no_signature_behind(
    macos_artifacts: tuple[Path, Path], macos_report: dict
) -> None:
    disk_image, bundle = macos_artifacts
    for record in macos_report["artifacts"]:
        assert record["signature"] is None
        assert record["signature_verified"] is False
    assert list(disk_image.parent.glob("*.asc")) == []
    assert list(disk_image.parent.glob("*.sig")) == []
    assert not (bundle / "Contents" / "_CodeSignature").exists()


def test_macos_report_denies_the_other_platforms(macos_report: dict) -> None:
    scope = macos_report["scope"]
    assert scope["macos_codesign"] is False
    assert scope["macos_notarization"] is False
    assert scope["linux_gpg_detached_signature"] is False
    assert scope["windows_authenticode"] is False
    assert "no Apple Developer ID" in scope["note"]


def test_macos_manifest_verifies_with_sha256sum(macos_artifacts: tuple[Path, Path]) -> None:
    if shutil.which("sha256sum") is None:
        pytest.skip("sha256sum is not installed")
    disk_image, bundle = macos_artifacts
    result = run_script(
        MACOS_SCRIPT,
        "--report",
        str(disk_image.parent / "report.json"),
        str(disk_image),
        str(bundle),
        env={"MACOS_SIGNING_IDENTITY": ""},
    )
    assert result.returncode == 0, result.stderr

    manifest = disk_image.parent / "SHA256SUMS"
    assert manifest.is_file()
    # The bundle is a directory: shasum --check would reject a line for it, so
    # the manifest must not contain one.
    assert bundle.name not in manifest.read_text(encoding="utf-8")
    check = subprocess.run(
        ["sha256sum", "--check", "--strict", manifest.name],
        cwd=manifest.parent,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert check.returncode == 0, check.stdout + check.stderr


def test_macos_bundle_digest_is_stable_and_content_sensitive(
    macos_artifacts: tuple[Path, Path], tmp_path: Path
) -> None:
    _, bundle = macos_artifacts

    def digest_of(report_name: str) -> str:
        report_path = tmp_path / report_name
        result = run_script(
            MACOS_SCRIPT,
            "--report",
            str(report_path),
            str(bundle),
            env={"MACOS_SIGNING_IDENTITY": ""},
        )
        assert result.returncode == 0, result.stderr
        report = json.loads(report_path.read_text(encoding="utf-8"))
        return report["artifacts"][0]["sha256"]

    first = digest_of("first.json")
    assert first == digest_of("second.json"), "the bundle digest is not reproducible"

    (bundle / "Contents" / "Info.plist").write_text("<plist>changed</plist>\n", encoding="utf-8")
    assert digest_of("third.json") != first, "the bundle digest ignores its contents"


def test_macos_require_signature_fails_without_an_identity(
    macos_artifacts: tuple[Path, Path], tmp_path: Path
) -> None:
    result = run_script(
        MACOS_SCRIPT,
        "--report",
        str(tmp_path / "report.json"),
        "--require-signature",
        str(macos_artifacts[0]),
        env={"MACOS_SIGNING_IDENTITY": ""},
    )
    assert result.returncode == 1
    assert "MACOS_SIGNING_IDENTITY" in result.stderr


@pytest.mark.skipif(platform_module.system() == "Darwin", reason="this host is macOS")
def test_macos_identity_off_darwin_is_refused(
    macos_artifacts: tuple[Path, Path], tmp_path: Path
) -> None:
    report_path = tmp_path / "report.json"
    result = run_script(
        MACOS_SCRIPT,
        "--report",
        str(report_path),
        str(macos_artifacts[0]),
        env={"MACOS_SIGNING_IDENTITY": "Developer ID Application: Nobody (TEAM123456)"},
    )
    assert result.returncode == 1
    assert "not Darwin" in result.stderr
    assert not report_path.exists(), "a refusal must not leave a report behind"


def test_macos_missing_artifact_is_refused(tmp_path: Path) -> None:
    result = run_script(
        MACOS_SCRIPT, "--report", str(tmp_path / "report.json"), str(tmp_path / "absent.dmg")
    )
    assert result.returncode == 1
    assert "no such artifact" in result.stderr


def test_macos_missing_entitlements_is_refused(
    macos_artifacts: tuple[Path, Path], tmp_path: Path
) -> None:
    result = run_script(
        MACOS_SCRIPT,
        "--report",
        str(tmp_path / "report.json"),
        "--entitlements",
        str(tmp_path / "absent.plist"),
        str(macos_artifacts[0]),
        env={"MACOS_SIGNING_IDENTITY": ""},
    )
    assert result.returncode == 1
    assert "entitlements" in result.stderr


def test_macos_notarization_is_reported_as_not_attempted(
    macos_artifacts: tuple[Path, Path], tmp_path: Path
) -> None:
    report_path = tmp_path / "report.json"
    result = run_script(
        MACOS_SCRIPT,
        "--report",
        str(report_path),
        "--notarize",
        str(macos_artifacts[0]),
        env={"MACOS_SIGNING_IDENTITY": "", "MACOS_NOTARY_PROFILE": ""},
    )
    assert result.returncode == 0, result.stderr

    notarization = json.loads(report_path.read_text(encoding="utf-8"))["notarization"]
    assert notarization["requested"] is True
    assert notarization["performed"] is False
    assert notarization["stapled"] is False
    assert notarization["submission_ids"] == []
    assert "nothing was signed" in notarization["reason"]

    strict = run_script(
        MACOS_SCRIPT,
        "--report",
        str(tmp_path / "strict.json"),
        "--require-notarization",
        str(macos_artifacts[0]),
        env={"MACOS_SIGNING_IDENTITY": ""},
    )
    assert strict.returncode == 1


# --------------------------------------------------------------------------
# Windows scaffold, unsigned path
# --------------------------------------------------------------------------


def test_windows_unsigned_run_is_honest_and_still_checksums(
    windows_artifact: Path, tmp_path: Path
) -> None:
    report_path = tmp_path / "windows-signing-report.json"
    result = run_windows_script("-Report", str(report_path), str(windows_artifact))
    assert result.returncode == 0, result.stdout + result.stderr

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert_report_schema(report, "scripts/sign-windows-artifact.ps1", "windows")
    assert report["signed"] is False
    assert report["signing"]["certificate_requested"] is False
    assert report["signing"]["certificate_source"] is None
    assert report["signing"]["signtool_path"] is None
    assert report["signing"]["digest_algorithm"] == "SHA256"
    assert "WINDOWS_SIGNING_CERT" in report["reason"]

    record = report["artifacts"][0]
    assert record["sha256"] == hashlib.sha256(windows_artifact.read_bytes()).hexdigest()
    assert record["size_bytes"] == windows_artifact.stat().st_size
    assert record["signature"] is None
    assert report["scope"]["windows_authenticode"] is False
    assert (windows_artifact.parent / "SHA256SUMS").is_file()


def test_windows_report_records_the_host_it_actually_ran_on(
    windows_artifact: Path, tmp_path: Path
) -> None:
    """The unsigned path runs anywhere, and the report may not imply Windows."""
    report_path = tmp_path / "report.json"
    result = run_windows_script("-Report", str(report_path), str(windows_artifact))
    assert result.returncode == 0, result.stderr

    report = json.loads(report_path.read_text(encoding="utf-8"))
    expected = {"Linux": "Linux", "Darwin": "Darwin"}.get(platform_module.system(), "Windows")
    assert report["platform"]["system"] == expected
    assert report["signing"]["host_is_windows"] == (expected == "Windows")


def test_windows_require_signature_fails_without_a_certificate(
    windows_artifact: Path, tmp_path: Path
) -> None:
    result = run_windows_script(
        "-RequireSignature", "-Report", str(tmp_path / "report.json"), str(windows_artifact)
    )
    assert result.returncode == 1
    assert "WINDOWS_SIGNING_CERT" in result.stdout + result.stderr


@pytest.mark.skipif(os.name == "nt", reason="this host is Windows")
def test_windows_certificate_off_windows_is_refused(
    windows_artifact: Path, tmp_path: Path
) -> None:
    report_path = tmp_path / "report.json"
    result = run_windows_script(
        "-Report",
        str(report_path),
        str(windows_artifact),
        env={"WINDOWS_SIGNING_CERT": "0123456789abcdef0123456789abcdef01234567"},
    )
    assert result.returncode == 1
    assert "not Windows" in result.stdout + result.stderr
    assert not report_path.exists(), "a refusal must not leave a report behind"


def test_windows_unusable_certificate_value_is_refused(
    windows_artifact: Path, tmp_path: Path
) -> None:
    result = run_windows_script(
        "-Report",
        str(tmp_path / "report.json"),
        str(windows_artifact),
        env={"WINDOWS_SIGNING_CERT": "not-a-thumbprint-or-a-pfx"},
    )
    assert result.returncode == 1
    assert "WINDOWS_SIGNING_CERT" in result.stdout + result.stderr


def test_windows_scaffold_rejects_a_missing_artifact(tmp_path: Path) -> None:
    result = run_windows_script("-Report", str(tmp_path / "report.json"), str(tmp_path / "no.exe"))
    assert result.returncode == 1
    assert "no such artifact" in result.stdout + result.stderr


def test_windows_scaffold_rejects_an_unknown_option(windows_artifact: Path) -> None:
    result = run_windows_script("--not-an-option", str(windows_artifact))
    assert result.returncode == 2


# --------------------------------------------------------------------------
# One schema across three platforms
# --------------------------------------------------------------------------


@pytest.fixture
def linux_report(linux_artifact: Path, tmp_path: Path) -> dict:
    report_path = tmp_path / "linux-signing-report.json"
    result = run_script(
        LINUX_SCRIPT,
        "--report",
        str(report_path),
        str(linux_artifact),
        env={"SIGNING_KEY": ""},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(report_path.read_text(encoding="utf-8"))


def test_linux_and_macos_reports_share_one_schema(linux_report: dict, macos_report: dict) -> None:
    assert_report_schema(linux_report, "scripts/sign-linux-artifact.sh", "linux")
    assert_report_schema(macos_report, "scripts/sign-macos-artifact.sh", "macos")
    assert linux_report["schema_version"] == macos_report["schema_version"]
    assert set(linux_report["scope"]) == set(macos_report["scope"])


def test_windows_report_shares_that_schema(windows_artifact: Path, tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    result = run_windows_script("-Report", str(report_path), str(windows_artifact))
    assert result.returncode == 0, result.stderr

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert_report_schema(report, "scripts/sign-windows-artifact.ps1", "windows")
    assert set(report["scope"]) == set(SCOPE_KEYS)


# --------------------------------------------------------------------------
# Release manifest
# --------------------------------------------------------------------------


def write_report(path: Path, **overrides: object) -> Path:
    """A synthetic per-platform report, for the aggregation paths only.

    These documents describe signatures nobody made. They exist to drive
    scripts/release-signing-manifest.sh, never to be published: the manifest
    the repository ships is generated from real runs.
    """
    report = {
        "schema_version": SCHEMA_VERSION,
        "tool": "scripts/sign-linux-artifact.sh",
        "target_platform": "linux",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "platform": {"system": "Linux", "machine": "x86_64", "release": "test"},
        "signing": {"method": "gpg-detached-armored"},
        "signed": False,
        "reason": "synthetic fixture",
        "manifest": None,
        "artifacts": [],
        "artifact_count": 0,
        "scope": dict.fromkeys(SCOPE_KEYS[:-1], False) | {"note": "synthetic fixture"},
    }
    report.update(overrides)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return path


def signed_report(path: Path, target: str, tool: str) -> Path:
    return write_report(
        path,
        tool=tool,
        target_platform=target,
        signed=True,
        reason="synthetic fixture: signed",
        artifacts=[
            {
                "path": f"dist/{target}-artifact",
                "size_bytes": 1,
                "sha256": "0" * 64,
                "signature": "synthetic",
                "signature_verified": True,
            }
        ],
        artifact_count=1,
    )


def run_manifest(tmp_path: Path, *args: str) -> tuple[subprocess.CompletedProcess[str], Path]:
    output = tmp_path / "release-signing-manifest.json"
    result = run_script(MANIFEST_SCRIPT, "--output", str(output), *args)
    return result, output


def test_manifest_records_every_platform_that_was_not_signed(tmp_path: Path) -> None:
    result, output = run_manifest(
        tmp_path,
        "--linux-report",
        str(tmp_path / "absent-linux.json"),
        "--macos-report",
        str(tmp_path / "absent-macos.json"),
        "--windows-report",
        str(tmp_path / "absent-windows.json"),
    )
    assert result.returncode == 0, result.stdout + result.stderr

    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert manifest["tool"] == "scripts/release-signing-manifest.sh"
    assert manifest["schema_version"] == SCHEMA_VERSION
    assert sorted(manifest["platforms"]) == ["linux", "macos", "windows"]
    assert manifest["missing_reports"] == ["linux", "macos", "windows"]
    assert manifest["signed_platforms"] == []
    assert manifest["fully_signed"] is False
    assert manifest["artifact_count"] == 0
    for entry in manifest["platforms"].values():
        assert entry["present"] is False
        assert entry["signed"] is False
        assert "no report at" in entry["reason"]
    assert "no Apple Developer ID" in manifest["note"]


def test_manifest_aggregates_real_unsigned_reports(
    linux_report: dict, macos_report: dict, tmp_path: Path
) -> None:
    linux_path = write_report(tmp_path / "linux.json", **linux_report)
    macos_path = write_report(tmp_path / "macos.json", **macos_report)

    result, output = run_manifest(
        tmp_path,
        "--linux-report",
        str(linux_path),
        "--macos-report",
        str(macos_path),
        "--windows-report",
        str(tmp_path / "absent-windows.json"),
        "--version",
        "9.9.9",
    )
    assert result.returncode == 0, result.stdout + result.stderr

    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert manifest["release_version"] == "9.9.9"
    assert manifest["unsigned_platforms"] == ["linux", "macos"]
    assert manifest["missing_reports"] == ["windows"]
    assert manifest["fully_signed"] is False
    assert manifest["artifact_count"] == (
        linux_report["artifact_count"] + macos_report["artifact_count"]
    )
    assert manifest["platforms"]["linux"]["signing_method"] == "gpg-detached-armored"
    assert manifest["platforms"]["macos"]["notarized"] is False


def test_manifest_is_fully_signed_only_when_all_three_are(tmp_path: Path) -> None:
    result, output = run_manifest(
        tmp_path,
        "--linux-report",
        str(signed_report(tmp_path / "l.json", "linux", "scripts/sign-linux-artifact.sh")),
        "--macos-report",
        str(signed_report(tmp_path / "m.json", "macos", "scripts/sign-macos-artifact.sh")),
        "--windows-report",
        str(signed_report(tmp_path / "w.json", "windows", "scripts/sign-windows-artifact.ps1")),
        "--require-all-signed",
    )
    assert result.returncode == 0, result.stdout + result.stderr

    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert manifest["signed_platforms"] == ["linux", "macos", "windows"]
    assert manifest["unsigned_platforms"] == []
    assert manifest["fully_signed"] is True


def test_manifest_require_signed_fails_on_an_unsigned_platform(tmp_path: Path) -> None:
    result, output = run_manifest(
        tmp_path,
        "--linux-report",
        str(write_report(tmp_path / "linux.json")),
        "--macos-report",
        str(tmp_path / "absent.json"),
        "--windows-report",
        str(tmp_path / "absent-windows.json"),
        "--require-signed",
        "macos",
    )
    assert result.returncode != 0
    # The manifest is still written: the unsigned state is the finding.
    assert output.is_file()
    assert json.loads(output.read_text(encoding="utf-8"))["fully_signed"] is False


def test_manifest_refuses_a_report_filed_under_the_wrong_platform(tmp_path: Path) -> None:
    macos_shaped = write_report(
        tmp_path / "macos.json",
        tool="scripts/sign-macos-artifact.sh",
        target_platform="macos",
    )
    result, output = run_manifest(tmp_path, "--linux-report", str(macos_shaped))
    assert result.returncode == 1
    assert "macos report but was passed as the linux report" in result.stderr
    assert not output.exists()


def test_manifest_refuses_a_signature_claim_with_nothing_verified(tmp_path: Path) -> None:
    """signed=true and no verified artifact is the exact lie worth catching."""
    forged = write_report(
        tmp_path / "linux.json",
        signed=True,
        reason="claims a signature",
        artifacts=[
            {
                "path": "dist/audio-studio.deb",
                "size_bytes": 1,
                "sha256": "0" * 64,
                "signature": "dist/audio-studio.deb.asc",
                "signature_verified": False,
            }
        ],
        artifact_count=1,
    )
    result, output = run_manifest(tmp_path, "--linux-report", str(forged))
    assert result.returncode == 1
    assert "signature_verified" in result.stderr
    assert not output.exists()


def test_manifest_refuses_a_malformed_report(tmp_path: Path) -> None:
    broken = tmp_path / "linux.json"
    broken.write_text("{not json", encoding="utf-8")
    result, _ = run_manifest(tmp_path, "--linux-report", str(broken))
    assert result.returncode == 1
    assert "not valid JSON" in result.stderr

    incomplete = write_report(tmp_path / "incomplete.json")
    document = json.loads(incomplete.read_text(encoding="utf-8"))
    del document["scope"]
    incomplete.write_text(json.dumps(document), encoding="utf-8")
    result, _ = run_manifest(tmp_path, "--linux-report", str(incomplete))
    assert result.returncode == 1
    assert "missing report fields: scope" in result.stderr


def test_manifest_rejects_an_unknown_platform(tmp_path: Path) -> None:
    result, _ = run_manifest(tmp_path, "--require-signed", "solaris")
    assert result.returncode == 2


@pytest.mark.skipif(
    not COMMITTED_MANIFEST.is_file(), reason="no published release-signing manifest"
)
def test_the_published_manifest_says_what_is_unsigned() -> None:
    manifest = json.loads(COMMITTED_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["tool"] == "scripts/release-signing-manifest.sh"
    assert sorted(manifest["platforms"]) == ["linux", "macos", "windows"]
    assert manifest["signed_platforms"] == [], (
        "this project has no signing credentials; a published manifest that "
        "claims a signed platform is either stale or wrong"
    )
    assert manifest["fully_signed"] is False
