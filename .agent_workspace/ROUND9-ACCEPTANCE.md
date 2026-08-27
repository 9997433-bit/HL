Model slug: claude-fable-5-thinking-xhigh
# Round 9 验收标准 · 深度打磨与发布工程

> 版本：Round 9 v1.1（2026-08-27，随探针修订同步）
> 依据：`.agent_workspace/ROUND9-BRIEF.md` + `round8-hongen-audit.md` §R9 归属备忘
> 配套：`.agent_workspace/acceptance-log-round9.md`（实测回填模板）、`scripts/check-round9.mjs`（H1–H8 机读探针，固定 8 个结果，`--json` 供编排器聚合）
> 判定原则：每条都能被脚本或 10 分钟内的手动步骤验证；**写进简报不跑脚本视为未交付**（主计划原则 4）。

## 0. 轮次门禁 G1–G6（顺序执行，全过才可出包）

| # | 门禁 | 验证方式 | PASS 标准 |
|---|---|---|---|
| G1 | 全量单测回归 | `npm test` | 全绿（识字 `test:srs`+`test:speech`+`test:ocr`+`check:data`+build+`check:bundle`+smoke；数学 `check:content`+build+smoke；feedback 单测） |
| G2 | Round 9 硬门槛 | `npm run check:round9` | 退出码 0（**8/8**，见 §1；基线 `ec733bb` + 探针 v1.1 为 **1/8 有意红灯**，见 §4.1） |
| G3 | Round 8 不退化 | `npm run check:round8` | 退出码 0（**8/8**，H8 同口径兜底）；抽查 `check:round7` 8/8、`check:round6` 7/7 |
| G4 | Round 3 全链回归 | `npm run test:round3` | 全绿（含离线 smoke + acceptance）；axe critical/serious = 0 |
| G5 | 出包 + Android | `npm run build:all` + `npm run sync:android` + `npm run check:android` | zip 产出 + `check:android` **26/26** |
| G6 | Lighthouse 终验 | `scripts/lighthouse-ci.mjs`（H6 交付）或 `npm run test:acceptance` | 双 App **Perf ≥ 95**、A/BP ≥ 90，按 log §2.1 表格回填；原始 JSON 入 `evidence/r9/` |

---

## 1. 八项硬门槛（H1–H8，固定 8 个结果）

`npm run check:round9` 逐项断言，任一 FAIL 即退出码 1。**固定输出 8 个结果**，结果数 ≠ 8 时门禁自身 FAIL——防止探针被静默削减。`--json` 输出机读汇总（`passed`/`failed`/`results[].id/status/msg`）。模块不可读取、视图未接路由、脚本无断言、空文件占位等一律 FAIL，不设 PENDING 放行。

| ID | 交付物 | PASS 标准 | 验证方式 | 责任分支 |
|---|---|---|---|---|
| H1 | 儿歌 v2 | `SONGS` **合规条目 ≥ 10**（R8 同口径）+ 歌词同步 v2 信号（剥注释）+ smoke 标记 `ROUND9_H1_SMOKE` | 探针 §2.1 + 走查 W1 | r9-literacy-songs |
| H2 | OCR 扩样 | fixtures **有效 PNG ≥ 8**（魔数 + ≥1KB）、handwriting 命名 ≥ 2 张、精度脚本内 tier 信号 + `ROUND9_H2` | 探针 §2.2 + 走查 W2 | r9-literacy-ocr-expand |
| H3 | 图谱推荐 | **R9 专属**推荐路径函数（`nextSkills` 是 R8 存量不算数）+ 视图展示 + smoke 标记 `ROUND9_H3_SMOKE` | 探针 §2.3 + 走查 W3 | r9-math-graph-reco |
| H4 | 跟读路线 | 评估文档（> 800 字符 + ASR/音素 + 离线/评估关键词）**或** PoC 接线（剥注释） | 探针 §2.4 + 走查 W4 | r9-literacy-followread-asr |
| H5 | 绘本投稿 | `BOOK-COMMUNITY-SUBMISSION.md` > 1500 字符 + 投稿 + schema/字段 + fenced 示例块 | 探针 §2.5 + 走查 W5 | r9-content-quality |
| H6 | LH CI 锁 | `scripts/lighthouse-ci.mjs` 存在且含 lighthouse + **版本锁** + 阈值断言；`evidence/r9` **可解析 JSON ≥ 2** | 探针 §2.6 + G6 | r9-perf-ci-device |
| H7 | 发布清单 | 报告含 Round 9 + `evidence/r9` 索引 + **零 ⏳/❌/「待 R8」**；`RELEASE-CHECKLIST.md` > 800 字符含 LICENSE/发布/证据三重信号 | 探针 §2.7 | r9-global-release |
| H8 | R8 不退化 | `check:round8` 退出码 0 且输出 **8/8** | 探针 §2.8 | 全部分支合并前 |

