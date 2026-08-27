Model slug: claude-fable-5
# Round 11 验收标准 · 洪恩体验打磨与真机常态化

> 版本：Round 11 v1.1（2026-08-27，随探针修订同步）
> 依据：`.agent_workspace/ROUND11-BRIEF.md` + `round10-hongen-audit.md` §5 R11 归属备忘
> 配套：`.agent_workspace/acceptance-log-round11.md`（实测回填模板）、`scripts/check-round11.mjs`（H1–H8 机读探针，固定 8 个结果，`--json` 供编排器聚合）
> 判定原则：每条都能被脚本或 10 分钟内的手动步骤验证；**写进简报不跑脚本视为未交付**（主计划原则 4）。

## 0. 轮次门禁 G1–G6（顺序执行，全过才可出包）

| # | 门禁 | 验证方式 | PASS 标准 |
|---|---|---|---|
| G1 | 全量单测回归 | `npm test` | 全绿（识字 `test:srs`+`test:speech`+`test:ocr`+`check:data`+build+`check:bundle`+smoke+投稿校验；数学 `check:content`+build+smoke；feedback 单测） |
| G2 | Round 11 硬门槛 | `npm run check:round11` | 退出码 0（**8/8**，见 §1；基线 `09dfe9f` + 探针 v1.1 为 **1/8 有意红灯**，见 §4.1） |
| G3 | Round 10 不退化 | `npm run check:round10` | 退出码 0（**8/8**，H8 同口径兜底）；抽查 `check:round9` 8/8、`check:round8` 8/8 |
| G4 | Round 3 全链回归 | `npm run test:round3` | 全绿（含离线 smoke + acceptance）；axe critical/serious = 0 |
| G5 | 出包 + Android | `npm run build:all` + `npm run sync:android` + `npm run check:android` | zip 产出 + `check:android` **26/26** |
| G6 | Lighthouse 双档 | `node scripts/lighthouse-ci.mjs`（mobile 档）+ desktop 档（R10 口径） | 双 App mobile **P ≥ 95**、A/BP ≥ 90；分数落 log §2.1；原始 JSON 入 `evidence/r11/`（H6 联动） |

---

## 1. 八项硬门槛（H1–H8，固定 8 个结果）

`npm run check:round11` 逐项断言，任一 FAIL 即退出码 1。**固定输出 8 个结果**，结果数 ≠ 8 时门禁自身 FAIL——防止探针被静默削减。`--json` 输出机读汇总（`passed`/`failed`/`results[].id/status/msg`）。模块不可读取、空文件占位、引用不落盘的资产、只在注释里写标记，一律 FAIL，不设 PENDING 放行。

| ID | 交付物 | PASS 标准 | 验证方式 | 责任分支 |
|---|---|---|---|---|
| H1 | 跟读产品化 | manifest **严格 JSON 解析**（freezeChecklist ≥3 条实义字符串 + modelId 非空）+ Go/No-Go 文档**实体**（>800 字符 + Go/No-Go + 结论/判定/指标/阈值信号）+ 评测集**实体**（文档 >500 + 评测信号，或 harness 脚本带断言）+ 识字 smoke 字面 `ROUND11_H1_SMOKE` | 探针 §2.1 + 走查 W1 | r11-literacy-followread-prod |
| H2 | OCR 矩阵 | `real*.png` 有效 PNG（魔数 + ≥4KB）**按内容去重 ≥5** + `real-samples.json` 授权条目（name+license）**≥5** + CameraOcrView 失败话术（基线为假词表，见 §2.2）+ 精度脚本 `ROUND11_H2` | 探针 §2.2 + 走查 W2 | r11-literacy-ocr-matrix |
| H3 | 周计划 | 数据/图谱侧周计划信号（**池不含家长面板**）+ ParentView.vue **自身**理由/采纳信号 + 数学 smoke `ROUND11_H3_SMOKE` | 探针 §2.3 + 走查 W3 | r11-math-week-plan |
| H4 | 绘本场景 | **数据探针**：`BOOKS` 中 ≥1 页 `scene`（或 `sceneElements`）数组含 **≥2 个对象元素** + 渲染接线（BookPageScene.vue 实体 或 BookReadView scene 信号）+ `ROUND11_H4` | 探针 §2.4 + 走查 W4 | r11-literacy-book-scene |
| H5 | 儿歌过半 | `SONGS` 合规条目（R9 口径：对象 + id 非空不重复 + title/name）引用锚定音频扩展名、拒 `://`/`..`，public 资产**存在且 ≥10KB、按去重文件计 ≥8** + `ROUND11_H5` | 探针 §2.5 + 走查 W5 | r11-literacy-songs-expand |
| H6 | 预算/趋势 | `evidence/r11/` **有效证据 ≥1**（JSON 可解析 + >200B，或 md >200B）+ 预算**实体**（脚本带 route+budget+断言，或文档 >800 + 路由 + 预算/阈值） | 探针 §2.6 + G6 | r11-perf-budget-trend |
| H7 | TTS/分发 | 评估文档**实体**（>1500 + 候选方案信号 + 结论信号）**或** 商店清单实体（>500 + 商店信号，或 RELEASE-CHECKLIST 内 `ROUND11_H7` 段）**且**反馈回路实体（>500 + 反馈 + 渠道/回路/流程） | 探针 §2.7 + 走查 W6 | r11-tts-store-feedback |
| H8 | R10 不退化 | `check:round10` 退出码 0 且输出 **8/8**（链式兜底 R9/R8…） | 探针 §2.8 | 全部分支合并前 |

