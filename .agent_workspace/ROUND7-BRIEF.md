# Round 7 简报 · 全面超越终验

> 基线：`cursor/openmoji-integration-9f67` @ Round 6 闭合（`check:round6` 7/7）
> 集成分支：`cursor/openmoji-integration-9f67`
> 门禁：`npm test` 全绿 → `npm run check:round7` → `npm run test:round3` → `npm run build:all`

## P0 必交付

### 识字
- **L-M10** Tesseract.js 拍照识字 v1（前端 OCR → 字库匹配讲解，离线 wasm）
- **L-M4** 听音识字形近干扰项（distractors 走形近字库，非纯随机）
- **L-M6** 字源动画 65→**200+**（pipeline 批量，不手搓）

### 数学
- **M-M1** 年龄档 L1–L5 **全模块联动**（非仅 Arithmetic/Parent）
- **M-M6** 逻辑配对/迷宫小游戏 v1（Canvas，reduced-motion 降级）

### 共同
- **第 4 主题** `aurora` + 四主题对比度走查（axe + 手动留档 C-5）
- **Lighthouse Perf ≥ 90** 双 App（首屏拆包 / SW 预缓存策略优化）
- **全浏览器矩阵** C-6（Chrome / Firefox / Safari WebKit 探针 + 走查表）
- **GLOBAL-SUMMARY-REPORT.md** 洪恩对标全表 ✅ + 证据包索引
- **Android sync** 重跑 `npm run sync:android` + `check:android` 26/26

## 硬门槛（`check-round7.mjs`）

| 探针 | 阈值 |
|---|---|
| H1 拍照识字 | 路由 + OCR pipeline + smoke |
| H2 形近干扰 | Listen/Quiz distractors 探针 |
| H3 字源动画 | ≥ 200 字 |
| H4 年龄档联动 | ≥5 模块读 ageBand |
| H5 逻辑小游戏 | 配对或迷宫路由 + smoke |
| H6 第 4 主题 | theme=aurora + tokens 接线 |
| H7 全局报告 | GLOBAL-SUMMARY-REPORT 全表 ✅ |

## 子代理分工（10）

| # | 模型 | 分支 | 任务 |
|---|---|---|---|
| 1 | fable | `cursor/r7-arch-contracts-9f67` | Round 7 架构契约 |
| 2 | fable | `cursor/r7-module-audit-9f67` | 洪恩对标终验审计 |
| 3 | fable | `cursor/r7-acceptance-spec-9f67` | ROUND7-ACCEPTANCE + check-round7 |
| 4 | opus-fast | `cursor/r7-literacy-ocr-9f67` | Tesseract 拍照识字 |
| 5 | opus-fast | `cursor/r7-literacy-distractors-9f67` | 形近干扰 + 字源 200+ |
| 6 | opus-fast | `cursor/r7-math-ageband-9f67` | 年龄档全模块联动 |
| 7 | opus-fast | `cursor/r7-math-logic-games-9f67` | 逻辑配对/迷宫 |
| 8 | gpt-sol | `cursor/r7-theme-aurora-9f67` | 第 4 主题 + 四主题对比度 |
| 9 | gpt-sol | `cursor/r7-perf-lighthouse-9f67` | Perf 三板斧冲 ≥90 |
| 10 | gpt-sol | `cursor/r7-global-report-9f67` | GLOBAL-SUMMARY + test:round3 + zip |

## 规则

- 首行 Model slug；分支 `cursor/<name>-9f67`
- 内容脚本化 + CI 探针；合并前 `check:round6` 7/7 不退化
- 共享 VM 用 worktree；只 cherry-pick 功能 commit
- 参考：`.agent_workspace/SURPASS-HONGEN-MASTER-PLAN.md` §Round 7
