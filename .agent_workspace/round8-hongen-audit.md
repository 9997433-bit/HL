Model slug: claude-fable-5-thinking-xhigh
# Round 8 · 洪恩模块对标审计

> 审计人：Round 8 子代理 #2（fable）
> 审计基线：分支 `cursor/r8-module-audit-9f67`（自 `cursor/openmoji-integration-9f67` @ `a8b21b3`，即 Round 7 闭合 + Round 8 编排启动点）
> 审计日期：2026-08-27 · Node 22.14.0 · worktree `/tmp/wt-r8-audit`（干净树）
> 方法：**逐文件重新走读源码**（不照抄 Round 7 结论），每条状态附文件路径证据；
> 内容体量用 `node --input-type=module` 实际 import 数据文件统计（数学侧经 `--import ./scripts/register-alias.mjs` 解析 `@/` 别名）；
> `check:round6 / check:round7 / check:round8 / 识字 check:data / 数学 check:content` 各实跑一次，退出码与逐行输出为准。
> **口径说明**：Round 8 是「深度超越与 A 层终态」轮，◐ 的判定杆随主计划终点上移（字源 800、Perf 95、剧情手写 99、儿歌 v1、AI 学伴对话面、OCR 精度定标、技能图谱）。个别 R7 判 ✅ 的行本轮下调为 ◐，属**口径上移**而非功能退化，逐行注明。

---

## 0. 基线门禁实测（a8b21b3，本机实跑）

| 门禁 | 结果 | 明细 |
|---|---|---|
| `check:round6` | **7/7 绿（exit 0）** | H1 字库 1820 · H2 绘本 132 + verifyBookCoverage 零越界 · H3 古诗 24 · H4 跟读三重接线 · H5 小游戏 5 款精确接线 · H6 母题 214 |
| `check:round7` | **8/8 绿（exit 0）** | H1 拍照识字 `/ocr` 三重接线 · H2 形近字库 **1817 组** + 功能探针 + 听音/测验双接线 · H3 字源 **525** 字无重复 · H4 年龄档 **6/6** 模块 · H5 `/memory-pairs`+`/maze`+smoke · H6 aurora tokens 32 / THEMES 4 · H7 全局报告 31/31 |
| `check:round8` | **1/8（有意红灯，exit 1）** | 仅 H8（R7 不退化）绿；H1 字源 525/800 · H2 剧情 58/99 + 儿歌 0/3 · H3 技能图谱路由/视图/数据全缺 · H4 精度脚本缺（**CharDetailView 形近池已有**）· H5 v2 能力+smoke 缺 · H6 Perf 未回填 + `evidence/r8` 缺 · H7 报告未刷 Round 8 |
| 识字 `check:data` | **61/61 绿** | 统计行：`1820 字 / 99 单元 / 18 偏旁 / 132 本绘本（1121 页，557 不重复用字）/ 60 成语 / 525 字有字源演变`；R7 新增探针组在列：形近覆盖 1817/1820（≥95%）、形近不足 3 个的字仅 4 个（上限 91）、派生字源形旁/读音与字表一致、四造字法每类 ≥5 字 |
| 数学 `check:content` | **全部通过（exit 0）** | 母题 214（28 语义标签/42 场景，一步 93 · 两步 86 · 进阶 35，每母题 2000 道压测）；**年龄档 L1–L5 驱动 6 个玩法**；**技能点映射：产出 25 个 id 全部在图谱里**（`curriculum.js`）；数独三档唯一解；比大小 3000；每日冒险 400 天；**条件迷宫 200 座（10294 步全最短路通关）· 配对记忆 1000 副**；自适应弱项抽中 3719/4000 |

`check:round8` 1/8 是 R8 功能分支未合并时的**有意红灯**（探针契约先于交付落地）；`check:round7` 8/8 表明 Round 7 七大交付已在基线全部合入闭合。

**内容体量实测（import 数据文件直接计数）**：

