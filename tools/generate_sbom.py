#!/usr/bin/env python3
"""Generate the software bill of materials for the Linux desktop bundle.

Produces three JSON artifacts:

- ``.agent_workspace/v1.1/linux-sbom.json`` — a CycloneDX-1.5-shaped BOM of the
  built bundle: every Python distribution in the build environment (annotated
  with its distribution profile and whether evidence of it exists inside the
  bundle) plus the native shared libraries that PyInstaller collected.
- ``packaging/SBOM.json`` — an SPDX-2.3-shaped document derived from the build
  virtualenv alone. It is written even when no bundle exists, so a partially
  failed build still leaves a reviewable dependency inventory.
- ``.agent_workspace/v1.1/linux-build-report.json`` — the distribution gate
  report: launcher hash, bundle size, LGPL replaceability evidence, licence
  notice presence, and the pedalboard-absence check.

The licence policy encoded here mirrors ``THIRD_PARTY_LICENSES.md``: the
default profile must contain no GPL component, and pedalboard may never appear
in a bundle. Licences are taken from each wheel's own metadata first and only
fall back to the curated table for wheels whose metadata is vague.

Run from the repository root::

    python tools/generate_sbom.py

The tool introspects ``audio-studio/.venv`` through a subprocess, so the
interpreter running this script does not have to be the build interpreter.
Exit status is 0 when every distribution check passes and 1 otherwise; the
SBOM files are written in both cases.
"""

from __future__ import annotations

import argparse
import ast
import datetime as _dt
import hashlib
import json
import platform
import re
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TOOL_NAME = "tools/generate_sbom.py"
SCHEMA_VERSION = 1

#: Distribution profiles from THIRD_PARTY_LICENSES.md / audio-studio/pyproject.toml.
#: "default" is what a plain ``pip install audio-studio`` resolves (including
#: its transitive closure); everything else is opt-in or build/dev tooling.
PROFILE_BY_DIST = {
    "numpy": "default",
    "scipy": "default",
    "soundfile": "default",
    "pyside6-essentials": "default",
    "pyside6": "default",
    "shiboken6": "default",
    "cffi": "default",  # soundfile transitive
    "pycparser": "default",  # cffi transitive
    "sounddevice": "audio",
    "pyaudio": "audio",
    "soxr": "mastering",
    "pedalboard": "plugins",
    "pyinstaller": "installer",
    "pyinstaller-hooks-contrib": "installer",
    "altgraph": "installer",
    "pip": "build-tooling",
    "setuptools": "build-tooling",
    "wheel": "build-tooling",
    "packaging": "build-tooling",
    "pytest": "dev",
    "pytest-qt": "dev",
    "pytest-cov": "dev",
    "pluggy": "dev",
    "iniconfig": "dev",
    "pygments": "dev",
    "mypy": "dev",
    "mypy-extensions": "dev",
    "pathspec": "dev",
    "ruff": "dev",
    "typing-extensions": "dev",
}

#: GPL-3.0 components that must never be bundled (see THIRD_PARTY_LICENSES.md).
FORBIDDEN_IN_BUNDLE = {"pedalboard"}

#: For dual-licensed components the wheel declares every alternative; this is
#: the licence Audio Studio distributes under (THIRD_PARTY_LICENSES.md:
#: "this project selects LGPL-3.0").
SELECTED_LICENSE_BY_DIST = {
    "pyside6-essentials": "LGPL-3.0-only",
    "pyside6": "LGPL-3.0-only",
    "shiboken6": "LGPL-3.0-only",
}

