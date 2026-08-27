Model slug: claude-fable-5-thinking-xhigh
# Round 9 · 洪恩模块对标审计（R9 八项交付终验）

> 审计人：Round 9 子代理 #2（fable）
> 审计基线：分支 `cursor/r9-module-audit-9f67`（自 `cursor/openmoji-integration-9f67` @ `fa875cf`，即 **Round 9 八项交付全部合入**后的集成线 HEAD）
> 审计日期：2026-08-27 · Node 22.14.0 · worktree `/tmp/wt-r9-audit`（干净树）
> 方法：**逐文件重新走读源码**（不照抄 R8 审计结论），每条状态附文件路径证据；
> 内容体量用 `node --input-type=module` 实际 import 数据文件统计（数学侧经 `--import ./scripts/register-alias.mjs` 解析 `@/` 别名）；
> `check:round9 / check:round8 / check:round7 / check:round6 / 识字 check:data / 数学 check:content` 各实跑一次，退出码与逐行输出为准；跟读 PoC 单测与 OCR 精度基准另行实跑取一手数字。
> **口径说明**：本轮审 **R9 八项深度交付相对 Round 8 终态（`ec733bb`）的变化**。Round 8 终态 = R8 八项交付全部合入、`check:round8` 8/8、`check:round9` 1/8（有意红灯，仅 H8 绿，见 ROUND9-ACCEPTANCE §4.1）；该起点下 31 项对标 = ✅ 27 / ◐ 4 / ❌ 0，四个 ◐（L-M5/L-M9/L-M10/L-M11）全部对应 R9 简报的四条深度杆。

---

## 0. 门禁实测（fa875cf，本机实跑，一行表）

| 门禁 | 退出码 | 结果 | 关键数字 |
|---|---|---|---|
| `check:round9` | **0** | **8/8** | H1 儿歌 **13 首合规** + 歌词同步 v2 + smoke · H2 **9 张有效基准图（handwriting 2 张）** + tier 接进精度脚本 · H3 推荐路径函数+视图+smoke · H4 doc=true 且 poc=true · H5 投稿文档 · H6 CI 版本锁+阈值断言 + evidence/r9 **2 份 JSON** · H7 报告+清单 · H8 R8 8/8 |
| `check:round8` | **0** | **8/8** | H1 字源 808 · H2 剧情 99 条 + **儿歌 13 首**（`/songs/:id?`）· H3 图谱 34 节点/30 边 · H4 OCR 三重信号 + 形近池 · H5 跟读 v2 + smoke · H6 LH 识字 98/100/100 · 数学 99/100/100 + r8 证据 · H7 报告终验 · H8 R7 8/8 |
| `check:round7` | **0** | **8/8** | H1 `/ocr` · H2 形近 1817 组 + 双接线 · H3 字源 808 · H4 年龄档 6/6 · H5 `/memory-pairs`+`/maze` · H6 aurora 32 tokens/THEMES 4 · H7 全局报告 31/31（31 达标、0 在途） |
| `check:round6`（抽查） | **0** | **7/7** | 字库 1820 · 绘本 132 零越界 · 古诗 24 · 跟读三重接线 · 小游戏 5 款 · 母题 214 |
| 识字 `check:data` | **0** | **71/71** | 统计行：`1820 字 / 99 单元 / 18 偏旁 / 132 本绘本（1121 页，557 不重复用字）/ 60 成语 / 808 字字源 / 13 首儿歌（52 句，147 不重复用字）/ 99 条单元剧情`；儿歌组探针（≥3 首、song-index 一致、id 无重复、verifySongCoverage 零未学字、每首 4+ 句速度 60–110、每分区有歌）全绿 |
| 数学 `check:content` | **0** | **全部通过** | 母题 214（28 标签/42 场景，93/86/35）· 年龄档 L1–L5 × 6 玩法 · **新增行「技能图谱推荐：首推 10以内加法（差一点），L1–L5 目标 L1→10以内比大小 1 步 … L4/L5→平均分与包含除 6 步」** · 图谱 34/30/6 泳道 L1–L5 覆盖 6→17→26→34→34 · 数独三档唯一解 · 比大小 3000 · 每日 400 天 · 迷宫 200 座 10294 步最短路 · 配对 1000 副 · 弱项 3719/4000 |

**这是九轮以来第一次：当轮硬门槛在审计时点即 8/8**（R4–R8 审计时点均为有意红灯），因为本轮审计排期在功能合入之后——R9 七个功能位全部交付并通过 v1.1 加固探针（v1.1 相对 v1.0 堵掉 8 处恒真/占位漏洞，修订记录见 ROUND9-ACCEPTANCE §2）。

**内容体量实测（import 数据文件直接计数）**：

