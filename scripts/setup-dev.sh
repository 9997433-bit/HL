#!/usr/bin/env bash
# Bootstrap the Python environment and report native audio prerequisites.
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-${ROOT_DIR}/.venv}"
PYTHON_BIN="${PYTHON_BIN:-}"
INSTALL_DEV=1
USE_VENV=1
STRICT_PROBE=0
PROBE_OUTPUT="${ROOT_DIR}/.agent_workspace/round1/system-probe.json"

usage() {
  cat <<'EOF'
Usage: scripts/setup-dev.sh [options]

Options:
  --runtime-only       Install requirements.txt without development tools.
  --no-venv            Install into the active Python environment.
  --strict             Fail when the final system probe is not fully ready.
  --probe-output PATH  Set the JSON probe output path.
  -h, --help           Show this help.

Environment:
  PYTHON_BIN            Python interpreter to use (default: python3/python).
  VENV_DIR              Virtual environment path (default: .venv).
EOF
}

while (($#)); do
  case "$1" in
    --runtime-only)
      INSTALL_DEV=0
      shift
      ;;
    --no-venv)
      USE_VENV=0
      shift
      ;;
    --strict)
      STRICT_PROBE=1
      shift
      ;;
    --probe-output)
      if (($# < 2)); then
        printf 'error: --probe-output requires a path\n' >&2
        exit 2
      fi
      PROBE_OUTPUT="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'error: unknown option: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "${PYTHON_BIN}" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    printf 'error: Python 3.11-3.13 is required but was not found.\n' >&2
    exit 1
  fi
fi

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  printf 'error: Python interpreter not found: %s\n' "${PYTHON_BIN}" >&2
  exit 1
fi

if ! "${PYTHON_BIN}" -c 'import sys; raise SystemExit(not ((3, 11) <= sys.version_info[:2] < (3, 14)))'; then
  printf 'error: Python 3.11-3.13 is required.\n' >&2
  "${PYTHON_BIN}" --version >&2
  exit 1
fi

if ((USE_VENV)); then
  if [[ ! -x "${VENV_DIR}/bin/python" && ! -x "${VENV_DIR}/Scripts/python.exe" ]]; then
    printf 'Creating virtual environment at %s\n' "${VENV_DIR}"
    "${PYTHON_BIN}" -m venv "${VENV_DIR}"
  fi
  if [[ -x "${VENV_DIR}/Scripts/python.exe" ]]; then
    PYTHON_BIN="${VENV_DIR}/Scripts/python.exe"
  else
    PYTHON_BIN="${VENV_DIR}/bin/python"
  fi
fi

REQUIREMENTS_FILE="${ROOT_DIR}/requirements.txt"
if ((INSTALL_DEV)); then
  REQUIREMENTS_FILE="${ROOT_DIR}/requirements-dev.txt"
fi

printf 'Using %s\n' "$("${PYTHON_BIN}" --version 2>&1)"
printf 'Installing pinned dependencies from %s\n' "${REQUIREMENTS_FILE}"
"${PYTHON_BIN}" -m pip install --upgrade pip
"${PYTHON_BIN}" -m pip install --requirement "${REQUIREMENTS_FILE}"

printf 'Probing PortAudio, ALSA, ffmpeg, Python libraries, and audio devices\n'
probe_args=(--output "${PROBE_OUTPUT}")
if ((STRICT_PROBE)); then
  probe_args+=(--strict)
fi
set +e
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/probe-system.py" "${probe_args[@]}"
probe_exit=$?
set -e

"${PYTHON_BIN}" - "${PROBE_OUTPUT}" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(f"Probe status: {report['status']}")
missing = report["missing_dependencies"]
if missing:
    print("Missing dependencies:")
    for item in missing:
        print(f"  - {item['name']} ({item['kind']}): {item['detail']}")
else:
    print("Missing dependencies: none")
risks = report["platform_risks"]
if risks:
    print("Platform risks:")
    for item in risks:
        print(f"  - {item['code']}: {item['detail']}")
else:
    print("Platform risks: none")
print(f"Probe JSON: {sys.argv[1]}")
PY

case "$(uname -s 2>/dev/null || true)" in
  Darwin)
    printf 'Native dependency hint: brew install portaudio libsndfile ffmpeg\n'
    ;;
  Linux*)
    printf 'Native dependency hint (Debian/Ubuntu): sudo apt-get install portaudio19-dev libasound2-dev libsndfile1-dev ffmpeg\n'
    ;;
  MINGW*|MSYS*|CYGWIN*)
    printf 'Windows hint: PortAudio is bundled by sounddevice wheels; install ffmpeg separately and add it to PATH.\n'
    ;;
esac

exit "${probe_exit}"
