Model slug: claude-fable-5
# Round 13 验收记录

> 状态：**已回填（2026-08-28 实测）**
> 集成线：`cursor/openmoji-integration-9f67`；本轮实测 commit `7d8ac7a`（evidence report.json 的 commit 字段同值）
> 判定标准：`.agent_workspace/ROUND13-ACCEPTANCE.md`（探针 `scripts/check-round13.mjs` v1.1）
> 回填纪律：每格填**实测数据或命令输出**，禁止「应该可以」「理论上通过」；未达标项进 §3，不得静默遗漏。

## 0. 基线

| 门禁 | 基线实测（`9f7ae90` + 探针 v1.1） | 集成终验 |
|---|---|---|
| `check:round12` | 8/8 PASS | **8/8 PASS**（2026-08-28，exit 0） |
| `check:round13` | **1/8**（有意红灯，仅 H8 绿；v1.0 存在 H6 手搓 report / H7 BLOCKED 演练假绿风险，v1.1 已打回） | **7/8**（H1–H6、H8 绿；仅 H7 红 = BLOCKED 预期，见 §3） |

### 0.1 v1.1 负向实测摘要（探针修订取证）

| 伪造手段 | v1.0 子信号 | v1.1 子信号 | 判定 |
|---|---|---|---|
| 手搓 android-sim `report.json` 无 APK/日志 | H6 可能绿 | `sim=false` | v1.1 堵洞 ✓ |
| BLOCKED 商店 dry-run + `ROUND13_H7` | H7 可能绿 | `submit=false` | v1.1 堵洞 ✓ |
| `progress.js` 写 lift 字段代实验 md | H5 `exp=true` | `exp=false` | v1.1 堵洞 ✓ |
| freeze md 写「≥50」无 JSON clips | H1 `freeze=true` | `freeze=false` | v1.1 堵洞 ✓ |
| `[其余见 ROUND13-ACCEPTANCE §4.1 负向表]` | | | |

## 1. H1–H8 回填（集成分支逐项落数）

> 「要回填什么」按下表第三列；探针口径见 ROUND13-ACCEPTANCE §2.1–§2.8。

| ID | 交付物 | 实测回填（2026-08-28 @ `7d8ac7a`） | 判定 |
|---|---|---|---|
| H1 | ASR 放行 | freeze 腿：files[] 落盘校验 37,022,120 B；冻结集骨架 56 条（≥50）；`r13-asr-freeze-set.md` + RTF 基准（`r13-asr-android-rtf-baseline.md`）；harness `test-asr-eval-set.mjs` 带 `ROUND13_H1`；smoke `ROUND13_H1_SMOKE` 在 literacy smoke.mjs | **P** |
| H2 | OCR Android | `report.json` → `ocr.pass=true` + step `ocr-device-a:true`，`ocr-device-a.log` 3,667 B 含 `ROUND13_H2` 输出行；回流设计 `r13-ocr-regression-loop.md`（采集→标注→复现→闭环 + owner 表）；harness 标记在 `test-ocr-device.mjs` 汇总输出行 | **P** |
| H3 | 绘本终局 | 探针实测 209 页 scene（≥200）；`ROUND13_H3` 台账 `r13-literacy-books-final.md`；BookPageScene 接线由探针渲染腿核验 | **P** |
| H4 | 范唱批次 | 探针实测 13/13 音频 + 范唱 3 首（≥3，去重 ≥10KB）；台账 `r13-songs-vocal-batch.md` 带 `ROUND13_H4` | **P** |
| H5 | lift 实验 | `r13-reco-lift-experiment.md` 准实验/对照口径；`ROUND13_H5_SMOKE` 在 math smoke.mjs | **P** |
| H6 | Android 模拟 | report `simulated:true`，8/8 steps PASS；双 APK 落盘且 SHA 与磁盘对账一致（见 §2.1）；四份日志齐；`r13-android-sim-record.md` 结论 PASS（simulated） | **P** |
| H7 | 商店实提 | **BLOCKED**：无 Play Console 账号/上传密钥，无真实回执；记录 `r13-store-submission-record.md` 保持诚实红灯，不伪造 SUBMITTED（解阻路径见 ORCHESTRATION-COMPLIANCE-AUDIT §3） | **F（预期）** |
| H8 | R12 不退化 | `check:round12`：「8/8 项通过，0 项失败」，exit 0 | **P** |

## 2. 性能与质量量化

### 2.1 Android 模拟（H6/G6，`node scripts/android-sim.mjs`）

| App | smoke 路由 | 交互 | 问题数 | APK bytes | APK SHA256（report，与磁盘对账一致） | 日志 | 判定 |
|---|---:|---:|---:|---:|---|---|---|
| 识字 | 164 | 42 | 0 | 36,222,498 | `4923affc…b80e95533` | `smoke-literacy.log` | **P** |
| 数学 | 20 | 36 | 0 | 4,261,568 | `7fc33e5a…3a8fbd64` | `smoke-math.log` | **P** |

> 2026-08-28 于本集成 VM 全链路重跑（`SIM_EXIT=0`）：JDK 17 + Android SDK 34（platform-34 / build-tools 34.0.0）。
> OCR 合入后 report 与 APK 已刷新，旧表（41 交互 / `6c481966…`）作废。

**签核**：report `simulated:true` = **true**；`r13-android-sim-record.md` 结论 = **PASS（simulated）**；**不等价真机**声明已读 = **[x]**

### 2.2 OCR Android + 回流（H2）

