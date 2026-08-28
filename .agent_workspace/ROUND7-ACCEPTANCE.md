# Round 7 验收标准 · 全面超越终验

> 版本：Round 7 v1.1（2026-08-27）
> 依据：`.agent_workspace/ROUND7-BRIEF.md` + `.agent_workspace/SURPASS-HONGEN-MASTER-PLAN.md` §Round 7
> 配套：`.agent_workspace/acceptance-log-round7.md`（实测回填模板）、`scripts/check-round7.mjs`（H1–H7 机读探针，固定 8 个结果）
> 判定原则：每条都能被脚本或 10 分钟内的手动步骤验证；**写进简报不跑脚本视为未交付**（主计划原则 4）。

## 0. 轮次门禁 G1–G6（顺序执行，全过才可出包）

| # | 门禁 | 验证方式 | PASS 标准 |
| --- | --- | --- | --- |
| G1 | 全量单测回归 | `npm test` | 全绿（识字 `test:srs`+`check:data`+build+`check:bundle`+smoke；数学 `check:content`+build+smoke；feedback 单测）；Round 7 新功能不得回归 Round 6 成果 |
| G2 | 往轮内容不退化 | `npm run check:round6`（自身涵盖 4/5/5B 的存量口径） | 退出码 0（**7/7** 保持全绿）；抽查 `check:round5` 12/12、`check:round5b` 6/6 |
| G3 | Round 7 终验硬门槛 | `npm run check:round7` | 退出码 0（**8/8**，见 §1；基线 `46759f3` 为 **0/8 有意红灯**，见 §4.1） |
| G4 | Round 3 全链回归 | `npm run test:round3` | 全绿（含离线 smoke + acceptance）；axe critical/serious = 0 |
| G5 | 出包 + Android 同步 | `npm run build:all` + `npm run sync:android` + `npm run check:android` | zip 产出、Android 工程同步、`check:android` **26/26** |
| G6 | Lighthouse 终验 | `npm run test:acceptance`（内嵌 Lighthouse）或手动跑（§4.2） | 双 App Performance / Accessibility / Best Practices **均 ≥ 90**，按 §4.2 模板回填 |

---

## 1. 七项硬门槛（H1–H7，固定 8 个结果）

`npm run check:round7` 逐项断言，任一 FAIL 即退出码 1。**固定输出 8 个结果**（H2 拆「字库 + 接线」两条），结果数 ≠ 8 时门禁自身 FAIL——防止探针被静默削减。`--json` 输出机读汇总（`passed`/`failed`/`results[].id/status/msg`）供编排器聚合。Round 7 是终验硬门槛：模块不可读取、视图未接路由、smoke 无断言等一律 FAIL，不设 PENDING 放行。

| ID | 交付物 | PASS 标准 | 验证方式 | 责任分支 |
| --- | --- | --- | --- | --- |
| H1 | 拍照识字 v1（Tesseract.js） | **路由 + OCR pipeline + smoke 三重接线**，缺一即 FAIL：真实路由挂 `@/views/*.vue`、pipeline 文件含识别调用 + 拍照/选图降级、`tesseract.js` 入依赖、smoke 带标记或路由字面量 | 探针 §2.1 + smoke §3 | r7-literacy-ocr |
| H2.data | 形近字库 + 取样函数 | `similar-chars.js` ≥ **100 组**；`similarDistractors` **功能探针**通过（抽样 15 字：恰 count 个去重条目、排除目标字、含形近字） | 探针 §2.2 | r7-literacy-distractors |
| H2.wiring | 听音/测验干扰项非纯随机 | `ListenGameView` 与 `CharDetailView` 均 import `@/utils/distractors` 并调用 `buildOptions`/`similarDistractors` | 探针 §2.2 | r7-literacy-distractors |
| H3 | 字源动画 65→**200+** | `ETYMOLOGY_CHARS` ≥ 200 字、无重复凑数、`TOTAL_ETYMOLOGY` 一致；pipeline 批量生成，禁手搓 | 探针 §2.3 + `check:data`（G1 兜底） | r7-literacy-distractors |
| H4 | 年龄档 L1–L5 全模块联动 | settings store 暴露 `ageBand`，六个玩法视图 ≥ **5** 个读取（可经 `useAgeBand` composable） | 探针 §2.4 + 走查 W5 | r7-math-ageband |
| H5 | 逻辑配对/迷宫 v1 | 数学 App 存在配对或迷宫**真实路由**（≥1 条，推荐两条）挂 `@/modules/**.vue`，且 smoke 带标记或路由字面量 | 探针 §2.5 + smoke §3 | r7-math-logic-games |
| H6 | 第 4 主题 aurora | tokens 定义（≥ 5 个自定义属性）+ 识字 `THEMES` ≥ 4 款含 aurora + 数学 settings 注册 aurora | 探针 §2.6 + 走查 W6 | r7-theme-aurora |
| H7 | 全局报告终验 | `GLOBAL-SUMMARY-REPORT.md` 更新到 Round 7、全表零 ❌ 零 ⬜、带证据包索引 | 探针 §2.7 | r7-global-report |

