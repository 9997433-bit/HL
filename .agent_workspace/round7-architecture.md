> Model slug: claude-fable-5（Round 7 子代理 #1 · `cursor/r7-arch-contracts-9f67`）

# Round 7 · 全面超越终验架构契约

> 基线：`cursor/openmoji-integration-9f67` @ `46759f3`（Round 6 闭合 `check:round6` 7/7；
> `check:round7` 基线 **0/7** 全红——H1–H7 全部待交付；`check:android` 已 26/26）。
> 性质：**只定数据契约与 API 边界，不含实现**。功能由子代理 #4–#9 按本契约落地，
> #3/#10 按第 11 节的门禁映射验收。
> 关联：`ROUND7-BRIEF.md`、`ROUND7-ACCEPTANCE.md`、`scripts/check-round7.mjs`、
> `round6-architecture.md`、`literacy-architecture.md`、`math-architecture.md`

---

## 0. 总原则（对 Round 7 全部交付生效）

1. **探针即契约**。`scripts/check-round7.mjs` 已合入基线（`46759f3`），固定 7 项输出。
   本文档所有路径、导出名、正则关键词以该探针**逐行**能匹配为准，禁止另起路径
   再回头改探针。特别注意两个「负向断言」：
   - H2 要求 `ListenGameView.vue` **不再出现** `shuffle(list.filter` 这一取样写法；
   - H7 要求 `GLOBAL-SUMMARY-REPORT.md` 任何表格行里**一个 ❌ 都不能剩**。
2. **内容脚本化**。字源扩到 200+、形近邻居 1820 字全量，一律
   「seed 真源 + 生成器 + check:data 校验」，生成物头部标注出处、禁止手改。
   范式沿用 `apps/literacy-app/scripts/gen-char-corpus.mjs`（seed → 索引 + 数据 +
   derived-cache；生成期工具经 `TOOLS_DIR` 临时装，不进 dependencies）。
3. **两层加载与预算红线**。识字入口 JS（含同步依赖）**< 420 KB**
   （`apps/literacy-app/scripts/check-bundle.mjs` 的 `ENTRY_JS_BUDGET_KB`）。
   本轮新增的重资产全部走懒加载：tesseract 引擎只许在 OCR 视图 chunk 内
   动态 `import()`；`etymology-extended.js` 只许被 `etymology.js`（字源 chunk）引用；
   `similar-chars.js` 是轻表可进主包，但**只存字符不存释义**。
4. **纯数据红线**。被 Node 门禁 `await import` 的文件本轮新增两个：
   `data/etymology-index.js`（H3 直接 import）与 `data/similar-chars.js`
   （H2 读文本）。它们与其依赖禁止引 Vue / 浏览器 API，识字侧 data 文件一律相对路径。
5. **不退化**。`check:round4/5/5b/6` 读取的文件只加字段不删字段；每个分支合并前
   `npm test` 全绿 + `npm run check:round6` 7/7 是底线。数值红线：FSRS 参数、
   `starsToUnlock`、单元 60% 解锁、母题阈值 185/40、字库 1800、绘本 130、古诗 20 不动。
6. **存储向后兼容**。识字主存档 `happy-literacy:v1` 的 `migrate()` 不加顶层字段；
   aurora 主题只是 `settings.theme` 的新合法值（老档默认 `sunny` 不受影响）。
   数学 `mathquest/settings` 新增 `theme` 字段必须在 `sanitize()` 里给白名单 + 默认值，
   老档缺字段时落回 `cosmos`。
7. **并发纪律**。多个子代理共用一台 VM：**不要切 `/workspace` 共享树的分支**，
   一律 `git worktree`（`/tmp/wt-<task>`）；改动面收敛到新文件 + 第 10 节点名的热点行。
8. **全程离线**。tesseract 的 worker / wasm / 语言包全部本地化进 `public/`，
   运行时零第三方域名请求（合规项 C-1 / L-O2 不许被 OCR 破掉）。

---

## 1. 契约一 · Tesseract.js 拍照识字 v1（H1，所有者 #4）

### 1.1 探针拆解与路径锁定

H1 = `ocrRoute && ocrMod`，探针认多个路径，本契约**锁定全部从严命中**：

| 探针条件 | 锁定交付 |
|---|---|
| 路由源码含 `/camera\|ocr\|photo/i` 或存在 `views/CameraOcrView.vue` | 静态路由 `path: '/camera'`、`name: 'camera-ocr'`，`component: () => import('@/views/CameraOcrView.vue')`，`meta: { title: '拍照识字', emoji: '📷' }` |
| 存在 `utils/ocr.js` 或 `composables/useOcr.js` 或 literacy `package.json` 含 tesseract | `apps/literacy-app/src/composables/useOcr.js` + `apps/literacy-app/package.json` dependencies 加 `tesseract.js`（npm 解析最新稳定版，这是 Round 6「不新增运行时依赖」原则在本轮的**唯一豁免**，Brief L-M10 点名） |

路由写静态路径（不带 `:`），`scripts/smoke.mjs` 的 `findStaticRoute` 才扫得到
（同 Round 6 §3.2 的教训）；smoke 的 `ROUTES` 加一行 `['拍照识字', '/#/camera']`。

