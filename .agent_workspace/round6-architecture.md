> Model slug: claude-fable-5（Round 6 子代理 #1 · `cursor/r6-arch-contracts-9f67`）

# Round 6 · 体量对齐架构契约

> 基线：`cursor/openmoji-integration-9f67` @ `51308da`（Round 5 12/12 · Round 5B 6/6，
> `check:round6` 基线 **2/7**：H2 越界=0 与 H6 母题 214 已绿，其余四项待交付）。
> 性质：**只定数据契约与 API 边界，不含实现**。功能由子代理 #4–#9 按本契约落地，
> #3/#10 按第 8 节的门禁映射验收。
> 关联：`ROUND6-BRIEF.md`、`ROUND6-ACCEPTANCE.md`、`scripts/check-round6.mjs`、
> `round5b-play-architecture.md`、`literacy-architecture.md`、`math-architecture.md`

---

## 0. 总原则（对 Round 6 全部交付生效）

1. **探针即契约**。`scripts/check-round6.mjs` 已加固为**固定 7 项输出、无 PENDING**：
   文件存在但导入失败、视图存在但没接路由，一律 FAIL。本文档所有路径与导出名
   以该探针能匹配为准，禁止另起路径再回头改探针。
2. **内容脚本化**。上量的内容（字、绘本、诗、母题）一律「seed 真源 + 生成器 +
   自动校验」，生成物头部标注出处、禁止手改。已有范式：
   `apps/literacy-app/scripts/gen-char-corpus.mjs`（字库）、
   `apps/literacy-app/scripts/gen-books.mjs`（绘本，本轮新增）、
   `apps/math-app/src/data/wordProblems.js` 的语义模板 × 场景皮肤（母题）。
3. **两层加载是红线**。识字侧任何全量数据都拆「轻索引进主包 + 正文按需 import()」
   两层。首屏预算由 `apps/literacy-app/scripts/check-bundle.mjs` 守住：
   入口 JS（含同步依赖）**< 420 KB**（`ENTRY_JS_BUDGET_KB`），课文包零同步加载、
   字义指纹零泄漏。扩量子代理合并前必须本地跑
   `npm run build && npm run check:bundle`（literacy-app 内）。
4. **纯数据红线**。被 Node 门禁 `await import` 的数据文件
   （`data/games.js`、`data/books.js`、`data/poems.js`、`data/wordProblems.js`、
   `data/characters.js` 及其依赖）禁止引 Vue、浏览器 API；`@/` 别名仅在
   `scripts/alias-loader.mjs` 能解析的范围内使用，识字侧 data 文件一律相对路径。
5. **不破坏既有门禁**。`check:round5`（12/12）与 `check:round5b`（6/6）读取的文件
   **只加字段不删字段**；`npm test` 全绿是每个分支的自查底线。
6. **存储向后兼容**。识字主存档 `happy-literacy:v1` 的 `migrate()` 不再加顶层字段，
   本轮新增持久化（诗歌进度、跟读降级档位等）一律独立 localStorage 键。
7. **并发纪律**。多个子代理共用一台 VM 的 `/workspace` 工作树：**不要切共享树的
   分支**，用 `git worktree` 或只在自己分支的文件集内落笔；改动面尽量收敛到
   新文件 + 本契约第 7 节点名的热点行。

---

## 1. 契约一 · 字库 1000 → 1800（H1，所有者 #4）

### 1.1 真源与行格式

唯一真源是 `apps/literacy-app/scripts/data/char-seed.txt`（现 1000 字 / 58 单元）。

```text
@unit u59|单元名|🧧|var(--seed-mango)|一句话描述        ← 单元头，5 段
汉字|拼音|部首id或-|卡片emoji|释义|组词1,组词2|例句      ← 7 段生成行
```

- 4 段行是 u1–u33 老单元的遗留（课文仍在手写的 `chars/uN.js`），**新增字禁用**；
  +800 个新字全部写 7 段行，由生成器产出课文包。
- 部首写 `-` 表示自动派生；组词、例句可用 `文本=拼音` 覆写标注器。
- 同一单元「要么全 7 段、要么全 4 段」，混写生成器直接中止。

### 1.2 生成流水线