## 2. 探针细则（机读接线契约，逐项与 `check-round9.mjs` v1.1 对齐）

探针分两类：**数据探针**经 `scripts/alias-loader.mjs` 直接 `import` 应用数据模块（顶部 `register('./alias-loader.mjs', …)` 不可删）；**接线探针**为纯静态分析（fs + 正则，**剥注释后**匹配，无 node_modules 可跑）。剥注释规则：HTML `<!-- -->`、块 `/* */`、整行 `//` 全剥——**信号必须写成代码**（常量、断言名或行内尾注），单独一行 `// ROUND9_XX` 会被剥掉导致 FAIL。责任分支按下列路径/命名接线即绿；如需改约定，必须在同一 PR 内同步探针与本节，否则视为未交付。

> **v1.1 探针修订记录**（相对 `ec733bb` 首版堵掉的漏洞）：
> 1. **H3 reco 信号基线恒真**：v1.0 用 `/recommend|nextSkills|推荐/` 匹配 `skill-graph.js`——`nextSkills()` 是 **Round 8 交付物**（`ec733bb` 上实测 `reco=true`），R9 只需加一行 smoke 标记即可绿灯，推荐路径本体可以完全不交。现要求 R9 专属路径函数信号 + 视图展示信号（基线均为 false，已验证）+ smoke。
> 2. **H2 `ROUND8_H4` 交替项恒真**：v1.0 接受 `/ROUND8_H4|ROUND9_H2/`，而 `ROUND8_H4` 在基线 `test-ocr-accuracy.mjs` 里已存在——该信号形同虚设。且 PNG 只数文件名（0 字节/改扩展名可凑 8 张）、handwriting 光靠文件名即过。现要求 `ROUND9_H2`（剥注释）+ PNG 魔数与 ≥1KB 校验 + handwriting 命名图 ≥ 2 张 + 脚本内 tier 信号。
> 3. **H1 裸计数**：v1.0 数 `SONGS.length`——10 个空对象/重复 id 也算 10 首，倒退回 R8 v1.0 已堵过的洞；且 v2 标记对 `SongsView.vue` **不剥注释**（写句注释就过）、简报硬门槛里的 smoke 根本没被检查。现复用 R8 合规条目口径（对象 + id 非空不重复 + title/name + lyrics/lines/audio/src 之一）、剥注释匹配、强制 `ROUND9_H1_SMOKE`。
> 4. **H4 纯长度即过**：v1.0 `doc.length > 800` 即绿——贴 800 字符任意水文即过；PoC 正则不剥注释。现文档须同时含 ASR/音素与离线/评估关键词；PoC 剥注释后匹配。
> 5. **H5 单关键字即过**：v1.0 三关键字**任一**命中即绿（1500 字符里出现一次 "JSON" 就过）。现要求 投稿 AND schema/字段/JSON AND fenced 代码块示例。
> 6. **H6 拼接 package.json**：v1.0 把 `package.json` 拼进正则——只要 scripts 里起个叫 `lighthouse-ci` 的名字、`scripts/lighthouse-ci.mjs` 文件不存在也能过；证据 JSON 空文件即算。现要求文件存在 + lighthouse/版本锁/阈值断言多重信号（剥注释）+ JSON 可解析且 > 200 字节。
> 7. **H7 占位不拦、单关键字即过**：v1.0 报告只查 `Round 9` 字样——9 处 `⏳ 待 R8` 残留照样绿，违背简报 P0「31/31 去掉全部 ⏳」；清单三关键字任一即过。现报告加零 ⏳/❌/「待 R8」+ 字面 `evidence/r9` 索引，清单三重信号齐备。
> 8. **元自检与 `--json` 缺失**：v1.0 收集了 `results` 数组但从未输出，也没有 R8 的「结果数 ≠ 8 门禁自身 FAIL」防削减自检。现两者补齐，与 `check-round8.mjs` 同款。

