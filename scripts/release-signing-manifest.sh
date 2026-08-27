#!/usr/bin/env bash
# Collect the per-platform signing reports into one release-level manifest.
#
# Three scripts sign three platforms — scripts/sign-linux-artifact.sh,
# scripts/sign-macos-artifact.sh, scripts/sign-windows-artifact.ps1 — and each
# writes a report about its own run. A release is the union of those runs, and
# the union is where an unsigned platform quietly disappears from a summary
# that says "signed release". This script writes that union down:
# .agent_workspace/v1.2/release-signing-manifest.json names every platform,
# whether its report exists at all, whether it claims a signature, and which
# platforms are unsigned.
#
# It signs nothing itself. It reads reports, and it refuses two kinds of
# nonsense rather than passing them on: a report filed under the wrong
# platform, and a report that says signed=true while not one of its artifacts
# carries a verified signature.
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/release-signing.sh
source "${ROOT_DIR}/scripts/lib/release-signing.sh"

# The Linux report predates the v1.2 workspace and stayed where it was written.
LINUX_REPORT="${LINUX_SIGNING_REPORT:-${ROOT_DIR}/.agent_workspace/v1.1/linux-signing-report.json}"
MACOS_REPORT="${MACOS_SIGNING_REPORT:-}"
[[ -n "${MACOS_REPORT}" ]] \
  || MACOS_REPORT="$(release_signing_default_report macos-signing-report.json)"
WINDOWS_REPORT="${WINDOWS_SIGNING_REPORT:-}"
[[ -n "${WINDOWS_REPORT}" ]] \
  || WINDOWS_REPORT="$(release_signing_default_report windows-signing-report.json)"
OUTPUT_PATH="${RELEASE_SIGNING_MANIFEST:-}"
[[ -n "${OUTPUT_PATH}" ]] \
  || OUTPUT_PATH="$(release_signing_default_report release-signing-manifest.json)"
RELEASE_VERSION="${RELEASE_VERSION:-}"
REQUIRE_SIGNED=()

usage() {
  cat <<'EOF'
Usage: scripts/release-signing-manifest.sh [options]

Reads the Linux, macOS and Windows signing reports and writes a combined
release manifest to .agent_workspace/v1.2/release-signing-manifest.json.

A missing report is recorded as a platform that was not signed here, not as an
error: on most machines two of the three cannot run at all.

Options:
  --linux-report PATH    Default .agent_workspace/v1.1/linux-signing-report.json
  --macos-report PATH    Default .agent_workspace/v1.2/macos-signing-report.json
  --windows-report PATH  Default .agent_workspace/v1.2/windows-signing-report.json
  --output PATH          Manifest location (default as above).
  --version STRING       Release version to record (default: read from
                         audio-studio/pyproject.toml).
  --require-signed NAME  Exit non-zero unless NAME (linux, macos, windows)
                         reports a verified signature. Repeatable.
  --require-all-signed   Shorthand for all three platforms.
  -h, --help             Show this help.

Environment:
  LINUX_SIGNING_REPORT, MACOS_SIGNING_REPORT, WINDOWS_SIGNING_REPORT,
  RELEASE_SIGNING_MANIFEST, RELEASE_VERSION are the same settings as above.

Refusals (exit 1):
  a report whose target_platform or tool belongs to a different platform than
  the option it was passed under; a report that claims signed=true while none
  of its artifacts has signature_verified=true.
EOF
}

while (($#)); do
  case "$1" in
    --linux-report)
      LINUX_REPORT="$2"
      shift 2
      ;;
    --macos-report)
      MACOS_REPORT="$2"
      shift 2
      ;;
    --windows-report)
      WINDOWS_REPORT="$2"
      shift 2
      ;;
    --output)
      OUTPUT_PATH="$2"
      shift 2
      ;;
    --version)
      RELEASE_VERSION="$2"
      shift 2
      ;;
    --require-signed)
      REQUIRE_SIGNED+=("$2")
      shift 2
      ;;
    --require-all-signed)
      REQUIRE_SIGNED+=(linux macos windows)
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    -*)
      usage >&2
      usage_error "unknown option: $1"
      ;;
    *)
      usage >&2
      usage_error "unexpected argument: $1"
      ;;
  esac
done

for platform in "${REQUIRE_SIGNED[@]-}"; do
  case "${platform}" in
    "" | linux | macos | windows) ;;
    *) usage_error "unknown platform: ${platform} (expected linux, macos or windows)" ;;
  esac
done

if [[ -z "${RELEASE_VERSION}" ]]; then
  PYPROJECT="${ROOT_DIR}/audio-studio/pyproject.toml"
  if [[ -f "${PYPROJECT}" ]]; then
    RELEASE_VERSION="$(sed -n 's/^version[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' \
      "${PYPROJECT}" | head -n 1)"
  fi
fi

PYTHON="$(python_bin)"
mkdir -p "$(dirname -- "${OUTPUT_PATH}")"

log "linux report:   ${LINUX_REPORT}"
log "macos report:   ${MACOS_REPORT}"
log "windows report: ${WINDOWS_REPORT}"

set +e
LINUX_REPORT="${LINUX_REPORT}" \
  MACOS_REPORT="${MACOS_REPORT}" \
  WINDOWS_REPORT="${WINDOWS_REPORT}" \
  OUTPUT_PATH="${OUTPUT_PATH}" \
  RELEASE_VERSION="${RELEASE_VERSION}" \
  REQUIRE_SIGNED="${REQUIRE_SIGNED[*]-}" \
  ROOT_DIR="${ROOT_DIR}" \
  "${PYTHON}" - <<'PY'