```text
char-seed.txt ──gen-char-corpus.mjs──▶ src/data/char-index.js        （轻索引，进主包）
                                     ├▶ src/data/chars/uN.js          （课文包，懒加载）
                                     └▶ shared/data/common-hanzi.json （monorepo 共享基线）
派生缓存：scripts/data/derived-cache.json（笔画/部首/拼音）
```

新字必须先跑 `node scripts/gen-char-corpus.mjs --refresh`（需
`TOOLS_DIR` 指到临时装的 cnchar / cnchar-radical / pinyin-pro）刷新缓存，
之后日常生成零外部依赖。生成器内置校验（全部 FAIL 即中止）：

| 规则 | 出处（gen-char-corpus.mjs） |
|---|---|
| 全表无重复字 | `entries.has(row.char)` |
| 笔画能在 hanzi-writer-data 里数出来 | `strokeCounter()` |
| 部首 id 能落到 `src/data/radicals.js`（映射表 `scripts/data/radical-glyphs.json`） | `radicalIdOf()` + `getRadical()` |
| 拼音解得出 1–5 声调；卡片 emoji 非空 | `toneOf()` |
| 释义以句号结尾；组词 ≥2 且含本字；例句含本字、以句末标点结尾 | detail 校验段 |
| 每单元 ≥5 字 | `unit.rows.length < 5` |
| 多音字：组词/例句读音与字表登记音不一致时按字表掰回并告警 | `reconcile()` |

### 1.3 手工接线（生成器不覆盖的两处）

`apps/literacy-app/src/data/characters.js`：

1. `UNITS` 数组追加新单元行（id/name/emoji/color/desc 与 seed 的 `@unit` 头一致）；
2. `UNIT_LOADERS` 显式 import() 映射追加 `u59: () => import('./chars/u59.js')` ——
   这是懒加载的接线点，写显式映射而非 `import.meta.glob` 是既有决策，勿改。

另外每个新单元要在 `apps/literacy-app/src/data/unit-stories.js` 的 `STORIES`
补一句剧情（≤30 字）；漏了不会红灯（`unitStory()` 有 `unit.desc` 兜底），
但兜底文案是给过渡期用的，交付时应写满。

### 1.4 门禁与预算

- `check:round6` H1 读 `TOTAL_CHARACTERS ≥ 1800`；
- app 级 `npm run check:data`（`apps/literacy-app/scripts/check-data.mjs`）核对
  索引/课文包一一对应、`shared/data/common-hanzi.json` 基线不丢字不改拼音；
- `npm run check:bundle`：每单元切出 `chars-uN-*.js` 块、首屏零课文包、
  字义指纹零泄漏、入口 < 420 KB。**索引层是首屏唯一全量层**，1800 行索引
  估算比现状多 ~50 KB，预算内但已逼近——禁止往索引行加第 8 个字段；
  真要超预算，调整 `ENTRY_JS_BUDGET_KB` 须走 #3 验收线，不得私改。
- 笔顺数据由 `npm run gen:hanzi`（predev/prebuild 自动跑）从 hanzi-writer-data
  同步，新字无需手工处理。

---

## 2. 契约二 · 绘本 30 → 130（H2，所有者 #5）

### 2.1 两摞书 + 轻索引的文件布局

| 文件 | 角色 |
|---|---|
| `apps/literacy-app/src/data/books/core.js` | 手写 30 本（`CORE_BOOKS`），注音逐句校过，是语感基准 |
| `apps/literacy-app/src/data/books/extended.js` | 批量扩充 100+ 本（`EXTENDED_BOOKS`），生成物勿手改 |
| `apps/literacy-app/src/data/books.js` | 汇总层：`BOOKS = [...core, ...extended]` 按 level 排序；`BOOK_MAP` / `getBook` / `charsInBook` / `verifyBookCoverage` 导出面**冻结**（H2 探针直接调用） |
| `apps/literacy-app/src/data/book-index.js` | 轻索引（书目 id 等），生成物 |
| `apps/literacy-app/scripts/gen-books.mjs` | 生成器：seed → extended.js + book-index.js |
| `apps/literacy-app/scripts/data/book-seed-l1.mjs` … `book-seed-l6.mjs` | 六个分级的书目 seed |
| `apps/literacy-app/scripts/data/book-pinyin.mjs` | 注音层（算出来的拼音，越界字先在这里暴露） |

