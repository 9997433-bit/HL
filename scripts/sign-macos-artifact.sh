#!/usr/bin/env bash
# Codesign macOS release artifacts when an Apple signing identity is available,
# and say plainly that nothing was signed when one is not.
#
# This project holds no Apple Developer ID. On a machine that does hold one — a
# real macOS host where `security find-identity -v -p codesigning` lists the
# identity — this script signs with the hardened runtime and a secure
# timestamp, verifies what it signed with codesign itself, and can hand the
# result to notarytool. Anywhere else it refuses to improvise: it will not run
# codesign off macOS, it will not call an artifact signed because a variable
# was set, and the JSON report it always writes records signed=false together
# with the reason.
#
# Nothing here fabricates a signature or a notarization ticket. An unsigned
# macOS build stays Gatekeeper-quarantined on a user's machine, and that is the
# honest state of this project's macOS artifacts today.
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/release-signing.sh
source "${ROOT_DIR}/scripts/lib/release-signing.sh"

REPORT_PATH="${MACOS_SIGNING_REPORT:-$(release_signing_default_report macos-signing-report.json)}"
MANIFEST_NAME="${MANIFEST_NAME:-SHA256SUMS}"
MANIFEST_DIR=""
# CODESIGN_IDENTITY is what scripts/build-macos.sh reads, and one machine with
# one Developer ID should not need the credential under two names.
IDENTITY="${MACOS_SIGNING_IDENTITY:-${CODESIGN_IDENTITY:-}}"
ENTITLEMENTS="${MACOS_SIGNING_ENTITLEMENTS:-}"
NOTARY_PROFILE="${MACOS_NOTARY_PROFILE:-}"
NOTARIZE=0
REQUIRE_SIGNATURE=0
REQUIRE_NOTARIZATION=0
ARTIFACTS=()

usage() {
  cat <<'EOF'
Usage: scripts/sign-macos-artifact.sh [options] ARTIFACT [ARTIFACT...]

Codesigns macOS artifacts (.app bundles, .dmg, .pkg, .zip) when
MACOS_SIGNING_IDENTITY names an identity in the login keychain, writes a
SHA256SUMS manifest for the regular files among them, and always writes a JSON
report describing exactly what was and was not done.

Options:
  --identity ID           Signing identity (same as MACOS_SIGNING_IDENTITY).
                          Common forms: "Developer ID Application: Name (TEAMID)"
                          or the certificate SHA-1 hash.
  --entitlements PATH     Entitlements plist passed to codesign.
  --notarize              Submit signed artifacts to notarytool and staple.
  --keychain-profile NAME Stored notarytool credentials (MACOS_NOTARY_PROFILE).
  --manifest-dir PATH     Where SHA256SUMS goes (default: the first artifact's
                          directory).
  --manifest-name NAME    Manifest file name (default: SHA256SUMS).
  --report PATH           Report location
                          (default: .agent_workspace/v1.2/macos-signing-report.json).
  --require-signature     Exit non-zero when no identity is configured.
  --require-notarization  Exit non-zero when notarization did not happen.
  -h, --help              Show this help.

Environment:
  MACOS_SIGNING_IDENTITY      Unset means checksums only and signed=false.
                              CODESIGN_IDENTITY, the variable
                              scripts/build-macos.sh reads, is accepted too.
  MACOS_SIGNING_ENTITLEMENTS  Entitlements plist, as --entitlements.
  MACOS_NOTARY_PROFILE        notarytool --keychain-profile name.
  MACOS_SIGNING_REPORT, MANIFEST_NAME are the same settings as above.

Notes:
  An identity can only be used on macOS: codesign, xcrun and the keychain do
  not exist elsewhere, so setting MACOS_SIGNING_IDENTITY on another host is an
  error here rather than a silently unsigned build.
  A directory artifact (an .app bundle) is described by the SHA-256 of its file
  tree — every relative path and file digest, in sorted order — because a
  directory has no single content hash. Ship a .dmg or .zip when a downloader
  needs a checksum they can verify with shasum.
EOF
}

