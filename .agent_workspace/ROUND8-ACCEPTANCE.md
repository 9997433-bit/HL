Model slug: claude-fable-5-thinking-xhigh
# Round 8 验收标准 · 深度超越与 A 层终态

> 版本：Round 8 v1.1（2026-08-27，随探针修订同步）
> 依据：`.agent_workspace/ROUND8-BRIEF.md` + `round7-hongen-final-audit.md` §R8
> 配套：`.agent_workspace/acceptance-log-round8.md`（实测回填模板）、`scripts/check-round8.mjs`（H1–H8 机读探针，固定 8 个结果）
> 判定原则：每条都能被脚本或 10 分钟内的手动步骤验证；**写进简报不跑脚本视为未交付**（主计划原则 4）。

## 0. 轮次门禁 G1–G7（顺序执行，全过才可出包）

| # | 门禁 | 验证方式 | PASS 标准 |
|---|---|---|---|
| G1 | 全量单测回归 | `npm test` | 全绿（识字 `test:srs`+`test:speech`+`test:ocr`+`check:data`+build+`check:bundle`+smoke；数学 `check:content`+build+smoke；feedback 单测） |
| G2 | Round 7 不退化 | `npm run check:round7` | 退出码 0（**8/8**，H8 同口径兜底） |
| G3 | Round 6 不退化 | `npm run check:round6` | 退出码 0（**7/7**）；抽查 `check:round5` 12/12、`check:round5b` 6/6 |
| G4 | Round 8 硬门槛 | `npm run check:round8` | 退出码 0（**8/8**，见 §1；基线 `a8b21b3` 为 **1/8 有意红灯**，见 §4.1） |
| G5 | Round 3 全链回归 | `npm run test:round3` | 全绿（含离线 smoke + acceptance）；axe critical/serious = 0 |
| G6 | 出包 + Android | `npm run build:all` + `npm run sync:android` + `npm run check:android` | zip 产出 + `check:android` **26/26** |
| G7 | Lighthouse 终验 | `npm run test:acceptance` 或手动（§4.2） | 双 App **Perf ≥ 95**、A/BP ≥ 90，按 log §2.1 表格回填（H6 探针读此表） |

---

## 1. 八项硬门槛（H1–H8，固定 8 个结果）

`npm run check:round8` 逐项断言，任一 FAIL 即退出码 1。**固定输出 8 个结果**，结果数 ≠ 8 时门禁自身 FAIL——防止探针被静默削减。`--json` 输出机读汇总（`passed`/`failed`/`results[].id/status/msg`）供编排器聚合。Round 8 是深度硬门槛：模块不可读取、视图未接路由、脚本无断言、空文件占位等一律 FAIL，不设 PENDING 放行。

| ID | 交付物 | PASS 标准 | 验证方式 | 责任分支 |
|---|---|---|---|---|
| H1 | 字源 800 | `ETYMOLOGY_CHARS` ≥ **800** 字、无重复、全汉字、`TOTAL_ETYMOLOGY` 一致；pipeline 生成 | 探针 §2.1 + `check:data`（G1 兜底） | r8-literacy-etymology |
| H2 | 单元剧情 + 儿歌 | `TOTAL_UNIT_STORIES` ≥ **99** 且 u59–u99 **功能探针**逐个非兜底；`songs.js` ≥ **3** 首合规条目 + **真实儿歌路由** | 探针 §2.2 + 走查 W2 | r8-literacy-stories |
| H3 | 技能图谱 | 数学真实路由 + 动态视图 + `skill-graph.js` ≥ **10** 节点含边关系 + 视图联动进度/年龄档 | 探针 §2.3 + 走查 W3 | r8-math-skillgraph |
| H4 | OCR 精度 + quiz | `test-ocr-accuracy.mjs`（或 `ROUND8_H4` 标记）含识别调用 + accuracy 计算 + 阈值断言；CharDetailView 形近池不退化 | 探针 §2.4 + 走查 W4 | r8-literacy-ocr-quality |
| H5 | 跟读 v2 | 音素/声调级评分或学伴对话面 + smoke 字面标记 `ROUND8_H5_SMOKE` | 探针 §2.5 + smoke §3 | r8-literacy-followread |
| H6 | Perf 95 | acceptance-log §2.3 表格行：双 App **P ≥ 95、A/BP ≥ 90**；`evidence/r8/` ≥ **2** 份 LH 原始 JSON | 探针 §2.6 + G7 | r8-perf-lighthouse |
| H7 | 全局报告 | `GLOBAL-SUMMARY-REPORT.md` 更新到 Round 8、零 ❌ 零占位、含 `evidence/r8` 证据索引 | 探针 §2.7 | r8-global-report |
| H8 | R7 不退化 | `check:round7` 退出码 0 且输出 **8/8** | 探针 §2.8 | 全部分支合并前 |