**主包消费方改读轻索引**：`stores/progress.js`（`booksFinished` 计数）、
`views/HomeView.vue`、`views/ParentView.vue` 现在 `import { BOOKS } from '@/data/books.js'`，
130 本正文会跟着进主包——这三处必须改引 `book-index.js`。
`BooksView.vue` / `BookReadView.vue` 是路由级懒加载 chunk，继续读 `books.js`。
`src/main.js` 的 dev 自检用的是动态 `import('./data/books.js')`，不进 prod 主包，保持。

### 2.2 单本 schema（冻结，两摞完全一致）

```js
{
  id: 'bx17',            // 手写本保留 bN，扩充本用 bxN，全库唯一
  title, pinyin,         // 书名 + 书名拼音
  level: 3,              // 1–6：分级 = 句长与情节复杂度，不是新字数量
  levelName,             // 「第 3 级 · …」
  cover, palette,        // 封面 emoji + 两色渐变
  summary,               // 一句话简介
  newChars: ['字', …],   // 本书想突出的字（可为空数组，不做覆盖判定）
  pages: [{ emoji, text, p }]   // p 的音节 token 与 text 的汉字一一对应
}
```

### 2.3 覆盖规则（红线）

- 正文只允许 `characters.js` 的 `CHARACTER_MAP` 已收录汉字 + `books.js` 顶部
  `PUNCTUATION` 白名单；`verifyBookCoverage()` 返回 `[{ book, missing }]`，
  必须为空数组（H2 第二项探针）。
- **依赖顺序**：扩充书目若用到 1000 字之外、1800 字之内的新字，则 #5 依赖 #4
  先合。建议扩充正文只用现有 1000 字（新字放 `newChars` 展示位也不行——
  `charsInBook` 扫的是正文），把两个分支彻底解耦。
- app 级 `check:data` 书目规则同步扩展：id 唯一、≥3 个分级、每级 ≥3 本、
  每本 ≥5 页、每页 emoji/text/p 齐全、meta（title/pinyin/cover/palette/summary/levelName）齐全。
  30 这个旧阈值升到 130，由 #5 在 `apps/literacy-app/scripts/check-data.mjs` 内完成。

---

## 3. 契约三 · 古诗 20 首 + 跟读评测 v1（H3/H4，所有者 #6）

### 3.1 数据文件

| 文件 | 角色 |
|---|---|
| `apps/literacy-app/src/data/poems.js` | 唯一真源：`export const POEMS = [...]`（H3 探针也认 `poetry.js`/default 导出，本契约**锁定 poems.js + 具名 POEMS 数组**） |
| `apps/literacy-app/src/data/poem-index.js` | 轻索引（id/title/emoji），首页/进度计数用；正文只进诗歌视图 chunk |

单首 schema（对齐 `idioms.js` 的「认读不书写」策略——诗中超纲字只认读、
不进 FSRS，注释講意思）：

```js
{
  id: 'jing-ye-si',
  title: '静夜思', author: '李白', dynasty: '唐',
  emoji: '🌙', palette: ['#…', '#…'],
  theme: '思乡',                       // 选填，书架分组用
  lines: [{ text: '床前明月光', p: 'chuáng qián míng yuè guāng' }, …],
  words: [{ w: '霜', m: '秋夜地上白白的冰粒' }, …],   // 难字注释
  read: '离家的人看见月亮，就想起了家。'              // 读后一句话
}
```

**点字规则**（与绘本 pages 同规）：`p` 的音节 token 数与 `text` 的汉字数
一一对应，点第 i 个字读第 i 个音节；朗读走 `utils/audio.js` 的
`speak()`（SpeechSynthesis），嗓音可用性由 `composables/useVoiceStatus.js` 探测。

### 3.2 路由（smoke 的 `findStaticRoute` 只认不带 `:` 的静态路径，务必留静态入口）

