# Round 8 简报 · 深度超越与 A 层终态

> 基线：`cursor/openmoji-integration-9f67` @ Round 7 闭合（`check:round7` 8/8 · `check:round6` 7/7）
> 集成分支：`cursor/openmoji-integration-9f67`
> 门禁：`npm test` 全绿 → `npm run check:round8` → `npm run check:round7` → `npm run test:round3` → `npm run build:all`

## P0 必交付

### 识字 · 内容深度
- **L-M6** 字源动画 **525→800**（pipeline 批量，同步 `etymology-index.js`）
- **L-M11** 单元剧情 **u59–u99 手写**（41 条，告别 `unitTeaser()` 兜底）；儿歌/音乐内容 v1（≥3 首，路由或专题入口）
- **L-M10** OCR **识别精度量化**（固定基准图集 + `test-ocr-accuracy.mjs`）；复核 `CharDetailView` 测验走形近池

### 识字 · 体验升级
- **L-M9** 跟读 v2：音素/声调级评分或 AI 学伴对话面（三档降级保留，在线识别隐私提示不退）

### 数学 · 可视化
- **M-M1** **技能图谱**可视化（路由 + 数据 + 与 ageBand/母题进度联动）

### 共同 · A 层终态
- **Lighthouse Perf ≥ 95** 双 App（R7 识字 97 / 数学 94；数学须补到 95+）
- **证据包完备**：LH 原始 JSON + axe 输出归档至 `.agent_workspace/evidence/r8/`
- **GLOBAL-SUMMARY-REPORT** 刷新 Round 8（31/31 模块，零 ❌ 零 ⬜）
- **四主题 a11y** serious 余项收尾（数学首页对比度等）
- **Android** 重跑 `sync:android` + `check:android` 26/26

## 硬门槛（`check-round8.mjs`）

| 探针 | 阈值 |
|---|---|
| H1 字源 800 | `ETYMOLOGY_CHARS` ≥ 800 |
| H2 单元剧情 | `STORIES` 键 ≥ 99（含 u59–u99） |
| H3 技能图谱 | 路由 + 视图 + 数据文件三重接线 |
| H4 OCR 精度 | 基准集测试脚本 + smoke/CI 标记 |
| H5 跟读 v2 | 音素/对话面接线 + smoke 标记 |
| H6 Perf 95 | 双 App Lighthouse P ≥ 95（acceptance-log 留档） |
| H7 全局报告 | Round 8 报告 + 证据包索引 |
| H8 往轮不退化 | `check:round7` 8/8 |

## 子代理分工（10）

| # | 模型 | 分支 | 任务 |
|---|---|---|---|
| 1 | fable | `cursor/r8-arch-contracts-9f67` | Round 8 架构契约 |
| 2 | fable | `cursor/r8-module-audit-9f67` | 洪恩对标 R8 审计 |
| 3 | fable | `cursor/r8-acceptance-spec-9f67` | ROUND8-ACCEPTANCE + check-round8 强化 |
| 4 | opus-fast | `cursor/r8-literacy-etymology-9f67` | 字源 525→800 |
| 5 | opus-fast | `cursor/r8-literacy-stories-9f67` | u59–u99 剧情 + 儿歌 v1 |
| 6 | opus-fast | `cursor/r8-math-skillgraph-9f67` | 技能图谱可视化 |
| 7 | opus-fast | `cursor/r8-literacy-ocr-quality-9f67` | OCR 精度评测 + quiz 形近复核 |
| 8 | gpt-sol | `cursor/r8-literacy-followread-9f67` | 跟读 v2 / 学伴对话面 |
| 9 | gpt-sol | `cursor/r8-perf-lighthouse-9f67` | Perf 冲 95 + a11y 余项 |
| 10 | gpt-sol | `cursor/r8-global-report-9f67` | 证据包 + GLOBAL-SUMMARY + 终验回归 |

## 规则

- 首行 Model slug；分支 `cursor/<name>-9f67`
- 内容脚本化 + CI 探针；合并前 `check:round7` 8/8、`check:round6` 7/7 不退化
- 共享 VM 用 worktree（`/tmp/wt-r8-<task>`）；只 cherry-pick 功能 commit
- 参考：`.agent_workspace/round7-hongen-final-audit.md` §R8 归属清单