## 2. 探针细则（机读接线契约，逐项与 `check-round8.mjs` 对齐）

探针分三类：**数据探针**经 `scripts/alias-loader.mjs` 直接 `import` 应用数据模块（`@/` 按「谁 import 就落谁的 src」解析——`check-round8.mjs` 顶部的 `register('./alias-loader.mjs', …)` 不可删）；**接线探针**为纯静态分析（fs + 正则，剥注释后匹配，无 node_modules 可跑）；**功能探针**（H2 剧情独有）实际调用交付函数断言行为。责任分支按下列路径/命名接线即绿；如需改约定，必须在同一 PR 内同步探针与本节，否则视为未交付。

> **v1.1 探针修订记录**（相对 `a8b21b3` 首版堵掉的漏洞）：
> 1. H2 儿歌路由原本把 `unit-stories.js` 正文纳入关键字匹配——剧情文案里写「儿歌」二字即算路由已接；现要求真实路由 + 动态视图文件存在。
> 2. H2 剧情原本对源码正则数 `uNN:` 键（注释可凑数、空字符串可占位）；现改为 import 后的功能探针（兜底/空文案不算数）。
> 3. H4 原本 `test-ocr-accuracy.mjs` 空文件存在即过；现要求识别调用 + accuracy 计算 + 阈值断言三重内容。
> 4. H6 原探针要求「识字 … 95 / 100 / 100」斜杠格式但回填模板表格拆三格——**按模板正确回填反而不被认到**；且正则未锚定行首（日期类 `026/08/27` 有误匹配面）、证据包空目录即过。现表格行锚定 + A/BP ≥ 90 + 递归数 `evidence/r8` 的 `.json` ≥ 2。
> 5. H1 补齐 R7 同口径的 `TOTAL_ETYMOLOGY` 一致性 + 全汉字校验（防 ASCII 凑数）。
> 6. H3 数据文件原本提到 `nodes|skills|edges` 任一即过；现要求 ≥ 10 节点 + 边关系 + 视图联动。H5 关键字加词边界（`milestone` 不再误命中 `tone`）。H7 证据索引由「证据包」旧词收紧为字面 `evidence/r8`。

### 2.1 H1 字源 800（数据探针）

- 探针 `import` `apps/literacy-app/src/data/etymology-index.js`，将 `ETYMOLOGY_CHARS` 按码点展开：
  - 计数 ≥ **800**；
  - **无重复字凑数**（Set 去重后长度不变）；
  - **全部为汉字**（逐字 `\p{Script=Han}`，防用 ASCII/标点凑数）；
  - 若导出 `TOTAL_ETYMOLOGY`，必须等于实际计数。
- 模块不可读取（语法错误、路径变更）即 FAIL。
- 语料本体 `etymology.js`（演变阶段、解说词）与索引同步由识字 `check:data` 校验（G1 兜底）；扩量走 `gen-etymology.mjs` pipeline 批量生成，禁手搓 275 个新条目。
- 动画观感（演变补间、reduced-motion 静帧降级）走走查 W1。

### 2.2 H2 单元剧情 u59–u99 + 儿歌（功能探针 + 接线探针）

- **剧情（功能探针）**：探针 `import` `apps/literacy-app/src/data/unit-stories.js`：
  - `TOTAL_UNIT_STORIES` ≥ **99**（即 `STORIES` 实际键数，u1–u99）；
  - 对 u59–u99 逐个调用 `unitStory({ id, name, desc: 哨兵串 })`，返回值必须是**非空字符串**且**不含哨兵串**——兜底文案会把 `unit.desc` 嵌进去，所以「落到 `fallback()`」和「空字符串占位」都会被当场识破；
  - **接口契约**：保持 `unitStory(unit)` 导出签名与「兜底文案嵌入 `unit.desc`」的行为（或干脆删除 fallback，u59–u99 全部手写后不再需要）；改接口须同 PR 改探针与本节。
- **儿歌数据**：`apps/literacy-app/src/data/songs.js` 导出 `SONGS` 数组（或 default 导出），探针 `import` 后计数**合规条目 ≥ 3**：每条为对象、`id` 非空且不重复、有 `title`/`name`、有 `lyrics`/`lines`/`audio`/`src` 之一（光有 id 的空壳不算）。纯数据模块，勿 import Vue/浏览器 API，否则探针读取失败即 0。
- **儿歌路由**：识字 router 存在 `path` 匹配 `/song|儿歌|music|nursery/i` 的路由（推荐 `/songs`），其 `component` 为 `() => import('@/views/….vue')`（或 modules）动态导入，且视图文件真实存在。剧情文案里提「儿歌」不算路由（v1.1 已堵）。
- 儿歌音频资产走懒加载，不进 SW 首屏预缓存（§6 红线）；可播性走走查 W2。