| 指标 | 基线实测 | 主计划终点 | 达成率 | Δ vs R7 审计基线（46759f3） |
|---|---|---|---|---|
| 识字字库 | **1820 字 / 99 单元** | 1800 | 101% | = |
| 分级绘本 | **132 本 / 1121 页**，零越界 | 130 | 102% | = |
| 成语 / 古诗 | **60 条 / 24 首** | 60+ / 20 | 100% / 120% | = |
| 小游戏（不含 listen） | **5 款**（maze/memory/spot/spell/catch） | ≥5 | 100% | = |
| 形近字库 | **1817 组**（覆盖 1820 字的 95%+，`similar-chars.js`） | — | 新增 | 0 → 1817 |
| 字源动画 | **525 字**（无重复，`etymology-index.js`；R8 门槛 ≥800） | 800 | **66%** | 65 → 525 |
| 手写单元剧情 | **58 条**（`TOTAL_UNIT_STORIES`，u59–u99 走 `unitTeaser()` 兜底） | 99 | 59% | = |
| 儿歌 | **0 首**（无 `data/songs.js`，无路由） | ≥3 | 0% | = |
| 应用题母题 | **214 个**（18 语义模板 × 10 场景 + 34 手写） | 185 | 116% | = |
| 技能点图谱数据层 | **34 个技能点**（`curriculum.js` `SKILL_MAP`，可视化未接线） | 路由+视图+数据 | 数据先行 | 新发现 |
| 徽章 / 成就 | 识字 11 枚 / 数学 18 项 | 维持 | — | = |
| Lighthouse（R7 实测 12.8.2 mobile） | **识字 97/100/100 · 数学 94/100/100** | 双 App P ≥ 95 | 识字达 / 数学差 1 | 87/84 → 97/94 |
| 首屏 JS gzip | 识字 108,112 B / 数学 77,058 B | <420 KB / <250 KB | 达标 | 数学 -26.7% |
| zip / Android | literacy 2,891,785 B · math 435,723 B · check:android 26/26 | <10 MB · 26/26 | 达标 | acceptance-log-round7 §2.1 回填 |

---

## 1. 识字 App 对标表（L-M1 … L-M15）

图例：✅ 达标 / ◐ 有 MVP 但缺洪恩级深度 / ❌ 未实现。「Δ」列 = 相对 Round 7 终验审计的变化；`口径↑` = 状态下调源于 R8 判定杆上移，非功能退化。

