#!/usr/bin/env bash
# Build the Audio Studio desktop bundle for Linux and check what it contains.
#
# The interesting part of this script is not the PyInstaller invocation, which
# is three lines, but the gates around it: a bundle is a distribution, and a
# distribution is where the licence terms of everything inside it come due.
# See packaging/pyinstaller.spec and packaging/LGPL-RELINKING.txt.
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
ALLOW_GPL="${ALLOW_GPL:-0}"

usage() {
  cat <<'EOF'
Usage: scripts/build-linux.sh [options]

Options:
  --clean           Remove previous dist/ and build/ output first.
  --install-deps    Install PyInstaller into the selected interpreter.
  --no-smoke        Skip launching the built bundle offscreen.
  --dist-dir PATH   Output directory (default: dist/).
  -h, --help        Show this help.

Environment:
  PYTHON_BIN        Interpreter to build with (default: audio-studio/.venv,
                    then the active python3).
  ALLOW_GPL=1       Permit building while pedalboard is installed. The result
                    is a GPL-3.0 distribution and must not be published as an
                    MIT binary; see THIRD_PARTY_LICENSES.md.
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
die() {
  printf '\033[1;31merror:\033[0m %s\n' "$*" >&2
  exit 1
}

if [[ -z "${PYTHON_BIN}" ]]; then
  if [[ -x "${APP_DIR}/.venv/bin/python" ]]; then
    PYTHON_BIN="${APP_DIR}/.venv/bin/python"
  else
    PYTHON_BIN="$(command -v python3 || command -v python)" \
      || die "no python interpreter found; set PYTHON_BIN"
  fi
fi

[[ "$(uname -s)" == "Linux" ]] || log "not running on Linux — building anyway, output is host-specific"
[[ -f "${SPEC_FILE}" ]] || die "missing spec file: ${SPEC_FILE}"

log "interpreter: ${PYTHON_BIN} ($("${PYTHON_BIN}" --version 2>&1))"

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
  rm -rf "${DIST_DIR}/${NAME}" "${WORK_DIR}"
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

# The LGPL is satisfied by replaceable shared libraries, so a bundle without
# separate Qt objects in it is a licence problem, not just a surprising build.
log "checking that the LGPL libraries stayed replaceable"
mapfile -t QT_LIBS < <(find "${BUNDLE}" -name 'libQt6Core.so*' -o -name 'libpyside6*' | sort)
((${#QT_LIBS[@]})) || die "no Qt shared libraries in the bundle — did the spec switch to --onefile?"
for lib in "${QT_LIBS[@]}"; do
  printf '    %s\n' "${lib#"${BUNDLE}/"}"
done

if grep -rqi 'pedalboard' "${BUNDLE}" --include='*.pyc' --include='*.so' 2>/dev/null; then
  die "pedalboard artifacts found in the bundle; refusing to call this an MIT build"
fi

for notice in THIRD_PARTY_LICENSES.md LGPL-RELINKING.txt; do
  [[ -f "${BUNDLE}/_internal/licenses/${notice}" || -f "${BUNDLE}/licenses/${notice}" ]] \
    || die "the bundle is missing licenses/${notice}"
done

if ((RUN_SMOKE)); then
  log "smoke-testing the bundle"
  "${LAUNCHER}" --version
  QT_QPA_PLATFORM=offscreen "${LAUNCHER}" --offscreen --null-audio --exit-after 2 \
    || die "the bundle did not start"
fi

log "bundle ready: ${BUNDLE}"
log "ship it together with licenses/LGPL-RELINKING.txt and THIRD_PARTY_LICENSES.md"