#: Fallback SPDX expressions for wheels whose metadata carries no usable
#: licence field. Sourced from THIRD_PARTY_LICENSES.md; wheel metadata wins.
LICENSE_FALLBACK_BY_DIST = {
    "numpy": "BSD-3-Clause",
    "scipy": "BSD-3-Clause",
    "soundfile": "BSD-3-Clause",
    "pyside6-essentials": "LGPL-3.0-only",
    "pyside6": "LGPL-3.0-only",
    "shiboken6": "LGPL-3.0-only",
    "cffi": "MIT-0",
    "pycparser": "BSD-3-Clause",
    "sounddevice": "MIT",
    "pyaudio": "MIT",
    "soxr": "LGPL-2.1-or-later",
    "pedalboard": "GPL-3.0-only",
    "pyinstaller": "GPL-2.0-or-later WITH Bootloader-exception",
    "pyinstaller-hooks-contrib": "Apache-2.0 OR GPL-2.0-or-later",
    "altgraph": "MIT",
    "pip": "MIT",
    "setuptools": "MIT",
    "wheel": "MIT",
    "packaging": "Apache-2.0 OR BSD-2-Clause",
    "pytest": "MIT",
    "pytest-qt": "MIT",
    "pluggy": "MIT",
    "iniconfig": "MIT",
    "pygments": "BSD-2-Clause",
    "mypy": "MIT",
    "mypy-extensions": "MIT",
    "pathspec": "MPL-2.0",
    "ruff": "MIT",
    "typing-extensions": "PSF-2.0",
    "pyyaml": "MIT",
    "audio-studio": "MIT",
}

#: Licences for native shared objects the bundle scan can encounter, matched
#: by soname prefix. Everything not matched is reported as NOASSERTION: those
#: are host system libraries PyInstaller copied, and their licence must be
#: read from the exact release artifact, not guessed here.
NATIVE_LICENSE_BY_PREFIX = (
    ("libQt6", "LGPL-3.0-only"),
    ("libpyside6", "LGPL-3.0-only"),
    ("libshiboken6", "LGPL-3.0-only"),
    ("libsndfile", "LGPL-2.1-or-later"),
    ("libportaudio", "MIT"),
    ("libscipy_openblas", "BSD-3-Clause"),
    ("libgfortran", "GPL-3.0-or-later WITH GCC-exception-3.1"),
    ("libquadmath", "LGPL-2.1-or-later"),
    ("libsoxr", "LGPL-2.1-or-later"),
    ("libpython3", "PSF-2.0"),
    ("libFLAC", "BSD-3-Clause"),
    ("libogg", "BSD-3-Clause"),
    ("libvorbis", "BSD-3-Clause"),
    ("libopus", "BSD-3-Clause"),
    ("libmpg123", "LGPL-2.1-only"),
    ("libmp3lame", "LGPL-2.0-or-later"),
)

#: Directories inside the bundle whose shared objects carry licence
#: obligations of their own; the rest of _internal is host-system copies.
NATIVE_SCAN_SUBDIRS = (
    ".",
    "_soundfile_data",
    "numpy.libs",
    "scipy.libs",
    "PySide6/Qt/lib",
)

_VENV_DUMP_SCRIPT = r"""
import json, sys
from importlib import metadata

dists = []
for dist in metadata.distributions():
    meta = dist.metadata
    name = (meta.get("Name") or "").strip()
    if not name:
        continue
    top_level = []
    try:
        text = dist.read_text("top_level.txt")
        if text:
            top_level = text.split()
    except Exception:
        pass
    if not top_level:
        seen = set()
        for f in dist.files or []:
            first = f.parts[0] if f.parts else ""
            if not first or first.endswith((".dist-info", ".egg-info")) or first == "..":
                continue
            if first.endswith(".py"):
                first = first[:-3]
            elif ".so" in first:
                first = first.split(".", 1)[0]
            elif "." in first:
                continue
            seen.add(first)
        top_level = sorted(seen)
    classifiers = [c for c in meta.get_all("Classifier") or [] if c.startswith("License ::")]
    dists.append(
        {
            "name": name,
            "version": dist.version or "0",
            "license_expression": (meta.get("License-Expression") or "").strip(),
            "license_field": (meta.get("License") or "").strip(),
            "license_classifiers": classifiers,
            "top_level": top_level,
            "requires": meta.get_all("Requires-Dist") or [],
        }
    )
json.dump(
    {"python_version": sys.version.split()[0], "distributions": dists},
    sys.stdout,
)
"""

