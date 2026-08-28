Model slug: claude-opus-5-thinking-high-fast
# Round 12 H2 · 拍照识字真机 / 模拟器 harness

> 脚本：`apps/literacy-app/scripts/test-ocr-device.mjs`
> 入口：`npm --prefix apps/literacy-app run test:ocr:device`（已挂进 `npm run test` 链，在 `check:bundle` 之后）
> 样张矩阵：`.agent_workspace/r12-ocr-matrix.md`
> VM 能力边界：`.agent_workspace/ANDROID-DEVICE-CHECKLIST.md` §1.1
> 证据落点：`.agent_workspace/evidence/r12/ocr-device-<serial>.json`
>
> **R14 起这份文档的 §3 / §4 / §5 已被 `.agent_workspace/r13-ocr-regression-loop.md` §5
> 取代**（`ROUND14_H2`）：B 段不再只是「把人和图送到位」，它自己接进设备的 WebView
> 逐张认字；退出码从两档变三档（SKIP 单独走 exit 2）；证据落点从
> `evidence/r12/ocr-device-<serial>.json` 改成 `evidence/r14/android/ocr-device-b.json`。
> 下面 §1 / §2 讲的 A 段口径与变异测试仍然有效，照读。
>
> 一句话：拍照识字这条链上最容易在真机上断的那几段，**都不在 OCR 引擎里**。
> `test-ocr-accuracy.mjs` 守「引擎认得出多少字」，这个脚本守「字还没进引擎之前
> 的那一路」——6 MB 的 wasm 取不取得到、断网之后还在不在、按下「拍一张」
> 会不会真的开摄像头、家长在安装页上看到几条权限。

## 1. 为什么不能只标一个 SKIP

这台 Cursor Cloud VM 没有 `adb`、没有 Android SDK、没连任何设备。最省事的写法
是整个脚本打一行 `SKIP: 需要真机`，交差。但那样等于把一整类问题推迟到
「有设备的那天」，而这些问题里的绝大多数**在源码和构建产物里当场就能查出来**：

- 引擎路径指没指到 CDN——查 `src/utils/ocr.js` 的字符串字面量就知道；
- worker 是不是 `blob:`——`blob:` 起的 worker 属于 opaque origin，不受 Service Worker
  控制，它内部的 `importScripts` 拿不到 OCR 缓存，**在线时一切正常、飞行模式下必挂**；
- SW 的 OCR 缓存名带不带版本前缀——带了的话每发一版孩子重下 5.5 MB，
  桌面上感觉不到，按流量计费的手机上感觉得到；
- 取图走的是 `<input type="file">` 还是 `getUserMedia`——后者在 Android WebView 里
  要 app 侧实现 `onPermissionRequest`，Capacitor 默认壳层没接，装到手机上就是黑屏；
- 清单里有没有多要一条 `CAMERA`。

这些全都是「桌面 Chrome 上绿、真机上红」的类型。等设备到位才发现它们，
成本是一轮出包 + 一轮走查；在 VM 上拦下来，成本是一次 `node`。

所以脚本分两段：**A 段在 VM 上照跑，红了就是红了；B 段要设备，VM 上 SKIP。**

## 2. A 段 · 前提条件（VM 上 34 项全绿）

| 组 | 项数 | 它挡住的真机故障 |
|---|---|---|
| A1 Capacitor 壳层 | 3 | `androidScheme` 不是 `https` → WebView 跑在不安全上下文，SW 根本注册不了，「下过一次就能离线认字」整条失效 |
| A2 引擎资源同源 | 6 | 路径回退到 jsDelivr 默认值 / `workerBlobURL: true` → 飞行模式下 404 或静默失败 |
| A3 引擎包落盘与预算 | 9 | 清单字节数与磁盘对不上 → 界面上「要下 5.5 MB」和实际等待时间长期不一致；合计超 6 MiB → 移动流量上的家长先付账 |
| A4 Service Worker | 4 | OCR 缓存撞上 `CACHE_PREFIX` → 每次发版重下；缓存了半截的 range 响应 → 离线时一直坏到用户清缓存 |
| A5 取图路径 | 4 | 走 `getUserMedia` → WebView 黑屏；相册 input 带了 `capture` → 安卓跳过相册直接开相机，「电脑上没摄像头也能选照片」这条路没了 |
| A6 权限 | 4 | 走 file input 却申请 `CAMERA` / `READ_MEDIA_IMAGES` → 商店审核和家长眼前凭空多两行吓人的话 |
| A7 待推样张 | 4 | 少于 8 张或缺 `tier` → 真机走查说不清覆盖了哪一类；单张 >512 KiB → `adb push` 变成一场等待 |
| A8 APK assets | SKIP | `cap copy` 漏掉 `public/ocr/` 不会报错，只会让装机后一按「开始认字」就 404 |

