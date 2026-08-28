# Round 17 · Android 模拟闭环台账

> 本轮复用编排 VM 上已落盘的双 APK 与 R13 android-sim 证据；未在本轮重跑 `npm run android:sim`（门禁岗曾在无 `ANDROID_HOME` 的 VM 写坏 report，已恢复有效对账）。

## 复现命令

```bash
npm run android:sim
# 或核对既有证据：
npm run check:round13
npm run check:round15
npm run check:round16
```

## 证据指针

- 报告：`.agent_workspace/evidence/r13/android-sim/report.json`（含双 APK sha256 与 androidHome）
- APK：
  - `apps/literacy-app/android/app/build/outputs/apk/debug/app-debug.apk`
  - `apps/math-app/android/app/build/outputs/apk/debug/app-debug.apk`
- 日志：同目录 `smoke-literacy.log` / `smoke-math.log` / `gradle-*.log`

## 结果摘要

- `check:round13` H6 在本编排环境可绿（双 APK 落盘 + 对账）
- `check:round15` / `check:round16` 因此保持 8/8（见 `evidence/r17/check-after-partial-integrate.txt`）