| 指标 | 本轮实测 | 主计划/R9 终点 | 达成率 | Δ vs Round 8 终态（ec733bb） |
|---|---|---|---|---|
| 识字字库 | **1820 字 / 99 单元** | 1800 | 101% | = |
| 分级绘本 | **132 本 / 1121 页**，零越界 | 130 | 102% | =（新增**投稿规范**见 H5） |
| 成语 / 古诗 | **60 条 / 24 首** | 60+ / 20 | 100% / 120% | = |
| 小游戏（不含 listen） | **5 款** | ≥5 | 100% | = |
| 形近字库 | **1817 组**（覆盖 ≥95%） | — | 维持 | = |
| 字源动画 | **808 字**（无重复） | 800 | 101% | 计数 =，**13 条形声字 origin 手工改稿**（a76af74） |
| 手写单元剧情 | **99 条**（`TOTAL_UNIT_STORIES`） | 99 | 100% | 计数 =，**7 条改稿去模板骨架**（5e99fbf） |
| 儿歌 | **13 首 / 52 句 / 147 不重复用字** + 歌词-旋律同步 v2 | R9 杆 ≥10 或 v2 | **130%（双达标）** | **7 → 13 首**，v2 动画（预备拍/进度/留痕/音高抬升） |
| OCR 精度基准 | **10 张图 / 8 类版面，总召回 55/55（100%）**，逐 tier 定线 | R9 杆 ≥8 张含手写 tier | 达标（fixtures 9 张 + 样例 1 张） | 5 张 1 tier → 10 张 8 tier（handwriting/low-light/busy-bg/perspective 为新增） |
| 应用题母题 | **214 个**（93/86/35） | 185 | 116% | = |
| 技能图谱 | 34 节点 / 30 边 / 6 泳道 + **`recommend()`/`recommendPath()` 只读推荐层** | 推荐路径 + 视图 + smoke | 100% | `nextSkills` 平铺 → 理由分层推荐 + 依赖有序补课路线 |
| 跟读 | 三档降级 + 学伴对话 + **ASR 评估文档 + `phonemeMarks`/`similarityV2` PoC** | 评估文档或 PoC（二选一） | **双交付** | v2 → v3 路线定盘（sherpa-onnx 首选） |
| 徽章 / 成就 | 识字 11 枚 / 数学 18 项 | 维持 | — | = |
| Lighthouse（12.8.2 mobile，evidence/r9 原始 JSON 本轮解析复核） | **识字 98/100/100 · 数学 98/100/100** | 双 App P ≥ 95 | 双达标 | 识字 98 维持 · 数学 99→**98**（-1，仍超线 3 分；测量 commit `e1cdced`） |
| 首屏 JS gzip | 识字 **109,539 B** / 数学 **88,735 B**（evidence/r9/acceptance-output.txt L285-292） | <420 KB / <250 KB | 达标 | ≈=；**数学 `check-bundle.mjs` 本轮补齐并挂进 `npm test`**（两轮流程债清账） |
| zip / Android | literacy **6,252,719 B** · math **458,315 B** · check:android **26/26**（acceptance-log-round8 §4，#10 R8 收口终验实测） | <10 MB · 26/26 | 达标 | R8 值 6,228,970/455,047 → 终验重出包微涨（儿歌 v2 前） |

---

## 1. 识字 App 对标表（L-M1 … L-M15）

图例：✅ 达标 / ◐ 有 MVP 但缺洪恩级深度 / ❌ 未实现。「Δ」列 = 相对 Round 8 终态（ec733bb 起点口径：✅ 27 / ◐ 4）。