#: License classifier suffix -> SPDX id, for wheels that only declare trove
#: classifiers. Deliberately small: unmapped classifiers fall through to the
#: curated table and finally to NOASSERTION.
_CLASSIFIER_TO_SPDX = {
    "MIT License": "MIT",
    "BSD License": "BSD-3-Clause",
    "Apache Software License": "Apache-2.0",
    "ISC License (ISCL)": "ISC",
    "Python Software Foundation License": "PSF-2.0",
    "GNU General Public License v3 (GPLv3)": "GPL-3.0-only",
    "GNU Lesser General Public License v3 (LGPLv3)": "LGPL-3.0-only",
    "GNU Library or Lesser General Public License (LGPL)": "LGPL-2.1-or-later",
    "Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
}


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def repo_relative(path: Path) -> str:
    """Repository-relative path when possible, absolute otherwise."""
    try:
        return str(path.resolve().relative_to(REPOSITORY_ROOT))
    except ValueError:
        return str(path.resolve())


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_unexceptioned_gpl(alternative: str) -> bool:
    """True for a plain GPL licence: not LGPL and not covered by an exception."""
    return (
        bool(re.search(r"(?<!L)GPL", alternative))
        and "exception" not in alternative.lower()
    )


def concluded_license(name: str, declared: str) -> str:
    """The licence this project actually receives the component under.

    A dual-licensed declaration (``A OR B``) lets the recipient choose; the
    project's choice is curated in ``SELECTED_LICENSE_BY_DIST``, defaulting to
    the declared expression when no choice is needed or recorded.
    """
    selected = SELECTED_LICENSE_BY_DIST.get(normalize(name))
    if selected and selected in declared.split(" OR "):
        return selected
    return declared


def resolve_license(dist: dict[str, Any]) -> tuple[str, str]:
    """Return ``(spdx_expression, source)`` for one venv distribution."""
    expression = dist["license_expression"]
    if expression:
        return expression, "wheel-metadata:license-expression"
    field = dist["license_field"]
    # Old-style License fields are free text; accept only short expressions.
    if field and len(field) <= 64 and "\n" not in field:
        return field, "wheel-metadata:license-field"
    for classifier in dist["license_classifiers"]:
        suffix = classifier.rsplit("::", 1)[-1].strip()
        if suffix in _CLASSIFIER_TO_SPDX:
            return _CLASSIFIER_TO_SPDX[suffix], "wheel-metadata:classifier"
    fallback = LICENSE_FALLBACK_BY_DIST.get(normalize(dist["name"]))
    if fallback:
        return fallback, "curated:THIRD_PARTY_LICENSES.md"
    return "NOASSERTION", "unresolved"


def dump_venv(python_bin: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [str(python_bin), "-c", _VENV_DUMP_SCRIPT],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)


