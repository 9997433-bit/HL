# Round 18 架构 · 密度收口 + 拆包性能 + 剖析对齐

> 岗位：r18-arch-contracts（子代理 #1）
> 分支：`cursor/r18-arch-contracts-9f67`（基于 `cursor/r18-orchestration-9f67` @ `770bded`）
> 本文是 H2 / H3 / H4 / H5 各实现岗的共同契约。改契约先改本文档。
> 本岗只定协议不做 UI；所有数字都是在编排分支上实测的，不是抄简报。

## 0. 一页话总览（本岗实测基线）

| 维度 | 实测现状（770bded） | R18 目标 | 归属 |
|---|---|---|---|
| 富 Play | `countRichPlays()` = **940**（seed 覆盖 u1–u55，全库 99 单元 × 大多 20 字/单元） | ≥**1200** 条、narration 去重 ≥**960** | H2 |
| rich 打包 | `char-play.js` 顶层 `import * as richModule from './char-play-rich.js'`（源码 **262KB**）；`char-intro.js` 也同步 `import { getRichPlay }`。CharPlayStage → CharDetailView 同步链整包吃进 | rich 按单元懒加载分片；单字关键路径只拉当前单元一片 | H3 |
| 剖析步数 | 214 母题；`template.steps` 与 `analyzeEquation(make().equation).length` 一致 **158/214 = 73.8%**（不一致 56 条，见 §3.1 归类）；104 题剖析仅 1 步 | 一致率 ≥**90%**（本契约照 §3 修完应为 100%） | H4 |
| 手写剖析 | `EXPLAIN_COUNT` = **50** 条登记（34 手写母题 + 16 语义条）；经皮肤展开 214 题全部命中 | 登记 ≥**80** 条、去重中文讲解句 ≥**200** | H5 |

四块延续既有纪律：**数据层同步纯函数、永不 null、Node 可跑；UI 层可跳过、
reduced-motion 完整可用**。所有 `ROUND18_H*` 标记必须落在**可执行代码**里
（探针剥注释后再扫，写在注释里等于没写）。

---

## 1. H2 · 富 Play seed 扩到 ≥1200 的契约（r18-play-rich-1200 岗）

### 1.1 只改 seed 与生成器阈值，不改运行时形状

流水线不动：`scripts/data/char-play-seed.txt`（五段式 `字|主题|模板|旁白|道具`）
→ `node scripts/gen-char-play-rich.mjs` → 生成物（**注意：生成物落点本轮变了，见 §2.2，
由 H3 岗先改生成器落盘逻辑，H2 岗只管 seed 内容与阈值**）。
条目形状（char/unit/theme/template/interaction/narration/props/templateFallback:false）一个字段不加不减。

### 1.2 单元范围与配额

- 字表 u54 起每单元 20 字；累计 **u68 = 1200 字整**，所以 seed 至少续写 **u56–u68**；
  **建议写满 u56–u75（1340 条）** 给探针留余量，也和简报「约 u56–u75」对齐。
- `gen-char-play-rich.mjs` 参数改动（一处一行，全部有既有变量）：
  - `RICH_UNIT_LIMIT`: 55 → **75**
  - `MIN_RICH_PLAYS`: 900 → **1200**
  - `MIN_DISTINCT_NARRATION`: 720 → **960**
  - `PROBE_MARK`: `'ROUND17_H2'` → **`'ROUND18_H2'`**
  - `PROBE_HISTORY`: 追加为 `['ROUND15_H3', 'ROUND16_H3', 'ROUND17_H2', PROBE_MARK]`
    （历轮探针剥注释后仍要读得到自己那一枚，一个都不许删）

### 1.3 narration 去重（全库口径，不是增量口径）

- 生成器现有两道闸不许放松：一字不差撞句判错 + `narrationKey()` 近似撞句
  （只差标点/语气词）判错；`distinctNarrationKeys !== rows.length` 拒绝落盘。
- **新写的 u56–u75 要和已有 u1–u55 的 940 句一起去重**——生成器本来就是全量校验，
  所以「续写时抄前 55 个单元的句子」同样会被拦，不要试。
- 旁白仍然照着字义写（雨接雨滴、火添柴那个标准），≤26 字口语，能讲出这个字是什么。

### 1.4 ROUND18_H2 落点

- 生成物 manifest（§2.2 的 `play-rich/index.js`）里：
  `export const RICH_PLAY_PROBE = 'ROUND18_H2'` + `RICH_PLAY_PROBE_HISTORY`（历轮全带）。
