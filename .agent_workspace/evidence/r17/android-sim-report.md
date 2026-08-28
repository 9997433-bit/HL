# Round 17 Android simulation report

- Command: `npm run android:sim`
- Commit under test: `36b4288`
- Timestamp: `2026-08-28T15:45:36.157Z`
- Exit code: `0`
- Harness: `android-sim-harness-v2`
- Android SDK: `/home/ubuntu/android-sdk`

The full Android simulation chain passed. This is VM WebView simulation plus Capacitor APK
construction; it does **not** replace Android physical-device QA sign-off.

## Step results

| Step | Result |
| --- | --- |
| `build:all` | PASS |
| `sync:android` | PASS |
| `check:android` | PASS |
| Literacy `assembleDebug` | PASS |
| Math `assembleDebug` | PASS |
| Literacy WebView smoke | PASS — 164 routes, 45 interactions, 0 problems |
| Math WebView smoke | PASS — 20 routes, 38 interactions, 0 problems |
| OCR device harness section A | PASS |

## APK evidence

- Literacy APK: `apps/literacy-app/android/app/build/outputs/apk/debug/app-debug.apk`
  - Bytes: `37534737`
  - SHA-256: `0ccc001f6e910f7b7f4b75960607f2cb6aabaaefea567345b1df67d39f4b58d3`
- Math APK: `apps/math-app/android/app/build/outputs/apk/debug/app-debug.apk`
  - Bytes: `4283557`
  - SHA-256: `e21ab280c97ddb2d79781e5f569b23a22d54e5e569de844d845538db1c977bce`

Both smoke suites observed the requested Android 13 Pixel 7 WebView user agent. The machine-readable
run output and per-step logs were generated under `.agent_workspace/evidence/r13/android-sim/`.
