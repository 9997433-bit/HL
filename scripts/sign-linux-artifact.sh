#!/usr/bin/env bash
# Checksum and, when a key is configured, GPG-sign Linux release artifacts.
#
# Scope: Linux only, and detached OpenPGP signatures only. This project has no
# Apple Developer ID and no Authenticode certificate, so nothing here performs
# macOS codesigning or notarization, or Windows signing, and the report it
# writes says so in as many words. A release note that claims otherwise would
# be claiming something no script in this repository does.
#
# Without SIGNING_KEY the run still succeeds and still produces the SHA-256
# manifest — an unsigned release with honest checksums is a normal state for
# this project, and the report records signed=false with the reason rather than
# leaving the question open.
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/linux-packaging.sh
source "${ROOT_DIR}/scripts/lib/linux-packaging.sh"

REPORT_PATH="${SIGNING_REPORT:-${ROOT_DIR}/.agent_workspace/v1.1/linux-signing-report.json}"
MANIFEST_NAME="${MANIFEST_NAME:-SHA256SUMS}"
MANIFEST_DIR=""
SIGNING_KEY="${SIGNING_KEY:-}"
GPG_BIN="${GPG_BIN:-}"
REQUIRE_SIGNATURE=0
ARTIFACTS=()

usage() {
  cat <<'EOF'
Usage: scripts/sign-linux-artifact.sh [options] ARTIFACT [ARTIFACT...]

Writes a SHA256SUMS manifest beside the artifacts and, when SIGNING_KEY is
set, a detached armoured GPG signature (.asc) for the manifest and for each
artifact. Always writes a JSON report describing exactly what was done.

Options:
  --key ID              GPG key to sign with (same as SIGNING_KEY).
  --manifest-dir PATH   Where SHA256SUMS goes (default: the first artifact's
                        directory).
  --manifest-name NAME  Manifest file name (default: SHA256SUMS).
  --report PATH         Report location
                        (default: .agent_workspace/v1.1/linux-signing-report.json).
  --require-signature   Exit non-zero when no key is configured.
  -h, --help            Show this help.

Environment:
  SIGNING_KEY       Key id, fingerprint or uid to sign with. Unset means
                    checksums only and signed=false in the report.
  GNUPGHOME         Honoured as usual by gpg; set it to use a scratch keyring.
  SIGNING_REPORT, MANIFEST_NAME, GPG_BIN are the same settings as above.

Not covered, deliberately: macOS codesign/notarization and Windows
Authenticode. This script signs Linux artifacts with GPG and nothing else.
EOF
}

