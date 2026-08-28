Model slug: claude-opus-4-6-20260815
# evidence/r14/android —— 真机层证据（ROUND14_H2 / H6）

> 这个目录只放**设备上跑出来的东西**。VM 上的 headless Chrome 属于
> `evidence/r14/ocr/`，Capacitor 模拟走查属于 `evidence/r13/android-sim/`（冻结面）。
> 三个目录分开，是因为把它们混成一句「真机验过了」是这套证据最容易出、
> 也最难在事后看出来的假。

## 1. 当前状态（2026-08-28）

| 文件 | 在不在 | 说明 |
|---|---|---|
| `ocr-device-b.json` | **不在** | 需要一台真机。没有设备就不写，更不会拿别的东西顶上 |
| `ocr-device-b.skip.json` | 在 | 上一次尝试的 SKIP 台账：谁缺什么、设备到位跑哪条命令 |
| `ocr-device-b.emulator.json` | 不在 | 只有 `--allow-emulator` 才会生成，且恒带 `simulated:true` |
| `ocr-device-b.schema.json` | 在 | 上面几份 JSON 的形状，`test-ocr-device.mjs` 的 A12 段照它校验 |
| `device-signoff.json` | 不在 | H6 的两台真机签核，归真机线（#5→#16） |

因此 **H2 的「真机 B 段」那条腿现在是红的，而且应该是红的**。
本轮在这条腿上交付的是可执行的采集手段（B 段自动化 + schema + 台账），
不是一份绿灯：`check-round14` 的 H2 会照实红着，直到有人把设备插上。

Cursor Cloud VM 上验证过的边界（2026-08-28 本轮实测）：Android SDK 与 `adb`
可以装上，`/dev/kvm` 也在，但 x86_64 模拟器的 guest 起不来（vCPU 不执行，
qemu 挂在 0% CPU）——这台 VM 没有可用的嵌套虚拟化。所以连「拿模拟器预演一遍」
都做不到，B 段在 VM 上只能是 SKIP。

## 2. `ocr-device-b.json` 怎么产生

```bash
# 出包机：把 dist 同步进壳层并出一个 debug 包（WebView 远程调试只有 debug 包才开）
npm run sync:android:literacy
(cd apps/literacy-app/android && ./gradlew assembleDebug)
adb install -r apps/literacy-app/android/app/build/outputs/apk/debug/app-debug.apk

# 出发之前先在本机预演一遍页面操作（不碰设备，不写这个目录）
node apps/literacy-app/scripts/test-ocr-device.mjs --section=a --self-test-ui

# 设备插上之后：A 段 + B 段全跑，证据落在这里
node apps/literacy-app/scripts/test-ocr-device.mjs --require-device
```

退出码：`0` 全绿；`1` 有断言红（产品/构建的问题）；`2` 没红但 B 段没跑成
（没设备、没装 App、接不进 WebView）。**exit 2 不是通过**——CI 上要和 exit 1
分开归类：一个是去插机器，一个是去改代码。

## 3. B 段在设备上做了什么

| 步 | 做什么 | 为什么这件事只能在设备上做 |
|---|---|---|
| B1 | `getprop` / `wm size` / `dumpsys package` 采指纹，断言 WebView ≥ Chromium 91 | wasm SIMD 从 91 起才有；低于它 `useOcr` 走「浏览器太旧」的降级分支，而这跟引擎本身无关 |
| B2 | 十张真实样张 `adb push` 到 app 私有的 external files 目录（脚本用）与 `/sdcard/Download/hongen-ocr`（人工走查用） | 分区存储下 App 读不了别家的 Download，所以脚本用的那份必须落在 app 自己的目录 |
| B3 | `am start -W` 冷启计时 + `dumpsys meminfo` 峰值 PSS | 冷启耗时和内存只有真机的调度和内存压力下才有意义 |
| B4 | `adb forward` 出 WebView 的 devtools socket，用 CDP 的 `DOM.setFileInputFiles` 逐张喂进 App 真正的「相册选」，从 DOM 读回认出来的字 | 掉不掉字取决于 WebView 的 canvas 缩放插值和 wasm SIMD 有没有生效——人眼看不出来，只能逐张对字数 |
| B5 | 开飞行模式，重载页面，同一张再认一遍 | 「下过一次就能离线认字」只有断网的真机能证；桌面上永远是绿的 |

脚本做不了的（相机取景、权限弹窗、TalkBack、连续 15 分钟温升）不在这份证据里，
它们在 `ANDROID-DEVICE-CHECKLIST.md` §3–§4，由 Android QA 逐项签。
B 段跑完会把这句话写进证据的 `notes`，免得「自动化跑过了」被读成「真机全验过了」。

## 4. 读这份 JSON 的两个人

`scripts/check-round14.mjs` 的 H2 只看三个字段：`pass === true`、`onDevice === true`、
`simulated !== true`。**正因为只看三个字段，伪造它只要三行**，所以同一个 harness 的
A12 段反过来校验这份证据自洽：`recall` 要等于逐张 `rows[].hit` 之和、
`firstScreenCorrect` 要等于逐张为真的张数、`pass:true` 必须带着飞行模式那一段，
且断网前后认出的字一样多。要手搓一个绿灯，得把十张样张的分数一起编圆。

另一个读者是下一轮想知道「上一次的绿灯凭什么」的人：`rows` 里每张有
tier 坐标、期望字、命中数、丢字、把握分和耗时；`engineLimit` 列出本次
按 `queue.json` 允许丢的字（当前只有喷漆样张的「滑」，复核轮次 R16）。