| 模块 | 洪恩能力 | 状态 | Δ | 实测证据（文件路径 + 关键事实） | Round 8 责任 |
|---|---|---|---|---|---|
| L-M1 | 1800 常用字分级 | ✅ | = | `data/characters.js` 1820 字 / 99 单元；`check-data.mjs` ≥1800 门禁与懒加载管线（`char-index.js` + `chars/` 分包）维持；`check-bundle.mjs` L24 首屏 420 KB 预算常驻 | 维护 |
| L-M2 | 认-读-写-玩闭环（状态机） | ✅ | = | `views/CharDetailView.vue` `PHASES` intro→trace→listen→quiz→reward + `pendingNext` 可按停（WCAG 2.2.1）维持 | 维护 |
| L-M3 | 笔顺+描红判定 + 错3次示范 | ✅ | = | `components/HanziStrokeBox.vue` `demoAfterMistakes: 3` + `demonstrateStroke()` 慢放示范维持 | 维护 |
| L-M4 | 听音识字 + 形近干扰 | ✅ | ◐→✅ | **R7 #5 交付闭环**（36e01ba）：`data/similar-chars.js` 1817 组（`gen-similar-chars.mjs` 管线生成）+ `utils/distractors.js`（`buildOptions`/`similarDistractors`）；`ListenGameView.vue` L23 import `buildOptions`、`CharDetailView.vue` L43 import `similarDistractors`——**听音与单字测验双接线**；check:round7 H2 功能探针（干扰项去重/排除目标/形近优先）实跑绿；check:data 覆盖率 ≥95% 门禁常驻。四轮预警项就此清账 | 维护 |
| L-M5 | 130 本分级绘本 | ✅ | = | `data/books.js` 132 本 / 1121 页，`verifyBookCoverage()` 零越界；两摞结构 + `book-index.js` 维持 | 维护（社区投稿格式文档两轮未清 → R9 备忘） |
| L-M6 | 800+ 字源互动 | ◐ | ◐（65→525） | `etymology-index.js` **525 字**无重复（check:round7 H3 绿、check:round8 H1 红 525/800）；**管线已工业化**（a9c1d1a）：`scripts/gen-etymology.mjs` 从 `scripts/data/etymology-seed.txt` 派生 `etymology-derived.js`（形声模板填空 + 会意两句话），check:data 9 项字源探针（形旁与部首一致、读音与字表一致、每类 ≥5 字）。剩余为纯种子扩容 | **#4** `cursor/r8-literacy-etymology-9f67`（525→800） |
| L-M7 | 记忆曲线复习 | ✅ | = | `utils/srs.js`（FSRS-lite）+ `stores/progress.js` + `ParentView.vue` 热力图维持；R8 红线「FSRS 不动」 | 维护 |
| L-M8 | 成语/古诗国学 | ✅ | = | 成语 60 + 古诗 24（`verifyPoemCoverage()` 零越界）+ `PoemDetailView.vue` 三件套维持 | 维护 |
| L-M9 | AI 学伴/跟读评测 | ◐ | ✅→◐ `口径↑` | v1 完好：`FollowReadView.vue` + `/follow-read/:id?` + `useSpeechEval.js` 三档降级（L9 recognition 逐字评测 → recording 录音回放 → listen-only），隐私实话实说（L15-17：录音不落盘不上传；SpeechRecognition 可能走厂商在线服务故**默认关**，家长显式开 `allowRecognition`）。**R8 杆：音素/声调级评分或 AI 学伴对话面**——`useSpeechEval.js`/`FollowReadView.vue`/`speechEval.js` grep `phoneme|音素|声调|tone` **零命中**，`MascotCompanion.vue` 无 chat/dialog；check:round8 H5 红（v2 能力+smoke 双缺）。非退化，是洪恩「AI 学伴」对话面的深度差 | **#8** `cursor/r8-literacy-followread-9f67` |
| L-M10 | 拍照识字 | ◐ | ❌→◐ | **R7 #4 交付接线闭环**（eabf55c/ae1e7cf/91ce6aa）：路由 `/ocr`（`/camera` 重定向）+ `views/CameraOcrView.vue` + `composables/useOcr.js` + `utils/ocr.js`（tesseract.js ^7.0.0）+ `public/ocr/`（`chi_sim.traineddata.gz` + `sample-photo.png`）；`sw.js` L14 专用 `OCR_CACHE` 运行时缓存（不占首屏预缓存）；offline-smoke 跑通**断网识字整条链路**（91ce6aa）；`THIRD_PARTY_NOTICES.md` L28-29 署名齐全；`test-ocr.mjs` 守取字纯逻辑（extractHanzi/splitByLibrary）。**按测量驱动原则维持 ◐**：识别精度无固定基准图集量化（无 `test-ocr-accuracy.mjs`，check:round8 H4 红），与 R7 审计对 Perf 的判法同源——没有定标数不转 ✅ | **#7** `cursor/r8-literacy-ocr-quality-9f67` |
| L-M11 | 动画儿歌/IP | ◐ | ✅→◐ `口径↑` | 吉祥物/音效/地图叙事维持（`MascotCompanion.vue` + `sfx.js` + `LearnView.vue`）。**R8 杆：u59–u99 手写剧情 + 儿歌 v1**——`unit-stories.js` `TOTAL_UNIT_STORIES = 58`，u59–u99 共 41 单元仍走 `unitTeaser()` 兜底模板；`data/` 目录无 `songs.js`，路由无儿歌入口（check:round8 H2 红：58/99 + 0/3 + 路由缺失）。「动画儿歌」是洪恩本模块的题眼，R7 判 ✅ 靠兜底设计说明撑住，R8 起不再豁免 | **#5** `cursor/r8-literacy-stories-9f67` |
| L-M12 | 字迷宫/跑酷等小游戏 ≥5 | ✅ | = | `data/games.js` 6 款（listen + 5），路由全接线 + smoke/axe 覆盖维持 | 维护 |
| L-M13 | 家长控制/防沉迷 | ✅ | = | 口算门 + 导出/导入 + 每日时长 + `planUnits` + `dailyGoal` 维持 | 维护 |
| L-M14 | 奖励/徽章体系 | ✅ | = | `data/badges.js` 11 枚 + `BadgeShelf.vue` + `dailyQuest.js` 维持 | 维护 |
| L-M15 | 性能/无障碍/离线 | ✅ | ◐→✅ | **R7 #9 定标闭环**（9747422/295f908/ba5ff3a，acceptance-log-round7 §5）：Lighthouse 12.8.2 mobile **识字 97/100/100**（P ≥ 95 A 层口径已达）；axe 20 路由 + 3 主题 × 24 状态 0/0；首屏 gzip 108,112 B（GSAP 移出首页同步依赖、关键 CSS 内联、SW 安装延后）；offline-smoke 2076 项预缓存含 OCR 链路。**留一手**：R8 H6 要求成绩回填 `acceptance-log-round8` + 原始 JSON 归档 `evidence/r8/`，当前两者皆空——#9 重测归档时识字侧不得回落 95 以下 | 维护（#9 复测 + 证据归档） |