### 1.2 离线资产：`public/ocr/` 目录

```text
apps/literacy-app/public/ocr/
  worker.min.js                ← copy 自 node_modules/tesseract.js/dist/
  tesseract-core-simd.wasm.js  ← copy 自 node_modules/tesseract.js-core/
  tesseract-core.wasm.js       ← 无 SIMD 的兜底核
  chi_sim.traineddata.gz       ← tessdata_fast 简体中文语言包（~11 MB）
```

- 引入脚本 `apps/literacy-app/scripts/fetch-ocr-assets.mjs`：从 node_modules 复制
  worker/core，从 tessdata_fast 固定 URL 下载语言包并**校验 pin 住的 SHA-256**；
  只在开发机跑一次，产物提交进仓库，CI / smoke / build 永不联网
  （同 `gen-char-corpus.mjs` 的 `TOOLS_DIR` 生成期联网惯例）。
- `useOcr.js` 里 `createWorker` 必须显式传
  `{ workerPath, corePath, langPath }` 三个本地路径（相对 `import.meta.env.BASE_URL`），
  否则 tesseract.js 默认打 CDN，直接违反 C-1。

### 1.3 `composables/useOcr.js` 导出面（冻结）

```js
export function useOcr() {
  return {
    status,      // ref<'idle'|'loading-engine'|'ready'|'recognizing'|'done'|'error'>
    progress,    // ref<number> 0–1，引擎下载/识别两个阶段共用，UI 画进度条
    engineReady, // computed<boolean>
    recognize(source),   // ImageBitmap|HTMLCanvasElement|Blob → Promise<Candidate[]>
    dispose()    // 视图 onUnmounted 时终结 worker，防内存驻留
  }
}
// Candidate = { char: '日', confidence: 0.93, known: true }
// known = CHARACTER_MAP.has(char)（data/characters.js），只有 known 的字才给讲解入口
```

- tesseract 引擎**只在这里动态 `import('tesseract.js')`**；`CameraOcrView.vue`
  本身是路由级懒加载 chunk，两层懒加载叠加保证主包零增量
  （`check:bundle` 的入口预算与指纹检查会守住）。
- 识别参数：`tessedit_char_whitelist` 设为字表全部 1820 字
  （运行时从 `CHARACTER_MAP` 的键拼出来，**不要**再造一份字符串常量）——
  白名单同时解决「识别出超纲字没法讲解」和「乱码候选」两个问题；
  页面分割模式用 `SINGLE_LINE`，孩子拍的多半是一行字。

### 1.4 视图 pipeline 与降级链（探测顺序即降级顺序）

| tier | 判定 | 行为 |
|---|---|---|
| `camera` | `navigator.mediaDevices.getUserMedia({ video })` 成功 | 取景 → canvas 截帧 → 预处理（灰度 + 阈值二值化 + 缩放到长边 ≤1024）→ `recognize()` |
| `upload` | 摄像头拒权 / 无摄像头（无头 smoke 环境必走这档） | `<input type="file" accept="image/*" capture="environment">`，同一条预处理 + 识别链 |
| `manual` | 引擎加载失败（如语言包被清缓存后离线） | 提示手动进 `/learn` 查字，本会话记住降档（sessionStorage），不反复弹权限框 |

- 结果区：每个 `known` 候选渲染为卡片，含大字 + 拼音（读 `CHARACTER_MAP`），
  「学这个字」跳 `/learn/:char`（讲解走既有 `loadCharacter()` 懒加载链）；
  朗读走 `utils/audio.js` 的 `speak()`。识别完成的播报进 `[aria-live]` 区。
- 记账红线：拍照识字**只做入口不做测评**，不写 `progress.recordAnswer`
  （没有作答行为，喂 FSRS 会污染排程）；`/learn/:char` 内学完自然记账。
- 影像数据只存内存 canvas/blob，不落盘、不上传、不进 localStorage。
- smoke 交互段：无头 Chrome 无摄像头，断言 upload 档表单可见、无控制台报错即可，
  不要求真识别（引擎 11 MB 不进冒烟热路径）。

### 1.5 SW 预缓存策略（与契约七共享，先在这里定死）

`scripts/vite-offline-plugin.mjs` 现状是「dist 全量进 install-time precache」。
OCR 资产 ~11 MB 全塞 install 清单会拖慢首次进站的后台带宽（Lighthouse 移动模拟下
影响 Perf），策略改为**两段式**：

- 插件加选项 `runtimeCachePrefixes: ['ocr/']`：命中前缀的文件不进
  `PRECACHE_URLS`，改注入第二个占位 `/* __RUNTIME_MANIFEST__ */`；
- `apps/literacy-app/public/sw.js` 对 runtime 清单内的 URL 走
  **cache-first + 首次取回落盘**（复用现有 `caches.match → fetch` 结构，加一个
  `RUNTIME_CACHE_URLS` 集合判断即可），版本号沿用 `__PRECACHE_VERSION__`；
- UI 契约：`CameraOcrView` 首次加载引擎时明示「正在下载识字引擎（约 11 MB，
  只下这一次）」；此后断网可用。**断网且从未下载过**落到 `manual` 档，不是 bug。