| path | name | view |
|---|---|---|
| `/poems` | `poems` | `views/PoemsView.vue`（书架列表） |
| `/poems/:id` | `poem` | `views/PoemReadView.vue`（朗读 + 点字 + 拼音） |
| `/follow-read` | `follow-read` | `views/FollowReadView.vue`（跟读评测；诗篇用 `?poem=id` query 传入，缺省取最近读的一首） |

三条都必须写成 `component: () => import('@/views/Xxx.vue')`——H4 探针用
`dynamicView()` 正则精确匹配这个写法。`scripts/smoke.mjs` 里
`ROUND6_H3_SMOKE` / `ROUND6_H4_SMOKE` 探测桩已就位（#10 已合入）：
静态路由一出现就自动进浏览器回归，无需再改 smoke。

### 3.3 跟读评测 pipeline：`composables/useSpeechEval.js`

H4 探针认四个路径（`useSpeechEval.js` / `useFollowRead.js` / `utils/speechEval.js` /
`utils/speechRecognition.js`），本契约**锁定 `composables/useSpeechEval.js`**，
且该文件（含 FollowReadView 合并源码）必须同时出现
`SpeechRecognition` 与 `MediaRecorder|getUserMedia|recordedBlob|audioUrl`
关键词——即降级链的上下两档都要真实现，缺一档探针即红。

三档降级（探测顺序即降级顺序）：

| tier | 判定 | 行为 |
|---|---|---|
| `asr` | `window.SpeechRecognition ?? webkitSpeechRecognition` 可用且启动成功 | 逐句识别，与原文做**去声调逐字比对**（多音/轻声容错），出 0–3 星 |
| `record` | 无 ASR（或 ASR 启动失败，如离线的 Chrome），但 `navigator.mediaDevices.getUserMedia` + `MediaRecorder` 可用 | 录音→`recordedBlob`→`URL.createObjectURL` 回放自评，不打分，完成即发星 |
| `listen` | 都不可用 / 麦克风拒权 | TTS 领读 + 孩子口头跟读 + 「我读完了」按钮 |

导出面（冻结）：

```js
export function useSpeechEval() {
  return {
    tier,        // ref<'asr'|'record'|'listen'>
    status,      // ref<'idle'|'listening'|'recording'|'scoring'|'done'|'error'>
    start(text), // 开始一句跟读；ASR 启动失败时内部自动降档再试
    stop(),
    result,      // ref<{ stars: 0|1|2|3, matched: string[] } | null>（仅 asr 档）
    playback,    // ref<string|null>（record 档的 audioUrl）
    reset()
  }
}
```

红线与 a11y（smoke 会断言）：

- 只用浏览器内建能力，**不接任何云端 ASR/TTS**；权限拒绝后本会话记住降档
  （sessionStorage 即可），不反复弹权限框；
- 页面文案含「跟读/录音」、按钮含「开始/录音/重试/播放」之一、结果播报进
  `[aria-live]` 区——这三条是 `smoke.mjs` H4 交互段的硬断言；
- 录音数据只存内存 blob，不落盘不上传；
- 诗歌阅读/跟读进度用独立键 `happy-literacy:poems:v1`，不动主存档。

---

## 4. 契约四 · 识字小游戏 +2（H5，所有者 #7）

### 4.1 注册表契约（H5 已按此强校验）

`apps/literacy-app/src/data/games.js` 追加两项，锁定为：

| id | name | route | skill | view |
|---|---|---|---|---|
| `spell` | 拼字工坊 | `/games/spell` | `compose` | `SpellGameView` |
| `catch` | 接字雨 | `/games/catch` | `listen-fast` | `CatchGameView` |

H5 探针逐项校验（不含 listen，≥5 款）：`id/name/route/skill/view` 全为非空字符串、
id 与 route 全库唯一、route 在 `apps/literacy-app/src/router/index.js` 里以
`component: () => import('@/views/<view>.vue')` **精确接线**、视图文件真实存在。
注册表保持零依赖纯数据（原则 4）。

### 4.2 玩法接线契约

- **出题池**：一律走 `composables/useCharPool.js`——只出已学字，不够开局时
  退回课程最前排并挂说明（与 listen/maze/memory/spot 同一套规则，勿自建池）；
- **记账**：答题结果走 `progress.recordAnswer(char, correct)`（喂 FSRS + 星星），
  与 maze/memory/spot 一致；不写 `state.listen`（那是听音识字的专属战绩）；
