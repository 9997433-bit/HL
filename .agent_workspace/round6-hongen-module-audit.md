Model slug: fable
# Round 6 · 洪恩模块对标审计（fresh code walk）

> 审计人：Round 6 子代理 #2（fable）
> 审计基线：分支 `cursor/r6-module-audit-9f67`（自 `cursor/openmoji-integration-9f67` @ `90663c1`，即 Round 5 + Round 5B + Android 同步闭合点）
> 审计日期：2026-08-27 · Node 22.14.0
> 方法：**逐文件重新走读源码**（不照抄 Round 5 结论），每条状态附文件路径证据；
> 内容体量用 `node` 实际 import 数据文件统计（数学侧走 `scripts/alias-loader.mjs` 解析 `@/` 别名）；
> 轮次门禁 `check:round4 / round5 / round5b / round6` 在本 worktree 各实跑一次。

---

## 0. 基线门禁实测（90663c1，本机实跑）

| 门禁 | 结果 | 明细 |
|---|---|---|
| `check:round4` | **4/4 绿** | 字库 1000（≥500）、错题本、adaptive、种子 PRNG |
| `check:round5` | **12/12 绿** | 1000 字 / 30 绘本零越界 / 60 成语 / 118 母题（≥100）/ 数形演示 8 类 / 新小游戏 3 款 + 路由接线 / 字源 65 字 / 七巧板 / 分与合 / 竖式 |
| `check:round5b` | **6/6 绿** | 每日冒险、吉祥物 12 路由、useFeedback 11 处、地图叙事（LearnView 灰显+剧情+解锁过渡）、街机大厅 4/4、答对节奏双 App |
| `check:round6` | **1/7（预期红）** | 仅 H2 verifyBookCoverage 零越界通过；H1 1000<1800、H2 30<130、H3 古诗未接线、H4 跟读未接线、H5 小游戏 3<5、H6 母题 118<185 全红 |

**内容体量实测（import 数据文件直接计数）**：

| 指标 | 基线实测 | R6 目标 | 达成率 |
|---|---|---|---|
| 识字字库 | **1000 字 / 58 单元**（`TOTAL_CHARACTERS`） | 1800 | 56% |
| 分级绘本 | **30 本 / 240 页 / L1–L6** | 130 | 23% |
| 成语 | **60 条** | 60+（已达） | 100% |
| 古诗 | **0 首**（无 `poems.js`，无路由） | 20 | 0% |
| 小游戏（不含 listen） | **3 款**（maze/memory/spot，`data/games.js` 注册表） | 5 | 60% |
| 应用题母题 | **118 个**（14 语义模板 × 6 场景皮肤；一步 55 · 两步 40 · 进阶 23） | 185 | 64% |
| 字源动画 | 65 字（主计划终点 ≥800） | R6 未指派 | 8% |
| 数形演示 | 8 类（≥7 已达） | 维持 | 100% |
| 徽章 / 成就 | 识字 10 枚 / 数学 18 项 | 维持 | — |

---

## 1. 识字 App 对标表（L-M1 … L-M15）

图例：✅ 达标 / ◐ 有 MVP 但缺洪恩级深度 / ❌ 未实现。「Δ」列 = 相对 Round 5 审计的变化。

