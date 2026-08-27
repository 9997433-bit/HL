#!/usr/bin/env bash
# Shared helpers for the Linux packaging wrappers.
#
# Source this from scripts/package-*.sh; it is not executable on its own.
#
# Everything here exists because a package is a distribution. The one-dir
# PyInstaller bundle produced by scripts/build-linux.sh satisfies the LGPL by
# keeping Qt, libsndfile and friends replaceable and by carrying the notices
# beside the launcher. A packaging step that flattens, compresses or strips
# those files, or that drops the licence documents on the way into an AppDir or
# a .deb, undoes that quietly. So each wrapper re-runs the same gate on the
# bundle it is handed and again on the tree it produces.

if [[ -n "${_LINUX_PACKAGING_SH_SOURCED:-}" ]]; then
  return 0
fi
_LINUX_PACKAGING_SH_SOURCED=1

PACKAGING_LIB_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PACKAGING_ROOT_DIR="$(cd -- "${PACKAGING_LIB_DIR}/../.." && pwd)"

#: The bundle directory and the launcher inside it, both named for the project.
PACKAGE_NAME="audio-studio"
#: Notices that must travel with any redistributed binary.
LICENSE_NOTICES=(THIRD_PARTY_LICENSES.md LGPL-RELINKING.txt)
#: Bundling this would relicense the artifact; see THIRD_PARTY_LICENSES.md.
GPL_PAYLOAD="pedalboard"

log() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mwarning:\033[0m %s\n' "$*" >&2; }
die() {
  printf '\033[1;31merror:\033[0m %s\n' "$*" >&2
  exit 1
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

# Locate the directory inside the bundle that holds the licence notices.
# scripts/build-linux.sh accepts either layout, so both are searched here too.
bundle_license_dir() {
  local bundle="$1"
  local candidate
  for candidate in "${bundle}/_internal/licenses" "${bundle}/licenses"; do
    if [[ -d "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  return 1
}

resolve_bundle() {
  local bundle="$1"
  [[ -d "${bundle}" ]] || die "no bundle directory at ${bundle}
     Build one first: scripts/build-linux.sh"
  [[ -x "${bundle}/${PACKAGE_NAME}" ]] \
    || die "no ${PACKAGE_NAME} launcher in ${bundle}; that is not a one-dir bundle"
  abspath "${bundle}"
}

# The LGPL components reach the application on the condition that a recipient
# can swap them for their own build, so a bundle with no separate shared
# objects in it is a licence failure and not merely an odd build.
require_replaceable_lgpl_libraries() {
  local tree="$1"
  local -a libs
  mapfile -t libs < <(find "${tree}" \
    \( -name 'libQt6Core.so*' -o -name 'libsndfile.so*' -o -name 'libpyside6*' \) \
    -print | sort)
  ((${#libs[@]})) || die "no replaceable LGPL shared libraries under ${tree}
     Package the one-dir bundle from scripts/build-linux.sh, never a --onefile
     build: relinking is how this project satisfies the LGPL."
  printf '    %s\n' "${libs[@]#"${tree}/"}"
}

require_license_notices() {
  local tree="$1"
  local notice found
  for notice in "${LICENSE_NOTICES[@]}"; do
    found="$(find "${tree}" -name "${notice}" -print -quit)"
    [[ -n "${found}" ]] || die "the tree at ${tree} is missing ${notice}
     Every redistributed copy has to carry the third-party notices and the
     LGPL relinking instructions; see packaging/LGPL-RELINKING.txt."
  done
}

reject_gpl_payload() {
  local tree="$1"
  if grep -rqi "${GPL_PAYLOAD}" "${tree}" \
    --include='*.pyc' --include='*.so' --include='*.so.*' 2>/dev/null; then
    die "${GPL_PAYLOAD} (GPL-3.0) artifacts found under ${tree}; refusing to
     package this as an MIT distribution."
  fi
}

# The single gate every wrapper runs, on its input bundle and on its output.
bundle_license_gate() {
  local tree="$1"
  require_license_notices "${tree}"
  require_replaceable_lgpl_libraries "${tree}"
  reject_gpl_payload "${tree}"
}

detect_version() {
  local pyproject="${PACKAGING_ROOT_DIR}/audio-studio/pyproject.toml"
  local version=""
  if [[ -f "${pyproject}" ]]; then
    version="$(sed -n 's/^version[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' \
      "${pyproject}" | head -n 1)"
  fi
  [[ -n "${version}" ]] || die "cannot read the project version from ${pyproject};
     pass --version explicitly"
  printf '%s\n' "${version}"
}

detect_deb_architecture() {
  if command -v dpkg >/dev/null 2>&1; then
    dpkg --print-architecture
    return 0
  fi
  case "$(uname -m)" in
    x86_64) printf 'amd64\n' ;;
    aarch64) printf 'arm64\n' ;;
    armv7l) printf 'armhf\n' ;;
    i686 | i386) printf 'i386\n' ;;
    *) die "unknown machine $(uname -m); pass --arch explicitly" ;;
  esac
}

appimage_architecture() {
  case "$(uname -m)" in
    x86_64) printf 'x86_64\n' ;;
    aarch64) printf 'aarch64\n' ;;
    armv7l) printf 'armhf\n' ;;
    i686 | i386) printf 'i686\n' ;;
    *) die "unknown machine $(uname -m); pass --arch explicitly" ;;
  esac
}

write_desktop_entry() {
  local path="$1"
  mkdir -p "$(dirname -- "${path}")"
  cat >"${path}" <<EOF
[Desktop Entry]
Type=Application
Name=Audio Studio
GenericName=Audio Editor
Comment=Professional audio editing and analysis workstation
Exec=${PACKAGE_NAME} %F
Icon=${PACKAGE_NAME}
Terminal=false
Categories=AudioVideo;Audio;AudioVideoEditing;
MimeType=audio/wav;audio/x-wav;audio/flac;audio/ogg;audio/mpeg;
StartupWMClass=audio-studio
EOF
}

install_license_documents() {
  local bundle="$1" dest="$2"
  local license_dir notice
  license_dir="$(bundle_license_dir "${bundle}")" \
    || die "no licenses/ directory inside ${bundle}"
  mkdir -p "${dest}"
  for notice in "${LICENSE_NOTICES[@]}"; do
    [[ -f "${license_dir}/${notice}" ]] || die "missing ${license_dir}/${notice}"
    cp -f "${license_dir}/${notice}" "${dest}/${notice}"
  done
}

install_icon() {
  local dest="$1"
  local source="${PACKAGING_ROOT_DIR}/packaging/${PACKAGE_NAME}.svg"
  [[ -f "${source}" ]] || die "missing icon: ${source}"
  mkdir -p "$(dirname -- "${dest}")"
  cp -f "${source}" "${dest}"
}