- **反馈**：`composables/useFeedback.js`（Round 5B §2 薄绑定）+ `utils/sfx.js`，
  连对走 `correct(el, { streak })` 节奏音；
- **大厅**：`views/GamesView.vue` 的内联 `GAMES` 数组各加一张卡
  （`trains` 能力标签 + `howToPlay` 一句话玩法）。内联数组与 `data/games.js`
  的合并欠账（R5B §5.2）**不在本轮强制**，但新卡的文案字段先按注册表字段名写，
  给下一轮合并铺路；
- **回归**：`scripts/smoke.mjs` 的 routes 清单加两行 + 各加一段键盘可玩的
  交互断言（仿 maze「只用键盘走到目标字」段落的写法）；
- 红线：reduced-motion 读 `<html data-motion>`；结果播报进 aria-live；
  整局键盘可达（smoke 交互段用键盘驱动，做不到就过不了）。

---

## 5. 契约五 · 应用题母题 ≥185（H6，所有者 #8 —— **已达标，契约转守门**）

基线 `51308da` 已合入 214 个母题（语义模板 18 × 场景皮肤 10 + 手写 34），
H6 绿灯。本节冻结现状、约定扩展协议，防后来者退化。

### 5.1 结构与导出面（冻结）

`apps/math-app/src/data/wordProblems.js`：

```text
CRAFTED（手写母题）+ SEMANTIC_TEMPLATES × SCENE_SKINS（= SKINNED，id 为「语义-皮肤」）
  ⇒ WORD_PROBLEMS ⇒ WORD_PROBLEM_COUNT（H6 直接读这个值）
```

导出名 `WORD_PROBLEMS` / `WORD_PROBLEM_COUNT` / `WORD_PROBLEM_TIERS` /
`problemsOfTier` / `WORD_PROBLEM_TAGS` / `SCENE_SKINS` / `SEMANTIC_TEMPLATES`
被 `scripts/check-round6.mjs` 与 `apps/math-app/scripts/check-content.mjs`
双处消费，**不得改名/删除**。

三种对象形状：

```js
// 皮肤：只答「在哪里、数什么、动词怎么说」，不带数学结构
{ id, scene, emoji, item, unit, verb, away, place, holder }
// 语义模板：只管数学结构与取值域
{ id, skill /* 必须过 curriculum.js#isKnownSkill */, tag, steps, make(skin) }
// make() 返回（手写母题与皮肤化母题完全一致，下游不区分来源）
{ text, equation, answer /* 恒为正整数 */, unit, hint, visual?: { icon, groups, strike? } }
```

随机数一律走 `@/utils/random` 的种子化 mulberry32 流：`reseed(seed)` 后逐字可复现，
家长报告的错题回放依赖这一点，禁止 `Math.random()`。

### 5.2 阈值（check:content 已同步上调，禁止回调）

| 探针 | 阈值 | 出处 |
|---|---|---|
| 母题总数 | ≥ 185 | `check-round6.mjs` H6；`check-content.mjs` `MIN_TEMPLATES = 185` |
| 场景种类 | ≥ 40 | `check-content.mjs` `MIN_SCENES = 40` |
| 生成健壮性 | 每母题 2000 次生成：无负数/NaN、选项不重复、id 唯一 | `check-content.mjs` 主循环 |

扩展协议：优先加**新语义模板**（一条 × 10 皮肤 = 整排 +10）；新皮肤须保证
`verb/away/place/holder` 能无语病地嵌进全部既有模板；`steps`（1/2/≥3）分档
自动进 `WORD_PROBLEM_TIERS`，无需改壳。

---

## 6. 契约六 · 数学地图叙事 + 专题入口（M-M12/M-M4/M-M11，所有者 #9）

### 6.1 文案真源与玩法真源分层

| 文件 | 角色 |
|---|---|
| `apps/math-app/src/data/modules.js` | **玩法接线真源**（id/route/node/starsToUnlock/skills…）。被 `check:round5` 读取，只加不删；既有 `story/lockedStory/unlockLine` 三字段保留 |
| `apps/math-app/src/data/unit-stories.js` | **章节叙事真源**（新文件，与识字侧 `unit-stories.js` 命名对齐）：`CHAPTERS` 以模块 id 为键 |
| `apps/math-app/src/data/topics.js` | **专题入口注册表**（新文件） |