## 2. 探针细则（机读接线契约，逐项与 `check-round11.mjs` v1.1 对齐）

探针分两类：**数据探针**经 `scripts/alias-loader.mjs` 直接 `import` 应用数据模块（顶部 `register('./alias-loader.mjs', …)` 不可删）；**接线探针**为纯静态分析（fs + 正则，**剥注释后**匹配，无 node_modules 可跑）。剥注释规则：HTML `<!-- -->`、块 `/* */`、整行 `//` 全剥——**信号必须写成代码**（常量、断言名或行内尾注），单独一行 `// ROUND11_XX` 会被剥掉导致 FAIL。责任分支按下列路径/命名接线即绿；如需改约定，必须在同一 PR 内同步探针与本节，否则视为未交付。

> **v1.1 探针修订记录**（相对 v1.0 堵掉的漏洞，全部经基线/负向实测取证；v1.0 末版已把 H1 freezeOk 强制布尔（`09dfe9f`），v1.1 保持）：
> 1. **H1 一份文档点亮全项 + freeze 兜底正则**：v1.0 `smoke` 匹配 `/\bROUND11_H1(_SMOKE)?\b/` 且池为 `literacySmoke + doc`——同一份文档写一个 `ROUND11_H1` 字样**同时满足 harness 与 smoke**；而 `freezeOk` 在基线**恒真**（R10 spike 的 manifest 已带 5 条 freezeChecklist + modelId，实测 `freeze=true`）——v1.0 的 H1 净增量约束坍缩成「写一份含 ROUND11_H1 的 md」。另外 JSON 解析失败时 v1.0 落到 `/freezeChecklist|sha256|Go.?No.?Go/i` 文本兜底——基线 manifest 文本本身就含 `freezeChecklist` 字样，**manifest 被改坏探针反而变真**。现：smoke 收紧为字面 `ROUND11_H1_SMOKE` 且只认识字 `smoke.mjs`；Go/No-Go 与评测集拆成**两个实体腿**（长度 + 内容信号，见 §2.1）；freezeOk 解析失败 **fail-closed**（负向实测：manifest 加一个尾逗号 → v1.1 `freeze=false`，v1.0 恒真）。
> 2. **H2 ux 基线恒真 + 图不去重 + 授权清单不查**：CameraOcrView 基线已含「换一张」（实测 `ux=true`）——失败话术是零约束；real 图只数命名与魔数，**同一张图复制 5 份即过**；R10 建立的 `real-samples.json` 出处/授权清单完全不查，图与清单可脱节。现：词表剔除「换一张」，只认基线为假的 `失败|认不出|光线|太暗|模糊|重拍|ROUND11_H2`（限 CameraOcrView 自身）；PNG 按 **sha1 内容去重**计数（负向实测：一张改为另一张副本 → `real=4/5` 红）；`samples[]` 中含 `name`+`license` 的条目 ≥5（基线 3）。
> 3. **H3 跨文件拼接坍缩（R9 H3 / R10 H3 同款第三次复发）**：v1.0 `plan` 池混入 `ParentView.vue`——家长面板写一次「周计划」**同时点亮 plan 与 parent**，数据/图谱侧可以零交付。现 plan 池 = `data/` 下 `^(skill|week|daily).*\.js$` + `modules/skill-graph/*`（**不含 parent 模块**）；parent 只认 `ParentView.vue` 自身（`推荐理由|采纳|weekPlan|周计划`，基线 false）；smoke 维持数学 `ROUND11_H3_SMOKE`。
> 4. **H4 纯正则零结构校验**：v1.0 `/scene|scenes|多元素|…/` 命中即过——数据里塞个 `const scene = null` 即绿，「多元素」本体完全不查。现改**数据探针**：`import` `books.js` 后要求 ≥1 页 `page.scene`（或 `page.sceneElements`）为数组且**含 ≥2 个对象元素**（基线 132 本 / 0 页，页结构现为单 `emoji` 字段——正是「告别单 emoji」的靶子）；渲染腿 = `BookPageScene.vue` 实体（剥注释 >300 字符）或 `BookReadView.vue` 出 scene 信号；`ROUND11_H4` 标记池扩到 `data/books/` 种子文件（场景 DSL 落在 core.js/l*.js 也探得到）。
> 5. **H5 全数回退 R10 H5 v1.1 已堵过的洞**：v1.0 不过滤合规条目（重复 id 算多首）、不去重（8 条引用同一文件算 8 首）、扩展名不锚定（`/\.(mp3|…)/` 连 `fake.mp3.txt` 也算）、候选路径回退 `ref.replace(/^.*audio\//,'audio/')` 允许 **CDN URL 蹭本地同名文件**、不拒 `..` 路径穿越。现恢复 R9/R10 口径：合规条目过滤 + `^[^?#]+\.(mp3|ogg|wav|m4a)$` 锚定 + 拒 `://` 与 `..` + public 落盘 ≥10KB + **按去重资产文件计 ≥8**（负向实测：删 1 个落盘文件 → `audio=7/8` 红）。
> 6. **H6 空占位即过（R10 H4 裸 exists 同款）**：v1.0 任意 `.json/.md` 文件（含 0 字节）算证据；budget 三选一里两个是裸 `exists()`——`touch check-route-budget.mjs` 或 `touch r11-perf-budget.md` 即过。现证据须 JSON 可解析 + >200B（md 则 >200B）；预算实体 = 脚本剥注释含 `route/路由`+`budget/预算`+`process.exit|assert`，或文档 >800 字符 + 路由 + 预算/阈值信号（负向实测：文档清空 → `budget=false` 红）。
> 7. **H7 标记即过 + touch 即过**：v1.0 tts 腿是 `length>1500 || ROUND11_H7`——20 字节的「ROUND11_H7」占位文件即过；store 腿的 RELEASE-CHECKLIST 商店字样**基线恒真**（实测 true），FEEDBACK-LOOP/r11-store-checklist 裸 `exists`——**touch 一个空文件整个 H7 变绿**。现 tts = >1500 **且**候选方案信号（`piper|vits|espeak|sherpa|录音`）**且**结论信号（`结论|建议|选型|对比`）；store = 商店清单实体（`r11-store-checklist.md` >500 + 商店信号，或 RELEASE-CHECKLIST 内字面 `ROUND11_H7` 标记新增章节）**且**反馈回路实体（`FEEDBACK-LOOP.md` >500 + 反馈 + 渠道/回路/处理/流程）（负向实测：标记占位 + 空反馈文件 → `tts=false，store=false` 红）。
> 8. **保持项**：固定 8 结果自检、`--json`、H8 子进程口径、H2 PNG 魔数 + ≥4KB、H1 freezeOk 布尔化（v1.0 末版 `09dfe9f` 已修）均保留不动。

