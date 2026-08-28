# Round 13 H2 · 拍照识字：Android 模拟与失败样本回流

> 脚本：`apps/literacy-app/scripts/test-ocr-device.mjs`（A 段静态断言 / B 段真机 / **C 段 Android WebView 模拟**）
> 队列：`apps/literacy-app/scripts/fixtures/ocr/regressions/queue.json`
> 证据：`.agent_workspace/evidence/r13/android-sim/`（`report.json` 的 `ocr` 段 + `ocr-section.json` + `ocr-device-a.log`）
> 上游口径：`.agent_workspace/r12-ocr-device-harness.md`（A/B 两段）、`.agent_workspace/r12-ocr-matrix.md`（十张样张的分格）
>
> 一句话：这一轮不是又加了几条断言，而是**第一次在 VM 上端到端量出了 App 真实的识别水平**——
> 量出来的数字比引擎跑分难看，两个只有装机才会暴露的问题当场现形。

## 1. 为什么要有 C 段

R12 交付的 A 段查源码和构建产物，B 段的代码是实的但要设备。中间空着一问，
而它恰好是最要紧的那一问：**这条链现在到底能认出多少字。**

`test-ocr-accuracy.mjs` 看起来已经回答了：二十张基准图、总召回 99%，
真实照片那一档 40/41。但它是在 Node 里拿 **原图** 喂引擎的，绕过了
App 自己的 `preprocess()`——也就是说，它测的是引擎，不是产品。

C 段把 `dist` 架在 `127.0.0.1` 上（localhost 属安全上下文，Service Worker
注册得了，与 Capacitor 把 dist 挂在 `https://localhost/` 是同一类环境），
用 Pixel 7 的 UA 和 412×915@2.625x 的视口起一个无头 Chrome，然后走界面自己的路：
进 `/#/ocr` → 把样张塞进「拍一张」那个 `<input type="file">` → 等 `data-phase`
变成 `done` → 从 DOM 上读认出来的字。**读 DOM 而不是读引擎返回值**，
因为孩子看到的就是 DOM：字进没进字库、「把握不大」那张卡亮没亮，都在这一层才成立。

C 段绿 **不代表可以跳过 B 段**。它不是真机：WebView 不是 Chrome，
没有真实相机、没有低端机的内存压力、没有真实的 System WebView 版本差异。
真机项仍然全部标着 `[SKIP owner: Android QA]`。

| 断言 | 它挡住的东西 |
|---|---|
| C1 Chromium ≥ 91 + Android UA 下 `/#/ocr` 起得来 | 低于 91 没有 wasm SIMD，测出来的是降级分支 |
| C2 Service Worker 注册并激活、识字包清单读得到 | A1 从 `androidScheme` 推出「SW 能注册」，这里是运行时实证 |
| C3 DOM 里「拍一张」带 `capture=environment`、「相册选」不带 | A5 查的是 `.vue` 源码，条件渲染出岔子时两者会不一样 |
| C4 十张真实样张逐张 ≥ App 侧基线，合计 ≥ 33/41 | 识别退化。**基线是 App 侧实测，不是引擎跑分** |
| C5 认不全的样张，界面都亮了降级卡 | 认错了却一声不吭，比认不出更糟——孩子会把错字当真 |
| C6 引擎三件套进了 `literacy-app-ocr-pack` 缓存 | A4 的静态断言在运行时的对照 |
| C7 飞行模式重进 `/#/ocr`，逐张重认与在线一致 | 「下过一次就能离线认字」这条承诺本身 |
| C8 整条链路没有未捕获异常 | Android UA 分支下的 JS 崩溃 |
| C9 认不全的样张在回流队列里都有记录 | 新的失败被静静吞掉 |
| C10 按 APK 的 assets 布局再认一遍 | 装机后语言包取不到（见 §2） |

跑一趟约 40 秒，挂在识字 App 的 `npm test` 链末尾（`test:ocr:webview`），
也由 `npm run android:sim` 调用并把结论写进 H6 的报告。

## 2. 第一次跑就抓到的两件事

### 2.1 语言包在 APK 里换了名字（已修）

出了 debug 包翻中央目录才看见：

| 位置 | 文件名 | 字节 |
|---|---|---|
| 仓库 / dist | `ocr/chi_sim.traineddata.gz` | 1730011 |
| APK 里 | `assets/public/ocr/chi_sim.traineddata` | 2469156 |

