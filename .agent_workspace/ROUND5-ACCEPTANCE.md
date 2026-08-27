# Round 5 验收标准 —— 内容体量第一波

> 版本：Round 5 v1.0（2026-08-26）
> 依据：`.agent_workspace/SURPASS-HONGEN-MASTER-PLAN.md` §5「Round 5」+ `.agent_workspace/ROUND5-BRIEF.md`
> 配套：`.agent_workspace/sota-acceptance-criteria.md`（SOTA 全量标准，不重复罗列）、`.agent_workspace/acceptance-log-round5.md`（实测回填模板）
> 判定原则：每条都能被脚本或 10 分钟内的手动步骤验证；**写进简报不跑脚本视为未交付**（主计划原则 4）。

## 0. 轮次门禁（顺序执行，全过才可出包）

| # | 门禁 | 验证方式 | PASS 标准 |
| --- | --- | --- | --- |
| G1 | 全量单测回归 | `npm test` | 全绿（识字 srs/check:data/build/check:bundle/smoke + 数学 check:content/单测/build/smoke），Round 5 改动不得回归 Round 4 成果 |
| G2 | Round 5 内容硬门槛 | `npm run check:round5` | 退出码 0（6 项硬门槛全绿，见 §4；当前基线预期 **6 项全 FAIL**，属有意红灯） |
| G3 | Round 3 全链回归 | `npm run test:round3` | 全绿（含离线 smoke + acceptance）；Lighthouse Perf/A11y ≥ 90（过渡），终值目标 ≥ 95；axe critical/serious = 0 |
| G4 | 出包 | `npm run build:all` | 成功出包，zip 体积回填 acceptance-log §8（D-7：<10MB 级）；识字首屏 JS gzip < 250KB 保持 |
| G5 | 总达成率 | acceptance-log-round5.md 汇总 | P0 交付（§1–§3）达成率 ≥ **95%**；日志全部实测回填，无「待回填」残留 |

---

## 1. 识字 P0 交付与 PASS 标准

| 编号 | 交付物 | PASS 标准 | 验证方式 | 责任分支 |
| --- | --- | --- | --- | --- |
| L-M1 | 字库 500→**1000** | ① `TOTAL_CHARACTERS ≥ 1000`（`character-index.js` 索引 + `chars/uN.js` 懒加载分片，不进首屏 chunk）；② `check:data` 全过（拼音/声调/部首/笔画/单元归属/emoji 字段齐全，与 `shared/data/common-hanzi.json` 基线一致）；③ 内容必须脚本化生成，禁止手搓无校验数据 | `npm run check:round5` + `cd apps/literacy-app && npm run check:data` + dist chunk 清单 | r5-literacy-1000chars |
| L-M5 | 分级绘本 5→**30** | ① `BOOKS.length ≥ 30`，分级（level）覆盖递进梯度；② 正文只用已收录字：`verifyBookCoverage()` 返回**空数组**（零越界）；③ 每本有 id/title/pinyin/level/pages 完整结构，页文含拼音 | `npm run check:round5`（计数 + 零越界断言） + 实机翻页走查 | r5-literacy-books |
| L-M8 | 成语 20→**60** | `IDIOMS.length ≥ 60`；每条含释义、故事/例句与配图 emoji；成语页可达且详情完整 | `npm run check:round5` + 实机走查 | r5-literacy-idioms-etymology |
| L-M6 | 字源动画 pipeline v1 | ≥ **50** 字可播放「字源演变」演示（makemeahanzi 数据或 GSAP 程序化演变）；入口在字详情内可达；可跳过（D-6）；`prefers-reduced-motion` 降级 | 探针（§4）+ 手动抽查 ≥ 5 字 | r5-literacy-idioms-etymology |
| L-M12 | **3 款**新识字小游戏 | ① 新增小游戏 ≥ 3（迷宫/配对/拼字等，不含已有听音游戏）；② 注册到 `apps/literacy-app/src/data/games.js` 的 `GAMES` 表（约定见 §5）；③ 每款路由可达 + smoke 断言；④ 键盘可完成、触控 ≥ 56×56、可跳过庆祝 | `npm run check:round5`（注册表 + 路由接线） + smoke + 手动走查 | r5-literacy-minigames |

## 2. 数学 P0 交付与 PASS 标准

| 编号 | 交付物 | PASS 标准 | 验证方式 | 责任分支 |
| --- | --- | --- | --- | --- |
| M-M3 | 应用题母题 34→**100** | ① `WORD_PROBLEMS.length ≥ 100`（语义模板 × 场景皮肤，每个母题为 `make()` 生成器）；② 参数域约束保证正整数答案；③ `check:content` 门禁扩展覆盖新母题（可复现、答案合法） | `npm run check:round5` + `cd apps/math-app && npm run check:content` | r5-math-problems-100 |
| M-M8 | 数形结合演示 ≥ **7** 类 | ① `VISUAL_DEMOS` 注册表 ≥ 7 类（约定见 §5）；② 每类演示「实物→图形→算式」三段递进，模块首屏可发现入口；③ 可跳过（D-6），`prefers-reduced-motion` 降级为静态图 | `npm run check:round5`（注册表计数） + 手动逐类走查 | r5-math-manipulatives |
| M-M5 | 七巧板 Canvas 玩法 v1 | 拖拽/旋转拼图可完成至少 3 个目标图形；判定与完成反馈；键盘替代通道 | 探针（§4）+ 手动走查 | r5-math-manipulatives |
| M-M13 | 分与合教具 v1 | `compose-ten` 技能点接线；数字分解/合成可交互演示 + 练习判定 | 探针（§4）+ 手动走查 | r5-math-manipulatives |
| M-M11 | 竖式专题 v1 | 进位/借位错因专练入口可达；按 `errorTags` 归因出题 | 探针（§4）+ 手动走查 | r5-math-manipulatives |