- math-app 的 sw.js 不受影响（无 runtime 前缀时插件行为与现状逐字节一致——
  这是 #9 改插件时的回归底线）。

---

## 2. 契约二 · 听音/测验形近干扰项（H2，所有者 #5）

### 2.1 探针拆解

H2 = 关键词命中 && 旧写法消失：

- `ListenGameView.vue` + `CharDetailView.vue` + `data/similar-chars.js` 拼起来的文本
  命中 `/similar|shapeLike|confusable|形近|NEIGHBORS|distractorPool/i`；
- `ListenGameView.vue` **不得再含** `shuffle(list.filter`（现第 141 行
  `const distractors = shuffle(list.filter((c) => c.char !== pick.char))...` 必须被替换）。

### 2.2 数据文件：`apps/literacy-app/src/data/similar-chars.js`（新，生成物）

由 `apps/literacy-app/scripts/gen-similar-chars.mjs` 生成，真源两份：

| 真源 | 内容 |
|---|---|
| `scripts/data/similar-seed.txt` | 手工核过的形近组，一行一组：`己已巳`、`未末`、`土士`、`人入`、`日目`、`大太犬`……组内互为最高优先级邻居 |
| `src/data/char-index.js` 的行字段 | 兜底特征：同部首、笔画差 ≤1、同声旁（从 7 段 seed 的组词/字形派生缓存里取）按加权分排序 |

导出面（冻结，探针关键词 `NEIGHBORS` 与 `distractorPool` 都在这里出现）：

```js
/** 汉字 → 形近邻居（按相似度降序，含来源分级）。生成物，勿手改。 */
export const SIMILAR_NEIGHBORS = { 日: '目田白旦甲', 己: '已巳', /* … 1820 行 */ }

/**
 * 取 n 个干扰项（形近优先）。
 * @param opts.pool      限定候选池（如「已学字」）；池内不足时自动放宽到全字表
 * @param opts.avoidHomophone  true 时剔除与目标去声调同音的字（听音场景必开）
 */
export function distractorPool(char, n, opts = {}) { /* 纯函数，无随机 */ }
```

- 值用**紧凑字符串**而非数组（1820 行，主包体积敏感；`check:bundle` 入口预算
  已逼近 420 KB，这份表实测应 < 25 KB）；
- `distractorPool` 返回**确定性排序**的候选，取样时的洗牌由调用方做——
  这样单测能断言「日 的第一邻居是 目」。

### 2.3 消费方接线（两处，改法锁定)

**`views/ListenGameView.vue`**（听音识字，第 130–146 行 `nextRound()`）：

```js
// 旧：const distractors = shuffle(list.filter((c) => c.char !== pick.char)).slice(0, OPTIONS - 1)
// 新：形近优先 + 听音场景必剔同音；池仍是「已学优先」的 list，规则对孩子不变
const near = distractorPool(pick.char, OPTIONS - 1, {
  pool: list.map((c) => c.char),
  avoidHomophone: true      // 听音题干扰项若与答案同音则题目无解，这是硬红线
})
const distractors = near.map((ch) => CHARACTER_MAP.get(ch))
```

**`views/CharDetailView.vue`**（第 264–277 行）：`distractors()` 保留
「排除同释义」的既有闸门（`exclude` 参数），内部取字改为
`distractorPool(decoded.value, count, { pool: 同单元优先 })`；
「听一听」步骤（`buildListen`）加 `avoidHomophone: true`，
「考一考」步骤（`buildQuiz`）不剔同音（考的是字义不是字音）。

### 2.4 校验（`scripts/check-data.mjs` 追加，#5 完成）

| 规则 | 说明 |
|---|---|
| 邻居表与字表逐字对齐 | 1820 个键一个不缺，邻居全部 ∈ `CHARACTER_MAP`，不含自身 |
| 每字邻居 ≥ 4 | seed 组 + 部首/笔画兜底必须凑齐，凑不齐生成器直接 FAIL |
| seed 组内字全在字表 | 防手滑写了超纲字 |
| `avoidHomophone` 语义单测 | `test-srs.mjs` 同级新增 `test-similar.mjs`：断言「日」的听音干扰不含任何 rì 同音字 |

---

## 3. 契约三 · 字源动画 65 → 200+（H3，所有者 #5）

### 3.1 探针与两摞语料布局

H3 探针 `await import('…/data/etymology-index.js')` 后断言
`ETYMOLOGY_CHARS.length >= 200`（`ETYMOLOGY_CHARS` 现为**字符串**，保持字符串——
string 的 `.length` 探针照样认，且主包最省）。布局仿绘本「两摞书」（Round 6 §2）：

| 文件 | 角色 |
|---|---|
| `src/data/etymology.js` | 手写 65 字（`PICTURES` + `COMPOUNDS`）原地保留，是叙事基准；文件尾改为 `ETYMOLOGY = [...PICTURES, ...COMPOUNDS, ...EXTENDED_ETYMOLOGY]` |
| `src/data/etymology-extended.js` | 批量扩充 135+ 字（`EXTENDED_ETYMOLOGY`），生成物勿手改 |
| `src/data/etymology-index.js` | 轻索引（字符串），生成器同步重写；`hasEtymology()` / `TOTAL_ETYMOLOGY` 导出面冻结 |
| `scripts/gen-etymology.mjs` | 生成器：seed → extended + index |
| `scripts/data/etymology-seed.mjs` | 扩充字的 seed（见 3.2） |

