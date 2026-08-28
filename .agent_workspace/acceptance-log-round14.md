# Round 14 验收记录

> 状态：**模板 · 待集成回填**
> 集成线：`cursor/openmoji-integration-9f67` @ `[待填 SHA]`
> 判定标准：`.agent_workspace/ROUND14-ACCEPTANCE.md`（探针 `scripts/check-round14.mjs` v1.0）

## 0. 基线

| 门禁 | R13 集成实测 | R14 集成终验 |
|---|---|---|
| `check:round13` | 7/8（H7 BLOCKED） | `[待填]` |
| `check:round14` | **1/8**（仅 H8 绿，预期） | `[待填：7/8 或 8/8]` |
| `check:round12` | 8/8 PASS | `[待填]` |
| 体验口径 ◐ 数 | 6（round13-hongen-audit） | `[待填：目标 0]` |

## 1. H1–H8 回填

| ID | 交付物 | 要回填什么（实测） | 判定 |
|---|---|---|---|
| H1 | ASR 体验 | available；recorded 条数；device RTF p95；`ROUND14_H1` smoke | `[P/F]` |
| H2 | OCR 体验 | App 召回；device B JSON；队列状态；`ROUND14_H2` | `[P/F]` |
| H3 | 绘本密度 | scene 页数（≥400）；`ROUND14_H3` | `[P/F]` |
| H4 | 范唱全库 | humanVocal **13/13**（`cursor/r14-literacy-vocal-full-9f67` 实测绿）；`r14-songs-vocal-full.md` 已改 13/13 口径 | **P**（待集成复测） |
| H5 | L1 朗读 | 资产数；`r14-tts-l1-batch.md`；`ROUND14_H5_SMOKE` | `[P/F]` |
| H6 | 真机签核 | device-signoff；GO 定案；真机设备矩阵 | `[P/F]` |
| H7 | 商店内测 | Console 回执；非 BLOCKED | `[P/F]` |
| H8 | 往轮不退化 | round12 8/8 + round13 ≥7/8 | `[P/F]` |

## 2. 体验 flip 台账

| 模块 | R13 ◐ 原因 | R14 实测 | flip |
|---|---|---|---|
| L-M9 | 录音回放 | `[待填]` | `[ ]` |
| L-M10 | 真机零签核 | `[待填]` | `[ ]` |
| L-M11 | 3/13 范唱 | 13/13 真人声源范唱随包；三份 Piper 旧资产已下架 | `[x]`（盲听签核仍 BLOCKED） |
| L-M5 | 209/1121 scene | `[待填]` | `[ ]` |
| L-M15/16 | simulated only | `[待填]` | `[ ]` |

## 3. 未达标表

| 项 | 差距 | 计划 |
|---|---|---|
| `[待填]` | | |

## 4. 手动走查 W1–W6

- [ ] W1 ASR 体验
- [ ] W2 OCR 体验
- [ ] W3 绘本观感
- [ ] W4 范唱全库
- [ ] W5 L1 朗读
- [ ] W6 真机/商店

## 5. 结论

- 集成 SHA：`[待填]`
- `check:round14`：`[待填]`
- 体验口径 ◐ 清零：`[是/否]`