def pip_freeze(python_bin: Path) -> list[str]:
    proc = subprocess.run(
        [str(python_bin), "-m", "pip", "freeze", "--all"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in proc.stdout.splitlines() if line.strip()]


def pyz_site_package_roots(work_dir: Path) -> set[str] | None:
    """Top-level site-packages module names frozen into the PYZ archive.

    Returns ``None`` when the PyInstaller work directory is unavailable, so a
    missing build degrades to directory-scan evidence instead of an error.
    """
    toc_path = work_dir / "PYZ-00.toc"
    if not toc_path.is_file():
        return None
    try:
        _pyz, entries = ast.literal_eval(toc_path.read_text(encoding="utf-8"))
    except (ValueError, SyntaxError):
        return None
    roots: set[str] = set()
    for module_name, source_path, _kind in entries:
        source = str(source_path)
        # site-packages covers third-party wheels; the repository-root prefix
        # covers the editable install of audio-studio itself.
        if "/site-packages/" not in source and not source.startswith(str(REPOSITORY_ROOT)):
            continue
        roots.add(module_name.split(".", 1)[0])
    return roots


def scan_bundle(bundle: Path) -> dict[str, Any]:
    """Collect distribution-gate evidence from the built one-dir bundle."""
    launcher = bundle / "audio-studio"
    internal = bundle / "_internal"
    if not launcher.is_file() or not internal.is_dir():
        return {"present": False, "path": repo_relative(bundle)}

    total_bytes = 0
    file_count = 0
    pedalboard_hits: list[str] = []
    for path in bundle.rglob("*"):
        if not path.is_file():
            continue
        file_count += 1
        total_bytes += path.stat().st_size
        if "pedalboard" in path.name.lower():
            pedalboard_hits.append(str(path.relative_to(bundle)))

    qt_libs = sorted(
        str(p.relative_to(bundle))
        for pattern in ("libQt6Core.so*", "libpyside6*")
        for p in bundle.rglob(pattern)
    )
    notices = {
        name: (internal / "licenses" / name).is_file() or (bundle / "licenses" / name).is_file()
        for name in ("THIRD_PARTY_LICENSES.md", "LGPL-RELINKING.txt")
    }

    natives: dict[str, dict[str, Any]] = {}
    for subdir in NATIVE_SCAN_SUBDIRS:
        directory = internal / subdir if subdir != "." else internal
        if not directory.is_dir():
            continue
        for so_path in directory.glob("*.so*"):
            if not so_path.is_file():
                continue
            soname = so_path.name
            license_id = "NOASSERTION"
            for prefix, spdx in NATIVE_LICENSE_BY_PREFIX:
                if soname.startswith(prefix):
                    license_id = spdx
                    break
            record = natives.setdefault(
                soname, {"soname": soname, "license": license_id, "paths": []}
            )
            record["paths"].append(str(so_path.relative_to(bundle)))
    for record in natives.values():
        record["paths"].sort()

    return {
        "present": True,
        "path": repo_relative(bundle),
        "launcher_sha256": sha256_of(launcher),
        "launcher_bytes": launcher.stat().st_size,
        "total_bytes": total_bytes,
        "file_count": file_count,
        "qt_shared_libraries": qt_libs,
        "license_notices_present": notices,
        "pedalboard_artifacts": sorted(pedalboard_hits),
        "native_libraries": [natives[k] for k in sorted(natives)],
    }


def classify_components(
    venv: dict[str, Any],
    bundle_info: dict[str, Any],
    pyz_roots: set[str] | None,
) -> list[dict[str, Any]]:
    internal = None
    if bundle_info["present"]:
        internal = REPOSITORY_ROOT / bundle_info["path"] / "_internal"

    components = []
    for dist in sorted(venv["distributions"], key=lambda d: normalize(d["name"])):
        norm = normalize(dist["name"])
        declared, license_source = resolve_license(dist)
        license_id = concluded_license(norm, declared)
        profile = PROFILE_BY_DIST.get(norm, "environment")
        if norm == "audio-studio":
            profile = "application"

        evidence: list[str] = []
        if internal is not None:
            for top in dist["top_level"]:
                if (internal / top).is_dir():
                    evidence.append(f"bundle-dir:_internal/{top}")
                elif list(internal.glob(f"{top}*.so*")):
                    evidence.append(f"bundle-so:_internal/{top}*.so")
        if pyz_roots is not None:
            for top in dist["top_level"]:
                if top in pyz_roots:
                    evidence.append(f"pyz-module:{top}")

        components.append(
            {
                "type": "application" if norm == "audio-studio" else "library",
                "bom-ref": f"pkg:pypi/{norm}@{dist['version']}",
                "name": norm,
                "version": dist["version"],
                "purl": f"pkg:pypi/{norm}@{dist['version']}",
                "licenses": [{"license": {"id": license_id}}],
                "properties": [
                    {"name": "audio-studio:profile", "value": profile},
                    {"name": "audio-studio:bundled", "value": str(bool(evidence)).lower()},
                    {"name": "audio-studio:bundle-evidence", "value": ";".join(sorted(evidence)) or "absent"},
                    {"name": "audio-studio:license-source", "value": license_source},
                    {"name": "audio-studio:license-declared", "value": declared},
                ],
            }
        )
    return components


def build_cyclonedx(
    app_version: str,
    components: list[dict[str, Any]],
    bundle_info: dict[str, Any],
    venv: dict[str, Any],
    freeze_lines: list[str],
) -> dict[str, Any]:
    native_components = []
    for native in bundle_info.get("native_libraries", []):
        native_components.append(
            {
                "type": "library",
                "bom-ref": f"native:{native['soname']}",
                "name": native["soname"],
                "version": "bundled",
                "licenses": [{"license": {"id": native["license"]}}],
                "properties": [
                    {"name": "audio-studio:profile", "value": "native"},
                    {"name": "audio-studio:bundled", "value": "true"},
                    {"name": "audio-studio:bundle-evidence", "value": ";".join(native["paths"])},
                    {
                        "name": "audio-studio:license-source",
                        "value": (
                            "curated:THIRD_PARTY_LICENSES.md"
                            if native["license"] != "NOASSERTION"
                            else "unresolved:system-library"
                        ),
                    },
                ],
            }
        )

    properties = [
        {"name": "audio-studio:schema-version", "value": str(SCHEMA_VERSION)},
        {"name": "audio-studio:platform", "value": platform.platform()},
        {"name": "audio-studio:build-python", "value": venv["python_version"]},
        {"name": "audio-studio:bundle-present", "value": str(bundle_info["present"]).lower()},
        {
            "name": "audio-studio:pip-freeze-sha256",
            "value": hashlib.sha256("\n".join(freeze_lines).encode()).hexdigest(),
        },
    ]
    if bundle_info["present"]:
        properties += [
            {"name": "audio-studio:bundle-path", "value": bundle_info["path"]},
            {"name": "audio-studio:launcher-sha256", "value": bundle_info["launcher_sha256"]},
            {"name": "audio-studio:bundle-bytes", "value": str(bundle_info["total_bytes"])},
        ]

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": utc_now(),
            "tools": [{"vendor": "audio-studio", "name": TOOL_NAME, "version": "1.0"}],
            "component": {
                "type": "application",
                "bom-ref": f"pkg:pypi/audio-studio@{app_version}",
                "name": "audio-studio",
                "version": app_version,
                "licenses": [{"license": {"id": "MIT"}}],
                "purl": f"pkg:pypi/audio-studio@{app_version}",
            },
            "properties": properties,
        },
        "components": components + native_components,
    }


