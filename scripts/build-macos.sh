#!/usr/bin/env bash
# Build the Audio Studio desktop bundle for macOS and check what it contains.
#
# The counterpart of scripts/build-linux.sh, running the same licence gates
# against the same packaging/pyinstaller.spec. Three things are macOS-specific:
#
# * The LGPL objects are .dylib files and Qt .framework directories rather than
#   .so files, so the replaceability check looks for those names instead.
# * The architecture the bundle can actually run on is computed from every
#   Mach-O object in it, not from the launcher alone. PySide6 ships universal2
#   wheels while numpy, scipy and soundfile do not, so a bundle full of fat Qt
#   libraries is still a single-architecture product. Publishing it as
#   "universal" would be a false claim; --expect-arch makes the build fail
#   rather than let a release name drift away from what was built.
# * Code signing is opt-in through CODESIGN_IDENTITY and stops at signing.
#   Notarisation needs an Apple ID and a Developer ID certificate that this
#   project does not have, so no notarisation tool is invoked here and the
#   output says so. See packaging/MACOS.md.
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="${ROOT_DIR}/audio-studio"
SPEC_FILE="${ROOT_DIR}/packaging/pyinstaller.spec"
NAME="audio-studio"

DIST_DIR="${DIST_DIR:-${ROOT_DIR}/dist}"
WORK_DIR="${WORK_DIR:-${ROOT_DIR}/build/pyinstaller}"
PYTHON_BIN="${PYTHON_BIN:-}"
CLEAN=0
INSTALL_DEPS=0
RUN_SMOKE=1
EXPECT_ARCH=""
ALLOW_GPL="${ALLOW_GPL:-0}"
#: Empty means "do not sign". "-" is an ad-hoc signature: it satisfies the
#: arm64 loader but tells Gatekeeper nothing about who produced the binary.
CODESIGN_IDENTITY="${CODESIGN_IDENTITY:-}"

usage() {
  cat <<'EOF'
Usage: scripts/build-macos.sh [options]

Options:
  --clean             Remove previous dist/ and build/ output first.
  --install-deps      Install PyInstaller into the selected interpreter.
  --no-smoke          Skip launching the built bundle offscreen.
  --dist-dir PATH     Output directory (default: dist/).
  --expect-arch ARCH  Fail unless the bundle runs on exactly ARCH, one of
                      arm64, x86_64 or universal2. Use this whenever the
                      artifact name states an architecture.
  -h, --help          Show this help.

Environment:
  PYTHON_BIN          Interpreter to build with (default: audio-studio/.venv,
                      then the active python3).
  ALLOW_GPL=1         Permit building while pedalboard is installed. The result
                      is a GPL-3.0 distribution and must not be published as an
                      MIT binary; see THIRD_PARTY_LICENSES.md.
  CODESIGN_IDENTITY   Sign the bundle with this identity. "-" is an ad-hoc
                      signature; a Developer ID name signs for real. Unset
                      means the bundle is left as PyInstaller produced it.
                      Notarisation is never performed; see packaging/MACOS.md.
EOF
}

while (($#)); do
  case "$1" in
    --clean)
      CLEAN=1
      shift
      ;;
    --install-deps)
      INSTALL_DEPS=1
      shift
      ;;
    --no-smoke)
      RUN_SMOKE=0
      shift
      ;;
    --dist-dir)
      DIST_DIR="$2"
      shift 2
      ;;
    --expect-arch)
      EXPECT_ARCH="$2"
      shift 2
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

log() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mwarning:\033[0m %s\n' "$*" >&2; }
die() {
  printf '\033[1;31merror:\033[0m %s\n' "$*" >&2
  exit 1
}

case "${EXPECT_ARCH}" in
  "" | arm64 | x86_64 | universal2) ;;
  *) die "unsupported --expect-arch: ${EXPECT_ARCH} (arm64, x86_64 or universal2)" ;;
esac

# A macOS bundle cross-built somewhere else is not a macOS bundle: PyInstaller
# collects the host's interpreter and the host's shared libraries. Refusing is
# more useful than producing a Linux tree under a macOS name.
[[ "$(uname -s)" == "Darwin" ]] \
  || die "macOS bundles must be built on macOS; this host is $(uname -s).
     Use scripts/build-linux.sh for Linux output."

for tool in lipo codesign; do
  command -v "${tool}" >/dev/null 2>&1 \
    || die "required tool not found: ${tool}
     Install the Xcode command line tools: xcode-select --install"
done

if [[ -z "${PYTHON_BIN}" ]]; then
  if [[ -x "${APP_DIR}/.venv/bin/python" ]]; then
    PYTHON_BIN="${APP_DIR}/.venv/bin/python"
  else
    PYTHON_BIN="$(command -v python3 || command -v python)" \
      || die "no python interpreter found; set PYTHON_BIN"
  fi