### 2.3 H3 技能图谱（接线探针）

- **路由**：`apps/math-app/src/router/index.js` 存在 `path` 匹配 `/skill|图谱|map-graph/i` 的路由（推荐 `/skill-map`），`component` 为 `() => import('@/modules/….vue')`（或 views）动态导入且文件真实存在。
- **数据**：`apps/math-app/src/data/skill-graph.js`（或 `skills.js`）剥注释后：
  - `id:` 节点条目 ≥ **10**；
  - 含边关系信号之一：`edges|links|prereq|requires|unlocks|parent|children`——图谱必须有「先学什么才解锁什么」的边，不接受纯节点列表。
- **视图联动**：路由视图剥注释后必须同时出现 `skill|图谱` 与 `ageBand|AGE_BAND|progress|topic|母题` 之一——图谱要读真实进度/年龄档，不接受静态贴图页。
- 图形渲染、键盘可达、reduced-motion 降级走走查 W3 + §6 红线。

### 2.4 H4 OCR 精度基准 + quiz 复核（接线探针）

- **精度脚本**：`apps/literacy-app/scripts/test-ocr-accuracy.mjs` 剥注释后必须**同时**含三类信号（空文件/占位文件不算，v1.1 已堵）：
  - 识别调用：`recognize|createWorker|tesseract|ocr` 任一（真实跑 OCR pipeline，固定基准图集可用 `gen-ocr-sample.mjs` 生成）；
  - 精度计算：`accuracy|正确率|命中率` 任一（输出量化数字，回填到 log §2.2）；
  - 阈值断言：`process.exit|assert` 任一（低于基准线必须以非零退出码失败，进 CI 有牙齿）。
- 替代路径：把基准并进 `scripts/test-ocr.mjs` 时加字面标记 **`ROUND8_H4`**，同样按上述三重信号校验。
- 建议把脚本挂进识字 `package.json`（如 `test:ocr-accuracy`）并纳入 `npm test` 链——探针不强制，G1 会跑到。
- **quiz 复核（R7 存量保绿）**：`CharDetailView.vue` 必须保持 import `@/utils/distractors` 并调用 `buildOptions(`/`similarDistractors(`——基线已绿，合并时不得退化。
- 精度目标值与基准图集规模写进 log §2.2（建议 ≥ 20 张、报告逐字命中）；观感走走查 W4。

### 2.5 H5 跟读 v2（接线探针）

- **v2 能力**：`useSpeechEval.js` + `FollowReadView.vue` + `MascotCompanion.vue` 三文件合并剥注释后匹配任一：
  - 音素/声调级：`\bphonemes?\b`、`音素`、`\btones?\b`、`声调`、`声母`、`韵母`（英文词有词边界，`milestone` 不会误命中）；
  - 学伴对话面：`companion` 与 `chat|dialog|reply|对话` 相距 ≤ 80 字符，或 `学伴` 与 `对话` 相距 ≤ 40 字符；
  - 或字面标记 **`ROUND8_H5`**（显式声明入口）。
- **smoke**：`apps/literacy-app/scripts/smoke.mjs` 含字面标记 **`ROUND8_H5_SMOKE`**。注意探针先剥**整行** `//` 注释——标记要写成常量/断言名或行内尾注（如 `await interact(...) // ROUND8_H5_SMOKE`），单独一行 `// ROUND8_H5_SMOKE` 会被剥掉导致 FAIL。
- 三档降级（在线识别 → 本地评分 → 仅跟读）与隐私提示不得退化（R6/R7 存量）；对话观感走走查 W5。

### 2.6 H6 Lighthouse Perf ≥ 95 + 证据包（日志探针）

- 探针剥 HTML 注释后按**表格行锚定**解析 `acceptance-log-round8.md`：行首 `|`、第一格含 `识字`/`数学`、**第二格以 `P / A / BP` 三个数字斜杠分隔开头**（如 `| 识字 | 96 / 100 / 100 | P |`）。判定：双 App **P ≥ 95 且 A ≥ 90 且 BP ≥ 90**。
  - 回填格式**必须**用 log §2.1 现成表格：分数单格斜杠分隔、数字打头；拆成三个单元格或写在正文里探针不认（v1.1 起模板与探针已对齐，别再改散）。
