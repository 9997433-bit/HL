# v1.2.0 Product Signoff — Round H (fable)

- **Date:** 2026-08-27
- **Branch:** `cursor/v1.0-round-h-b3cf` → merge to alpha
- **Version:** `1.2.0`
- **Tag:** `v1.2.0`

## What v1.2.0 is

The tri-platform CI release: one `v*` tag now builds the PyInstaller bundle
independently on Linux, Windows and macOS runners and publishes a **GitHub
Release** carrying all three ZIPs, the Linux SBOM and a `SHA256SUMS` manifest —
downloadable without a GitHub login, which v1.1.0's CI-artifact distribution
required. Signing scaffolds now cover all three platforms and a release-level
manifest aggregates their reports into one `fully_signed` verdict (today:
`false`, everywhere). The engine is untouched — the application suite is
byte-for-byte the v1.1.0 suite and still passes identically.

## Verdicts

| Claim | Verdict |
|---|---|
| **Tri-platform release builds from one tag** | **Go — defined and contract-tested**: `publish-release.yml` is the only tag-triggered workflow, building on `ubuntu-latest`, `windows-latest` and `macos-latest`; the v1.2.0 tag push is its first live run |
| **GitHub Release automation** | **Go — defined and contract-tested**: release created only after all three builds pass and the five-asset set is verified (`tests/test_publish_release_workflow.py`) |
| **Windows distributable build** | **Go — script and gates, unexecuted**: `build-windows.ps1` mirrors the Linux gates; no Windows host exists here, so its first real execution is the tag's `windows-latest` job |
| **macOS distributable build** | **Go — arm64 only**: `build-macos.sh` with Darwin licence gates and an `--expect-arch` gate; plain directory, no `.app`/`.dmg`, no SBOM — both disclosed in the job log |
| **Signing scaffolds, all three platforms** | **Go — scaffold only**: unsigned paths and both wrong-host refusals exercised on this VM; signed branches verified by contract test, not run (no credentials exist) |
| **Release signing manifest** | **Go** — published at `release-signing-manifest.json`: `fully_signed: false`, `unsigned_platforms: ["linux"]`, `missing_reports: ["macos", "windows"]` |
| **Hardware certification path (C4)** | **Go — runbook only**: `docs/HARDWARE_CERTIFICATION.md` + `run-hardware-certification.sh`; C4's evidence is still server-loopback, unchanged |
| **Apple / Microsoft code signing** | **No-Go** (no Developer ID, no Authenticode certificate; nothing signs or notarizes) |
| **macOS Intel / universal2 asset** | **No-Go** (numpy, scipy, soundfile publish no universal2 wheels; asset is named `-arm64` so the gap is visible) |
| **Windows / macOS SBOM** | **No-Go** (`tools/generate_sbom.py` is Linux-scoped; only `audio-studio-sbom.json` for the Linux bundle ships) |

## Round H deliverables

| Deliverable | Where | Evidence |
|---|---|---|
| Unified release publishing | `.github/workflows/publish-release.yml` | Replaces `release-linux.yml`/`release-windows.yml`; three build jobs + a publish job that verifies `audio-studio-linux.zip`, `audio-studio-windows.zip`, `audio-studio-macos-arm64.zip`, `audio-studio-sbom.json`, `SHA256SUMS` before creating the release. Contract tests: `tests/test_publish_release_workflow.py`, expanded `tests/test_release_workflow.py` |
| Windows build script | `scripts/build-windows.ps1`, `packaging/WINDOWS.md` | GPL-exclusion, separate `Qt6Core.dll` (LGPL replaceability), bundled licence notices, `--version` smoke — asserted by contract test; never yet run on a Windows machine |
| macOS build script | `scripts/build-macos.sh`, `packaging/MACOS.md`, `.github/workflows/release-macos.yml` | Darwin licence gates plus `--expect-arch arm64`; the separate macOS lane runs on demand and on PRs touching the macOS build path — it has not run yet on this branch |
| Release asset preparation | `scripts/prepare-release-assets.sh` | Deterministic ZIP names via Python zipfile (identical on Linux/macOS/Git Bash), `SHA256SUMS` manifest; exercised for real on this VM by the contract suite |
| macOS + Windows signing scaffolds | `scripts/sign-macos-artifact.sh`, `scripts/sign-windows-artifact.ps1`, shared `scripts/lib/release-signing.sh` | `.agent_workspace/v1.2/release-signing-evidence.md`: unsigned paths run for real on this host, wrong-host credential refusals run for real, signed branches constrained by `tests/test_release_signing.py` (879 lines) |
| Release signing manifest | `scripts/release-signing-manifest.sh` | `.agent_workspace/v1.2/release-signing-manifest.json`: `fully_signed: false`; refuses wrong-platform reports and signature claims with no verified artifact |
| Hardware certification runbook | `docs/HARDWARE_CERTIFICATION.md`, `scripts/run-hardware-certification.sh` | Bench procedure for C4 on a class-compliant USB interface; `--require-physical` on both probes; contract-tested by `tests/test_hardware_certification_docs.py` |

## Honest gaps

These ship *disclosed*, not silently claimed:

1. **The release pipeline has never run end-to-end.** `publish-release.yml`
   triggers only on a `v*` tag, and no tag has been pushed since it landed.
   Its jobs, gates and asset set are contract-tested, but the v1.2.0 tag push
   is the first live execution — watch it, and expect the release to be
   withheld if any platform job fails (that is the designed behaviour).
2. **No Windows or macOS bundle has ever been built.** `build-windows.ps1`
   and `build-macos.sh` cannot run on this Linux VM; neither has produced an
   artifact anywhere yet. The Linux path is the only one proven with real
   artifacts (v1.1.0's AppImage/deb/bundle).
3. **Nothing is signed, on any platform.** No GPG release key, no Apple
   Developer ID, no Authenticode certificate. The manifest publishes
   `fully_signed: false` with Linux checksummed-but-unsigned and
   macOS/Windows having no signing run at all. Gatekeeper and SmartScreen
   will warn; macOS recipients must clear quarantine per `packaging/MACOS.md`.
4. **The macOS asset is arm64 only and is a bare directory** — no `.app`, no
   `.dmg`, no notarization, and no macOS SBOM. The Windows ZIP likewise ships
   without an SBOM; only the Linux bundle has one.
5. **AppImage and deb remain local-build artifacts.** The GitHub Release
   ships plain ZIPs of the one-directory bundles; the v1.1.0-era AppImage/deb
   wrappers are unchanged and still not produced from CI.
6. **C4 is still server-loopback evidence.** Round H added the runbook and
   automation for a physical USB interface measurement, not the measurement:
   no converter exists on this VM and the published latency evidence is
   unchanged.

## Test evidence

Run on this VM at this HEAD: application suite **1721 passed / 12 skipped**
(identical to v1.1.0 — Round H made no engine changes); repository-level suite
**435 passed / 0 failed**, which includes the SOTA acceptance checklist at
**31 passed / 0 xfailed** and the 144 release-engineering contract tests
(`test_release_workflow.py`, `test_publish_release_workflow.py`,
`test_release_signing.py`, `test_hardware_certification_docs.py`,
`test_linux_packaging_scripts.py`, `test_sbom.py`). Push CI on the Round H
head is green.

## Tag instruction

Tag **`v1.2.0`** on the merge commit after CI is green. The tag push is the
first end-to-end run of `publish-release.yml`: confirm the GitHub Release
appears with all five assets and that `sha256sum -c SHA256SUMS` verifies them.
If any platform build fails, no release is created — fix and re-tag rather
than hand-publishing a partial asset set.
