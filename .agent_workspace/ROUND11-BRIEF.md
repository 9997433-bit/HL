# Round 11 简报 · 洪恩体验打磨与真机常态化

> 基线：`cursor/openmoji-integration-9f67` @ R10 闭合（`check:round10` 8/8 · LICENSE/隐私/1.0.0 齐）
> 集成分支：`cursor/openmoji-integration-9f67`
> 目标：把 R10 的 spike/样张/3 首真音频升到**可感知的洪恩级体验**；横切债立项闭环

## 为何还要 Round 11

R10 工程门禁已绿，但体验审计口径仍为 **✅24 / ◐7**（见 `round10-hongen-audit.md` §5）：

| 深度债 | R10 已交付 | R11 目标 |
|---|---|---|
| L-M9 跟读 | Worker spike，`available:false` | **冻结清单 + 评测集骨架 + Go/No-Go 证据**（真模型可后续挂载） |
| L-M10 OCR | 3 张 real-photo | **实拍矩阵扩样 ≥5 + 失败降级话术** |
| L-M11 儿歌 | 3/13 首真实音频 | **≥8 首真实旋律**（覆盖过半曲库） |
| L-M5 绘本 | 投稿 CI | **页级场景组合**（多元素 DSL/样板，告别单 emoji） |
| M-M1 推荐 | 一键开练 | **周计划 + 家长侧推荐理由/采纳痕迹** |
| L/M-M15/16 | desktop LH + 清单 SKIP | **路由级预算表 + evidence/r11 趋势冻结** |
| X1 合成语音 | 全线 SpeechSynthesis | **离线 TTS 选型评估文档**（piper/vits vs 分批录音） |
| 发布后半程 | MIT + 隐私页 | **商店/分发清单条目 + 试用反馈回路骨架** |

## 硬门槛（`check-round11.mjs` 基线 1/8，仅 H8 绿）

| 探针 | 阈值 |
|---|---|
| H1 跟读产品化 | ASR freezeChecklist 齐全 + 评测集/Go-No-Go 文档或 harness + `ROUND11_H1` |
| H2 OCR 矩阵 | real-photo 有效图 ≥5 + 失败话术信号 + `ROUND11_H2` |
| H3 周计划 | 推荐→周计划数据/视图 + 家长侧理由 + `ROUND11_H3_SMOKE` |
| H4 绘本场景 | 页级多元素场景样板 ≥1 单元 + `ROUND11_H4` |
| H5 儿歌过半 | 真实音频 ≥8 首 + `ROUND11_H5` |
| H6 预算/趋势 | `evidence/r11/` + 路由级预算或 LH 趋势记录 |
| H7 TTS/分发 | 离线 TTS 评估文档 **或** 商店清单章节 + 反馈回路文件 |
| H8 往轮不退化 | `check:round10` 8/8 |

## 子代理分工（10）

| # | 模型 | 分支 | 任务 |
|---|---|---|---|
| 1 | fable | `cursor/r11-arch-contracts-9f67` | Round 11 体验打磨架构契约 |
| 2 | fable | `cursor/r11-module-audit-9f67` | 洪恩体验口径复审（R10 后） |
| 3 | fable | `cursor/r11-acceptance-spec-9f67` | ROUND11-ACCEPTANCE + check-round11 v1.1 |
| 4 | opus-fast | `cursor/r11-literacy-followread-prod-9f67` | 跟读冻结清单 + 评测集/Go-No-Go |
| 5 | opus-fast | `cursor/r11-literacy-ocr-matrix-9f67` | OCR 实拍扩样 + 失败话术 |
| 6 | opus-fast | `cursor/r11-math-week-plan-9f67` | 推荐周计划 + 家长面板 |
| 7 | opus-fast | `cursor/r11-literacy-book-scene-9f67` | 绘本页场景组合样板 |
| 8 | gpt-sol | `cursor/r11-literacy-songs-expand-9f67` | 儿歌真实音频扩至 ≥8 |
| 9 | gpt-sol | `cursor/r11-perf-budget-trend-9f67` | 路由预算 + evidence/r11 |
| 10 | gpt-sol | `cursor/r11-tts-store-feedback-9f67` | TTS 评估 + 商店/反馈骨架 |

## 规则

- 首行 Model slug；分支 `cursor/<name>-9f67`
- worktree 开发；cherry-pick 合入；合并前 `check:round10` 8/8 不退化
- 参考：`.agent_workspace/round10-hongen-audit.md` §5 R11 归属
- **禁止**把未授权商业模型/曲库塞进仓库；真模型用清单+哈希冻结，资产用 CC0/自建