### 2.1 H1 跟读产品化（文件探针 + 接线探针）

- **冻结清单**：`apps/literacy-app/public/asr/manifest.json` 必须**严格 JSON 解析**（解析失败 fail-closed）；`freezeChecklist` 为数组且 ≥3 条 `trim().length >= 8` 的字符串；`modelId` 非空字符串。基线已满足（R10 spike 遗留）——此腿是**不退化约束**，不是 R11 净增量。
- **Go/No-Go 实体**：`.agent_workspace/r11-followread-gonogo.md` >800 字符 + `/go[\s/_-]?no[\s/_-]?go/i` + `/结论|判定|指标|阈值/`。要求写清判定指标、阈值与结论（Go 或 No-Go 都算交付，证据要可复核）。
- **评测集实体**：`.agent_workspace/r11-asr-eval-set.md` >500 字符 + `/评测|eval[\s_-]?set|冻结集/i`，**或** `apps/literacy-app/scripts/test-asr-eval-set.mjs` 剥注释后含 `/assert|process\.exit/` + `/评测|eval|冻结/i`（骨架脚本必须真有断言，不是空壳）。
- **smoke**：识字 `scripts/smoke.mjs` 剥注释后含字面 **`ROUND11_H1_SMOKE`**（写进文档不算）。
- 真模型可后续挂载（`available:false` 合法）；模型资产如引入必须本地、带哈希、禁 CDN（§6）。

