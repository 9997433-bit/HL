#!/usr/bin/env bash
# Build a minimal Debian package around the Linux one-dir bundle.
#
# This is a skeleton, not a distribution-quality package: the bundle carries
# its own Python, Qt and libsndfile, so the package installs a self-contained
# tree under /usr/lib/audio-studio and depends only on the X/GL stack that Qt
# needs from the system. It is enough to hand someone a file they can
# `apt install ./audio-studio_*.deb`, and it keeps the pieces the licences
# require: the shared libraries stay separate files, and the notices land in
# /usr/share/doc/audio-studio where a recipient will look for them.
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/linux-packaging.sh
source "${ROOT_DIR}/scripts/lib/linux-packaging.sh"

BUNDLE_DIR="${BUNDLE_DIR:-${ROOT_DIR}/dist/${PACKAGE_NAME}}"
OUTPUT_DIR="${OUTPUT_DIR:-${ROOT_DIR}/dist}"
MAINTAINER="${DEB_MAINTAINER:-Audio Studio Team <releases@example.invalid>}"
VERSION=""
REVISION="${DEB_REVISION:-1}"
ARCH=""
TREE_ONLY=0

# Qt needs these from the host even though the bundle ships Qt itself; the list
# mirrors the runtime packages the CI workflow installs before launching the
# application offscreen.
DEPENDS="libc6, libdbus-1-3, libegl1, libfontconfig1, libgl1, libglib2.0-0,\
 libxcb-cursor0, libxcb-xinerama0, libxi6, libxkbcommon-x11-0, libxrender1"

usage() {
  cat <<'EOF'
Usage: scripts/package-deb.sh [options]

Builds dist/audio-studio_<version>-<revision>_<arch>.deb from the one-dir
bundle produced by scripts/build-linux.sh.

Options:
  --bundle PATH       One-dir bundle to package (default: dist/audio-studio).
  --output-dir PATH   Where the .deb and staging tree go (default: dist/).
  --version X.Y.Z     Upstream version (default: audio-studio/pyproject.toml).
  --revision N        Debian revision (default: 1).
  --arch NAME         Debian architecture (default: dpkg --print-architecture).
  --maintainer TEXT   Maintainer field, "Name <email>".
  --tree-only         Stage the package tree but do not run dpkg-deb.
  -h, --help          Show this help.

Environment:
  BUNDLE_DIR, OUTPUT_DIR, DEB_MAINTAINER, DEB_REVISION are the same settings.

Without dpkg-deb installed the staged tree is still produced; build it
elsewhere with `dpkg-deb --build --root-owner-group <tree> <output.deb>`.
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
    --revision)
      REVISION="$2"
      shift 2
      ;;
    --arch)
      ARCH="$2"
      shift 2
      ;;
    --maintainer)
      MAINTAINER="$2"
      shift 2
      ;;
    --tree-only)
      TREE_ONLY=1
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
[[ -n "${ARCH}" ]] || ARCH="$(detect_deb_architecture)"

mkdir -p "${OUTPUT_DIR}"
OUTPUT_DIR="$(abspath "${OUTPUT_DIR}")"
STAGE="${OUTPUT_DIR}/deb/${PACKAGE_NAME}_${VERSION}-${REVISION}_${ARCH}"
DEB_FILE="${OUTPUT_DIR}/${PACKAGE_NAME}_${VERSION}-${REVISION}_${ARCH}.deb"

log "bundle:  ${BUNDLE_DIR}"
log "package: ${PACKAGE_NAME} ${VERSION}-${REVISION} (${ARCH})"

log "checking the bundle before packaging it"
bundle_license_gate "${BUNDLE_DIR}"

log "staging ${STAGE}"
rm -rf "${STAGE}"
mkdir -p "${STAGE}/DEBIAN" "${STAGE}/usr/lib" "${STAGE}/usr/bin"
cp -a "${BUNDLE_DIR}" "${STAGE}/usr/lib/${PACKAGE_NAME}"

# A wrapper rather than a symlink into /usr/lib: PyInstaller resolves the
# bundle directory from argv[0], and a wrapper also gives us a place to keep
# the LD_LIBRARY_PATH escape hatch that relinking depends on.
cat >"${STAGE}/usr/bin/${PACKAGE_NAME}" <<EOF
#!/bin/sh
# Launch the packaged Audio Studio bundle.
#
# To run against your own build of a bundled LGPL library, either replace the
# file in /usr/lib/${PACKAGE_NAME}/_internal or point LD_LIBRARY_PATH at your
# copy before starting. See /usr/share/doc/${PACKAGE_NAME}/LGPL-RELINKING.txt.
exec /usr/lib/${PACKAGE_NAME}/${PACKAGE_NAME} "\$@"
EOF
chmod 0755 "${STAGE}/usr/bin/${PACKAGE_NAME}"

