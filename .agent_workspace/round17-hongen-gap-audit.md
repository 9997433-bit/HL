# Round 17 · 洪恩差距总审计（识字 + 数学 · 续 R16 表）

> 审计代理：R17 #2（`cursor/r17-hongen-gap-audit-9f67`）· Model slug: claude-fable-5-thinking-high
> 审计基线：`cursor/r17-orchestration-9f67` @ `f9f8cf1`（`check:round17` 实测 **1/8**，仅 H7 借 r13 报告先绿；`check:round16` 实测 **7/8**，唯一红是 H8 的 APK 环境链，见 §4-A）
> 续写自：`round16-hongen-gap-audit.md`（R16 收口 v1.1 **8/8**）
> 对标口径：洪恩识字（一字一动画 + 800 互动）与洪恩数学（「学」动画课 + 应用题视频剖析 + 川川学伴 + 家长报告），沿用 ROUND17-BRIEF 的五张牌

## 0. 一句话结论

R16 把六个缺口全部推过了门槛线（认步回退舞台全库挂载、富 Play 640、学演示 21、剖析壳、阶段学伴 95 条、双 App 周报），**「有没有」的问题已经解决，R17 要解决的是「够不够好、接没接到、证没证明」**。仍弱的四件事：① **富 Play 覆盖**——640/1820，u41 起仍是模板回填，孩子学到中段手感断崖（H2：→≥900）；② **学演示缺口**——34 技能点只有 21 个有演示，应用题四类母题（差比/倍数/平分/两步）和图形/分类全无（H3：→≥27）；③ **剖析精品化**——`wpAnalysis.js` 是从 `equation` 通用推导的「公式翻译」，不是「老师讲题」，没有一条按母题手写的分步剖析链（H4：≥20 母题手写 explain）；④ **接线与证据**——阶段台词库建好了但单字页没挂学伴、QuizShell 只有空插槽（H5），四条新体验没有一张走查截图（H6），真机 ASR/OCR/APK 台账还停在 r13 的旧报告上（H7）。四件事全是在 R16 交付物上做加法，不动架构。

## 1. 识字 App 模块表（对标洪恩识字）

评级：✅ 达标（保持勿动）· ◐ 半成（R17 有归属）· ❌ 缺失

| 模块 | 洪恩做法 | R16 已完成 | 仍差什么 | 评级 | R17 归属 |
|---|---|---|---|---|---|
| **玩（进字互动）** | 精选 800 互动 | 富脚本 seed 扩到 u40，`countRichPlays()=640`，narration 全去重（640/640），16 模板 4 类交互 | u41–u114 共 **1180 字仍是模板回填**；洪恩 800 精选 vs 咱 640 手写，量上还没反超 | ◐ | **H2**（#4 play-rich-900：seed 续到约 u56，640→≥900，narration 去重 ≥720，`ROUND17_H2`） |
| **认（字源/回退舞台）** | 一字一动画 | `IntroFallbackStage` 上线：无字源 1012 字按「部首主题→零件拆解→组词情境」三选一默认播（ROUND16_H2 ×3 可执行标记），加上字源 808 字 = **认步动画 100% 覆盖** | 覆盖已全，本轮只需回归保护 + 走查截图佐证（H6 第一张图） | ✅ | 保持；H6 取证 |
| **练（听音选字）** | 听音找字 | R15 前已达标（形近干扰/两次机会/统一反馈） | — | ✅ | 保持 |
| **写（笔顺描红）** | 动画引导+纠错 | `useWriteGuide` 先示范再描红、连错自动示范 | — | ✅ | 保持 |
| **说/测（读测领奖）** | 读测过关 | speak 步四步记账 + 原地开奖，可跳过 | — | ✅ | 保持 |
| **学伴（墨墨）** | 川川全程陪伴 | `mascotLines.js` 阶段化（new-char/combo/review-due/tired/wrong-streak），双 App 合计 95 条去重台词，`pickMascotStage` 契约（ROUND16_H6） | **台词库建好了但没接到关键路径**：`CharDetailView` 里 0 处 mascot 引用，孩子学单字全程听不到墨墨的阶段话 | ◐ | **H5**（#7 mascot-wire：单字页接 `useMascotCoach` 阶段台词，`ROUND17_H5`） |
| **家长中心/周报** | 报告推送 | `useWeeklyReport`：弱项一句话 + ≤3 练习深链，全本地（ROUND16_H7） | 逻辑在、缺走查证据（周报是 H6 四图之一） | ✅ | 保持；H6 取证 |
| **内容库（超越项）** | 精选订阅制 | 132 绘本 / 24 古诗 / 60 成语 / 13 儿歌（人声）/ 部首馆 / 字源馆，离线免订阅 | — | ✅ | 反超点，勿动 |
| **街机游戏** | 融在闯关 | 6 小游戏绑定已学字 | — | ✅ | 保持 |
| **跟读 ASR / 拍照 OCR** | 无对应 | harness/评测集/离线模型链已备（R11–R14） | **真机证据仍停在 r13**：无 R17 轮的 `android:sim` 复测或诚实 BLOCKED 台账 | ◐ | **H7**（#10：重跑 `android:sim` 或落 `evidence/r17/device-blocked.md` 含复现命令） |

