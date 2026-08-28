# Round 18 Android simulation — BLOCKED

- Status: **BLOCKED**
- Command: `npm run android:sim`
- Executed command: `ANDROID_HOME=/home/ubuntu/android-sdk npm run android:sim`
- Commit under test: `a15e09c`
- Latest attempt: `2026-08-28T17:18:10.327Z`
- Latest exit code: `1`
- Full command output: `.agent_workspace/evidence/r18/android-sim-command.log`

The Android SDK and JDK were available. Both apps completed `assembleDebug`, and the generated APK
metadata matched the APK files on disk at the end of the latest run:

| APK | Bytes | SHA-256 |
| --- | ---: | --- |
| `apps/literacy-app/android/app/build/outputs/apk/debug/app-debug.apk` | 37551246 | `b53d8f0b70badc7b9a14feac0e62ad55f117798f858a9e180a0690712b3267a8` |
| `apps/math-app/android/app/build/outputs/apk/debug/app-debug.apk` | 4292264 | `9fd9bc0ed0d08064689fec921696a2561aec1116a80ee4811477202682c535ad` |

The overall harness did not pass:

1. On both complete attempts, literacy smoke reported one problem: the photo-recognition scenario did
   not observe an on-demand request for `chi_sim.traineddata.gz`.
2. On the latest attempt, math smoke could not create a Puppeteer profile because `mkdtemp` returned
   `ENOSPC` for `/tmp`. Disk space recovered afterward, but the completed run remains non-passing.

This is not an Android simulation PASS and does not replace physical-device QA. The generated Round 13
report was deliberately not promoted as passing evidence, and no stale report hash was substituted for
the APK hashes above.

## 复现

```bash
ANDROID_HOME=/home/ubuntu/android-sdk npm run android:sim
```