### 2.1 H1 儿歌 v2（数据探针 + 接线探针）

- **曲库**：探针 `import` `apps/literacy-app/src/data/songs.js`，`SONGS`（或 default 导出）**合规条目 ≥ 10**：每条为对象、`id` 非空且不重复、有 `title`/`name`、有 `lyrics`/`lines`/`audio`/`src` 之一（光有 id 的空壳不算）。基线 7 首全合规 → 净增 ≥ 3 首真歌。纯数据模块勿 import Vue/浏览器 API，否则读取失败即 0。
- **新歌红线**：歌词逐字必须在 `characters.js` 字表内（`verifySongCoverage()`，`check:data` / G1 兜底）；`notes` 逐字音名个数与汉字数对上；无音频文件（合成旋律 + TTS 路线不变）。
- **v2 信号**：`SongsView.vue` + 识字 smoke **剥注释后**匹配 `/ROUND9_H1|歌词同步|lyric[-_]?sync|songs?[-_]?v2/i`——歌词同步动画增强要落在代码里（类名、常量、函数名均可），写句注释不算。
- **smoke**：识字 `scripts/smoke.mjs` 剥注释后含字面 **`ROUND9_H1_SMOKE`**（建议写成断言名或行内尾注，见 §3）。

### 2.2 H2 OCR 基准扩样（文件探针 + 接线探针）

- **基准图**：`apps/literacy-app/scripts/fixtures/ocr/` 下**有效 PNG ≥ 8**——逐张校验 PNG 魔数（`89 50 4E 47 …`）且 ≥ 1KB，0 字节文件、改扩展名的占位一律不算；其中**文件名含 `handwriting`/`hand`/`手写` 的 ≥ 2 张**（tier 是一组图不是一张，命名如 `handwriting-note.png`）。基线 4 张（blackboard/blurry-note/book-page/warm-light）。
- **脚本接线**：`test-ocr-accuracy.mjs` 剥注释后含 `handwriting|手写`（tier 真正接进基准集，光加图不跑不算）+ 字面 **`ROUND9_H2`**。
- **不退化**：R8 H4 的三重信号（识别调用 + accuracy 计算 + 阈值断言）由 `check:round8` 兜底——扩样不得删掉总阈值断言；tier 可以设分层阈值（手写/低光允许低于印刷体基准），量化结果回填 log §2.2。
- 低光/复杂背景 tier 按简报 P0 一并扩样（建议 lowlight-\*/complex-\* 命名），探针只硬锁 handwriting（简报硬门槛口径），其余走走查 W2。

### 2.3 H3 技能图谱推荐路径（接线探针）

- **路径函数**：`apps/math-app/src/data/skill-*.js` 全部文件 + `modules/skill-graph/` 目录下全部文件，剥注释后匹配 `/推荐路径|recommend(ed)?Path|ROUND9_H3/i`。推荐命名 `recommendPath()`：基于真实进度/FSRS 掌握度，从当前技能到目标技能给出一条**只读**学习路径（对比 R8 `nextSkills()` 的「下 4 个」平铺列表，路径要沿依赖边走）。若另起文件名/函数名，用字面 `ROUND9_H3` 显式声明入口。
- **视图展示**：`SkillGraphView.vue` 剥注释后含 `推荐|recommend`——推荐路径要画在图谱上（高亮路径/侧栏列表均可），不接受纯数据函数无 UI。基线视图无此信号（已验证），这是 R9 净增量。
- **smoke**：识字或数学 `scripts/smoke.mjs` 剥注释后含字面 **`ROUND9_H3_SMOKE`**（推荐放数学侧，见 §3）。
- **只读红线**：推荐不写回——不改 FSRS 状态、不解锁节点、不加进度（走查 W3 验证）。

