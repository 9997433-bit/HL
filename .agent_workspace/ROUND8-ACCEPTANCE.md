Model slug: claude-fable-5
# Round 8 验收标准 · 深度超越与 A 层终态

> 版本：Round 8 v1.0（2026-08-27）
> 依据：`.agent_workspace/ROUND8-BRIEF.md` + `round7-hongen-final-audit.md` §R8
> 配套：`.agent_workspace/acceptance-log-round8.md`、`scripts/check-round8.mjs`（H1–H8）

## 0. 轮次门禁 G1–G7

| # | 门禁 | PASS 标准 |
|---|---|---|
| G1 | `npm test` | 全绿 |
| G2 | `npm run check:round7` | **8/8** 不退化 |
| G3 | `npm run check:round6` | **7/7** |
| G4 | `npm run check:round8` | **8/8** |
| G5 | `npm run test:round3` | 全绿 |
| G6 | `build:all` + `sync:android` + `check:android` | zip + **26/26** |
| G7 | Lighthouse | 双 App **P ≥ 95**（A/BP ≥ 90） |

## 1. 八项硬门槛（H1–H8）

| ID | 交付物 | PASS 标准 | 责任分支 |
|---|---|---|---|
| H1 | 字源 800 | `ETYMOLOGY_CHARS` ≥ 800，pipeline 生成 | r8-literacy-etymology |
| H2 | 单元剧情 + 儿歌 | `STORIES` ≥ 99（u59–u99 全覆盖）；`songs.js` ≥ 3 首 + 路由 | r8-literacy-stories |
| H3 | 技能图谱 | 数学路由 + 视图 + `skill-graph.js` 数据 | r8-math-skillgraph |
| H4 | OCR 精度 + quiz | `test-ocr-accuracy.mjs` 或 ROUND8_H4 基准；CharDetailView 形近池 | r8-literacy-ocr-quality |
| H5 | 跟读 v2 | 音素/声调或学伴对话 + `ROUND8_H5_SMOKE` | r8-literacy-followread |
| H6 | Perf 95 | acceptance-log-round8 双 App P ≥ 95；`evidence/r8/` 原始 JSON | r8-perf-lighthouse |
| H7 | 全局报告 | Round 8 报告零 ❌ 零占位 + 证据索引 | r8-global-report |
| H8 | R7 不退化 | `check:round7` 8/8 | 全部分支合并前 |

## 2. 红线

- 首屏 JS gzip 识字 < 420 KB、数学 < 250 KB（`check:bundle`）
- OCR / 字源 / 儿歌重资产懒加载，不进 SW 预缓存首屏
- FSRS、解锁规则、母题 185 阈值不动
- worktree 开发，禁止在共享 `/workspace` 切功能分支