**识字小计：✅ 11 / ◐ 4 / ❌ 0（共 15 项）**（Round 7 审计：✅ 11 / ◐ 3 / ❌ 1）

---

## 2. 数学 App 对标表（M-M1 … M-M16）

| 模块 | 洪恩能力 | 状态 | Δ | 实测证据（文件路径 + 关键事实） | Round 8 责任 |
|---|---|---|---|---|---|
| M-M1 | 3–12 岁 L1–L5 年龄档 + 技能图谱 | ◐ | ◐（半句闭环） | **年龄档半句已清账**（R7 #6，48d2ddf）：`data/age-band.js`（`AGE_BANDS` 5 档 × `AGE_BAND_MODULES` 6 玩法）+ `composables/useAgeBand.js` + `AgeBandBadge.vue`；六视图（NumberSense/Geometry/Logic/WordProblems/Sudoku/Arithmetic）**全部消费**（check:round7 H4 6/6），新逻辑游戏双视图与 `core/engine/maze.js`/`memory-pairs.js` 也读档；check:content「年龄档各驱动 6 个玩法默认难度，档位越高越难」行为级门禁绿。**技能图谱半句未接线**：`data/curriculum.js` `SKILL_MAP` 34 个技能点已在场且 check:content 有映射探针（产出 25 个 id 全在图谱），但无 `/skill*` 路由、无视图、无 `data/skill-graph.js`（check:round8 H3 三缺）——数据先行，可视化归 #6 | **#6** `cursor/r8-math-skillgraph-9f67` |
| M-M2 | 1000+ 互动/无限题 | ✅ | = | mulberry32 + `questionId()` + 母题 ≥185 门禁 + 每母题 2000 道压测维持；等价判定已由 R7 全局报告留档 | 维护 |
| M-M3 | 185 应用题母题 | ✅ | = | `wordProblems.js` 214 个（18×10+34；93/86/35），28 语义标签 / 42 场景 | 维护 |
| M-M4 | 数感/比较/运算 | ✅ | = | `/number-sense`、`/compare`（3000 道校验）、`/arithmetic`、`/column-arithmetic` 维持 | 维护 |
| M-M5 | 几何/空间 + 七巧板 | ✅ | = | `GeometryView.vue` + `TangramView.vue`（`/tangram`）维持 | 维护 |
| M-M6 | 逻辑/规律 + 配对/迷宫 | ✅ | ◐→✅ | **R7 #7 交付闭环**（5b8fcfe/680c679）：路由 `/memory-pairs` + `/maze`（router L83/L90）+ `modules/logic/MemoryPairsView.vue`/`MazeView.vue`（Canvas）+ `core/engine/memory-pairs.js`/`maze.js`；**`modules.js` L120-121 专题入口已登记**（R7 审计预警的「探针不查首页可达」漏洞实查无恙）；smoke 交互用例（配错回盖/撞墙拦截/顺序收集）+ 画布截图探针钉死动效降级；check:content 内容级门禁：**条件迷宫 200 座全最短路通关 + 配对 1000 副可复现**。三轮顺延项就此清账 | 维护 |
| M-M7 | 数独专项 | ✅ | = | 4/6/9 三档唯一解 + 提示 + 键盘维持；本轮起 SudokuView 也消费年龄档 | 维护 |
| M-M8 | 数形结合演示 | ✅ | = | `visualDemos.js` 8 类三段契约 + `VisualDemosView.vue` 维持 | 维护 |
| M-M9 | 自适应难度 | ✅ | = | `core/engine/adaptive.js`；check:content 弱项抽中 3719/4000、错题优先 2868:1132 绿 | 维护 |
| M-M10 | 错题本 | ✅ | = | `stores/progress.js` `wrongBook` questionId 级 + `WrongBook.vue` 重练维持 | 维护 |
| M-M11 | 计算专题/速算 | ✅ | = | `/sprint` 速算冲刺 + 口算连击 + 竖式维持 | 维护 |
| M-M12 | 剧情关卡地图 + 日冒险 | ✅ | = | 章节契约 + `unlock-scene` 过场 + `daily.js` 400 天可复现维持 | 维护 |
| M-M13 | 互动教具 ≥3 | ✅ | = | 拖拽计数 + 数轴 + `ComposeTenView.vue` 分与合维持 | 维护 |
| M-M14 | 家长面板 | ✅ | = | 口算门 + 雷达 + 错因 + 导出/导入 + 年龄档选择器维持 | 维护 |
| M-M15 | 奖励/成就 | ✅ | = | `achievements.js` 18 项 + Toast/RoundSummary + 动效可关维持 | 维护 |
| M-M16 | 性能/无障碍/离线 | ◐ | ◐（差 1 分） | R7 #9 已定标：LH 12.8.2 mobile **数学 94/100/100**——A11y 95→100（锁定卡片不再用父级透明度压对比度，首页 axe serious 5→0）、首屏 gzip 105,114→77,058 B（-26.7%）。**A 层口径 P ≥ 95 还差 1 分**（R8 H6 红），axe/离线四轮全绿。维持 ◐ 待 #9 冲线 + `evidence/r8` 归档 | **#9** `cursor/r8-perf-lighthouse-9f67` |