| 模块 | 洪恩能力 | 状态 | Δ | 实测证据（文件路径 + 关键事实） | 后续归属 |
|---|---|---|---|---|---|
| L-M1 | 1800 常用字分级 | ✅ | = | `data/characters.js` 1820 字 / 99 单元；`check-data.mjs` ≥1800 门禁 + 懒加载分包 + 420 KB 预算维持 | 维护 |
| L-M2 | 认-读-写-玩闭环（状态机） | ✅ | = | `views/CharDetailView.vue` `PHASES` intro→trace→listen→quiz→reward + `pendingNext` 可按停维持 | 维护 |
| L-M3 | 笔顺+描红判定 + 错3次示范 | ✅ | = | `components/HanziStrokeBox.vue` `demoAfterMistakes: 3` + 慢放示范维持 | 维护 |
| L-M4 | 听音识字 + 形近干扰 | ✅ | = | `similar-chars.js` 1817 组 + `distractors.js` 双接线维持；本轮 OCR 精度脚本又加 4 条形近复核探针（`test-ocr-accuracy.mjs` L404-456） | 维护 |
| L-M5 | 130 本分级绘本 | ✅ | **◐→✅** | 内容面维持（132 本 / 1121 页零越界）。**R9 #7 交付清账**（038c5b6）：`.agent_workspace/BOOK-COMMUNITY-SUBMISSION.md` **16,789 字符**——顶层 schema 逐字段（§3.1-3.4：分级字表约束/多音字/页数下限/contributor 授权）+ draft 2020-12 JSON Schema 全文（§3.5，可直接喂 ajv）+ A 类机器硬拦截 10 条/B 类人工评审（§4）+ 本地自检命令链（§5，gen:books → check:data）+ 合格/退稿双示例（§6，14 个 fenced 块）。**R6→R7→R8 三轮备忘就此销账**。check:round9 H5 绿 | 维护（§7 自列 import 脚本 + ajv CI 两项 → R10） |
| L-M6 | 800+ 字源互动 | ✅ | = | 808 字无重复维持（本轮 import 复核 `etymology-index.js` 808/808）；**质量债改稿**（a76af74）：13 个今义跑出形旁共性的形声字（汽/滑/测/洞/汰/治/法/艺/英/机/校/村/极）在 `etymology-seed.txt` 加「本来是什么」覆盖位，`gen-etymology.mjs` xing 行放开可选第 5 段——「治本来是治水、校本来是木栅栏」替换掉自相矛盾的模板句；parts/evolve 不动，check:data 的形旁/读音一致性探针照跑全绿 | 维护 |
| L-M7 | 记忆曲线复习 | ✅ | = | `utils/srs.js`（FSRS-lite）+ 热力图维持；红线「FSRS 不动」九轮未破 | 维护 |
| L-M8 | 成语/古诗国学 | ✅ | = | 成语 60 + 古诗 24 + 三件套维持 | 维护 |
| L-M9 | AI 学伴/跟读评测 | ✅ | **◐→✅** | v2 存量完好（三档降级 + `allowRecognition` 默认关 + 学伴对话 `companionReplyForResult`，R8 H5 探针绿）。**R9 #8 双路线交付**（4da6a22/bcaf5ad）：① 评估文档 `.agent_workspace/r9-followread-asr-evaluation.md`（**≈9.4K 字符**，sherpa-onnx 首选/Vosk 对照/whisper.cpp 上限对照/Leopard 淘汰的五方案对比表，含包体/RTF/内存/许可证四维；三档降级契约明文「本地引擎失败只降 recording、不静默切可联网的 Web Speech」；Go/No-Go 五层门槛 + 300 条儿童冻结集方案 + A–D 分阶段路线）；② 纯函数 PoC `utils/speechEval.js` L100-250：`phonemeMarks()`（编辑距离对齐 + 注入式拼音 → hit/tone/near/miss 四档标记）+ `similarityV2()`（hit=1/tone=0.5/near=0.25），**带 ROUND9_H4 标记、不接 UI、不改 evaluate()、三档降级零改动**；单测本轮实跑 **14/14**（含 v3 声调/近音/漏字保守判定 3 条新用例）。文档诚实度高：明言「tone 只是 ASR 选字的拼音差异，不能证明声波里的调型读错」 | R10：sherpa-onnx Worker spike + 隐私文案修正（见 §5-2） |
| L-M10 | 拍照识字 | ✅ | **◐→✅** | **R9 #5 扩样定标闭环**（d5d2ae5/baf7123/8f8e621）：基准集 5→**10 张图 / 8 类版面**（print×2/warm-light/inverted/blur + 新增 **handwriting×2/low-light/busy-background/perspective**），`fixtures/ocr/` 9 张有效 PNG（最小 9,531 B，全过魔数校验）；`test-ocr-accuracy.mjs` **逐图召回/关键字/误检额度/置信度四重断言 + 逐 tier 汇总 + `MIN_IMAGES=8` + `REQUIRED_TIERS` 四类钉死**（删图砍 tier 当场红灯）；本轮实跑 **20/20，总召回 55/55（100%），单图 24–88ms**，唯一误检为复杂背景 tier 的「司靶」2 字（单独 3 字额度，写进阈值而非掩盖）。**边界如实声明**：手写 tier 为 `gen-ocr-benchmark.mjs` 逐字抖动（JITTER 写死保证字节可复现）模拟，「认不出真人手写是已知边界，这张守的是模拟手写不整页塌」（脚本 L109-110 + 验收片段 §2 明文）；低光 82px 归零踩坑记录在案（acceptance-log-round9-h2 §4） | R10：真实拍摄样张 + Android WebView 实测 |
| L-M11 | 动画儿歌/IP | ✅ | **◐→✅** | **R9 #4 交付闭环**（09a957a）：`data/songs.js` **13 首 / 52 句**（7→13，新开「一家人」分区；id 无重复、`verifySongCoverage()` 零未学字、notes 逐字对齐，check:data 儿歌组 6 探针全绿）；**歌词同步 v2**（`SongsView.vue` +330 行）：三拍预备拍（`COUNT_IN_BEATS=3`，试出来的）+ 唱过留浅底 + 真实时间进度条 + **`pitchOfNote()` 音名→0-1 相对高度驱动 `--pitch` CSS 变量**（字按音高抬升 + 音高带同步走，关音效也看得见旋律线）；reduced-motion 下位移全停、颜色/进度/音高带保留。smoke 新增 **128 行 ROUND9_H1 交互断言**（曲库 ≥10、`data-song-sync=v2`、音高带点数=第一句字数、预备拍期间零高亮、两帧对比进度/留痕/≥3 种音高推进、停一停全清）。99 条剧情侧另有 7 条质量改稿（5e99fbf：u63/68/72/74/79/80/87 告别「四个引号字并排」骨架） | R10：旋律资产升级（合成音→曲库/录制） |
| L-M12 | 字迷宫/跑酷等小游戏 ≥5 | ✅ | = | `data/games.js` 6 款（listen + 5），路由 + smoke/axe 覆盖维持 | 维护 |
| L-M13 | 家长控制/防沉迷 | ✅ | = | 口算门 + 导出/导入 + 每日时长 + `planUnits` + `dailyGoal` 维持 | 维护 |
| L-M14 | 奖励/徽章体系 | ✅ | = | `data/badges.js` 11 枚 + `BadgeShelf.vue` + `dailyQuest.js` 维持 | 维护 |
| L-M15 | 性能/无障碍/离线 | ✅ | = | **R9 #9 复测归档**：LH 12.8.2 mobile **识字 98/100/100**（`evidence/r9/lighthouse-literacy-app.json` 本轮解析复核 categories 0.98/1/1、formFactor mobile）；axe **22 路由 + 4 主题 × 24 状态 critical=0 serious=0**（acceptance-output.txt 尾部全 PASS，aurora 主题在列）；首屏 gzip 109,539 B。R8 审计留一手的「axe 原始 JSON 归档」以 acceptance-output.txt 全文归档形式落地 evidence/r9 | 维护 |

