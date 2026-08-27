# Building and shipping the Audio Studio macOS distribution

This is the release engineer's guide to the macOS bundle: how to build it,
what the build refuses to do, and what a recipient has to know because this
project holds no Apple Developer ID. The Linux procedure and the licence
rationale behind the gates live in `packaging/DISTRIBUTION.md` and
`THIRD_PARTY_LICENSES.md`; only the macOS-specific parts are repeated here.

## What the build produces

| Piece | Where it comes from |
|---|---|
| One-directory bundle `dist/audio-studio/` | `scripts/build-macos.sh` (PyInstaller, `packaging/pyinstaller.spec`) |
| Licence notices inside the bundle | `_internal/licenses/THIRD_PARTY_LICENSES.md` and `_internal/licenses/LGPL-RELINKING.txt`, placed by the spec |
| Release ZIP `audio-studio-macos-arm64.zip` | `scripts/prepare-release-assets.sh`, run by `.github/workflows/publish-release.yml` |

There is no `.app` wrapper and no `.dmg`. The spec has no `BUNDLE` step, so the
output is the same one-directory tree as on Linux, run as
`dist/audio-studio/audio-studio`. A `.dmg` of an unsigned, un-notarised `.app`
is worse for a recipient than a directory, because Gatekeeper refuses a
downloaded application outright while a command-line launch can be allowed.
Revisit this when there is an identity to sign with.

There is also no macOS SBOM. `tools/generate_sbom.py` inventories a Linux
bundle — it writes `linux-sbom.json` and scans for `.so` files — so running it
against a macOS build would produce a mislabelled document. The release
workflow says so in the job log rather than pretending to parity.

## Building

Build on macOS, from an environment **without** the `plugins` extra:
pedalboard is GPL-3.0 and its presence would relicense the whole artifact.

```bash
# from the repository root; uses audio-studio/.venv by default
scripts/build-macos.sh --install-deps --clean
```

The script is `scripts/build-linux.sh`'s counterpart and runs the same
distribution gates. It fails, rather than produce a bundle, when:

- pedalboard is importable in the build interpreter (`ALLOW_GPL=1` overrides
  this and produces a GPL-3.0 artifact that must never be published as MIT);
- the Qt/PySide6 objects are missing from the output — on macOS it looks for
  `libQt6Core*.dylib`, `QtCore.framework`, `libpyside6*` and `libshiboken6*` —
  which would mean the LGPL libraries are no longer replaceable;
- there is no `_internal/` directory beside the launcher, the shape a
  `--onefile` build would have;
- pedalboard artifacts appear anywhere in the bundle;
- the licence notices are absent from `_internal/licenses/`;
- the bundle's architecture does not match `--expect-arch` (see below);
- the offscreen smoke test (`--offscreen --null-audio --exit-after 2`) fails.

Useful variants: `--no-smoke` for a machine that cannot start Qt offscreen,
`--dist-dir PATH` to build elsewhere, `PYTHON_BIN=...` to select the
interpreter. The script runs under the system `/bin/bash` 3.2; no bash 4
builtins are used.

Cross-building is refused. PyInstaller collects the host interpreter and the
host's shared libraries, so a "macOS" bundle produced on Linux would be a Linux
tree under a misleading name.

## Architecture: arm64, not universal

`--expect-arch arm64|x86_64|universal2` makes the build fail unless the bundle
runs on exactly that architecture. Use it whenever the artifact name states an
architecture — that is the whole point of the flag, and both workflows pass
`--expect-arch arm64`.

The architecture is computed as the intersection of the slices in *every*
Mach-O object in the bundle, not from the launcher alone, because a bundle is
only as portable as its narrowest library. That distinction is load-bearing
here: PySide6 ships `universal2` wheels, but numpy, scipy and soundfile publish
separate `arm64` and `x86_64` wheels and no fat ones. An Apple silicon build
therefore contains fat Qt libraries and thin numpy, and is an **arm64 product**.
Calling it universal because `lipo -archs` on some library prints two
architectures would be false.