A3 和 A8 有条件 SKIP：`public/ocr/` 由 `prebuild` 上的 `gen-ocr-assets.mjs` 从
`node_modules` 复制、被 `.gitignore` 排除，`android/app/src/main/assets/` 要跑过
`sync:android:literacy` 才有。**全都不在 = 这个仓库还没构建过，不是退化**，
所以报 SKIP 并给出该跑哪条命令；但只要有一部分在，就按「构建产物不一致」判红。

### 2.1 这些断言不是打勾——变异测试

把三处代码故意改坏，A 段当场变红，改回来又全绿：

| 注入的改动 | 变红的断言 |
|---|---|
| `src/utils/ocr.js`：`workerBlobURL: false` → `true` | A2 workerBlobURL |
| `vite.config.js`：预缓存 `exclude` 去掉 `ocr` | A4 预缓存排除 |
| `AndroidManifest.xml`：加一条 `android.permission.CAMERA` | A6 没有多要 CAMERA |

三处一起注入：`31 通过 / 3 失败`，退出码 1；还原后 `34 通过 / 0 失败`，退出码 0。

## 3. B 段 · 真机执行（VM 上 SKIP，代码是实的）

这一段的代码不是占位：QA 拿一台机器插上 USB 就能跑，不需要谁先去把脚本补完。

| 项 | 脚本做什么 | 人做什么 |
|---|---|---|
| B1 设备指纹 | `getprop` 取型号 / Android 版本 / API，`wm size` `wm density` 取屏幕，`dumpsys package com.google.android.webview` 取 WebView 版本 | —— |
| B2 样张铺开 | `adb push` 十张真实样张到 `/sdcard/Download/hongen-ocr`，再广播一次 `MEDIA_SCANNER_SCAN_FILE`（不扫库相册选择器里看不见） | 用「相册选」照矩阵一格一格走，逐格记录 |
| B3 冷启 | `am force-stop` + `am start -n com.hongen.literacy/.MainActivity` | 走到「拍照识字」，记首次下引擎包耗时与峰值内存 |
| B4 离线 | —— | 开飞行模式重进 `/#/ocr`，确认引擎从 SW 缓存起来 |

B1 里唯一的硬断言是 **WebView ≥ Chromium 91**：wasm SIMD 从 91 起才有，低于这条线
`useOcr` 会走到「浏览器太旧」那条降级分支，跟引擎本身无关——不先量这一条，
后面所有识别失败都会被归错因。

跑完之后落一份 `evidence/r12/ocr-device-<serial>.json`，里面是设备指纹、
推了几张样张、装没装上、以及 A/B 两段的逐条结果。

### 3.1 真机走查表（B2，按矩阵逐格）

| 格 | 样张 | 期望文字 | VM 基线召回 | 真机实测 | 备注 |
|---|---|---|---|---|---|
| dappled · tilt-down · painted-board | `real-park-sign` | 爱护花草 | 4/4 | 待填 | |
| indoor-lamp · tilt-up · plastic-cone | `real-floor-cone` | 小心地滑 | 4/4 | 待填 | |
| daylight · frontal · concrete | `real-wall-stencil` | 小心地滑 | 3/4 | 待填 | 「滑」在 VM 上稳定丢，真机同样丢才算一致 |
| daylight · frontal · enamel-metal | `real-road-warning` | 小心行人 | 4/4 | 待填 | |
| spotlight · frontal · metal-letter | `real-toilet-sign` | 洗手间 | 3/3 | 待填 | |
| shade · frontal · chalkboard | `real-blackboard-press` | 中华书局 | 4/4 | 待填 | |
| overcast · tilt-up · reflective-sign | `real-road-slogan` | 爱护环境光荣 | 6/6 | 待填 | |
| overcast · frontal · acrylic-plaque | `real-town-plaque` | 社会治安 | 4/4 | 待填 | |
| backlit · oblique · lightbox-film | `real-shop-oblique` | 良欣美食 | 4/4 | 待填 | |
| hand-shadow · tilt-down · thermal-paper | `real-receipt-shadow` | 小碗米饭 | 4/4 | 待填 | |

