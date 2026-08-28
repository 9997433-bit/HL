# Round 6 验收标准 —— 洪恩体量对齐（内容硬门槛）

> 版本：Round 6 v1.1（2026-08-27）
> 依据：`.agent_workspace/ROUND6-BRIEF.md` + `.agent_workspace/SURPASS-HONGEN-MASTER-PLAN.md`
> 配套：`.agent_workspace/acceptance-log-round6.md`（实测回填模板）、`scripts/check-round6.mjs`（H1–H6 机读探针，固定 7 个结果）
> 判定原则：每条都能被脚本或 10 分钟内的手动步骤验证；**写进简报不跑脚本视为未交付**（主计划原则 4）。

## 0. 轮次门禁 G1–G5（顺序执行，全过才可出包）

| # | 门禁 | 验证方式 | PASS 标准 |
| --- | --- | --- | --- |
| G1 | 全量单测回归 | `npm test` | 全绿（识字 `test:srs`+`check:data`+build+`check:bundle`+smoke；数学 `check:content`+build+smoke；feedback 单测）；Round 6 扩量不得回归 Round 5/5B 成果 |
| G2 | 往轮内容不退化 | `npm run check:round5` + `npm run check:round5b` | 退出码均为 0（12/12 与 6/6 保持全绿） |
| G3 | Round 6 内容硬门槛 | `npm run check:round6` | 退出码 0（**7/7**，见 §1；基线 `90663c1` 为 **1/7 有意红灯**，见 §4.1） |
| G4 | Round 3 全链回归 | `npm run test:round3` | 全绿（含离线 smoke + acceptance）；Lighthouse Perf/A11y ≥ 90；axe critical/serious = 0 |
| G5 | 出包 + 回填 | `npm run build:all` + acceptance-log | zip 产出并按 §4.2 模板记录体积；`acceptance-log-round6.md` 无「待回填」残留 |

---

## 1. 六项硬门槛（H1–H6）

`npm run check:round6` 逐项断言，任一 FAIL 即退出码 1。**固定输出 7 个结果**（H2 拆「数量 + 越界」两条），结果数 ≠ 7 时门禁自身 FAIL——防止探针被静默削减。`--json` 输出机读汇总（`passed`/`failed`/`results[].id/status/msg`）供编排器聚合。Round 6 是硬门槛：模块不可读取、视图未接路由等一律 FAIL，不设 PENDING 放行。

| ID | 交付物 | PASS 标准 | 验证方式 | 责任分支 |
| --- | --- | --- | --- | --- |
| H1 | 字库 1000→**1800** | `TOTAL_CHARACTERS ≥ 1800`；脚本化生成（`char-seed.txt` + `gen-char-corpus.mjs`），`check:data` 同步扩展 | 探针 §2.1 + smoke §3 | r6-literacy-1800chars |
| H2 | 绘本 30→**130** | ① `BOOKS.length ≥ 130`；② `verifyBookCoverage()` 返回空数组（**零越界**，两条分别计入 7 结果） | 探针 §2.2 + smoke §3 | r6-literacy-books-130 |
| H3 | 古诗 **20 首** | `POEMS` 条目 ≥ 20（朗读+点字+拼音的观感走 §5 走查） | 探针 §2.3 + 走查 §5 | r6-literacy-poems-speech |
| H4 | 跟读评测 v1 | **路由 + composable + smoke 三重接线**，缺一即 FAIL：真实路由挂 `@/views/*.vue`、pipeline 文件含识别+录音降级、smoke 带 `ROUND6_H4_SMOKE` 标记 | 探针 §2.4 + smoke §3 | r6-literacy-poems-speech |
| H5 | 小游戏累计 ≥ **5**（不含 listen） | 注册表 ≥ 5 且每项 `id/name/route/skill/view` 齐备、id/route 唯一、`route` **精确接到 router 的对应视图文件** | 探针 §2.5 + smoke §3 | r6-literacy-minigames |
| H6 | 母题 118→**185+** | `WORD_PROBLEM_COUNT ≥ 185`（语义模板 × 场景皮肤）；`check:content` 校验答案可解 | 探针 §2.6 + smoke §3 | r6-math-problems-185 |

## 2. 探针细则（机读接线契约）

探针分两类：**数据探针**经 `scripts/alias-loader.mjs` 直接 `import` 应用数据模块（`@/` 按「谁 import 就落谁的 src」解析——`check-round6.mjs` 顶部的 `register('./alias-loader.mjs', …)` 不可删）；**接线探针**为纯静态分析（fs + 正则，剥注释后匹配，无 node_modules 可跑）。责任分支按下列路径/命名接线即绿；如需改约定，必须在同一 PR 内同步探针与本节，否则视为未交付。

### 2.1 H1 字库