## 2. 探针细则（机读接线契约）

探针分三类：**数据探针**经 `scripts/alias-loader.mjs` 直接 `import` 应用数据模块（`@/` 按「谁 import 就落谁的 src」解析——`check-round7.mjs` 顶部的 `register('./alias-loader.mjs', …)` 不可删）；**接线探针**为纯静态分析（fs + 正则，剥注释后匹配，无 node_modules 可跑）；**功能探针**（H2 独有）实际调用交付函数断言行为。责任分支按下列路径/命名接线即绿；如需改约定，必须在同一 PR 内同步探针与本节，否则视为未交付。

### 2.1 H1 拍照识字（路由 + pipeline + smoke，缺一即 FAIL）

- **路由**：`apps/literacy-app/src/router/index.js` 存在 `path` 匹配 `/camera|ocr|photo/i` 的路由（推荐 `/ocr`，可另挂 `/camera` redirect），其 `component` 为 `() => import('@/views/….vue')` 动态导入，且该视图文件真实存在
- **pipeline**：`src/composables/useOcr.js` 或 `src/utils/ocr.js` 至少一个存在（两个都有则并读）；`tesseract.js` 必须出现在识字 App `package.json`
- **能力关键字**（pipeline 文件 + 路由视图合并源码，剥注释后）：
  - 识别调用：`createWorker | .recognize( | Tesseract` 任一
  - 拍照/选图降级：`getUserMedia | mediaDevices | capture= | type="file | accept= | FileReader | createObjectURL` 任一——无摄像头/拒权限的设备必须能从相册选图
- **smoke**：`apps/literacy-app/scripts/smoke.mjs` 含字面标记 **`ROUND7_H1_SMOKE`**，或 OCR 路由字面量（如 `/ocr`）进 ROUTES/interact——见 §3
- OCR 引擎与语言包必须**离线本地化**（懒加载块 + `public/ocr/`），运行时零第三方域名——经 §6 红线与 `test:offline` 兜底；识别准确率不做静态探针，走走查 W1

### 2.2 H2 形近干扰（H2.data 字库 + 功能，H2.wiring 接线，两条分别计入 8 结果）

- **数据源**：`apps/literacy-app/src/data/similar-chars.js` 导出 `SIMILAR_MAP`（`Map`，值为「形近字字符串或字符数组」均可；也接受 `SIMILAR_CHARS` 普通对象）与 `similarChars(char)` 查询函数；**≥ 100 组**（每组至少 1 个非自身形近字，探针统一归一化后计数）；相似度数据走脚本生成（如 `gen-similar-chars.mjs`），禁手敲长表
- **取样函数**：`apps/literacy-app/src/utils/distractors.js` 导出：
  - `similarDistractors(char, count, options?)` → 返回**字表条目数组**（带 `.char`），按「形近字库 → 同部首笔画近 → 笔画近 → 池内其余」逐档补齐
  - `buildOptions(target, count, options?)` → 目标条目 + 干扰项洗牌后的完整选项
