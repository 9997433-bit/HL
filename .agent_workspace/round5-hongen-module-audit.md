# Round 5 · 洪恩模块对标审计（fresh code walk）

> 审计人：Round 5 子代理 #2（fable）
> 审计基线：分支 `cursor/r5-module-audit-9f67`（自 `cursor/openmoji-integration-9f67` @ `aacd996`，即 Round 4 闭合点）
> 审计日期：2026-08-26 · Node 22.14.0
> 方法：**逐文件重新走读源码**（不照抄 Round 4 结论），每条状态附代码证据路径；
> 内容体量用 `node` 实际 import 数据文件统计；测试计数来自本机 `npm test` 实跑（留档 `/tmp/r5-npm-test-baseline.log`）。

---

## 0. 基线 `npm test` 实测（aacd996、本机实跑）

命令：`npm test`（= `test:literacy` + `test:math`），**退出码 0，全绿**。

| 套件 | 明细 | 结果 |
|---|---|---|
| 识字 `test:srs` | FSRS 单元测试 | **8/8 通过** |
| 识字 `check:data` | 字表/绘本/成语/部首内容自检 | **35 项通过，0 项失败**（R4 基线 33 项） |
| 识字 `check:bundle` | 构建产物体检（**R4 新增门禁**） | **4 项通过**：33/33 单元课文独立切块、首屏无同步课文包、首屏无字义、首屏 JS 269 KB（预算 420 KB） |
| 识字 `build` | vite 构建 | ✅ **701 个构建文件**（R4 基线 374），含 **621 个离线笔顺 JSON**（课程字 500 + 部首/成语/绘本用字 121，约 1384 KB） |
| 识字 `smoke.mjs` | 无头浏览器冒烟 | **21 条路由 + 18 项交互，0 项有问题**（R4 基线 21+15；新增：五步状态机自动衔接、同笔连错 3 次自动示范、徽章点亮 3 条断言） |
| 数学 `check:content` | 题库/数独/音效自检 | **全部通过**（母题 34 个 × 各压测 2000 道；比大小 3000 道可按 seed 复现；每日冒险 400 天 2000 道同日可复现跨日不重样；自适应引擎弱项抽中 3719/4000、升降档与 EMA 一致；技能映射 25 个 id 全在图谱） |
| 数学 `build` | vite 构建 | ✅ **41 个构建文件**（index 主包 285.21 kB / gzip 102.56 kB；**路由级拆包已落地**：Daily/Compare/Progress/Parent/各星球视图均为独立 chunk） |
| 数学 `smoke.mjs` | 无头浏览器冒烟 | **12 条路由 + 21 项交互，0 项有问题**（R4 基线 10+17；新增路由 `/daily` `/compare`，新增断言：今日冒险刷新不换题+打卡、比大小三符号、错题本入库→重做出库、呼吸高亮） |

冒烟合计：**识字 39 项 / 数学 33 项，共 72 项全过**（R4 基线 63 项）。

**轮次门禁快照（本分支实跑）**：

- `node scripts/check-round4.mjs`：**4 项通过 / 0 失败**（字库 500、错题本、adaptive、种子 PRNG 探针全绿）——Round 4 硬门槛已闭合。
- `node scripts/check-round5.mjs`：**0 项通过 / 5 项失败**（字库 500<1000、绘本 5<30、成语 20<60、母题探针报错、数形演示未接线）——基线**预期全红**，即 Round 5 的靶子。
- ⚠️ 两个门禁问题须 **#10** 处理：① `check-round5.mjs` 的母题探针直接 `import wordProblems.js` 会因 `@/utils` 别名崩掉（`Cannot find package '@/utils'`），要像 `check-content.mjs` 一样走 `--import ./scripts/register-alias.mjs` 或读构建产物；② `npm run check:round5` 别名尚未进 `package.json`（`aacd996` 只加了脚本文件，别名在 #10 的未提交工作区改动里）。

---

## 1. 识字 App 对标表（L-M1 … L-M15）

图例：✅ 达标 / ◐ 有 MVP 但缺洪恩级深度 / ❌ 未实现。「Δ」列 = 相对 Round 4 审计的变化。

