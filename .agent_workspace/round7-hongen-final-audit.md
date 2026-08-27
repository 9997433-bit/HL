Model slug: claude-fable-5
# Round 7 · 洪恩模块对标终验审计

> 审计人：Round 7 子代理 #2（fable）
> 审计基线：分支 `cursor/r7-module-audit-9f67`（自 `cursor/openmoji-integration-9f67` @ `46759f3`，即 Round 6 内容闭合 + Round 7 编排启动点）
> 审计日期：2026-08-27 · Node 22.14.0
> 方法：**逐文件重新走读源码**（不照抄 Round 6 结论），每条状态附文件路径证据；
> 内容体量用 `node --input-type=module` 实际 import 数据文件统计（数学侧走 `register('./scripts/alias-loader.mjs')` 解析 `@/` 别名）；
> `check:round6 / check:round7 / 识字 check:data / 数学 check:content` 在独立 worktree（`46759f3` 干净树）各实跑一次，退出码与逐行输出为准。

---

## 0. 基线门禁实测（46759f3，本机实跑）

| 门禁 | 结果 | 明细 |
|---|---|---|
| `check:round6` | **7/7 绿（exit 0）** | H1 字库 1820（≥1800）· H2 绘本 132（≥130）+ verifyBookCoverage 零越界 · H3 古诗 24（≥20）· H4 跟读路由/composable/smoke 三重接线（`/follow-read/:id?`）· H5 小游戏 5 款精确接线（不含 listen）· H6 母题 214（≥185） |
| `check:round7` | **0/7（预期红）** | H1 拍照识字未接线 · H2 形近干扰未接线 · H3 字源 65 < 200 · H4 年龄档联动 1/5 模块 · H5 逻辑小游戏未接线 · H6 aurora 主题未接线 · H7 GLOBAL-SUMMARY-REPORT 仍有 3 行 ❌ |
| 识字 `check:data` | **56/56 绿** | 输出统计行：`1820 字 / 99 单元 / 18 偏旁 / 132 本绘本（共 1121 页，557 个不重复用字）/ 60 个成语 / 65 个字有字源演变`；阈值已提到 ≥1800 字（L46）/ ≥130 本 / ≥20 首（L214） |
| 数学 `check:content` | **全部通过** | `应用题母题 214 个：28 类语义标签 / 42 种场景，一步 93 · 两步 86 · 进阶 35，每个母题各生成 2000 道`；`MIN_TEMPLATES = 185`（L55）已同步；种子化 reseed 逐字复现、比大小 3000 道、每日冒险 400 天可复现、自适应引擎弱项抽中 3719/4000 全绿 |

`check:round7` 0/7 是 Round 7 功能分支未合并时的**有意红灯**（探针契约先于交付落地），不代表退化；`check:round6` 7/7 表明 Round 6 六项内容硬门槛已在基线闭合。

**内容体量实测（import 数据文件直接计数）**：

