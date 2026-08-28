Model slug: claude-fable-5
# Round 13 验收记录

> 状态：**模板 · 待集成回填**
> 集成线：`cursor/openmoji-integration-9f67` @ `e4d3998`（H6 证据刷新待下一 commit）
> 判定标准：`.agent_workspace/ROUND13-ACCEPTANCE.md`（探针 `scripts/check-round13.mjs` v1.1）
> 回填纪律：每格填**实测数据或命令输出**，禁止「应该可以」「理论上通过」；未达标项进 §3，不得静默遗漏。

## 0. 基线

| 门禁 | 基线实测（`9f7ae90` + 探针 v1.1） | 集成终验 |
|---|---|---|
| `check:round12` | 8/8 PASS | `[待填]` |
| `check:round13` | **1/8**（有意红灯，仅 H8 绿；v1.0 存在 H6 手搓 report / H7 BLOCKED 演练假绿风险，v1.1 已打回） | **5/8**（H3–H6、H8 绿；H1/H2/H7 待合入） |

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

| ID | 交付物 | 要回填什么（实测） | 判定 |
|---|---|---|---|
| H1 | ASR 放行 | 走了哪条腿（release / freeze）；files[] 清单；冻结集 recorded 条数与 RTF 基准摘要；harness `ROUND13_H1` 输出；smoke `ROUND13_H1_SMOKE` 路径 | `[P/F]` |
| H2 | OCR Android | android-sim OCR 段 steps + `ocr-device-a.log` 摘要；回流设计要点与责任 owner；harness `ROUND13_H2` 位置 | `[P/F]` |
| H3 | 绘本终局 | scene 页数/涉及本数（≥200）；`ROUND13_H3` 台账；BookPageScene 接线；旧页回归抽检 | `[P/F]` |
| H4 | 范唱批次 | 13/13 音频清单；≥3 范唱资产（文件、字节、来源）；`r13-songs-vocal-batch.md` 摘要；`ROUND13_H4` 位置 | `[P/F]` |
| H5 | lift 实验 | 准实验/对照口径与数值；报表/趋势导出路径；`ROUND13_H5_SMOKE` 交互路径 | `[P/F]` |
| H6 | Android 模拟 | report.json 摘要（simulated/routes/APK SHA）；四份日志路径；`r13-android-sim-record.md` 签核结论 | **P** |
| H7 | 商店实提 | 真实 Console/TestFlight 回执（日期/版本/SHA）；非 BLOCKED；双人复核签字 | `[P/F]` |
| H8 | R12 不退化 | `check:round12` 输出行（8/8）+ 退出码 | `[P/F]` |

## 2. 性能与质量量化

### 2.1 Android 模拟（H6/G6，`node scripts/android-sim.mjs`）

| App | smoke 路由 | 交互 | 问题数 | APK bytes | APK SHA256（report） | 日志 | 判定 |
|---|---:|---:|---:|---:|---|---|---|
| 识字 | 164 | 41 | 0 | 36,384,158 | `6c481966…7113e50` | `smoke-literacy.log` | **P** |
| 数学 | 20 | 36 | 0 | 4,299,368 | `14ec403b…3a3a1d34a` | `smoke-math.log` | **P** |

**签核**：report `simulated:true` = **true**；`r13-android-sim-record.md` 结论 = **PASS（simulated）**；**不等价真机**声明已读 = **[x]**

### 2.2 OCR Android + 回流（H2）

| 项 | 证据 | 判定 |
|---|---|---|
| android-sim OCR 段 | `report.json` → `ocr.pass` + `ocr-device-a.log` | `[P/F]` |
| 失败样本回流设计 | `r13-ocr-regression-loop.md` 摘要 | `[P/F]` |
| 真机复验（owner） | `[待填：PASS/SKIP owner: Android QA]` | `[P/F/SKIP]` |

### 2.3 体积与资产

| 指标 | 预算/基线 | 集成实测 | 判定 |
|---|---|---|---|
| 识字首屏 JS gzip | < 420 KB | `[待填]` | `[P/F]` |
| 数学首屏 JS gzip | < 250 KB | `[待填]` | `[P/F]` |
| scene 页（≥2 元素） | R12: 105 → R13: ≥200 | `[待填]` | `[P/F]` |
| 范唱批次净增 | ≥3 去重 ≥10KB | `[待填]` | `[P/F]` |
| literacy zip Δ | R12 值 + scene/范唱/ASR Δ | `[待填：总量与 Δ 来源]` | 记录 |
| math zip | R12 值 | `[待填]` | 记录 |

### 2.4 新增资产与依赖清单（H1/H4/H7）

| 资产/依赖 | 路径 | 大小 | 来源 | 许可证 | 进 THIRD_PARTY_NOTICES |
|---|---|---|---|---|---|
| ASR 冻结集 clips（recorded） | `[待填]` | `[待填]` | `[待填]` | `[待填]` | `[ ]` |
| 范唱批次 ×n | `[待填]` | `[待填]` | `[待填]` | `[待填]` | `[ ]` |
| 商店 AAB（release） | `[待填]` | `[待填]` | 本地构建 | — | N/A |

## 3. 未达标表

| 项 | 现状与差距 | 责任分支 | 计划 |
|---|---|---|---|
| `[待填：无则写「无」]` | | | |

## 4. 手动走查勾选（ROUND13-ACCEPTANCE §5）

- [ ] W1 ASR 放行复核（冻结集/RTF + available 降级边界）
- [ ] W2 OCR Android + 回流（sim 可复现 + 失败样本路径）
- [ ] W3 绘本终局观感（≥200 scene + 旧页不回归）
- [ ] W4 范唱批次（≥3 首 + 13/13 旋律 + 许可）
- [ ] W5 lift 实验可信（对照口径 + 只读度量）
- [ ] W6 模拟/商店（simulated 声明 + 真实 Console 回执非 BLOCKED）

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

- 集成 SHA：`[待填]`
- `check:round13`：`[待填：8/8 项通过，0 项失败]`
- **Round 13 体验终局：`[P/F]`**；R12 及更早回归不退化
