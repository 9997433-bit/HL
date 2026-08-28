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
