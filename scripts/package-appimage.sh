#!/usr/bin/env bash
# Wrap the Linux one-dir bundle into an AppDir, and into an AppImage when
# appimagetool is available.
#
# The AppDir is the part this script guarantees: a spec-shaped directory with
# AppRun, a desktop entry, an icon and the licence notices, produced from
# dist/audio-studio without flattening or compressing anything. Turning that
# into a single .AppImage file is one appimagetool invocation, and appimagetool
# is a large binary that needs FUSE, so it is optional here and the exact
# command is printed when it is missing.
#
# The bundle must stay a directory of replaceable shared libraries inside the
# AppDir: an AppImage mounts read-only, but a recipient can extract it with
# `--appimage-extract`, replace an LGPL library in the extracted tree and run
# AppRun from there. See packaging/LGPL-RELINKING.txt.
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/linux-packaging.sh
source "${ROOT_DIR}/scripts/lib/linux-packaging.sh"

BUNDLE_DIR="${BUNDLE_DIR:-${ROOT_DIR}/dist/${PACKAGE_NAME}}"
OUTPUT_DIR="${OUTPUT_DIR:-${ROOT_DIR}/dist}"
APPIMAGETOOL="${APPIMAGETOOL:-}"
VERSION=""
ARCH=""
FETCH_TOOL=0
APPDIR_ONLY=0
REQUIRE_APPIMAGE=0

APPIMAGETOOL_URL_BASE="https://github.com/AppImage/appimagetool/releases/download/continuous"

usage() {
  cat <<'EOF'
Usage: scripts/package-appimage.sh [options]

Builds dist/AudioStudio.AppDir from the one-dir bundle, then an AppImage if
appimagetool can be found.

Options:
  --bundle PATH        One-dir bundle to wrap (default: dist/audio-studio).
  --output-dir PATH    Where the AppDir and AppImage go (default: dist/).
  --version X.Y.Z      Version for the AppImage file name (default: read from
                       audio-studio/pyproject.toml).
  --arch NAME          AppImage architecture tag (default: from uname -m).
  --appimagetool PATH  Use this appimagetool binary.
  --fetch-appimagetool Download appimagetool from GitHub if it is not present.
  --appdir-only        Stop after the AppDir; never run appimagetool.
  --require-appimage   Fail instead of stopping at the AppDir when appimagetool
                       is unavailable (use this in release CI).
  -h, --help           Show this help.

Environment:
  BUNDLE_DIR, OUTPUT_DIR, APPIMAGETOOL   Same as the options above.

Manual step when appimagetool is not installed:

  wget -O appimagetool https://github.com/AppImage/appimagetool/releases/\
download/continuous/appimagetool-x86_64.AppImage
  chmod +x appimagetool
  ./appimagetool dist/AudioStudio.AppDir dist/audio-studio-<version>-x86_64.AppImage

  In a container without FUSE, run appimagetool as
  `./appimagetool --appimage-extract-and-run ...`.
EOF
}

while (($#)); do
  case "$1" in
    --bundle)
      BUNDLE_DIR="$2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --version)
      VERSION="$2"
      shift 2
      ;;
    --arch)
      ARCH="$2"
      shift 2
      ;;
    --appimagetool)
      APPIMAGETOOL="$2"
      shift 2
      ;;
    --fetch-appimagetool)
      FETCH_TOOL=1
      shift
      ;;
    --appdir-only)
      APPDIR_ONLY=1
      shift
      ;;
    --require-appimage)
      REQUIRE_APPIMAGE=1
      shift
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

BUNDLE_DIR="$(resolve_bundle "${BUNDLE_DIR}")"
[[ -n "${VERSION}" ]] || VERSION="$(detect_version)"
[[ -n "${ARCH}" ]] || ARCH="$(appimage_architecture)"

mkdir -p "${OUTPUT_DIR}"
OUTPUT_DIR="$(abspath "${OUTPUT_DIR}")"
APPDIR="${OUTPUT_DIR}/AudioStudio.AppDir"

log "bundle:  ${BUNDLE_DIR}"
log "version: ${VERSION} (${ARCH})"

log "checking the bundle before wrapping it"
bundle_license_gate "${BUNDLE_DIR}"

log "laying out ${APPDIR}"
rm -rf "${APPDIR}"
mkdir -p "${APPDIR}/usr/lib" "${APPDIR}/usr/bin"
# -a keeps symlinks, permissions and the separate .so files intact; a copy that
# dereferences or strips them breaks both Qt's plugin loading and relinking.
cp -a "${BUNDLE_DIR}" "${APPDIR}/usr/lib/${PACKAGE_NAME}"