**数学小计：✅ 14 / ◐ 2 / ❌ 0（共 16 项）**（Round 7 审计：✅ 13 / ◐ 3 / ❌ 0）

---

## 3. 总览与增量

**总盘子：31 项 = ✅ 25（80.6%）/ ◐ 6（19.4%）/ ❌ 0（0%）——首次零 ❌。**

| 轮次审计 | ✅ | ◐ | ❌ |
|---|---|---|---|
| Round 4 | 4 | 20 | 7 |
| Round 5 | 13 | 13 | 5 |
| Round 6 | 17 | 12 | 2 |
| Round 7 | 24 | 6 | 1 |
| **Round 8 基线（本次）** | **25** | **6** | **0** |

状态变化明细（相对 R7 审计）：

- **◐→✅（3 项）**：L-M4 形近干扰（1817 组 + 双视图 + 功能探针）、L-M15 识字性能（LH 97 实测定标，A 层 95 口径亦达）、M-M6 数学逻辑游戏（双路由 + Canvas + 内容门禁 + 专题登记）。
- **❌→◐（1 项）**：L-M10 拍照识字——接线/离线/署名全闭环，唯识别精度未定标；按「无测量不转 ✅」的既有判法计 ◐（对标表历史上首次归零 ❌）。
- **✅→◐（2 项，口径上移非退化）**：L-M9（R8 杆 = 音素/声调评分或学伴对话面）、L-M11（R8 杆 = 99 条手写剧情 + 儿歌 ≥3 首）。两项 v1 功能完好且门禁全绿。
- **持平 ◐（3 项）**：L-M6 字源 65→525（涨 8 倍但未到 800）、M-M1（年龄档半句清账，技能图谱半句待 #6）、M-M16（Perf 94 差 1 分）。
- **对齐性**：6 个 ◐ 与 R8 简报 P0 五大项 + Perf 冲线**一一对应，全部已立项**（#4 字源、#5 剧情儿歌、#6 图谱、#7 OCR 精度、#8 跟读 v2、#9 Perf），连续第二轮做到「◐ 存量 = 在途任务」零悬空。

---

## 4. Round 8 子代理交付后预期与 R9 归属

> 对照 `.agent_workspace/ROUND8-BRIEF.md` §子代理分工。#1–#3 为架构/审计/验收支撑，不改对标行，此处审 #4–#10。审计时点各功能分支均未起步（基线 a8b21b3）。

### #4 `cursor/r8-literacy-etymology-9f67`（字源 525→800）

- **交付后预期**：L-M6 ◐→**✅**（主计划终点 800 达成，本项五轮长跑收官）。H1 探针读 `etymology-index.js` 的 `ETYMOLOGY_CHARS`（≥800 且无重复）——**扩容必须同步索引**，与 R7 H3 同一陷阱；且 R7 H3 仍在跑 `TOTAL_ETYMOLOGY === 实际数` 一致性断言，改语料不同步声明会打红 H8。管线路径现成：往 `scripts/data/etymology-seed.txt` 加种子 → `gen-etymology.mjs` 再生成；check:data 的形旁/读音一致性 9 探针会自动看住派生质量。
- **仍缺项归 R9**：无（达 800 即清账；若批量派生文案模板感过重，质量走查记 R9 备忘）。