### 2.4 H4 跟读 v3 ASR/音素路线（文档探针 或 接线探针，二选一）

- **文档路径固定**：`.agent_workspace/r9-followread-asr-evaluation.md`，> 800 字符**且**含 `ASR|音素|phoneme` **且**含 `离线|offline|评估|evaluat`——要的是离线 ASR/音素评估的候选方案、包体积/延迟代价与三档降级兼容性论证，不是 800 字符水文。
- **或 PoC**：`useSpeechEval.js` + `utils/speechEval.js` 剥注释后匹配 `/phonemeMarks|similarityV2|ROUND9_H4/i`。
- 三档降级（在线识别 → 本地评分 → 仅跟读）与隐私提示**不得破坏**（§6 红线 + R6/R7 存量探针兜底）；PoC 若引第三方模型必须本地资产、禁 CDN。

### 2.5 H5 绘本社区投稿格式（文档探针）

- `.agent_workspace/BOOK-COMMUNITY-SUBMISSION.md`：> 1500 字符，**同时**含「投稿」、`schema|字段|JSON` 之一、fenced 代码块（```）示例。
- 内容要求（走查 W5 验证可执行性）：绘本 JSON schema 逐字段说明（含分级字表约束——每页正文用字必须在指定级别字表内，同儿歌红线）、完整投稿示例、校验方式（挂哪条 `check:data` 链）、审核/拒稿标准。

### 2.6 H6 Lighthouse 版本锁 CI + 证据包（接线探针 + 文件探针）

- **CI 脚本**：`scripts/lighthouse-ci.mjs` 必须存在，剥注释后**同时**含：`lighthouse`、`version|版本`（**版本锁**——锁定 LH 大版本防跨版本评分口径漂移，实现方式不限：断言 `lighthouse/package.json` 版本、固定 `LH_VERSION` 常量比对均可）、`process.exit|assert`（阈值断言，低于线非零退出）、`95|MIN_LH|threshold|阈值`（阈值本体，双 App P ≥ 95、A/BP ≥ 90，与 G6 同口径）。本地起服务本地跑，禁远端 PSI（零第三方域名红线）。
- **证据包**：`.agent_workspace/evidence/r9/` 递归统计**可解析且 > 200 字节**的 `.json` ≥ 2（双 App LH 原始报告，命名如 `lighthouse-literacy.json`/`lighthouse-math.json`；axe 输出一并归档）。空文件、`{}` 占位不算。
- Android 真机走查清单（简报工程项）归入本分支交付，探针不硬锁，回填 log §4。

### 2.7 H7 Round 9 报告 + 发布清单（日志探针）

- **报告** `GLOBAL-SUMMARY-REPORT.md`：含 `Round 9`、字面 `evidence/r9` 证据索引，且**零 ⏳、零 ❌、零「待 R8」**——对齐简报 P0「31/31 ✅（去掉全部 ⏳ 待 R8）」，基线残留 9 处（含图例行），全部要落成实测状态。
  - ⚠️ 预验证实测教训：31 个模块行的**行数**被 `check:round7` H7 计数——收口时必须**改写状态列**，整行删掉会把 R7 门禁碰红（见 §4.1）。
- **清单** `RELEASE-CHECKLIST.md`：> 800 字符，**同时**含 `LICENSE`、`发布|release`、`证据|evidence|回滚`——LICENSE/第三方声明确认、发布步骤、证据归档与回滚预案缺一不可。对外声明草案（简报发布项）建议并入本文件或旁置，探针不单独硬锁。

### 2.8 H8 Round 8 不退化（子进程探针）

- 探针以子进程跑 `scripts/check-round8.mjs`：退出码 0 **且**输出含 `8/8`。
- R8 八结果含字源 800、u59–u99 功能探针、儿歌合规 ≥ 3 + 路由、技能图谱三重接线、OCR 三重信号、跟读 v2、LH 表格行 + evidence/r8、R7 链式兜底——R9 任何分支合并如碰坏其一，此处红灯。R7/R6 及更早由 G3 在集成分支抽查兜底。

## 3. smoke 断言建议（新面必须进浏览器 smoke，随责任分支同 PR 交付）

识字 smoke（`apps/literacy-app/scripts/smoke.mjs`）现有约定：`ROUTES` 逐条开页断言无 console error/pageerror，交互断言在 interact 列表；数学同构。**标记写法**：探针剥整行 `//` 注释——标记要写成常量/断言名或行内尾注（如 `await interact(...) // ROUND9_H1_SMOKE`），单独一行 `// ROUND9_H1_SMOKE` 会被剥掉导致 FAIL。Round 9 增量：

