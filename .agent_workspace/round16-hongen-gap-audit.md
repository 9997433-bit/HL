# Round 16 · 洪恩差距总审计（识字 + 数学 · 体验口径）

> 审计代理：R16 #2（`cursor/r16-hongen-gap-audit-9f67`）· Model slug: claude-fable-5-thinking-high
> 审计基线：`cursor/r16-orchestration-9f67` @ `bcc98d7`（`check:round16` 实测 **0/8**；`check:round15` 实测 **7/8**，仅 H8 环境红，详见 §4-A）
> 审计对象：`apps/literacy-app`（R15 玩认练写说已合入）+ `apps/math-app` 全模块
> 对标口径：洪恩识字（精选一字一动画 + 800 互动）与洪恩数学（「学」动画课 + 应用题视频剖析 + 川川学伴 + 家长报告），沿用 ROUND16-BRIEF 的六张牌

## 0. 一句话结论

R15 之后识字侧「玩认练写说」骨架已经齐了（五步默认从玩起、全库 1820 字 Play 非空、写步先示范再描红），数学侧星球刷题 + 技能图谱 + 错题本也扎实；剩下的差距集中在**四个"密度/可解释"缺口**：① 无字源的 1012 个字在认步仍是一行释义（H2）；② 富 Play 只到 272，前段手感够、中段（u21 以后）全是模板（H3）；③ 数学的「学」只有 8 条数形演示且藏在独立画廊里，刷题前看不到（H4），应用题卡壳时只有两级文字提示、没有图示分步剖析（H5）；④ 两个学伴的台词是「按页面」组织的，不是「按学习阶段」的（H6），家长中心有数据没结论——看得到统计、看不到「这周该练什么」的一句话（H7）。四个缺口都不需要新架构，全部可以在现有组件（CharPlayStage 模板机 / VisualMathDemo 三段契约 / QuizShell / useMascotCoach / ParentView）上做加法。

## 1. 识字 App 模块表（对标洪恩识字）

| 模块 | 洪恩做法 | 咱们现状（代码证据） | 评级 | R16 归属 |
|---|---|---|---|---|
| **玩（进字互动）** | 精选 800 互动，每字进学前情境小游戏 | 五步默认从 `play` 起（`CharDetailView` PHASES=play→intro→listen→trace→speak）；`getCharPlay` 全库 1820/1820 非空；富脚本 `CHAR_PLAY_RICH` **272 条**（u1–u20，seed 驱动 `gen:play:rich` 生成，16 种模板 / tap·drag·swipe·sequence 四类交互），其余 **1548 条**为 radical/theme 模板回填（`templateFallback:true`） | ◐ | **H3**（#5 play-rich-500：272→≥500，优先 u21–u40） |
| **认（字源动画）** | 「根据字源、字义设计每一个汉字动画」，认字即看动画 | 有字源的 **808 字**：`EtymologyStage` 在 intro 步 `autoplay` 默认播（ROUND15_H4 达标）。无字源的 **1012 字**：intro 面板只有 🔊读音按钮 + 释义一行 + 笔画部首一行（`CharDetailView` L742–764 的 `v-if="hasOrigin"` 分支外无任何舞台） | ◐ | **H2**（#4 intro-fallback：部首/零件/组词情境三选一讲解舞台，默认挂载，标记 `ROUND16_H2`） |
| **练（听音选字）** | 听音找字互动 | listen 步：形近字干扰（`similarDistractors`）、两次机会、`useFeedback` 统一音效/粒子/震动 | ✅ | 保持不动，回归保护 |
| **写（笔顺描红）** | 动画引导 + AI 纠错 | `useWriteGuide`（ROUND15_H6）：进 trace 先播整字示范（可跳过）再 `startQuiz()` 描红；同笔连错 3 次自动示范 | ✅ | 保持不动 |
| **说/测（读测领奖）** | 读测过关闯关领奖 | speak 步 = 字义选择 + 原地开奖（星星/徽章，四步真做完才记账）；庆祝走 `feedback.celebrate` 可跳过 | ✅ | 保持不动 |
| **学伴（墨墨）** | 川川全程陪伴、有性格 | `MascotCompanion` + `useMascotCoach`：**按路由场景**（home/learn/games/books…）出 38 条台词，接进度上下文（due/streak/learned），点了会朗读。**没有按学习阶段**（遇新字/连对/该复习/疲劳）的人格剧本，无 `ROUND16_H6` | ◐ | **H6**（#8：阶段化人格剧本，两 App 合计 ≥40 条非占位） |
| **家长中心** | 学习报告推送 | `ParentView`：PIN 门、今日/累计时长、徽章墙、**「建议加强的字」列表**、时长与动效设置。有统计**无周报**：没有「本周弱项一句话 + 建议练习 ≤3」的可解释输出 | ◐ | **H7**（#8：`useWeeklyReport` 本地生成，标记 `ROUND16_H7`） |
| **内容库（超越项）** | 精选内容，订阅解锁 | 绘本 **132** 本 / 古诗 24 / 成语 60 / 儿歌 13（含人声批次）/ 部首馆 / 字源馆，全离线免订阅 | ✅ | 反超点，本轮不动 |
| **街机游戏** | 融在闯关里 | 6 个独立小游戏（听音/迷宫/配对/找不同/拼音/接字），出题绑定已学字 | ✅ | 保持 |
| **跟读 ASR / 拍照识字 OCR** | 无对应 / 无对应 | harness、评测集、离线模型链已备（R11–R14），**真机验证依赖外部设备** | ◐ | BLOCKED 台账（不作硬门槛，见简报） |