- **功能探针**（非纯随机的机读证明）：从 `SIMILAR_MAP` 与字表的交集抽样 ≤ 15 字，逐个断言 `similarDistractors(字, 3)`：恰好 3 个、去重、不含目标字、**至少 1 个来自该字的形近集**；任一违约即 FAIL
- **H2.wiring**：`ListenGameView.vue` 与 `CharDetailView.vue`（单字页「考一考」）都必须 import `@/utils/distractors` 并调用 `buildOptions(`/`similarDistractors(`——只建库不接线视为未交付

### 2.3 H3 字源动画

- 数据源：`apps/literacy-app/src/data/etymology-index.js` 导出 `ETYMOLOGY_CHARS`（字符串），探针按码点展开计数，要求 **≥ 200**、**无重复字凑数**；如导出 `TOTAL_ETYMOLOGY` 必须与实际一致
- 语料本体 `etymology.js`（演变阶段、解说词）与索引的同步由识字 `check:data` 校验，经 G1 兜底；扩量走 pipeline 批量生成（脚本 + 数据表），禁止手搓 135 个新条目
- 动画观感（演变补间、reduced-motion 降级为静帧）走走查 W3

### 2.4 H4 年龄档联动

- settings store（`apps/math-app/src/stores/settings.js`）必须暴露 `ageBand`（L1–L5），剥注释后可匹配
- 以下六个玩法视图 ≥ **5** 个引用 `ageBand`/`AGE_BAND`（直接读 store 或经 `useAgeBand` composable，文件内出现即计）：
  - `modules/number-sense/NumberSenseView.vue`、`modules/geometry/GeometryView.vue`、`modules/logic/LogicView.vue`、`modules/word-problems/WordProblemsView.vue`、`modules/sudoku/SudokuView.vue`、`modules/arithmetic/ArithmeticView.vue`
- 家长面板可调档、各档难度肉眼可辨走走查 W5；档位驱动的出题参数合法性由数学 `check:content` 兜底（G1）

### 2.5 H5 逻辑配对/迷宫

- **路由**：`apps/math-app/src/router/index.js` 存在 `path` 匹配 `/pair|match|memory|maze|配对|迷宫/i` 的路由 ≥ 1 条（推荐配对 + 迷宫两条，如 `/memory-pairs`、`/maze`），其 `component` 为 `() => import('@/modules/….vue')` 动态导入且文件真实存在
- **smoke**：`apps/math-app/scripts/smoke.mjs` 含字面标记 **`ROUND7_H5_SMOKE`**，或已接线路由的字面量进 ROUTES/interact——见 §3
- Canvas 渲染、键盘可达、`prefers-reduced-motion` 降级走走查 W4 + §6 红线

### 2.6 H6 第 4 主题 aurora

- **tokens**：`shared/styles/design-tokens.css` 存在 `[data-theme='aurora']` 块且块内 ≥ **5** 个 `--` 自定义属性
- **识字注册**：`apps/literacy-app/src/stores/settings.js` 的 `THEMES` 注册表 ≥ **4** 款且含 `aurora`（sunny/care/night/aurora 四主题可切换）
- **数学注册**：`apps/math-app/src/stores/settings.js` 出现 `aurora`（cosmos 保持默认，aurora 可选）
- 四主题对比度走查（正文 ≥ 4.5:1）+ axe 零新增走 W6 与 §6 红线

### 2.7 H7 全局报告

- `.agent_workspace/GLOBAL-SUMMARY-REPORT.md` 长度 > 500 字符、正文含 `Round 7`
- 表格行**零 ❌ 且零 ⬜**（「待实测」占位必须全部落成实测值或移入未达标表）
- 含证据包索引（`证据`/`Evidence` 关键字）：每条终验结论注明来源（命令输出、acceptance-log 小节、Lighthouse 报告路径）

## 3. smoke 断言建议（新面必须进浏览器 smoke，随责任分支同 PR 交付）

识字 smoke（`apps/literacy-app/scripts/smoke.mjs`）现有约定：`ROUTES` 逐条开页断言无 console error/pageerror，交互断言在 `inter` 列表。数学 smoke 同构。Round 7 建议增量：