### 2.2 H2 OCR 实拍矩阵（文件探针 + 接线探针）

- **样张**：`apps/literacy-app/scripts/fixtures/ocr/` 下 `^real` 命名 `.png`，逐张校验 PNG 魔数 + ≥4096 字节，**按 sha1 内容去重后 ≥5**（基线 3 张）。
- **授权清单**：同目录 `real-samples.json` 严格解析后 `samples[]` 中含 `name` + `license` 的条目 **≥5**——新图必须同步登记出处/授权（R10 建立的清单纪律不许脱节）。
- **失败话术**：`CameraOcrView.vue` 剥注释后匹配 `/失败|认不出|光线|太暗|模糊|重拍|\bROUND11_H2\b/`。**「换一张”基线已存在、不算数**；如用别的文案，落 `ROUND11_H2` 字面标记或同 PR 修订本节。
- **脚本标记**：`test-ocr-accuracy.mjs` 剥注释后含字面 **`ROUND11_H2`**（real tier 扩样真正接进精度脚本，量化结果回填 log §2.2）。
- **不退化**：R10 的 3 张真样张与 `ROUND10_H2` 断言由 H8 链兜底，扩样不得删旧图旧断言。

### 2.3 H3 推荐周计划（接线探针）

- **plan 腿**：`apps/math-app/src/data/` 下 `^(skill|week|daily).*\.js$`（建议新建 `week-plan.js`）+ `modules/skill-graph/` 全部文件，剥注释拼接后匹配 `/weekPlan|weeklyPlan|周计划|\bROUND11_H3\b/i`。**池不含 parent 模块**——家长面板的字样不能替数据层交差。
- **parent 腿**：`modules/parent/ParentView.vue` **自身**剥注释后匹配 `/推荐理由|采纳|weekPlan|周计划/i`（基线 false）：家长侧必须能看到推荐理由与采纳痕迹。
- **smoke**：数学 `scripts/smoke.mjs` 剥注释后含字面 **`ROUND11_H3_SMOKE`**（建议：进图谱 → 生成/查看周计划 → 家长面板断言理由可见）。
- **写回边界**：周计划生成/采纳仅经用户显式操作写记录；自动写回 FSRS/解锁状态仍然禁止（走查 W3）。

### 2.4 H4 绘本页级场景组合（数据探针 + 接线探针）