cat >"${APPDIR}/AppRun" <<EOF
#!/usr/bin/env bash
# AppImage entry point: hand over to the bundled launcher in place.
set -Eeuo pipefail
HERE="\$(cd -- "\$(dirname -- "\$(readlink -f -- "\${BASH_SOURCE[0]}")")" && pwd)"
export PATH="\${HERE}/usr/bin\${PATH:+:\${PATH}}"
exec "\${HERE}/usr/lib/${PACKAGE_NAME}/${PACKAGE_NAME}" "\$@"
EOF
chmod +x "${APPDIR}/AppRun"

# appimagetool reads the desktop entry and the icon from the AppDir root; the
# copies under usr/share are what a desktop environment integrates after the
# AppImage is installed by a tool such as appimaged.
write_desktop_entry "${APPDIR}/${PACKAGE_NAME}.desktop"
write_desktop_entry "${APPDIR}/usr/share/applications/${PACKAGE_NAME}.desktop"
install_icon "${APPDIR}/${PACKAGE_NAME}.svg"
install_icon "${APPDIR}/usr/share/icons/hicolor/scalable/apps/${PACKAGE_NAME}.svg"
install_license_documents "${BUNDLE_DIR}" "${APPDIR}/usr/share/doc/${PACKAGE_NAME}"

log "re-checking the AppDir"
bundle_license_gate "${APPDIR}"

log "AppDir ready: ${APPDIR}"

if ((APPDIR_ONLY)); then
  exit 0
fi

if [[ -z "${APPIMAGETOOL}" ]] && command -v appimagetool >/dev/null 2>&1; then
  APPIMAGETOOL="$(command -v appimagetool)"
fi

if [[ -z "${APPIMAGETOOL}" ]] && ((FETCH_TOOL)); then
  TOOL_CACHE="${ROOT_DIR}/build/appimagetool"
  mkdir -p "${TOOL_CACHE}"
  TOOL_PATH="${TOOL_CACHE}/appimagetool-${ARCH}.AppImage"
  TOOL_URL="${APPIMAGETOOL_URL_BASE}/appimagetool-${ARCH}.AppImage"
  if [[ ! -x "${TOOL_PATH}" ]]; then
    log "downloading ${TOOL_URL}"
    if command -v wget >/dev/null 2>&1; then
      wget --quiet --output-document "${TOOL_PATH}" "${TOOL_URL}" \
        || die "download failed: ${TOOL_URL}"
    elif command -v curl >/dev/null 2>&1; then
      curl --silent --show-error --location --fail \
        --output "${TOOL_PATH}" "${TOOL_URL}" \
        || die "download failed: ${TOOL_URL}"
    else
      die "neither wget nor curl is available to fetch appimagetool"
    fi
    chmod +x "${TOOL_PATH}"
  fi
  APPIMAGETOOL="${TOOL_PATH}"
fi

if [[ -z "${APPIMAGETOOL}" ]]; then
  MESSAGE="appimagetool is not installed, so the AppDir is the artifact.
     Finish the AppImage with:
       ${APPIMAGETOOL_URL_BASE}/appimagetool-${ARCH}.AppImage
       chmod +x appimagetool-${ARCH}.AppImage
       ./appimagetool-${ARCH}.AppImage ${APPDIR} \\
         ${OUTPUT_DIR}/${PACKAGE_NAME}-${VERSION}-${ARCH}.AppImage
     Or re-run this script with --fetch-appimagetool."
  if ((REQUIRE_APPIMAGE)); then
    die "${MESSAGE}"
  fi
  warn "${MESSAGE}"
  exit 0
fi

APPIMAGE="${OUTPUT_DIR}/${PACKAGE_NAME}-${VERSION}-${ARCH}.AppImage"
log "running ${APPIMAGETOOL}"
rm -f "${APPIMAGE}"

# appimagetool is itself an AppImage: without FUSE in the sandbox it has to
# unpack itself first, and ARCH is how it labels the output when it cannot
# infer one.
APPIMAGE_EXTRACT_AND_RUN=1 ARCH="${ARCH}" "${APPIMAGETOOL}" \
  --no-appstream "${APPDIR}" "${APPIMAGE}" \
  || die "appimagetool failed; the AppDir at ${APPDIR} is still usable"

[[ -f "${APPIMAGE}" ]] || die "appimagetool reported success but produced no ${APPIMAGE}"
chmod +x "${APPIMAGE}"

log "AppImage ready: ${APPIMAGE}"
log "sign it with scripts/sign-linux-artifact.sh before publishing"
