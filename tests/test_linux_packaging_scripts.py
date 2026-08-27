"""Contract tests for the Linux packaging and signing wrappers.

The wrappers are shell, so two kinds of check live here. The static ones read
the sources: every script has to be executable, fail fast, and route its
licence gate through scripts/lib/linux-packaging.sh rather than reimplementing
a weaker version of it. The functional ones run the scripts against a
synthetic one-dir bundle in a temporary directory, which is what actually
proves the gate fires and that the notices survive into the AppDir and the
.deb.

The bundle fixture is a stand-in for PyInstaller output: a launcher, two
shared objects standing for the LGPL libraries, and the notices where
scripts/build-linux.sh puts them. That is everything the packaging scripts
look at, and it keeps this suite runnable without a 200 MB build.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
PACKAGING_LIB = SCRIPTS_DIR / "lib" / "linux-packaging.sh"
APPIMAGE_SCRIPT = SCRIPTS_DIR / "package-appimage.sh"
DEB_SCRIPT = SCRIPTS_DIR / "package-deb.sh"
SIGN_SCRIPT = SCRIPTS_DIR / "sign-linux-artifact.sh"

PACKAGING_SCRIPTS = (APPIMAGE_SCRIPT, DEB_SCRIPT, SIGN_SCRIPT)
ALL_SOURCES = (*PACKAGING_SCRIPTS, PACKAGING_LIB)

LICENSE_NOTICES = ("THIRD_PARTY_LICENSES.md", "LGPL-RELINKING.txt")

#: Signing programs for other platforms. This repository has no Apple
#: Developer ID and no Authenticode certificate, so an invocation of any of
#: these would be a claim the project cannot back.
FOREIGN_SIGNING_COMMANDS = ("codesign", "notarytool", "xcrun", "signtool", "osslsigncode")

DEFAULT_SIGNING_REPORT = ".agent_workspace/v1.1/linux-signing-report.json"


def run_script(
    script: Path, *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
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


@pytest.fixture(scope="module")
def bundle(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A minimal stand-in for a scripts/build-linux.sh one-dir bundle."""
    root = tmp_path_factory.mktemp("bundle") / "audio-studio"
    internal = root / "_internal"
    licenses = internal / "licenses"
    licenses.mkdir(parents=True)

    launcher = root / "audio-studio"
    launcher.write_text("#!/bin/sh\necho 'audio-studio (test bundle)'\n", encoding="utf-8")
    launcher.chmod(0o755)

    # Named for the real LGPL libraries: the gate looks for these by name.
    (internal / "libQt6Core.so.6").write_bytes(b"\x7fELF stand-in\n")
    (internal / "libsndfile.so.1").write_bytes(b"\x7fELF stand-in\n")

    shutil.copyfile(
        REPO_ROOT / "THIRD_PARTY_LICENSES.md", licenses / "THIRD_PARTY_LICENSES.md"
    )
    shutil.copyfile(
        REPO_ROOT / "packaging" / "LGPL-RELINKING.txt", licenses / "LGPL-RELINKING.txt"
    )
    return root


@pytest.fixture
def stripped_bundle(bundle: Path, tmp_path: Path) -> Path:
    """The same bundle with its licence notices removed."""
    copy = tmp_path / "unlicensed" / "audio-studio"
    shutil.copytree(bundle, copy)
    shutil.rmtree(copy / "_internal" / "licenses")
    return copy


# --------------------------------------------------------------------------
# Static checks
# --------------------------------------------------------------------------


@pytest.mark.parametrize("script", PACKAGING_SCRIPTS, ids=lambda path: path.name)
def test_script_is_executable_and_fails_fast(script: Path) -> None:
    assert script.is_file(), f"{script} is missing"
    assert script.stat().st_mode & stat.S_IXUSR, f"{script} is not executable"

    lines = script.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "#!/usr/bin/env bash"
    assert "set -Eeuo pipefail" in lines, f"{script.name} does not fail fast"