同一份 PNG 在 VM 和真机上跑，结果**应当一致**——Tesseract 是确定性的，
不一致就说明真机侧有别的东西在起作用（WebView 版本、wasm SIMD 有没有生效、
`preprocess()` 的 canvas 实现差异），那才是这一段真正要抓的东西。

矩阵里明确缺的四格（夜间点阵屏、布幔横幅、>45° 极端侧拍、真实手写）
不在上表里——它们不是「找不到公开照片」，是**只能现拍**。QA 在设备上补拍时，
按 `.agent_workspace/r12-ocr-matrix.md` §6 的流程回填成正式样张。

## 4. SKIP 的口径

SKIP 不算通过，也不算失败。每条 SKIP 必须写清三件事：**是谁的**、**缺什么**、
**到位之后跑哪条命令**。「以后再说」不算 SKIP。

当前 VM 上的 5 条：

| SKIP | owner | 缺什么 |
|---|---|---|
| A8 APK assets 里的 OCR 包 | 本机 / Android Build | 没跑过 `npm run sync:android:literacy` |
| B1 设备指纹 | Android QA | VM 无 adb |
| B2 十张样张 push + 逐格走查 | Android QA | VM 无 adb |
| B3 冷启 → `/#/ocr` → 首包耗时与峰值内存 | Android QA | VM 无 adb |
| B4 飞行模式下引擎从 SW 缓存起来 | Android QA | VM 无 adb |

SKIP 会原样打进 stdout，也进 `--json` 的 `skips[]`，**谁都不能拿 exit 0 冒充
「真机验过了」**。要在真机 CI 上强制必须有设备，加 `--require-device`——
那时所有 SKIP 转成 FAIL，退出码 1。

## 5. 用法

```bash
# A 段全跑，B 段有设备才跑（VM 上：34 通过 / 0 失败 / 5 SKIP，exit 0）
npm --prefix apps/literacy-app run test:ocr:device

# 机读汇总：{ marker, device, passed, failed, skipped, evidence, passes[], fails[], skips[] }
node apps/literacy-app/scripts/test-ocr-device.mjs --json

# 真机 CI：没设备直接红
node apps/literacy-app/scripts/test-ocr-device.mjs --require-device
```

先跑一遍 `npm --prefix apps/literacy-app run build`（`prebuild` 会生成
`public/ocr/`），A3 那九条才是真断言而不是 SKIP。要连 A8 一起验，
再跑 `npm run sync:android:literacy`。

## 6. 脚本里那几条数字的来历

| 常量 | 值 | 为什么是这个数 |
|---|---|---|
| `PACK_BUDGET_MIB` | 6.0 | worker 0.11 + wasm 内核 3.72 + `chi_sim` 语言包 1.65 ≈ 5.5 MiB，留半兆余量。当前实测 5.47 MiB。松开这条线，最先付账的是低端机上用移动流量的家长 |
| `SAMPLE_MAX_KIB` / `SAMPLE_TOTAL_MAX_MIB` | 512 / 2 | 低端机上 `adb push` 十张图不能变成一场等待。当前实测合计 0.60 MiB |
| `MIN_SAMPLES` | 8 | 与 `test-ocr-accuracy.mjs` 的 `MIN_REAL_IMAGES` 对齐，当前 10 张 |
| WebView Chromium 下限 | 91 | wasm SIMD 的起始版本，低于它 `useOcr` 走降级分支 |
| `DEVICE_DIR` | `/sdcard/Download/hongen-ocr` | `adb push` 进得去且不需要 root；广播一次媒体扫描之后，系统选择器里就能挑到这十张 |