while (($#)); do
  case "$1" in
    --identity)
      IDENTITY="$2"
      shift 2
      ;;
    --entitlements)
      ENTITLEMENTS="$2"
      shift 2
      ;;
    --notarize)
      NOTARIZE=1
      shift
      ;;
    --keychain-profile)
      NOTARY_PROFILE="$2"
      shift 2
      ;;
    --manifest-dir)
      MANIFEST_DIR="$2"
      shift 2
      ;;
    --manifest-name)
      MANIFEST_NAME="$2"
      shift 2
      ;;
    --report)
      REPORT_PATH="$2"
      shift 2
      ;;
    --require-signature)
      REQUIRE_SIGNATURE=1
      shift
      ;;
    --require-notarization)
      REQUIRE_NOTARIZATION=1
      NOTARIZE=1
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    --)
      shift
      ARTIFACTS+=("$@")
      break
      ;;
    -*)
      usage >&2
      usage_error "unknown option: $1"
      ;;
    *)
      ARTIFACTS+=("$1")
      shift
      ;;
  esac
done

((${#ARTIFACTS[@]})) || {
  usage >&2
  usage_error "no artifacts given"
}

PYTHON="$(python_bin)"

for artifact in "${ARTIFACTS[@]}"; do
  [[ -e "${artifact}" ]] || die "no such artifact: ${artifact}"
done

if [[ -n "${ENTITLEMENTS}" && ! -f "${ENTITLEMENTS}" ]]; then
  die "no entitlements plist at ${ENTITLEMENTS}"
fi

HOST_SYSTEM="$(uname -s)"
CODESIGN_BIN="$(command -v codesign || true)"
MACOS_VERSION=""
if [[ "${HOST_SYSTEM}" == "Darwin" ]] && command -v sw_vers >/dev/null 2>&1; then
  MACOS_VERSION="$(sw_vers -productVersion 2>/dev/null || true)"
fi

log "artifacts: ${#ARTIFACTS[@]}"

# The manifest covers the regular files only: `shasum --check` cannot verify a
# directory, and a line it would refuse is worse than an absent one.
MANIFEST_FILES=()
for artifact in "${ARTIFACTS[@]}"; do
  if [[ -f "${artifact}" ]]; then
    MANIFEST_FILES+=("${artifact}")
  fi
done

MANIFEST_PATH=""
if ((${#MANIFEST_FILES[@]})); then
  [[ -n "${MANIFEST_DIR}" ]] || MANIFEST_DIR="$(dirname -- "${MANIFEST_FILES[0]}")"
  mkdir -p "${MANIFEST_DIR}"
  MANIFEST_DIR="$(abspath "${MANIFEST_DIR}")"
  MANIFEST_PATH="${MANIFEST_DIR}/${MANIFEST_NAME}"
  : >"${MANIFEST_PATH}"
  for artifact in "${MANIFEST_FILES[@]}"; do
    printf '%s  %s\n' \
      "$(sha256_of "${artifact}")" "$(basename -- "${artifact}")" >>"${MANIFEST_PATH}"
  done
  log "manifest:  ${MANIFEST_PATH}"
else
  warn "every artifact is a directory; no SHA256SUMS manifest was written"
fi

SIGNED=0
REASON=""
AUTHORITY=""
NOTARIZED=0
NOTARY_REASON="not requested"
NOTARY_SUBMISSIONS=""

verify_signature() {
  local target="$1"
  "${CODESIGN_BIN}" --verify --strict --deep --verbose=2 -- "${target}"
}

sign_artifact() {
  local target="$1"
  local -a command=(
    "${CODESIGN_BIN}" --force --timestamp --options runtime
    --sign "${IDENTITY}"
  )
  if [[ -n "${ENTITLEMENTS}" ]]; then
    command+=(--entitlements "${ENTITLEMENTS}")
  fi
  "${command[@]}" -- "${target}"
}

if [[ -z "${IDENTITY}" ]]; then
  REASON="no MACOS_SIGNING_IDENTITY configured: artifacts are checksummed but"
  REASON+=" unsigned, and macOS will quarantine them for a downloader"
  if ((REQUIRE_SIGNATURE)); then
    die "${REASON} (--require-signature was given)"
  fi
  warn "${REASON}"
elif [[ "${HOST_SYSTEM}" != "Darwin" ]]; then
  die "MACOS_SIGNING_IDENTITY is set but this host is ${HOST_SYSTEM}, not Darwin.
     codesign, xcrun and the keychain exist only on macOS; run this on the Mac
     that holds the Developer ID. Refusing to report a signature that was never
     made."
elif [[ -z "${CODESIGN_BIN}" ]]; then
  die "MACOS_SIGNING_IDENTITY is set but codesign is not on PATH; install the
     Xcode command line tools."
else
  log "signing with identity: ${IDENTITY}"
  for artifact in "${ARTIFACTS[@]}"; do
    sign_artifact "${artifact}" || die "codesign failed for ${artifact}"
    # A signature this script cannot verify is not one it will report.
    verify_signature "${artifact}" || die "codesign --verify failed for ${artifact}"
  done
  AUTHORITY="$("${CODESIGN_BIN}" --display --verbose=2 -- "${ARTIFACTS[0]}" 2>&1 \
    | sed -n 's/^Authority=//p' | head -n 1 || true)"
  SIGNED=1
  REASON="codesign --options runtime --timestamp applied and verified with"
  REASON+=" codesign --verify --strict for every artifact"
fi

if ((NOTARIZE)); then
  if ((!SIGNED)); then
    NOTARY_REASON="not attempted: nothing was signed, and notarytool rejects an unsigned upload"
  elif [[ -z "${NOTARY_PROFILE}" ]]; then
    NOTARY_REASON="not attempted: no MACOS_NOTARY_PROFILE; store credentials with"
    NOTARY_REASON+=" xcrun notarytool store-credentials"
  elif ! command -v xcrun >/dev/null 2>&1; then
    NOTARY_REASON="not attempted: xcrun is not available on this host"
  elif ((${#MANIFEST_FILES[@]} == 0)); then
    NOTARY_REASON="not attempted: notarytool takes a .zip, .dmg or .pkg, not a bare"
    NOTARY_REASON+=" .app directory"
  else
    for artifact in "${MANIFEST_FILES[@]}"; do
      submission="$(xcrun notarytool submit "${artifact}" \
        --keychain-profile "${NOTARY_PROFILE}" --wait --no-progress 2>&1 \
        | sed -n 's/^ *id: *//p' | head -n 1)" \
        || die "notarytool submit failed for ${artifact}"
      xcrun stapler staple -- "${artifact}" \
        || die "stapler failed for ${artifact}; the ticket was not attached"
      xcrun stapler validate -- "${artifact}" \
        || die "stapler validate failed for ${artifact}"
      NOTARY_SUBMISSIONS+="${submission}"$'\n'
    done
    NOTARIZED=1
    NOTARY_REASON="submitted with notarytool --wait, stapled and validated"
  fi
  ((NOTARIZED)) || warn "${NOTARY_REASON}"
  if ((REQUIRE_NOTARIZATION && !NOTARIZED)); then
    die "${NOTARY_REASON} (--require-notarization was given)"
  fi
fi

# One record per line for the report writer: path, kind, signature, verified.
RECORDS="$(mktemp)"
trap 'rm -f "${RECORDS}"' EXIT

for artifact in "${ARTIFACTS[@]}"; do
  kind="file"
  if [[ -d "${artifact}" ]]; then
    kind="bundle"
  fi
  signature=""
  if ((SIGNED)); then
    signature="embedded-codesign"
  fi
  printf '%s\t%s\t%s\t%s\n' \
    "$(abspath "${artifact}")" "${kind}" "${signature}" "${SIGNED}" >>"${RECORDS}"
done

mkdir -p "$(dirname -- "${REPORT_PATH}")"

AUTHORITY="${AUTHORITY}" \
  CODESIGN_BIN="${CODESIGN_BIN}" \
  ENTITLEMENTS="${ENTITLEMENTS}" \
  HOST_SYSTEM="${HOST_SYSTEM}" \
  IDENTITY="${IDENTITY}" \
  MACOS_VERSION="${MACOS_VERSION}" \
  MANIFEST_PATH="${MANIFEST_PATH}" \
  NOTARIZE="${NOTARIZE}" \
  NOTARIZED="${NOTARIZED}" \
  NOTARY_PROFILE="${NOTARY_PROFILE}" \
  NOTARY_REASON="${NOTARY_REASON}" \
  NOTARY_SUBMISSIONS="${NOTARY_SUBMISSIONS}" \
  REASON="${REASON}" \
  RECORDS="${RECORDS}" \
  REPORT_PATH="${REPORT_PATH}" \
  ROOT_DIR="${ROOT_DIR}" \
  SIGNED="${SIGNED}" \
  "${PYTHON}" - <<'PY'
import hashlib
import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path

root = Path(os.environ["ROOT_DIR"])
report_path = Path(os.environ["REPORT_PATH"])
signed = os.environ["SIGNED"] == "1"
notarized = os.environ["NOTARIZED"] == "1"


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def tree_digest(directory: Path) -> tuple[str, int]:
    """SHA-256 over every relative path and file digest, in sorted order.

    A directory has no content hash of its own, and an .app bundle is a
    directory. Hashing the sorted (path, digest) pairs gives a value two
    machines can compare, which is all this report claims for it.
    """
    digest = hashlib.sha256()
    total = 0
    for entry in sorted(p for p in directory.rglob("*") if p.is_file()):
        payload = entry.read_bytes()
        total += len(payload)
        digest.update(str(entry.relative_to(directory)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(payload).hexdigest().encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest(), total


def described(path: Path, kind: str, signature: str, verified: bool) -> dict:
    if kind == "bundle":
        checksum, size = tree_digest(path)
        scope = "bundle-tree"
    else:
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        size = path.stat().st_size
        scope = "file"
    return {
        "path": relative(path),
        "kind": kind,
        "size_bytes": size,
        "sha256": checksum,
        "digest_scope": scope,
        "signature": signature or None,
        "signature_verified": bool(signature) and verified,
    }


artifacts = []
for line in Path(os.environ["RECORDS"]).read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    path_text, kind, signature, verified = line.split("\t")
    artifacts.append(described(Path(path_text), kind, signature, verified == "1"))

manifest = None
if os.environ["MANIFEST_PATH"]:
    manifest_path = Path(os.environ["MANIFEST_PATH"])
    manifest = {
        "path": relative(manifest_path),
        "kind": "file",
        "size_bytes": manifest_path.stat().st_size,
        "sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "digest_scope": "file",
        # The manifest itself is never codesigned: it is a text file beside the
        # artifacts, not a Mach-O object.
        "signature": None,
        "signature_verified": False,
    }

submissions = [
    line.strip()
    for line in os.environ["NOTARY_SUBMISSIONS"].splitlines()
    if line.strip()
]

report = {
    "schema_version": int(os.environ.get("RELEASE_SIGNING_SCHEMA_VERSION", "1")),
    "tool": "scripts/sign-macos-artifact.sh",
    "target_platform": "macos",
    "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "platform": {
        "system": platform.system(),
        "machine": platform.machine(),
        "release": platform.release(),
    },
    "signing": {
        "method": "apple-codesign-hardened-runtime",
        "identity_requested": bool(os.environ["IDENTITY"]),
        "identity": os.environ["IDENTITY"] or None,
        "authority": os.environ["AUTHORITY"] or None,
        "entitlements": os.environ["ENTITLEMENTS"] or None,
        "codesign_path": os.environ["CODESIGN_BIN"] or None,
        "host_system": os.environ["HOST_SYSTEM"],
        "macos_version": os.environ["MACOS_VERSION"] or None,
        "secure_timestamp": signed,
    },
    "notarization": {
        "requested": os.environ["NOTARIZE"] == "1",
        "performed": notarized,
        "keychain_profile": os.environ["NOTARY_PROFILE"] or None,
        "submission_ids": submissions,
        "stapled": notarized,
        "reason": os.environ["NOTARY_REASON"],
    },
    "signed": signed,
    "reason": os.environ["REASON"],
    "manifest": manifest,
    "artifacts": artifacts,
    "artifact_count": len(artifacts),
    # Spelled out so no downstream summary can widen this into a platform
    # nobody signed for.
    "scope": {
        "linux_gpg_detached_signature": False,
        "macos_codesign": signed,
        "macos_notarization": notarized,
        "windows_authenticode": False,
        "note": (
            "macOS codesigning only. This project holds no Apple Developer ID, "
            "so a run without MACOS_SIGNING_IDENTITY checksums the artifacts "
            "and signs nothing; Linux GPG signing is "
            "scripts/sign-linux-artifact.sh and Windows Authenticode is "
            "scripts/sign-windows-artifact.ps1."
        ),
    },
}

report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(f"report: {report_path}")
PY

if ((SIGNED)); then
  log "signed: ${REASON}"
else
  log "not signed: ${REASON}"
fi
if ((NOTARIZE)); then
  log "notarization: ${NOTARY_REASON}"
fi
