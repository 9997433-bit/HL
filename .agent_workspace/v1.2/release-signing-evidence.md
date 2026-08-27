# Cross-platform release signing — what was run, and what it could not be

Evidence for the two scaffolds added in this round,
`scripts/sign-macos-artifact.sh` and `scripts/sign-windows-artifact.ps1`, and
for `scripts/release-signing-manifest.sh`, which collects their reports and the
Linux one into a single release-level document.

The headline is a negative result and it is the accurate one: **no artifact of
this project is signed on any platform.** There is no GPG release key, no Apple
Developer ID, and no Authenticode certificate here, and none of these scripts
can invent one. What this round adds is machinery that says so precisely, per
platform, in a form a release checklist can read.

## Environment

- Ubuntu 24.04 container, Linux 6.12.94+ x86_64, Python 3.12.3
- PowerShell 7.4.6 (installed to exercise the Windows scaffold; the GitHub
  `ubuntu-latest` runners carry `pwsh` as well, so the suite runs it in CI)
- `shellcheck` 0.9.0, `gpg` 2.4.4
- No macOS host, no Windows host, no `codesign`, no `signtool.exe`

## The unsigned path, run for real

Both scaffolds were run against stand-in files on this Linux host. That is the
only thing a Linux host can prove about them, and it is the branch that runs on
a release machine without credentials, so it is worth proving. These runs were
not published: the reports they wrote stayed in `/tmp`.

```
scripts/sign-macos-artifact.sh /tmp/sigdemo/AudioStudio-1.1.0.dmg
  ==> artifacts: 1
  ==> manifest:  /tmp/sigdemo/SHA256SUMS
  warning: no MACOS_SIGNING_IDENTITY configured: artifacts are checksummed but
           unsigned, and macOS will quarantine them for a downloader
  ==> not signed: (same reason, recorded in the report)
  exit 0

pwsh -File scripts/sign-windows-artifact.ps1 /tmp/sigdemo/audio-studio.exe
  ==> artifacts: 1
  WARNING: no WINDOWS_SIGNING_CERT configured: artifacts are checksummed but
           unsigned, and SmartScreen will warn a downloader about them
  ==> manifest:  /tmp/sigdemo/SHA256SUMS
  ==> not signed: (same reason, recorded in the report)
  exit 0
```

Each run wrote a report with `signed: false`, the reason, the SHA-256 and size
of every artifact, and a `scope` block denying all four signing claims
(`linux_gpg_detached_signature`, `macos_codesign`, `macos_notarization`,
`windows_authenticode`). `--require-signature` / `-RequireSignature` turns the
same state into exit 1 for a release job that must not ship unsigned.

## What the scaffolds refuse

A credential on a host that cannot use it is the case where a scaffold would
otherwise be tempted to write something reassuring:

```
MACOS_SIGNING_IDENTITY="Developer ID Application: Nobody (TEAM123456)" \
  scripts/sign-macos-artifact.sh dist/AudioStudio-1.1.0.dmg
  error: MACOS_SIGNING_IDENTITY is set but this host is Linux, not Darwin.
         codesign, xcrun and the keychain exist only on macOS; run this on the
         Mac that holds the Developer ID. Refusing to report a signature that
         was never made.
  exit 1, and no report is written

WINDOWS_SIGNING_CERT=0123456789abcdef0123456789abcdef01234567 \
  pwsh -File scripts/sign-windows-artifact.ps1 dist/audio-studio.exe
  Windows signing failed: a signing certificate is configured but this host is
  not Windows; signtool.exe exists only there. Refusing to report a signature
  that was never made.
  exit 1, and no report is written
```

The signed branches were not run, because running them here is impossible. They
are constrained instead by construction and by test: each sets its signed flag
only after the platform's own verifier has accepted the artifact —
`codesign --verify --strict` on macOS, `signtool verify /pa` followed by
`Get-AuthenticodeSignature` on Windows — and `tests/test_release_signing.py`
asserts that ordering in the sources. No test supplies a fake certificate,
because a test that mocked `codesign` into succeeding would assert a capability
this repository does not have.

## The release manifest

`scripts/release-signing-manifest.sh` with no arguments produced
`.agent_workspace/v1.2/release-signing-manifest.json` from the reports that
actually exist in this repository:

| platform | report | state |
| --- | --- | --- |
| linux | `.agent_workspace/v1.1/linux-signing-report.json` | present, `signed: false` — 2 artifacts checksummed, no `SIGNING_KEY` |
| macos | `.agent_workspace/v1.2/macos-signing-report.json` | absent — nothing signed macOS artifacts for this release |
| windows | `.agent_workspace/v1.2/windows-signing-report.json` | absent — nothing signed Windows artifacts for this release |

`fully_signed: false`, `signed_platforms: []`, `unsigned_platforms: ["linux"]`,
`missing_reports: ["macos", "windows"]`. The distinction is deliberate: Linux
artifacts were built and checksummed by a script that would have signed them
had there been a key, while the other two platforms produced no signing run at
all.

The aggregator also refuses two things rather than passing them on, both
exercised in the test suite: a report filed under the wrong platform (a macOS
report handed to `--linux-report`), and a report claiming `signed: true` while
none of its artifacts has `signature_verified: true`.

## What a release operator has to do

Nothing in this repository becomes signed by setting a variable. For a signed
release someone must:

1. Hold the credential — a GPG release key, a Developer ID Application
   certificate in a Mac's keychain, an Authenticode certificate (ideally on an
   HSM or a token, as the CA/Browser Forum baseline now requires).
2. Run each script on that platform's own machine: `sign-linux-artifact.sh` on
   Linux, `sign-macos-artifact.sh` on macOS, `sign-windows-artifact.ps1` on
   Windows.
3. Notarize the macOS artifact (`--notarize` with a stored
   `notarytool --keychain-profile`), or a downloader still sees a Gatekeeper
   block on first launch.
4. Re-run `scripts/release-signing-manifest.sh --require-all-signed` and get
   exit 0.

Until then, `fully_signed` is false and every published summary should say the
same thing this file does.