| 模块 | 洪恩能力 | 状态 | Δ | 实测证据（文件路径 + 关键事实） | Round 5 责任分支 |
|---|---|---|---|---|---|
| L-M1 | 1800 常用字分级 | ◐ | ❌→◐ | `apps/literacy-app/src/data/characters.js`：`CHARACTERS.length = 500`、**33 个单元**；懒加载管线已成型：`char-index.js` 主包索引 + `chars/u1.js…u33.js` 按单元切包（check:bundle 验证 33/33 块独立、首屏无字义）；离线笔顺 621 个 JSON。体量 = 洪恩的 ~28%，**R4 目标 500 已达成**，管线可直接扩容 | **#4** `cursor/r5-literacy-1000chars-9f67`（500→1000） |
| L-M2 | 认-读-写-玩闭环（状态机） | ✅ | ◐→✅ | `apps/literacy-app/src/views/CharDetailView.vue`：五步状态机 `PHASES = intro→trace→listen→quiz→reward`（L40-46），自动衔接走 `pendingNext` 可按停（WCAG 2.2.1，L52-61）、听音环节内嵌本页（L43 三选一）、`done` 只记真正做完的步骤、四步齐才发奖（L64-82）。smoke 断言「五步自动衔接完成（闭环 1 次），步骤条可回跳」实测通过 | 维护（smoke 断言已入门禁） |
| L-M3 | 笔顺+描红判定 + 错3次示范 | ✅ | ◐→✅ | `apps/literacy-app/src/components/HanziStrokeBox.vue`：逐笔判定 + `demoAfterMistakes: 3`（L31-32）——同笔连错 3 次 `demonstrateStroke()` 慢放示范该笔再从原地接回测验（L218+）；键盘替代通道同享此逻辑（示范期间挡住「写下一笔」，L216）。smoke 断言「连错 3 次触发 1 次自动示范，接回测验后写完」实测通过 | 维护 |
| L-M4 | 听音识字/测验 | ◐ | = | `apps/literacy-app/src/views/ListenGameView.vue`：干扰项**仍为随机取样**（L141 `shuffle(list.filter(...)).slice(...)`，无形近字库）；`CharDetailView.vue` 内嵌听音步的 `distractors()`（L238-250）同样随机。3 皮肤/复习优先维持 R4 状态 | **⚠️ R5 简报未指派**——建议并入 #7 或列维护项 |
| L-M5 | 130 本分级绘本 | ❌ | = | `apps/literacy-app/src/data/books.js`：`BOOKS.length = 5`（28 页、84 个不重复用字，check:data 实测）。体量 = 洪恩的 ~4%，R4 未动（按计划） | **#5** `cursor/r5-literacy-books-9f67`（5→30，正文仅用已学字） |
| L-M6 | 800+ 字源互动 | ◐ | = | `apps/literacy-app/src/data/radicals.js`：仍为 18 个部首 + `RadicalsView.vue` 详情页；无 makemeahanzi 字源、无演变动画 | **#6** `cursor/r5-literacy-idioms-etymology-9f67`（字源动画 pipeline v1，≥50 字可演示） |
| L-M7 | 记忆曲线复习 | ✅ | = | `apps/literacy-app/src/utils/srs.js`（FSRS-lite，8/8 单测）+ `stores/progress.js` 调度 + `ParentView.vue` 记忆热力图；smoke「到期卡进复习队列、未到期不进」实测通过。R4「可视化增强」未指派也未做，但基础能力本就达标 | 维护 |
| L-M8 | 成语/古诗国学 | ◐ | = | `apps/literacy-app/src/data/idioms.js`：仍 20 条成语（小剧场/换主题头图 smoke 过）；古诗 0 首 | **#6**（成语 20→60；古诗 20 首归 R6） |
| L-M9 | AI 学伴/跟读评测 | ❌ | = | `apps/literacy-app/src/utils/speech.js` 仅 TTS；全库无 SpeechRecognition/录音 | R6（本轮不动） |
| L-M10 | 拍照识字 | ❌ | = | 全库 grep `tesseract/ocr/拍照` 零命中 | R6/R7（本轮不动） |
| L-M11 | 动画儿歌/IP | ◐ | = | GSAP 仍在 9+ 视图但已改**异步加载**（R4 Perf 三板斧：进度环/首页进场改 CSS、庆祝层延迟加载动画组件）；内容侧无新增儿歌/IP | **#7** 扩游戏壳时顺带（本轮主责在小游戏） |
| L-M12 | 字迷宫/跑酷等小游戏 ≥5 | ❌ | = | `src/router/index.js`：小游戏仍只有 `/listen` 1 款（`/game/listen` 是旧路径重定向）；迷宫/配对/跑酷/找不同/拼字均无 | **#7** `cursor/r5-literacy-minigames-9f67`（+3 款，路由可达 + smoke 断言） |
| L-M13 | 家长控制/防沉迷 | ✅ | ◐→✅ | `apps/literacy-app/src/views/ParentView.vue`：口算门 + 进度 + 热力图 + 导出/导入 + 每日时长之外，**学习计划已落地**（L126-149/L376-380：`planUnits` 自选单元、空数组=全课程；`stores/progress.js` L78-87 `dailyGoal` 每日新字上限 + L327-331 计划过滤）。R4 目标全部交付 | 维护 |
| L-M14 | 奖励/徽章体系 | ✅ | ◐→✅ | `apps/literacy-app/src/data/badges.js`：**10 枚徽章**（单指标+阈值，bronze/silver/gold 三档，可画进度条）+ `BadgeShelf.vue` 成就墙；progress store `badgeStats` 记账。smoke 断言「首页点亮 1 枚；家长中心共 10 枚（9 枚带进度条）」实测通过 | 维护（新小游戏可扩 metric） |
| L-M15 | 性能/无障碍/离线 | ✅ | ◐→✅ | **Lighthouse 99/100/100**（Perf/A11y/BP，R4 验收实测，gzip 静态服）；axe 20 路由 + 42 主题×状态扫描 `critical=0/serious=0`；离线：sw 预缓存 + 621 笔顺 JSON + offline-smoke；首屏 gzip 101,140 B（R4 实测，较拆包前 -23.5%）；`check:bundle` 4 项门禁常驻 `npm test` 防回退 | **#10** `cursor/r5-regression-gate-9f67` 回归维持（内容扩容后须重测） |