fi

[[ -f "${SPEC_FILE}" ]] || die "missing spec file: ${SPEC_FILE}"

log "interpreter: ${PYTHON_BIN} ($("${PYTHON_BIN}" --version 2>&1))"
log "host: $(sw_vers -productName 2>/dev/null || echo macOS) \
$(sw_vers -productVersion 2>/dev/null || echo unknown) on $(uname -m)"

if ((INSTALL_DEPS)); then
  log "installing build dependencies"
  "${PYTHON_BIN}" -m pip install --upgrade "pyinstaller>=6.3"
fi

"${PYTHON_BIN}" -m PyInstaller --version >/dev/null 2>&1 \
  || die "PyInstaller is not installed in ${PYTHON_BIN}; re-run with --install-deps"
log "PyInstaller $("${PYTHON_BIN}" -m PyInstaller --version)"

# A GPL dependency in the build environment can be pulled into the analysis by
# any import the spec's exclude list has not anticipated, and the result is a
# GPL distribution whatever the licence header says. Refuse by default.
if "${PYTHON_BIN}" -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('pedalboard') else 1)" 2>/dev/null; then
  if [[ "${ALLOW_GPL}" != "1" ]]; then
    die "pedalboard (GPL-3.0) is installed in this interpreter.
     Bundling it makes the whole distribution GPL-3.0. Build from an
     environment without the 'plugins' extra, or set ALLOW_GPL=1 if you
     really mean to produce a GPL artifact."
  fi
  log "WARNING: building with pedalboard present — the output is a GPL-3.0 distribution"
fi

if ((CLEAN)); then
  log "cleaning ${DIST_DIR} and ${WORK_DIR}"
  rm -rf "${DIST_DIR:?}/${NAME}" "${WORK_DIR}"
fi

log "building ${NAME}"
(
  cd "${ROOT_DIR}"
  PYTHONPATH="${APP_DIR}${PYTHONPATH:+:${PYTHONPATH}}" \
    "${PYTHON_BIN}" -m PyInstaller \
    --noconfirm \
    --distpath "${DIST_DIR}" \
    --workpath "${WORK_DIR}" \
    "${SPEC_FILE}"
)

BUNDLE="${DIST_DIR}/${NAME}"
LAUNCHER="${BUNDLE}/${NAME}"
[[ -x "${LAUNCHER}" ]] || die "the build produced no launcher at ${LAUNCHER}"
[[ -d "${BUNDLE}/_internal" ]] \
  || die "no _internal/ directory beside the launcher — did the spec switch to --onefile?
     A self-extracting build defeats LGPL relinking; see packaging/pyinstaller.spec."

# Every Mach-O object in the bundle. Read with a loop rather than mapfile:
# /bin/bash on macOS is still 3.2 and this script has to run there.
MACHO_OBJECTS=()
while IFS= read -r object; do
  MACHO_OBJECTS+=("${object}")
done < <(
  find "${BUNDLE}" -type f \( -name '*.dylib' -o -name '*.so' \) -print | sort
  find "${BUNDLE}" -type d -name '*.framework' -print | sort
)

# The LGPL is satisfied by replaceable shared libraries, so a bundle without
# separate Qt objects in it is a licence problem, not just a surprising build.
log "checking that the LGPL libraries stayed replaceable"
QT_LIBS=()
while IFS= read -r lib; do
  QT_LIBS+=("${lib}")
done < <(find "${BUNDLE}" \
  \( -name 'libQt6Core*.dylib' -o -name 'QtCore.framework' \
  -o -name 'libpyside6*' -o -name 'libshiboken6*' \) -print | sort)