2469156 正好等于本机 `gunzip` 的结果——**Android Gradle 合并 assets 时把 `.gz`
解开并去掉了后缀**。而 `tesseract.js` 的 `gzip: true` 只会去取带 `.gz` 的那个名字。

于是：浏览器里一路顺，装到机器上一按「开始认字」就取不到语言包。
更糟的是它不报错——worker 停在「正在翻汉字词典」上再没动过，
孩子看到的是一条永远走不完的进度条（C10 变异测试实测：整整两分钟没有任何变化）。

改法在 `src/utils/ocr.js`：起 worker 之前用一个 `Range: bytes=0-0` 探哪个名字在，
在就用哪个。Web 照旧走 `.gz`，Android WebView 走解压后的名字，结论跟着
worker 缓存，第二张照片不再探。

守它的是 C10：按 Gradle 打包后的布局起第二个服务器（`.gz` 一律 404，
解压后的名字供 `gunzip` 出来的字节），换个端口就是换个源，SW 和 caches 都是干净的，
再让 App 完整认一遍。把探名去掉，C10 当场红。

这类问题正是 R12 那份 harness 文档说要抓、却抓不到的：`cap copy` 没漏文件，
`assets/` 目录里一切正常，**只有真包里不一样**。所以 A8 现在直接读 APK 的中央目录
（自己解析 zip，不依赖 `unzip`/`aapt`），逐个文件跟 `public/` 对字节。

### 2.2 引擎跑分 40/41，App 实测 33/41（已回流，未修）

同样十张真实照片，两条链路差出八个字：

| 样张 | 期望 | Node 引擎跑原图 | App 完整链路 | 把握 |
|---|---|---|---|---|
| real-park-sign | 爱护花草 | 4/4 conf 78 | 4/4 | 87 |
| real-floor-cone | 小心地滑 | 4/4 conf 86 | 4/4 | 75 |
| real-wall-stencil | 小心地滑 | 3/4 conf 70 | 3/4「小心地海」 | 32 |
| real-road-warning | 小心行人 | 4/4 conf 93 | 4/4 | 93 |
| **real-toilet-sign** | 洗手间 | **3/3 conf 84** | **2/3「六手间」** | 33 |
| **real-blackboard-press** | 中华书局 | **4/4 conf 76** | **2/4「站华书朋」** | 44 |
| real-road-slogan | 爱护环境光荣 | 6/6 conf 94 | 6/6 | 95 |
| **real-town-plaque** | 社会治安 | **4/4 conf 62** | **2/4「会安储痊」** | 33 |
| real-shop-oblique | 良欣美食 | 4/4 conf 92 | 4/4 | 89 |
| **real-receipt-shadow** | 小碗米饭 | **4/4 conf 64** | **2/4「小便米饮」** | 52 |
| 合计 | | **40/41** | **33/41** | |

定位过程（两步就够了，都在 VM 上）：

1. **不是放大。** 先把这几张按 App 里同样的 scale 预放大到 1280，再喂给 App——
   结果一字不差，连置信度都一样。二次重采样不是原因。
2. **是对比度拉伸。** 把 `preprocess()` 的产物（缩放 + 灰度 + 拉伸）存成 PNG，
   拿 **Node 引擎** 跑：逐字复现了 App 侧的「六手间」「站华书朋」「小便米饮」，
   置信度也一样落到 33 / 44 / 52。同一个引擎、同一份语言包，只是图先过了一遍我们自己的预处理。

也就是说：**掉的八个字是自家预处理造成的，跟 WebView、wasm、语言包都无关。**
`preprocess()` 对合成基准图是加分的（park-sign 78→87、road-slogan 94→95），
对真实实拍的小字是减分的——全局拉伸按整张图的最暗最亮定端点，
反光、手影、粉笔飞白都会被一起拉满，笔画反而糊进去。

**这一轮不修。** 改 `preprocess()` 会同时动到 `test-ocr-accuracy.mjs` 的阈值、
`CameraOcrView` 里那三条按曝光/锐度定的分岔线（`DIM_LUMA` / `DIM_SPAN` /
`BLUR_SHARPNESS` 都是拿现有预处理量出来的）以及低光/反色两类基准图的成绩，
是一次要单独验的改动。四条已经进队列（`r13-webview-*`，owner「识字 App」，
到期第 14 轮），带着根因、复现命令和实测数字。

