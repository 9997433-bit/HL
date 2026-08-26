# Round 4 · 洪恩模块对标审计（fresh code walk）

> 审计人：Round 4 子代理 #2（fable）
> 审计基线：分支 `cursor/r4-module-audit-9f67`（自 `origin/cursor/openmoji-integration-9f67`，HEAD `ffd4296`）
> 审计日期：2026-08-26 · Node 22.14.0
> 方法：**逐文件重新走读源码**（非引用 Round 3 审计结论），每条状态都附代码证据路径；
> 内容体量用 `node` 实际 import 数据文件统计，测试计数来自本机 `npm test` 实跑。

---

## 0. 基线 `npm test` 实测（本分支、本机实跑）

命令：`npm test`（= `test:literacy` + `test:math`），**退出码 0，全绿**。

| 套件 | 明细 | 结果 |
|---|---|---|
| 识字 `test:srs` | FSRS 单元测试 | **8/8 通过** |
| 识字 `check:data` | 字表/绘本/成语/部首内容自检 | **33 项通过，0 项失败** |
| 识字 `build` | vite 构建 | ✅ 374 个构建文件（含 336 个离线笔顺 JSON） |
| 识字 `smoke.mjs` | 无头浏览器冒烟 | **21 条路由 + 15 项交互，0 项有问题** |
| 数学 `check:content` | 题库/数独/音效自检 | **全部通过**（母题 34 个，每个母题各生成 2000 道压测；技能映射 23 个 id 全在图谱） |
| 数学 `build` | vite 构建 | ✅ 39 个构建文件（index 主包 275.29 kB / gzip 98.48 kB，未拆） |
| 数学 `smoke.mjs` | 无头浏览器冒烟 | **10 条路由 + 17 项交互，0 项有问题** |

冒烟合计：**识字 36 项 / 数学 27 项，共 63 项全过**。完整输出见本轮 CI 日志（本机留档 `/tmp/npm-test-baseline.log`）。

另：仓库已存在 `scripts/check-round4.mjs`（R4 硬门槛 stub，要求字库 ≥500，当前基线 200 字 **预期红灯**，未接入 `npm test`）。

---

## 1. 识字 App 对标表（L-M1 … L-M15）

图例：✅ 达标 / ◐ 有 MVP 但缺洪恩级深度 / ❌ 未实现。

