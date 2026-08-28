Model slug: claude-fable-5-thinking-xhigh
# Round 13 H2 · 拍照识字失败样本回流设计（采集 → 标注 → 复现 → 闭环）

> 标记：`ROUND13_H2`
> 上游：`r12-ocr-matrix.md`（light × angle × paper 的 tier 坐标系）、`r12-ocr-device-harness.md`（真机 harness 口径）
> 执行面：`apps/literacy-app/scripts/test-ocr-device.mjs`（A 段由 `scripts/android-sim.mjs` 作为 `ocr-device-a` step 调用）
> 证据：`.agent_workspace/evidence/r13/android-sim/report.json` → `ocr.pass` + `ocr-device-a.log`
>
> 一句话：R12 把「什么样的照片会让识别断掉」画成了 tier 格子；这份设计回答下一个
> 问题——**真机上新冒出来的失败照片，怎么变成下一轮固定回归的格子**。没有回流，
> 样张矩阵就是一张拍完即冻结的快照，家长手里真实的失败分布会持续漂离它。

## 1. 回流四步

### 1.1 采集

- **触发面**：① 真机走查（B 段 push 到 `/sdcard/Download/hongen-ocr` 的样张 + QA 现场自拍）；② 内测轨道开通后的家长反馈渠道（当前 H7 BLOCKED，此面未开）。
- **采集物**：原始照片（压缩后 ≤512 KiB，对齐 `SAMPLE_MAX_KIB`）、期望字、实际识别输出、设备指纹（B1 段采的 model / Android 版本 / WebView 版本）。
- **入库位置**：`.agent_workspace/evidence/r13/ocr-failures/<日期>-<序号>.png` + 同名 `.json` 元数据。
- **红线**：照片不许带人脸、门牌号等可识别隐私；来源与授权字段沿用 `real-samples.json` 的 `source` 纪律，采不到授权的样张只记文字描述不入库。

### 1.2 标注

- 每张失败样本必须落 **tier 坐标**（light / angle / paper 各占一格），词表复用 `real-samples.json` 的 `matrix` 段；三根轴都套不进去的，先扩 matrix 词表、再入库——不许出现「无坐标样张」。
- 同时标注**失败类型**：全字错 / 部分字错 / 引擎超时 / 引擎起不来。后两类不是样张问题，回流到 A 段断言（资源路径、SW 缓存、包体预算）而不是样张库。

### 1.3 复现

- **离线复现**：`npm --prefix apps/literacy-app run test:ocr:accuracy` 把新样张喂进 Node 引擎，确认失败在引擎层可复现，并记下失败分数作为修复基线。
- **模拟复现**：`npm run android:sim` 的 `ocr-device-a` step 守链路前提（同源资源、SW 缓存、file input、权限清单）；真机复现由 owner: Android QA 带设备跑 `node scripts/test-ocr-device.mjs --require-device`。
- 引擎层复现不了、只在真机上失败的，保留设备指纹并标 `device-only`，进真机回归清单而不是 Node 基准——不许因为「本机是绿的」就关单。

### 1.4 闭环

- 修复验证后，失败样张从 `ocr-failures/` **晋升**为 `apps/literacy-app/scripts/fixtures/ocr/real-*.png` 常驻回归；晋升要过 R12 的两条去重线：内容 hash 不重、tier 格子不重。
- 每轮在验收记录里出一行帐：新增失败 n → 复现 n → 修复 n → 晋升 n。晋升即扩大 `test-ocr-accuracy` 的分母，防止「修一个丢一个」。
- 门禁挂钩：`check:round13` H2 同时查 android-sim OCR 段（`ocr.pass` + `ocr-device-a` step + 日志落盘）、本设计文档、以及 harness 源码中的 `ROUND13_H2` 输出标记（`test-ocr-device.mjs` 汇总行）——三腿缺一即红。

## 2. Owner 与时限

