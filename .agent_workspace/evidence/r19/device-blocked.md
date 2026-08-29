# Round 19 Android simulation — BLOCKED

- Status: **BLOCKED**
- Command: `npm run android:sim`
- Executed command: `ANDROID_HOME=/home/ubuntu/android-sdk npm run android:sim`
- Gate branch: `cursor/r19-regression-gate-9f67`
- Attempt commit: `2624e06`（编排启动 tip；随后已 fast-forward 到 `0ec04b7`）
- Latest attempt: `2026-08-29T01:04:09.526Z`
- Latest exit code: `1`
- Full command output / report snapshot: `.agent_workspace/evidence/r19/android-sim-command.log`

Android SDK 与 JDK 可用。双 App `assembleDebug` 成功，同次盘上 APK 与 harness 报告一致：

| APK | Bytes | SHA-256 |
| --- | ---: | --- |
| `apps/literacy-app/android/app/build/outputs/apk/debug/app-debug.apk` | 37615274 | `6269d6f72d13c9ecb81c64656e7d7615efc63ca8e39c430590eb9f6db7967499` |
| `apps/math-app/android/app/build/outputs/apk/debug/app-debug.apk` | 4297730 | `5f29c871f40802811199d2cf52e5501f45472bdfdeee60db0ba1f3745a7c87d5` |

全链路未绿：

1. literacy WebView smoke：`拍照识字` 场景未观察到按需请求 `chi_sim.traineddata.gz`（164 路由 / 45 交互 / 1 问题）。
2. math smoke 与 OCR A 段通过；WebView UA 注入核验通过。
3. 整体 harness `process.exit(1)`，不得当作本轮 Android 模拟 PASS，也不等价真机签核。

未把 r13/r17/r18 旧绿报告冒充为本轮 PASS；往轮 `check:round18` 所需双 APK 由门禁岗按已入库 `report.json` 哈希在本地对齐后复验（见 `evidence/r19/check-round18.txt`）。

## 复现

```bash
ANDROID_HOME=/home/ubuntu/android-sdk npm run android:sim
```