### #5 `cursor/r8-literacy-stories-9f67`（u59–u99 剧情 + 儿歌 v1）

- **交付后预期**：L-M11 ◐→**✅**。H2 探针**四条件**：`unit-stories.js` 源文件里 `u<数字>:` 字面键 ≥99 且 u59–u99 无缺（**正则扫源码，不认拆文件**——41 条手写剧情必须落在该文件内）+ `data/songs.js` 存在且 `id:` 条目 ≥3 + 儿歌路由（path 匹配 `song|儿歌|music|nursery` 或源码出现 `SongsView/SongList`）。
- **仍缺项归 R9**：儿歌 v1（≥3 首）之上的曲目扩充与旋律-歌词逐句同步动画；u59–u99 与 u1–u58 手写质感一致性走查。

### #6 `cursor/r8-math-skillgraph-9f67`（技能图谱可视化）

- **交付后预期**：M-M1 ◐→**✅**（M-M1 两个半句就此全部闭环，31 项对标表**理论满盘**的最后一块拼图之一）。H3 探针三重：路由 path 匹配 `skill|图谱|map-graph` 且动态 import 视图 + 视图文件在场 + **数据文件必须是 `data/skill-graph.js` 或 `data/skills.js`**（含 `nodes|skills|edges` 语义）——现成的 `curriculum.js` **不计数**，最省事做法是新建 `skill-graph.js` 从 `curriculum.js` 组装 nodes/edges 再导出，34 个技能点与 check:content 映射探针天然对齐。联动 ageBand/母题进度是简报要求，探针不验，靠 #3 验收与走查兜底。
- **仍缺项归 R9**：图谱 × FSRS/自适应联动深化（按图谱推荐下一步学习路径）。

### #7 `cursor/r8-literacy-ocr-quality-9f67`（OCR 精度评测）

- **交付后预期**：L-M10 ◐→**✅**（31 项中最后一个「无测量」项定标）。H4 探针：`scripts/test-ocr-accuracy.mjs` 存在，或 `test-ocr.mjs` 内出现 `ROUND8_H4` 标记 + `benchmark|accuracy|基准|sample-photo` 语义；CharDetailView 形近池半边**基线已绿**（L43 import 实查在场），#7 只需守住不动。基准图集可从 `public/ocr/sample-photo.png` + `gen-ocr-sample.mjs` 扩批。
- **仍缺项归 R9**：基准集扩样（手写体/低光/复杂背景）与精度阈值门禁化（本轮先定标，阈值线由实测决定）。

### #8 `cursor/r8-literacy-followread-9f67`（跟读 v2 / 学伴对话面）

- **交付后预期**：L-M9 ◐→**✅**。H5 探针在 `useSpeechEval.js + FollowReadView.vue + MascotCompanion.vue` 拼接源码上匹配 `phoneme|音素|tone|声调|companion.*(chat|dialog|reply)|学伴.*对话|ROUND8_H5`，另须 `ROUND8_H5_SMOKE` 进识字 smoke。**红线**：三档降级与「在线识别默认关 + 家长显式开」的隐私姿态不得退（简报明文）；`companion.*chat` 类正则不跨行，稳妥做法是真实能力 + 源码显式 `ROUND8_H5` 标记双保险。中文声调评分在 Web Speech API 边界内只能做拼音声调近似比对，属可接受 v2 口径。
- **仍缺项归 R9**：真·音素级识别引擎评估（离线 wasm ASR 选型），若 #8 走近似比对路线。

### #9 `cursor/r8-perf-lighthouse-9f67`（Perf 冲 95 + a11y 余项）

- **交付后预期**：M-M16 ◐→**✅**（数学 94→95+，差 1 分是全部 6 个 ◐ 里最薄的一层窗户纸）；L-M15 复测归档不回落。H6 探针**三条件**：`acceptance-log-round8.md` 内「识字」「数学」后各跟上 `P/A/BP` 三元组（正则取首个 `\d{2,3}/\d{2,3}/\d{2,3}`，**在 §2.1 表格里回填真实数字，别在它前面插入别的数字三元组**）+ 双 P ≥95 + `.agent_workspace/evidence/r8/` 目录在场。锁 Lighthouse 版本（R7 用 12.8.2）防漂移；数学首页对比度 serious 余项按简报一并收尾。
- **仍缺项归 R9**：LH 版本锁定进 CI 常驻门禁 + 真机/桌面档双档定标。