导出面冻结：`ETYMOLOGY` / `ETYMOLOGY_MAP` / `getEtymology` / `kindOf` /
`TOTAL_ETYMOLOGY` / `ETYMOLOGY_KINDS` / `KIND_MAP`（`check-data.mjs` 与
`EtymologyView.vue` / `CharDetailView.vue` 双处消费，不得改名）。
`etymology.js` 仍只进字源 chunk；`etymology-index.js` 仍是主包唯一全量层。

### 3.2 扩充策略：会意/形声可脚本化，象形不硬凑

单字 schema 与现状完全一致（`{ c, kind, origin, evolve, sketch? | parts }`），
下游 `EtymologyStage.vue` / `utils/etymologySketch.js` 零改动。批量上量走
**parts 路线**（会意 `hui` / 形声 `xing`）：

```js
// etymology-seed.mjs 单行：字|类|形旁=含义|声旁=读音链|一句话起源
{ c: '洋', kind: 'xing', semantic: ['氵', '和水有关'], phonetic: ['羊', 'yáng'] }
```

生成器由模板产出 `origin` / `evolve` / `parts`（模板句式沿用现有 65 字的口吻，
如「带三点水的字，多半和水有关」「『氵』管意思，『羊』管读音，念 yáng」），
拼音从 `char-index.js` 行里取，禁止另标。**象形/指事**需要 `sketch` 手画小图，
不强行批量——`check-data.mjs` 第 367 行「每类 ≥5」照旧即可，200+ 的大头
落在形声（这也符合汉字学事实：八成汉字是形声字）。

### 3.3 红线与门禁

- 每个扩充字必须 ∈ `CHARACTER_MAP`（check-data 第 323 行既有规则）——
  「写一写」终点帧靠离线笔顺数据，收超纲字断网开天窗；
- `parts` 里的零件字形 `g` 若是可检字（如「羊」），**建议**也在字表内
  （点零件跳详情的既有交互才不断链），偏旁类零件（「氵」「犭」）豁免；
- `ETYMOLOGY_CHARS === ETYMOLOGY.map(e => e.c).join('')`（check-data 第 362 行）
  由生成器保证；
- `check-data.mjs` 第 318 行阈值 `>= 50` 升到 `>= 200`，由 #5 同分支完成，禁回调；
- smoke 已有 `/#/etymology` 与两个单字样例路由，#5 在 `ROUTES` 补一条
  扩充字样例（如 `字源 洋（形声·扩充）`），防「生成了但渲染炸」。

---

## 4. 契约四 · 年龄档 L1–L5 全模块联动（H4，所有者 #6）

### 4.1 探针拆解

H4 数以下六个视图文件中命中 `/ageBand|AGE_BAND/i` 的个数，**≥ 5 过关**；
基线只有 `ArithmeticView.vue`（1/5）。本契约锁定**六个全接**，留一格冗余：

```text
apps/math-app/src/modules/number-sense/NumberSenseView.vue
apps/math-app/src/modules/geometry/GeometryView.vue
apps/math-app/src/modules/logic/LogicView.vue
apps/math-app/src/modules/word-problems/WordProblemsView.vue
apps/math-app/src/modules/sudoku/SudokuView.vue
apps/math-app/src/modules/arithmetic/ArithmeticView.vue   ← 已接，冻结
```

### 4.2 接线范式（照抄 ArithmeticView，不建全局调度层）

年龄档真源不变：`stores/settings.js` 的 `AGE_BANDS`（L1–L5）与
`settings.ageBand`（家长中心 `ParentView.vue` 已有切换 UI，勿动）。
每个视图开头声明一张 `X_BY_AGE_BAND` 映射表 + 用它算**默认起步档**：

```js
const SIZE_BY_AGE_BAND = { L1: 4, L2: 4, L3: 6, L4: 9, L5: 9 }
const sizeKey = ref(SIZE_BY_AGE_BAND[settings.ageBand] ?? 4)
```

**语义红线：ageBand 只决定「进来时停在哪一档」，孩子在玩法页内仍可自由切档**
（settings.js 第 9–11 行注释是这条的既有出处）。不做玩法锁定、不做中局跳档
（切档只影响下一局 `newRound()`）。

### 4.3 各模块映射表（锁定值，#6 按表落地）

| 模块 | 旋钮（现有 ref） | L1 | L2 | L3 | L4 | L5 |
|---|---|---|---|---|---|---|
| number-sense | 出题数域上限（点数/比大小取值域） | 5 | 10 | 20 | 20 | 20 |
| arithmetic | `level`（已冻结） | 10 | 10 | 20 | 100 | 100 |
| geometry | `scope`（'2d'\|'3d'\|'all'） | 2d | 2d | all | 3d | 3d |
| logic | 题型池（3.1 的生成器家族） | ABAB 图案 | 图案+分类 | +数列(等差/递减) | +倍数/差递增 | 全家族+交替 |
| sudoku | `sizeKey` × `difficulty` | 4×easy | 4×easy | 6×normal | 9×normal | 9×hard |
| word-problems | `tier`（`WORD_PROBLEM_TIERS` 的 id） | 'one' | 'one' | 'two' | 'all' | 'multi' |