## 2. 数学 App 模块表（对标洪恩数学）

| 模块 | 洪恩做法 | 咱们现状（代码证据） | 评级 | R16 归属 |
|---|---|---|---|---|
| **学（概念演示）** | 每个知识点先看动画课再练 | `visualDemos.js` **8 条**演示，三段契约已是「object（实物）→ visual（图形）→ equation（算式）」，`VisualMathDemo.vue` 统一播放/跳过。但：① 8 < 12；② 只在首页工具卡 `/visual-demos` 独立画廊，**刷题入口前看不到**（`skill-practice.js` 仅 mul-table/div-basic 两个技能指过去）；③ 数据路径 `data/visualDemos.js` 不在 H4 探针白名单（见 §4-B） | ◐ | **H4**（#6 learn-demo：扩到 ≥12 技能点 + 练前可跳过演示接线 + `ROUND16_H4`） |
| **练（星球刷题）** | 闯关刷题 | 6 大行星：口算（含竖式逐位）、数感（含凑十）、几何（含七巧板）、逻辑（迷宫/记忆配对）、数独、今日冒险；`QuizShell` 统一判题/两级提示扣星/进度/总结 | ✅ | 保持，回归保护 |
| **应用题** | 视频剖析讲解 | 母题生成器库（手写母题 + 语义模板×场景皮肤笛卡尔积，`wordProblems.js` 1243 行），种子化可复现；题面带线段/实物 `visual`、两级 hint（文字 + 列式）。**无剖析壳**：作答前/中打不开「图示 + 分步 + 变式」的讲解层 | ◐ | **H5**（#7 wp-analysis：`WpAnalysisPanel`，复用母题 `visual`/`equation` 数据，变式=同母题 `make()` 重抽，`ROUND16_H5`） |
| **学伴（小算）** | 川川 AI 学伴 | `MascotBot` + `mascotLines.js` 仅 **14 条**、只有 home/daily 两场景；无阶段化（连对/卡壳/疲劳）人格 | ◐ | **H6**（#8，与墨墨同一契约） |
| **家长中心** | 学习报告 | `ParentView`：时长门禁、周计划视图（`week-plan.js` 按掌握度排）、错题回放（种子化）、静态建议清单。**没有本地生成的「本周弱项一句话 + 建议 ≤3 题」** | ◐ | **H7**（#8：`useWeeklyReport`，从 errorTags/掌握度聚合出一句话 + 3 个练习深链） |
| **技能图谱 / 推荐** | 无明示 | `curriculum.js` **34 技能点** + 依赖图 + 掌握度阈值 + 年龄档（AgeBand）+ 周计划；`ALL_SKILLS_PRACTICE_COVERED` 全技能有练习入口 | ✅ | 反超点；H4 演示按此图谱选 12+ 技能 |
| **错题本 / 成就** | 报告内嵌 | `WrongBook`（errorTags 归因）、`achievements.js`、连击/星星/XP | ✅ | H7 周报的数据源 |
| **护眼 / a11y** | 家长控制 | 休息提醒、时长顺延、reduced-motion 全局 | ✅ | 保持 |

