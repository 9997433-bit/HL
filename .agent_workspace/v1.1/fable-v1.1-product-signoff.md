# v1.1.0 Product Signoff — Round G (fable)

- **Date:** 2026-08-27
- **Branch:** `cursor/v1.0-round-g-b3cf` → merge to alpha
- **Version:** `1.1.0`
- **Tag:** `v1.1.0`

## What v1.1.0 is

The first release of Audio Studio a user can **download and run** rather than
build from source. Round G turns the packaging scaffold that has sat in the
tree since the beta (`packaging/pyinstaller.spec`, `scripts/build-linux.sh`)
into a release pipeline: a `v*` tag push builds the Linux bundle in CI and
publishes it as a downloadable artifact with an SBOM, and the packaging
wrappers produced real, smoke-tested AppImage and deb artifacts on this VM.
v1.0.1's 30/30 SOTA checklist state is unchanged underneath.

## Verdicts

| Claim | Verdict |
|---|---|
| **First distributable Linux build** | **Go** — AppImage and deb built, run and hash-recorded; CI uploads the bundle on every `v*` tag |
| **Release CI artifact** | **Go** — `audio-studio-linux-x64` from `.github/workflows/release-linux.yml` |
| **SBOM shipped with the build** | **Go** — CycloneDX 1.5 bundle SBOM (151 components) + SPDX-shaped build-environment SBOM |
| **Signing scaffold** | **Go — scaffold only**: SHA256SUMS + optional GPG detached signatures; current releases are checksummed, **unsigned** |
| **macOS installer** | **No-Go** (source install remains) |
| **Windows installer** | **No-Go** (source install remains) |
| **Apple / Microsoft code signing** | **No-Go** (no certificates held; no script performs either) |

## Round G deliverables

| Deliverable | Where | Evidence |
|---|---|---|
| Linux release workflow | `.github/workflows/release-linux.yml` | `v*` tags + manual dispatch; uploads `audio-studio-linux-x64`; contract-tested by `tests/test_release_workflow.py` |
| One-directory bundle | `scripts/build-linux.sh` + `packaging/pyinstaller.spec` | `linux-build-report.json`: status **pass**, 454 files, launcher sha256 recorded, LGPL Qt libraries verified replaceable, pedalboard (GPL-3.0) refused, license notices bundled |
| AppImage | `scripts/package-appimage.sh` | `audio-studio-1.1.0-x86_64.AppImage`, 103 MB, sha256 recorded, `--version` and offscreen smoke run — `linux-packaging-evidence.md` |
| Debian package | `scripts/package-deb.sh` | `audio-studio_1.1.0-1_amd64.deb`, 85 MB, installed / run / purged cleanly on Ubuntu 24.04 |
| Signing scaffold | `scripts/sign-linux-artifact.sh` | `linux-signing-report.json`: SHA256SUMS written, `signed: false` ("no SIGNING_KEY configured"); GPG path exercised in `tests/test_linux_packaging_scripts.py` with a throwaway key |
| SBOM generation | `tools/generate_sbom.py`, guide in `packaging/DISTRIBUTION.md` | `linux-sbom.json` (CycloneDX 1.5, 151 components), `packaging/SBOM.json` (build environment), schema and license policy enforced by `tests/test_sbom.py` |

## Honest gaps

These ship *disclosed*, not silently claimed:

1. **No macOS or Windows installers.** Both platforms remain
   `pip install ./audio-studio` source installs, exercised by CI smoke lanes
   only. The PyInstaller spec has never been run on either platform.
2. **No Apple or Microsoft code signing.** The project holds no Apple
   Developer ID and no Authenticode certificate; no script in this repository
   performs codesigning, notarization or Authenticode, and the signing report
   records all three as `false`. The scaffold provides integrity for people
   who verify checksums, not platform trust.
3. **Linux artifacts are unsigned.** `sign-linux-artifact.sh` wrote checksums
   and recorded `signed: false`; a production `SIGNING_KEY` has never signed
   anything here.
4. **Distribution channel.** CI publishes the raw bundle directory as a
   workflow artifact (GitHub login required to download); the AppImage and
   deb were built and verified locally by the wrappers, not published from CI,
   and nothing is attached to a GitHub Release or a package repository.
5. **Platform scope.** x86_64 only, built and installed on Ubuntu 24.04; no
   arm64, no other-distribution installs tested, and the recorded hashes are
   not a reproducible-build claim.

## Test evidence

Carried forward from v1.0.1 (no engine changes in Round G): application suite
1721 passed / 12 skipped; SOTA checklist 31 passed / 0 xfailed. Round G adds
contract tests for the release workflow (`tests/test_release_workflow.py`),
the packaging wrappers and signing path
(`tests/test_linux_packaging_scripts.py`), and the SBOM artifacts
(`tests/test_sbom.py`).

## Tag instruction

Tag **`v1.1.0`** on the merge commit after CI is green; the tag push is what
triggers the first distributable build.