- **H1 拍照识字**：`/ocr` 进 ROUTES；交互断言（旁注 `ROUND7_H1_SMOKE`）：headless 默认拒摄像头权限时页面显示选图降级 UI 而非 pageerror；「选图 → 识别 → 讲解」最短闭环（可用固定测试图触发）；OCR 懒加载块不得混入首屏 chunk（`check:bundle` 兜底）
- **H2 形近干扰**：听音识字与单字测验的既有断言自动覆盖新取样路径，无需新增；若干扰项渲染异常会在现有 interact 中暴露
- **H5 逻辑小游戏**：`/memory-pairs`、`/maze` 进 ROUTES；各加 1 项交互断言（旁注 `ROUND7_H5_SMOKE`）：配对走「翻两张 → 配对/回盖 → 全清结算」；迷宫走「键盘移动 → 撞墙拦截 → 到达终点」
- **H6 主题**：任一 App 加 1 条断言：切到 aurora 后 `document.documentElement.dataset.theme === 'aurora'` 且无 console error
- **H4 年龄档**：家长面板切档后进任一玩法模块无报错（难度观感走 W5）

## 4. 基线与 Lighthouse / Perf 记录

### 4.1 基线红灯记录（有意红灯）

基线 `cursor/openmoji-integration-9f67` @ `46759f3`（Round 6 闭合、Round 7 未合并）实测：

```
  ✗ H1 拍照识字未闭环：路由=缺失，pipeline=缺失，tesseract 依赖=缺失，识别调用=缺失，拍照/选图降级=缺失，smoke=缺失 —— 由 r7-literacy-ocr 交付
  ✗ H2 形近字库未接线（缺 similar-chars.js、distractors.js）—— 由 r7-literacy-distractors 交付
  ✗ H2 干扰项接线不全：听音识字=纯随机，单字测验=纯随机（须 import @/utils/distractors 并调用 buildOptions/similarDistractors）—— 由 r7-literacy-distractors 交付
  ✗ H3 字源动画 65/200 字
  ✗ H4 年龄档联动 1/5 模块；未接线：NumberSenseView、GeometryView、LogicView、WordProblemsView、SudokuView —— 由 r7-math-ageband 交付
  ✗ H5 逻辑小游戏未闭环：已接线路由=缺失，smoke=缺失 —— 由 r7-math-logic-games 交付
  ✗ H6 第 4 主题未闭环：aurora tokens=0（要求 ≥ 5），识字 THEMES=缺失（3 款，要求 ≥ 4），数学注册=缺失 —— 由 r7-theme-aurora 交付
  ✗ H7 GLOBAL-SUMMARY-REPORT 未终验：未更新到 Round 7；❌ 3 行；⬜ 待实测 73 行 —— 由 r7-global-report 交付

Round 7 终验门禁：0/8 项通过，8 项失败。 → 退出码 1
```

0/8 属**有意红灯**：探针先行、交付点绿（继承 Round 4/5/5B/6 原则）。探针已逐分支验证：五个功能分支的工作区各自恰好点绿自己负责的结果（H2.data 实测 1817 组、H4 6/6、H5 `/memory-pairs`+`/maze`、H6 tokens 32 项、H1 三重接线），集成后 8/8 可达。

### 4.2 Lighthouse / Perf / 体积模板（集成后回填到 acceptance-log）

跑法：`npm run test:acceptance`（对双 App dist 起本地服务并跑 Lighthouse，报告在临时目录 `lighthouse-*.json`）；或手动 `lighthouse http://127.0.0.1:<port>/ --preset=desktop`。OCR 引擎（wasm + 语言包近 6 MB）是本轮最大体积风险：必须走路由懒加载 + `public/ocr/`，首屏 chunk 与 Lighthouse Perf 不得为它买单。

| 指标 | 预算/基线 | 集成实测 | 判定 |
| --- | --- | --- | --- |
| Lighthouse 识字 Perf / A11y / BP | ≥ 90 / ≥ 90 / ≥ 90 | `[P/A/BP]` | `[P/F]` |
| Lighthouse 数学 Perf / A11y / BP | ≥ 90 / ≥ 90 / ≥ 90 | `[P/A/BP]` | `[P/F]` |
| 识字首屏 JS gzip | < 250 KB | `[待回填]` | `[P/F]` |
| 数学首屏 JS gzip | < 250 KB | `[待回填]` | `[P/F]` |
| OCR 懒加载块 + public/ocr 资产 | 只在 `/ocr` 路由加载 | `[KB / 加载时机]` | `[P/F]` |
| literacy-app zip | 基线 `[待回填]` MB | `[待回填]` MB（Δ`[±]`） | 记录 + 解释来源 |
| math-app zip | 基线 `[待回填]` MB | `[待回填]` MB（Δ`[±]`） | 记录 + 解释来源 |