## 2. 数学 App 模块表（对标洪恩数学）

| 模块 | 洪恩做法 | R16 已完成 | 仍差什么 | 评级 | R17 归属 |
|---|---|---|---|---|---|
| **学（概念演示）** | 每知识点先动画课 | `learn-demos.js` **21 条**三态（实物→图形→算式）演示 + `LearnDemoLauncher` 五处入口 + 练前可跳过接线（ROUND16_H4） | 34 技能点还差 13 个无演示，其中**适合三段契约的至少 8 个全空**：wp-diff（差比）/wp-times（倍数）/wp-share（平分）/wp-two-step（两步）/shape-3d/classify/number-trace/tangram-basic | ◐ | **H3**（#5 learn-demo-plus：21→≥27，优先上列 8 候选，`ROUND17_H3` 或续用 ROUND16_H4 标记文件） |
| **练（星球刷题）** | 闯关刷题 | 六大行星 + `QuizShell` 统一判题/提示/总结，R16 未动 | — | ✅ | 保持，回归保护 |
| **应用题剖析** | 视频剖析讲解 | `WpAnalysisPanel` + `utils/wpAnalysis.js`（ROUND16_H5）：图示→分步→变式三屏，作答前/中可开 | **分步是从 `equation` 通用推导的公式翻译**（「先算 a+b」级别），没有一条按母题手写的「为什么这样列式」讲解；对标洪恩「视频剖析」，通用壳只算及格线 | ◐ | **H4**（#6 wp-explain-hand：≥20 母题手写 `explain` 分步链，`ROUND17_H4`，落探针白名单路径，见 §4-C） |
| **学伴（小算）** | 川川 AI 学伴 | 阶段台词并入统一契约（与墨墨同 95 条池） | **QuizShell 只有 mascot 空插槽**（L488 `<slot name="mascot">`），刷题连对/答错三连时没人说话；`recentWrong` 没接进阶段判定 | ◐ | **H5**（#7：QuizShell 接 `pickMascotStage`，`ROUND17_H5`） |
| **家长中心/周报** | 学习报告 | `useWeeklyReport` errorTags+掌握度聚合，弱项一句话 + 3 深链（ROUND16_H7） | 缺走查证据（H6 四图之一） | ✅ | 保持；H6 取证 |
| **技能图谱/推荐** | 无明示 | 34 技能依赖图 + 年龄档 + 周计划，全技能有练习入口 | — | ✅ | 反超点；H3 按此图谱选缺口技能 |
| **错题本/成就** | 报告内嵌 | errorTags 归因、种子化回放 | — | ✅ | H4 变式与 H5 `recentWrong` 的数据源 |
| **护眼/a11y** | 家长控制 | 休息提醒、reduced-motion 全局 | — | ✅ | 保持；所有 R17 新面板必须继承 |

## 3. 差距 → 探针 H1–H8 映射（基线实测 1/8 @f9f8cf1）

