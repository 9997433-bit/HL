Model slug: claude-fable-5
# Round 12 验收记录

> 状态：**模板 · 待集成回填**
> 集成线：`cursor/openmoji-integration-9f67` @ `[待填 SHA]`
> 判定标准：`.agent_workspace/ROUND12-ACCEPTANCE.md`（探针 `scripts/check-round12.mjs` v1.1）
> 回填纪律：每格填**实测数据或命令输出**，禁止「应该可以」「理论上通过」；未达标项进 §3，不得静默遗漏。

## 0. 基线

| 门禁 | 基线实测（`7c2e6e7` + 探针 v1.1） | 集成终验 |
|---|---|---|
| `check:round11` | 8/8 PASS | `[待填]` |
| `check:round12` | 1/8（有意红灯，仅 H8 绿；v1.0 子信号 H1 gonogo/H7 feedback 假绿已在 v1.1 打回） | `[待填：必须 8/8 PASS]` |

### 0.1 v1.1 负向实测摘要（探针修订取证）

| 伪造手段 | v1.0 子信号 | v1.1 子信号 | 判定 |
|---|---|---|---|
| 仅 r11 Go/No-Go（含 available） | `gonogo=true` | `ship=false` | v1.1 堵洞 ✓ |
| R11 FEEDBACK-LOOP 无 R12 标记 | `feedbackRun=true` | `feedbackRun=false` | v1.1 堵洞 ✓ |
| `[其余见 ROUND12-ACCEPTANCE §4.1 负向表]` | | | |

## 1. H1–H8 回填（集成分支逐项落数）

> 「要回填什么」按下表第三列；探针口径见 ROUND12-ACCEPTANCE §2.1–§2.8。

| ID | 交付物 | 要回填什么（实测） | 判定 |
|---|---|---|---|
| H1 | ASR 落库 | files[] 清单（path/sha256/bytes/落盘体积）；整包 MiB；R12 ship Go/No-Go 结论与跑分；harness `ROUND12_H1` 输出；smoke `ROUND12_H1_SMOKE` 路径 | `[P/F]` |
| H2 | OCR 系统化 | 去重 real 张数与 tier 分布表；samples 授权 ≥8；真机 harness 命令/步骤；real tier 精度；`ROUND12_H2` 位置 | `[P/F]` |
| H3 | 绘本铺开 | scene 页数/涉及本数；高频单元列表；BookPageScene 接线；`ROUND12_H3` 位置；旧页回归抽检 | `[P/F]` |
| H4 | 儿歌全库 | 13/13 音频清单（文件、字节、来源、许可证）；范唱试点形态（资产或文档）；`ROUND12_H4` 位置；降级实测 | `[P/F]` |
| H5 | 推荐度量 | lift/采纳率对照数据与口径；34 节点开练覆盖证明；`ROUND12_H5_SMOKE` 交互路径；写回边界核验 | `[P/F]` |
| H6 | 真机/LH | evidence/r12 mobile LH 分数（识字/数学）；LH 版本；定案三选一结论与 `ROUND12_H6` 段落 | `[P/F]` |
| H7 | TTS/发布 | 走了哪条腿（tts / release+feedback）；试点链路或提交演练日期/SHA；R12 反馈运行摘要 | `[P/F]` |
| H8 | R11 不退化 | `check:round11` 输出行（8/8）+ 退出码 | `[P/F]` |

## 2. 性能与质量量化

### 2.1 Lighthouse mobile 复测（H6/G6）

| App | 档位 | P / A / BP | LH 版本 | 原始 JSON（evidence/r12/） | 判定 |
|---|---|---|---|---|---|
| 识字 | mobile | `[待填]`（阈值 ≥95/≥90/≥90） | `[待填]` | `[待填]` | `[P/F]` |
| 数学 | mobile | `[待填]`（阈值 ≥95/≥90/≥90） | `[待填]` | `[待填]` | `[P/F]` |
| 识字 | desktop | `[待填]`（记录 + 对比 R11） | `[待填]` | `[待填]` | 记录 |
| 数学 | desktop | `[待填]`（记录 + 对比 R11） | `[待填]` | `[待填]` | 记录 |

### 2.2 OCR 矩阵 tier 精度（`npm run test:ocr:accuracy` @ 集成 SHA）

| tier | 图数 | 精度（召回） | 阈值 | 判定 |
|---|---|---|---|---|
| 合成/印刷 tier（存量） | `[待填]` | `[待填]` | `[待填]` | `[P/F]` |
| real 真样张（R11 存量 6 + **R12 净增 ≥2**） | `[待填 ≥8]` | `[待填]` | `[待填：自设阈值]` | `[P/F]` |
| 真机 harness（adb/WebView） | `[待填]` | `[待填：PASS/SKIP]` | 步骤可复现 | `[P/F/SKIP]` |

### 2.3 体积

| 指标 | 预算/基线 | 集成实测 | 判定 |
|---|---|---|---|
| 识字首屏 JS gzip | < 420 KB | `[待填]` | `[P/F]` |
| 数学首屏 JS gzip | < 250 KB | `[待填]` | `[P/F]` |
| ASR 模型包（files[] 合计） | ≤ 60 MiB | `[待填]` | `[P/F]` |
| literacy zip | R11 值 + 模型/音频/scene Δ | `[待填：总量与 Δ 来源]` | 记录 |
| math zip | R11 值 | `[待填]` | 记录 |

### 2.4 新增资产与依赖清单（H1/H2/H4/H7）

| 资产/依赖 | 路径 | 大小 | 来源 | 许可证 | 进 THIRD_PARTY_NOTICES |
|---|---|---|---|---|---|
| ASR 模型 files[] | `[待填]` | `[待填]` | `[待填]` | `[待填]` | `[ ]` |
| OCR 实拍样张 ×n（净增 ≥2） | `[待填]` | `[待填]` | `[待填]` | `[待填]` | `[ ]` |
| 儿歌音频 ×n（净增至 13/13） | `[待填]` | `[待填]` | `[待填]` | `[待填]` | `[ ]` |
| 范唱/TTS 试点 | `[待填]` | `[待填]` | `[待填]` | `[待填]` | `[ ]` |

## 3. 未达标表

| 项 | 现状与差距 | 责任分支 | 计划 |
|---|---|---|---|
| `[待填：无则写「无」]` | | | |

## 4. 手动走查勾选（ROUND12-ACCEPTANCE §5）

- [ ] W1 ASR 落库复核（哈希一致 + 跑分数据 + 降级不退化）
- [ ] W2 OCR 矩阵复核（8 张真实 + tier 可信 + 真机 harness 可复现）
- [ ] W3 绘本铺开观感（≥60 页 scene + 旧页不回归 + 不卡）
- [ ] W4 儿歌全库 + 范唱（13 首可播 + 许可 + 降级保留）
- [ ] W5 推荐度量可信（34 节点 + 对照数据 + 仅用户写记录）
- [ ] W6 真机/TTS/发布走查（LH 与定案一致 + 试点/演练可执行 + R12 反馈运行）

## 5. 集成终验命令摘录

```bash
# 集成 SHA
git rev-parse HEAD

# 硬门槛（必须 8/8）
npm run check:round12

# 往轮不退化
npm run check:round11 && npm run check:round10

# 全链（G1/G4）
npm test && npm run test:round3

# 出包 + Android（G5）
npm run build:all && npm run sync:android && npm run check:android
```

### 结论

- 集成 SHA：`[待填]`
- `check:round12` 输出：`[待填：粘贴 8/8 全文]`
- **Round 12 全量落地**：`[待填：P/F（n/8）]`