A genuine `universal2` bundle needs universal2 wheels (or from-source builds)
for every native dependency. Until those exist upstream, publishing an Intel
build means running the same workflow on an Intel runner and naming the result
`x86_64`.

## Code signing (optional) and notarisation (not performed)

Signing is opt-in through `CODESIGN_IDENTITY`:

```bash
# ad-hoc: satisfies the arm64 loader, tells Gatekeeper nothing about origin
CODESIGN_IDENTITY=- scripts/build-macos.sh

# a real identity from the login keychain, with the hardened runtime
CODESIGN_IDENTITY="Developer ID Application: Example Ltd (TEAMID)" \
  scripts/build-macos.sh
```

Unset — the default, and what CI uses — leaves the bundle exactly as
PyInstaller produced it. When an identity is given, every `.dylib`, `.so` and
`.framework` in the bundle is signed before the launcher, because a launcher
signature covers the nested objects as they were when it was made, and the
launcher signature is then verified with `codesign --verify --strict`.

**Notarisation is never performed by this project.** It requires an Apple ID
enrolled in the Developer Program and a Developer ID certificate, neither of
which exists here, so no `notarytool`, `altool` or `stapler` invocation appears
in the build script or the workflows. Nothing in the release output may claim
otherwise.

The practical consequence for a recipient: a bundle downloaded through a
browser carries the `com.apple.quarantine` attribute, and Gatekeeper will
refuse to run it with a message about an unidentified developer. Clearing that
is the recipient's deliberate act, and the release notes should say so:

```bash
tar -xzf audio-studio-macos-arm64.tar.gz     # or unzip the release ZIP
xattr -dr com.apple.quarantine audio-studio
./audio-studio/audio-studio
```

## Verifying LGPL compliance on the built artifact

The LGPL is satisfied by keeping its libraries replaceable, which on macOS
means checking the same property against `.dylib` files and frameworks:

1. **Confirm the LGPL objects are present and separate.**

   ```bash
   find dist/audio-studio -name 'libQt6Core*.dylib' -o -name 'QtCore.framework' \
        -o -name 'libpyside6*' -o -name 'libsndfile*'
   ```

   Every hit must be a file or framework directory under `_internal/`, not
   something embedded in the launcher.

2. **Confirm nothing rewrote them.** `strip=False` and `upx=False` in
   `packaging/pyinstaller.spec` are licence obligations, not tuning knobs.
   Signing with an identity does modify the objects, which is permitted — a
   recipient can re-sign a replacement ad-hoc — but stripping or compressing
   them is not.

3. **Exercise the replacement path once per release.** Replace the Qt object
   in `_internal/` with a same-major build of your own and start the launcher.
   If the application does not come up, the distribution does not meet the
   terms described in `LGPL-RELINKING.txt`. On a signed bundle, re-sign the
   replaced object (`codesign --force --sign - <object>`) first, and say in the
   release notes that this is what a recipient has to do.

4. **Confirm the notices ship.** `_internal/licenses/LGPL-RELINKING.txt` and
   `_internal/licenses/THIRD_PARTY_LICENSES.md` must be inside the bundle and
   inside whatever archive is published from it.

## Where the workflows fit

- `.github/workflows/publish-release.yml` builds macOS on a `v*` tag through
  `scripts/build-macos.sh --expect-arch arm64` and publishes
  `audio-studio-macos-arm64.zip` as part of the GitHub Release. It is the only
  tag-triggered workflow.
- `.github/workflows/release-macos.yml` builds the same bundle on demand
  (`workflow_dispatch`) and on pull requests that touch the macOS build path.
  It uploads `audio-studio-macos-arm64.tar.gz`: a tar, because
  `actions/upload-artifact` zips its input, which would drop the executable bit
  and dereference the symlinks inside the Qt frameworks.