| 模块 | 洪恩能力 | 状态 | Δ | 实测证据（文件路径 + 关键事实） | Round 6 责任 |
|---|---|---|---|---|---|
| L-M1 | 1800 常用字分级 | ◐ | = | `apps/literacy-app/src/data/characters.js`：`TOTAL_CHARACTERS = 1000`、**58 个单元**；懒加载管线成熟（`char-index.js` 主包索引 + `chars/` 按单元切包 + `character-index.js`；`check-bundle.mjs` 首屏预算 420 KB 门禁常驻）。体量 = 洪恩的 ~56%，R5 目标 1000 已达成，扩到 1800 只是量的问题 | **#4** `cursor/r6-literacy-1800chars-9f67` |
| L-M2 | 认-读-写-玩闭环（状态机） | ✅ | = | `apps/literacy-app/src/views/CharDetailView.vue`：`PHASES`（L58）intro→trace→listen→quiz→reward，自动衔接走 `pendingNext`（L85）可按停（WCAG 2.2.1）；四步齐才发奖 | 维护 |
| L-M3 | 笔顺+描红判定 + 错3次示范 | ✅ | = | `apps/literacy-app/src/components/HanziStrokeBox.vue`：`demoAfterMistakes: 3`（L32），同笔连错 3 次 `demonstrateStroke()`（L222）慢放示范再接回测验，键盘替代同享 | 维护 |
| L-M4 | 听音识字 + 形近干扰 | ◐ | = | `apps/literacy-app/src/views/ListenGameView.vue` L141：干扰项**仍是随机取样** `shuffle(list.filter((c) => c.char !== pick.char))`，无形近字库；`characters.js` 无 `confusable` 字段。R4/R5 两轮审计都建议补，**R6 简报仍未指派** | ⚠️ 建议 #4 扩字库时顺带加形近字段，或 #7 做游戏时带走；否则归 R7 |
| L-M5 | 130 本分级绘本 | ◐ | ❌→◐ | `apps/literacy-app/src/data/books.js`：**30 本 / 240 页 / 六级**，`verifyBookCoverage` 零越界（check:round6 唯一绿灯项）。体量 = 洪恩的 ~23%，生成管线（正文仅用已学字）已被 R5 验证 | **#5** `cursor/r6-literacy-books-130-9f67` |
| L-M6 | 800+ 字源互动 | ◐ | ◐+（管线成型） | `apps/literacy-app/src/data/etymology.js`：**65 字**；`utils/etymologySketch.js` 形状 DSL（8 种图元，Node 可校验）+ `components/EtymologyStage.vue` GSAP timeline 演变动画（L30/L150）+ 路由 `/etymology/:char`。**管线 ✅、体量 8%**，R6 简报未安排扩容 | ⚠️ 65→800 无人认领，归 **R7**（管线现成，纯内容工作） |
| L-M7 | 记忆曲线复习 | ✅ | = | `apps/literacy-app/src/utils/srs.js`（FSRS-lite）+ `stores/progress.js` 调度 + `ParentView.vue` L311 记忆强度热力图 | 维护 |
| L-M8 | 成语/古诗国学 | ◐ | ◐+（成语达标） | `apps/literacy-app/src/data/idioms.js`：**60 条**（R5 #6 交付，`idiom-index.js` 懒加载）——成语侧已达洪恩口径；**古诗 0 首**：无 `poems.js`/`poetry.js`、路由无 `/poems`，check:round6 H3 红 | **#6** `cursor/r6-literacy-poems-speech-9f67`（古诗 20 首） |
| L-M9 | AI 学伴/跟读评测 | ❌ | = | `apps/literacy-app/src/utils/speech.js` 仅 4 个 TTS 函数（`speak/stopSpeaking/isSpeechSupported/primeSpeech`）；全库 grep `SpeechRecognition/webkitSpeech/MediaRecorder/getUserMedia` **零命中**，check:round6 H4 红 | **#6**（跟读评测 v1：Web Speech 比对 + 录音回放降级） |
| L-M10 | 拍照识字 | ❌ | = | 全库 grep `tesseract/ocr` 零命中 | **R7**（主计划本就排 R7） |
| L-M11 | 动画儿歌/IP | ✅ | ◐→✅ | 我方目标「GSAP 程序化动画 + 开源素材、不复制 IP」已成立：`components/MascotCompanion.vue` 吉祥物陪跑（check:round5b P2 实测 12 路由、点触语音/鼓励）+ `utils/sfx.js` 音效 + `data/unit-stories.js` 58 单元一句话剧情 + `LearnView.vue` 地图叙事（灰显/剧情/解锁过渡/动效降级，check:round5b P4）+ 街机大厅（P5）。**儿歌/音乐内容仍无**，作为补充项记 R7 备忘，不影响我方口径达标 | 维护（儿歌内容 → R7 备忘） |
| L-M12 | 字迷宫/跑酷等小游戏 ≥5 | ◐ | ❌→◐ | `apps/literacy-app/src/data/games.js` 注册表 4 款：listen + **maze（字迷宫）/ memory（配对记忆）/ spot（找不同）**，路由 `/games/maze|memory|spot` 全接线（check:round5 H6 双探针绿）。不含 listen 为 3 款，距 ≥5 差 2 | **#7** `cursor/r6-literacy-minigames-9f67`（+2 款） |
| L-M13 | 家长控制/防沉迷 | ✅ | = | `apps/literacy-app/src/views/ParentView.vue` + `stores/progress.js`/`settings.js`：口算门 + 导出/导入 + 每日时长 + `planUnits` 自选单元 + `dailyGoal` 每日新字上限 | 维护 |
| L-M14 | 奖励/徽章体系 | ✅ | = | `apps/literacy-app/src/data/badges.js` 10 枚三档徽章 + `BadgeShelf.vue`；R5B 增量：`stores/dailyQuest.js` + `DailyQuestCard.vue` 每日任务（check:round5b P1 任务 4/3 + 完成庆祝） | 维护 |
| L-M15 | 性能/无障碍/离线 | ◐ | ✅→◐ | A11y/离线稳：axe 20 路由 + 42 交互态 `critical=0/serious=0`、sw 预缓存 + offline-smoke、首屏 JS gzip 108,149 B（<256 KB 预算）。**Perf 出现版本漂移**：R5 回归分支 LH 96/100/100，但 R5B 用 Lighthouse 13.4.1 移动端复测**识字 Perf 87 < 90**（acceptance-log-round5b §1 自判 FAIL）。按「测量驱动」原则降为 ◐，待 #10 统一 LH 版本重新定标 | **#10** `cursor/r6-regression-gate-9f67`（定标 + 内容扩容后重测） |