- **证据包**：`.agent_workspace/evidence/r8/` 递归统计 `.json` ≥ **2** 份（至少双 App LH 原始报告；axe 输出一并归档）。空目录/`.gitkeep` 不算。
- 跑法见 §4.2；数据必须来自集成分支实测，禁止挪用 R7 的 97/94 旧数。

### 2.7 H7 全局报告 Round 8（日志探针）

- `.agent_workspace/GLOBAL-SUMMARY-REPORT.md`：
  - 长度 > 4000 字符、正文含 `Round 8`；
  - **零 ❌ 且零占位**（`⬜`、`待回填`、`[P/F]` 全部落成实测值或移入未达标表）；
  - 含字面 `evidence/r8` 证据索引——每条终验结论注明来源（命令输出、log 小节、LH 报告路径）。「证据包」泛词不再算数（v1.1 已堵，防 R7 报告残留蒙混）。

### 2.8 H8 Round 7 不退化（子进程探针）

- 探针以子进程跑 `scripts/check-round7.mjs`：退出码 0 **且**输出含 `8/8`。
- R7 八结果含 OCR 三重接线、形近字库功能探针、字源 ≥ 200、年龄档 ≥ 5/6、逻辑游戏路由、aurora、全局报告——R8 任何分支合并如碰坏其一，此处红灯。R6 及更早由 G2/G3 在集成分支兜底。

## 3. smoke 断言建议（新面必须进浏览器 smoke，随责任分支同 PR 交付）

识字 smoke（`apps/literacy-app/scripts/smoke.mjs`）现有约定：`ROUTES` 逐条开页断言无 console error/pageerror，交互断言在 interact 列表。数学 smoke 同构。Round 8 增量：

- **H2 儿歌**：`/songs` 进 ROUTES；1 项交互断言：打开任一儿歌 → 歌词渲染 → 播放/暂停切换无报错（音频可 mock 或静音）。
- **H3 技能图谱**：`/skill-map` 进 ROUTES；1 项交互断言：图谱渲染出节点、点已解锁节点跳对应模块、锁定节点给「先学 XX」提示。
- **H4 OCR 精度**：`test-ocr-accuracy.mjs` 独立跑（不进浏览器 smoke），断言整体正确率 ≥ 自定基准线并打印逐字结果。
- **H5 跟读 v2**：交互断言旁注字面 `ROUND8_H5_SMOKE`（写法见 §2.5）：进入跟读页 → v2 评分面/学伴对话面渲染 → 降级路径无 pageerror。
- **H1 字源**：现有单字页 smoke 自动覆盖新增字入口；抽查走 W1。

## 4. 基线与 Lighthouse 记录

### 4.1 基线红灯记录（有意红灯）

基线 `cursor/openmoji-integration-9f67` @ `a8b21b3`（Round 7 闭合、R8 未合并），v1.1 探针实测：

```
  ✓ H8 Round 7 门禁 8/8 无退化

  ✗ H1 字源动画 525/800 字 —— 由 r8-literacy-etymology 交付
  ✗ H2 单元剧情/儿歌未闭环：STORIES=58/99，u59–u99 兜底/缺失=u59、u60、u61、u62、u63…，儿歌=0/3，儿歌路由=缺失 —— 由 r8-literacy-stories 交付
  ✗ H3 技能图谱未闭环：路由=缺失，视图=缺失，数据=缺失，视图联动=缺失 —— 由 r8-math-skillgraph 交付
  ✗ H4 OCR/测验未闭环：精度脚本=缺失，CharDetailView 形近池=有 —— 由 r8-literacy-ocr-quality 交付
  ✗ H5 跟读 v2 未闭环：v2 能力=缺失，smoke=缺失 —— 由 r8-literacy-followread 交付
  ✗ H6 Perf 未达标：识字 P/A/BP=未回填，数学 P/A/BP=未回填（要求 P ≥ 95、A/BP ≥ 90，按 log §2.1 表格行回填），evidence/r8 JSON=0/2 —— 由 r8-perf-lighthouse 交付
  ✗ H7 全局报告未终验：Round8=缺失，❌=0，占位=0，evidence/r8 索引=缺失 —— 由 r8-global-report 交付

Round 8 深度门禁：1/8 项通过，7 项失败。 → 退出码 1
```

