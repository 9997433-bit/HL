# Round 9 简报 · 深度打磨与发布工程

> 基线：`cursor/openmoji-integration-9f67` @ Round 8 闭合（`check:round8` 8/8 · `check:round7` 8/8 · `check:round6` 7/7）
> 集成分支：`cursor/openmoji-integration-9f67`
> 门禁：`npm test` 全绿 → `check:round9` → `check:round8` → `test:round3` → `build:all`

## P0 必交付

### Round 8 编排闭合（#10 优先）
- 刷新 `GLOBAL-SUMMARY-REPORT.md` → 31/31 **✅**（去掉全部 ⏳ 待 R8）
- `npm test` → `test:round3` → `build:all` → `sync:android` → `check:android`
- 终验回填 `acceptance-log-round8.md`

### Round 9 深度
- **L-M5** 绘本社区投稿格式文档（`.agent_workspace/BOOK-COMMUNITY-SUBMISSION.md`）
- **L-M11** 儿歌 v2：曲库扩充 + 歌词同步动画增强（≥10 首或 v2 标记）
- **L-M10** OCR 基准扩样（手写/低光/复杂背景 tier + CI 阈值）
- **L-M9** 跟读 v3 路线：离线 ASR/音素评估文档或 PoC（不破坏三档降级）
- **M-M1** 技能图谱 × 进度/FSRS 推荐路径（只读推荐，不写回作弊）
- **工程** Lighthouse 版本锁 CI + `evidence/r9/` + Android 真机走查清单
- **质量** u59–u99 剧情 + 批量字源文案抽查修稿（≤20 条模板感条目）
- **发布** LICENSE 确认、对外声明草案、`RELEASE-CHECKLIST.md`

## 硬门槛（`check-round9.mjs`）

| 探针 | 阈值 |
|---|---|
| H1 儿歌 v2 | ≥10 首或 v2 动画标记 + smoke |
| H2 OCR 扩样 | ≥8 张基准图含 handwriting tier |
| H3 图谱推荐 | 推荐路径函数 + 视图展示 + smoke |
| H4 跟读路线 | ASR/音素评估文档或 PoC 接线 |
| H5 绘本投稿 | BOOK-COMMUNITY-SUBMISSION.md 完整 |
| H6 LH CI 锁 | CI 脚本 + evidence/r9 JSON |
| H7 发布清单 | RELEASE-CHECKLIST + Round 9 报告 |
| H8 往轮不退化 | check:round8 8/8 |

## 子代理分工（10）

| # | 模型 | 分支 | 任务 |
|---|---|---|---|
| 1 | fable | `cursor/r9-arch-contracts-9f67` | Round 9 架构契约 |
| 2 | fable | `cursor/r9-module-audit-9f67` | 洪恩对标 R9 审计 |
| 3 | fable | `cursor/r9-acceptance-spec-9f67` | ROUND9-ACCEPTANCE + check-round9 |
| 4 | opus-fast | `cursor/r9-literacy-songs-9f67` | 儿歌 v2 扩库 + 动画 |
| 5 | opus-fast | `cursor/r9-literacy-ocr-expand-9f67` | OCR 基准扩样 |
| 6 | opus-fast | `cursor/r9-math-graph-reco-9f67` | 技能图谱推荐路径 |
| 7 | opus-fast | `cursor/r9-content-quality-9f67` | 绘本投稿文档 + 剧情/字源质量修稿 |
| 8 | gpt-sol | `cursor/r9-literacy-followread-asr-9f67` | 跟读 ASR/音素路线 |
| 9 | gpt-sol | `cursor/r9-perf-ci-device-9f67` | LH CI 锁 + 真机清单 + math check-bundle |
| 10 | gpt-sol | `cursor/r9-global-release-9f67` | **R8 闭合** + R9 报告 + RELEASE-CHECKLIST |

## 规则

- 首行 Model slug；分支 `cursor/<name>-9f67`
- worktree 开发；cherry-pick 合入；合并前 `check:round8` 8/8 不退化
- 参考：`round8-hongen-audit.md` §R9 归属备忘