- 生成器 `gen-char-play-rich.mjs` 自身的 `PROBE_MARK` 常量也是可执行标记（scripts 目录在扫描范围内）。
- 探针数法（给 spec 岗）：`await loadAllRichPlays()`（§2.3）后
  `countRichPlays() ≥ 1200` 且 narration 去重 ≥ 960；同时校验 manifest 自报数与实测一致（manifest 说谎即红）。

---

## 2. H3 · 富脚本按单元懒加载（r18-play-codesplit 岗）——本轮最重的一刀

### 2.1 现状与目标

现状同步链：`CharDetailView.vue` →(静态)→ `CharPlayStage.vue` →(静态)→ `char-play.js`
→(静态)→ `char-play-rich.js`（262KB 源码）。另有 `char-intro.js` →(静态)→ `char-play-rich.js`。
结论：**单字详情的关键路径整包吃进全部 940（将来 1340）条富脚本**。

目标：打开单字详情首包不含 rich 全量；进入某个字时只加载它所在单元的一片；
`check:bundle` 预算（ENTRY_JS_BUDGET_KB=420）不放宽。

### 2.2 分片命名与索引（生成器落盘契约）

`gen-char-play-rich.mjs` 改为输出一个目录（对齐既有 `data/chars/uN.js` 课文分片先例）：

```
apps/literacy-app/src/data/play-rich/
  u1.js … u75.js     每单元一片：export const UNIT_RICH_PLAYS = [ …完整条目… ]
  index.js           manifest（轻量，可进同步包）
```

`index.js`（生成器产出，唯一允许被同步 import 的文件）导出：

- `RICH_PLAY_UNIT_LOADERS`：`{ u1: () => import('./u1.js'), …, u75: () => import('./u75.js') }`
  ——字面量动态 import 表，Vite/Rollup 据此每单元切一个 chunk。
- `RICH_PLAY_MANIFEST`：`{ plays, narrations, units: [...], perUnit: { u1: 20, … } }`
  ——生成期实测数字，运行时/探针对账用。**不含任何 narration/props 正文**，
  保证 index.js 体积 O(单元数) 而不是 O(条数)。
- `RICH_PLAY_PROBE = 'ROUND18_H2'`、`RICH_PLAY_PROBE_HISTORY`、`RICH_PLAY_THRESHOLDS`、
  `RICH_SPLIT_PROBE = 'ROUND18_H3'`（本轮拆包的可执行标记之一）。

**旧 `src/data/char-play-rich.js` 删除**（不留薄壳——留壳等于给人再同步 import 的门）。
受影响引用全列在 §2.5 接线清单，谁改谁在清单上打勾。

### 2.3 char-play.js 的 API 契约（异步化但不砸同步纪律）

`RICH` 注册表与 `registerCharPlays()` 保留，改成由 loader 喂：

| API | 签名 | 契约 |
|---|---|---|
| `ensurePlayUnit(unitId)` | `(string) => Promise<void>` | 加载并注册该单元分片；幂等（缓存 Promise，不重复拉）；未知 unitId 静默 resolve（走 generated 兜底，不 reject） |
| `preloadPlayUnits(unitIds)` | `(string[]) => Promise<void>` | `Promise.all(ensurePlayUnit)`，预取入口 |
| `loadAllRichPlays()` | `() => Promise<number>` | 全量加载（探针 / 单测 / 内容审计专用），返回注册条数。**UI 代码禁止调用**——smoke 测试要断言 src 的 .vue 里没有它 |
| `getCharPlay(char)` | 同步，签名不变 | 行为不变：富层只查**已注册**的 RICH → generated → emergency，永不 null。加载前调用拿到的是 generated 版——所以 UI 必须走下面的异步口或先 preload |
| `getCharPlayAsync(char)` | `(string) => Promise<CharPlay>` | 先 `ensurePlayUnit(unitOf(char))`（char→unit 查 CHAR_INDEX，字表外的字跳过加载）再返回 `getCharPlay(char)`。**CharPlayStage 一律走这个口** |
| `peekRichPlay(char)` | 同步 | 查已注册缓存，未加载返回 null（给 char-intro 用，见 §2.5） |
| `countRichPlays()` / `listRichPlays()` / `hasRichPlay()` | 同步 | 口径 = **已注册条数**（诚实口径，加载多少报多少） |
| `richPlayCoverage()` | 同步 | 返回 `{ probe, plays: 已注册, manifest: RICH_PLAY_MANIFEST }`——探针拿 manifest 数字先看，再 loadAll 实测对账 |

确定性纪律不变：同一个字归一出的关卡与加载顺序无关（归一种子只依赖 char + template）。