| 探针 | 对应差距 | 基线实测 | 责任岗 |
|---|---|---|---|
| H1 差距续表 | 本文档 | ✗ →（本文交付后 ✓） | #2（本岗） |
| H2 富 Play ≥900 | rich=640 < 900，去重 640 < 720，无 `ROUND17_H2` | ✗ | #4 |
| H3 学演示 ≥27 | 标记/三态/可跳过全 true，**计数 21 < 27** | ✗ | #5 |
| H4 精品剖析 ≥20 | 白名单三文件里无 `ROUND17_H4`，计数 0 | ✗ | #6 |
| H5 学伴关键接线 | 无 `ROUND17_H5`；台词库在、页面没挂 | ✗ | #7 |
| H6 走查证据包 | `evidence/r17/walkthrough.md` 不存在（doc=0） | ✗ | #8 |
| H7 真机/BLOCKED | 借 r13 `android-sim/report.json` 已过针，但按简报口径应补 R17 轮新台账 | ✓（弱绿） | #10 |
| H8 round16 8/8 | 干净 VM 7/8：round13 H6 双 APK 不在盘（环境性，非功能性） | ✗ 7/8 | #10（§4-A） |

## 4. 审计发现（探针结构与路径坑，实现岗务必先读）

- **A. H8 仍是那条 APK 环境链**：`check:round16` H8→`check:round15` H8→`check:round13` H6，红在双 APK 产物不在干净 VM 盘上。这与 R16 §4-A 完全同源，且 R17 的 H7 恰好要求 `android:sim` 闭环——#10 应把两件事合并做：验收环境先 `npm run android:sim` 重建双 APK（顺手产出 `evidence/r17/android-sim-report.md`），H7 从「借 r13 旧报告的弱绿」升级为本轮实测，H8 随之转绿。若 SDK 不可得，则落 `device-blocked.md`（必须含 `BLOCKED` 字样 + `npm run android:sim` 复现命令，探针按此判定）。
- **B. H2 的两道门与 seed 位置**：探针跑 `countRichPlays()` 须 ≥900，且 `listRichPlays()` 里非 fallback 条目的 narration **去重后 ≥720**。seed 在 `apps/literacy-app/scripts/data/char-play-seed.txt`（不是 src/data 下），现覆盖 u1–u40 共 640 行；每单元 16 字，+260 条即续写到约 **u56**。富库 `char-play-rich.js` 是生成物（文件头声明勿手改），正确姿势仍是**扩 seed → `npm run gen:play:rich`**。`ROUND17_H2` 标记只认三个文件：`char-play.js` / `char-play-rich.js` / `gen-char-play-rich.mjs`（生成器模板里加最稳）。注意 round15 H3 的 narration 去重门（≥160）与本轮 ≥720 叠加生效，新写 260 条不能互相复制、也不能撞旧 640 条。
- **C. H4 探针白名单只有三条路径**：`utils/wpAnalysis.js`、`data/word-problem-explains.js`、`modules/word-problems/explains.js`。手写剖析落在别处不算数。计数逻辑数的是这三个文件里 `id:`/`masterId:`/`problemId:` 的出现次数（须 ≥20）+ `ROUND17_H4` 标记。#6 建议新建 `data/word-problem-explains.js`：每条 = `{ masterId, steps: [讲解句…], why: 为什么这样列式 }`，键回 `wordProblems.js` 的母题 id，`WpAnalysisPanel` 优先取手写、无则回落通用推导——这样通用壳仍兜底全量，精品层覆盖高频 20+。
- **D. H3 计数是「标记文件内 skillId 去重」**：探针扫 `apps/math-app/src` 里含 `ROUND17_H3` **或** `ROUND16_H4` 的文件，拼接后数 `skillId:'…'`/`demoId:'…'` 去重。现 21 条全在 `learn-demos.js`（已带 ROUND16_H4），所以 #5 直接在同文件续写 +6 即达 27，无需新标记；但注意三态（实物/图形/算式）与「跳过」关键字必须继续出现在标记文件拼接文本里——续写条目沿用现有 schema 就天然满足。候选优先 wp-diff/wp-times/wp-share/wp-two-step（补齐应用题四类母题的「学」，与 H4 剖析形成同一批技能的学-练-讲闭环），再补 shape-3d/classify。
- **E. H5 是接线不是写台词**：95 条阶段台词与 `pickMascotStage(ctx)` 契约都在（ROUND16_H6），红的只是消费端。探针要求含 `ROUND17_H5` 的文件拼接文本同时命中「CharDetail/useMascotCoach/QuizShell/recentWrong/pickMascotStage 之一」+「mascot/学伴/台词/stage 之一」。#7 两侧各接一处即可：识字侧 `CharDetailView` 按步骤切换喂 ctx（新字=new-char、speak 完成=combo）；数学侧 QuizShell 用现成 mascot 插槽 + `recentWrong` 喂 wrong-streak。台词继续禁 emoji（SpeechSynthesis 约束）。
- **F. H6 证据引用必须落盘**：探针从 `walkthrough.md`（>400 字）里抓 `evidence/r17/*.png|jpg|webp|mp4` 路径并核对文件存在，须 ≥4 张且覆盖「认步回退 / 学演示 / 剖析 / 周报」四关键词。#8 注意路径写相对 `.agent_workspace/` 的 `evidence/r17/xxx.png` 形式；截图工具产物先落盘再写文档，防「引用了不存在的图」被 fileHits 打红。