- number-sense 的取值域常量与 `compareOnly` 模式共存：`/compare` 专线复用同一映射；
- logic 的题型池分档即 4.2 范式的对象值换成「生成器函数数组」；
- 单测/门禁：`apps/math-app/scripts/check-content.mjs` 不动（它测的是母题生成，
  与视图无关）；回归靠 `npm run smoke`——六个路由本来就在 `ROUTES` 清单里，
  接线炸了冒烟直接红。

### 4.4 不许做的事

- 不改 `curriculum.js` 的技能 DAG 与 `isKnownSkill` 白名单；
- 不动 `starsToUnlock` / `progress.isModuleUnlocked`（年龄档≠解锁）；
- 不新增持久化键——`ageBand` 已在 `mathquest/settings` 里，够用；
- `recordAnswer` 的 skill 归属照旧走 `data/skill-mapping.js`，
  不因档位而改记账目标。

---

## 5. 契约五 · 逻辑配对/迷宫小游戏 v1（H5，所有者 #7）

### 5.1 探针拆解与路由锁定

H5 = math 路由源码命中 `/pair|memory|maze|配对|迷宫/i` **且**
`modules/logic/LogicView.vue` 存在（后者已满足）。锁定两条新路由（都写
`component: () => import(...)` 动态形态，与全 router 一致）：

| path | name | view | meta.title |
|---|---|---|---|
| `/logic/pairs` | `logic-pairs` | `modules/logic/PairsGameView.vue` | 星际配对 |
| `/logic/maze` | `logic-maze` | `modules/logic/MazeGameView.vue` | 星门迷宫 |

`LogicView.vue`（规律环带大厅）顶部加两张入口卡；`modules/home/HomeView.vue`
不加新星球（这两款是 logic 星球的**子玩法**，不是新地图节点）。

### 5.2 玩法与记账契约

- **配对**（PairsGameView）：Canvas 翻牌记忆配对，牌面是「数量点阵 ↔ 数字」
  「算式 ↔ 得数」两套（按 ageBand 选套，见 §4.3 logic 行）；
  记账 `progress.recordAnswer('logic', ok, { skill: 'classify', stars, xp })`；
- **迷宫**（MazeGameView）：Canvas 网格迷宫，路口给条件题（「走能被 2 整除的门」），
  记账 `progress.recordAnswer('logic', ok, { skill: 'maze-condition', … })`——
  两个 skill 都是 `curriculum.js` 白名单里的既有节点（第 43/44 行），
  `isKnownSkill` 不需要扩；
- 记在 `'logic'` 模块名下（不进 `SIDE_MODULES` 也不开新模块 id），
  掌握度并进规律环带，成就墙不会冒裸 id——与 Round 6 topics `record` 字段同一动机；
- 随机数一律 `@/utils/random` 的种子化流（`reseed` 后同 seed 同迷宫），
  禁 `Math.random()`。

### 5.3 Canvas 工程红线（Brief 点名 reduced-motion 降级）

- 尺寸按 `devicePixelRatio` 缩放，`ResizeObserver` 跟随容器；
- **键盘可玩**：方向键走格/选牌，Enter 确认——math `scripts/smoke.mjs` 的交互段
  用键盘驱动断言（仿识字 maze 段写法），做不到过不了冒烟；
- `utils/motion.js#reducedMotion()` 为真：翻牌/走格动画退化为直切状态帧，
  GSAP 补间全部跳过，Canvas 里不做逐帧位移插值；
- 状态播报进 `.sr-only` 的 `[aria-live]` 区（Canvas 本身对读屏是黑箱，
  旁路播报是唯一通道）；`document.hidden` 时暂停计时；
- 反馈走 `composables/useFeedback.js` + `utils/sound.js`，不自建音效。

### 5.4 回归

math `scripts/smoke.mjs` 的 `ROUTES` 加两行（`['星际配对', '/#/logic/pairs']`、
`['星门迷宫', '/#/logic/maze']`）+ 各一段键盘交互断言。

---

## 6. 契约六 · 第 4 主题 aurora + 四主题对比度（H6，所有者 #8）

### 6.1 探针拆解

H6 把 literacy `stores/settings.js` + math `stores/settings.js` +
`shared/styles/design-tokens.css` 三份源码拼起来，要求命中 `/aurora/i`
**且** `/theme.*aurora|aurora.*theme/i`。三处都要真出现 aurora 字样。

### 6.2 令牌层：`shared/styles/design-tokens.css` §8 追加

追加 `:root[data-theme='aurora']` 块——**极光夜空**：深青底、青绿→紫的极光渐变、
`color-scheme: dark`。语义令牌一个都不能少（组件只引语义层，缺一个就会
穿帮到 sunny 兜底），照 sunny 块逐项映射：