### 4.3 浏览器矩阵 C-6（走查表，集成后回填）

| 检查项 | Chrome | Firefox | Safari/WebKit |
| --- | --- | --- | --- |
| 识字：冷启动 + 学一个字闭环 | `[P/F]` | `[P/F]` | `[P/F]` |
| 识字：拍照识字（含拒权限降级） | `[P/F]` | `[P/F]` | `[P/F]` |
| 数学：冷启动 + 答题闭环 + 逻辑游戏 | `[P/F]` | `[P/F]` | `[P/F]` |
| 双 App：aurora 主题渲染 | `[P/F]` | `[P/F]` | `[P/F]` |
| 双 App：断网冷启动 | `[P/F]` | `[P/F]` | `[P/F]` |

## 5. 手动走查（探针盲区，合并前 10 分钟过一遍）

| # | 走查项 | 期望 |
| --- | --- | --- |
| W1 | 拍照识字闭环 | 允许摄像头：取景 → 识别 → 命中字库字进讲解；拒摄像头：自动落到相册选图，无死路；识别失败给出温和重试而非报错 |
| W2 | 形近干扰观感 | 听音识字连玩 10 题：选项肉眼形近（如 日/曰/旦）、不重复、正确率不受 UI 泄露影响；单字测验同 |
| W3 | 字源动画抽查 | 新增字任抽 5 字：演变动画可播、解说词与字形对应、`prefers-reduced-motion` 降级为静帧序列 |
| W4 | 逻辑小游戏可玩 | 配对与迷宫「开始→玩→结算」完整闭环；Canvas 键盘可达；结算庆祝可跳过；reduced-motion 降级 |
| W5 | 年龄档联动 | 家长面板切 L1/L3/L5：≥5 个模块难度肉眼可辨（数域/棋盘/选项数变化）；档位持久化，重进不丢 |
| W6 | aurora 对比度 | 四主题 × 首页/学习页/游戏页：正文对比度 ≥ 4.5:1、焦点环可见；axe 对比度零新增 |
| W7 | 硬性红线抽查 | 触控 ≥ 56×56、键盘可达、庆祝可跳过、`prefers-reduced-motion` 降级（继承 Round 3/4） |

## 6. 不回归红线（继承 Round 3–6，抽查即可）

- `npm run check:round6` 保持 7/7（其口径已覆盖字库 1800 / 绘本 130 / 古诗 / 跟读 / 小游戏 / 母题）；`check:round5` 12/12、`check:round5b` 6/6 抽查
- axe critical = 0 且 serious = 0（双 App 全路由 + 交互态，`npm run test:a11y`）——aurora 新主题态也要过
- 断网冷启动完成学习闭环（`npm run test:offline`）——`/ocr`、`/memory-pairs`、`/maze` 新路由同样要离线可用（OCR 资产预缓存或给「需先联网下载」的明确降级提示）
- 运行时零第三方域名请求：tesseract 引擎/语言包一律本地 `public/ocr/`，禁 CDN
- 识字首屏 JS gzip < 250KB：OCR/字源扩量数据必须按路由懒加载，不得挤进首屏 chunk
- Android 同步不缺席：`npm run sync:android` 后 `check:android` 26/26
- FSRS 复习队列、每日冒险、吉祥物陪跑等 Play 层能力在新路由上不缺席

## 7. 回填要求

每条 H1–H7 在 `acceptance-log-round7.md` 对应小节必须有**实测数据或命令输出**（计数、日志粘贴、走查勾选）。集成回填必须带：集成 SHA、`check:round7` 全文输出（8/8）、Lighthouse 双 App 三项分数、zip 体积表、浏览器矩阵。禁止「应该可以」「理论上通过」。未达标项一律进 log §3 未达标表并写明责任分支与计划，不得静默遗漏。