- **H1 儿歌 v2**：R8 已有「唱一遍逐字高亮」交互断言，v2 增强断言歌词同步动画推进（当前行高亮/滚动跟随），旁注 `ROUND9_H1_SMOKE`。
- **H3 图谱推荐**：数学 smoke 增 1 项交互断言：进入 `/skill-map` → 推荐路径渲染（高亮/列表可见）→ 点推荐项跳对应模块或给先修提示，旁注 `ROUND9_H3_SMOKE`。
- **H2 OCR**：`test-ocr-accuracy.mjs` 独立跑（不进浏览器 smoke），逐 tier 打印精度；建议挂 `test:ocr:accuracy` 进 `npm test` 链（G1 兜底）。
- **H4 PoC**（如走 PoC 路线）：跟读页降级路径断言不得删；PoC 面渲染无 pageerror。

## 4. 基线与预验证

### 4.1 基线红灯记录（有意红灯）

基线 `cursor/openmoji-integration-9f67` @ `ec733bb`（Round 8 闭合、R9 未合并），v1.1 探针实测：

```
  ✓ H8 Round 8 门禁 8/8 无退化

  ✗ H1 儿歌 v2 未闭环：7/10 首合规，v2=缺失，smoke=缺失 —— r9-literacy-songs
  ✗ H2 OCR 扩样未闭环：有效 PNG=4/8，handwriting 图=0/2，脚本 tier=false，ROUND9_H2=false —— r9-literacy-ocr-expand
  ✗ H3 图谱推荐未闭环：路径函数=false，视图展示=false，smoke=false —— r9-math-graph-reco
  ✗ H4 跟读路线未闭环：doc=false（0 字符），poc=false —— r9-literacy-followread-asr
  ✗ H5 绘本投稿文档未闭环：长度=0/1500，投稿=false，schema=false，示例=false —— r9-content-quality
  ✗ H6 Perf CI 未闭环：ci=false，有效 json=0/2 —— r9-perf-ci-device
  ✗ H7 发布清单未终验：报告=false（Round9=false，evidence/r9=false，占位=有残留），清单=false（0 字符） —— r9-global-release

Round 9 深度门禁：1/8 项通过，7 项失败。 → 退出码 1
```

1/8 属**有意红灯**：探针先行、交付点绿（继承 Round 4–8 原则）。v1.1 已做**绿灯路径预验证**：在验收分支工作区以最小伪造交付物（10 首合规儿歌 + 歌词同步/smoke 标记、8 张有效 PNG 含 2 张 handwriting + 脚本信号、`recommendPath` + 视图/ smoke 信号、关键词齐备的评估文档、含 schema 与示例的投稿文档、版本锁 CI 脚本 + 2 份 JSON、报告改写 ⏳→✅ + RELEASE-CHECKLIST）模拟集成，实测 **8/8 → 退出码 0** 且 `check:round8`/`check:round7` 链全绿，随后回滚不入库——按 §2 契约接线必然点绿。预验证顺带发现：模拟第一版把报告里带 ⏳ 的模块**整行删除**，`check:round7` H7 的 31 模块行计数当场红灯——已写进 §2.7 警示，r9-global-release 收口时只能改写状态列。

### 4.2 Lighthouse / Perf / 体积（集成后回填到 acceptance-log §2.1 / §2.3）