```text
--bg-page --bg-page-solid --bg-blob-a/b/c
--surface --surface-strong --surface-sunken --surface-border
--text-strong --text --text-invert
--text-soft            ← 红线：按本主题最亮底色算对比 ≥ 4.5:1（care 块注释同款算法）
--brand --brand-strong --brand-soft
--accent --accent-soft --info --danger --success --star
--grid-line --stroke-ink --stroke-hint
--focus-ring --overlay-scrim
--shadow-sm/md/lg/press --shadow-glow
color-scheme: dark
```

新原始色进 §1 色板（如 `--aurora-teal-*`），组件层**零硬编码**
（`npm run check:tokens:wiring` 回归）。night 主题已是深色系，
aurora 与 night 必须拉开辨识度（偏青绿 vs night 的偏蓝紫）。

### 6.3 识字侧接线（3 → 4 主题）

| 文件 | 改动 |
|---|---|
| `src/stores/settings.js` 第 17–21 行 | `THEMES` 追加 `{ id: 'aurora', name: '极光夜空', emoji: '🌌', desc: '…' }` |
| `src/stores/progress.js` 第 791 行 | `cycleTheme` 的 `order` 数组补 `'aurora'`（尾插，保持 sunny 起点） |
| 其余 | **零改动**：`applyAppearance()` 写 `<html data-theme>` 是通用的，`toggleEyeCare` 语义（sunny↔care）不动，`reset()` 默认 `sunny` 不动，存档结构不动 |

### 6.4 数学侧接线（cosmos 固定 → 双主题可切）

math 现状是 `index.html` 写死 `data-theme="cosmos"`。改动锁定：

| 文件 | 改动 |
|---|---|
| `src/stores/settings.js` | `DEFAULTS` 加 `theme: 'cosmos'`；`sanitize()` 白名单 `['cosmos', 'aurora']`，越界落回 cosmos；顺手导出 `export const THEMES = [...]`（探针命中点之一） |
| `src/App.vue`（或 main.js） | 挂载时 + `watch(() => settings.theme)` 写 `document.documentElement.dataset.theme`（index.html 的静态值退化为 FOUC 兜底，保留） |
| `modules/parent/ParentView.vue` | 家长中心加主题切换段（按钮组，`aria-pressed`，仿 AGE_BANDS 段写法） |

### 6.5 四主题对比度走查（C-5，axe + 手动留档）

- `scripts/axe-states.mjs` 第 22 行 `THEMES = ['sunny', 'care', 'night']`
  加 `'aurora'`——状态级扫描自动变成 **4 主题 × 全部交互态**，
  critical/serious 仍必须为 0（`test:a11y` / `test:acceptance` 双入口）；
- 手动走查留档 `.agent_workspace/round7-theme-contrast.md`：四主题 × 关键界面
  （首页 / 单字详情 / 听音 / 家长中心 + math 地图 / 算术 / 家长中心）的
  正文、软文字、按钮文字实测对比度（工具值），逐格 ≥ 4.5:1（大字 ≥ 3:1），
  这是 GLOBAL-SUMMARY §3.3「L/M-A3 对比度」终验列的证据源。

---

## 7. 契约七 · Lighthouse Perf ≥ 90 双 App（G6，所有者 #9）

### 7.1 门禁与测法（已存在，不新造）

`npm run test:acceptance`（`scripts/acceptance.sh`）：构建 ≤ 60s、首屏 JS gzip
< 250 KB、Lighthouse **Perf / A11y / BP ≥ 0.90**（`MIN_LH_*` 默认值即 Round 7
阈值，不要调 env 放水）、axe 双扫描。测法固定：gzip 静态服 + headless Chrome
移动模拟 + simulate 节流——与 GLOBAL-SUMMARY 附录的采集方法一致，
终验数字只认这条链的输出。

### 7.2 三板斧（Brief 点名「首屏拆包 / SW 预缓存策略优化」）

1. **首屏拆包守住**：识字入口 < 420 KB（`check:bundle`）。本轮主包唯一合法增量是
   `similar-chars.js`（§2.2，< 25 KB）；tesseract、etymology-extended、
   任何新视图都必须验证在懒加载 chunk 里（check:bundle 的 `collectSync`
   同步依赖遍历会抓现行）。math 侧无索引层机制，靠 acceptance.sh 的
   gzip 阈值 + 路由级 `import()` 纪律。
2. **SW 预缓存两段式**：§1.5 的 `runtimeCachePrefixes` 落地——install 清单
   不再背 OCR 的 11 MB；SW 注册本就在 `window load` 之后（双 App main.js 已如此），
   保持。预缓存清单排序把入口 chunk / CSS 排前（弱网下半途关页也先缓存到关键资源）。
3. **首帧关键路径**：`index.html` 预算内不加阻塞资源；字体全系统栈（零 webfont）
   保持；若 LCP 卡在首页大元素，允许给首页首屏元素加 `content-visibility` 或
   预渲染骨架，但**禁止**为分数去删 aria 结构或懒加载首屏文本。

### 7.3 记录

双 App 的 P/A/BP 三分 + 首屏 gzip + zip 体积回填
`.agent_workspace/acceptance-log-round7.md` §Perf 与 GLOBAL-SUMMARY §3.2；
达不到 90 的项必须附 Lighthouse audit id 级归因，不许只贴分数。