| 模块 | 洪恩能力 | 状态 | 实测证据（文件路径 + 关键事实） | Round 4 负责人 |
|---|---|---|---|---|
| L-M1 | 1800 常用字分级 | ❌ | `apps/literacy-app/src/data/characters.js`：`CHARACTERS.length = 200`、16 个单元；离线笔顺 `apps/literacy-app/public/hanzi-data/`（336 个 JSON）；门禁 `apps/literacy-app/scripts/check-data.mjs`（≥200）。体量 = 洪恩的 ~11% | **#5 opus-fast**（R4 目标 500） |
| L-M2 | 认-读-写-玩闭环（状态机） | ◐ | `apps/literacy-app/src/views/CharDetailView.vue`：认(拼音/释义)+读(`say()`)+写(描红 `onQuizComplete`)集中在一页，但无 intro→trace→listen→quiz→reward 状态机；听音测验在独立路由 `/listen`（`src/router/index.js` L33-38），互不衔接、无奖励收尾环节 | **#4 opus-fast** |
| L-M3 | 笔顺+描红判定 + 错3次示范 | ◐ | `apps/literacy-app/src/components/HanziStrokeBox.vue`：逐笔判定 ✅（`writer.quiz` + `onMistake`，L147-165）；`showHintAfterMisses: 2` 只给轮廓提示，**无「错 3 次自动示范该笔」的完整演示**；键盘替代 ✅（空格/回车/→ 写下一笔、Esc 跳过，L213-222，smoke 已测「键盘写完『日』」） | **#4 opus-fast** |
| L-M4 | 听音识字/测验 | ◐ | `apps/literacy-app/src/views/ListenGameView.vue`：`OPTIONS=4`（2×2）、`ROUNDS=10`、3 皮肤 card/fish/mole（L32-56）、复习字 60% 优先（L136-137）；**干扰项为随机取样（L141），无形近字干扰**——主计划标 ✅ 偏乐观，本审计降为 ◐ | 维护（形近干扰建议并入 R5） |
| L-M5 | 130 本分级绘本 | ❌ | `apps/literacy-app/src/data/books.js`：`BOOKS.length = 5`，3 个分级；逐句朗读高亮+点字发音已有（smoke ✓）。体量 = 洪恩的 ~4% | R5→30 / R6→130（本轮不动） |
| L-M6 | 800+ 字源互动 | ◐ | `apps/literacy-app/src/data/radicals.js`：18 个部首（glyph/hint/meaning/示例字联动）+ `views/RadicalsView.vue` 详情页；**无 makemeahanzi 字源、无演变动画**，距 800 字量级差两个数量级 | R5（本轮不动） |
| L-M7 | 记忆曲线复习 | ✅ | `apps/literacy-app/src/utils/srs.js`（FSRS-lite 纯函数，`test-srs.mjs` 8/8）；`stores/progress.js` L18/L254-271：描红/答题走 `schedule()`、`reviewQueue` 按到期排序；家长页热力图 `views/ParentView.vue` L87-121（`retention` 分档渲染） | R4「巩固+可视化增强」**§6 未指派**（建议并入 #4 或 #10） |
| L-M8 | 成语/古诗国学 | ◐ | `apps/literacy-app/src/data/idioms.js`：20 条成语（故事≥2段+四字拆解+情景题，check:data 全过）；**古诗 0 首**（全库 grep「古诗/poem」无命中） | R5（本轮不动） |
| L-M9 | AI 学伴/跟读评测 | ❌ | `apps/literacy-app/src/utils/speech.js` 仅 `speechSynthesis` TTS；全库 grep `SpeechRecognition/跟读/录音` 零命中 | R6（本轮不动） |
| L-M10 | 拍照识字 | ❌ | 全库 grep `tesseract/ocr/拍照` 零命中（含 package.json） | R6（本轮不动） |
| L-M11 | 动画儿歌/IP | ◐ | GSAP 已进 9+ 视图（`HomeView/BookReadView/IdiomDetailView/...`）+ `CelebrationOverlay.vue`/`StarBurst.vue`/`MascotCompanion.vue`；OpenMoji 图标层 `shared/utils/openmoji.js`。无儿歌/Lottie 级 IP 内容 | R5 扩游戏壳（本轮不动） |
| L-M12 | 字迷宫/跑酷等小游戏 ≥5 | ❌ | 路由仅 1 款小游戏（`/listen`，3 皮肤是换肤不是新玩法）；迷宫/配对/跑酷/找不同/拼字均无 | R5–R6（本轮不动） |
| L-M13 | 家长控制/防沉迷 | ◐ | `apps/literacy-app/src/views/ParentView.vue`：口算门（L44-58）、各单元进度（L242+）、记忆热力图、JSON 导出/导入（L136-145）、每日时长滑杆+到点提醒（L413-435）✅；**无自定义学习计划（自选单元/每日新字数 dailyGoal 无 UI，仅 store 默认值 5）** | **#5 opus-fast** |
| L-M14 | 奖励/徽章体系 | ◐ | 星星/xp/等级在 `stores/progress.js`（L75-77）✅；**无成就/徽章体系**（grep `ACHIEVEMENT` 零命中；`CharCard.vue` 的 badge 只是掌握度角标）。对照：数学侧已有 16 个成就定义 | **#4 opus-fast** |
| L-M15 | 性能/无障碍/离线 | ◐ | 离线：`public/sw.js` 预缓存 + `scripts/offline-smoke.sh` ✅；axe：`scripts/axe-check.mjs` 19/19 页 critical=0/serious=0（`acceptance-log-round3.md`）；viewport meta 已可缩放（`index.html` L7，R3 扣分项在本分支已修）；**Perf 未达标**：R3 实测识字 86–89（`round3-sota-final-audit.md` §1.1），待拆包/gzip | **#8 + #10 gpt-sol** |

**识字小计：✅ 1 / ◐ 9 / ❌ 5（共 15 项）**

