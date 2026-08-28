# Round 5 简报 · 内容体量第一波

> 基线分支：`cursor/openmoji-integration-9f67` @ Round 4 闭合（500 字 / check:round4 全绿）
> 集成分支：`cursor/openmoji-integration-9f67`（子代理完成后 cherry-pick 合并）
> 门禁：`npm test` 全绿 → `npm run check:round5` → `npm run test:round3`

## P0 必交付

### 识字
- **L-M1** 字库 500→**1000**（`char-index.js` + `chars/uN.js` 懒加载，保持 `check:data` 全过）
- **L-M5** 分级绘本 5→**30**（正文仅用已学字，`verifyBookCoverage` 零越界）
- **L-M8** 成语 20→**60**
- **L-M6** 字源动画 pipeline v1（makemeahanzi / GSAP 程序化演变，≥50 字可演示）
- **L-M12** **3 款**新识字小游戏（迷宫/配对/拼字等，路由可达 + smoke 断言）

### 数学
- **M-M3** 应用题母题 34→**100**（语义模板 × 场景皮肤，`check:content` 门禁）
- **M-M8** 数形结合演示动画 ≥**7** 类模块首屏可演示（实物→图形→算式，可跳过）
- **M-M5** 七巧板 Canvas 玩法 v1
- **M-M13** 分与合教具 v1（`compose-ten` 技能点接线）
- **M-M11** 竖式专题 v1（进位/借位错因专练入口）

## 硬门槛（`check:round5.mjs`）

| 探针 | 阈值 |
|---|---|
| 识字字库 | ≥ 1000 |
| 识字绘本 | ≥ 30 |
| 识字成语 | ≥ 60 |
| 数学母题 | ≥ 100 |
| 数形演示 | ≥ 7 类（探针或目录约定） |

## 子代理分工（10）

| # | 模型 | 分支 | 任务 |
|---|---|---|---|
| 1 | fable | `cursor/r5-arch-contracts-9f67` | 架构契约：1000字/30绘本/100母题/小游戏/教具 |
| 2 | fable | `cursor/r5-module-audit-9f67` | 洪恩对标 Round 5 增量审计 |
| 3 | fable | `cursor/r5-acceptance-spec-9f67` | 验收标准 + acceptance-log-round5 + check-round5 |
| 4 | opus-fast | `cursor/r5-literacy-1000chars-9f67` | 500→1000 字 + 懒加载扩展 |
| 5 | opus-fast | `cursor/r5-literacy-books-9f67` | 绘本 5→30 |
| 6 | opus-fast | `cursor/r5-literacy-idioms-etymology-9f67` | 成语 20→60 + 字源动画 pipeline |
| 7 | opus-fast | `cursor/r5-literacy-minigames-9f67` | 3 款新识字小游戏 |
| 8 | opus-fast | `cursor/r5-math-problems-100-9f67` | 母题 34→100 |
| 9 | gpt-sol | `cursor/r5-math-manipulatives-9f67` | 数形演示×7 + 七巧板 + 分与合 + 竖式 |
| 10 | gpt-sol | `cursor/r5-regression-gate-9f67` | check:round5 接线 + test:round3 + 验收回填 |

## 规则
- 分支名 `cursor/<name>-9f67`；共享 VM 用 **git worktree**
- 首行声明 Model slug；`npm test` 全绿再 push
- 内容必须脚本化生成 + `check:data` / `check:content` 校验，禁止手搓无校验 JSON