**识字小计：✅ 6 / ◐ 5 / ❌ 4（共 15 项）**（Round 4 审计：✅ 1 / ◐ 9 / ❌ 5）

---

## 2. 数学 App 对标表（M-M1 … M-M16）

| 模块 | 洪恩能力 | 状态 | Δ | 实测证据（文件路径 + 关键事实） | Round 5 责任分支 |
|---|---|---|---|---|---|
| M-M1 | 3–12 岁 L1–L5 年龄档 | ◐ | = | `apps/math-app/src/stores/settings.js` `AGE_BANDS` + 家长页可选维持；`rg -l ageBand src` 仍只命中 `ArithmeticView.vue`/`ParentView.vue`/`settings.js`——**全模块联动 R4 未做、R5 简报也未指派** | **⚠️ 未指派**——建议并入 #9 或顺延 R6 |
| M-M2 | 1000+ 互动/无限题 | ◐ | =（质变） | **种子化已闭环**：`src/utils/random.js` 全量 mulberry32（`hashSeed`/`createRng`/`questionId()` 把 seed 写进题目 id）；check:content 实测「比大小 3000 道可按 seed 复现」「每日冒险同日可复现」。**体量未动**：母题 34、`check-content.mjs` `MIN_TEMPLATES = 25`，距 ≥300 门禁仍差一个量级，故整体维持 ◐ | **#8** `cursor/r5-math-problems-100-9f67`（扩容后同步提门禁阈值） |
| M-M3 | 185 应用题母题 | ◐ | = | `apps/math-app/src/data/wordProblems.js`：34 个母题（25 类语义标签/32 种场景，一步13·两步16·进阶5，check:content 权威计数）。体量 = 洪恩的 ~18% | **#8**（34→100） |
| M-M4 | 数感/比较/运算 | ◐ | ◐+（比较已补） | 数感 ✅、运算 ✅ 维持；**比较玩法已落地**：`router` L19-22 `/compare` 比大小擂台（`mode: 'compare'` 复用数量星云壳）+ `data/compare.js`，smoke「> < = 三个符号、判定正确」实测过，数量星云内也混入比大小题型；**竖式仍 ❌** | **#9** `cursor/r5-math-manipulatives-9f67`（竖式专题 v1） |
| M-M5 | 几何/空间 + 七巧板 | ◐ | = | `geometry/GeometryView.vue` 5 种题型维持；七巧板仍无 Canvas 玩法 | **#9**（七巧板 Canvas v1） |
| M-M6 | 逻辑/规律 + 配对/迷宫 | ◐ | = | `logic/LogicView.vue` 5 种规律题维持；记忆配对/迷宫仍无 | **⚠️ 主计划归 R5 但 R5 简报 P0 未列**——建议并入 #9 余量或明确顺延 R6 |
| M-M7 | 数独专项 | ✅ | = | 4/6/9 三档 + 唯一解门禁（check:content 272 局全压测）+ smoke 填格/提示/切 9×9 全过 | 维护 |
| M-M8 | 数形结合演示 | ❌ | = | `check-round5.mjs` 探针实跑确认「数形演示未接线」（期望 `apps/math-app/src/data/visualDemos.js` 或等价注册表，不存在）；仍只有 wordProblems 静态 `visual` 图示 | **#9**（演示 ×7 类模块首屏，可跳过） |
| M-M9 | 自适应难度 | ✅ | ◐→✅ | `src/core/engine/adaptive.js`：连对 3 升档/连错 2 降档、升降后 streak 归零、**一轮最多挪一档**（`9e8c4af`）；弱项优先按权重抽题（`pickNextQuestion`），**已接线 `QuizShell.vue`**（非死代码）。check:content 断言「弱项抽中 3719/4000、错题优先 2868:1132、升降档与 EMA 推进一致」实测通过 | 维护 |
| M-M10 | 错题本 | ✅ | ❌→✅ | `stores/progress.js`：questionId 级 `wrongBook` + `retryWrong()`（L554，答对移出+奖 1 星）；`components/WrongBook.vue` 重做流程（试过的选项禁掉再试）；入口在 `modules/progress/ProgressView.vue` L331。smoke「答错入库 → 进度页重做出库 → 答对后出库并落盘」实测通过 | 维护 |
| M-M11 | 计算专题/速算 | ◐ | = | 口算闯关维持（连击/数轴/错因/键盘）；竖式/进位借位错因专练仍无 | **#9**（竖式专题 v1，与 M-M4 同一交付） |
| M-M12 | 剧情关卡地图 + 日冒险 | ✅ | ◐→✅ | `modules/home/HomeView.vue`：推荐星球**呼吸高亮**（L411 只动光晕；L570 关动效时退化为常亮描边，a11y 兜底）+「今日冒险 · 5 题」CTA；`modules/daily/DailyView.vue` + `data/daily.js`：每天固定 5 题、同日刷新不换题、跨日不重样（check:content 400 天 2000 道压测）、完成打卡连续天数。smoke 两条断言实测过 | 维护 |
| M-M13 | 互动教具 ≥3 | ◐ | = | 仍 2/3：拖拽装货计数 + 数轴；分与合（`compose-ten`）仍无玩法 | **#9**（分与合教具 v1） |
| M-M14 | 家长面板 | ✅ | = | 口算门 + 雷达 6 轴 + 错因统计 + 导出/导入 + 7 天时长 + 防沉迷维持（smoke「板块 7 个」「导入 99 题/42 星生效」全过）；孩子侧 `ProgressView.vue` 新增错题本板块间接深化了报表 | 维护 |
| M-M15 | 奖励/成就 | ✅ | = | `data/achievements.js` 16 成就 + Toast/RoundSummary + 动效可关维持 | 维护（低优先扩徽章） |
| M-M16 | 性能/无障碍/离线 | ✅ | ◐→✅ | **Lighthouse 97/100/100**（R4 验收实测；`npm run test:round3` 复跑 98）；axe 0/0；离线 sw + offline-smoke；**路由级拆包已落地**（本次构建实见 Daily/Compare/Progress/Parent/各星球视图独立 chunk，index gzip 102.56 kB） | **#10** 回归维持（母题扩容后须重测） |