import json
import os
import platform as platform_module
import sys
from datetime import datetime, timezone
from pathlib import Path

root = Path(os.environ["ROOT_DIR"])
output_path = Path(os.environ["OUTPUT_PATH"])

SOURCES = {
    "linux": (Path(os.environ["LINUX_REPORT"]), "scripts/sign-linux-artifact.sh"),
    "macos": (Path(os.environ["MACOS_REPORT"]), "scripts/sign-macos-artifact.sh"),
    "windows": (Path(os.environ["WINDOWS_REPORT"]), "scripts/sign-windows-artifact.ps1"),
}

#: Every per-platform report has to carry these before it can be aggregated.
REQUIRED_KEYS = (
    "schema_version",
    "tool",
    "generated_at",
    "platform",
    "signing",
    "signed",
    "reason",
    "artifacts",
    "artifact_count",
    "scope",
)


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def load(name: str, path: Path, expected_tool: str) -> dict:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        fail(f"{path} is not valid JSON: {error}")
    if not isinstance(document, dict):
        fail(f"{path} is not a signing report object")

    missing = [key for key in REQUIRED_KEYS if key not in document]
    if missing:
        fail(f"{path} is missing report fields: {', '.join(missing)}")

    # An older report predates target_platform; the tool name still pins it.
    declared = document.get("target_platform")
    if declared is not None and declared != name:
        fail(f"{path} is a {declared} report but was passed as the {name} report")
    if document["tool"] != expected_tool:
        fail(
            f"{path} was written by {document['tool']}, not {expected_tool}; "
            f"it is not the {name} report"
        )

    artifacts = document["artifacts"]
    if not isinstance(artifacts, list):
        fail(f"{path} has a non-list artifacts field")

    verified = [
        artifact
        for artifact in artifacts
        if isinstance(artifact, dict) and artifact.get("signature_verified") is True
    ]
    if document["signed"] is True and not verified:
        fail(
            f"{path} claims signed=true while no artifact has "
            f"signature_verified=true; refusing to carry that claim into the "
            f"release manifest"
        )
    return document


platforms: dict[str, dict] = {}
for name, (path, expected_tool) in SOURCES.items():
    if not path.is_file():
        platforms[name] = {
            "report": relative(path),
            "present": False,
            "signed": False,
            "reason": (
                f"no report at {relative(path)}: nothing signed {name} artifacts "
                f"for this release"
            ),
            "artifact_count": 0,
            "artifacts": [],
        }
        continue

    document = load(name, path, expected_tool)
    platforms[name] = {
        "report": relative(path),
        "present": True,
        "signed": bool(document["signed"]),
        "reason": document["reason"],
        "tool": document["tool"],
        "generated_at": document["generated_at"],
        "signing_method": (document.get("signing") or {}).get("method"),
        "host_system": (document.get("platform") or {}).get("system"),
        "notarized": bool((document.get("notarization") or {}).get("performed", False)),
        "artifact_count": document["artifact_count"],
        "artifacts": [
            {
                "path": artifact.get("path"),
                "size_bytes": artifact.get("size_bytes"),
                "sha256": artifact.get("sha256"),
                "signature": artifact.get("signature"),
                "signature_verified": bool(artifact.get("signature_verified")),
            }
            for artifact in document["artifacts"]
        ],
    }

signed_platforms = sorted(name for name, entry in platforms.items() if entry["signed"])
unsigned_platforms = sorted(
    name for name, entry in platforms.items() if entry["present"] and not entry["signed"]
)
missing_reports = sorted(name for name, entry in platforms.items() if not entry["present"])
artifact_count = sum(entry["artifact_count"] for entry in platforms.values())

manifest = {
    "schema_version": int(os.environ.get("RELEASE_SIGNING_SCHEMA_VERSION", "1")),
    "tool": "scripts/release-signing-manifest.sh",
    "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "release_version": os.environ["RELEASE_VERSION"] or None,
    "platform": {
        "system": platform_module.system(),
        "machine": platform_module.machine(),
        "release": platform_module.release(),
    },
    "platforms": platforms,
    "signed_platforms": signed_platforms,
    "unsigned_platforms": unsigned_platforms,
    "missing_reports": missing_reports,
    "fully_signed": len(signed_platforms) == len(SOURCES),
    "artifact_count": artifact_count,
    "note": (
        "Aggregated from the per-platform signing reports; this script signs "
        "nothing. A platform listed in unsigned_platforms was checksummed but "
        "not signed, and one in missing_reports was not signed here at all. "
        "This project holds no Apple Developer ID and no Authenticode "
        "certificate, so macOS and Windows artifacts are unsigned unless a "
        "release operator supplies those credentials."
    ),
}

output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(f"manifest: {output_path}")

required = [name for name in os.environ["REQUIRE_SIGNED"].split() if name]
unmet = sorted({name for name in required if not platforms[name]["signed"]})
if unmet:
    print(
        "error: no verified signature for: " + ", ".join(unmet),
        file=sys.stderr,
    )
    raise SystemExit(3)
PY
STATUS=$?
set -e

case "${STATUS}" in
  0) ;;
  3) die "the manifest was written, but a --require-signed platform is unsigned" ;;
  *) exit "${STATUS}" ;;
esac

log "manifest written: ${OUTPUT_PATH}"