### 2.4 消费端接线与预取策略

- **CharPlayStage.vue**：`watch(() => props.char)` 里 `play = await getCharPlayAsync(char)`；
  等待期沿用现有进场骨架/空态（单片 gzip 前 ≈ 5–8KB，本地应 <100ms）；
  竞态防护：异步返回时 char 已切走就丢弃结果。skip/complete 事件不变。
- **CharDetailView.vue**：进入详情、以及左右翻字时，把当前字的 `ensurePlayUnit(unit)`
  与既有 `loadUnitDetails(unit)` 并进同一个 `Promise.all`（预取点已经存在，加一项）。
- **LearnView（单元列表）**：点开某单元时 `preloadPlayUnits([该单元])`——孩子点第一个字时片已在缓存。
- **char-intro.js**：断开 `import { getRichPlay } from './char-play-rich.js'`，
  改 `import { peekRichPlay } from './char-play.js'`。`partsOf()` 查不到（片未加载）返回 null
  → intro 自动落 radical / word 模式，**永不空场**，同步纯函数纪律不破。
  想保证 parts 模式命中的调用方自己先 await ensurePlayUnit。

### 2.5 接线清单（谁动谁打勾）

| 文件 | 改动 |
|---|---|
| `scripts/gen-char-play-rich.mjs` | 落盘改为 play-rich/ 分片 + index.js；阈值与标记见 §1.2 |
| `src/data/char-play.js` | 删顶层 rich import；实现 §2.3 API；`RICH_PLAY_PROBE` 改从 index.js re-export |
| `src/data/char-play-rich.js` | **删除** |
| `src/data/char-intro.js` | 改用 `peekRichPlay`（§2.4） |
| `src/components/CharPlayStage.vue` | 改走 `getCharPlayAsync` + 竞态防护 |
| `src/views/CharDetailView.vue` / LearnView | 预取接线（§2.4） |
| `scripts/gen-char-play.mjs` | RICH 源探测表里 `src/data/char-play-rich.js` 改为 `src/data/play-rich/` 目录 |
| `scripts/test-char-play.mjs` | 开头 `await loadAllRichPlays()` 再跑全库断言 |
| `scripts/test-play-rich-guard.mjs` | 负例仍应拒绝落盘；生成物路径断言改到 play-rich/ |
| `scripts/check-bundle.mjs` | 新增两条断言（§2.6） |
| `scripts/check-round17.mjs` | 见 §2.7，只允许一行加载适配 |

### 2.6 check:bundle 增强（防「拆了又被人缝回去」）

1. dist 里存在 ≥50 个 play-rich 单元 chunk（按 manifest.units 数对账）；
2. 入口同步闭包 **以及 CharDetailView 所在 chunk 的同步闭包** 不含 rich 指纹串
   （拿 u1 一句 narration 如「只点一个苹果就好」做指纹，比查文件名可靠——改名骗不过）；
3. `ENTRY_JS_BUDGET_KB = 420` 不放宽。

### 2.7 与往轮门禁（H8）的兼容——必须先想清楚再动手

`check-round17.mjs` 的 H2 在 Node 里 `import char-play.js` 后**同步**调
`countRichPlays()` 期望 ≥900。拆包后启动时注册表为空，该探针会读到 0 → H8 崩。

- **主案**：regression-gate 岗把 check-round17 升 **v1.2**：H2 处加一行
  `if (typeof mod.loadAllRichPlays === 'function') await mod.loadAllRichPlays()`。
  阈值（900/720）与其余口径一个字不动，版本变更在验收日志留痕（该文件 v1.0→v1.1 已有升版先例）。
- **备案**（主案被否再用）：char-play.js 顶层 `if (typeof window === 'undefined') await loadAllRichPlays()`
  ——Node 探针环境预热、浏览器零成本。缺点是环境分叉 + 顶层 await，能不用就不用。

### 2.8 ROUND18_H3 可执行标记落点

1. `play-rich/index.js`：`export const RICH_SPLIT_PROBE = 'ROUND18_H3'`（生成器产出）；
2. `char-play.js`：`ensurePlayUnit` 实现处 `export const PLAY_SPLIT_PROBE = 'ROUND18_H3'`。

探针除了扫标记还要验行为（给 spec 岗）：(a) 静态断言 char-play.js / char-intro.js 源码里
不再出现 `from './char-play-rich.js'` 或对分片的静态 import；(b) `getCharPlay('雨')`（未加载）
source 不为 rich、`await getCharPlayAsync('雨')` source 为 rich；(c) build 后跑 §2.6。