跑法：`node scripts/lighthouse-ci.mjs`（H6 交付，版本锁 + 阈值断言）或 `npm run test:acceptance`；原始 JSON 拷入 `.agent_workspace/evidence/r9/`。R8 终态识字 98/100/100、数学 99/100/100——R9 新增内容（儿歌扩库、OCR 图集、推荐路径渲染）不得把任一 App 拖回 95 以下。

| 指标 | 预算/基线 | 集成实测 | 判定 |
|---|---|---|---|
| Lighthouse 识字 P / A / BP | ≥ 95 / ≥ 90 / ≥ 90（R8：98/100/100） | log §2.1 | `[P/F]` |
| Lighthouse 数学 P / A / BP | ≥ 95 / ≥ 90 / ≥ 90（R8：99/100/100） | log §2.1 | `[P/F]` |
| 识字首屏 JS gzip | < 420 KB（`check:bundle`） | log §2.3 | `[P/F]` |
| 数学首屏 JS gzip | < 250 KB（`check:bundle`） | log §2.3 | `[P/F]` |
| zip 体积 | R8：literacy 6,228,970 B / math 455,047 B | log §2.3（Δ 注明来源） | 记录 |

## 5. 手动走查（探针盲区，合并前 10 分钟过一遍）

| # | 走查项 | 期望 |
|---|---|---|
| W1 | 儿歌 v2 观感 | 新增歌任抽 3 首：可进可播可退、歌词同步动画跟得上节奏、reduced-motion 降级为静态高亮；新歌歌词无字表外用字 |
| W2 | OCR tier 复核 | 跑 `test-ocr-accuracy.mjs` 看逐 tier/逐字报告：handwriting/低光/复杂背景各 tier 有量化数字且过各自阈值 |
| W3 | 图谱推荐可信 | 推荐路径与真实进度对得上（学完推荐首项后刷新，路径前移）；**只读**——localStorage 里 FSRS/解锁状态无写回；键盘可达 |
| W4 | 跟读路线评审 | 文档结论可执行（候选方案有包体积/延迟数据、有明确取舍）或 PoC 三档降级完好、隐私提示在、拒麦克风路径无 pageerror |
| W5 | 投稿文档演练 | 照文档从零写一本最小合规绘本 JSON：字段齐、能过校验；故意放一个字表外字，校验能拦住 |
| W6 | 发布走查 | LICENSE/第三方声明与实际依赖一致（OpenMoji/Tesseract/字体逐个核）；RELEASE-CHECKLIST 逐项可执行；Android 真机清单可照做 |

## 6. 不回归红线（继承 Round 3–8，抽查即可）

- `check:round8` 8/8（H8 硬门槛）、`check:round7` 8/8、`check:round6` 7/7；`check:round5` 12/12、`check:round5b` 6/6 抽查
- 首屏 JS gzip 识字 < 420 KB、数学 < 250 KB（`check:bundle`）；OCR 图集/儿歌/图谱重资产懒加载，不进 SW 预缓存首屏
- axe critical = 0 且 serious = 0（双 App 全路由 + 交互态 + 四主题，`npm run test:a11y`）
- 断网冷启动完成学习闭环（`npm run test:offline`）——R9 无新路由，存量 `/songs`、`/skill-map` 离线可用不得退化
- 运行时零第三方域名请求：LH CI 本地跑、ASR PoC 模型本地资产，禁 CDN/远端 PSI
- FSRS、解锁规则、母题 185 阈值不动；**图谱推荐只读不写回**；家长面板、每日冒险、吉祥物陪跑不缺席
- Android 同步不缺席：`npm run sync:android` 后 `check:android` 26/26
- worktree 开发（`/tmp/wt-r9-*`），禁止在共享 `/workspace` 切功能分支

## 7. 回填要求

每条 H1–H8 在 `acceptance-log-round9.md` 对应小节必须有**实测数据或命令输出**（计数、日志粘贴、走查勾选），§1 表格写明「要回填什么」。集成回填必须带：集成 SHA、`check:round9` 全文输出（8/8）、Lighthouse 双 App 三项分数与锁定的 LH 版本号、OCR 逐 tier 精度、zip/bundle 体积表、走查勾选。禁止「应该可以」「理论上通过」。未达标项一律进 log §3 未达标表并写明责任分支与计划，不得静默遗漏。