- **数据腿**：探针 `import` `apps/literacy-app/src/data/books.js`，遍历 `BOOKS[].pages[]`：≥1 页的 `scene`（或 `sceneElements`）为数组且**过滤后 ≥2 个非空对象元素**。元素结构（type/emoji/位置等 DSL 字段）由责任分支定义并写进 log §1；单对象、字符串数组、`null` 占位都不算。
- **渲染腿**：`src/components/BookPageScene.vue` 存在且剥注释后 >300 字符，**或** `src/views/BookReadView.vue` 剥注释后含 `/scene/i`（场景真的被读页视图消费）。
- **标记**：`ROUND11_H4` 字面落在 `books.js`、`data/books/*.js`、`BookPageScene.vue`、`BookReadView.vue` 或识字 smoke 任一（剥注释后）。
- **不退化**：无 scene 字段的旧页按原单 emoji 渲染路径展示；`verifyBookCoverage()` 字表红线由 `check:data`/G1 兜底。

### 2.5 H5 儿歌真实旋律过半（数据探针 + 文件探针）

- **曲目口径**：探针 `import` `songs.js`，按 R9 合规口径过滤（对象 + `id` 非空不重复 + `title`/`name`）；取 `audio || src || melodyUrl`，须匹配 `^[^?#]+\.(mp3|ogg|wav|m4a)$`（锚定），**含 `://` 或 `..` 的引用直接拒绝**。
- **资产落盘**：引用（去前导 `/`）解析到 `apps/literacy-app/public/` 下，文件**存在且 ≥10240 字节**；按**去重后的资产文件**计数 **≥8**（基线 3）。来源与许可证写 log §2.4 + THIRD_PARTY_NOTICES。
- **标记**：`songs.js`（剥注释）或识字 smoke 含字面 **`ROUND11_H5`**。
- **不退化**：合成旋律 `playMelody()` 降级路径不得删除；音频懒加载、不进 SW 预缓存首屏（§6）。

### 2.6 H6 路由预算与趋势（文件探针）

- **证据**：`.agent_workspace/evidence/r11/` 下有效文件 ≥1——`.json` 须 >200 字节且 `JSON.parse` 通过；`.md` 须 >200 字节。建议：双 App LH JSON（mobile/desktop）+ 一份 R10→R11 趋势 md。
- **预算实体**（二选一）：`apps/math-app/scripts/check-route-budget.mjs` 或 `scripts/check-route-budget.mjs` 剥注释后含 `route/路由` + `budget/预算` + `process.exit|assert`（能红的脚本才算）；**或** `.agent_workspace/r11-perf-budget.md` >800 字符 + `/路由|route/i` + `/预算|budget|阈值/i`（逐路由预算表 + 超标处置约定）。
- 阈值沿 G6：mobile P ≥ 95；desktop 记录分数不设硬阈值，异常回归单独立项。

### 2.7 H7 离线 TTS 评估 或 商店/反馈骨架（文件探针）

- **tts 腿**：`.agent_workspace/r11-tts-evaluation.md` **>1500 字符** 且含候选方案信号（`/piper|vits|espeak|sherpa|分批录音|录音/i`）且含结论信号（`/结论|建议|选型|对比/`）——必须是真评估（候选对比 + 明确建议），凑长度的空话过不了走查 W6。
- **store 腿**（两件都要）：商店清单实体 = `.agent_workspace/r11-store-checklist.md` >500 字符 + `/商店|Play|App Store|上架/i`，**或** `RELEASE-CHECKLIST.md` 内新增含字面 `ROUND11_H7` 的商店章节（基线商店字样恒真，故必须带标记）；反馈回路实体 = `.agent_workspace/FEEDBACK-LOOP.md` >500 字符 + `/反馈|feedback/i` + `/渠道|回路|处理|流程/`。
- H7 = tts **或** store（简报口径）；两腿都交更好，回填 log §1。

### 2.8 H8 Round 10 不退化（子进程探针）

- 探针以子进程跑 `scripts/check-round10.mjs`：退出码 0 **且**输出含 `8/8`。R10 八结果再链式兜底 R9/R8 及更早；R11 任何分支合并如碰坏其一，此处红灯。R7 及更早由 G3 在集成分支抽查兜底。

## 3. smoke 断言建议（新面必须进浏览器 smoke，随责任分支同 PR 交付）

标记写法同 R9/R10：探针剥整行 `//` 注释——标记要写成常量/断言名或**行内尾注**（如 `await interact(...) // ROUND11_H1_SMOKE`），单独一行注释会被剥掉导致 FAIL。Round 11 增量：