**识字小计：✅ 6 / ◐ 7 / ❌ 2（共 15 项）**（Round 5 审计：✅ 6 / ◐ 5 / ❌ 4）

---

## 2. 数学 App 对标表（M-M1 … M-M16）

| 模块 | 洪恩能力 | 状态 | Δ | 实测证据（文件路径 + 关键事实） | Round 6 责任 |
|---|---|---|---|---|---|
| M-M1 | 3–12 岁 L1–L5 年龄档 | ◐ | = | `rg -n ageBand apps/math-app/src` 仍只命中 3 处：`stores/settings.js`（定义 L1–L5）、`ParentView.vue`（选择器）、`ArithmeticView.vue` L39（`LEVEL_BY_AGE_BAND` 唯一消费方）。**R4→R5→R6 连续三轮无人指派**，全模块联动始终悬空 | ⚠️ 建议并入 **#9**（其交付面覆盖比较/速算/生活应用出题参数）；否则归 R7 |
| M-M2 | 1000+ 互动/无限题 | ◐ | = | 种子化管线维持：`src/utils/random.js` mulberry32 + `questionId()`；`check-content.mjs` `MIN_TEMPLATES = 100`（R5 已从 25 提到 100），每母题压测 2000 道可复现。**母题 118 < 主计划 ≥300 字面口径**，#8 扩到 185 后需复核该口径的判定方式（185 母题 × 参数 = 事实无限题） | **#8** `cursor/r6-math-problems-185-9f67` |
| M-M3 | 185 应用题母题 | ◐ | = | `apps/math-app/src/data/wordProblems.js`：**118 个**（`SEMANTIC_TEMPLATES` 14 × `SCENE_SKINS` 6 交叉 + 手工母题；一步 55 · 两步 40 · 进阶 23，import 实测）。体量 = 洪恩的 ~64% | **#8**（118→185+） |
| M-M4 | 数感/比较/运算 | ✅ | ◐→✅ | 数感/运算维持；比较 `/compare` + `data/compare.js`（三符号 + `makeCompareQuestion` 种子化）；**竖式已补齐**：`modules/arithmetic/ColumnArithmeticView.vue`「竖式工坊」（L176，进位/借位分步引导 L125-126），路由 `/column-arithmetic`，check:round5 探针绿 | **#9** 入口接线打磨（简报 M-M4/M-M11 项） |
| M-M5 | 几何/空间 + 七巧板 | ✅ | ◐→✅ | `modules/geometry/GeometryView.vue` 5 种题型 + **`TangramView.vue` 七巧板**（路由 `/tangram`，check:round5 探针绿） | 维护 |
| M-M6 | 逻辑/规律 + 配对/迷宫 | ◐ | = | `modules/logic/LogicView.vue` **5 种规律题**（number/emoji/group/rotate/shape，L97-191）；数学侧记忆配对/迷宫仍无（识字侧 R5 已有 memory/maze，玩法可迁移）。R5 审计已预警「明确顺延 R6 而不是默认漏掉」，**R6 简报仍未列** | ⚠️ 归 **R7**（建议迁移识字侧 MemoryGame/MazeGame 壳） |
| M-M7 | 数独专项 | ✅ | = | 4/6/9 三档 + 唯一解门禁 + 提示 + 键盘维持 | 维护 |
| M-M8 | 数形结合演示 | ✅ | ❌→✅ | `apps/math-app/src/data/visualDemos.js`：**8 类**演示，统一三段契约 `object（实物）→ visual（图形）→ equation（算式）` + narration；`modules/visual-demos/VisualDemosView.vue` 支持**跳过/重播/手动逐步**，路由 `/visual-demos` + 首页接线。check:round5 H5 绿（8 ≥ 7） | 维护 |
| M-M9 | 自适应难度 | ✅ | = | `src/core/engine/adaptive.js`：`pickNextQuestion`（L134）弱项加权 + 连对升/连错降 + `createAdaptiveEngine`（L283）；`components/QuizShell.vue` L32/L58 默认 `adaptive: true` 实际接线 | 维护 |
| M-M10 | 错题本 | ✅ | = | `stores/progress.js` questionId 级 `wrongBook` + `retryWrong()`；`components/WrongBook.vue` 重做流程；入口在 `modules/progress/ProgressView.vue` | 维护 |
| M-M11 | 计算专题/速算 | ✅ | ◐→✅ | 口算闯关：`modules/arithmetic/ArithmeticView.vue` 连击加成（L286 连击 chip + L135 combo 星星加成）+ 数轴 + 错因；**竖式/进位借位专练**：`ColumnArithmeticView.vue`（与 M-M4 同一交付）。主计划两个要件都已在场 | **#9** 速算/生活应用专题入口接线（增强，非从无到有） |
| M-M12 | 剧情关卡地图 + 日冒险 | ✅ | = | `data/modules.js` 每星球 `story`/`lockedStory` 双文案（L29-120）+ `modules/home/HomeView.vue` 解锁过场 `unlock-scene`（L287）+ 呼吸高亮 + 今日冒险 5 题（`data/daily.js` 同日可复现）；运行时验收脚本 `scripts/check-map-narrative.mjs` 双 App 跑真浏览器。R6 目标是**升级**到 Matific 级章节叙事，底子已是 ✅ | **#9** `cursor/r6-math-map-narrative-9f67`（章节名+解锁条件文案深化） |
| M-M13 | 互动教具 ≥3 | ✅ | ◐→✅ | 3/3 齐：拖拽装货计数（`modules/number-sense/NumberSenseView.vue`）+ 数轴（`ArithmeticView.vue`）+ **分与合 `ComposeTenView.vue`**（路由 `/compose-ten`，check:round5 探针绿） | 维护 |
| M-M14 | 家长面板 | ✅ | = | 口算门 + 雷达 + 错因 + 导出/导入 + 时长 + 年龄档选择器维持（`modules/parent/ParentView.vue`） | 维护 |
| M-M15 | 奖励/成就 | ✅ | = | `data/achievements.js` **18 项**（R5 基线 16）+ Toast/RoundSummary + 动效可关 | 维护 |
| M-M16 | 性能/无障碍/离线 | ◐ | ✅→◐ | A11y/离线稳：axe 0/0、sw + offline-smoke、首屏 gzip 102,651 B；路由级拆包维持。**Perf 同 L-M15 漂移**：R5 回归 96/100/100 → R5B LH 13.4.1 复测**数学 Perf 84 < 90**（log 自判 FAIL）。降 ◐ 待定标 | **#10**（同 L-M15） |

