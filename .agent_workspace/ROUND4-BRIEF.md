# Round 4 简报 · P0 清零 + 核心闭环

> 基线分支：`cursor/openmoji-integration-9f67`（含 Round 3 合并态 + OpenMoji + 主计划）
> 集成分支：`cursor/hongen-edu-apps-9f67`
> 门禁：`npm run test:round3` 全绿 → Lighthouse Perf/A11y ≥90（过渡）→ `build:all`

## P0 必交付

### 识字
- **L-M2** 单字状态机：`intro→trace→listen→quiz→reward` 在 `CharDetailView` 自动衔接
- **L-M3** 描红错 3 次自动示范该笔（HanziStrokeBox）
- **L-M14** 徽章体系 v1（progress store + 成就页展示）
- **L-M1** 字库 200→**500**，`characters.js` 路由级/动态 import 懒加载
- **L-M13** 家长自定义学习计划（每日新字数 / 自选单元）

### 数学
- **M-M10** 错题本：`wrongBook[questionId]` + 重练入口，答对移出
- **M-M9** `adaptive.js`：连对升档/连错降档/弱项优先出题
- **M-M2/M-P9** mulberry32 PRNG + 题目 ID = 母题+seed；check 门禁 ≥300 可复现
- **M-M12** 日冒险 5 题 + 当前关呼吸高亮（HomeView）
- **M-M4** 比较模块入口（或比较玩法并入 number-sense）

### 共同
- Perf 三板斧：characters 拆包、gzip 静态服、关键 CSS
- `check:tokens` Phase 2/3 PASS
- `acceptance-log-round4.md` 实测回填 + zip 重打

## 子代理分工（10）

| # | 模型 | 分支前缀 | 任务 |
|---|---|---|---|
| 1 | fable | cursor/r4-arch-contracts | 状态机/adaptive/wrongBook 架构契约文档 |
| 2 | fable | cursor/r4-module-audit | 洪恩模块对标逐条审计（Round 4 口径） |
| 3 | fable | cursor/r4-acceptance-spec | Round 4 验收标准 + acceptance-log 模板 |
| 4 | opus-fast | cursor/r4-literacy-statemachine | 状态机 + 错3笔 + 徽章 |
| 5 | opus-fast | cursor/r4-literacy-500chars | 500字 + 懒加载 + 学习计划 |
| 6 | opus-fast | cursor/r4-math-wrongbook | 错题本 + adaptive 调度器 |
| 7 | opus-fast | cursor/r4-math-seed-daily | PRNG seed + 日冒险 + 比较模块 |
| 8 | gpt-sol | cursor/r4-perf-bundle | Perf 三板斧 |
| 9 | gpt-sol | cursor/r4-tokens-phase23 | tokens Phase 2/3 |
| 10 | gpt-sol | cursor/r4-lighthouse-regression | Lighthouse + test:round3 + zip |

## 规则
- 分支名必须 `cursor/<name>-9f67`
- 10 子代理共享 `/workspace`：冲突时用 **git worktree** 独立目录
- 首行声明 Model slug；完成 push；`npm test` 全绿再 PR