## 5. 超越路径优先级（体验视角，非仅过针）

**关键路径：H2/H3/H4 三条互不依赖可并行；H5 独立小改；H6 依赖前四条出货后取证；H7/H8 同岗合并处理。**

| 优先 | 缺口 | 建议做法（复用现成积木） |
|---|---|---|
| P0 | **H2 富 Play 640→≥900** | seed 续 u41–u56，照 16 模板写法、narration 与字义强相关且全库不重复；写完跑 `gen:play:rich` + round15 H3 + round17 H2 三针确认。这是把「随手点开是手写关」从前 40 单元推到前 56 单元的一步 |
| P0 | **H3 学演示 21→≥27** | 在 `learn-demos.js` 续写 6+ 条，优先应用题四类（wp-diff/times/share/two-step）+ shape-3d/classify；三段契约与 `LearnDemoLauncher` 入口自动继承，无新接线 |
| P0 | **H4 剖析精品化 ≥20** | 新建 `data/word-problem-explains.js` 手写 20+ 母题分步链（每步一句「老师话」，讲为什么不只讲怎么算），`WpAnalysisPanel` 优先手写、回落通用推导；变式入口沿用 `make()` 重抽 |
| P1 | **H5 学伴关键接线** | 单字页 + QuizShell 各一处消费 `pickMascotStage`，`ROUND17_H5`；不新写台词，只接线 + 喂上下文（combo/wrong-streak/review-due） |
| P1 | **H6 走查证据包** | 四图：无字源冷门字（九/捏）认步舞台、新增学演示播放中、手写剖析面板、家长周报；`walkthrough.md` 按图配「操作路径 + 预期 + 实见」 |
| P1 | **H7+H8 合并** | 先 `android:sim` 重建双 APK（H8 链转绿）顺手出 R17 报告（H7 实绿）；SDK 缺则诚实 BLOCKED 台账，两针口径见 §4-A |

## 6. 已领先项（不动，别在本轮为过针弄坏）

- 全库同密度：1820 字五步全通、Play 100% 覆盖、**认步动画 100% 覆盖（R16 新反超点，洪恩是精选制）**；完全离线、无订阅墙
- 内容矩阵：132 绘本 / 24 古诗 / 60 成语 / 13 儿歌（人声）/ 部首馆 / 字源馆
- 数学骨架：34 技能依赖图谱 + 年龄档 + 周计划 + 种子化错题回放 + 全本地可解释周报（洪恩报告在云端，咱隐私反超）
- a11y：reduced-motion / 可跳过 / aria-live 全链已过往轮探针——R17 新增的剖析精品层、学伴接线、演示条目必须继承这套约定