顺带一提：这四张 App 都亮了「把握不大」（`data-trouble=shaky`，置信度 32–52），
所以孩子看到的不是一个自信的错字——C5 守的就是这一条。

## 3. 回流队列

### 3.1 为什么要有队列

「认错了」这件事，今天有三个地方会看见，没有一个地方会记住：跑分脚本打一行数字、
真机走查记在表格里、家长看见错字就换一张。下一轮换个人来，
只能重新发现一遍——上一轮定位到哪里、结论是什么、谁在跟，全丢了。

队列就是那个记住的地方。它不是 bug 列表的复制品，只收一类东西：
**一次具体的识别失败，连同它的现场**（哪张图、期望什么、实际认成什么、
界面亮了哪种提示、在哪条链路上、什么条件下拍的）。

### 3.2 一条记录长什么样

```json
{
  "id": "r13-webview-toilet-sign",
  "capturedAt": "2026-08-28",
  "source": "webview-sim",
  "sample": "real-toilet-sign",
  "tier": { "light": "spotlight", "angle": "frontal", "paper": "metal-letter" },
  "reason": "shaky",
  "expected": "洗手间",
  "got": "六手间",
  "missed": "洗",
  "status": "triaged",
  "owner": "识字 App",
  "dueRound": 14,
  "note": "……根因、对照数字……",
  "repro": "node scripts/test-ocr-device.mjs --webview-sim"
}
```

`reason` 用的是 **界面自己那套分岔**（`CameraOcrView` 的 `reason`）：
`dim` / `blurry` / `blank` / `shaky` / `error`，外加一个界面看不见的 `partial`——
置信度够高、字却是错的，那一类 UI 不会给任何提示，只能靠样张对账发现。
A9 会去 `CameraOcrView.vue` 里把分岔读出来跟队列词表对账：界面加一种新分岔而
队列不知道，回流上来的记录只能塞进错的格子，分类当场失真。

`tier` 沿用 `r12-ocr-matrix.md` 的 **光照 × 角度 × 纸质** 三根轴：
回流上来的失败落在哪一格，直接决定下一批样张该补哪一格。

### 3.3 状态机

```
      ┌── accepted-limit ──→ 阈值里留痕，跑分守着（引擎边界，不修）
new ──┤
      └── triaged ──┬── fixed ────→ 有断言守着（如 §2.1 的 C10）
                    └── promoted ─→ 固化成 fixtures/ocr/ 里的基准样张
```

| 状态 | 进入条件 | A9 要求 |
|---|---|---|
| `new` | 刚回流，还没人看过 | 有 owner、有 dueRound |
| `triaged` | 已定位到原因，等修 | 有 owner、有 dueRound |
| `promoted` | 已固化成基准样张 | `promotedTo` 指的图真的在 |
| `accepted-limit` | 确认是离线引擎的边界 | note 写清为什么（≥40 字），阈值里留痕 |
| `fixed` | 已修 | 有守着它的断言 |

### 3.4 三条回流入口

| 入口 | 谁产的 | 怎么进队列 |
|---|---|---|
| `webview-sim` | C 段每次跑 | 认不全的样张 C9 会核对；`--record-failures` 直接追加成 `new` |
| `device-qa` | 真机走查（B 段）逐格记录 | QA 按 §3.2 的字段手写，连同 `evidence/r*/` 的证据一起提 |
| `accuracy-bench` | 跑分脚本掉线的那张 | 改阈值的人必须同时留一条，说明是退化还是边界 |
| `parent-report` | 家长在应用里报「这个字不对」 | **通道还没有**，见 §5 |

### 3.5 让它转起来的那两条硬规矩

1. **C9：C 段认不全的样张，队列里必须有对应记录，否则红。**
   新的失败没法被静静吞掉——要么修，要么进队列认领。
2. **到期就红：`new` / `triaged` 的记录，`dueRound` 小于当前轮次即失败。**
   当前轮次不是写死的，取仓库里最大的那个 `check-round<N>.mjs`——
   下一轮的门禁文件一落地，逾期的记录当天自己变红，不靠谁记得。

「以后再说」不算回流：没人认领、没有到期轮次的记录，A9 一律判红。

## 4. 当前队列