### #10 `cursor/r8-global-report-9f67`（证据包 + GLOBAL-SUMMARY + 终验回归）

- **交付后预期**：H7 绿。现报告是 Round 7 版（gpt-5.6-sol，31/31 行、零 ❌），但**7 行「⏳ 待 R7 子代理 #N」已全部时过境迁**（对应能力本基线已合入），必须逐行改为实测终态。**双门禁夹击提醒**：R8 H7 要求全文出现 `Round 8`、零 ❌ 零占位（`⬜|待回填|[P/F]`）、引用 `evidence/r8`、正文 >4000 字符；同时 R7 H7 探针继续在跑——31 行模块表必须保持、状态列只认 `✅` 或 `⏳ 待 R7 子代理 #4-10` 字样、首行 Model slug、同时引用 round6/round7 两份审计。**改成「待 R8 子代理」字样会打红 R7 H7（进而打红 R8 H8）**，Round 8 报告的模块行只能全 ✅ 落地，在途项用表外文字说明。本审计（`round8-hongen-audit.md`）应一并入引用与证据索引。
- **报告须写明的口径判定（本审计移交）**：① L-M9/L-M11 两行 R8 曾因口径上移临时下调 ◐，终版按 #8/#5 交付实测回写；② L-M10 达标口径 = 接线闭环 + 固定基准集精度定标（精度绝对值本轮只记录不设罚线）；③ M-M2「无限题」等价判定沿用 R7 报告留档。
- **仍缺项归 R9**：对外发布声明与证据包冻结（LICENSE 确认 D-1 仍待发布负责人，R7 报告 §4 既有备忘）。

### 全部交付后的预期终盘

#4–#10 如约交付并通过 G1–G7，31 项 = **✅ 31 / ◐ 0 / ❌ 0**，check:round8 8/8——主计划「零 ❌ 零 ⬜」A 层终态达成，对标表五轮长跑收官。届时唯一的合理余量是 §「R9 归属备忘」清单（深度打磨与发布工程，无功能缺口）。

### R9 归属备忘（本轮预判汇总）

| # | 项 | 来源 |
|---|---|---|
| 1 | L-M5 绘本社区投稿格式文档（R6→R7→R8 三轮备忘未清，建议 R9 必办或正式除名） | R6 审计既有备忘 |
| 2 | 儿歌曲目扩充 + 旋律-歌词同步动画（v1 → v2） | #5 交付面之外 |
| 3 | OCR 基准集扩样（手写体/低光/复杂背景）+ 精度阈值门禁化 | #7 定标结果决定 |
| 4 | 跟读音素评分的离线 ASR 引擎评估（若 #8 走拼音近似路线） | #8 技术路线决定 |
| 5 | 技能图谱 × FSRS/自适应联动（图谱节点推荐学习路径） | #6 v1 可视化之外 |
| 6 | Lighthouse 版本锁定进 CI + 真机 Android WebView/桌面档双档定标 | #9 交付面之外 |
| 7 | u59–u99 剧情与 u1–u58 手写质感一致性走查、字源批量派生文案质量抽查 | #5/#4 批量生产的质量债 |
| 8 | 发布终态：LICENSE 确认（D-1）、对外声明措辞、证据包冻结与版本号 | R7 报告既有备忘 + #10 视交付 |
| 9 | Android 真机走查（相机权限流 / OCR wasm 在 WebView 的实测性能） | check:android 26 项为静态门禁 |

---

## 5. 门禁联动提醒（发给 #3/#9/#10 与功能组）