| 步骤 | owner | 时限口径 |
|---|---|---|
| 采集入库（真机走查渠道） | Android QA | 走查当日 |
| 采集入库（家长反馈渠道） | 产品运营（待 H7 解阻后指定） | 反馈后 3 个工作日 |
| tier 标注 + 失败类型 | 识字模块负责人 | 入库后下一次集成前 |
| 引擎/链路复现 | 识字模块负责人 | 同上 |
| 修复 + 晋升回归 | 识字模块负责人 | 下一轮硬门槛前 |

## 3. 当前状态（2026-08-28 实测）

- android-sim `ocr-device-a`：**PASS**（`report.json` → `ocr.pass = true`，日志 `ocr-device-a.log` 落盘）。
- 失败样本存量：**0**。真机走查与内测反馈两条采集面都还没开（与 H7 BLOCKED 同源：无 Play 内测轨道就没有外部家长的失败照片流入）。
- 因此本轮交付的是**机制**而非样张增量：格子、账本、owner、门禁挂钩已就位，采集面解阻当日即可启动第一批回流。

## 4. R14 回流第一批（`ROUND14_H2`）

R13 说「采集面没开就没有样张」，这句话漏了一条采集面：**我们自己的 App**。
`test-ocr-accuracy.mjs` 一直喂给引擎的是**原图**，可孩子在 App 里按下的那条链，
照片要先过 `utils/ocr.js` 的 `preprocess()`。这两个数从来没有分开量过——
分开一量，原图 40/41、App 侧只有 33/41。七个字丢在预处理里，
而原图基准一分都没掉，跑了四轮全绿。

四步照走，账记在 `apps/literacy-app/scripts/fixtures/ocr/regressions/queue.json`：

| 步 | 这一批的落点 |
|---|---|
| 采集 | 新增采集面 `app-webview-matrix`：`scripts/test-ocr-app-matrix.mjs` 在 headless Chrome 里跑真的 `preprocess()`，逐张对账（`simulated:true`，不等价真机） |
| 标注 | 五条单子都带 tier 坐标（复用 `real-samples.json` 的 matrix 词表）与失败类型，全是「部分字错」 |
| 复现 | 引擎层可复现：同一张图，原图 3/3、过预处理 2/3，差值就是预处理的账 |
| 闭环 | 4 条 `closed` + rootCause，1 条 `engine-limit`（喷漆「滑」，原图也认不出，留作回归底线） |

一行帐：**新增 5 → 复现 5 → 修复 4 → 晋升 0**（这五张本来就是常驻回归样张，
分母没变，变的是这条链上多了 App 侧那一段的量法）。

根因两条，都在 `src/utils/ocr.js`：

1. **短边补到 640 的放大**。理由曾经写着「太小的照片笔画会糊成一团」，实测反过来：
   双线性插值造不出笔画，只把边缘摊平，而引擎的行识别本来就要把每一行归一化，
   放大等于让它重采样两次。十张真实样张都是 300 px 以内的裁图，被放大 4 倍后
   App 侧 33/41；只降不升之后立刻回到 39/41。
2. **无条件的全局对比度拉伸**。跨度已经两百多的照片，拉伸增益只剩 1.1 倍，
   一个像素都改不动，却顺手把三通道压成灰度——喷漆「小心地滑」的「心」就丢在这里，
   字面和水泥墙一个亮度，分得开它们的只有颜色。跨度 ≥180 不再拉，40/41 到手，
   与原图基准持平。

门禁挂钩多两腿（`test-ocr-device.mjs` A9 / A10）：App 侧召回掉回 40 以下当场红，
关单不写 rootCause 当场红，队列里有本轮之前该修完却还挂着的单当场红。

## 5. R14-2：把「复现」那一步铺到设备上（`ROUND14_H2`）