**数学小计：✅ 11 / ◐ 5 / ❌ 0（共 16 项）**（Round 5 审计：✅ 7 / ◐ 8 / ❌ 1）

---

## 3. 总览与增量

**总盘子：31 项 = ✅ 17（54.8%）/ ◐ 12（38.7%）/ ❌ 2（6.5%）。**

| 轮次审计 | ✅ | ◐ | ❌ |
|---|---|---|---|
| Round 4 | 4 | 20 | 7 |
| Round 5 | 13 | 13 | 5 |
| **Round 6 基线（本次）** | **17** | **12** | **2** |

状态变化明细（相对 R5 审计）：

- **升 ✅（5 项）**：M-M4（竖式补齐）、M-M5（七巧板）、M-M8（数形演示 ❌→✅）、M-M11（口算+竖式双要件）、M-M13（分与合补齐）、L-M11（R5B 吉祥物/音效/地图叙事使我方口径成立）——其中 L-M11 从 ◐、M-M8 从 ❌ 直升。
- **脱 ❌（2 项）**：L-M5（5→30 绘本）、L-M12（1→4 款游戏），均升 ◐。
- **降 ◐（2 项）**：L-M15 / M-M16——R5B 用 Lighthouse 13.4.1 复测 Perf 87/84（< 90，log 自判 FAIL），与 R5 回归分支 96 分冲突，按测量驱动原则先降后定标。
- **仅剩 ❌（2 项）**：L-M9 跟读评测（#6 本轮交付）、L-M10 拍照识字（R7 计划内）。