**数学小计：✅ 7 / ◐ 8 / ❌ 1（共 16 项）**（Round 4 审计：✅ 3 / ◐ 11 / ❌ 2）

---

## 3. 总览、增量与缺口

**总盘子：31 项 = ✅ 13（41.9%）/ ◐ 13（41.9%）/ ❌ 5（16.1%）。**
（Round 4 审计：✅ 4 / ◐ 20 / ❌ 7 → 本轮 **+9 个 ✅、-2 个 ❌**。）

**Round 4 交付核销（本次走读逐项确认，非引用验收记录）**：

| R4 目标 | 走读结论 |
|---|---|
| 识字状态机（L-M2） | ✅ 交付，五步内嵌 + 可按停自动衔接 + smoke 断言 |
| 错 3 笔示范 + 徽章（L-M3/L-M14） | ✅ 交付，`demoAfterMistakes=3` + 10 徽章 + smoke 断言 |
| 字库 500 + 懒加载 + 学习计划（L-M1/L-M13） | ✅ 交付，500 字/33 单元切包 + check:bundle 门禁 + planUnits/dailyGoal UI |
| 错题本 + adaptive（M-M10/M-M9） | ✅ 交付，questionId 级 + 重做出库 + 调度接线 QuizShell |
| seed PRNG + 日冒险 + 比较（M-M2/M-M12/M-M4） | ✅ 交付，mulberry32 全量替换 + 可复现压测 + 呼吸高亮 |
| Perf ≥95（L-M15/M-M16） | ✅ 交付，LH 99/97，gzip 静态服 + 拆包 + check:bundle 防回退 |
| R4 未指派项（L-M7 可视化 / M-M1 联动 / M-M14 深化 / M-M15 扩徽章） | 未做增量；除 M-M1 外底子本就 ✅，**M-M1 是唯一被连续两轮漏掉的 R4 目标** |