**识字小计：✅ 15 / ◐ 0 / ❌ 0（共 15 项）**（Round 8 终态：✅ 11 / ◐ 4——**识字侧首次满盘**）

---

## 2. 数学 App 对标表（M-M1 … M-M16）

| 模块 | 洪恩能力 | 状态 | Δ | 实测证据（文件路径 + 关键事实） | 后续归属 |
|---|---|---|---|---|---|
| M-M1 | 3–12 岁 L1–L5 年龄档 + 技能图谱 | ✅ | =（深化） | 年龄档 6/6 消费 + 图谱三重接线维持。**R9 #6 推荐层**（f089211/ecd2bbc/026fd60）：`skill-graph.js` 新增 `recommend()`（**四类理由分层**：finish 差一点 48 分 > base 补基础 34 > focus 本档主推 30 > ahead 超前挑战 12，掌握度接近阈值加分、超档扣分、**下游闭包 `REACH` 加权**「挡着五个技能的点数比零下游的描红更值得先练」，每条带 `why` 人话理由）+ **`recommendPath(id, mastery)`**（目标技能 + 未过线前置按依赖序排出补课路线，已过线不出现——「还要练几步不是族谱」）+ `pickGoal()`（本档最下游未拿下者为目标）；本轮实测 `recommend({L2 存档})` 首推 `add-within-10/finish`、目标 `wp-remain` 路线 3 步，`recommendPath('sub-within-100',{})` = 6 步依赖有序。**视图**：`SkillGraphView.vue` 图上推荐位描圈标序号 + 「推荐下一步」侧栏（`data-reco-item/reason/rank`）+ **只读声明**（`data-reco-readonly` 含「不写进度」）。**smoke**（数学侧 ROUND9_H3_SMOKE，026fd60 补代码级常量防剥注释）：L1/L2/L4 三档 `audit()`（只推 learning/ready、序号连续、图圈=列表逐 id 对齐、超前不插队、路线终点=目标、路线依赖序、已掌握不混入）+ **换档只换排序不换判读**（statusLine 相等断言）+ **逛完一圈 localStorage 掌握度逐 id 相等、无新增键、星星不动**——「只读推荐不写回」红线是行为级验证，非口号。check:content 新增推荐行（L1–L5 目标与步数）常驻门禁 | R10：推荐 × 错题本/每日冒险闭环 |
| M-M2 | 1000+ 互动/无限题 | ✅ | = | mulberry32 + `questionId()` + 母题 ≥185 门禁 + 2000 道压测维持 | 维护 |
| M-M3 | 185 应用题母题 | ✅ | = | `wordProblems.js` 214 个（93/86/35），28 标签 / 42 场景 | 维护 |
| M-M4 | 数感/比较/运算 | ✅ | = | `/number-sense`、`/compare`（3000 道）、`/arithmetic`、`/column-arithmetic` 维持 | 维护 |
| M-M5 | 几何/空间 + 七巧板 | ✅ | = | `GeometryView.vue` + `TangramView.vue` 维持 | 维护 |
| M-M6 | 逻辑/规律 + 配对/迷宫 | ✅ | = | `/memory-pairs` + `/maze` + 内容门禁（200 座最短路 / 1000 副）维持 | 维护 |
| M-M7 | 数独专项 | ✅ | = | 4/6/9 三档唯一解（200/60/12 局）+ 年龄档消费维持 | 维护 |
| M-M8 | 数形结合演示 | ✅ | = | `visualDemos.js` 8 类三段契约维持 | 维护 |
| M-M9 | 自适应难度 | ✅ | = | 弱项抽中 3719/4000、错题优先 2868:1132 绿 | 维护 |
| M-M10 | 错题本 | ✅ | = | `wrongBook` questionId 级 + 重练维持 | 维护 |
| M-M11 | 计算专题/速算 | ✅ | = | `/sprint` + 口算连击 + 竖式维持 | 维护 |
| M-M12 | 剧情关卡地图 + 日冒险 | ✅ | = | 章节契约 + `daily.js` 400 天可复现维持 | 维护 |
| M-M13 | 互动教具 ≥3 | ✅ | = | 拖拽计数 + 数轴 + 分与合维持 | 维护 |
| M-M14 | 家长面板 | ✅ | = | 口算门 + 雷达 + 错因 + 导出/导入 + 年龄档选择器维持 | 维护 |
| M-M15 | 奖励/成就 | ✅ | = | `achievements.js` 18 项 + 动效可关维持 | 维护 |
| M-M16 | 性能/无障碍/离线 | ✅ | =（-1 分记录在案） | LH 12.8.2 mobile **数学 98/100/100**（`evidence/r9/lighthouse-math-app.json` 复核 0.98/1/1）——较 R8 终验 99 回落 1 分（推荐层新面渲染），仍超 95 线 3 分；axe 双 App 全绿。**流程债清账**（93b805c1 系）：`apps/math-app/scripts/check-bundle.mjs` 落地（module 入口静态 import 追踪 + 逐资源 gzip 合计 <250 KiB）并挂进数学 `npm test` 链（package.json L12-13）——R8 审计 §5.7 两轮欠账销；实测 88,735 B（预算的 35%）。`scripts/lighthouse-ci.mjs` 版本锁见 §3-H6 | 维护 |