---

## 3. H4 · `template.steps` 与剖析步数对齐协议（r18-wp-steps-align 岗）

### 3.1 56 条不一致的完整归类（本岗逐条实测，照单修，不许绕）

| 组 | 母题 | 条数 | 声明 vs 实际 | 修法 |
|---|---|---|---|---|
| A | `div-remainder`、`left-over`×10 | 11 | 2 vs 1 | 改 analyzeEquation：余数除法拆两步（§3.2） |
| B | `ceil-pack`×10、`minibus` | 11 | 3 vs 2 | 同上——余数除法两步 + 既有 `+1` 分句一步 = 3 ✓ |
| C | `mean`×10、`average` | 11 | 2 vs 3 | 改 analyzeEquation：括号内纯连加折叠为一步（§3.3） |
| D | `sum-times`×11、`sum-gap`×10、`sum-diff`、`meet` | 23 | 3 vs 2 | 改母题声明：steps 3→2 + 新增 `tier` 字段保住进阶档（§3.4） |

修完 A–D 一致率应为 **214/214 = 100%**（门槛 ≥90%，留足余量）。

### 3.2 余数除法拆两步（改 analyzeEquation，教学上是真两步）

`a ÷ b = q …… r` 现在合成一步。改为两步：

1. `{ op:'÷', a, b, value:q, expr:'a ÷ b', why:'每 b 一份地分，装满 q 份' }`（商步）
2. `{ kind:'remainder', a, b, quotient:q, remainder:r, value:r, why:'分掉 q 份共 q×b，剩下 r' }`（余步）

`asked` 归属：rhs 问余数（`…… ?`）→ 余步 asked、商步明示；rhs 商余全明文
（minibus/ceil-pack 的 `= full …… extra，full + 1 = ?`）→ 两步都不 asked，
asked 落在后面 `+1` 分句上。盖答案纪律（masked / leaksAnswer）对两步分别生效。

### 3.3 括号内纯连加折叠为一步（改 analyzeEquation，范围收窄到不误伤）

`(x + y + z) ÷ 3` 现在记 2 次加法。规则：**仅当括号内是 ≥3 个操作数的纯 `+` 连串**时
折叠成一步 n 元求和：`{ op:'+', operands:[x,y,z], a:x, b:z, value:和, expr:'x + y + z' }`。

- 范围红线：只折叠**括号内**、只折叠**纯加法**。`a − b − c`（two-step-buy，连花两次钱）
  是真两步，不在括号内也不是纯加，不受影响；`(sum + diff) ÷ 2` 括号内单次加法，折叠无变化。
- 折叠步新增 `operands` 字段；手写剖析函数（word-problem-explains）拿 operands 说话，
  a/b 保留为首尾操作数以兼容旧签名。
- **连带义务**：既有 `mean` / `average` 手写链是按 3 步写的，折叠后变 2 步，
  H5 岗必须同轮改写这两条（第一步「把三天的加起来」用 operands 报全三个数）。

### 3.4 「计算步数」与「难度档」解耦（改 wordProblems.js 数据侧）

D 组的题（和倍/和差/相遇）equation 就是 2 次计算，声明 3 是把「先转换思路」也算了一步——
**声明必须对齐物理事实：steps 3→2**。产品上它们仍是进阶题，所以：

- 母题新增可选字段 `tier: 'one' | 'two' | 'multi'`；D 组 23 条标 `tier: 'multi'`。
- `WORD_PROBLEM_TIERS` 的 match 改为 tier 字段优先、缺省按 steps 推：
  `p.tier === 'multi' || (!p.tier && p.steps >= 3)` 这个形状。
  UI（档位筛选、`question.steps >= 2` 的 chip）行为不变。

### 3.5 红线（H4 探针会盯的）

1. **`steps` 必须仍是字面量声明**。禁止改成 import buildAnalysis 动态求值——
   那是同义反复，探针数「声明与实测一致」就没有意义了。
2. analyzeEquation 的每一步必须对应**一次真实运算**（n 元求和算一次）。
   禁止生造「读题步 / 检查步」凑数；禁止把一次运算拆两步凑数。
3. 禁止纯为凑步数给 equation 加分句——分句必须每句有独立教学语义（minibus 的 `+1` 那种才算）。
4. asked 步盖答案纪律不变：`masked` / `leaksAnswer` 兜底一行不许删。
5. 步数结构必须与随机取值无关（make() 换 seed 步数不变）；现库已满足
   （extra ≥1、n2≠n1 等约束都在），新母题也要守住。探针可多跑几遍 make() 抽查。