**Round 5 指派缺口（简报 §分工没接住的项）**：

1. **M-M1 全模块联动**：R4 未指派 → R5 仍未指派，连续两轮悬空。建议并入 #9（其交付面已覆盖多数出题视图）或明确写进 R6。
2. **L-M4 形近干扰**：R4 审计建议并入 R5，简报未列。工作量小（换干扰项取样策略），建议 #7 做小游戏时顺手带走。
3. **M-M6 配对/迷宫**：主计划标 R5，简报 P0 未列。#9 已背 4 项交付，建议明确顺延 R6 而不是默认漏掉。
4. **门禁 bug（归 #10）**：`check-round5.mjs` 母题探针因 `@/utils` 别名无法 import `wordProblems.js`（探针永远红）；`check:round5` npm 别名未进 `package.json`。两者不修，Round 5 收尾门禁无法判绿。

**给内容组（#4/#5/#6/#8）的门禁联动提醒**：扩容的同时须同步提高对应自检阈值——识字 `check-data.mjs`（当前 ≥500）、数学 `check-content.mjs`（当前 `MIN_TEMPLATES = 25`），否则 `check:round5` 绿了老门禁还是旧水位，回退无人报警。

---

## 4. 审计方法备注

- 内容计数：`node --input-type=module` 直接 import `characters.js / books.js / idioms.js / radicals.js`（500/5/20/18）+ `badges.js`（10）；母题数以 `check-content.mjs` 输出为准（34，`wordProblems.js` 已用 `@/utils` 别名，直接 import 会崩——这同时暴露了 check-round5 探针 bug）。
- 功能有无：按模块逐文件读源码 + 定向 grep（demoAfterMistakes/planUnits/mulberry32/wrongBook/retryWrong/pickNextQuestion/呼吸/compare/daily/形近/ageBand/visualDemos 等全库扫描）。
- 测试计数：`npm test` 在本分支 worktree 实跑一次（退出码 0），逐行摘录各套件通过数；`check-round4.mjs`（4/4 绿）与 `check-round5.mjs`（0/5 红，基线预期）各实跑一次。
- Lighthouse/axe 数字未在本轮重测，引用 `acceptance-log-round4.md` §6 实测值（识字 99/100/100、数学 97/100/100、axe 0/0）并已注明——Round 5 收尾重测归 #10。