**数学小计：✅ 16 / ◐ 0 / ❌ 0（共 16 项）**（Round 8 终态：✅ 16 / ◐ 0——满盘维持，M-M1/M-M16 深度加码）

---

## 3. R9 八项交付逐项终验（相对 Round 8 终态的变化）

> 每项给出：交付内容 → 探针/实测证据 → 审计判定。全部在 `fa875cf` 实测。

### H1 儿歌 v2（#4，◐→✅ 的 L-M11 主体）

- **变化**：7→**13 首**（52 句 / 147 不重复用字），新分区「一家人」；同步动画 v1「逐字亮一下」→ v2 三件套（预备拍 / 进度条+留痕 / **音高驱动的字抬升与音高带**）。
- **实证**：`SONGS` import 计数 13、id 无重复、`verifySongCoverage()` 返回空数组（零未学字）、`song-index.js TOTAL_SONGS=13` 一致；smoke 128 行交互断言（见 L-M11 行）实测在 check:round9 输出中过绿；reduced-motion 契约在 smoke 里显式分档（quiet 时不验位移只验 `--pitch`）。
- **判定**：**闭环**。R9 杆是「≥10 首**或** v2」，实际双达标。R8 H2 的 ≥3 首 + 路由存量探针同步验绿（输出行已更新为 13 首）。

### H2 OCR 扩样（#5，◐→✅ 的 L-M10 主体）

- **变化**：基准 5 张 1 类 →**10 张 8 类**（fixtures 9 张 + public 样例 1 张），新增 handwriting×2/low-light/busy-background/perspective 四 tier 且 `REQUIRED_TIERS` 钉死；断言 14→**20 项**；`--json` 输出 `marker: ROUND9_H2, supersedes: ROUND8_H4` 逐 tier 机读。
- **实证**：本轮实跑 20/20、总召回 **55/55（100%）**、逐 tier 100%、复杂背景误检「司靶」2 字（额度 3）；PNG 逐张魔数 + ≥1KB 校验由探针执行（v1.1 堵掉 0 字节占位洞）。
- **边界如实**：手写 tier 为程序合成抖动模拟（JITTER 固定保证字节可复现），验收片段 §2 明文「不是宣称支持手写」；深底浅字 82px 整页归零的引擎坎已记录成回归口径（§4）。
- **判定**：**闭环**（测量驱动原则下 L-M10 转 ✅ 成立：固定基准集 + 逐 tier 阈值 + CI 挂载三件齐全）。真实样张归 R10。
- **小失配**：`acceptance-log-round9-h2.md` 实测表停在 9 张 51/51（8f8e621 补第二张 handwriting 图后未回写），现状为 10 张 55/55——数字更好，但片段应随图集更新，记 §5-4。

### H3 图谱推荐（#6，M-M1 深化）

- **变化**：R8 `nextSkills()` 平铺「下 4 个」→ R9 **理由分层推荐 + 依赖有序补课路线 + 图上描圈/侧栏双呈现**；v1.1 探针特意把 R8 存量 `nextSkills` 判为不算数（基线 reco=false 已验证），要求 R9 专属信号——`recommendPath()` 命名精确命中。
- **实证**：纯函数直接调用验证（见 M-M1 行）；smoke 三档行为级审计 + **localStorage 字节级只读断言**；check:content 新增推荐常驻行。
- **判定**：**闭环**，且是八项中行为级验证最重的一项（简报「只读推荐不写回作弊」红线有真实探针看住）。

### H4 跟读 ASR 路线（#8，◐→✅ 的 L-M9 主体）

- **变化**：探针二选一（文档或 PoC），实际**双交付**：≈9.4K 字符评估文档（五方案对比 + Go/No-Go 五层门槛 + 分阶段路线 + 儿童冻结集方案）+ `phonemeMarks`/`similarityV2` 纯函数 PoC（带 ROUND9_H4，不接 UI、不改 evaluate、单测 14/14）。
- **红线复核**：三档降级源码零改动（diff 只增不改）；`allowRecognition` 默认关维持；PoC 无新依赖、无模型下载、无 CDN。
- **判定**：**闭环**。文档质量显著高于「800 字符水文」判定线：明确拒绝把通用 ASR 汉字转写冒充音素评分，是全项目对能力边界最诚实的一份技术文档。
- **移交项**：文档 §3.2 自己点名 `FollowReadView.vue` L111「两种都不会把声音传到别的地方」表述与 `SpeechRecognition` 可能联网的事实不一致，**本轮未修**——记 §5-2 归 R10（或 v3 接线前必改）。