| id | 样张 | 状态 | owner | 到期 | 一句话 |
|---|---|---|---|---|---|
| `r12-wall-stencil-hua` | real-wall-stencil | accepted-limit | 识字 App | — | 喷漆断笔字「滑」→「海」，两条链路一致，阈值 0.75 已留痕 |
| `r13-webview-toilet-sign` | real-toilet-sign | triaged | 识字 App | R14 | preprocess 拉伸；3/3 → 2/3 |
| `r13-webview-blackboard-press` | real-blackboard-press | triaged | 识字 App | R14 | 同上；4/4 → 2/4 |
| `r13-webview-town-plaque` | real-town-plaque | triaged | 识字 App | R14 | 同上；4/4 → 2/4 |
| `r13-webview-receipt-shadow` | real-receipt-shadow | triaged | 识字 App | R14 | 同上；4/4 → 2/4 |

§2.1 那个语言包改名的问题没有进队列——它当轮就修了，且有 C10 守着，
按 §3.3 直接算 `fixed`，留在提交记录和这份文档里比留在待办队列里更合适。

## 5. 还缺的一块：家长侧上报

队列现在只有机器产的记录和 QA 手写的记录，缺最重要的那一路：**孩子真的拍了一张、
认错了**。界面已经具备条件——`CameraOcrView` 的 `data-trouble` 就是分类结果，
`result.photo` 里有曝光和锐度——差的是一条「这个字不对」的按钮和落盘格式。

没有做，是因为它牵扯到照片的处置：孩子拍的照片不能上传（「照片不会传到任何地方」
是这一页写在最上面的承诺），能带走的只有 `{ reason, luma, span, sharpness,
confidence, 认出的字, 设备指纹 }` 这些数字，加上家长**主动**选择导出的那一张图。
这是一次要单独设计的改动（家长中心里的导出入口 + 一份不含图的 JSON），
放在 R14 讨论。在那之前，`parent-report` 这个来源在词表里占着位子，是空的。

## 6. 用法

```bash
# A 段 + A9 回流队列体检（0.3 秒，不起浏览器）
npm --prefix apps/literacy-app run test:ocr:device

# 加跑 C 段 Android WebView 模拟（约 40 秒，要 dist 和 Chrome）
npm --prefix apps/literacy-app run test:ocr:webview

# 结论写进 android-sim 报告的 ocr 段（H6 的 android-sim.mjs 会这么调）
node apps/literacy-app/scripts/test-ocr-device.mjs \
  --sim-report=.agent_workspace/evidence/r13/android-sim/report.json

# 新失败自动追加进回流队列（状态 new，等人认领）
node apps/literacy-app/scripts/test-ocr-device.mjs --webview-sim --record-failures

# 真机 CI：SKIP 一律当失败
node apps/literacy-app/scripts/test-ocr-device.mjs --require-device
```

## 7. 变异测试

不改代码只改断言的脚本，谁都能写绿。这几条是把代码改坏之后当场变红的：

| 注入的改动 | 变红的断言 |
|---|---|
| `utils/ocr.js`：`gzip: await langIsGzipped()` → `gzip: true` | C10（卡在「正在翻汉字词典」，一分钟没结果） |
| `WEBVIEW_BASELINE` 里任一张的 `hit` 调高一格 | 该张的 C4 |
| 从队列里删掉一条 `r13-webview-*` | C9（认不全的样张在队列里没记录） |
| 队列里任一条 `triaged` 的 `dueRound` 改成 12 | A9（已过期：说好第 12 轮处理，现在是第 13 轮） |
| `CameraOcrView` 加一种新的 `reason` 而队列词表不动 | A9（界面有而队列没有的 reason） |

## 8. 这一段证明了什么、没证明什么

**证明了**：在 VM 上，Android UA + 移动视口 + localhost 安全上下文下，
拍照识字这条链完整跑得通——SW 注册、引擎三件套进缓存、十张真实样张认出 33/41、
断网重认逐张一致、按 APK 的 assets 布局照样认得出。

**没证明**：真机上的表现。相机取图、低端机内存、真实 System WebView 版本、
首次下引擎包的耗时——这四件事只有设备上才有，仍然全部挂在
`[SKIP owner: Android QA]` 下面，`--require-device` 会把它们转成红灯。
`report.json` 的 `ocr` 段里 `simulated: true` 一直在，**不得当作真机签核**。
