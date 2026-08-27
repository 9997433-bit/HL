#!/usr/bin/env bash
# Prepare deterministic names for GitHub Release assets.
#
# Python's standard library creates the ZIPs so this behaves the same on
# Linux, macOS, and the Git Bash environment on Windows runners.
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/prepare-release-assets.sh --output-dir DIR [operations]

Operations:
  --bundle PLATFORM DIR  Zip DIR as audio-studio-PLATFORM.zip (repeatable).
  --sbom FILE            Copy FILE as audio-studio-sbom.json.
  --checksums            Generate SHA256SUMS for every prepared asset.
  -h, --help             Show this help.

Examples:
  scripts/prepare-release-assets.sh \
    --output-dir release-assets \
    --bundle linux dist/audio-studio \
    --sbom .agent_workspace/v1.1/linux-sbom.json

  scripts/prepare-release-assets.sh \
    --output-dir release-assets \
    --checksums
EOF
}

OUTPUT_DIR=""
SBOM_PATH=""
GENERATE_CHECKSUMS=0
declare -a BUNDLE_PLATFORMS=()
declare -a BUNDLE_PATHS=()

while (($#)); do
  case "$1" in
    --output-dir)
      (($# >= 2)) || { echo "error: --output-dir requires a value" >&2; exit 2; }
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --bundle)
      (($# >= 3)) || { echo "error: --bundle requires PLATFORM and DIR" >&2; exit 2; }
      BUNDLE_PLATFORMS+=("$2")
      BUNDLE_PATHS+=("$3")
      shift 3
      ;;
    --sbom)
      (($# >= 2)) || { echo "error: --sbom requires a value" >&2; exit 2; }
      SBOM_PATH="$2"
      shift 2
      ;;
    --checksums)
      GENERATE_CHECKSUMS=1
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

[[ -n "${OUTPUT_DIR}" ]] || { echo "error: --output-dir is required" >&2; exit 2; }
if ((${#BUNDLE_PATHS[@]} == 0)) && [[ -z "${SBOM_PATH}" ]] && ((GENERATE_CHECKSUMS == 0)); then
  echo "error: specify at least one --bundle, --sbom, or --checksums operation" >&2
  exit 2
fi

PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="$(command -v python3 || command -v python)" || {
    echo "error: no Python interpreter found; set PYTHON_BIN" >&2
    exit 1
  }
fi

mkdir -p "${OUTPUT_DIR}"

for index in "${!BUNDLE_PATHS[@]}"; do
  platform="${BUNDLE_PLATFORMS[$index]}"
  bundle="${BUNDLE_PATHS[$index]}"
  [[ "${platform}" =~ ^[A-Za-z0-9._-]+$ ]] || {
    echo "error: invalid platform name: ${platform}" >&2
    exit 2
  }
  [[ -d "${bundle}" ]] || {
    echo "error: bundle directory does not exist: ${bundle}" >&2
    exit 1
  }

  "${PYTHON_BIN}" - "${OUTPUT_DIR}" "${platform}" "${bundle}" <<'PY'
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

output_dir = Path(sys.argv[1])
platform = sys.argv[2]
bundle = Path(sys.argv[3])
archive = output_dir / f"audio-studio-{platform}.zip"

with ZipFile(archive, "w", compression=ZIP_DEFLATED, compresslevel=9) as zip_file:
    for path in sorted(bundle.rglob("*")):
        if path.is_file():
            zip_file.write(path, Path("audio-studio") / path.relative_to(bundle))

print(f"prepared {archive}")
PY
done

if [[ -n "${SBOM_PATH}" ]]; then
  [[ -f "${SBOM_PATH}" ]] || {
    echo "error: SBOM does not exist: ${SBOM_PATH}" >&2
    exit 1
  }
  "${PYTHON_BIN}" - "${OUTPUT_DIR}" "${SBOM_PATH}" <<'PY'
import shutil
import sys
from pathlib import Path

output = Path(sys.argv[1]) / "audio-studio-sbom.json"
source = Path(sys.argv[2])
if source.resolve() != output.resolve():
    shutil.copyfile(source, output)
print(f"prepared {output}")
PY
fi

if ((GENERATE_CHECKSUMS)); then
  "${PYTHON_BIN}" - "${OUTPUT_DIR}" <<'PY'
import hashlib
import sys
from pathlib import Path

output_dir = Path(sys.argv[1])
manifest = output_dir / "SHA256SUMS"
assets = sorted(path for path in output_dir.iterdir() if path.is_file() and path != manifest)
if not assets:
    raise SystemExit(f"error: no release assets found in {output_dir}")

lines = []
for asset in assets:
    digest = hashlib.sha256()
    with asset.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    lines.append(f"{digest.hexdigest()}  {asset.name}")

manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"prepared {manifest}")
PY
fi
