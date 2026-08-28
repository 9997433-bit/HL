# Round 14 验收标准 · 洪恩体验对齐（E1–E5）

> 版本：Round 14 v1.0（2026-08-28）
> 依据：`.agent_workspace/ROUND14-BRIEF.md` + `round13-hongen-audit.md` §5.1 R14 尾巴
> 配套：`.agent_workspace/acceptance-log-round14.md`、`scripts/check-round14.mjs`（H1–H8，固定 8 结果）
> 判定原则：**体验 flip** 须孩子/家长可感知；真机 evidence 与 `simulated:true` 分目录，**禁止冒充**。

## 0. 轮次门禁 G1–G7

| # | 门禁 | 验证方式 | PASS 标准 |
|---|---|---|---|
| G1 | 全量单测 | `npm test` | 全绿 |
| G2 | Round 14 硬门槛 | `npm run check:round14` | **8/8**（基线 R13 集成后预期 **1/8**，仅 H8 绿） |
| G3 | Round 13 不退化 | `npm run check:round13` | **≥7/8**（H7 BLOCKED 可接受） |
| G4 | Round 12 不退化 | `npm run check:round12` | **8/8** |
| G5 | 出包 + Android | `build:all` + `sync:android` + `check:android` | 26/26 |
| G6 | 真机签核（H6） | 真机矩阵脚本 + `evidence/r14/android/` | `device-signoff.json` onDevice=true |
| G7 | 体验走查 | W1–W6 人工勾选 | 6/6 + owner 签字 |

## 1. 八项硬门槛（H1–H8）

| ID | 交付物 | PASS 标准 | 体验 flip |
|---|---|---|---|
| H1 | ASR 体验 | `available:true` + recorded≥300 + GO 文档 + 真机 RTF p95≤0.5 + `ROUND14_H1` + smoke | L-M9 ✅ |
| H2 | OCR 体验 | App≥40/41 + 真机 B 段 JSON + 队列无逾期 + `ROUND14_H2` | L-M10 ✅ |
| H3 | 绘本密度 | scene≥400 + 渲染 + `ROUND14_H3` | L-M5 大幅收窄 |
| H4 | 范唱全库 | 13/13 humanStudio 范唱 + `r14-songs-vocal-full.md` + `ROUND14_H4` | L-M11 ✅ |
| H5 | L1 朗读 | `r14-tts-l1-batch.md` + ≥20 资产 + `ROUND14_H5_SMOKE` | X1 收窄 |
| H6 | 真机签核 | `evidence/r14/android/device-signoff.json` + GO 定案 + `ROUND14_H6` | L-M15/M-M16 ✅ |
| H7 | 商店内测 | 真实 Console 回执 + `ROUND14_H7` | 发布 ✅ |
| H8 | 往轮不退化 | round12 8/8 + round13 ≥7/8 | 链式兜底 |

## 2. 体验 flip 判定表（终审用）

| 模块 | R13 后 | R14 目标 | 终验方法 |
|---|---|---|---|
| L-M9 | ◐ 录音回放 | ✅ 实时 ASR 评分 | 儿童跟读 3 首诗盲测 |
| L-M10 | ◐ VM sim | ✅ 真机拍照认字 | 10 张日常场景 |
| L-M11 | ◐ 3/13 范唱 | ✅ 13/13 真人 | 盲听家长问卷 |
| L-M5 | ◐ 209/1121 | ◐→✅ 高频全覆 | 随机翻 10 页 |
| X1 | ◐ 1 poem | ◐ L1 真人/TTS | L1 单元点读 |
| E5 | ◐ NO-GO | ✅ GO | 2 设备 30min |

## 3. 手动走查 W1–W6

- W1 ASR 体验：跟读实时反馈，非回放
- W2 OCR 体验：真机拍照 + 回流路径可演示
- W3 绘本观感：≥400 scene 页 + 旧页不回归
- W4 范唱全库：13 首真人主唱
- W5 L1 朗读：字卡听感可接受
- W6 真机/商店：真机 evidence + Console 回执（非 BLOCKED）

## 4. 基线负向预期（R13 集成 @ 7/8）

| 探针 | 基线预期 | 原因 |
|---|---|---|
| H1 | FAIL | available=false，recorded=0 |
| H2 | FAIL | 无 r14 device B，App 33/41 |
| H3 | FAIL | scene=209<400 |
| H4 | FAIL | humanVocal=0–3/13 |
| H5 | FAIL | 无 L1 批次 |
| H6 | FAIL | 无 r14 真机 signoff |
| H7 | FAIL | BLOCKED 延续 |
| H8 | PASS | round12 8/8 + round13 7/8 |