§1.3 的复现有两个面：Node 引擎（原图）和 App 侧 WebView（过 `preprocess()`）。
R14-1 把第二个面量出来了，也就在同一天暴露出第三个面从来没被量过——**设备**。
这不是补充，是这条回流链上最后一段没有仪表的路：同一张 PNG，
在 headless Chrome 上认出 40/41，在一台真机的 WebView 里认出几个，
到今天为止没有任何人、任何脚本回答过。

### 5.1 为什么「让 QA 用眼睛看」不算复现

R12/R13 的 B 段做的是「把人和图送到位」：push 十张样张、拉起 App，
剩下的由 QA 在设备上逐格走查、回填表格。这套办法在别的检查项上够用，
在拍照识字上不够——设备上会掉字的三件事，人眼一件都看不出来：

- **WebView 的 canvas 缩放插值**。`preprocess()` 的 `drawImage` 缩放由 Skia 实现，
  桌面 Chrome 和 Android WebView 用的不是同一条路径；掉字体现为「少认出一个字」，
  而不是「画面看着不一样」。
- **wasm SIMD 有没有真的生效**。Chromium 91+ 才有；没生效时引擎不报错，
  只是慢下来、精度不变——除非有人拿秒表和字数一起对，否则看不见。
- **SW 缓存命不命中**。断网后引擎还起不起得来，界面上只表现为「转圈久一点」
  或者一句通用的失败话术，肉眼分不出是缓存没命中还是照片拍糊了。

所以 B 段自己把这条链走完了：`adb forward` 出 WebView 的 devtools socket，
用 CDP 的 `DOM.setFileInputFiles` 把设备上的样张塞进 App 真正的「相册选」input，
从 DOM 上逐张读回认出来的字（`.ocr__hit[data-char]` 与 `.ocr__miss`），
再开一次飞行模式复跑同一张。从 input 之后的每一步——`preprocess`、worker、wasm、
DOM 渲染——都是 App 真的那一套，没有替身。

| 步 | 脚本做什么 | 判红的线 |
|---|---|---|
| B1 | 采指纹（型号 / Android / API / WebView / 分辨率） | WebView < Chromium 91 |
| B2 | 十张样张推进 app 私有目录（脚本用）与 `/sdcard/Download/hongen-ocr`（人工用） | 推上去的张数对不上 |
| B3 | `am start -W` 冷启计时 + `dumpsys meminfo` 峰值 PSS | 拉不起 App |
| B4 | 逐张喂进「相册选」，读回认出来的字 | 设备侧召回 < 40/41，或首屏认对 < 9/10 |
| B5 | 开飞行模式，重载，同一张再认一遍 | 引擎清单取不到，或断网后认出的字变少 |

分区存储是这里唯一一处不显然的设计：脚本用的那十张必须推进
`/sdcard/Android/data/com.hongen.literacy/files/`，因为 Android 10 起 App
读不了别家的 `Download`。给人用的那份仍然推进 `Download` 并扫一遍媒体库，
两份互不替代。

### 5.2 SKIP 有自己的退出码

退出码从两档变三档：`0` 跑到位且全绿 / `1` 有断言红 / **`2` 没红但 B 段没跑成**。
`--require-device` 的口径也跟着改：老口径是「所有 SKIP 一律当 FAIL」，
于是「设备没插上」和「App 装错了」得到同一个 exit 1，而这两件事该找的人
完全不同。现在设备缺席走 2 并大声说一句这不是产品失败；设备在，剩下的 SKIP
才当 FAIL——那时候「跑不了」就是真的有东西坏了。

`android-sim.mjs` 的 `ocr-device-a` step 改用 `--section=a`：它问的本来就只是
「前提条件绿不绿」，不该因为 VM 上没设备而变红（R13 H2 的口径不变）。

**模拟器不算真机。** 检测到 emulator 时默认按「没有设备」处理；
`--allow-emulator` 才跑，且结论强制 `simulated:true`、落到
`ocr-device-b.emulator.json`——文件名和 `ocr-device-b.json` 从头到尾不重叠，
所以「拿模拟器点亮 H2」这件事在文件系统层面就做不到。
（本轮实测：这台 VM 装得上 SDK、`/dev/kvm` 也在，但 x86_64 模拟器的 guest
起不来，连预演都做不到。）