---

## 4. Round 6 子代理交付后预期状态与 R7 归属

> 对照 `.agent_workspace/ROUND6-BRIEF.md` §子代理分工。#1–#3 为架构/审计/验收支撑，不改对标状态，此处审 #4–#9（+#10 门禁）。

### #4 `cursor/r6-literacy-1800chars-9f67`（1000→1800 字）

- **交付后预期**：L-M1 ◐→**✅**（1800 = 洪恩 100% 口径；58 单元管线扩到 ~100 单元量级，`check-bundle` 420 KB 预算须守住；新 800 字的离线笔顺 JSON 要进 sw 预缓存清单）。
- **仍缺项归 R7**：无（体量项就此清账）。**顺带机会**：给字表加 `confusable` 形近字段可一并解锁 L-M4——若不做，L-M4 归 R7。

### #5 `cursor/r6-literacy-books-130-9f67`（绘本 30→130）

- **交付后预期**：L-M5 ◐→**✅**（130 本 + `verifyBookCoverage` 零越界维持；等级分布覆盖 L1–L6）。
- **仍缺项归 R7**：主计划口径里的「社区投稿格式」文档（若本轮只交内容不交格式规范）。

### #6 `cursor/r6-literacy-poems-speech-9f67`（古诗 20 + 跟读评测 v1）

- **交付后预期**：L-M8 ◐→**✅**（成语 60 已达标 + 古诗 20 首朗读/点字/拼音）；L-M9 ❌→**✅**（我方目标即「Web Speech 跟读比对 + 录音回放降级」，v1 落地即达标）。注意 `check-round6.mjs` H3/H4 探针的**路径约定**：古诗须落在 `data/poems.js` 或 `data/poetry.js` 且导出 `POEMS`；跟读须让 router 出现 `speech`/`follow-read` 或存在 `views/FollowReadView.vue` / `composables/useSpeechEval.js` / `utils/speechEval.js`，否则门禁不认账。
- **仍缺项归 R7**：跟读评分精细化（音素/声调级）与「AI 学伴」对话面——洪恩的 AI 学伴宽于跟读，v1 之外的部分记 R7 备忘。

### #7 `cursor/r6-literacy-minigames-9f67`（再增 2 款小游戏）

- **交付后预期**：L-M12 ◐→**✅**（不含 listen ≥5 款；新游戏必须登记进 `data/games.js` 注册表 + 路由接线，H5 探针按注册表计数）。
- **仍缺项归 R7**：若本轮未顺带换 ListenGameView/CharDetailView 的干扰项取样策略，**L-M4 形近干扰归 R7**（连续三轮被建议、无人认领的最小改动项）。

### #8 `cursor/r6-math-problems-185-9f67`（母题 118→185+）

- **交付后预期**：M-M3 ◐→**✅**（≥185，H6 探针读 `WORD_PROBLEM_COUNT`）；M-M2 ◐→**✅***（185 母题 × 种子参数 = 无限可复现题，实质达标；*主计划「≥300 题门禁」字面口径建议由 #3/#10 在验收标准里明确「母题 ≥185 + 每母题压测 2000 道」等价替代，否则 R7 复核）。`check-content.mjs` `MIN_TEMPLATES` 须同步 100→185。
- **仍缺项归 R7**：若语义模板/场景皮肤只加母题不加新语义类，「185 **类**」的类目多样性复核归 R7。

### #9 `cursor/r6-math-map-narrative-9f67`（地图叙事 + 比较/速算/生活应用专题）