def build_spdx(app_version: str, components: list[dict[str, Any]]) -> dict[str, Any]:
    """SPDX-2.3-shaped document from the venv inventory only (no bundle)."""
    packages = []
    relationships = [
        {
            "spdxElementId": "SPDXRef-DOCUMENT",
            "relationshipType": "DESCRIBES",
            "relatedSpdxElement": "SPDXRef-Package-audio-studio",
        }
    ]
    for component in components:
        properties = {p["name"]: p["value"] for p in component["properties"]}
        license_id = component["licenses"][0]["license"]["id"]
        profile = properties["audio-studio:profile"]
        spdx_id = "SPDXRef-Package-" + re.sub(r"[^A-Za-z0-9.-]", "-", component["name"])
        packages.append(
            {
                "SPDXID": spdx_id,
                "name": component["name"],
                "versionInfo": component["version"],
                "downloadLocation": f"https://pypi.org/project/{component['name']}/{component['version']}/",
                "licenseConcluded": license_id,
                "licenseDeclared": properties["audio-studio:license-declared"],
                "supplier": "NOASSERTION",
                "filesAnalyzed": False,
                "comment": f"audio-studio profile: {profile}",
            }
        )
        if profile in {"default", "audio", "mastering"}:
            relationships.append(
                {
                    "spdxElementId": "SPDXRef-Package-audio-studio",
                    "relationshipType": "DEPENDS_ON",
                    "relatedSpdxElement": spdx_id,
                }
            )
    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"audio-studio-{app_version}-linux-build-environment",
        "documentNamespace": f"https://audio-studio.invalid/spdx/{uuid.uuid4()}",
        "creationInfo": {
            "created": utc_now(),
            "creators": [f"Tool: {TOOL_NAME}"],
            "licenseListVersion": "3.24",
        },
        "comment": (
            "Generated from the build virtualenv (audio-studio/.venv); written even "
            "when the desktop bundle itself failed to build. The bundle-scoped BOM "
            "is .agent_workspace/v1.1/linux-sbom.json."
        ),
        "packages": packages,
        "relationships": relationships,
    }