---

## 2. 数学 App 对标表（M-M1 … M-M16）

| 模块 | 洪恩能力 | 状态 | 实测证据（文件路径 + 关键事实） | Round 4 负责人 |
|---|---|---|---|---|
| M-M1 | 3–12 岁 L1–L5 年龄档 | ◐ | `apps/math-app/src/stores/settings.js` L12-18：`AGE_BANDS` L1–L5 + 越界清洗 ✅；家长页可选（`parent/ParentView.vue` 3 处）；**全 App 只有 `ArithmeticView.vue` 1 处读 `ageBand`，未全模块联动** | R4 目标但 **§6 未指派**（建议并入 #7） |
| M-M2 | 1000+ 互动/无限题 | ◐ | 母题×参数可无限出题 ✅（`check-content.mjs` 每母题压测 2000 次）；**`src/utils/random.js` 全部 `Math.random()`，无种子化 PRNG；`uid()` 是时间戳，题目不可复现；门禁 `MIN_TEMPLATES = 25`，距 ≥300 门禁差 12 倍** | **#7 opus-fast** |
| M-M3 | 185 应用题母题 | ◐ | `apps/math-app/src/data/wordProblems.js`：`WORD_PROBLEMS = 34` 个（check:content 实测：25 类语义标签/32 种场景，一步13·两步16·进阶5）。体量 = 洪恩的 ~18% | R5 扩至 185（本轮不动） |
| M-M4 | 数感/比较/运算 | ◐ | 数感 ✅（`number-sense/NumberSenseView.vue`：drag/count/seq 三题型）；运算 ✅（`arithmetic/ArithmeticView.vue`）；**比较玩法 ❌**（`compare-to-10` 技能在 `curriculum.js` L19 但无任何视图出比较题，grep「比大小/更多/更少」零命中）；**竖式 ❌** | **#7 opus-fast**（比较模块） |
| M-M5 | 几何/空间 + 七巧板 | ◐ | `geometry/GeometryView.vue`：find/name/sides/real/odd 5 种题型 ✅；**七巧板无玩法**（`tangram-basic` 只是 curriculum 技能点，无 Canvas 实现） | R5（本轮不动） |
| M-M6 | 逻辑/规律 + 配对/迷宫 | ◐ | `logic/LogicView.vue`：number/emoji/group/rotate/shape 5 种规律题 ✅；**记忆配对/迷宫玩法 ❌**（`maze-condition`/`deduction` 技能点无对应出题） | R5（本轮不动） |
| M-M7 | 数独专项 | ✅ | `sudoku/SudokuView.vue`：4/6/9 三档 + 提示 + 数字键盘；`core/engine/sudoku.js`：`countSolutions` 保唯一解（check:content 压测过）；smoke 实测 4×4 填完 + 9×9 切档 | 维护 |
| M-M8 | 数形结合演示 | ❌ | 全 App grep「演示/demo」零命中；仅 wordProblems 的静态 `visual: { icon, groups }` 图示，**无「实物→图形→算式」同步动画** | R5（本轮不动） |
| M-M9 | 自适应难度 | ◐ | `src/utils/mastery.js`：EMA `updateMastery` 已接线（`stores/progress.js` L302）✅；**调度器 `pickNextSkill`（70/20/10 策略）已写但全 App 零调用（死代码），无连对升档/连错降档** | **#6 opus-fast** |
| M-M10 | 错题本 | ❌ | `stores/progress.js` 只有 `errorTagCounts`（错因计数，L329-331）+ `data/errorTags.js` 错因字典；**无 questionId 级错题记录、无重练移出**。家长页也只展示错因统计（`parent/ParentView.vue` L475） | **#6 opus-fast** |
| M-M11 | 计算专题/速算 | ◐ | 口算闯关 ✅（`arithmetic/ArithmeticView.vue`：连击加成 + ≤20 数轴 + 错因归因 + 键盘输入，smoke 已测）；**竖式/进位错因专练 ❌** | R5（本轮不动） |
| M-M12 | 剧情关卡地图 + 日冒险 | ◐ | `home/HomeView.vue`：星球地图 + 星星解锁 + 「继续冒险」推荐下一星球（L30-35）✅；**无当前关呼吸高亮**（grep recommended/呼吸/pulse 零命中）；`dailyGoal` 只是 settings 字段（默认 5），**无日冒险 5 题玩法** | **#7 opus-fast** |
| M-M13 | 互动教具 ≥3 | ◐ | 2/3：拖拽装货计数（`NumberSenseView.vue` drag 题型，含回车装货键盘替代，smoke ✓）+ 数轴（`ArithmeticView.vue` L144-148，≤20）；**分与合教具 ❌**（`compose-ten` 技能点无玩法） | R5（本轮不动） |
| M-M14 | 家长面板 | ✅ | `parent/ParentView.vue`：口算门 + 技能雷达 6 轴 + 错因统计 + 整档 JSON 导出/导入 + 最近 7 天时长曲线（`stores/progress.js` `last7Days`）+ 防沉迷提醒（`BreakReminder.vue`）；smoke 3 项家长交互全过 | R4「报表深化」**§6 未指派**（建议并入 #6） |
| M-M15 | 奖励/成就 | ✅ | `data/achievements.js`：16 个成就 + `AchievementToast.vue`/`RoundSummary.vue`；星星/xp/等级/连击在 `stores/progress.js`；动效总开关 `settings.animations` 可关 | R4「扩徽章」**§6 未指派**（低优先） |
| M-M16 | 性能/无障碍/离线 | ◐ | 离线：`public/sw.js` 预缓存 39 文件 + offline-smoke ✅；axe 0/0（R3 log）；viewport meta 已修；**Perf 90–93 < 95**（R3 实测），`index` 主包 275 kB/gzip 98 kB 未拆 | **#8 + #10 gpt-sol** |