`CHAPTERS` 单章 schema：

```js
{
  chapterNo: 2, chapterName: '第二章 · 恒星燃料',
  story,        // 已解锁：到了那儿干什么
  lockedStory,  // 未解锁：为什么现在去不了
  unlockHint,   // 怎样才能进去 —— 说清做什么攒星，不是只报价格
  goal,         // 学到什么算通关（家长看得懂的一句）
  unlockLine    // 刚解锁那一下的过场台词，只播一次
}
```

冲突消解规则：视图取文案先查 `CHAPTERS[id]`，缺字段回落 `modules.js` 同名字段
——两份都在时以 `unit-stories.js` 为准，`modules.js` 的三条自此冻结不再更新。

### 6.2 专题入口（比较 / 速算 / 生活应用）

`TOPICS` 单项 schema：

```js
{
  id: 'sprint', name: '速算冲刺', route: '/sprint', emoji: '⚡',
  record: 'arithmetic',   // 答题记账并进哪颗星球的模块名下，不另开统计
  tagline, blurb, skills
}
```

- 三条专线锁定：`compare`（比大小擂台，`/compare` 路由已有，复用
  `NumberSenseView` 玩法壳 `props: { mode: 'compare' }`）、`sprint`（速算冲刺，
  **新路由 `/sprint`**，复用 `modules/arithmetic/ArithmeticView.vue` 口算闯关壳的
  限时模式）、`life`（生活应用，指向既有 `/word-problems`）；
- `record` 字段是记账契约：专题复用星球玩法壳，掌握度并进对应星球，
  防止成就墙冒出对不上号的裸 id（同 `SIDE_MODULES` 的设计动机）；
- **三处入口读同一份表**：`modules/home/HomeView.vue` 专题区、
  `modules/progress/ProgressView.vue` 专题行、星球视图内部的专题条。

### 6.3 解锁过渡与当前关呼吸

- 解锁判定唯一真源不变：`progress.isModuleUnlocked(id)` 按 `starsToUnlock`，
  **数值一颗星都不许动**；解锁瞬间一次性信号沿用 `progress.takeUnlock()`；
- 过渡动画 GSAP ≤1.2s，`utils/motion.js#reducedMotion()` 为真时跳过动画、
  直接切状态并用 `.sr-only` aria-live 播报 `unlockLine`；
- 当前关呼吸：HomeView 推荐星球的 `.breathe` 光晕已有，保持
  「reduced-motion 退化为常亮描边」的既有降级（HomeView 样式段注释已写明）；
- 运行时验收：`npm run check:map-narrative`（`scripts/check-map-narrative.mjs`
  用 Puppeteer 验灰显、剧情渲染、过场只演一次），合并前必须过。

### 6.4 识字侧同轮联动

识字 `apps/literacy-app/src/data/unit-stories.js` 已覆盖 u1–u58 并带兜底
（`unitStory()` 缺剧情时用 `unit.desc` 顶上）；#4 的新单元剧情补写规则见 §1.3。
解锁文案由 `unitTeaser()` / `unitCheer()` 模板生成，60% 解锁规则不动。

---

## 7. 文件所有权与冲突矩阵

| 热点文件 | 触碰者 | 隔离规则 |
|---|---|---|
| `literacy src/router/index.js` | #6（诗歌 3 条路由）、#7（2 条游戏路由） | 都是纯追加各自区段；先合者在前，后合者 rebase 成本≈0 |
| `literacy scripts/smoke.mjs` | #7（游戏交互段） | H3/H4 探测桩已由 #10 埋好（路由出现即自动生效），#6 无需改 smoke |
| `literacy src/data/characters.js` | #4 独占 | UNITS + UNIT_LOADERS 纯追加 |
| `literacy src/data/unit-stories.js` | #4（新单元剧情行） | STORIES 对象纯追加 |
| `literacy stores/progress.js`、`views/HomeView.vue`、`views/ParentView.vue` | #5（books.js → book-index.js 改引用） | 只改 import 与计数来源，不动其余逻辑；#6 诗歌进度用独立键不碰 progress |
| `literacy scripts/check-data.mjs` | #5（书目阈值 30→130 与两摞规则） | 字表阈值是下限（≥500），#4 无需改 |
| `literacy src/data/games.js`、`views/GamesView.vue` | #7 独占 | 注册表纯追加 |
| `math src/data/modules.js` | #9 | 只加不删（check:round5 红线） |
| `math src/router/index.js`、`modules/home/HomeView.vue`、`modules/arithmetic/ArithmeticView.vue`、`modules/progress/ProgressView.vue` | #9 独占本轮 | — |
| `math src/data/wordProblems.js`、`scripts/check-content.mjs` | 已由 #8 合入（`569105a`/`51308da`），本轮冻结 | 后续只按 §5.2 扩展协议动 |