write_desktop_entry "${STAGE}/usr/share/applications/${PACKAGE_NAME}.desktop"
install_icon "${STAGE}/usr/share/icons/hicolor/scalable/apps/${PACKAGE_NAME}.svg"

DOC_DIR="${STAGE}/usr/share/doc/${PACKAGE_NAME}"
install_license_documents "${BUNDLE_DIR}" "${DOC_DIR}"

cat >"${DOC_DIR}/copyright" <<EOF
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: Audio Studio

Files: *
Copyright: Audio Studio Team
License: MIT

Files: usr/lib/${PACKAGE_NAME}/*
Copyright: various, see THIRD_PARTY_LICENSES.md
License: MIT and LGPL-2.1-or-later and LGPL-3.0-only
 The bundle under /usr/lib/${PACKAGE_NAME} contains Qt 6, PySide6, Shiboken6
 (LGPL-3.0-only), libsndfile and optionally libsoxr and libquadmath
 (LGPL-2.1-or-later), alongside the MIT-licensed application. Those libraries
 are shipped as separate, uncompressed shared objects so that a recipient can
 replace them with a compatible build; LGPL-RELINKING.txt in this directory
 explains how, and where to obtain the corresponding source.
 .
 The full component inventory with versions and licence pointers is in
 THIRD_PARTY_LICENSES.md in this directory.

License: MIT
 Permission is hereby granted, free of charge, to any person obtaining a copy
 of this software and associated documentation files (the "Software"), to deal
 in the Software without restriction, including without limitation the rights
 to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the Software is
 furnished to do so, subject to the following conditions:
 .
 The above copyright notice and this permission notice shall be included in
 all copies or substantial portions of the Software.
 .
 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 SOFTWARE.
EOF

INSTALLED_KB="$(du -sk "${STAGE}/usr" | cut -f1)"

cat >"${STAGE}/DEBIAN/control" <<EOF
Package: ${PACKAGE_NAME}
Version: ${VERSION}-${REVISION}
Section: sound
Priority: optional
Architecture: ${ARCH}
Maintainer: ${MAINTAINER}
Depends: ${DEPENDS}
Installed-Size: ${INSTALLED_KB}
Homepage: https://example.invalid/audio-studio
Description: Professional audio editing and analysis workstation
 Audio Studio is a waveform and spectrum editor with metering, batch
 processing and a non-destructive edit history.
 .
 This package installs a self-contained bundle under /usr/lib/audio-studio.
 The LGPL libraries inside it are separate, uncompressed shared objects and
 can be replaced; see /usr/share/doc/audio-studio/LGPL-RELINKING.txt.
EOF

log "re-checking the staged tree"
bundle_license_gate "${STAGE}"
[[ -f "${DOC_DIR}/copyright" ]] || die "the staged package has no copyright file"

# md5sums is advisory, but dpkg --verify and every packaging lint expect it.
(
  cd "${STAGE}"
  find usr -type f -print0 | LC_ALL=C sort -z \
    | xargs -0 md5sum >"DEBIAN/md5sums"
)

log "staged tree ready: ${STAGE}"

if ((TREE_ONLY)); then
  exit 0
fi

if ! command -v dpkg-deb >/dev/null 2>&1; then
  warn "dpkg-deb is not installed, so the staged tree is the artifact.
     Build the package where dpkg-deb exists:
       dpkg-deb --build --root-owner-group ${STAGE} ${DEB_FILE}"
  exit 0
fi

log "building ${DEB_FILE}"
rm -f "${DEB_FILE}"
dpkg-deb --build --root-owner-group "${STAGE}" "${DEB_FILE}" >/dev/null

# A package that does not list its own notices is the failure mode worth
# catching here: everything above can be right and still lose them to a
# mis-staged path.
CONTENTS="$(dpkg-deb --contents "${DEB_FILE}")"
for required in \
  "usr/share/doc/${PACKAGE_NAME}/copyright" \
  "usr/share/doc/${PACKAGE_NAME}/LGPL-RELINKING.txt" \
  "usr/share/doc/${PACKAGE_NAME}/THIRD_PARTY_LICENSES.md" \
  "usr/bin/${PACKAGE_NAME}"; do
  grep -q "${required}\$" <<<"${CONTENTS}" \
    || die "the built package is missing ${required}"
done

log "package ready: ${DEB_FILE}"
dpkg-deb --info "${DEB_FILE}" | sed -n '2,12p'
log "sign it with scripts/sign-linux-artifact.sh before publishing"