**数学小计：✅ 3 / ◐ 11 / ❌ 2（共 16 项）**

---

## 3. 总览与主计划差异（fresh walk vs §2/§3「现状」列）

**总盘子：31 项 = ✅ 4（12.9%）/ ◐ 20（64.5%）/ ❌ 7（22.6%）。**

与主计划「现状」列的出入（本次走读新发现）：

1. **L-M4 应降级**：主计划标 ✅「3 皮肤」，但目标里的「形近干扰」不存在——干扰项是纯随机取样（`ListenGameView.vue` L141）。
2. **M-M9 调度器已写未接**：`pickNextSkill`（70% 弱项/20% 新技能/10% 复习）在 `mastery.js` 里是成品死代码，R4 #6 的工作量是**接线**而非从零写。
3. **viewport meta 已修**：R3 审计的 LH A11y 唯一扣分项（meta-viewport）在本分支两 App 的 `index.html` 均已是可缩放写法，A11y ≥95 大概率只差重测。
4. **`scripts/check-round4.mjs` 已就位**：R4 硬门槛 stub（字库 ≥500 预期红灯 + 错题本/adaptive/seed 探针）已在基线上，但未接进 `npm test`，#5/#6/#7 交付时须把对应探针升级为硬门槛。
5. **母题准确数 = 34**（check:content 权威计数），与主计划「~34」一致。

**R4 指派缺口（§6 任务表没接住的 R4 项）**：L-M7 可视化增强、M-M1 全模块联动、M-M14 报表深化、M-M15 扩徽章。建议：M-M1 并入 #7、M-M14 并入 #6、L-M7/M-M15 并入 #4 或顺延 R5，避免本轮无人认领。

---

## 4. 审计方法备注

- 内容计数：`node --input-type=module` 直接 import `characters.js / books.js / idioms.js / radicals.js`（200/5/20/18）；母题数以 `check-content.mjs` 输出为准（34）。
- 功能有无：按模块逐文件读源码 + 定向 grep（形近/演示/竖式/SpeechRecognition/tesseract/呼吸高亮等关键词全库扫描）。
- 测试计数：`npm test` 本机实跑一次（退出码 0），逐行摘录各套件的通过数，未复用 Round 3 数字。
- Lighthouse 数字未在本轮重测，引用 `round3-sota-final-audit.md` §1.1 实测值并已注明——重测归 #10。