def build_report(
    bundle_info: dict[str, Any],
    components: list[dict[str, Any]],
    checks: dict[str, bool],
    outputs: dict[str, str],
    venv: dict[str, Any],
) -> dict[str, Any]:
    bundled = [
        {"name": c["name"], "version": c["version"], "profile": c["properties"][0]["value"]}
        for c in components
        if c["properties"][1]["value"] == "true"
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact": "linux-build-report",
        "generated_by": TOOL_NAME,
        "generated_at": utc_now(),
        "status": "pass" if all(checks.values()) else "fail",
        "build": {
            "script": "scripts/build-linux.sh",
            "spec": "packaging/pyinstaller.spec",
            "python_version": venv["python_version"],
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "bundle": bundle_info,
        "bundled_python_distributions": bundled,
        "checks": checks,
        "sbom_outputs": outputs,
    }


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--python",
        type=Path,
        default=REPOSITORY_ROOT / "audio-studio/.venv/bin/python",
        help="build interpreter to inventory (default: audio-studio/.venv)",
    )
    parser.add_argument(
        "--bundle",
        type=Path,
        default=REPOSITORY_ROOT / "dist/audio-studio",
        help="built one-dir bundle to scan (default: dist/audio-studio)",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=REPOSITORY_ROOT / "build/pyinstaller/pyinstaller",
        help="PyInstaller work dir holding PYZ-00.toc (default: build/pyinstaller/pyinstaller)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPOSITORY_ROOT / ".agent_workspace/v1.1",
        help="directory for linux-sbom.json and linux-build-report.json",
    )
    parser.add_argument(
        "--spdx-output",
        type=Path,
        default=REPOSITORY_ROOT / "packaging/SBOM.json",
        help="path for the venv-scoped SPDX-shaped document",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    python_bin = args.python if args.python.exists() else Path(sys.executable)

    venv = dump_venv(python_bin)
    freeze_lines = pip_freeze(python_bin)
    bundle_info = scan_bundle(args.bundle.resolve())
    pyz_roots = pyz_site_package_roots(args.work_dir)

    app_version = next(
        (
            d["version"]
            for d in venv["distributions"]
            if normalize(d["name"]) == "audio-studio"
        ),
        "0",
    )

    components = classify_components(venv, bundle_info, pyz_roots)

    forbidden_bundled = [
        c["name"]
        for c in components
        if normalize(c["name"]) in FORBIDDEN_IN_BUNDLE and c["properties"][1]["value"] == "true"
    ]
    checks = {
        "bundle_present": bool(bundle_info["present"]),
        "launcher_hashed": bool(bundle_info.get("launcher_sha256")),
        "qt_libraries_replaceable": bool(bundle_info.get("qt_shared_libraries")),
        "license_notices_shipped": bool(bundle_info.get("license_notices_present"))
        and all(bundle_info.get("license_notices_present", {}).values()),
        "no_pedalboard_artifacts": bundle_info.get("pedalboard_artifacts") == [],
        "no_forbidden_distributions_bundled": not forbidden_bundled,
        "no_gpl_in_default_profile": not any(
            c["properties"][0]["value"] == "default"
            and all(
                is_unexceptioned_gpl(alt)
                for alt in c["licenses"][0]["license"]["id"].split(" OR ")
            )
            for c in components
        ),
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.spdx_output.parent.mkdir(parents=True, exist_ok=True)

    sbom_path = args.output_dir / "linux-sbom.json"
    report_path = args.output_dir / "linux-build-report.json"
    outputs = {
        "cyclonedx": repo_relative(sbom_path),
        "spdx": repo_relative(args.spdx_output),
        "build_report": repo_relative(report_path),
    }

    cyclonedx = build_cyclonedx(app_version, components, bundle_info, venv, freeze_lines)
    spdx = build_spdx(app_version, components)
    report = build_report(bundle_info, components, checks, outputs, venv)

    for path, payload in ((sbom_path, cyclonedx), (args.spdx_output, spdx), (report_path, report)):
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path}")

    print(f"status: {report['status']}")
    for name, ok in checks.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