| 指标 | 基线实测 | 主计划终点 | 达成率 | Δ vs R6 审计基线 |
|---|---|---|---|---|
| 识字字库 | **1820 字 / 99 单元**（`TOTAL_CHARACTERS`） | 1800 | **101%** | 1000 → 1820 |
| 分级绘本 | **132 本 / 1121 页 / L1–L6**，零越界 | 130 | **102%** | 30 → 132 |
| 成语 | **60 条** | 60+ | 100% | = |
| 古诗 | **24 首**（`POEMS`，`verifyPoemCoverage` 零越界） | 20 | **120%** | 0 → 24 |
| 小游戏（不含 listen） | **5 款**（maze/memory/spot/**spell/catch**，`data/games.js` 注册表） | ≥5 | **100%** | 3 → 5 |
| 应用题母题 | **214 个**（18 语义模板 × 10 场景皮肤 = 180 组合 + 34 手写；一步 93 · 两步 86 · 进阶 35） | 185 | **116%** | 118 → 214 |
| 字源动画 | 65 字（R7 门槛 ≥200，主计划终点 ≥800） | 800 | 8% | = |
| 数形演示 | 8 类（≥7 已达） | 维持 | 100% | = |
| 徽章 / 成就 | 识字 11 枚 / 数学 18 项 | 维持 | — | 徽章 10 → 11 |

---

## 1. 识字 App 对标表（L-M1 … L-M15）

图例：✅ 达标 / ◐ 有 MVP 但缺洪恩级深度 / ❌ 未实现。「Δ」列 = 相对 Round 6 审计的变化。

| 模块 | 洪恩能力 | 状态 | Δ | 实测证据（文件路径 + 关键事实） | Round 7 责任 |
|---|---|---|---|---|---|
| L-M1 | 1800 常用字分级 | ✅ | ◐→✅ | `apps/literacy-app/src/data/characters.js`：`TOTAL_CHARACTERS = 1820`、**99 个单元**（一级字表序，8228541 收口）；`check-data.mjs` L46 阈值提到 ≥1800、L101 共享字库基线 ≥1800；懒加载管线维持（`char-index.js` 主包索引 + `chars/` 按单元切包），`check-bundle.mjs` L24 首屏预算 420 KB 门禁常驻。check:round6 H1 绿 | 维护（体量项就此清账） |
| L-M2 | 认-读-写-玩闭环（状态机） | ✅ | = | `apps/literacy-app/src/views/CharDetailView.vue`：`PHASES`（L58）intro→trace→listen→quiz→reward，自动衔接走 `pendingNext`（文件头注释 L9：自动前进可按停，WCAG 2.2.1） | 维护 |
| L-M3 | 笔顺+描红判定 + 错3次示范 | ✅ | = | `apps/literacy-app/src/components/HanziStrokeBox.vue`：`demoAfterMistakes: 3`（L32），同笔连错 3 次触发 `demonstrateStroke()`（L182-183）慢放示范再接回测验 | 维护 |
| L-M4 | 听音识字 + 形近干扰 | ◐ | = | `apps/literacy-app/src/views/ListenGameView.vue`：干扰项**仍是随机取样** `shuffle(list.filter(...))`（check:round7 H2 探针 L48 显式反查此模式，当前红）；全库 grep `confusable/形近` 零命中，无 `data/similar-chars.js`。R4/R5/R6 三轮审计连续预警后 **R7 终于立项** | **#5** `cursor/r7-literacy-distractors-9f67` |
| L-M5 | 130 本分级绘本 | ✅ | ◐→✅ | `apps/literacy-app/src/data/books.js`：**132 本 / 1121 页 / L1–L6**（import 实测），`verifyBookCoverage()` 零越界；「手写核心 + 脚本生成」两摞结构（9d46b70）+ `book-index.js` 轻量索引；`check:data` 阈值提到 130（827c408）。check:round6 H2 双绿 | 维护（社区投稿格式文档 → R8 备忘） |
| L-M6 | 800+ 字源互动 | ◐ | = | `apps/literacy-app/src/data/etymology.js` + `etymology-index.js`：**65 字**；管线成熟（`utils/etymologySketch.js` 形状 DSL + `EtymologyStage.vue` GSAP 演变 + 路由 `/etymology/:char`）。check:round7 H3 红（65 < 200，探针读 `ETYMOLOGY_CHARS`） | **#5**（65→200+；200→800 归 R8） |
| L-M7 | 记忆曲线复习 | ✅ | = | `apps/literacy-app/src/utils/srs.js`（FSRS-lite）+ `stores/progress.js` 调度 + `ParentView.vue` L311 记忆强度热力图 | 维护 |
| L-M8 | 成语/古诗国学 | ✅ | ◐→✅ | 成语：`data/idioms.js` **60 条** + `idiom-index.js` 懒加载 + 路由 `/idioms`、`/idioms/:id`。古诗：`data/poems.js` **24 首** + `poem-index.js`（`TOTAL_POEMS` 与语料一致性校验 check:data L217）+ `verifyPoemCoverage()` 零越界 + 路由 `/poems`、`/poems/:id`；`PoemDetailView.vue` 三件套齐：逐句朗读（L83 逐句高亮）+ 点字 peek（L102-104 报读音释义）+ 拼音层（L174 随 `settings.showPinyin`）。check:round6 H3 绿 | 维护 |
| L-M9 | AI 学伴/跟读评测 | ✅ | ❌→✅ | `views/FollowReadView.vue` + 路由 `/follow-read/:id?`（`/speech` 重定向）；`composables/useSpeechEval.js` **三档降级**（L9 recognition：`SpeechRecognition` 逐字比对 → L215 recording：`getUserMedia` 录音回放 → listen-only），隐私提示（L16 在线识别如实告知）；`utils/speechEval.js` 文本对齐评分；smoke `ROUND6_H4_SMOKE`（`scripts/smoke.mjs` L1593 跟读入口与降级提示断言）。check:round6 H4 三重接线绿。我方目标口径（Web Speech 比对 + 录音降级）成立 | 维护（音素/声调级评分 + AI 学伴对话面 → R8 备忘） |
| L-M10 | 拍照识字 | ❌ | = | 全库 grep `tesseract / ocr / camera / photo` 在识字 src 与 package.json **零命中**；check:round7 H1 红（探针认 `CameraOcrView.vue` / `utils/ocr.js` / `useOcr.js` / package.json 依赖任一） | **#4** `cursor/r7-literacy-ocr-9f67` |
| L-M11 | 动画儿歌/IP | ✅ | = | `components/MascotCompanion.vue` 吉祥物陪跑 + `utils/sfx.js` 音效 + `data/unit-stories.js` 单元剧情 + `LearnView.vue` 地图叙事（灰显/剧情/解锁过渡）维持。**新发现**：手写剧情仍 58 条（`TOTAL_UNIT_STORIES = 58`），u59–u99 新单元走 `unitTeaser()` 兜底模板——不破坏口径（兜底由设计注释 L4-8 说明），但深度打磨记备忘 | 维护（u59–u99 手写剧情 + 儿歌内容 → R8 备忘） |
| L-M12 | 字迷宫/跑酷等小游戏 ≥5 | ✅ | ◐→✅ | `data/games.js` 注册表 **6 款**：listen + maze/memory/spot + **spell（拼字）/ catch（接字）**；不含 listen **5 款**；路由 `/games/maze|memory|spot|spell|catch` 全接线（router L46-74），`SpellGameView.vue`/`CatchGameView.vue` 在场，smoke+axe 已覆盖两款新游戏（fe4b33f）。check:round6 H5 绿（注册表逐款精确接线） | 维护 |
| L-M13 | 家长控制/防沉迷 | ✅ | = | `views/ParentView.vue` + `stores/settings.js`/`progress.js`：口算门 + 导出/导入 + 每日时长 + `planUnits` 自选单元 + `dailyGoal` 每日新字上限 | 维护 |
| L-M14 | 奖励/徽章体系 | ✅ | = | `data/badges.js` **11 枚**（R6 基线 10）+ `BadgeShelf.vue` + `stores/dailyQuest.js` 每日任务 | 维护 |
| L-M15 | 性能/无障碍/离线 | ◐ | = | A11y/离线稳：axe 20 路由 + 3×22 交互态 0/0、sw 预缓存 + offline-smoke、首屏 JS gzip 108,149 B（acceptance-log-round5b §1）、`check-bundle` 420 KB 预算常驻。**Perf 仍未定标**：最近一次实测为 R5B LH 13.4.1 移动端 **识字 Perf 87 < 90（自判 FAIL）**；R6 闭合（92a03f8 回归门禁）只复跑内容门禁未重测 LH，acceptance-log-round6 §2 回填模板仍空。按测量驱动原则维持 ◐ | **#9** `cursor/r7-perf-lighthouse-9f67` |

**识字小计：✅ 11 / ◐ 3 / ❌ 1（共 15 项）**（Round 6 审计：✅ 6 / ◐ 7 / ❌ 2）

---

## 2. 数学 App 对标表（M-M1 … M-M16）

| 模块 | 洪恩能力 | 状态 | Δ | 实测证据（文件路径 + 关键事实） | Round 7 责任 |
|---|---|---|---|---|---|
| M-M1 | 3–12 岁 L1–L5 年龄档 | ◐ | = | `rg -l ageBand apps/math-app/src` 仍只命中 3 文件：`stores/settings.js`（定义）、`ParentView.vue`（选择器）、`ArithmeticView.vue`（唯一学习模块消费方）。check:round7 H4 红：**1/5 模块**（探针点名 number-sense/geometry/logic/word-problems/sudoku/arithmetic 六文件需 ≥5 个读 `ageBand`）。R4→R5→R6 三轮悬空后 **R7 终于立项** | **#6** `cursor/r7-math-ageband-9f67` |
| M-M2 | 1000+ 互动/无限题 | ✅ | ◐→✅ | `src/utils/random.js` mulberry32 + `questionId()`（seed 写进题目 id）；`check-content.mjs` **`MIN_TEMPLATES = 185`（L55）已同步**，每母题压测 2000 道（L82）+ reseed 逐字复现（L144-156）。**214 母题 × 种子参数 = 事实无限题**，R6 审计悬置的「主计划 ≥300 字面口径」由「母题 ≥185 门禁 + 每母题 2000 道压测」等价覆盖——#10 全局报告应把该等价判定写明留档 | 维护（等价判定入 GLOBAL-SUMMARY → #10） |
| M-M3 | 185 应用题母题 | ✅ | ◐→✅ | `apps/math-app/src/data/wordProblems.js`：**214 个**（`WORD_PROBLEM_COUNT`；`SEMANTIC_TEMPLATES` 18 × `SCENE_SKINS` 10 = 180 组合 + 34 手写；一步 93 · 两步 86 · 进阶 35，import 实测）。R6 审计留的「类目多样性复核」已可闭合：check:content 输出 **28 类语义标签 / 42 种场景**。check:round6 H6 绿（569105a 交付） | 维护 |
| M-M4 | 数感/比较/运算 | ✅ | = | 比较 `/compare` + `data/compare.js`（比大小 3000 道判定/复现校验绿）；竖式 `modules/arithmetic/ColumnArithmeticView.vue`（进位/借位分步）+ 路由 `/column-arithmetic`；数感/四则维持 | 维护 |
| M-M5 | 几何/空间 + 七巧板 | ✅ | = | `modules/geometry/GeometryView.vue` 5 种题型 + `TangramView.vue` 七巧板（路由 `/tangram`） | 维护 |
| M-M6 | 逻辑/规律 + 配对/迷宫 | ◐ | = | `modules/logic/LogicView.vue` 5 种规律题维持；`rg -il 'memory|maze' apps/math-app/src/modules` **零命中**，数学侧配对/迷宫仍无。check:round7 H5 红（探针要求 math router 出现 pair/memory/maze/配对/迷宫 任一路由）。R5/R6 两轮顺延后 **R7 终于立项**（识字侧 MemoryGame/MazeGame 壳可迁移） | **#7** `cursor/r7-math-logic-games-9f67` |
| M-M7 | 数独专项 | ✅ | = | 4/6/9 三档 + 唯一解门禁 + 提示 + 键盘维持（`modules/sudoku/`） | 维护 |
| M-M8 | 数形结合演示 | ✅ | = | `data/visualDemos.js` **8 类**三段契约（object→visual→equation + narration）+ `VisualDemosView.vue` 跳过/重播/逐步，check:content「数形演示 8 类：实物/图形/算式/三段旁白齐全」绿 | 维护 |
| M-M9 | 自适应难度 | ✅ | = | `src/core/engine/adaptive.js`：`pickNextQuestion`（L134）+ `createAdaptiveEngine`（L217）；check:content 引擎探针绿（弱项抽中 3719/4000、错题优先 2868:1132、升降档与 EMA 一致） | 维护 |
| M-M10 | 错题本 | ✅ | = | `stores/progress.js`：`wrongBookKey`（L33）questionId 级记录 + `wrongBook`（L81）+ 合并迁移（L186）；`WrongBook.vue` 重练流程 | 维护 |
| M-M11 | 计算专题/速算 | ✅ | = | 口算闯关 `ArithmeticView.vue`（连击加成）+ 竖式 `ColumnArithmeticView.vue`；**R6 #9 增量**：`/sprint` 速算冲刺路由（router L45-48，`props: { mode: 'sprint' }` 复用 ArithmeticView）+ `modules.js` L119 `sprint` 专题入口登记 | 维护 |
| M-M12 | 剧情关卡地图 + 日冒险 | ✅ | = | **R6 #9 深化落地**：`data/unit-stories.js` 章节契约 `chapterNo/chapterName/story/unlockHint/unlockLine`（L23-26「第一章·起航云海」等）+ `modules.js` L94「生活行星」+ `HomeView.vue` `unlock-scene` 过场（L352）+ 呼吸高亮；日冒险 `data/daily.js` 400 天可复现（check:content 绿） | 维护 |
| M-M13 | 互动教具 ≥3 | ✅ | = | 拖拽计数（NumberSenseView）+ 数轴（ArithmeticView）+ 分与合 `ComposeTenView.vue`（路由 `/compose-ten`） | 维护 |
| M-M14 | 家长面板 | ✅ | = | 口算门 + 雷达 + 错因 + 导出/导入 + 时长 + 年龄档选择器（`modules/parent/ParentView.vue`） | 维护 |
| M-M15 | 奖励/成就 | ✅ | = | `data/achievements.js` **18 项** + Toast/RoundSummary + 动效可关 | 维护 |
| M-M16 | 性能/无障碍/离线 | ◐ | = | A11y/离线稳：axe 0/0、sw + offline-smoke、首屏 gzip 102,651 B、路由级拆包维持。**Perf 同 L-M15**：最近实测 R5B LH 13.4.1 **数学 Perf 84 < 90（自判 FAIL）**，R6 未重测。维持 ◐ 待 #9 定标冲线 | **#9**（同 L-M15） |

**数学小计：✅ 13 / ◐ 3 / ❌ 0（共 16 项）**（Round 6 审计：✅ 11 / ◐ 5 / ❌ 0）

---

## 3. 总览与增量

**总盘子：31 项 = ✅ 24（77.4%）/ ◐ 6（19.4%）/ ❌ 1（3.2%）。**

| 轮次审计 | ✅ | ◐ | ❌ |
|---|---|---|---|
| Round 4 | 4 | 20 | 7 |
| Round 5 | 13 | 13 | 5 |
| Round 6 | 17 | 12 | 2 |
| **Round 7 基线（本次）** | **24** | **6** | **1** |

状态变化明细（相对 R6 审计，共 7 项上移）：

- **◐→✅（6 项）**：L-M1（1000→1820 字/99 单元）、L-M5（30→132 绘本）、L-M8（+24 古诗三件套）、L-M12（3→5 款小游戏）、M-M2（MIN_TEMPLATES 185 门禁 + 无限题等价成立）、M-M3（118→214 母题，28 类语义标签）。
- **❌→✅（1 项）**：L-M9 跟读评测（FollowReadView + useSpeechEval 三档降级 + smoke 三重接线）。
- **持平 ◐（6 项）**：L-M4 形近干扰、L-M6 字源 65 字、L-M15/M-M16 Perf 待定标、M-M1 年龄档联动、M-M6 数学配对/迷宫——**六项全部已被 Round 7 简报立项**（见 §4），这是四轮以来第一次「◐ 存量 = 在途任务」完全对齐。
- **仅剩 ❌（1 项）**：L-M10 拍照识字（#4 本轮交付，主计划本就排 R7）。

---

## 4. Round 7 子代理交付后预期状态与 R8 归属

> 对照 `.agent_workspace/ROUND7-BRIEF.md` §子代理分工。#1–#3 为架构/审计/验收支撑，不改对标状态，此处审 #4–#10。审计时点各分支进度：#8 已有首个提交（ffc1ea5 shared aurora theme）、#10 已有报告初稿（c30e984），其余功能分支尚在 46759f3。

### #4 `cursor/r7-literacy-ocr-9f67`（Tesseract 拍照识字）

- **交付后预期**：L-M10 ❌→**✅**（对标表最后一个 ❌ 清零）。check:round7 H1 探针契约：router 含 `camera|ocr|photo` 或存在 `views/CameraOcrView.vue`，且 `utils/ocr.js` / `composables/useOcr.js` / package.json `tesseract` 依赖任一在场；ROUND7-ACCEPTANCE 还要求 smoke 断言。离线 wasm 须进 sw 预缓存清单，注意 `check-bundle` 420 KB 首屏预算——tesseract 必须懒加载。
- **仍缺项归 R8**：识别准确率量化评测（探针只验接线不验精度）。

### #5 `cursor/r7-literacy-distractors-9f67`（形近干扰 + 字源 200+）

- **交付后预期**：L-M4 ◐→**✅**（连续四轮预警项闭环）。H2 探针**双条件**：出现 `similar/confusable/形近/similar-chars.js` 语义 **且** `ListenGameView.vue` 里不再匹配 `shuffle(list.filter`——只加字段不改取样逻辑过不了门禁。L-M6 保持 ◐ 但 65→**200+**（H3 读 `etymology-index.js` 的 `ETYMOLOGY_CHARS`，交付物必须同步索引文件而不只 `etymology.js`）。
- **仍缺项归 R8**：字源 200→**800**（主计划终点，纯内容管线工作）；CharDetailView quiz 干扰项若本轮未同步换用形近池，需 R8 复核（H2 探针把 CharDetailView 源码计入匹配面，但语义命中任一文件即绿，存在只改 Listen 不改 quiz 的漏网可能）。

### #6 `cursor/r7-math-ageband-9f67`(年龄档全模块联动)

- **交付后预期**：M-M1 ◐→**✅**（三轮悬空项闭环）。H4 探针契约：number-sense / geometry / logic / word-problems / sudoku / arithmetic 六个视图文件中 **≥5 个**匹配 `ageBand|AGE_BAND`。当前只有 ArithmeticView（1/5）。年龄档应驱动出题参数（数域/步数/干扰项数）而非只读不用——ROUND7-ACCEPTANCE 口径是「读 settings.ageBand」，#3 验收如能加行为断言更稳。
- **仍缺项归 R8**：技能图谱可视化（主计划 M-M1 的「技能图谱」半句，历轮未展开）。

### #7 `cursor/r7-math-logic-games-9f67`（逻辑配对/迷宫）

- **交付后预期**：M-M6 ◐→**✅**。H5 探针：math router 出现 `pair|memory|maze|配对|迷宫` 任一路由 + `LogicView.vue` 在场；简报另要求 Canvas + reduced-motion 降级 + smoke。识字侧 `MemoryGameView.vue`/`MazeGameView.vue` 壳可迁移（R6 审计已给出该路径）。
- **仍缺项归 R8**：无（该项就此清账）。新游戏须登记 `modules.js` 专题入口，否则首页不可达（探针不查这一层）。

### #8 `cursor/r7-theme-aurora-9f67`（第 4 主题 + 四主题对比度）

- **交付后预期**：不改 L-M/M-M 对标行（主题属差异化 D-4 与走查 C-5 支撑），但解锁 check:round7 H6（双 App `stores/settings.js` + `shared/styles/design-tokens.css` 出现 aurora 主题接线）。已有首提交 ffc1ea5。四主题对比度走查留档支撑 L-M15/M-M16 的 a11y 侧不退化。
- **仍缺项归 R8**：若对比度走查发现 serious 级问题未在本轮修完，余项带单归 R8。

### #9 `cursor/r7-perf-lighthouse-9f67`（Perf 三板斧冲 ≥90）

- **交付后预期**：L-M15 / M-M16 ◐→**✅**（前提：锁定 Lighthouse CLI 版本消除 96 vs 87/84 漂移 + 双 App Perf ≥90 实测留档 acceptance-log-round7）。这是仅剩 6 个 ◐ 里权重最高的两项——A11y/离线子项四轮全绿，只差 Perf 定标数。
- **仍缺项归 R8**：主计划 A 层口径是 **LH ≥95**（ROUND7 门禁只到 ≥90）；若定标后落在 90–94，「冲 95」归 R8。

### #10 `cursor/r7-global-report-9f67`（GLOBAL-SUMMARY + 终验打包）

- **交付后预期**：H7 绿——现存 `.agent_workspace/GLOBAL-SUMMARY-REPORT.md` 是 **Round 3 框架版**，3 行 ❌（L85-87：LH A11y 87/93、axe critical 1/3、axe serious 58/5）全是被 R4–R6 修复覆盖的旧数，须按最新实测刷新为无 ❌ 全表。已有初稿 c30e984（分支带 `-c17e` 后缀，合并时注意与简报登记的分支名对齐）。
- **报告须写明的两个口径判定**（本审计移交）：① M-M2「≥300 题」字面口径 = 母题 ≥185 门禁 + 每母题 2000 道压测的等价替代；② L-M9 达标口径 = 「Web Speech 比对 + 录音降级」v1（洪恩「AI 学伴」的对话面明示为 R8 备忘而非缺陷）。
- **仍缺项归 R8**：对外声明证据包若只索引不附原始 LH JSON/axe 输出，取证完备性归 R8。

### R8 归属清单（本轮预判汇总）

| # | 项 | 来源 |
|---|---|---|
| 1 | L-M6 字源 200→800（主计划终点） | #5 只到 200+ |
| 2 | Perf 冲 95（主计划 A 层 ≥95 vs R7 门禁 ≥90） | #9 定标结果决定 |
| 3 | L-M9 音素/声调级评分 + AI 学伴对话面 | R6 审计既有备忘 |
| 4 | L-M11 儿歌/音乐内容 + u59–u99 手写单元剧情（现走兜底模板） | 本轮新发现 |
| 5 | L-M5 绘本社区投稿格式文档 | R6 审计既有备忘 |
| 6 | L-M10 OCR 识别精度量化 / CharDetailView quiz 形近池复核 | #4/#5 交付面之外 |
| 7 | M-M1 技能图谱可视化 | 主计划半句未展开 |
| 8 | 四主题对比度余项 / 证据包原始数据完备性 | #8/#10 视交付情况 |

---

## 5. 门禁联动提醒（发给 #3/#9/#10 与功能组）

1. **H2 是反向探针**：`check-round7.mjs` L48 要求 `ListenGameView.vue` 中**不得再出现** `shuffle(list.filter` 字样。#5 若保留旧函数做兜底注释掉，探针会误红（`stripComments` 未在此探针使用）；直接删除或改名取样函数最稳。
2. **H3 读的是索引不是语料**：探针 import `etymology-index.js` 的 `ETYMOLOGY_CHARS`（L58），#5 扩容若只改 `etymology.js` 不同步索引，功能好门禁照红——与 R6「H3/H4 路径约定」同类陷阱。
3. **H4 点名六文件**：探针白名单是六个具体视图路径（L66-73），把 ageBand 接进 composable/engine 而不在视图源码出现字面量的话不计数；至少在 5 个视图里显式读 `settings.ageBand`。
4. **H7 的 ❌ 计数是全文正则**：`(\|[^|\n]*❌[^|\n]*\|)`——#10 刷新报告时，历史章节里作为「修复前旧数」引用的 ❌ 也会被计入；旧数请改用文字描述或 ~~删除线~~，别留表格单元格里的 ❌。
5. **老门禁水位已对齐，勿回退**：识字 `check-data.mjs` ≥1800 字 / ≥130 本 / ≥20 首、数学 `MIN_TEMPLATES = 185` 均已在基线收口（R6 审计 §5-1 预警的滞后问题本轮已消除）；R7 合并时保持 `check:round6` 7/7 是 G2 硬门槛。
6. **Perf 定标是 L-M15/M-M16 转 ✅ 的唯一闸门**：acceptance-log-round6 §2 回填模板至今全空，R7 必须由 #9/#10 在 acceptance-log-round7 落 LH 版本号 + 双 App 三项分数，否则本审计维持 ◐ 判定不动。

---

## 6. 审计方法备注

- 内容计数：`node --input-type=module` 直接 import `characters.js（1820/99）/ books.js（132 本 1121 页，verifyBookCoverage()=0）/ poems.js（24，verifyPoemCoverage()=0）/ idioms.js（60）/ games.js（6 款，非 listen 5）/ etymology.js（65）/ badges.js（11）/ unit-stories.js（TOTAL_UNIT_STORIES=58）`；数学侧经 `register('./scripts/alias-loader.mjs')` import `wordProblems.js（214；SEMANTIC_TEMPLATES 18 × SCENE_SKINS 10；steps 1/2/3 = 93/86/35）/ visualDemos.js（8）/ achievements.js（18）`。
- 门禁实跑：`check:round6`（7/7，exit 0）、`check:round7`（0/7，exit 1，预期红）、识字 `npm run check:data`（56/56）、数学 `npm run check:content`（全绿，含每母题 2000 道压测与自适应引擎探针），均在 `46759f3` 干净 worktree 执行。
- 功能有无：逐文件读源码 + 定向 grep（PHASES/pendingNext、demoAfterMistakes、confusable/形近/similar、SpeechRecognition/MediaRecorder/getUserMedia、tesseract/ocr/camera、planUnits/dailyGoal、ageBand、MIN_TEMPLATES、chapterName/unlockHint/unlock-scene、pickNextQuestion、wrongBookKey、sprint、aurora 全库扫描）；路由以 `router/index.js` 实际注册为准（识字 24 条含重定向与兜底、数学 17 条）。
- Lighthouse/axe 未在本轮重测：引用 `acceptance-log-round5b.md` §1 实测记录（LH 13.4.1：识字 87 / 数学 84 FAIL；axe 20 路由 + 3×22 状态全零；gzip 108,149 / 102,651 B）；R6 闭合点（92a03f8）确认未重测 LH，故 L-M15/M-M16 维持 ◐ 并把定标责任交 #9。
- Round 7 在途进度快照（审计时点）：#8 ffc1ea5、#10 c30e984 已起步，#4/#5/#6/#7/#9 分支仍在基线 46759f3。