### H5 绘本投稿（#7 上半，◐→✅ 的 L-M5 主体）

- **变化**：三轮备忘 → 16,789 字符规范（schema 全文可喂 ajv + A/B 两类校验 + 自检命令链 + 合格/退稿双示例）。
- **判定**：**闭环**。§七 自列两项未落地（`import-book-submission.mjs` 自动导入脚本、CI ajv 步）姿态诚实，归 R10。
- **小误**：§五 写「内容自检（61 项）」，实际 check:data 已是 **71 项**（儿歌组 R8 末加入）——不影响可执行性，记 §5-4。

### H6 Perf CI（#9）

- **变化**：`scripts/lighthouse-ci.mjs` 落地——**三重版本锁**（package.json 声明 === 12.8.2、node_modules 安装版本 ===、生成报告 `lighthouseVersion` ===，任一漂移非零退出）+ 阈值断言（P ≥ 0.95，`ACCEPTANCE_MIN_LH_PERFORMANCE` 只许调高不许调低）+ 证据归档（报告缺失即 FAIL）；`test:lighthouse:ci` 进根 scripts；`evidence/r9/` 归档 2 份 LH 原始 JSON（各 ~490KB，本轮解析复核）+ acceptance-output.txt 全文（含 axe 22 路由 + 4×24 状态全绿、双 App 首屏 gzip）+ README 索引（测量 commit `e1cdced`、benchmarkIndex 在案）；**数学 check-bundle.mjs 补齐挂链**（两轮流程债清）；`ANDROID-DEVICE-CHECKLIST.md` 真机走查清单（低档/中高档双机位、出包/安装/权限/离线/性能/回归七段）。
- **判定**：**闭环**。清单为「可照做未执行」（全 `[待填]`），执行归 R10 真机轮。

### H7 发布（#10）

- **变化**：`RELEASE-CHECKLIST.md`（4.4K 字符）——LICENSE 表**首行即「阻断：仓库当前不存在」**并写明「未落实不得发布源代码或宣称开源」（六轮 D-1 悬案首次有了书面决议姿态：不是除名而是升格为发布阻断项）+ 版本号/tag/SHA256 冻结流程 + **对外声明草案**（含与洪恩「不存在隶属、授权或合作关系」的合规措辞）+ R8 证据 SHA256 冻结表 + 五道发布批准门；`GLOBAL-SUMMARY-REPORT.md` 增 §7 Round 9 终验表（七个交付位全 ✅ + 收口证据列）与 evidence/r9 索引，零 ⏳/❌/「待 R8」（fa875cf 最后一笔就是清 §7 占位）；`acceptance-log-round8.md` 终验回填完成（G1–G6 全 PASS、zip SHA256、Android 26/26，b65d6ad）。
- **判定**：**闭环**（探针口径）。但见 §5-1：R9 自己的 acceptance-log 未回填。

### H8 + 质量债（#7 下半）

- **H8**：check:round8 8/8 实跑绿（本审计 §0），R7/R6 抽查同绿——R9 七个功能位合入零踩线，「H1 儿歌 ≥3」等存量探针输出随新数据自然更新。
- **质量债 20 条改稿**：字源 13 条（a76af74，`洞=凹进去的一个口 + 氵几乎都和水有关` 类自相矛盾模板句 → 每条交代形旁为什么还在）+ 剧情 7 条（5e99fbf，u74「雪原白茫茫，吱吠吟吼并排」→「远处一声狗吠，能在耳朵里响上好一会儿」——字在句子里真的干事）。两笔均计数不变、探针全绿，正好压简报「≤20 条」上限。**判定：闭环**，抽查改稿前后文案质量差异真实（非重排措辞）。

---

## 4. 总览与增量

**总盘子：31 项 = ✅ 31（100%）/ ◐ 0 / ❌ 0——九轮长跑首次满盘，主计划「零 ❌ 零 ⬜」终态达成。**

| 轮次审计 | ✅ | ◐ | ❌ |
|---|---|---|---|
| Round 4 | 4 | 20 | 7 |
| Round 5 | 13 | 13 | 5 |
| Round 6 | 17 | 12 | 2 |
| Round 7 | 24 | 6 | 1 |
| Round 8（审计基线 a8b21b3） | 25 | 6 | 0 |
| Round 8 终态（ec733bb，R9 起点） | 27 | 4 | 0 |
| **Round 9 终态（本次，fa875cf）** | **31** | **0** | **0** |

状态变化明细（相对 Round 8 终态）：

- **◐→✅（4 项，即 R9 四条深度杆全部兑现）**：L-M5（投稿规范 16.8K 字符，三轮备忘销账）、L-M9（ASR 评估文档 + PoC 双交付，杆是二选一）、L-M10（基准 10 张 8 tier 逐层定线 100% 召回）、L-M11（儿歌 13 首 + 同步 v2，杆是二选一双达标）。
- **持平 ✅ 且深度加码（2 项）**：M-M1（推荐层 = R8 审计预判的「图谱 × FSRS/自适应联动」落地，行为级只读验证）、M-M16（math check-bundle 流程债清 + LH CI 版本锁常驻）。
- **无下调、无口径豁免**：本轮零「✅→◐」——R9 是第一轮没有任何行被新杆压回去的轮次，因为 R9 本身就是收口轮（深度打磨与发布工程），R10 归属全部是打磨/执行面，无功能缺口。
- **对齐性**：连续第四轮「◐ 存量 = 在途任务」零悬空，且本轮清零；R8 审计 §4 预判的 4 个「交付后预期 ◐→✅」与「R9 归属备忘」9 条全部命中或有明确去向（见 §6 对账）。

