# Linux packaging and signing — what was run, and what it showed

Evidence for the three wrappers added in this round:
`scripts/package-appimage.sh`, `scripts/package-deb.sh` and
`scripts/sign-linux-artifact.sh`, with the shared license gate in
`scripts/lib/linux-packaging.sh`.

Everything below was executed against a real PyInstaller bundle, not the
synthetic fixture the test suite uses.

## Environment

- Ubuntu 24.04 container, Linux 6.12.94+ x86_64, Python 3.12.3
- PyInstaller bundle from `scripts/build-linux.sh --no-smoke`,
  `dist/audio-studio`, 283 MB unpacked, version 1.1.0
- `dpkg-deb` 1.22.6, `gpg` 2.4.4, `shellcheck` 0.9.0
- `appimagetool` fetched by the script itself from the AppImage continuous
  release

## AppImage

`scripts/package-appimage.sh --fetch-appimagetool` produced
`dist/audio-studio-1.1.0-x86_64.AppImage` (102,955,512 bytes,
sha256 `10273311a558939dcadca21bc2ebb7aa2c303badc2e12d3ede78d386476c61dd`)
by way of `dist/AudioStudio.AppDir`.

Verified by running the file:

```
APPIMAGE_EXTRACT_AND_RUN=1 ./dist/audio-studio-1.1.0-x86_64.AppImage --version
  -> Audio Studio 1.1.0

APPIMAGE_EXTRACT_AND_RUN=1 QT_QPA_PLATFORM=offscreen \
  ./dist/audio-studio-1.1.0-x86_64.AppImage --offscreen --null-audio --exit-after 3
  -> exit 0
```

`APPIMAGE_EXTRACT_AND_RUN` is needed because the container has no FUSE; the
same AppImage mounts normally on a desktop.

## Debian package

`scripts/package-deb.sh` produced `dist/audio-studio_1.1.0-1_amd64.deb`
(84,740,004 bytes,
sha256 `b8670a80e07888508713b631ca7e554877c3b4f5544bc2d3ef8bcb55d74896f8`,
Installed-Size 289,296 kB, 435 md5sums entries).

Installed and run, then purged:

```
sudo dpkg -i dist/audio-studio_1.1.0-1_amd64.deb        -> configured cleanly
QT_QPA_PLATFORM=offscreen audio-studio --version         -> Audio Studio 1.1.0
audio-studio --offscreen --null-audio --exit-after 3     -> exit 0
dpkg -L audio-studio                                     -> /usr/share/doc/audio-studio/
                                                            {copyright,
                                                             LGPL-RELINKING.txt,
                                                             THIRD_PARTY_LICENSES.md}
sudo dpkg --purge audio-studio                           -> removed
```

The desktop entry and the scalable icon landed in `/usr/share/applications`
and `/usr/share/icons/hicolor/scalable/apps`, and the install triggered
`desktop-file-utils` and `hicolor-icon-theme` as a normal package should.

## Signing

`scripts/sign-linux-artifact.sh dist/*.AppImage dist/*.deb` with no
`SIGNING_KEY` in the environment wrote `dist/SHA256SUMS` and
`linux-signing-report.json` in this directory with `signed: false` and the
reason recorded. That is the honest state of this project's Linux releases
today: checksums, no signature.

The signing path itself is covered in
`tests/test_linux_packaging_scripts.py`, which generates a throwaway ed25519
key in a scratch `GNUPGHOME`, signs, and verifies each `.asc` with
`gpg --verify`. An unknown key id fails loudly rather than silently producing
an unsigned release.

## Not covered

- macOS codesigning and notarization, and Windows Authenticode. No script in
  this repository performs them, the project holds neither an Apple Developer
  ID nor a code-signing certificate, and the signing report states all three
  as `false` so no downstream summary can imply otherwise.
- A production release key. Nothing here has been signed with one; the report
  records `signed: false` until `SIGNING_KEY` names a real key.
- Installation on distributions other than the Ubuntu 24.04 container above,
  and any architecture other than amd64/x86_64.
- Reproducibility of the artifacts. The hashes above identify these builds;
  they are not a claim that a rebuild reproduces them byte for byte.