1/8 属**有意红灯**：探针先行、交付点绿（继承 Round 4–7 原则）。v1.1 探针已做**绿灯路径预验证**：在验收分支工作区以最小伪造交付物（800 汉字索引、u59–u99 剧情 + 3 首儿歌 + `/songs` 路由、`/skill-map` 12 节点图谱、三重信号精度脚本、声调关键字 + smoke 标记、log 表格行 + 2 份 JSON、报告 Round 8 + evidence/r8）模拟集成，实测 **8/8 → 退出码 0**，随后回滚不入库——按 §2 契约接线必然点绿。

### 4.2 Lighthouse / Perf / 体积（集成后回填到 acceptance-log §2.1 / §2.4）

跑法：`npm run test:acceptance`（对双 App dist 起本地服务并跑 Lighthouse）或手动 `lighthouse http://127.0.0.1:<port>/`；原始 JSON 拷入 `.agent_workspace/evidence/r8/`（命名如 `lighthouse-literacy.json`、`lighthouse-math.json`，axe 输出一并归档）。R7 终态识字 97 / 数学 94——本轮数学必须补到 95+，且 R8 新增内容（儿歌音频、字源扩量、图谱）不得把识字拖回 95 以下。

| 指标 | 预算/基线 | 集成实测 | 判定 |
|---|---|---|---|
| Lighthouse 识字 P / A / BP | ≥ 95 / ≥ 90 / ≥ 90（R7：97/100/100） | log §2.1 | `[P/F]` |
| Lighthouse 数学 P / A / BP | ≥ 95 / ≥ 90 / ≥ 90（R7：94/100/100） | log §2.1 | `[P/F]` |
| 识字首屏 JS gzip | < 420 KB（`check:bundle`） | log §2.4 | `[P/F]` |
| 数学首屏 JS gzip | < 250 KB（`check:bundle`） | log §2.4 | `[P/F]` |
| zip 体积 | R7：literacy 2,891,785 B / math 435,723 B | log §2.4（Δ 注明来源） | 记录 |

## 5. 手动走查（探针盲区，合并前 10 分钟过一遍）

| # | 走查项 | 期望 |
|---|---|---|
| W1 | 字源新增抽查 | 新增段任抽 5 字：演变动画可播、解说词与字形对应、reduced-motion 降级静帧 |
| W2 | 剧情 + 儿歌观感 | u59–u99 任抽 5 站：文案与单元主题对得上、无复制粘贴凑数；儿歌 3 首可进可播可退，音频懒加载 |
| W3 | 技能图谱可用 | 图谱按年龄档/进度渲染：已解锁可点进模块、锁定给先修提示；键盘可达；reduced-motion 降级 |
| W4 | OCR 精度复核 | 跑 `test-ocr-accuracy.mjs` 看逐字报告；实拍 2–3 张照片验证识别 → 讲解闭环仍通 |
| W5 | 跟读 v2 观感 | 读对/读错各试 3 次：声调/音素反馈或学伴回应有区分度；拒麦克风降级路径完好、隐私提示在 |
| W6 | 硬性红线抽查 | 触控 ≥ 56×56、键盘可达、庆祝可跳过、四主题对比度 ≥ 4.5:1（继承 R3–R7） |

## 6. 不回归红线（继承 Round 3–7，抽查即可）

- `check:round7` 8/8（H8 硬门槛）、`check:round6` 7/7；`check:round5` 12/12、`check:round5b` 6/6 抽查
- 首屏 JS gzip 识字 < 420 KB、数学 < 250 KB（`check:bundle`）；OCR / 字源 / 儿歌重资产懒加载，不进 SW 预缓存首屏
- axe critical = 0 且 serious = 0（双 App 全路由 + 交互态 + 四主题，`npm run test:a11y`）
- 断网冷启动完成学习闭环（`npm run test:offline`）——`/songs`、`/skill-map` 新路由离线可用或给明确降级提示
- 运行时零第三方域名请求：OCR 引擎/语言包/儿歌音频一律本地资产，禁 CDN
- FSRS、解锁规则、母题 185 阈值不动；家长面板、每日冒险、吉祥物陪跑在新路由不缺席
- Android 同步不缺席：`npm run sync:android` 后 `check:android` 26/26
- worktree 开发（`/tmp/wt-r8-*`），禁止在共享 `/workspace` 切功能分支

## 7. 回填要求

每条 H1–H8 在 `acceptance-log-round8.md` 对应小节必须有**实测数据或命令输出**（计数、日志粘贴、走查勾选）。集成回填必须带：集成 SHA、`check:round8` 全文输出（8/8）、Lighthouse 双 App 三项分数（**按 §2.6 表格行格式**）、OCR 精度基准值、zip 体积表、走查勾选。禁止「应该可以」「理论上通过」。未达标项一律进 log §3 未达标表并写明责任分支与计划，不得静默遗漏。