---

## 5. 未清项与探针盲区（发布前 / R10 必看）

1. **`acceptance-log-round9.md` 集成回填未做（最重要的收口欠账）**：§1 H1–H8 集成实测格、§2.1 LH 表、§2.2 OCR tier 表、§2.3 体积表、§4 走查勾选 W1–W6、§5 集成 SHA 与命令表**全部还是 ⬜/[P/F] 占位**。ROUND9-ACCEPTANCE §7 明文「每条 H1–H8 必须有实测数据或命令输出」，而 check:round9 H7 只查 GLOBAL-SUMMARY 与 RELEASE-CHECKLIST，**不查本日志——探针盲区**。数据全部现成（本审计 §0 + evidence/r9 + acceptance-log-round9-h2），编排收口时照抄回填即可，勿留占位过夜。
2. **跟读隐私文案失配**：`FollowReadView.vue` L111「两种都不会把声音传到别的地方」与「浏览器识别可能走厂商在线服务」（同页开关自己承认）矛盾，ASR 评估文档 §3.2 已点名修法（「录音回放和离线评测不上传；浏览器逐字识别可能联网，需家长打开」）——一行文案改动，建议不等 R10、发布前顺手清。
3. **Android 真机清单未执行**：ANDROID-DEVICE-CHECKLIST 全 `[待填]`，check:android 26/26 仍是静态门禁——真机走查（相机权限流/OCR wasm 性能/儿歌音频在 WebView）是 R10 头号执行项。
4. **两处文档小失配**：BOOK-COMMUNITY-SUBMISSION §五「61 项」应为 71 项；acceptance-log-round9-h2 实测表停在 9 张 51/51（现状 10 张 55/55，8f8e621 后未回写）。均不影响功能与门禁，下次动这两个文件时顺手校正。
5. **LICENSE 仍缺**：根目录无 LICENSE 文件（本轮实查）；RELEASE-CHECKLIST 已升格为发布阻断项并给出决议路径（权利人定原创部分许可，不得把 THIRD_PARTY_NOTICES 误当项目许可证）——不再是「悬置备忘」，但**动作本身仍待权利人**。
6. **数学 LH 98（-1）**：仍超线 3 分，但连续两轮下行趋势值得盯（99→98）；lighthouse-ci.mjs 已常驻，R10 若加新面先跑 `test:lighthouse:ci` 再合并。
7. **G4/G5 未在 fa875cf 重跑**：`test:round3`（offline-smoke + acceptance）与 `build:all`+`sync:android`+`check:android` 的最后实测在 #10 收口分支（acceptance-log-round8 终验 + evidence/r9 acceptance-output，commit `e1cdced` 时点）；此后合入的只有文档提交（e0dd19c/b65d6ad/fa875cf 均不触 src），风险极低，但编排最终回归若要出包，按惯例在集成 HEAD 再跑一遍 G4/G5 落数。

### R10 归属备忘（本轮汇总，全部为打磨/执行面，无功能缺口）

| # | 项 | 来源 |
|---|---|---|
| 1 | acceptance-log-round9 回填 + fa875cf 出包终验（G4/G5） | §5-1/§5-7，编排收口 |
| 2 | Android 真机走查执行（清单已备） | §5-3 |
| 3 | 跟读 v3 阶段 A：sherpa-onnx WASM Worker spike + Vosk/whisper.cpp 盲测对照（评估文档 §6 路线图） | #8 文档决策 |
| 4 | 跟读隐私文案修正（一行） | §5-2 |
| 5 | OCR 真实拍摄样张替换/补充程序合成图 + WebView 实测 | #5 边界声明 |
| 6 | 投稿通道自动化：import-book-submission.mjs + CI ajv 步 | H5 文档 §七 自列 |
| 7 | 儿歌旋律资产升级（合成音→开源曲库/录制）与 IP 化 | #4 交付面之外 |
| 8 | 图谱推荐 × 错题本/每日冒险闭环（推荐生成练习计划） | #6 只读推荐之外 |
| 9 | 发布执行：LICENSE 落实（阻断）、版本号统一（根 1.0.0 vs 双 App 0.1.0）、tag 冻结、隐私政策页 | RELEASE-CHECKLIST §1/§2/§5 |
| 10 | 字源 808 条批量派生的语文性人工复核余量（本轮抽修 13 条之外）+ 桌面档 LH 双档定标 | #7/#9 交付面之外 |

---

## 6. R8 审计预判对账（round8-hongen-audit §4 + 上轮备忘 → 本轮实况）

