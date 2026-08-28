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