((${#QT_LIBS[@]})) || die "no Qt shared libraries or frameworks in the bundle —
     did the spec switch to --onefile? Relinking is how this project satisfies
     the LGPL for Qt, PySide6 and libsndfile."
for lib in "${QT_LIBS[@]}"; do
  printf '    %s\n' "${lib#"${BUNDLE}/"}"
done

if grep -rqi 'pedalboard' "${BUNDLE}" \
  --include='*.pyc' --include='*.dylib' --include='*.so' 2>/dev/null; then
  die "pedalboard artifacts found in the bundle; refusing to call this an MIT build"
fi

for notice in THIRD_PARTY_LICENSES.md LGPL-RELINKING.txt; do
  [[ -f "${BUNDLE}/_internal/licenses/${notice}" || -f "${BUNDLE}/licenses/${notice}" ]] \
    || die "the bundle is missing licenses/${notice}"
done

# What the bundle runs on is the intersection of what its objects run on. A fat
# Qt library next to a thin numpy makes an arm64-only product, and the release
# name has to say arm64.
log "resolving the architectures this bundle can run on"
read -r -a BUNDLE_ARCHS < <(lipo -archs "${LAUNCHER}") \
  || die "cannot read the launcher architecture: ${LAUNCHER}"
((${#MACHO_OBJECTS[@]})) \
  || die "the bundle contains no shared objects at all; that is not a one-dir build"
NARROWED_BY=""
for object in "${MACHO_OBJECTS[@]}"; do
  object_archs=""
  if [[ -d "${object}" ]]; then
    binary="${object}/Versions/Current/$(basename -- "${object}" .framework)"
    [[ -f "${binary}" ]] || binary="${object}/$(basename -- "${object}" .framework)"
    [[ -f "${binary}" ]] || continue
    object_archs="$(lipo -archs "${binary}" 2>/dev/null || true)"
  else
    object_archs="$(lipo -archs "${object}" 2>/dev/null || true)"
  fi
  [[ -n "${object_archs}" ]] || continue

  kept=()
  for arch in "${BUNDLE_ARCHS[@]}"; do
    if [[ " ${object_archs} " == *" ${arch} "* ]]; then
      kept+=("${arch}")
    elif [[ -z "${NARROWED_BY}" ]]; then
      NARROWED_BY="${object#"${BUNDLE}/"} (${object_archs})"
    fi
  done
  ((${#kept[@]})) || die "no architecture is common to every object in the bundle;
     the first object without the launcher's architecture is ${NARROWED_BY}"
  BUNDLE_ARCHS=("${kept[@]}")
done

has_arm=0
has_intel=0
for arch in "${BUNDLE_ARCHS[@]}"; do
  case "${arch}" in
    arm64 | arm64e) has_arm=1 ;;
    x86_64 | x86_64h) has_intel=1 ;;
  esac
done
if ((has_arm && has_intel)); then
  ARCH_LABEL="universal2"
elif ((has_arm)); then
  ARCH_LABEL="arm64"
elif ((has_intel)); then
  ARCH_LABEL="x86_64"
else
  ARCH_LABEL="${BUNDLE_ARCHS[*]}"
fi
log "bundle architecture: ${ARCH_LABEL} (${BUNDLE_ARCHS[*]})"
[[ -z "${NARROWED_BY}" ]] \
  || log "narrowed from the launcher's own slices by ${NARROWED_BY}"

if [[ -n "${EXPECT_ARCH}" && "${ARCH_LABEL}" != "${EXPECT_ARCH}" ]]; then
  die "this bundle runs on ${ARCH_LABEL}, not the ${EXPECT_ARCH} that was claimed.
     Publish it under a name that matches, or build on a host that produces
     ${EXPECT_ARCH}. universal2 additionally needs universal2 wheels for every
     native dependency, which numpy, scipy and soundfile do not ship."
fi

if [[ -n "${CODESIGN_IDENTITY}" ]]; then
  if [[ "${CODESIGN_IDENTITY}" == "-" ]]; then
    log "ad-hoc signing the bundle (no identity, no Gatekeeper meaning)"
    sign_flags=(--force --sign -)
  else
    log "signing the bundle as ${CODESIGN_IDENTITY} with the hardened runtime"
    sign_flags=(--force --sign "${CODESIGN_IDENTITY}" --options runtime --timestamp)
  fi
  # Nested objects first: a launcher signature covers the objects as they were
  # when it was made, so signing them afterwards invalidates it.
  for object in "${MACHO_OBJECTS[@]}"; do
    codesign "${sign_flags[@]}" "${object}" >/dev/null 2>&1 \
      || warn "could not sign ${object#"${BUNDLE}/"}"
  done
  codesign "${sign_flags[@]}" "${LAUNCHER}" \
    || die "signing the launcher failed"
  codesign --verify --strict --verbose=2 "${LAUNCHER}" \
    || die "the launcher signature does not verify"
  log "signed; NOT notarised — no notarisation tool is invoked by this script"
else
  log "not signed: CODESIGN_IDENTITY is unset"
  log "  Gatekeeper will quarantine a downloaded copy; recipients clear it with"
  log "  xattr -dr com.apple.quarantine <bundle>. See packaging/MACOS.md."
fi

if ((RUN_SMOKE)); then
  log "smoke-testing the bundle"
  "${LAUNCHER}" --version
  QT_QPA_PLATFORM=offscreen "${LAUNCHER}" --offscreen --null-audio --exit-after 2 \
    || die "the bundle did not start"
fi

log "bundle ready: ${BUNDLE} (${ARCH_LABEL})"
log "ship it together with licenses/LGPL-RELINKING.txt and THIRD_PARTY_LICENSES.md"