新建文件（零冲突）：`literacy data/poems.js`、`data/poem-index.js`、
`data/books/core.js`、`data/books/extended.js`、`data/book-index.js`、
`views/PoemsView.vue`、`views/PoemReadView.vue`、`views/FollowReadView.vue`、
`views/SpellGameView.vue`、`views/CatchGameView.vue`、
`composables/useSpeechEval.js`、`scripts/gen-books.mjs`、`scripts/data/book-seed-l*.mjs`、
`scripts/data/book-pinyin.mjs`；`math data/unit-stories.js`、`data/topics.js`。

合并顺序建议：**#4 字库 → #5 绘本 → #6 诗/跟读 → #7 游戏 → #9 地图 → #3/#10 验收回填**。
#5 若按 §2.3 建议只用现有 1000 字，则 #4/#5 可乱序。

---

## 8. 契约 → 门禁映射

| 契约 | check:round6 探针 | 所有者 | 回归红线 |
|---|---|---|---|
| §1 字库 1800 | H1：`TOTAL_CHARACTERS ≥ 1800` | #4 | `check:data` + `check:bundle`（420 KB / 零课文包泄漏） |
| §2 绘本 130 | H2×2：`BOOKS.length ≥ 130` + `verifyBookCoverage()` 空 | #5 | 主包消费方改读 book-index；`check:data` 书目规则 |
| §3 古诗 20 | H3：`poems.js` 的 `POEMS ≥ 20` | #6 | 点字 token 对齐；静态路由 `/poems` |
| §3 跟读评测 | H4：静态路由 `/follow-read` + `useSpeechEval.js` 含 ASR/录音双关键词 + smoke `ROUND6_H4_SMOKE` 交互过 | #6 | 无云端依赖；aria-live 播报 |
| §4 小游戏 ≥5 | H5：注册表 5 字段 + id/route 唯一 + 路由精确接线 | #7 | `check:round5` H6 旧字段保留；smoke 键盘可玩 |
| §5 母题 ≥185 | H6：`WORD_PROBLEM_COUNT ≥ 185`（现 214） | 已达标 | `check:content` 阈值 185/40 禁回调 |
| §6 地图叙事 | （无 round6 探针）`check:map-narrative` 运行时验收 | #9 | `starsToUnlock` 不动；modules.js 只加不删 |

全部合并后的门禁链（`ROUND6-ACCEPTANCE.md` G1–G5）：
`npm test` → `npm run check:round5` → `npm run check:round5b` →
`npm run check:round6`（7/7）→ `npm run test:round3` → `npm run build:all`（zip 记体积），
并回填 `.agent_workspace/acceptance-log-round6.md`。

---

## 9. 明确不做（Out of scope）

- 不接云端 TTS / ASR / 任何在线内容源——全链路离线可用是底线；
- 不动 FSRS 参数、掌握度阈值、单元 60% 与星球 `starsToUnlock` 解锁数值；
- 不新增 npm 运行时依赖（生成期工具经 `TOOLS_DIR` 临时装，不进仓库 dependencies）；
- 不改识字主存档 `happy-literacy:v1` 顶层结构；
- 古诗不做书写/默写（认读 + 跟读为界，超纲字策略同成语页）；
- 不在本轮强制完成 GamesView 内联数组与 `data/games.js` 的合并欠账（R5B §5.2）；
- 跟读评测不存储、不上传任何录音数据。