while (($#)); do
  case "$1" in
    --key)
      SIGNING_KEY="$2"
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
      echo "unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      ARTIFACTS+=("$1")
      shift
      ;;
  esac
done

((${#ARTIFACTS[@]})) || {
  echo "no artifacts given" >&2
  usage >&2
  exit 2
}

require_command python3
require_command sha256sum

for artifact in "${ARTIFACTS[@]}"; do
  [[ -e "${artifact}" ]] || die "no such artifact: ${artifact}"
  [[ -f "${artifact}" ]] || die "not a regular file: ${artifact}
     Archive directories first; an AppDir signs as the AppImage or tarball
     built from it, not as a tree."
done

[[ -n "${MANIFEST_DIR}" ]] || MANIFEST_DIR="$(dirname -- "${ARTIFACTS[0]}")"
mkdir -p "${MANIFEST_DIR}"
MANIFEST_DIR="$(abspath "${MANIFEST_DIR}")"
MANIFEST_PATH="${MANIFEST_DIR}/${MANIFEST_NAME}"

[[ -n "${GPG_BIN}" ]] || GPG_BIN="$(command -v gpg || command -v gpg2 || true)"

log "artifacts: ${#ARTIFACTS[@]}"
log "manifest:  ${MANIFEST_PATH}"

# The manifest lists bare file names so that `sha256sum --check SHA256SUMS`
# works from the directory a user downloaded into.
: >"${MANIFEST_PATH}"
for artifact in "${ARTIFACTS[@]}"; do
  (
    cd -- "$(dirname -- "${artifact}")"
    sha256sum -- "$(basename -- "${artifact}")"
  ) >>"${MANIFEST_PATH}"
done

SIGNED=0
REASON=""
KEY_FINGERPRINT=""
GPG_VERSION=""

if [[ -n "${GPG_BIN}" ]]; then
  GPG_VERSION="$("${GPG_BIN}" --version 2>/dev/null | head -n 1 || true)"
fi

sign_file() {
  local target="$1"
  rm -f "${target}.asc"
  "${GPG_BIN}" --batch --yes --armor --detach-sign \
    --local-user "${SIGNING_KEY}" --output "${target}.asc" "${target}"
  "${GPG_BIN}" --batch --verify "${target}.asc" "${target}" 2>/dev/null
}

if [[ -z "${SIGNING_KEY}" ]]; then
  REASON="no SIGNING_KEY configured: artifacts are checksummed but unsigned"
  if ((REQUIRE_SIGNATURE)); then
    die "${REASON} (--require-signature was given)"
  fi
  warn "${REASON}"
elif [[ -z "${GPG_BIN}" ]]; then
  REASON="SIGNING_KEY is set but no gpg binary is available"
  die "${REASON}"
else
  # An unknown key id makes gpg exit non-zero, which is a reportable error
  # rather than a reason for the shell to die without saying anything.
  KEY_FINGERPRINT="$("${GPG_BIN}" --batch --with-colons --fingerprint \
    "${SIGNING_KEY}" 2>/dev/null | awk -F: '/^fpr:/ {print $10; exit}' || true)"
  [[ -n "${KEY_FINGERPRINT}" ]] \
    || die "gpg does not know the key ${SIGNING_KEY} in ${GNUPGHOME:-the default keyring}"
  log "signing with ${KEY_FINGERPRINT}"
  for artifact in "${ARTIFACTS[@]}"; do
    sign_file "${artifact}" || die "signing failed for ${artifact}"
  done
  sign_file "${MANIFEST_PATH}" || die "signing failed for ${MANIFEST_PATH}"
  SIGNED=1
  REASON="detached armoured signatures written and verified against ${KEY_FINGERPRINT}"
fi

# One record per line for the report writer: path, sha256, size, signature.
RECORDS="$(mktemp)"
trap 'rm -f "${RECORDS}"' EXIT

emit_record() {
  local path="$1" absolute digest size signature=""
  absolute="$(abspath "${path}")"
  digest="$(sha256sum -- "${path}" | awk '{print $1}')"
  size="$(wc -c <"${path}" | tr -d ' ')"
  if [[ -f "${path}.asc" ]]; then
    signature="$(abspath "${path}.asc")"
  fi
  printf '%s\t%s\t%s\t%s\n' "${absolute}" "${digest}" "${size}" "${signature}" \
    >>"${RECORDS}"
}

for artifact in "${ARTIFACTS[@]}"; do
  emit_record "${artifact}"
done

mkdir -p "$(dirname -- "${REPORT_PATH}")"

MANIFEST_PATH="${MANIFEST_PATH}" \
  REPORT_PATH="${REPORT_PATH}" \
  RECORDS="${RECORDS}" \
  ROOT_DIR="${ROOT_DIR}" \
  SIGNED="${SIGNED}" \
  REASON="${REASON}" \
  SIGNING_KEY="${SIGNING_KEY}" \
  KEY_FINGERPRINT="${KEY_FINGERPRINT}" \
  GPG_VERSION="${GPG_VERSION}" \
  python3 - <<'PY'
import hashlib
import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path

root = Path(os.environ["ROOT_DIR"])
manifest = Path(os.environ["MANIFEST_PATH"])
report_path = Path(os.environ["REPORT_PATH"])
signed = os.environ["SIGNED"] == "1"


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def described(path: Path) -> dict:
    signature = path.with_name(path.name + ".asc")
    return {
        "path": relative(path),
        "size_bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "signature": relative(signature) if signature.is_file() else None,
        "signature_verified": signature.is_file() and signed,
    }


artifacts = []
for line in Path(os.environ["RECORDS"]).read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    path_text, digest, size, signature = line.split("\t")
    path = Path(path_text)
    artifacts.append(
        {
            "path": relative(path),
            "size_bytes": int(size),
            "sha256": digest,
            "signature": relative(Path(signature)) if signature else None,
            "signature_verified": bool(signature) and signed,
        }
    )

report = {
    "schema_version": 1,
    "tool": "scripts/sign-linux-artifact.sh",
    "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "platform": {
        "system": platform.system(),
        "machine": platform.machine(),
        "release": platform.release(),
    },
    "signing": {
        "method": "gpg-detached-armored",
        "key_requested": bool(os.environ["SIGNING_KEY"]),
        "key_id": os.environ["SIGNING_KEY"] or None,
        "key_fingerprint": os.environ["KEY_FINGERPRINT"] or None,
        "gpg_version": os.environ["GPG_VERSION"] or None,
    },
    "signed": signed,
    "reason": os.environ["REASON"],
    "manifest": described(manifest),
    "artifacts": artifacts,
    "artifact_count": len(artifacts),
    # Stated explicitly so that no downstream summary can imply a platform
    # this project has never signed for.
    "scope": {
        "linux_gpg_detached_signature": signed,
        "macos_codesign": False,
        "macos_notarization": False,
        "windows_authenticode": False,
        "note": (
            "Linux GPG detached signing only. This project holds no Apple "
            "Developer ID and no Authenticode certificate, and no script here "
            "performs macOS codesigning or notarization or Windows signing."
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