## 3. 差距 → 探针 H1–H8 映射（基线实测 0/8）

| 探针 | 对应差距 | 基线实测（@bcc98d7） | 责任岗 |
|---|---|---|---|
| H1 总审计 | 本文档 | ✗ →（本文交付后 ✓） | #2（本岗） |
| H2 无字源认步动画 | 1012 字 intro 纯文字；无 `IntroFallbackStage`/`ROUND16_H2` | ✗ | #4 |
| H3 富 Play ≥500 | `countRichPlays()=272`，u21 起全模板 | ✗ 272 < 500 | #5 |
| H4 数学学演示 ≥12 | 演示 8 条、独立画廊、数据不在探针白名单路径 | ✗ hit=true, count=0 | #6 |
| H5 应用题剖析壳 | 只有两级文字 hint，无图示+分步+变式层 | ✗ | #7 |
| H6 学伴人格 ≥40 | 两 App 合计 44 条**字符串**已过量口径，但全是场景台词、无阶段剧本、无 `ROUND16_H6` | ✗（marked=false） | #8 |
| H7 家长周报 | 两 App 家长中心有统计无「弱项一句话+建议≤3」 | ✗ | #8 |
| H8 round15 8/8 | 干净环境 7/8：round13 H6 需先 `npm run android:sim` 重建 APK | ✗ 7/8 | #10（见 §4-A） |

## 4. 审计发现（探针结构与路径坑，#3/#10 及实现岗务必先读）

- **A. H8 是环境性红灯，不是功能性**：`check:round15` 在本基线 7/8，唯一红项是它内嵌的 `check:round13` H6（Android 双 APK 产物不在盘上，需先 `npm run android:sim`）。`check-round16.mjs` 的 H8 是**严格 8/8**、没有双腿兜底。#10 必须在验收环境先重建 APK 或在 acceptance-log 里固化「含产物环境实测」口径，否则全轮结构性无法 8/8——与 R15 §2-A 同类问题，这次要提前处理而不是最后补。
- **B. H4 探针路径白名单**：探针只从 `data/learn-demos.js`、`data/skill-learn-demos.js`、`modules/visual-demos/index.js` 里数条目（`skillId:` 或 `id:'…'`），另认 `.agent_workspace/evidence/r16/learn-demo-registry.md` 的 `- xxx` 行。现有 `data/visualDemos.js` **不在名单里**（本轮 hit=true 只因 `modules/visual-demos` 目录存在，count=0）。#6 建议：新建 `data/skill-learn-demos.js` 复用三段契约并 re-export 既有 8 条，加 `ROUND16_H4` 标记，同时落 registry markdown 双保险。
- **C. H3 计数与去重**：探针优先跑 `countRichPlays()`，兜底数 `char-play-seed.txt` 非注释行（须 ≥500 才生效）。富库是 seed 生成物（文件头声明「请勿手改」），#5 的正确姿势是**扩 seed → `npm run gen:play:rich`**。同时 `check:round15` v1.1 的 H3 有 narration 去重门（≥160），新增 228+ 条的 narration 不能互相复制，否则 H8 反被自己打红。
- **D. H6 差的是标记与阶段维度，不是数量**：探针拼接两 App `mascotLines.js` + `useMascotCoach.js` 后数出 44 条字符串（≥40 已过），红在 `ROUND16_H6` 缺失。但按简报口径，光加标记是「仅占位」——#8 要把台词从「按页面」改成「按阶段」（遇新字/连对 N 次/该复习/答错三连/疲劳提醒），且数学侧 14 条明显偏薄，应优先补小算。
- **E. H7 探针文件名单**：只读两 App 的 `ParentView.vue`、`modules/parent`、`composables/useWeeklyReport.js`、`utils/weeklyReport.js`。周报逻辑落在别的路径不算数；建议双 App 各建 `useWeeklyReport.js`（识字从「建议加强的字」+ 复习到期聚合，数学从 errorTags + 掌握度聚合），`ROUND16_H7` 打在 composable 里。
- **F. H2 组件命名白名单**：`ROUND16_H2` 标记只在 `CharDetailView.vue`、`IntroFallbackStage.vue`、`CharIntroStage.vue` 三个文件里找。#4 别自创文件名；接线判定还要求 intro 分支里有 `!hasOrigin`/else 路径挂舞台的结构证据。