- **H1 跟读**：识字 smoke 增断言：跟读页在 ASR 不可用（`available:false`）时降级链路可见、无 pageerror，旁注 `ROUND11_H1_SMOKE`。
- **H3 周计划**：数学 smoke 增交互断言：图谱/家长面板可见周计划与推荐理由、采纳操作可点，旁注 `ROUND11_H3_SMOKE`。
- **H4 绘本场景**：识字 smoke 打开一本带 scene 页的绘本，断言多元素渲染无 pageerror，标记 `ROUND11_H4` 可落数据常量。
- **H2/H5**：`test-ocr-accuracy.mjs` 独立跑（挂 `npm test` 链由 G1 兜底）；儿歌新增曲目进页可播（或降级合成旋律）不报错。

## 4. 基线与预验证

### 4.1 基线红灯记录（有意红灯）+ 绿灯路径预验证

基线 `cursor/openmoji-integration-9f67` @ `09dfe9f`（R10 闭合、R11 未合并），v1.1 探针实测：

```
  ✓ H8 Round 10 门禁 8/8 无退化

  ✗ H1 跟读未产品化：freeze=true，gonogo=false，evalset=false，smoke=false —— r11-literacy-followread-prod
  ✗ H2 OCR 矩阵未闭环：real=3/5，samples=3/5，ux=false，ROUND11_H2=false —— r11-literacy-ocr-matrix
  ✗ H3 周计划未闭环：plan=false，parent=false，smoke=false —— r11-math-week-plan
  ✗ H4 绘本场景未闭环：sceneUnits=0/1，rendered=false，ROUND11_H4=false —— r11-literacy-book-scene
  ✗ H5 儿歌扩样未闭环：audio=3/8，ROUND11_H5=false —— r11-literacy-songs-expand
  ✗ H6 预算趋势未闭环：evidence=0/1，budget=false（script=false，doc=false） —— r11-perf-budget-trend
  ✗ H7 TTS/分发未闭环：tts=false，store=false（storeDoc=false，feedback=false） —— r11-tts-store-feedback

Round 11 体验门禁：1/8 项通过，7 项失败。 → 退出码 1
```

1/8 属**有意红灯**：探针先行、交付点绿（继承 Round 4–10 原则）。`--json` 实测 `passed=1 failed=7 results=8`。注意 H1 `freeze=true` 是 R10 spike 遗留的基线事实（已在 §2.1 声明为不退化腿），其余全部子信号基线为假——每个 H 的净增量约束都真实存在。

**绿灯路径预验证（8/8 全路径）**：在验收分支工作区以最小伪造交付物模拟集成——Go/No-Go 与评测集 md + 识字 smoke 标记（H1）、2 张内容不同的 ≥4KB 真 PNG + samples 登记 ×2 + 视图话术 + 脚本标记（H2）、skill-graph 周计划常量 + ParentView 理由/采纳 + 数学 smoke 标记（H3）、books.js 首页挂 2 元素 scene + BookPageScene.vue + 标记（H4）、5 份 ≥10KB 音频落 public + SONGS 挂接 + 标记（H5）、evidence/r11 有效 JSON + 预算文档（H6）、TTS 评估文档（H7 tts 腿）——实测 **8/8 → 退出码 0**，H8 子进程 `check:round10` 在伪造物叠加下仍 8/8。另单测 H7 store 腿（商店清单 + 反馈回路实体、无 tts 文档）→ H7 仍绿。
随后**负向抽查**（一轮五杀）：manifest 加尾逗号 → `freeze=false`（fail-closed，v1.0 文本兜底恒真已废）；一张 real 图改为另一张的逐字节副本 → `real=4/5`；删 1 个落盘音频（songs.js 引用仍在）→ `audio=7/8`；预算文档清空 → `budget=false`；tts 文档只留「ROUND11_H7」+ 反馈回路 touch 空文件 → `tts=false，store=false`——五路占位/伪造全部红灯，v1.0 的洞确认已堵。伪造物全部回滚不入库，回滚后复测基线仍 1/8。

### 4.2 Lighthouse / 体积（集成后回填到 acceptance-log §2.1 / §2.3）