| 项 | 证据 | 判定 |
|---|---|---|
| android-sim OCR 段 | `report.json` → `ocr.pass = true`，step `ocr-device-a` PASS，`ocr-device-a.log` 3,667 B（37 项断言全绿 / 0 失败，B 段 4 项 SKIP owner: Android QA） | **P** |
| 失败样本回流设计 | `r13-ocr-regression-loop.md`：采集（真机走查/内测反馈）→ tier 标注 → 引擎/模拟/真机三层复现 → 晋升闭环账本 + owner/时限表 | **P** |
| 真机复验（owner） | SKIP owner: Android QA（VM 无 adb/设备；设备到位跑 `node scripts/test-ocr-device.mjs --require-device`） | **SKIP** |

### 2.3 体积与资产

| 指标 | 预算/基线 | 集成实测 | 判定 |
|---|---|---|---|
| 识字首屏 JS gzip | < 420 KB | **324 KB**（`check:bundle`：4 项通过，2026-08-28 实测） | **P** |
| 数学首屏 JS gzip | < 250 KB | 未单测（math npm test 不在本轮范围；无 math 侧改动） | 记录 |
| scene 页（≥2 元素） | R12: 105 → R13: ≥200 | **209**（check:round13 H3 实测） | **P** |
| 范唱批次净增 | ≥3 去重 ≥10KB | **3**（check:round13 H4 实测，13/13 旋律不退化） | **P** |
| literacy zip Δ | R12 值 + scene/范唱/ASR Δ | 30,910,895 B（≈29.5 MiB；主增量 = ASR 冻结包 37 MB 之部分 + 范唱/绘本资产） | 记录 |
| math zip | R12 值 | 478,547 B（≈467 KiB） | 记录 |

### 2.4 新增资产与依赖清单（H1/H4/H7）

| 资产/依赖 | 路径 | 大小 | 来源 | 许可证 | 进 THIRD_PARTY_NOTICES |
|---|---|---|---|---|---|
| ASR 冻结集 clips（recorded） | `[待填]` | `[待填]` | `[待填]` | `[待填]` | `[ ]` |
| 范唱批次 ×n | `[待填]` | `[待填]` | `[待填]` | `[待填]` | `[ ]` |
| 商店 AAB（release） | `[待填]` | `[待填]` | 本地构建 | — | N/A |

## 3. 未达标表

| 项 | 现状与差距 | 责任分支 | 计划 |
|---|---|---|---|
| H7 商店实提 | **BLOCKED**：无 Play Console 账号/上传密钥/Play App Signing；v1.1 探针拒收 dry-run，红灯为诚实信号 | `cursor/r13-store-submit-9f67`（记录已合入） | 解阻两路见 `ORCHESTRATION-COMPLIANCE-AUDIT.md` §3：用户供给凭据真提交，或签字接受 7/8 终态；**禁止伪造 SUBMITTED** |
| 真机复验 | VM 无 adb/设备，OCR B 段与整机 QA 均 SKIP | — | owner: Android QA，设备到位跑 `test-ocr-device.mjs --require-device` |

## 4. 手动走查勾选（ROUND13-ACCEPTANCE §5）

- [ ] W1 ASR 放行复核（冻结集/RTF + available 降级边界）— 探针 H1 绿；人工复核待 owner
- [x] W2 OCR Android + 回流（sim 可复现 + 失败样本路径）— 2026-08-28 本 VM 全链路重跑复现（`ocr-device-a` 37 断言绿），回流路径 `r13-ocr-regression-loop.md` §1.1
- [ ] W3 绘本终局观感（≥200 scene + 旧页不回归）— 探针 H3 绿（209 页）；观感走查待 owner
- [ ] W4 范唱批次（≥3 首 + 13/13 旋律 + 许可）— 探针 H4 绿；听感走查待 owner
- [ ] W5 lift 实验可信（对照口径 + 只读度量）— 探针 H5 绿；口径复核待 owner
- [ ] W6 模拟/商店（simulated 声明 + 真实 Console 回执非 BLOCKED）— simulated 声明已核；**Console 回执缺失（H7 BLOCKED），本项保持未勾**

## 5. 集成终验命令摘录

```bash
# 集成 SHA
git rev-parse HEAD

# 硬门槛（必须 8/8）
npm run check:round13

# 往轮不退化
npm run check:round12 && npm run check:round11

# 全链（G1/G4）
npm test && npm run test:round3

# 出包 + Android（G5）
npm run build:all && npm run sync:android && npm run check:android

# Android 模拟（G6）
node scripts/android-sim.mjs
```

### 结论

- 集成 SHA：证据测量点 `7d8ac7a`（report.json `commit` 字段同值；台账与证据刷新在其后续 commit 落盘）
- `check:round13`：**7/8 项通过，1 项失败**（唯一红灯 H7 = BLOCKED，预期红，见 §3）
- `check:round12`：**8/8 项通过**，exit 0（H8 腿同口径复核）
- 识字 app `npm test`：全量通过（srs/speech/asr×2/ocr×2/data/build/bundle/smoke；期间修复 NOTICES 缺 4 张样张署名的真实红灯）
- **Round 13 体验终局：P（工程面 7/8 + H7 阻断归档）**；R12 及更早回归不退化。
  8/8 需 H7 解阻（用户供给 Play Console 凭据真提交，或签字接受 7/8 终态）——见 `ORCHESTRATION-COMPLIANCE-AUDIT.md` §3。