## 3. 共同 P0 交付与 PASS 标准

| 编号 | 交付物 | PASS 标准 | 验证方式 | 责任分支 |
| --- | --- | --- | --- | --- |
| C-R5-1 | check:round5 接线 | 根 `package.json` 含 `check:round5`；6 项硬门槛全部脚本化（§4）；探针随责任分支交付升级为硬门槛 | `npm run check:round5` | r5-acceptance-spec / r5-regression-gate |
| C-R5-2 | 验收日志回填 | `acceptance-log-round5.md` 全部实测回填（无「待回填」）；`build:all` 重打 zip 并记录体积 | 文档审查 + G4 | r5-regression-gate |

---

## 4. `scripts/check-round5.mjs` 硬门槛与探针

Round 5 内容门禁脚本（`npm run check:round5`）。**六项硬门槛**（FAIL 即退出码 1）：

| # | 检查 | 阈值 | 基线现状（aacd996） | 责任分支 |
| --- | --- | --- | --- | --- |
| H1 | 识字字库 `TOTAL_CHARACTERS` | ≥ **1000** | 500 → **预期 FAIL** | r5-literacy-1000chars |
| H2 | 识字绘本 `BOOKS.length`（且 `verifyBookCoverage()` 零越界） | ≥ **30** | 5 → **预期 FAIL** | r5-literacy-books |
| H3 | 识字成语 `IDIOMS.length` | ≥ **60** | 20 → **预期 FAIL** | r5-literacy-idioms-etymology |
| H4 | 数学母题 `WORD_PROBLEMS.length` | ≥ **100** | 34 → **预期 FAIL** | r5-math-problems-100 |
| H5 | 数形演示 `VISUAL_DEMOS` 注册表 | ≥ **7** 类 | 未接线 → **预期 FAIL** | r5-math-manipulatives |
| H6 | 新识字小游戏（`GAMES` 注册表，不含 listen） | ≥ **3** 款且路由已接线 | 0 款 → **预期 FAIL** | r5-literacy-minigames |

**探针**（PENDING，只提示不拦截；功能一旦合入，对应探针必须在同一 PR 内升级为硬门槛，否则视为未交付——继承 Round 4 原则）：

| 探针 | 期望约定 | 责任分支 |
| --- | --- | --- |
| L-M6 字源动画 pipeline（≥50 字） | `apps/literacy-app/src/data/etymology.js` 导出 `ETYMOLOGY_CHARS`（或等价注册表） | r5-literacy-idioms-etymology |
| M-M5 七巧板 | `apps/math-app/src/modules/tangram/` 存在且注册进 `modules.js` | r5-math-manipulatives |
| M-M13 分与合 | `apps/math-app/src/modules/compose/`（或等价）+ `compose-ten` 技能点 | r5-math-manipulatives |
| M-M11 竖式专题 | `apps/math-app/src/modules/vertical/`（或等价）+ 进位/借位错因入口 | r5-math-manipulatives |

## 5. 注册表约定（探针可读性要求）

为让门禁脚本在 **Node 环境（无浏览器、无构建）** 下直接 import 校验，注册表必须是纯数据模块：

- **数形演示**：`apps/math-app/src/data/visualDemos.js` 导出 `VISUAL_DEMOS` 数组（或 `apps/math-app/src/core/visual-demos/index.js` 等价导出）。每项含 `id`、`title`、`skill`、`stages`（实物→图形→算式三段描述）。**不得直接 import `.vue` 组件**——组件用路由名/组件名字符串引用。
- **识字小游戏**：`apps/literacy-app/src/data/games.js` 导出 `GAMES` 数组。每项含 `id`、`name`、`route`（如 `/game/maze`）、`skill`、`view`（视图组件名字符串）。`route` 必须能在 `apps/literacy-app/src/router/index.js` 中找到接线。已有听音游戏（`listen`）可一并注册但**不计入** ≥ 3 新增门槛。
- 允许使用 `@/` 别名 import（门禁脚本内置 alias 解析 hook），但注册表模块的依赖链不得触及 `.vue` / CSS 等 Node 无法解析的资源。

## 6. 不回归红线（继承 Round 3/4，抽查即可）

- axe critical = 0 且 serious = 0（双 App 全路由 + 交互态，`npm run test:a11y`）
- 断网冷启动完成学习闭环（`npm run test:offline`）
- 触控 ≥ 56×56、键盘可达、庆祝可跳过、`prefers-reduced-motion` 降级
- 运行时零第三方域名请求；`THIRD_PARTY_NOTICES` 随新资源（如 makemeahanzi）同步
- 识字首屏 JS gzip < 250KB；字库/绘本/成语等大数据模块必须懒加载，不进首屏 chunk

## 7. 回填要求

每条 P0 在 `acceptance-log-round5.md` 对应小节必须有**实测数据或命令输出**（分数、计数、日志粘贴、走查勾选）。禁止「应该可以」「理论上通过」。未达标项一律进 acceptance-log §9 未达标表并写明责任分支与计划，不得静默遗漏。