---

## 8. 契约八 · GLOBAL-SUMMARY-REPORT 全表 ✅ + 证据包索引（H7，所有者 #10）

### 8.1 探针拆解（当前 3 行 ❌，全在 §3.3）

H7 = 文件 > 500 字符 **且** 正则 `\|[^|\n]*❌[^|\n]*\|` 零命中。
基线的 3 个 ❌ 在 §3.3 表「首轮实测」列（LH A11y `87 / 93 ❌`、
axe critical `1 / 3 ❌`、axe serious `58 / 5 ❌`）。改写规则：

- **历史数字不删改**，但表格单元格里的 ❌ 一律改写为文字
  （如 `87 / 93（未达标，Round 3 快照）`）——历史留痕挪出探针命中面；
- 全部 `⬜ 待实测` 用 Round 7 终验链（§7.1 + `npm test` + `test:round3`）的
  实测值回填为 ✅；测不了的项（如 30min 内存）写明豁免理由与替代证据，
  不许留空、不许写 ❌。

### 8.2 报告结构增量（在现有 7 节之上）

| 新增节 | 内容 | 证据源 |
|---|---|---|
| 洪恩对标全表 | 逐模块 ✅ 对照（识字 L-M1…M10 / 数学 M-M1…M12 / 共同 C-1…C-6） | #2 的 `.agent_workspace/round7-hongen-module-audit.md`（沿革：round4/5/5b/6 同名审计） |
| 证据包索引 | 两 zip 的大小 + SHA-256、acceptance-log round2–7 清单、`check:round4/5/5b/6/7` 输出快照、四主题对比度留档（§6.5）、浏览器矩阵（§8.3） | `ls -l dist/*.zip && sha256sum dist/*.zip`、`.agent_workspace/` 各 log |
| 三轮→七轮演进总览 | §2 表格从 Round 3 截止扩到 Round 7 | 各轮 acceptance-log |

### 8.3 全浏览器矩阵（C-6，走查表 + 探针）

留档 `.agent_workspace/round7-browser-matrix.md`：

- **自动探针**：`scripts/browser-matrix.mjs`（新）——对 dist 起静态服，
  按可用性依次跑 Chrome（既有 puppeteer 链）与系统里检测到的 Firefox / WebKit
  内核，逐路由收集控制台错误；探不到的内核**如实标 SKIP**，禁止伪造 PASS；
- **能力矩阵手动列**：SpeechRecognition（Chrome 有 / Firefox 无 → 跟读评测落
  record 档）、MediaRecorder、getUserMedia、SW、hash 路由——每格写
  「实测/推断 + 降级路径」，降级路径必须指到真实代码
  （如 `composables/useSpeechEval.js` 的三档链）。

### 8.4 门禁链（`ROUND7-ACCEPTANCE.md` G1–G6）

```text
npm test → npm run check:round6 (7/7) → npm run check:round7 (7/7)
  → npm run test:round3 → npm run build:all → npm run sync:android + check:android (26/26)
  → Lighthouse 双 App P/A/BP ≥ 90（test:acceptance）
```

全链输出回填 `.agent_workspace/acceptance-log-round7.md`（模板由 #3 定）。

---

## 9. 契约九 · Android 重同步（G5，所有者 #10 收尾）

- 基线 `check:android` 已 26/26（Capacitor 工程、manifest、图标、权限全绿），
  本轮是**重跑不重建**：全部功能分支合并后
  `npm run sync:android`（= build + `cap copy` + `cap sync` × 双 App）
  再 `npm run check:android`，26/26 不退化；
- `webDir: dist` 意味着 §1.2 的 `public/ocr/` 会整体进 APK assets——
  识字 APK 体积 +≈11 MB 是预期内的，写进 acceptance-log 的体积表并解释来源；
  **不要**为省体积把 OCR 资产从 dist 排除（Android 端离线 OCR 恰恰是卖点）;
- Android 壳内 `getUserMedia` 走 WebView 权限链，`CameraOcrView` 的 upload
  降级档（§1.4）是壳内的保底路径，不需要为壳单写原生插件（v1 边界）。

---

## 10. 文件所有权与冲突矩阵

