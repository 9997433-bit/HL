#!/usr/bin/env bash
# Shared helpers for the cross-platform release-signing scaffolds.
#
# Source this from scripts/sign-macos-artifact.sh and
# scripts/release-signing-manifest.sh; it is not executable on its own.
#
# It deliberately does not reuse scripts/lib/linux-packaging.sh. That library is
# the Linux packaging licence gate — AppDir layouts, .deb trees, replaceable
# shared objects — and a macOS signer that died on a Debian rule would be worse
# than the handful of shell utilities repeated here. What does belong in one
# place is the report vocabulary: three platforms writing three differently
# shaped JSON documents is how a release ends up claiming a signature that
# nobody produced.

if [[ -n "${_RELEASE_SIGNING_SH_SOURCED:-}" ]]; then
  return 0
fi
_RELEASE_SIGNING_SH_SOURCED=1

RELEASE_SIGNING_LIB_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_SIGNING_ROOT_DIR="$(cd -- "${RELEASE_SIGNING_LIB_DIR}/../.." && pwd)"

#: Bumped whenever the report layout shared by the three signing scripts and
#: the release manifest changes. scripts/sign-windows-artifact.ps1 carries the
#: same number; tests/test_release_signing.py checks that they agree.
export RELEASE_SIGNING_SCHEMA_VERSION=1
#: Where the cross-platform signing evidence is published.
export RELEASE_SIGNING_WORKSPACE="${RELEASE_SIGNING_ROOT_DIR}/.agent_workspace/v1.2"

log() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mwarning:\033[0m %s\n' "$*" >&2; }
die() {
  printf '\033[1;31merror:\033[0m %s\n' "$*" >&2
  exit 1
}

usage_error() {
  printf '\033[1;31merror:\033[0m %s\n' "$*" >&2
  exit 2
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

# Absolute path for a location that may not exist yet.
abspath() {
  local path="$1"
  if [[ -d "${path}" ]]; then
    (cd -- "${path}" && pwd)
  else
    local parent
    parent="$(cd -- "$(dirname -- "${path}")" && pwd)" || return 1
    printf '%s/%s\n' "${parent%/}" "$(basename -- "${path}")"
  fi
}

# macOS ships shasum, not the coreutils sha256sum, and these scripts have to run
# on the machine that holds the certificate rather than on a convenient one.
sha256_of() {
  local path="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum -- "${path}" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 -- "${path}" | awk '{print $1}'
  else
    die "no sha256sum and no shasum on this host; cannot checksum ${path}"
  fi
}

# The report writers are Python heredocs, so a missing interpreter is a hard
# stop rather than a report that silently never appears.
python_bin() {
  local candidate
  for candidate in "${PYTHON_BIN:-}" python3 python; do
    [[ -n "${candidate}" ]] || continue
    if command -v "${candidate}" >/dev/null 2>&1; then
      command -v "${candidate}"
      return 0
    fi
  done
  die "no Python interpreter found; set PYTHON_BIN"
}

release_signing_default_report() {
  printf '%s/%s\n' "${RELEASE_SIGNING_WORKSPACE}" "$1"
}