- 数据源：`apps/literacy-app/src/data/characters.js` 导出 `TOTAL_CHARACTERS`，探针直接 import 读数，要求 ≥ 1800
- 扩量走脚本：`scripts/data/char-seed.txt` + `scripts/gen-char-corpus.mjs` 再生成，禁止手敲长数组
- `check:data`（识字 App 内）同步校验：无重复字、拼音/笔画/分级字段完整——门禁经 G1 兜底

### 2.2 H2 绘本

- 数据源：`apps/literacy-app/src/data/books.js` 导出 `BOOKS` 与 `verifyBookCoverage`
- 数量：`BOOKS.length ≥ 130`（H2.count）
- 越界：`verifyBookCoverage()` 必须存在、必须返回数组、且为空（H2.coverage）——每本书只用该书解锁进度内的已学字；缺导出、返回非数组、抛异常均 FAIL
- 拆分文件（如 `data/books/*.js`）允许，但聚合入口保持 `books.js` 且两个导出名不变

### 2.3 H3 古诗

- 数据源：`apps/literacy-app/src/data/poems.js`（或 `poetry.js`）导出 `POEMS`（数组或对象均可），条目 ≥ 20
- 每首建议含 `id/title/author/lines/pinyin`，供朗读+点字+拼音三件套渲染；字段完备性由 `check:data` 与 §5 走查兜底
- 古诗路由与朗读交互进 smoke（§3），不计入 H3 探针本身

### 2.4 H4 跟读评测（路由 + composable + smoke，缺一即 FAIL）

- **路由**：`apps/literacy-app/src/router/index.js` 存在 `path` 匹配 `/follow-?read|speech-?(eval|assess)|read-?aloud/i` 的路由（`/` 或 `-` 分隔均可，推荐 `/follow-read/:id?`），其 `component` 为 `() => import('@/views/….vue')` 动态导入，且该视图文件真实存在
- **composable**：以下四选一必须存在（推荐第一个）：
  - `src/composables/useSpeechEval.js`
  - `src/composables/useFollowRead.js`
  - `src/utils/speechEval.js`
  - `src/utils/speechRecognition.js`
- **能力关键字**（composable + 路由视图合并源码，剥注释后）：
  - 识别：`SpeechRecognition`（webkit 前缀亦可）
  - 录音回放降级：`MediaRecorder | mediaDevices | getUserMedia | recordedBlob | audioUrl` 任一——无识别引擎的 WebView 里必须能录音回放自评
- **smoke**：`apps/literacy-app/scripts/smoke.mjs` 必须含字面标记 **`ROUND6_H4_SMOKE`**（写在跟读断言旁的注释或断言名里）且含跟读路由关键字（`follow-read` / `跟读评测`）。只加路由不加断言拿不到该标记——见 §3
- 评分逻辑（比对准确度、星级）不做静态探针，走 §5 走查 W2

### 2.5 H5 小游戏

- 注册表：`apps/literacy-app/src/data/games.js` 导出 `GAMES`；剔除 `id === 'listen'` 后 ≥ 5 款
- 每项字段齐备：`id/name/route/skill/view` 均为非空字符串；`id` 与 `route` 各自唯一
- **router 精确接线**：每项 `route` 必须能在 `router/index.js` 找到同 `path` 的路由，其动态导入的视图恰为 `@/views/<view>.vue`，且该文件真实存在——注册表写了 route 但 router 没挂、或挂错视图，都 FAIL
- 大厅渲染（`GamesView` 逐条出卡片 + 一句话玩法）继承 Round 5B P5 探针，经 G2 兜底

### 2.6 H6 母题

- 数据源：`apps/math-app/src/data/wordProblems.js` 导出 `WORD_PROBLEM_COUNT`（或 `WORD_PROBLEMS` 数组），≥ 185
- 该模块依赖 `@/utils/random`——正是 alias-loader 必须保留的原因
- 母题质量（答案可解、场景皮肤字段、去重）由数学 `check:content` 校验，经 G1 兜底；比较/速算/生活应用专题入口接线走 smoke §3 与走查 W5

## 3. smoke 断言建议（新面必须进浏览器 smoke，随责任分支同 PR 交付）

识字 smoke（`apps/literacy-app/scripts/smoke.mjs`）现有约定：`ROUTES` 逐条开页断言无 console error/pageerror，绘本用 `...BOOKS.map(…)` 全量展开；交互断言在 `inter` 列表。Round 6 建议增量：

- **H2 绘本**：无需改动——`BOOKS.map` 自动把 130 本全量铺进 ROUTES；注意 smoke 时长会显著增加，回填时记录总耗时，超过 CI 容忍度再谈抽样
- **H3 古诗**：古诗列表 + 至少 2 首详情路由进 ROUTES；交互断言：点「朗读」不报错、点单字出拼音气泡
- **H4 跟读**：跟读路由进 ROUTES；交互断言（旁注 `ROUND6_H4_SMOKE`）：无麦克风权限（headless 默认拒绝）时页面显示降级 UI 而非 pageerror；「开始跟读→停止」按钮可点
- **H5 小游戏**：新增 2 款游戏路由进 ROUTES；各加 1 项交互断言走「开始→答 1 题→出反馈」最短闭环
- **H1 字库**：字表页首屏渲染正常 + 任取 1 个新增高段位字的详情页可进（写字面板挂载）
- **数学 smoke**（`apps/math-app/scripts/smoke.mjs`）：比较/速算/生活应用专题入口路由进 ROUTES；母题扩量后任抽 1 题走答题闭环