| R8 审计预判/备忘 | 实况 | 判 |
|---|---|---|
| L-M5 投稿文档「R9 必办或正式除名」 | 16.8K 字符规范交付，H5 探针绿 | 命中·清账 |
| 儿歌 v1→v2（曲目扩充 + 旋律-歌词同步动画） | 13 首 + 预备拍/进度/留痕/音高抬升 | 命中·清账 |
| OCR 扩样（手写/低光/复杂背景）+ 阈值门禁化 | 四 tier 新增 + 逐 tier 阈值 + REQUIRED_TIERS 钉死 | 命中·清账 |
| 跟读离线 ASR 引擎评估（若 R8 走近似比对路线） | 评估文档 + PoC 双交付；分叉判断连续两轮命中 | 命中·清账 |
| 图谱 × FSRS/自适应联动（推荐学习路径） | recommend/recommendPath + 行为级只读验证 | 命中·清账 |
| LH 版本锁进 CI + 真机/桌面档定标 | 版本锁三重断言常驻；真机清单交付未执行、桌面档未做 | 部分命中（执行面归 R10） |
| u59–u99 质感走查、字源派生文案抽查 | 7 + 13 = 20 条改稿，压简报上限 | 命中·清账 |
| 发布终态：LICENSE（D-1）、对外声明、证据冻结 | 清单 + 声明草案 + SHA256 冻结表；LICENSE 升格阻断仍待权利人 | 部分命中（动作待人） |
| Android 真机走查（相机权限流/wasm 性能） | 清单交付，执行归 R10 | 顺延（如预判） |

---

## 7. 审计方法备注

- 内容计数：`node --input-type=module` 直接 import `songs.js`（SONGS 13 / 52 句 / id 去重 / verifySongCoverage()=[] / TOTAL_SONGS=13 一致）、`unit-stories.js`（TOTAL_UNIT_STORIES=99）、`etymology-index.js`（808，去重 808）；数学侧经 `--import ./scripts/register-alias.mjs` import `skill-graph.js`（SKILL_NODES 34 / SKILL_EDGES 30；导出新增 RECOMMEND_REASONS/RECOMMEND_REASON_MAP/recommend/recommendPath）并实际调用 `recommend()`/`recommendPath()` 验证行为；其余水位（1820/99、132/1121、60/24、214、1817、11/18）由 check:data 统计行与 check:content 输出复核，与 R8 终态一致。
- 门禁实跑（全部在 `fa875cf` 干净 worktree）：`check:round9` 8/8（exit 0，九轮首个审计时点绿灯）、`check:round8` 8/8（exit 0）、`check:round7` 8/8（exit 0）、`check:round6` 7/7（exit 0）、识字 `check:data` 71/71（exit 0）、数学 `check:content` 全绿（exit 0）；另单独实跑 `test-speech-eval.mjs`（14/14）与 `test-ocr-accuracy.mjs`（20/20，55/55 总召回，单图 24–88ms）。
- 功能有无：逐文件读源码 + 定向 grep（ROUND9_H1/H2/H3_SMOKE/H4 标记落点逐一实查为代码级信号非注释；`fixtures/ocr/` 9 张 PNG 逐张 stat 实数、最小 9,531 B；`recommendPath` 在 skill-graph.js L354；`phonemeMarks/similarityV2` 在 speechEval.js L100-250；数学 `check-bundle.mjs` 在场且挂 package.json test 链；根目录 LICENSE 实查不存在；FollowReadView L111 文案实查仍旧）；路由零变更（`git diff ec733bb..fa875cf -- */router` 空输出，识字 28 条/数学含 `/skill-graph` 维持）。
- Lighthouse/axe/zip 未在本轮重测：`evidence/r9/lighthouse-{literacy,math}-app.json` 原始 JSON 本轮直接解析（lighthouseVersion 12.8.2、formFactor mobile、categories 0.98/1/1 双 App）；axe 与首屏 gzip 引 `evidence/r9/acceptance-output.txt`（22 路由 + 4×24 状态 0/0；109,539 / 88,735 B）；zip/Android 引 `acceptance-log-round8.md` §3/§4 终验回填（6,252,719 / 458,315 B + SHA256，26/26）。测量 commit `e1cdced`（#9 分支），此后合入均为纯文档提交。
- 探针契约核读：`check-round9.mjs` v1.1 逐条读源码（H1 合规条目过滤器 + 剥注释 v2 正则 + 词边界 smoke；H2 PNG 魔数/1KB/handwriting 命名计数；H3 R9 专属信号——v1.0 的 `nextSkills` 恒真洞已堵；H4 关键词双与；H5 三重与；H6 文件在场 + 多信号 + JSON 可解析 >200B 递归计数；H7 零占位 + evidence/r9 字面索引；H8 spawn；结果数 ≠8 自 FAIL + `--json`）。
- R9 交付提交逐一走读：`git log ec733bb..fa875cf` 全部 21 笔（#4 儿歌 09a957a、#5 OCR d5d2ae5/baf7123/8f8e621、#6 图谱 f089211/ecd2bbc/e726036/026fd60、#7 质量 038c5b6/a76af74/5e99fbf、#8 ASR 4da6a22/bcaf5ad、#9 Perf 93805c1/cf1c31b、#10 发布 e0dd19c/b65d6ad/fa875cf、#1/#3 契约 6f24fa4/61853b6/92c7ce9/4d793a7）。