@pytest.mark.parametrize("source", ALL_SOURCES, ids=lambda path: path.name)
def test_script_parses(source: Path) -> None:
    result = subprocess.run(
        ["bash", "-n", str(source)], capture_output=True, text=True, timeout=60, check=False
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("source", ALL_SOURCES, ids=lambda path: path.name)
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


@pytest.mark.parametrize("script", PACKAGING_SCRIPTS, ids=lambda path: path.name)
def test_scripts_share_one_licence_gate(script: Path) -> None:
    text = script.read_text(encoding="utf-8")
    assert "scripts/lib/linux-packaging.sh" in text


@pytest.mark.parametrize("script", (APPIMAGE_SCRIPT, DEB_SCRIPT), ids=lambda path: path.name)
def test_packaging_scripts_gate_input_and_output(script: Path) -> None:
    """The gate has to run on the produced tree, not only on the input."""
    text = script.read_text(encoding="utf-8")
    calls = re.findall(r"^\s*bundle_license_gate\s", text, flags=re.MULTILINE)
    assert len(calls) >= 2, f"{script.name} gates fewer than two trees"
    assert "install_license_documents" in text


def test_licence_gate_checks_every_obligation() -> None:
    text = PACKAGING_LIB.read_text(encoding="utf-8")
    for notice in LICENSE_NOTICES:
        assert notice in text, f"the gate never mentions {notice}"
    # A one-file build would defeat LGPL relinking, and pedalboard would
    # relicense the artifact; both are refusals, not warnings.
    assert "require_replaceable_lgpl_libraries" in text
    assert "reject_gpl_payload" in text
    assert 'GPL_PAYLOAD="pedalboard"' in text


@pytest.mark.parametrize("source", ALL_SOURCES, ids=lambda path: path.name)
def test_no_foreign_platform_signing_is_invoked(source: Path) -> None:
    """Linux GPG only: nothing here may call a macOS or Windows signing tool."""
    pattern = re.compile(rf"^\s*(?:sudo\s+)?({'|'.join(FOREIGN_SIGNING_COMMANDS)})\b")
    offenders = [
        line for line in source.read_text(encoding="utf-8").splitlines() if pattern.match(line)
    ]
    assert not offenders, f"{source.name} invokes a non-Linux signing tool: {offenders}"


def test_sign_script_defaults_to_the_v11_report_path() -> None:
    assert DEFAULT_SIGNING_REPORT in SIGN_SCRIPT.read_text(encoding="utf-8")


def test_appimage_script_documents_the_manual_appimagetool_step() -> None:
    text = APPIMAGE_SCRIPT.read_text(encoding="utf-8")
    assert "--appdir-only" in text
    assert "appimagetool" in text
    assert "appimage-extract-and-run" in text, "no guidance for FUSE-less environments"


@pytest.mark.parametrize("script", PACKAGING_SCRIPTS, ids=lambda path: path.name)
def test_help_exits_cleanly(script: Path) -> None:
    result = run_script(script, "--help")
    assert result.returncode == 0, result.stderr
    assert "Usage:" in result.stdout


@pytest.mark.parametrize("script", PACKAGING_SCRIPTS, ids=lambda path: path.name)
def test_unknown_option_is_rejected(script: Path) -> None:
    result = run_script(script, "--not-an-option")
    assert result.returncode == 2, result.stdout + result.stderr


# --------------------------------------------------------------------------
# AppImage wrapper
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def appdir(bundle: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("appimage-out")
    result = run_script(
        APPIMAGE_SCRIPT,
        "--bundle",
        str(bundle),
        "--output-dir",
        str(output),
        "--appdir-only",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return output / "AudioStudio.AppDir"


def test_appdir_has_the_spec_shaped_entry_points(appdir: Path) -> None:
    apprun = appdir / "AppRun"
    assert apprun.is_file()
    assert apprun.stat().st_mode & stat.S_IXUSR, "AppRun is not executable"
    assert "audio-studio" in apprun.read_text(encoding="utf-8")

    desktop = (appdir / "audio-studio.desktop").read_text(encoding="utf-8")
    assert "[Desktop Entry]" in desktop
    assert "Exec=audio-studio" in desktop
    assert "Icon=audio-studio" in desktop
    assert (appdir / "audio-studio.svg").is_file()
    assert (appdir / "usr" / "share" / "applications" / "audio-studio.desktop").is_file()


def test_appdir_keeps_the_bundle_relinkable(appdir: Path) -> None:
    internal = appdir / "usr" / "lib" / "audio-studio" / "_internal"
    assert (internal / "libQt6Core.so.6").is_file()
    assert (internal / "libsndfile.so.1").is_file()
    assert (appdir / "usr" / "lib" / "audio-studio" / "audio-studio").stat().st_mode & stat.S_IXUSR


def test_appdir_carries_the_notices(appdir: Path) -> None:
    doc_dir = appdir / "usr" / "share" / "doc" / "audio-studio"
    for notice in LICENSE_NOTICES:
        assert (doc_dir / notice).is_file(), f"the AppDir lost {notice}"


def test_appimage_refuses_a_bundle_without_notices(stripped_bundle: Path, tmp_path: Path) -> None:
    result = run_script(
        APPIMAGE_SCRIPT,
        "--bundle",
        str(stripped_bundle),
        "--output-dir",
        str(tmp_path / "out"),
        "--appdir-only",
    )
    assert result.returncode != 0
    assert "THIRD_PARTY_LICENSES.md" in result.stderr


def test_appimage_refuses_a_flattened_bundle(bundle: Path, tmp_path: Path) -> None:
    """A bundle with no separate shared objects cannot be relinked."""
    flattened = tmp_path / "onefile" / "audio-studio"
    shutil.copytree(bundle, flattened)
    for library in (flattened / "_internal").glob("*.so*"):
        library.unlink()

    result = run_script(
        APPIMAGE_SCRIPT,
        "--bundle",
        str(flattened),
        "--output-dir",
        str(tmp_path / "out"),
        "--appdir-only",
    )
    assert result.returncode != 0
    assert "onefile" in result.stderr


def test_appimage_reports_a_missing_appimagetool_instead_of_guessing(
    bundle: Path, tmp_path: Path
) -> None:
    if shutil.which("appimagetool") is not None:
        pytest.skip("appimagetool is installed, so the fallback path is not exercised")

    result = run_script(
        APPIMAGE_SCRIPT,
        "--bundle",
        str(bundle),
        "--output-dir",
        str(tmp_path / "out"),
        env={"APPIMAGETOOL": ""},
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "out" / "AudioStudio.AppDir").is_dir()
    assert "appimagetool" in result.stderr

    strict = run_script(
        APPIMAGE_SCRIPT,
        "--bundle",
        str(bundle),
        "--output-dir",
        str(tmp_path / "strict"),
        "--require-appimage",
        env={"APPIMAGETOOL": ""},
    )
    assert strict.returncode != 0


# --------------------------------------------------------------------------
# Debian wrapper
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def deb_tree(bundle: Path, tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    output = tmp_path_factory.mktemp("deb-out")
    result = run_script(
        DEB_SCRIPT,
        "--bundle",
        str(bundle),
        "--output-dir",
        str(output),
        "--version",
        "9.9.9",
        "--revision",
        "2",
        "--arch",
        "amd64",
        "--tree-only",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return output, output / "deb" / "audio-studio_9.9.9-2_amd64"


def test_deb_tree_control_describes_the_package(deb_tree: tuple[Path, Path]) -> None:
    _, tree = deb_tree
    control = (tree / "DEBIAN" / "control").read_text(encoding="utf-8")
    assert "Package: audio-studio" in control
    assert "Version: 9.9.9-2" in control
    assert "Architecture: amd64" in control
    assert re.search(r"^Maintainer: .+ <.+>$", control, flags=re.MULTILINE)
    assert re.search(r"^Installed-Size: \d+$", control, flags=re.MULTILINE)
    assert (tree / "DEBIAN" / "md5sums").read_text(encoding="utf-8").strip()


def test_deb_tree_installs_a_launcher_and_desktop_entry(deb_tree: tuple[Path, Path]) -> None:
    _, tree = deb_tree
    launcher = tree / "usr" / "bin" / "audio-studio"
    assert launcher.stat().st_mode & stat.S_IXUSR
    assert "/usr/lib/audio-studio/audio-studio" in launcher.read_text(encoding="utf-8")
    assert (tree / "usr" / "share" / "applications" / "audio-studio.desktop").is_file()
    assert (
        tree / "usr" / "share" / "icons" / "hicolor" / "scalable" / "apps" / "audio-studio.svg"
    ).is_file()


def test_deb_tree_carries_copyright_and_notices(deb_tree: tuple[Path, Path]) -> None:
    _, tree = deb_tree
    doc_dir = tree / "usr" / "share" / "doc" / "audio-studio"
    copyright_text = (doc_dir / "copyright").read_text(encoding="utf-8")
    assert "LGPL-3.0-only" in copyright_text
    assert "LGPL-RELINKING.txt" in copyright_text
    for notice in LICENSE_NOTICES:
        assert (doc_dir / notice).is_file(), f"the package lost {notice}"


def test_deb_refuses_a_bundle_without_notices(stripped_bundle: Path, tmp_path: Path) -> None:
    result = run_script(
        DEB_SCRIPT,
        "--bundle",
        str(stripped_bundle),
        "--output-dir",
        str(tmp_path / "out"),
        "--tree-only",
    )
    assert result.returncode != 0
    assert "THIRD_PARTY_LICENSES.md" in result.stderr


def test_deb_refuses_a_missing_bundle(tmp_path: Path) -> None:
    result = run_script(DEB_SCRIPT, "--bundle", str(tmp_path / "nope"), "--tree-only")
    assert result.returncode != 0
    assert "no bundle directory" in result.stderr


@pytest.fixture(scope="module")
def built_deb(bundle: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    if shutil.which("dpkg-deb") is None:
        pytest.skip("dpkg-deb is not installed")
    output = tmp_path_factory.mktemp("deb-build")
    result = run_script(
        DEB_SCRIPT,
        "--bundle",
        str(bundle),
        "--output-dir",
        str(output),
        "--version",
        "9.9.9",
        "--arch",
        "amd64",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    package = output / "audio-studio_9.9.9-1_amd64.deb"
    assert package.is_file()
    return package


def test_built_deb_contents_include_the_notices(built_deb: Path) -> None:
    contents = subprocess.run(
        ["dpkg-deb", "--contents", str(built_deb)],
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    ).stdout
    for required in (
        "./usr/bin/audio-studio",
        "./usr/lib/audio-studio/audio-studio",
        "./usr/share/doc/audio-studio/copyright",
        "./usr/share/doc/audio-studio/LGPL-RELINKING.txt",
        "./usr/share/doc/audio-studio/THIRD_PARTY_LICENSES.md",
    ):
        assert required in contents, f"the package is missing {required}"


def test_built_deb_owns_its_files_as_root(built_deb: Path) -> None:
    """--root-owner-group: a package that ships builder uids is unusable."""
    contents = subprocess.run(
        ["dpkg-deb", "--contents", str(built_deb)],
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    ).stdout
    assert "root/root" in contents
    assert re.search(r"\b\d{4,}/\d{4,}\b", contents) is None


# --------------------------------------------------------------------------
# Signing scaffold
# --------------------------------------------------------------------------


def sign(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return run_script(SIGN_SCRIPT, *args, env=env)


@pytest.fixture
def artifacts(tmp_path: Path) -> list[Path]:
    directory = tmp_path / "release"
    directory.mkdir()
    first = directory / "audio-studio-9.9.9-x86_64.AppImage"
    second = directory / "audio-studio_9.9.9-1_amd64.deb"
    first.write_bytes(b"pretend AppImage payload\n")
    second.write_bytes(b"pretend deb payload\n")
    return [first, second]


def test_unsigned_run_is_honest_and_still_checksums(
    artifacts: list[Path], tmp_path: Path
) -> None:
    report_path = tmp_path / "linux-signing-report.json"
    result = sign(
        "--report", str(report_path), *[str(path) for path in artifacts], env={"SIGNING_KEY": ""}
    )
    assert result.returncode == 0, result.stdout + result.stderr

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["schema_version"] == 1
    assert report["tool"] == "scripts/sign-linux-artifact.sh"
    assert report["signed"] is False
    assert report["signing"]["key_requested"] is False
    assert report["signing"]["key_fingerprint"] is None
    assert "SIGNING_KEY" in report["reason"]
    assert report["artifact_count"] == len(artifacts)

    for path, described in zip(artifacts, report["artifacts"], strict=True):
        assert described["path"].endswith(path.name)
        assert described["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        assert described["size_bytes"] == path.stat().st_size
        assert described["signature"] is None
        assert described["signature_verified"] is False
        assert not path.with_name(path.name + ".asc").exists()


def test_manifest_verifies_with_sha256sum(artifacts: list[Path], tmp_path: Path) -> None:
    result = sign(
        "--report",
        str(tmp_path / "report.json"),
        *[str(path) for path in artifacts],
        env={"SIGNING_KEY": ""},
    )
    assert result.returncode == 0, result.stderr

    manifest = artifacts[0].parent / "SHA256SUMS"
    assert manifest.is_file()
    check = subprocess.run(
        ["sha256sum", "--check", "--strict", manifest.name],
        cwd=manifest.parent,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert check.returncode == 0, check.stdout + check.stderr


def test_report_denies_other_platform_signing(artifacts: list[Path], tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    result = sign(
        "--report", str(report_path), str(artifacts[0]), env={"SIGNING_KEY": ""}
    )
    assert result.returncode == 0, result.stderr

    scope = json.loads(report_path.read_text(encoding="utf-8"))["scope"]
    assert scope["linux_gpg_detached_signature"] is False
    assert scope["macos_codesign"] is False
    assert scope["macos_notarization"] is False
    assert scope["windows_authenticode"] is False
    assert "Linux GPG" in scope["note"]


def test_require_signature_fails_without_a_key(artifacts: list[Path], tmp_path: Path) -> None:
    result = sign(
        "--report",
        str(tmp_path / "report.json"),
        "--require-signature",
        str(artifacts[0]),
        env={"SIGNING_KEY": ""},
    )
    assert result.returncode != 0
    assert "SIGNING_KEY" in result.stderr


def test_missing_artifact_is_refused(tmp_path: Path) -> None:
    result = sign("--report", str(tmp_path / "report.json"), str(tmp_path / "absent.deb"))
    assert result.returncode != 0
    assert "no such artifact" in result.stderr


def test_directory_artifact_is_refused(tmp_path: Path, appdir: Path) -> None:
    result = sign("--report", str(tmp_path / "report.json"), str(appdir))
    assert result.returncode != 0
    assert "not a regular file" in result.stderr


@pytest.fixture
def scratch_gpg_key(tmp_path: Path) -> tuple[str, str]:
    """An ephemeral signing key in a throwaway keyring."""
    if shutil.which("gpg") is None:
        pytest.skip("gpg is not installed")
    home = tmp_path / "gnupg"
    home.mkdir(mode=0o700)
    uid = "Audio Studio Packaging Test <packaging-test@example.invalid>"
    generated = subprocess.run(
        [
            "gpg",
            "--batch",
            "--quiet",
            "--passphrase",
            "",
            "--quick-generate-key",
            uid,
            "ed25519",
            "sign",
            "never",
        ],
        env={**os.environ, "GNUPGHOME": str(home)},
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if generated.returncode != 0:
        pytest.skip(f"cannot generate a scratch gpg key here: {generated.stderr.strip()}")
    return str(home), uid


def test_signed_run_produces_verifiable_signatures(
    artifacts: list[Path], tmp_path: Path, scratch_gpg_key: tuple[str, str]
) -> None:
    home, uid = scratch_gpg_key
    report_path = tmp_path / "report.json"
    result = sign(
        "--report",
        str(report_path),
        *[str(path) for path in artifacts],
        env={"SIGNING_KEY": uid, "GNUPGHOME": home},
    )
    assert result.returncode == 0, result.stdout + result.stderr

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["signed"] is True
    assert report["signing"]["key_requested"] is True
    assert re.fullmatch(r"[0-9A-F]{40}", report["signing"]["key_fingerprint"])
    assert report["scope"]["linux_gpg_detached_signature"] is True
    assert report["scope"]["macos_codesign"] is False
    assert report["scope"]["windows_authenticode"] is False

    manifest = artifacts[0].parent / "SHA256SUMS"
    for path in (*artifacts, manifest):
        signature = path.with_name(path.name + ".asc")
        assert signature.is_file(), f"no detached signature for {path.name}"
        assert "BEGIN PGP SIGNATURE" in signature.read_text(encoding="utf-8")
        verified = subprocess.run(
            ["gpg", "--batch", "--verify", str(signature), str(path)],
            env={**os.environ, "GNUPGHOME": home},
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        assert verified.returncode == 0, verified.stderr

    for described in report["artifacts"] + [report["manifest"]]:
        assert described["signature"].endswith(".asc")
        assert described["signature_verified"] is True


def test_unknown_key_fails_loudly(
    artifacts: list[Path], tmp_path: Path, scratch_gpg_key: tuple[str, str]
) -> None:
    home, _ = scratch_gpg_key
    result = sign(
        "--report",
        str(tmp_path / "report.json"),
        str(artifacts[0]),
        env={"SIGNING_KEY": "nobody@example.invalid", "GNUPGHOME": home},
    )
    assert result.returncode != 0
    assert "does not know the key" in result.stderr
