# Round 17 Android device gate — BLOCKED

- Command: `npm run android:sim`
- Commit under test: `c326157`
- Run timestamp: `2026-08-28T15:26:37.366Z`
- Exit code: `1`
- Status: **BLOCKED**

The VM run completed its web simulation, but the isolated regression environment did not expose
`ANDROID_HOME`. The harness therefore reported `gradle: pass=false`, skipped both APK builds, and
returned exit code 1. No APK or physical-device approval is claimed.

Observed partial results:

- `build:all`, `sync:android`, and `check:android`: pass
- Literacy WebView smoke: 164 routes, 0 problems, pass
- Math WebView smoke: 20 routes, 0 problems, pass
- OCR device harness section A: pass
- Literacy and math APKs: not generated (`ANDROID_HOME is not set`)

## Reproduction

```bash
npm run android:sim
```

Before retrying the gate, configure a valid Android SDK path in the same shell and verify it:

```bash
export ANDROID_HOME=/path/to/android-sdk
test -d "$ANDROID_HOME"
npm run android:sim
```

This evidence satisfies the H7 honest-blocker path only; it is not an Android device sign-off.