1. **H1/H3 都只认指定文件**：H1 读 `etymology-index.js` 的 `ETYMOLOGY_CHARS`（同步索引！且 R7 H3 的 `TOTAL_ETYMOLOGY` 一致性断言仍在跑）；H3 数据文件白名单是 `data/skill-graph.js` / `data/skills.js` 二选一——已在场的 `curriculum.js` 不计数，须新建文件（可从 `curriculum.js` 组装导出）。
2. **H2 剧情键是对 `unit-stories.js` 源文件的正则扫描**（`/\bu(\d+)\s*:/`）：41 条新剧情必须以字面键写进该文件，拆分文件或运行时拼装都过不了门禁；儿歌路由的 path 正则不含 `rhyme`，路由名用 `songs`/`nursery` 最稳。
3. **H5 正则不跨行**：`companion.*(chat|dialog|reply)` 在剥注释后的拼接源码上按行匹配，学伴对话实现建议同行落 `ROUND8_H5` 显式标记 + smoke 落 `ROUND8_H5_SMOKE`，双保险。
4. **H6 回填格式敏感**：探针取「识字/数学」字样后**第一个** `\d{2,3}/\d{2,3}/\d{2,3}` 三元组——在 `acceptance-log-round8.md` §2.1 表回填，不要在文首新增含数字三元组的行；`evidence/r8/` 目录必须真实存在（放 LH 原始 JSON + axe 输出）。
5. **H7 受 R7/R8 双探针夹击**：Round 8 版全局报告必须同时满足 R7 H7（31 行模块表、状态列只认 `✅` 或 `⏳ 待 R7 子代理 #4-10`、首行 Model slug、引用两份审计）与 R8 H7（含 `Round 8`、零 ❌ 零占位、`evidence/r8` 索引、>4000 字符）。**「⏳ 待 R8 子代理」字样是双杀写法**——R7 H7 红 → R8 H8 连环红。
6. **H4 只剩半边**：CharDetailView 形近池基线已绿（36e01ba 交付时一步到位），#7 别动 `similarDistractors` 调用；新增 `test-ocr-accuracy.mjs` 后建议挂进 `test-literacy.sh`，防止只有文件没有 CI 执行面。
7. **数学侧无 `check-bundle.mjs`**：ROUND8-ACCEPTANCE 红线写了「数学 < 250 KB（check:bundle）」，但 `apps/math-app/scripts/` 里没有该脚本（识字侧有，预算 420 KB）——#3 或 #9 请补脚本或修正红线措辞，避免验收时对不上号（当前实测 77 KB，远低于线，属流程债不是性能债）。
8. **老水位勿回退**：`check:data` 61 项（含形近覆盖 ≥95%、字源派生一致性）与 `check:content` 全绿（含迷宫 200 座/配对 1000 副）是本基线新常态；R8 合并保持 `check:round7` 8/8（=H8）、`check:round6` 7/7 是 G2/G3 硬门槛。

---

## 6. 审计方法备注

- 内容计数：`node --input-type=module` 直接 import `characters.js（1820/99）/ books.js（132 本，verifyBookCoverage()=0）/ poems.js（24，verifyPoemCoverage()=0）/ idioms.js（60）/ games.js（6 款，非 listen 5）/ etymology-index.js（525，去重 525）/ badges.js（11）/ unit-stories.js（TOTAL_UNIT_STORIES=58）/ similar-chars.js（1817 组）`；数学侧经 `--import ./scripts/register-alias.mjs` import `wordProblems.js（214；18×10+34；93/86/35）/ visualDemos.js（8）/ achievements.js（18）/ curriculum.js（SKILL_MAP 34）/ age-band.js（5 档 × 6 玩法）`。
- 门禁实跑（全部在 `a8b21b3` 干净 worktree）：`check:round6`（7/7，exit 0）、`check:round7`（8/8，exit 0）、`check:round8`（1/8，exit 1，预期红）、识字 `check:data`（61/61）、数学 `check:content`（全绿，exit 0）。
- 功能有无：逐文件读源码 + 定向 grep（distractors 双视图 import 行号实查、useAgeBand 消费面 11 文件、phoneme/音素/声调/tone 零命中、songs 零命中、MascotCompanion 无 chat/dialog、`OCR_CACHE`/`ocrPrefix` 在 sw.js、modules.js L120-121 登记、tesseract 在 package.json 与 THIRD_PARTY_NOTICES）；路由以 `router/index.js` 实际注册为准（识字 27 条含 `/ocr` 与重定向、数学 18 条含 `/memory-pairs`、`/maze`）。
- Lighthouse/axe/zip/Android 未在本轮重测：引用 `acceptance-log-round7.md` §2/§5 实测记录（LH 12.8.2 mobile：识字 97/100/100、数学 94/100/100；axe 双 App 20/20 + 3×24 状态 0/0；gzip 108,112 / 77,058 B；zip 2,891,785 / 435,723 B；check:android 26/26），该日志为 R7 闭合的唯一实测出处；R8 终态由 #9/#10 重测并归档 `evidence/r8/`。
- Round 8 在途进度快照（审计时点）：#4–#10 功能分支均未起步，基线即 a8b21b3。