## 4. 基线与 Perf/体积记录

### 4.1 基线红灯记录（有意红灯）

基线 `cursor/openmoji-integration-9f67` @ `90663c1`（Round 5B 闭合、Round 6 未动工）实测：

```
  ✓ H2 verifyBookCoverage 零越界

  ✗ H1 字库 1000/1800 字
  ✗ H2 绘本 30/130 本
  ✗ H3 古诗未接线（要求 ≥ 20 首）
  ✗ H4 跟读评测未闭环：路由=缺失，composable=缺失，识别/录音降级=缺失，smoke=缺失
  ✗ H5 识字小游戏 3/5 款（不含 listen）
  ✗ H6 应用题母题 118/185 个

Round 6 内容门禁：1/7 项通过，6 项失败。 → 退出码 1
```

1/7 属**有意红灯**：探针先行、交付点绿（继承 Round 4/5/5B 原则）。H2.coverage 基线即绿属存量能力，扩到 130 本后必须保持绿。

### 4.2 Perf/体积记录模板（集成后回填到 acceptance-log）

字库/绘本/母题扩量的最大风险是**首屏与包体失控**（简报红线：扩量不得拖垮首屏，保持懒加载 + `check:bundle` 预算）。集成后按下表实测回填：

| 指标 | 预算/基线 | 集成实测 | 判定 |
| --- | --- | --- | --- |
| 识字首屏 JS gzip | < 250 KB | `[待回填]` | `[P/F]` |
| 数学首屏 JS gzip | < 250 KB | `[待回填]` | `[P/F]` |
| Lighthouse 识字 P/A/BP | ≥ 90 / ≥ 90 / ≥ 90 | `[P/A/BP]` | `[P/F]` |
| Lighthouse 数学 P/A/BP | ≥ 90 / ≥ 90 / ≥ 90 | `[P/A/BP]` | `[P/F]` |
| literacy-app zip | 基线 `[待回填]` MB | `[待回填]` MB（Δ`[±]`） | 记录即可 |
| math-app zip | 基线 `[待回填]` MB | `[待回填]` MB（Δ`[±]`） | 记录即可 |

zip 体积无硬上限但必须记录 Δ 并解释来源（新增字数据/绘本文本/古诗音频策略）；音频一律 TTS 或运行时生成，禁止把大媒体文件打进包。

## 5. 手动走查（探针盲区，合并前 10 分钟过一遍）

| # | 走查项 | 期望 |
| --- | --- | --- |
| W1 | 古诗三件套 | 逐句朗读高亮跟随；点任意字出拼音+读音；拼音标注不遮挡诗句 |
| W2 | 跟读评测闭环 | 允许麦克风：跟读后出星级/鼓励且能重试；拒绝麦克风：自动落到录音回放自评，无死路 |
| W3 | 新小游戏可玩 | 两款新游戏「开始→玩→结算」完整闭环；结算有庆祝且可跳过 |
| W4 | 绘本扩量抽查 | 任抽 5 本新书：翻页流畅、点字可读音、无越级生字 |
| W5 | 数学专题入口 | 比较/速算/生活应用入口可进可退；地图叙事升级后未解锁章节灰显+一句话剧情 |
| W6 | 硬性红线抽查 | 触控 ≥ 56×56、键盘可达、庆祝可跳过、`prefers-reduced-motion` 降级（继承 Round 3/4） |

## 6. 不回归红线（继承 Round 3/4/5/5B，抽查即可）

- `npm run check:round5` 保持 12/12、`npm run check:round5b` 保持 6/6
- axe critical = 0 且 serious = 0（双 App 全路由 + 交互态，`npm run test:a11y`）
- 断网冷启动完成学习闭环（`npm run test:offline`）——新增古诗/跟读/游戏路由同样要离线可用（跟读识别不可用时录音降级即可）
- 运行时零第三方域名请求；识字首屏 JS gzip < 250KB，扩量数据必须按路由懒加载，不得挤进首屏 chunk
- FSRS 复习队列、每日冒险、吉祥物陪跑等 Play 层能力在新路由上不缺席

## 7. 回填要求

每条 H1–H6 在 `acceptance-log-round6.md` 对应小节必须有**实测数据或命令输出**（计数、日志粘贴、走查勾选）。集成回填必须带：集成 SHA、`check:round6` 全文输出、六项实测计数、zip 体积表。禁止「应该可以」「理论上通过」。未达标项一律进 log §3 未达标表并写明责任分支与计划，不得静默遗漏。
