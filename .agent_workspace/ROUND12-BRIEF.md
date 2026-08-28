# Round 12 简报 · 洪恩级体验全量落地

> 基线：`cursor/openmoji-integration-9f67` @ R11 闭合（`check:round11` 8/8 · `53d125b`）
> 集成分支：`cursor/openmoji-integration-9f67`
> 目标：把 R11 的「样板/清单/评估」升到**孩子当场感知不到差距**；真机通道定案

## 为何还要 Round 12

R11 工程门禁已绿，但体验审计预判仍为 **◐7**（见 `round11-hongen-audit.md` §5.1）——R11 交付的是「敢上 / 能测 / 有样板」，不是全量洪恩级：

| 深度债 | R11 已交付 | R12 目标 |
|---|---|---|
| L-M9 跟读 | 冻结清单 + Go/No-Go + 评测集；`available:false` | **模型真落库**（files[] + sha256 + 可选 `available:true`）+ 儿童冻结集跑分 |
| L-M10 OCR | 6 张 real + 失败话术 | **系统化矩阵 ≥8 张**（光照×角度分格）+ **真机/模拟器 harness** |
| L-M11 儿歌 | 8/13 合成渲染旋律 | **13/13 全覆盖** + **范唱人声试点**（X1 选型落地） |
| L-M5 绘本 | 20 页场景样板（3 本） | **高频单元批量铺开**（≥60 页 scene 或 ≥15 本含 scene） |
| M-M1 推荐 | 周计划 + 家长理由 | **超越线**：开练覆盖 34 节点 + **推荐效果度量** |
| L/M-M15/16 | Web 预算 + evidence/r11 | **mobile LH 复测** + **真机通道三选一定案**（evidence/r12） |
| X1 合成语音 | TTS 选型评估文档 | **试点落地**（古诗/儿歌至少 1 条离线 TTS 或真人音频链路） |
| 发布/分发 | 商店清单 + 反馈骨架 | **提交演练文档** + 反馈回路可运行 |

## 硬门槛（`check-round12.mjs` 基线 1/8，仅 H8 绿）

| 探针 | 阈值 |
|---|---|
| H1 ASR 落库 | manifest `files[]` ≥1 项含 path/sha256/bytes **或** `available:true` + Go/No-Go 更新 + `ROUND12_H1` |
| H2 OCR 系统化 | real 去重 ≥8 + 矩阵 tier 标签（光照/角度）+ 真机 harness 实体 + `ROUND12_H2` |
| H3 绘本铺开 | scene 页 ≥60（≥2 元素/页）+ `ROUND12_H3` |
| H4 儿歌全库 | 去重音频资产 **13/13** + 范唱试点信号 + `ROUND12_H4` |
| H5 推荐度量 | 效果度量实体（掌握度 lift / 采纳率）+ 开练覆盖扩展 + `ROUND12_H5_SMOKE` |
| H6 真机/LH | `evidence/r12/` mobile LH ≥2 份有效 JSON + 真机通道定案文档 |
| H7 TTS/发布 | TTS 试点资产/接线 **或** 商店提交演练记录 + 反馈回路运行说明 |
| H8 往轮不退化 | `check:round11` 8/8 |

## 子代理分工（10）

| # | 模型 | 分支 | 任务 |
|---|---|---|---|
| 1 | fable | `cursor/r12-arch-contracts-9f67` | Round 12 全量落地架构契约 |
| 2 | fable | `cursor/r12-module-audit-9f67` | 洪恩体验口径终审（R11 后） |
| 3 | fable | `cursor/r12-acceptance-spec-9f67` | ROUND12-ACCEPTANCE + check-round12 v1.1 |
| 4 | opus-fast | `cursor/r12-literacy-asr-ship-9f67` | ASR 模型落库 + 跑分 + 可选 available |
| 5 | opus-fast | `cursor/r12-literacy-ocr-device-9f67` | OCR 矩阵系统化 + 真机 harness |
| 6 | opus-fast | `cursor/r12-literacy-books-rollout-9f67` | 绘本场景批量铺开 |
| 7 | opus-fast | `cursor/r12-literacy-songs-vocal-9f67` | 儿歌 13/13 + 范唱人声试点 |
| 8 | gpt-sol | `cursor/r12-math-reco-metrics-9f67` | 推荐度量 + 图谱开练全覆盖 |
| 9 | gpt-sol | `cursor/r12-perf-device-lh-9f67` | mobile LH 复测 + 真机通道定案 |
| 10 | gpt-sol | `cursor/r12-tts-release-drill-9f67` | TTS 试点 + 商店提交演练 |

## 规则

- 首行 Model slug；分支 `cursor/<name>-9f67`
- worktree 开发；cherry-pick 合入；合并前 `check:round11` 8/8 不退化
- 参考：`.agent_workspace/round11-hongen-audit.md` §5 R12 归属
- **禁止**未授权商业模型/曲库；ASR 模型 ≤60MiB 自托管 + THIRD_PARTY_NOTICES；音频 CC0/自建/明确授权
- 真机项 VM 不可测须标 `[SKIP owner: Android QA]`，但 **R12 必须三选一定案**（设备/云真机/显式发布决策）