## 5. 超越路径优先级（体验视角，非仅过针）

**关键路径：H2/H3/H4 三条互不依赖、可并行；H5 独立；H6/H7 同岗串行；H8 贯穿。**

| 优先 | 缺口 | 建议做法（复用现成积木） |
|---|---|---|
| P0 | **H2 认步回退舞台**（1012 字） | 新建 `IntroFallbackStage`：素材链 = 部首主题（`radicals.js` 全库有 radical）→ 零件拆解（合体字）→ 组词/例句情境（R15 审计已验证全库词句无空洞，如「捏→捏泥人」）。动效直接借 `EtymologyStage` 的 reduced-motion 范本（静态铺开 + aria-live + 手动分帧）。这是把「认=动画学」从 44% 推到 100% 的一步，也是对洪恩「精选字才有动画」的正面反超 |
| P0 | **H3 富 Play 272→≥500** | 扩 `char-play-seed.txt` 到 u21–u40（每单元 ~13 条，共约 +230），照 16 模板写法、narration 必须和字义强相关且互不重复（守 v1.1 去重门）。写完 `gen:play:rich` 再跑 round15 H3 确认 fallback 数同步下降 |
| P0 | **H4 学演示 ≥12 + 练前接线** | 三段契约（实物→图形→算式）**已经是对的**，缺量和入口：① 按技能图谱补到 ≥12（现缺：20 以内进退位、竖式、时间、人民币、图形对称、测量等候选）；② 在 `skill-practice.js`/QuizShell 入口加「先看 20 秒演示（可跳过）→ 再刷题」；③ 数据落探针白名单路径（§4-B） |
| P1 | **H5 应用题剖析壳** | `WpAnalysisPanel`：三屏 = 题面图示（复用母题 `visual.groups` 画线段/实物）→ 分步（复用 `equation` 拆步 + hint 文案升级）→ 变式入口（同母题 `make()` 重抽一道）。挂在 QuizShell 的提示区旁，作答前/中都能开，`ROUND16_H5` |
| P1 | **H6 学伴人格** | 统一契约：`mascotLines.js` 加 `stage` 维度（new-char/combo/review-due/tired/wrong-streak），墨墨补深、小算从 14 条起重写；两 App 合计 ≥40 条**阶段**台词，`ROUND16_H6`。台词继续禁 emoji（要过 SpeechSynthesis） |
| P1 | **H7 家长周报** | 双 App `useWeeklyReport.js`：输出 = 弱项一句话（识字：形近混淆最多的 1 组字；数学：errorTags 频次 Top1 的技能）+ ≤3 个练习深链（识字：`/char/x`；数学：`/practice?skill=x`）。全本地、种子化可复现，这是对洪恩「报告在云端」的隐私反超 |
| P2 | **H8 + smoke** | #9 给 H2 冷门字抽查（沿用 R15 审计五字：日/火/九/妈/捏，其中**九、捏**是 H2 的验收关键用例）+ H4/H5 路由断言；#10 先解决 §4-A 的 APK 环境，再回填 acceptance-log |

## 6. 已领先项（不动，别在本轮为过针弄坏）

- 全库同密度：1820 字五步全通、Play 100% 覆盖（洪恩是精选制）；完全离线、无订阅墙
- 内容矩阵：132 绘本 / 24 古诗 / 60 成语 / 13 儿歌（人声）/ 部首馆 / 字源馆
- 数学骨架：34 技能依赖图谱 + 年龄档 + 周计划 + 种子化错题回放（洪恩无公开等价物）
- a11y：reduced-motion / 可跳过 / aria-live / 自动衔接可按停，全链已过往轮探针——所有 R16 新舞台（H2/H4/H5）必须继承这套约定