跑法沿 R10：mobile 档 `node scripts/lighthouse-ci.mjs`（版本锁 + 阈值断言）；desktop 档同 R10 H6 交付跑法；原始 JSON 拷入 `.agent_workspace/evidence/r11/`（即 H6 证据）。R11 新增内容（音频扩样、场景 DSL、周计划）不得把任一 App mobile 档拖回 95 以下。

| 指标 | 预算/基线 | 集成实测 | 判定 |
|---|---|---|---|
| mobile 识字 P / A / BP | ≥ 95 / ≥ 90 / ≥ 90 | log §2.1 | `[P/F]` |
| mobile 数学 P / A / BP | ≥ 95 / ≥ 90 / ≥ 90 | log §2.1 | `[P/F]` |
| desktop 识字 / 数学 P | 记录 + 对比 R10（趋势入 evidence/r11） | log §2.1 | 记录 |
| 识字首屏 JS gzip | < 420 KB（`check:bundle`） | log §2.3 | `[P/F]` |
| 数学首屏 JS gzip | < 250 KB（`check:bundle`） | log §2.3 | `[P/F]` |
| zip 体积 | R10 值 + 音频 Δ 单列 | log §2.3 | 记录 |

## 5. 手动走查（探针盲区，合并前 10 分钟过一遍）

| # | 走查项 | 期望 |
|---|---|---|
| W1 | 跟读 Go/No-Go 复核 | 结论有数据支撑（评测集句目、指标、阈值可复算）；冻结清单与 manifest 一致；`available:false` 下三档降级不退化 |
| W2 | OCR 矩阵复核 | 5 张确为真实拍摄（非程序合成/非同图变体）；samples 清单出处/授权可信；弱光/模糊实拍下失败话术真的出现 |
| W3 | 周计划可信 | 周计划由推荐路径真实生成；家长面板理由与采纳痕迹对得上练习记录；仅用户点击写记录；键盘可达 |
| W4 | 绘本场景观感 | scene 页多元素渲染无破版；旧单 emoji 页不回归；低端机滚动不卡 |
| W5 | 儿歌扩样 | ≥8 首可进可播可退；来源与许可逐条记录；无音频曲目仍走合成旋律降级 |
| W6 | 预算/TTS/分发走查 | 预算表与 LH 实测对得上；TTS 评估结论可执行（体积/延迟/授权都有数）；商店清单与反馈回路可操作而非空话 |

## 6. 不回归红线（继承 Round 3–10，抽查即可）

- `check:round10` 8/8（H8 硬门槛）、`check:round9` 8/8、`check:round8` 8/8；更早轮次 G3 抽查
- 首屏 JS gzip 识字 < 420 KB、数学 < 250 KB（`check:bundle`）；音频/模型/样张一律懒加载，不进 SW 预缓存首屏
- axe critical = 0 且 serious = 0（双 App 全路由 + 交互态 + 四主题，`npm run test:a11y`）
- 断网冷启动完成学习闭环（`npm run test:offline`）
- 运行时零第三方域名请求；**禁止把未授权商业模型/曲库塞进仓库**——真模型用清单 + 哈希冻结，资产用 CC0/自建（简报红线）
- FSRS、解锁规则、母题阈值不动；周计划仅经用户显式操作写记录；家长面板、每日冒险、吉祥物陪跑不缺席
- Android 同步不缺席：`npm run sync:android` 后 `check:android` 26/26
- worktree 开发（`.agent_workspace/r11-*` 或 `/tmp/wt-r11-*`），禁止在共享 `/workspace` 切功能分支

## 7. 回填要求

每条 H1–H8 在 `acceptance-log-round11.md` 对应小节必须有**实测数据或命令输出**（计数、日志粘贴、走查勾选），§1 表格写明「要回填什么」。集成回填必须带：集成 SHA、`check:round11` 全文输出（8/8）、双档 Lighthouse 分数与版本号、OCR real tier 精度与新图授权清单、音频资产清单（文件、大小、来源、许可证）、周计划数据结构说明、scene DSL 字段说明、zip/bundle 体积表、走查勾选。禁止「应该可以」「理论上通过」。未达标项一律进 log §3 未达标表并写明责任分支与计划，不得静默遗漏。