### 3.6 ROUND18_H4 落点与探针口径

- `wpAnalysis.js`：`export const ROUND18_H4 = 'wp-steps-aligned'`（可执行）；
- `wordProblems.js`：tier 解耦处 `export const WP_TIER_PROBE = 'ROUND18_H4'`（本地常量，
  别反向 import wpAnalysis——会和 explains 构成循环依赖）。
- 探针实测（给 spec 岗）：遍历 `WORD_PROBLEMS`，
  `buildAnalysis({ ...p.make(), id: p.id }).steps.length === p.steps` 的比例 ≥90%。
  注意实例要手动带 id（View 层就是这么传的，见 WordProblemsView `id: template.id`）。

---

## 4. H5 · 手写剖析续写到 ≥80 的数据协议（r18-wp-explain-80 岗）

### 4.1 现状与口径

`word-problem-explains.js` 登记 50 条（34 条手写母题 + 16 条语义条）；语义条经
`语义-皮肤` 展开后 **214 题已全部命中**。所以「50→80」不能靠补空白（没有空白了），
靠的是**皮肤专属条目**：查表两趟走的规则已经保证「写明的具体 id 赢过语义展开」
（`EXPLAIN_MAP` 先落显式 id、再补组合），这正是留给 R18 的扩展口。

### 4.2 续写协议

- **复用同一文件** `word-problem-explains.js` 续写（简报明说可与 ROUND17_H4 同文件）；
  条目形状不变：`{ id, headline?, caption?, steps: [fn…] }`，steps 函数签名不变
  （新增 `operands` 可用，见 §3.3）。
- 新增 ≥30 条**皮肤专属条**，id 用展开后的具体组合（如 `sum-times-space`、`left-over-bakery`）：
  语义共享条不许出现具体名词（会串皮肤），专属条**可以点名道姓**（火箭、贝壳、面包）——
  这是真实的质量增量，不是凑数。优先覆盖：进阶语义（sum-times/sum-gap/ceil-pack/meet 类）
  × 高频皮肤，孩子最容易卡的组合先吃到专属讲法。
- **步数对齐义务**：每条 steps 数组长度必须等于该母题修完 §3 后的实测步数
  （A/B 组余数题变 2 步、mean 变 2 步、D 组 2 步）。写错长度不会崩
  （applyExplain 按位覆盖、写不上的留公式句），但 `handwritten` 招牌挂不上，等于白写。
- **既有条目复检**：§3 改了步序的母题（div-remainder、left-over、ceil-pack、minibus、
  mean、average）的旧手写链必须同轮改写对齐，这 6 组是 H4→H5 的硬交接。
- 泄题红线不变：asked 步的文案不许出现得数（leaksAnswer 是兜底不是许可）。

### 4.3 数字线与 ROUND18_H5 落点

- `EXPLAIN_COUNT ≥ 80`（登记条数，文件内去重 id）；去重中文讲解句 ≥ 200
  （headline + caption + 各 step 产出句合并去重；探针可运行时跑
  `buildAnalysis({...make(), id})` 收集 `hand === true` 的 why 句）。
- 落点：`export const ROUND18_H5 = 'handwritten-explain-80'`（可执行，和 ROUND17_H4 并存，
  历轮标记不许删）。

---

## 5. 全局红线（所有岗）

1. **禁止注释骗标**：`ROUND18_H2/H3/H4/H5` 全部落在可执行代码（export 常量 / 实参字符串），
   探针剥注释后再扫。
2. **禁止整包同步 import rich**：§2.2 之后任何 `.vue` / src 模块静态 import
   `play-rich/uN.js` 或已删除的 `char-play-rich.js` 都算破约；`loadAllRichPlays()`
   只许出现在 scripts / 探针 / 单测里。check:bundle 指纹断言是最后一道闸。
3. **禁止同义反复凑对齐**：steps 改动态求值、analyzeEquation 生造非计算步、
   equation 无语义拆分句，三者都算 H4 作弊。
4. 往轮探针只许做 §2.7 主案那一行加载适配，阈值与判定口径一个字不动，升版留痕。
5. 数据层保持同步纯函数、永不 null；异步只发生在「分片加载」这一层，
   加载失败退 generated/emergency，孩子永远有关可玩。

## 6. 各岗交接顺序建议

H3（生成器落盘改分片）先行 → H2（seed 续写，跑新生成器）随后；
H4（analyzeEquation + tier 解耦）先行 → H5（手写链续写 + 旧链复检）随后；
regression-gate 岗最后做 check-round17 v1.2 适配与 check:bundle 增强的合并验证。