### 5.3 谁来守这份证据

`check-round14` 的 H2 只读 `evidence/r14/android/ocr-device-b.json` 的三个字段：
`pass` / `onDevice` / `simulated`。**正因为只有三个字段，伪造它只要三行。**
所以 harness 的 A12 段反过来校验这份证据自洽：`recall` 要等于逐张 `rows[].hit`
之和，`firstScreenCorrect` 要等于逐张为真的张数，`pass:true` 必须带着飞行模式
那一段且断网前后认出的字一样多。手搓一个绿灯，得把十张样张的分数一起编圆
（负向实测：只填三个字段的伪造文件，A12 当场四条红）。

页面里那几步（进 `/#/ocr`、喂图、等 `data-phase`、读回字）抽在
`scripts/lib/ocr-webview-drive.mjs`，B 段和 `--self-test-ui` 用的是同一份：
前者接真机的 WebView，后者接本机 headless Chrome。分成两份抄的话，
「本机自测是绿的」很快就说明不了任何事情。这条自测第一次跑就逮到一个真 bug——
清上一张结果去点的是「再来一张」，而按钮上写的是「换一张」，第二张会一直卡住；
改成盯 `data-phase` 的变化之后与文案无关。

### 5.4 当前状态：这条腿是红的，而且应该是红的

没有设备，所以 `evidence/r14/android/ocr-device-b.json` **不存在**，H2 照实红着。
本轮在这条腿上交付的是采集手段（B 段自动化 + schema + 自洽性门禁 + SKIP 台账），
不是一份绿灯。台账落在 `ocr-device-b.skip.json`：五条 SKIP、owner 全是 Android QA、
每条都写清设备到位跑哪条命令。

一行帐（R14-2）：**新增 0 → 复现 0 → 修复 0 → 晋升 0**；变的是这条链上
多了设备那一段的量法，以及它现在有一份跑得起来的脚本在等设备。

## 6. 引擎底线单的消化口径（`ROUND14_H2`）

`engine-limit` 是队列里唯一一种「不修也算处理完」的状态，所以它是这套账本上
最危险的一格：认不出的字往里一扔，队列就干净了。R14-1 往里放了第一条
（`R14-OCR-005`，喷漆「小心地滑」的「滑」），R14-2 把它消化成一条有出口的单子，
并把要求写死在 `test-ocr-device.mjs` 的 A11 段——四件套缺一即红：

| 字段 | 要回答的问题 | `R14-OCR-005` 的答案 |
|---|---|---|
| `engineMissed` | 到底丢哪个字 | 「滑」 |
| `rootCause` | 凭什么算引擎的边界，不是我们的问题 | 镂空模板把每一笔断成若干块，LSTM 的行识别把断口读成笔画间隙，稳定输出「海」 |
| `reopenIf` | 什么情况下重新排期 | 换语言包 / 换 tesseract 主版本 / 真机 B 段丢的字不止「滑」 / 同格再进一张镂空样张也丢字 |
| `reviewRound` | 最晚哪一轮必须有人再看一眼 | R16 |

还多守一条：底线单认的字必须真的出自那张样张的期望文字（A11 最后一条）。
不然 B 段扣分时会凭空多扣或少扣——底线一旦对不上样张，它就从「记账」变成了
「豁免权」。

**这条底线是三面共同的判定，不是某一面的借口**：原图进 Node 引擎 3/4、
App 侧 WebView 3/4、设备侧待 B 段回填。三面丢的必须是同一个字，
才叫引擎边界；哪一面多丢一个，这条单子当场作废，退回 `triaged` 重新排期。
B 段每一张都会把「这次允许丢哪个字」写进证据的 `engineLimitAllowed`，
所以「被豁免的字」在报告里是显式的一列，而不是一个没人记得的常量。