| 热点文件 | 触碰者 | 隔离规则 |
|---|---|---|
| `literacy src/router/index.js` | #4（`/camera` 一条） | 纯追加区段 |
| `literacy scripts/smoke.mjs` | #4（camera 路由 + upload 档断言）、#5（字源样例路由行） | 各自追加，不改既有段 |
| `literacy package.json` | #4 独占（tesseract.js 依赖） | — |
| `literacy views/ListenGameView.vue` | #5 独占（第 130–146 行取样段） | 只换干扰项来源，不动皮肤/播报逻辑 |
| `literacy views/CharDetailView.vue` | #5 独占（`distractors()` 一处） | 状态机流程不动 |
| `literacy src/data/etymology.js` | #5（文件尾合并行） | PICTURES/COMPOUNDS 手写体不动 |
| `literacy scripts/check-data.mjs` | #5（字源阈值 200 + 形近规则段） | 既有规则只加不改 |
| `literacy stores/settings.js`、`stores/progress.js` | #8（THEMES + cycleTheme order） | 各一行级追加 |
| `shared/styles/design-tokens.css` | #8 独占（§1 新色板 + §8 aurora 块） | 既有主题块一个值都不动 |
| `scripts/axe-states.mjs` | #8（THEMES 加 aurora） | — |
| `scripts/vite-offline-plugin.mjs`、`literacy public/sw.js` | #9（两段式缓存；#4 依赖其行为但不改它） | 无 runtime 前缀时行为与现状逐字节等价 |
| `math src/router/index.js` | #7（两条 logic 子路由） | 纯追加 |
| `math src/stores/settings.js` | #8 独占（theme 字段）；#6 只读 `ageBand` 不写此文件 | — |
| `math 六个玩法视图` | #6（AGE_BAND 映射表 + 默认档行）；LogicView 另有 #7 加两张入口卡 | **LogicView 是 #6/#7 唯一交叉点**：#6 只动 script 顶部映射表，#7 只动 template 入口区，先合者在前 |
| `math modules/parent/ParentView.vue` | #8（主题段）；#6 不碰（AGE_BANDS 段已存在） | — |
| `math scripts/smoke.mjs` | #7（两行路由 + 交互段） | 纯追加 |
| `.agent_workspace/GLOBAL-SUMMARY-REPORT.md` | #10 独占 | #2 的审计只写自己的 audit 文件 |

新建文件（零冲突）：literacy `views/CameraOcrView.vue`、`composables/useOcr.js`、
`public/ocr/*`、`scripts/fetch-ocr-assets.mjs`、`data/similar-chars.js`、
`scripts/gen-similar-chars.mjs`、`scripts/data/similar-seed.txt`、
`data/etymology-extended.js`、`scripts/gen-etymology.mjs`、
`scripts/data/etymology-seed.mjs`、`scripts/test-similar.mjs`；
math `modules/logic/PairsGameView.vue`、`modules/logic/MazeGameView.vue`；
根 `scripts/browser-matrix.mjs`；`.agent_workspace/round7-theme-contrast.md`、
`round7-browser-matrix.md`、`round7-hongen-module-audit.md`、`acceptance-log-round7.md`。

合并顺序建议：**#4 / #5 / #6 / #7 四条功能线互不依赖可乱序**（LogicView 交叉点
按上表规则先到先得）→ #8 主题（跨双 App，晚合少 rebase）→ #9 Perf（要在全量
功能上量）→ #10 报告 + Android + 打包收尾。#3 的 acceptance 模板随时可合。

---

## 11. 契约 → 门禁映射

| 契约 | check:round7 探针 | 所有者 | 回归红线 |
|---|---|---|---|
| §1 拍照识字 | H1：`/camera` 路由 + `useOcr.js`/tesseract 依赖 | #4 | check:bundle 420 KB；零 CDN；smoke upload 档 |
| §2 形近干扰 | H2：关键词命中 + `shuffle(list.filter` 消失 | #5 | 听音干扰剔同音；check:data 邻居规则 |
| §3 字源 200+ | H3：`ETYMOLOGY_CHARS.length ≥ 200` | #5 | check-data 索引对齐 + 阈值 200；纯数据可 Node import |
| §4 年龄档联动 | H4：6 个视图 ≥5 命中 `ageBand` | #6 | 只改默认档不锁玩法；starsToUnlock 不动 |
| §5 逻辑小游戏 | H5：router 命中 pair/maze + LogicView 存在 | #7 | 键盘可玩；reduced-motion 直切帧；seed 可复现 |
| §6 aurora 主题 | H6：三文件命中 aurora + theme 关联 | #8 | 语义令牌全量映射；axe-states 4 主题 0 serious |
| §7 Lighthouse | （G6，非 H 探针）test:acceptance P/A/BP ≥ 90 | #9 | 无 runtime 前缀时 SW 插件行为不变 |
| §8 全局报告 | H7：>500 字符且表格零 ❌ | #10 | 历史数字不删改；实测不伪造 |
| §9 Android | （G5）sync:android + check:android 26/26 | #10 | APK 体积增量入 log |

---

## 12. 明确不做（Out of scope）

- OCR 不做手写体识别、不做拍整页课文的版面分析（v1 = 印刷体单行）；
  不接任何云端 OCR/ASR/TTS——全链路离线是底线；
- 不因 OCR 引入通用「插件层」或原生 Capacitor 插件；
- 形近干扰不做逐字形嵌入向量（seed 组 + 部首/笔画特征够 v1 用），
  不在运行时算相似度（全部生成期算好）；
- 字源不为凑数硬造象形小图；不动 `EtymologyStage.vue` 的动画协议；
- 年龄档不做自动升档推荐（那是 adaptive.js 的地盘，本轮不碰）；
- 主题不做「跟随系统深色」自动切换；不改 night/care/sunny/cosmos 既有值；
- 不调低 acceptance.sh 的任何 `MIN_LH_*` / 体积 / 构建时长阈值；
- 不改识字主存档 `happy-literacy:v1` 顶层结构与 FSRS 参数。
