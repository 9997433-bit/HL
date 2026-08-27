# v1.1.0 Product Signoff — Round G (fable)

- **Date:** 2026-08-27
- **Branch:** `cursor/v1.0-round-g-b3cf` → merge to alpha
- **Version:** `1.1.0`
- **Tag:** `v1.1.0`

## What v1.1.0 is

The first release of Audio Studio a user can **download and run** rather than
build from source. Round G turns the packaging scaffold that has sat in the
tree since the beta (`packaging/pyinstaller.spec`, `scripts/build-linux.sh`)
into a release pipeline: a `v*` tag push builds the Linux bundle in CI,
generates a software bill of materials, and publishes the result as a
downloadable artifact. v1.0.1's 30/30 SOTA checklist state is unchanged
underneath.

## Verdicts

| Claim | Verdict |
|---|---|
| **First distributable Linux build** | **Go** |
| **Release CI artifact on every `v*` tag** | **Go** |
| **SBOM shipped with the artifact** | **Go** |
| **Artifact integrity (signing scaffold)** | **Go — scaffold only, no platform-vendor certificates** |
| **macOS installer** | **No-Go** (source install remains) |
| **Windows installer** | **No-Go** (source install remains) |
| **Apple / Microsoft code signing** | **No-Go** (no certificates provisioned) |

## Round G deliverables

| Deliverable | Where | Notes |
|---|---|---|
| Linux release workflow | `.github/workflows/release-linux.yml` | `v*` tags + manual dispatch; uploads `audio-studio-linux-x64`; contract-tested by `tests/test_release_workflow.py` |
| Distributable Linux bundle | `scripts/build-linux.sh` + `packaging/pyinstaller.spec` | One-directory PyInstaller build; LGPL libraries verified replaceable; pedalboard (GPL-3.0) refused; license notices bundled |
| SBOM | release pipeline SBOM step | Dependency inventory generated at build time and shipped beside the bundle |
| Signing scaffold | release pipeline | Integrity artifacts (checksums / local signatures) — establishes the workflow a real certificate will slot into |

## Honest gaps

These ship *disclosed*, not silently claimed:

1. **No macOS or Windows installers.** Those platforms remain
   `pip install ./audio-studio` source installs, exercised by CI smoke lanes
   only. The PyInstaller spec has never been run on either platform.
2. **No Apple or Microsoft code signing.** There is no Apple Developer ID
   certificate, no notarization, and no Microsoft Authenticode certificate.
   The signing scaffold provides integrity verification for people who check,
   not platform trust: Gatekeeper and SmartScreen would warn on hypothetical
   future bundles until real certificates are provisioned.
3. **Linux bundle scope.** x86_64 only, built on GitHub `ubuntu-latest`; glibc
   compatibility is whatever that runner provides. No arm64 build, no
   reproducible-build attestation.
4. **Distribution channel.** The bundle is a CI artifact attached to the
   workflow run, not a GitHub Release asset, package-manager entry, AppImage,
   Flatpak or deb — the artifact requires a GitHub login to download.
5. **SBOM boundary.** The SBOM inventories the Python dependency closure of
   the bundle; system shared libraries collected by PyInstaller are covered by
   the license notices (`THIRD_PARTY_LICENSES.md`, `LGPL-RELINKING.txt`)
   rather than SBOM entries.

## Test evidence

Carried forward from v1.0.1 (no engine changes in Round G): application suite
1721 passed / 12 skipped; SOTA checklist 31 passed / 0 xfailed. Round G adds
release-workflow contract tests (`tests/test_release_workflow.py`).

## Tag instruction

Tag **`v1.1.0`** on the merge commit after CI is green; the tag push is what
triggers the first distributable build.