- **交付后预期**：M-M12 保持 ✅ 并加深（章节名 + 解锁条件文案 + 呼吸高亮已有底子，升级到 Matific 级叙事）；M-M4/M-M11 保持 ✅ 并补「速算/生活应用」专题**入口**（首页可达、`modules.js` 登记）。
- **仍缺项归 R7**：**M-M1 全模块联动**——除非 #9 把 `ageBand` 接进比较/速算/生活应用的出题参数（强烈建议，这是它连续三轮悬空后最顺路的收口点），否则继续挂 R7；**M-M6 数学侧配对/迷宫**同样归 R7（识字侧游戏壳可迁移）。

### #10 `cursor/r6-regression-gate-9f67`（门禁与回归）

- **交付后预期**：check:round6 6 项硬门槛全绿；**Lighthouse 版本定标**（锁定 CLI 版本写进脚本/文档，消除 96 vs 87/84 的漂移）→ 若 Perf ≥95 复现，L-M15/M-M16 回 ✅；内容扩容后重测包体与离线。
- **仍缺项归 R7**：若定标后 Perf 落在 90–94，冲 95 的优化归 R7。

**R7 归属清单（本轮预判）**：L-M4 形近干扰（若 #4/#7 未带走）、L-M6 字源 65→800、L-M9 评分精细化/AI 学伴、L-M10 拍照识字 OCR、L-M11 儿歌内容备忘、M-M1 全模块联动（若 #9 未带走）、M-M6 数学配对/迷宫、M-M2 「≥300」口径复核（若 #8/#3 未在验收标准里等价替代）、Perf 冲 95（视 #10 定标结果）。

---

## 5. 门禁联动提醒（发给 #10 与内容组）

1. **老门禁阈值滞后**：`apps/literacy-app/scripts/check-data.mjs` L43 仍是 `TOTAL_CHARACTERS >= 500`（应提至 1800）；`apps/math-app/scripts/check-content.mjs` L55 `MIN_TEMPLATES = 100`（应提至 185）。不提的话 check:round6 绿了，日常 `npm test` 的水位还是旧的，回退无人报警。
2. **check-round6 探针契约**：H1 读 `TOTAL_CHARACTERS`；H5 读 `data/games.js` 的 `GAMES` 并按 `id !== 'listen'` 计数；H3/H4 的文件路径约定见 §4-#6。内容组交付物路径若不匹配，功能做完门禁照红。
3. **H4 探针偏松**：router 源码含 `speech` 字符串即判过（`check-round6.mjs` L76-79）。#10 应按 ROUND6-ACCEPTANCE「路由 + smoke 断言」的口径在 `smoke.mjs` 加跟读交互断言，防止字符串碰瓷过门禁。
4. **Perf 定标**：acceptance-log-round5b §1 已如实记录 LH 13.4.1 下 87/84 FAIL 与 R5 回归分支 96 的冲突。#10 须锁定 Lighthouse 版本（写进 `test:acceptance` 或文档）再出 Round 6 终数，本审计据此先把 L-M15/M-M16 记 ◐。

---

## 6. 审计方法备注

- 内容计数：`node --input-type=module` 直接 import `characters.js（1000/58）/ books.js（30/240 页）/ idioms.js（60）/ games.js（4）/ etymology.js（65）/ radicals.js（18）/ badges.js（10）`；数学侧经 `register('./scripts/alias-loader.mjs')` 解析 `@/` 别名后 import `wordProblems.js（118；SEMANTIC_TEMPLATES 14 × SCENE_SKINS 6；steps 1/2/3 = 55/40/23）/ visualDemos.js（8）/ achievements.js（18）`。
- 功能有无：按模块逐文件读源码 + 定向 grep（PHASES/pendingNext、demoAfterMistakes、confusable/形近、SpeechRecognition/MediaRecorder/getUserMedia、tesseract/ocr、planUnits/dailyGoal、ageBand、MIN_TEMPLATES、story/lockedStory、pickNextQuestion、数轴/drag、进位/借位 等全库扫描），路由以 `router/index.js` 实际注册为准（识字 15 条 + 重定向、数学 15 条）。
- 门禁计数：`check:round4（4/4）/ round5（12/12）/ round5b（6/6）/ round6（1/7）` 在本 worktree 各实跑一次，退出码与逐行输出为准。
- Lighthouse/axe 未在本轮重测：引用 `acceptance-log-round5.md`（96/100/100）与 `acceptance-log-round5b.md` §1（LH 13.4.1：87/84 FAIL；axe 20/20 + 3×22 全零；gzip 108,149 / 102,651 B）两处实测记录，冲突已按「就低 + 待定标」处理并注明归 #10。
