> Model slug: claude-fable-5-thinking-xhigh（Round 8 子代理 #1 · `cursor/r8-arch-contracts-9f67`）

# Round 8 · 深度超越与 A 层终态架构契约

> 基线：`cursor/openmoji-integration-9f67` @ `a8b21b3`（Round 7 闭合：`check:round7` **8/8**、
> `check:round6` **7/7**、`check:android` 26/26；`check:round8` 基线 **1/8**——仅 H8 绿，
> H1–H7 待交付）。
> 性质：**只定数据契约与 API 边界，不含实现**。功能由子代理 #4–#9 按本契约落地，
> #3/#10 按第 9 节的门禁映射验收。
> 关联：`ROUND8-BRIEF.md`、`ROUND8-ACCEPTANCE.md`、`acceptance-log-round8.md`、
> `scripts/check-round8.mjs`、`round7-architecture.md`、`round7-hongen-final-audit.md` §R8。

基线上两个**已经点亮的半格**，交付者别再重做、只须不退化：

- H4 的 `quizWired` 半条件在基线已绿（`CharDetailView.vue` L43 已
  `import { similarDistractors } from '@/utils/distractors.js'`，L274 / L327 已调用）——
  #7 只补精度基准与听音同音闸门；
- H7 的 ❌ 与占位计数在基线已是 0（R7 #10 清过一轮），#10 只须加 Round 8 章节
  并保持零 ❌ 零占位，不需要再考古改写历史表格。

---

## 0. 总原则（对 Round 8 全部交付生效）

1. **探针即契约**。`scripts/check-round8.mjs` 已合入基线（`a8b21b3`），固定 8 项输出。
   本文档所有路径、导出名、正则关键词以该探针**逐行**能匹配为准，禁止另起路径再回头
   改探针（探针加严归 #3，放宽谁都不许）。三个易踩的正则细节先点名：
   - H2 数剧情用 `/\bu(\d+)\s*:/g` 扫 `unit-stories.js` **原始源码**（不剥注释）——
     u59–u99 必须是字面量键，写成循环生成或计算键名探针不认；
   - H5 对 `useSpeechEval.js` / `FollowReadView.vue` / `MascotCompanion.vue` 三文件
     **先剥注释再匹配**（`stripComments`）——`音素/声调/tone/phoneme/companion…reply`
     这些关键词必须出现在**标识符、字符串或模板文本**里，只写在注释里等于没写；
   - H6 从 `acceptance-log-round8.md` 里**首个「识字/数学」字样之后的首个
     `dd / dd / dd` 斜杠三连**取分——回填格式必须是 `97 / 100 / 100` 这种斜杠连写，
     基线模板里 `| 识字 | [待回填] | [待回填] | [待回填] |` 的分列写法拿不到分（见 §6.3）。
2. **内容脚本化**。字源扩到 800 沿用「seed 真源 + 生成器 + check:data 校验」链
   （`gen-etymology.mjs`），生成物头部标注出处、禁止手改。u59–u99 剧情与儿歌是
   **手写创作内容**，不走生成器，但一样要有 check:data 级别的自动化校验兜底
   （键覆盖、用字越界、口径一致）。
3. **两层加载与预算红线**。识字入口 JS（含同步依赖）**< 420 KB**
   （`apps/literacy-app/scripts/check-bundle.mjs` L24 `ENTRY_JS_BUDGET_KB`）；数学首屏
   gzip < 250 KB（`acceptance.sh`）。本轮主包唯一合法增量是 `etymology-index.js`
   的索引字符串（525→800 字 ≈ +0.9 KB）；`songs.js` 只许被 `SongsView.vue`（懒加载
   chunk）引用，`skill-graph.js` 只许被 `SkillGraphView.vue`（懒加载 chunk）与 Node
   门禁引用，OCR 基准图集住在 `scripts/data/` 根本不进构建。
4. **纯数据红线**。被 Node 门禁读取/导入的新文件：`etymology-index.js`（H1 直接
   `await import`）、`songs.js`（H2 读文本）、`skill-graph.js`（H3 读文本 +
   check:content 导入校验）。它们与其依赖禁止引 Vue / 浏览器 API；识字侧 data 文件
   一律相对路径，数学侧 `skill-graph.js` 用相对路径 import `./curriculum.js`
   （Vite 与裸 Node 都能跑，不依赖 alias loader）。
5. **不退化**。每个分支合并前 `npm test` 全绿 + `check:round7` **8/8** +
   `check:round6` **7/7** 是底线（G1–G3）。数值红线：FSRS 参数、`starsToUnlock`、
   单元 60% 解锁、母题阈值 185/40、字库 1820、绘本 130+、古诗 20+、形近组 ≥100、
   年龄档 6 视图接线、aurora 四主题、`/ocr` 三重接线全部不动。`check:round7` H2 的
   反向断言仍然生效：`ListenGameView.vue` 不得出现 `shuffle(list.filter`。
6. **存储向后兼容**。识字主存档 `happy-literacy:v1` 的 `migrate()` **不加顶层字段**
   ——儿歌 v1 因此不记主存档（见 §2.4）；数学 `mathquest/settings` 不新增持久化键，
   技能图谱只**读** `settings.ageBand` 与 `progress.mastery`，不写任何 store。
7. **并发纪律**。多个子代理共用一台 VM：不要切 `/workspace` 共享树的分支，一律
   `git worktree`（`/tmp/wt-r8-<task>`）；改动面收敛到新文件 + 第 8 节点名的热点行。
   注意根 `node_modules` 是 npm workspaces 提升安装，worktree 里跑门禁前先
   `ln -s /workspace/node_modules`（基线 lockfile 未变时）或独立 `npm install`。
8. **全程离线**。儿歌不引入音频资产（旋律走 WebAudio 合成、歌词朗读走既有
   `speak()`）；OCR 精度基准在 Node 里跑本地 tesseract.js（worker/core 取自
   node_modules，语言包取自 `public/ocr/chi_sim.traineddata.gz`），CI 零联网。

---

## 1. 契约一 · 字源动画 525 → 800（H1，所有者 #4）

### 1.1 探针拆解

H1 = `await import('apps/literacy-app/src/data/etymology-index.js')` 后
`Array.from(ETYMOLOGY_CHARS).length >= 800` **且无重复字**。基线 525
（手写 65 + 派生 460），缺口 **275+**。

### 1.2 文件布局与导出面（全部冻结，只改内容不改形状）

| 文件 | 角色 | R8 动作 |
|---|---|---|
| `src/data/etymology.js` | 手写层（`PICTURES`+`COMPOUNDS`=`HANDWRITTEN` 65 字）+ 合并出口 | **零改动** |
| `src/data/etymology-derived.js` | 生成物：`DERIVED`（460 → 735+） | 重新生成 |
| `src/data/etymology-index.js` | 生成物：`ETYMOLOGY_CHARS` / `TOTAL_ETYMOLOGY` / `hasEtymology()` | 重新生成 |
| `scripts/data/etymology-seed.txt` | 真源 seed | **追加 275+ 行** |
| `scripts/gen-etymology.mjs` | 生成器（含 `SEMANTIC` 形旁语义表） | 扩表，派生逻辑不动 |

导出名 `ETYMOLOGY` / `ETYMOLOGY_MAP` / `getEtymology` / `kindOf` / `TOTAL_ETYMOLOGY` /
`ETYMOLOGY_KINDS` / `KIND_MAP` / `HANDWRITTEN` / `DERIVED` 一个不许改——
`check-data.mjs`、`EtymologyView.vue`、`CharDetailView.vue`（经 index）三处消费。
单字 schema 与现状完全一致（`{ c, kind, origin, evolve, sketch? | parts }`），
下游 `EtymologyStage.vue` / `utils/etymologySketch.js` **零改动**。

### 1.3 扩充策略（275+ 字从哪来）

- **主力仍是形声**（seed 四段格式 `xing|汉字|声旁|声旁读音` 不变）。基线 seed 的
  自我约束「声旁必须是能给孩子看的字」在 R8 放宽为：**声旁是单个可显示汉字即可**，
  允许字表外但小学常见的声旁（尧、奚、圭、佥、仑……）；生成器对字表外声旁不产
  「点零件跳详情」链接语义（既有 parts 渲染本就按字符展示，无需改视图）。
  仍然禁止的：声旁是生僻构件（㐬、𢦏、巠 这类打不出/讲不了的），宁缺毋滥。
- **`SEMANTIC` 形旁语义表按需扩**：新收字的部首若不在表内，生成器现行为是 FAIL——
  这是特性不是 bug，#4 补表（`note` 短语 + `line` 成句，口吻对齐现有 32 项），
  禁止绕开表直接硬编码讲法。
- **会意补位**：形声池不足时用 seed 五段格式
  （`hui|字|零件=说明+零件=说明|本来是什么|怎么变的`）补会意字，两句话手写。
  **不许**为凑数把形声字谎报成会意、不许硬造象形小图（`check-data.mjs` L393
  「每类 ≥5」维持现状即可，800 的大头在形声，符合汉字学事实）。
- 每个新字必须 ∈ `CHARACTER_MAP`（`check-data.mjs` L325 既有规则）；1820 字表
  减去已收 525，池子还有 ~1300 字，形声占比足够。

### 1.4 门禁与回归

- `check-data.mjs` **L320 阈值 `>= 200` 升到 `>= 800`**，#4 同分支完成，禁回调；
  索引一致性（L364 `ETYMOLOGY_CHARS === ETYMOLOGY.map(e=>e.c).join('')`）、
  派生形旁与字表部首一致（L380）、查重（L322）全部既有，重跑即可。
- `check:round7` H3（≥200）被 800 自动覆盖，无需动。
- literacy `scripts/smoke.mjs` 的 `ROUTES` 追加一条 R8 扩充字样例
  （如 `['字源 扩充样例（R8）', '/#/etymology/<新收字>']`），防「生成了但渲染炸」。
- 体积：`etymology-derived.js` 只被 `etymology.js`（字源 chunk）引用，主包零增量；
  `etymology-index.js` 字符串 +≈0.9 KB 在预算内。`check:bundle` 会守。

---

## 2. 契约二 · 单元剧情 u59–u99 手写 + 儿歌 v1（H2，所有者 #5）

### 2.1 探针拆解

H2 四个与门，缺一即红：

| 条件 | 阈值 |
|---|---|
| `unit-stories.js` 源码里 `\bu(\d+)\s*:` 键数 | ≥ 99 |
| u59–u99 41 个键 | 一个不缺 |
| `src/data/songs.js` 里 `\bid\s*:` 计数 | ≥ 3 |
| 儿歌路由 | 识字 router 路由 path 命中 `/song\|儿歌\|music\|nursery/i`，或 router/unit-stories 源码命中 `/儿歌\|nursery\|SongsView\|SongList/i` |

### 2.2 单元剧情：`src/data/unit-stories.js`（手写追加）

- `STORIES` 对象追加 **u59–u99 共 41 条字面量键**（探针扫源码，键必须逐个写出）。
- 文案口径与 u1–u58 完全一致：**一句话（约 12–28 字）回答「这一站有什么」**，
  主题贴 `unit-index.js` 里该单元的 `name`/`desc`（u59「识字小路·笔画最少的一批字」
  → 写笔画；u99「识字终点·一千八百字到啦」→ 写抵达）。u59–u99 是按笔画/字形
  梯度切的收尾单元，剧情要把「越来越难的字」写成一条上山的叙事线，避免 41 句
  互相雷同（这是「告别 `unitTeaser()` 兜底」的意义所在——兜底模板一句套 41 站
  正是 R8 要消灭的观感）。
- **导出面冻结**：`unitStory` / `unitTeaser` / `unitCheer` / `TOTAL_UNIT_STORIES`。
  `fallback()` 与 `unitTeaser()` 的模板逻辑**保留不删**（`LearnView.vue` 消费方
  零改动；99 键全覆盖后兜底自然失活，删函数反而炸调用方）。文件头注释里
  「字表有 58 个单元」的口径同步改为 99。
- 校验（`check-data.mjs` 追加，#5 完成）：`UNITS` 的每个 id 都在 `STORIES` 有
  **手写**键（即 `TOTAL_UNIT_STORIES >= UNITS.length`）；每条剧情非空、长度
  8–40 字、不含「这一站的字都在这儿等你」兜底句式。

### 2.3 儿歌数据：`src/data/songs.js`（新，手写）

```js
/** 儿歌 v1：公版传统童谣，逐句跟唱。歌词正文每个字要么在字表里，
 *  要么在 SONG_GLOSS 里有拼音和一句话解释（沿古诗 POEM_GLOSS 的约束范式）。 */
export const SONGS = [
  {
    id: 'liang-zhi-lao-hu',     // 路由/记录用稳定 id，kebab-case 拼音
    title: '两只老虎',
    emoji: '🐯',
    tempo: 96,                   // BPM，连播时每句间奏的节拍参考
    palette: ['#ffce4d', '#ff9f45'],
    summary: '一句话说这首儿歌唱什么',
    lines: [
      { text: '两只老虎，两只老虎', pinyin: 'liǎng zhī lǎo hǔ liǎng zhī lǎo hǔ' },
      // pinyin 逐字空格分隔，字数与 text 的汉字数必须对上（标点不注音）
    ],
    actions: ['拍手', '跺脚']    // 可选：亲子律动提示
  }
]
export const SONG_GLOSS = { /* 字 → { p: 拼音, m: 一句话意思 }，字表外字兜底 */ }
export const SONG_MAP = new Map(SONGS.map((s) => [s.id, s]))
export const TOTAL_SONGS = SONGS.length
export function getSong(id) { return SONG_MAP.get(id) ?? null }
export function verifySongCoverage() { /* 返回越界字数组，check:data 断言为空 */ }
```

- **≥3 首**，选公版/传统童谣（两只老虎、小星星、数鸭子一类），不抄任何在版权
  期内的歌词。`id:` 键**只出现在歌曲对象顶层**——探针数的是全文 `\bid\s*:`，
  lines/嵌套结构里不许再用 `id` 字段名，保证计数=真实首数、不虚报。
- 用字约束走**古诗模式**而非绘本模式（儿歌正文不能改字）：逐字 ∈ `CHARACTER_MAP`
  或 ∈ `SONG_GLOSS`，`verifySongCoverage()` 由 `check-data.mjs` 跑（#5 追加规则，
  仿 L214 附近的古诗段）。

### 2.4 儿歌视图与路由

| 项 | 锁定 |
|---|---|
| 路由 | `path: '/songs'`、`name: 'songs'`、`component: () => import('@/views/SongsView.vue')`、`meta: { title: '儿歌童谣', emoji: '🎵' }`——静态路径，`/songs` 命中探针 `/song/i` 与 smoke 的 `findStaticRoute` |
| 视图 | `SongsView.vue` 单路由页内选歌（v1 不开 `/songs/:id` 详情路由，少一份 smoke/axe 状态成本） |
| 播放 | 逐句点读/整首连播走 `utils/audio.js` 的 `speak()`（`settings.speechRate` 生效）；当前句高亮 + `[aria-live]` 播报；**零音频资产**，若做旋律用 WebAudio 合成（仿 `audio.js` 的 `STREAK_CHORDS` 先例），可选不设门禁 |
| 拼音层 | 随 `settings.showPinyin` 显隐（沿 `PoemDetailView` 范式）；点字弹 gloss/字表释义 |
| 记账 | **v1 不写主存档**（§0.6 红线：`happy-literacy:v1` 不加顶层字段）；不喂 FSRS（没有作答行为）。想记「唱过几首」只许 sessionStorage |
| 入口 | `HomeView.vue` 加一张入口卡（静态文案，**不 import** `songs.js`，守主包）；smoke `ROUTES` 加 `['儿歌童谣', '/#/songs']` |
| 降级 | `speechSupported` 为假时如实提示「请大人读」，不装哑巴也不假唱（`voiceStatus()` 既有能力） |

---

## 3. 契约三 · 数学技能图谱可视化（H3，所有者 #6）

### 3.1 探针拆解与路径锁定

H3 = 路由 path 命中 `/skill|图谱|map-graph/i` **且**该路由是
`component: () => import('@/modules/....vue')` 动态形态 **且**视图文件存在 **且**
`data/skill-graph.js`（优先）或 `data/skills.js` 内容命中 `/nodes|skills|edges/i`。锁定：

| 项 | 锁定值 |
|---|---|
| 路由 | `path: '/skill-map'`、`name: 'skill-map'`、`component: () => import('@/modules/progress/SkillGraphView.vue')`、`meta.title: '技能图谱'`——写法与全 router 逐字同构（探针的 `dynamicView` 正则只认单引号 `@/modules/...` 形态） |
| 数据 | `apps/math-app/src/data/skill-graph.js`（新，探针首选路径） |
| 视图 | `apps/math-app/src/modules/progress/SkillGraphView.vue`（新，与 ProgressView 同目录——它是进度域的可视化，不是新星球） |

### 3.2 数据文件：`skill-graph.js` 导出面（冻结）

**唯一真源仍是 `curriculum.js` 的 `SKILLS`（34 节点）与 `deps` DAG**——skill-graph
不复制节点清单，import 后只派生布局与状态函数：

```js
import { SKILLS, SKILL_MAP } from './curriculum.js'          // 相对路径，§0.4
import { MASTERY_THRESHOLD } from '../utils/mastery.js'

/** 节点：curriculum 技能点 + 图上坐标。x 按 level 列（L1–L5 五列），
 *  y 按 module 泳道分行，单位是 0–100 的百分比（与 modules.js 的 node 同制）。 */
export const GRAPH_NODES = SKILLS.map(...)  // { id, name, module, level, deps, x, y }
/** 边：deps 展开成 { from: 依赖, to: 技能 }，方向 = 学习顺序。 */
export const GRAPH_EDGES = [...]
/** 泳道元数据：{ module, name, y }，name 取自 AGE_BAND_MODULES/星球名同源口径。 */
export const GRAPH_LANES = [...]
/**
 * 节点四态。mastered: mastery ≥ MASTERY_THRESHOLD；
 * learning: 0 < mastery < 阈值；ready: 未开始但 deps 全 mastered（deps 空视为满足）；
 * locked: 有未 mastered 的 deps。纯函数，无随机。
 * @param {string} id 技能 id
 * @param {Record<string, number>} mastery progress.state.mastery 快照
 */
export function nodeState(id, mastery) { /* → 'mastered'|'learning'|'ready'|'locked' */ }
```

- 纯数据 + 纯函数，禁 Vue / 浏览器 API（探针读文本，`check:content` 经
  `register-alias` import 校验）。
- `check:content` 追加规则（#6 完成，既有规则只加不改）：`GRAPH_NODES` 的 id 集合
  与 `SKILLS` 一一对应；`GRAPH_EDGES` 逐条都能在 `deps` 里找到出处、无多余边；
  坐标全部落在 [0,100]；`nodeState` 对「空 mastery」返回值只含 ready/locked
  且 ready 数 == 无依赖节点数。

### 3.3 视图契约：`SkillGraphView.vue`

- **SVG 渲染**（不用 Canvas——34 个节点要逐个可聚焦，读屏黑箱不可接受）：
  节点是 `<button>`（或 role=button 的 `<g>`），`aria-label` = `技能名·L档·状态`；
  边用 `<path>` `aria-hidden`。键盘 Tab 遍历节点，Enter 打开详情卡。
- **联动三件套**（Brief 点名 ageBand / 母题进度）：
  1. `settings.ageBand` → 初始视角/高亮对应 level 列，**只影响进来时看哪儿，
     不锁任何节点**（沿 R7 契约四的语义红线：ageBand≠解锁）；
  2. `progress.mastery` → `nodeState()` 四态着色（语义令牌，零硬编码色值；
     四态另配形状/描边差异，不只靠颜色区分——色弱可辨）；
  3. 节点详情卡：技能名、level、掌握度百分比、依赖清单（点依赖跳该节点）、
     「去练这个」按钮跳 `modules.js` 里该 `curriculumId` 星球的 `route`；
     `word-problems` 泳道的节点额外显示该技能的母题覆盖数
     （`WORD_PROBLEMS.filter(t => t.skill === id).length`——`wordProblems.js`
     已在懒加载 chunk 域，Vite 共享 chunk 不回流主包）。
- sr-only `[aria-live]` 汇总行：「已掌握 x / 共 34 项技能」。
- `reducedMotion()` 为真时无进场动画、无路径流光；`document.hidden` 无常驻计时。
- 入口：`ProgressView.vue` 顶部加入口卡（#6 独占该文件本轮改动）；HomeView 不加
  新星球（图谱是进度域视图，不是地图节点）。
- math `scripts/smoke.mjs` 的 `ROUTES` 加 `['技能图谱', '/#/skill-map']`。
- **不做的**：不改 `curriculum.js` 的节点与 deps；不动 `starsToUnlock` /
  `isModuleUnlocked`（星球解锁与技能四态是两套语义，图谱如实展示后者）；
  不新增持久化键；不做自动推荐学径（那是 adaptive.js 的地盘）。

---

## 4. 契约四 · OCR 精度基准 + 测验形近复核（H4，所有者 #7）

### 4.1 探针拆解

H4 = `hasBenchmark && quizWired`。`quizWired` 基线已绿（见文首），红线是**别把它改红**：
`CharDetailView.vue` 里 `@/utils/distractors` 的 import 与 `similarDistractors(` 调用
字样必须保留（这同时也是 `check:round7` H2.wiring 的命中点）。`hasBenchmark` 锁定
**从严路径**：交付 `apps/literacy-app/scripts/test-ocr-accuracy.mjs`（文件存在即命中，
`ROUND8_H4` 标记备胎不用）。

### 4.2 基准图集：`scripts/data/ocr-benchmark/`（新，生成后入库）

```text
apps/literacy-app/scripts/data/ocr-benchmark/
  manifest.json      ← [{ file, expect: '期望字符串', tier: 'clean'|'small'|'hard' }]
  clean-01.png …     ← T1 清晰印刷大字（≥4 张：单行 2–4 字，≈96px，白底）
  small-01.png …     ← T2 小字号长行（≥3 张：8–12 字，≈48px）
  hard-01.png …      ← T3 低对比/浅纹理底（≥3 张）
```

- 生成器 `scripts/gen-ocr-benchmark.mjs`（新，仿 `gen-ocr-sample.mjs` 的
  puppeteer-core 渲染链）：固定字体栈、固定布局，**开发机跑一次产物提交入库**，
  CI 不重画（字体环境差异会让基准漂移，入库图 = 冻结基准）。
- 图集全部用字 ∈ `CHARACTER_MAP`；总量 ≥10 张；`scripts/data/` 不进构建产物，
  APK / dist 体积零影响。

### 4.3 精度脚本：`test-ocr-accuracy.mjs`

- Node 里起 tesseract.js worker：`workerPath`/`corePath` 指 **node_modules**
  （Node 环境不走 `document.baseURI`，不复用 `ocrAssetUrl`），`langPath` 指
  `public/ocr/`（复用入库的 `chi_sim.traineddata.gz`，`gzip: true`）——全程离线。
  识别参数与运行时对齐（`OEM.LSTM_ONLY`；预处理不做——基准图本身干净，
  量的是引擎+语言包的底线）。
- 指标：逐图 `recall = |extractHanzi(识别文本) ∩ expect| / |expect|`（经
  `extractHanzi` 归一，与运行时取字规则同一条链）；按 tier 聚合宏平均。
- **阈值写死在脚本里，禁 env 放水**：T1 ≥ 0.95、全集 ≥ 0.85 起步；#7 实测定标后
  只许**上调**（图集与参数都冻结，tesseract 是确定性的，不存在 flaky 借口）。
- 输出机读汇总行（`tier / images / recall`），供 acceptance-log §2 引用。
- 挂载：literacy `package.json` 注册 `"test:ocr:accuracy": "node scripts/test-ocr-accuracy.mjs"`,
  并串进 app `test` 链（`test:ocr` 之后）。**豁免条款**：若实测全链耗时 > 90 s，
  允许改挂终验链（`ROUND8-ACCEPTANCE` 的 G5/G6 段）并在验收文档标注，
  但 `check:round8` H4 的文件存在性命中不受影响。

### 4.4 测验形近复核（Brief 点名「复核 CharDetailView 测验走形近池」）

- **听音步补同音闸门**（唯一代码改动点，`CharDetailView.vue` L274）：
  「听一听」放的是读音，干扰项若与目标**去声调同音**则题目无解。锁定改法：

```js
// 旧：listenOptions.value = shuffle([item.value, ...similarDistractors(decoded.value, 2)])
// 新：听音场景剔同音（toneless 来自 @/utils/pinyin.js，既有导出）
const samePinyin = (entry) => toneless(entry.pinyin) === toneless(item.value.pinyin)
listenOptions.value = shuffle([
  item.value,
  ...similarDistractors(decoded.value, 2, { reject: samePinyin })
])
```

- 「考一考」（`buildQuiz` L327）**不剔同音**（考字义不考字音）、保留既有
  「排除同释义」闸门——零改动。
- 单测：新增 `scripts/test-distractors.mjs`（挂 app `test` 链）：断言
  ①「日」的听音干扰不含任何 rì 同音字；② `similarDistractors` 首位仍是形近字库
  的最像邻居（`check:round7` H2 语义不破）；③ reject 闸门不把候选数打到 0
  （形近池 + 四档兜底仍能凑齐 2 个）。

---

## 5. 契约五 · 跟读 v2 音素/声调级评分 + 学伴对话面（H5，所有者 #8）

### 5.1 探针拆解与关键词落点

H5 = 关键词命中 + smoke 标记，两者都过剥注释这一关（§0.1）：

- 关键词 `/phoneme|音素|tone|声调|companion.*(?:chat|dialog|reply)|学伴.*对话|ROUND8_H5/i`
  必须落在 `useSpeechEval.js` / `FollowReadView.vue` / `MascotCompanion.vue`
  三文件拼接文本的**代码**里。本契约锁定多点命中留冗余：标识符
  `toneMarks` / `phonemeSummary` / `companionReply`，模板文本「声调」图例，
  三处至少两处真出现；
- literacy `scripts/smoke.mjs` 新增**代码级常量** `const ROUND8_H5_SMOKE = '/follow-read'`
  （仿 `ROUND6_H4_SMOKE` 的写法）+ 对应交互段。

### 5.2 评分内核：`utils/speechEval.js`（纯函数扩展，旧导出面冻结）

既有导出 `GRADES` / `normalizeTranscript` / `alignChars` / `similarity` /
`scoreFromSimilarity` / `LOUDNESS_SCORE_CAP` / `scoreFromLoudness` / `gradeOf` /
`evaluate` 的签名与行为**一个都不动**（`test-speech-eval.mjs` 既有断言冻结）。追加：

```js
/**
 * 音素/声调级诊断：对 alignChars 的替换对做拼音比对。
 * status 增补语义（只加不改）：
 *   'hit'  字对了
 *   'tone' 字错但去调拼音相同 —— 声调没读准（mā/mǎ）
 *   'near' 字错但声母或韵母相同 —— 发音接近（shān/sān）
 *   'miss' 其余（含查不到拼音的字，如实按 miss，不猜）
 * @param {string} reference 原文
 * @param {string} heard     识别文本
 * @param {(char: string) => string|null} lookupPinyin 带调拼音查询，由调用方注入
 *        （speechEval 保持零数据依赖：诗行注音 → CHARACTER_MAP → POEM_GLOSS 的
 *        组合链在 composable 侧拼）
 */
export function phonemeMarks(reference, heard, lookupPinyin) 
// → { chars: [{ char, status, expected?, heardAs? }], toneErrors, nearMisses }

/** v2 相似度：tone 记 0.5、near 记 0.25 的部分学分，多读轻罚规则沿用 similarity。 */
export function similarityV2(reference, heard, lookupPinyin)
```

- `utils/pinyin.js` 追加两个纯函数（`toneless`/`pinyinLetters` 不动）：
  `toneNumber(pinyin)`（带调拼音 → 1–4，无调号 → 5 轻声；heard 字走
  `CHARACTER_MAP` 条目的 `tone` 字段更快，函数是给诗行注音用的）与
  `splitSyllable(pinyin)`（去调后拆 `{ initial, final }`，零声母 initial 为空串）。
- `evaluate()` 的 recognition 分支：调用方传了 `lookupPinyin` 时用
  `phonemeMarks`/`similarityV2` 产出（`chars[].status` 四态、新增
  `phonemes: { toneErrors, nearMisses }` 字段），**没传则行为与今天逐字节一致**
  ——这是旧单测不炸的结构保证。loudness / selfcheck 档**不假装有音素信息**
  （听不出字就不标声调，界面如实说明）。
- 单测：`test-speech-eval.mjs` 追加 v2 断言（妈↔马 → tone；山↔三 → near；
  查不到拼音 → miss；`similarityV2` 部分学分数值锁定），既有断言零改动。

### 5.3 组合层与界面

- `useSpeechEval(options)` 加可选项 `lookupPinyin`；`result` 透传 v2 字段。
  **三档降级链（recognition / loudness / selfcheck）与隐私契约一字不动**：
  `allowRecognition` 默认 `false`、在线识别提示（`VoiceNotice` / `modeNote`）不退、
  录音只存内存 Blob。这是 Brief 的显式红线「三档降级保留，在线识别隐私提示不退」。
- `FollowReadPanel.vue` 结果区：逐字标记扩四态（hit 绿 / tone 黄标「声调」/
  near 橙标「再听听」/ miss 灰），点字重听正确读音（`speak(char)`）；
  图例文本含「声调」（关键词落点之一）。`scored` 事件 payload **只加字段**
  （`toneErrors` / `nearMisses`），`progress.recordFollowRead` 兼容旧形状。
- **学伴对话面**：`FollowReadView.vue` 用既有 `MascotCompanion` + `useMascotCoach`
  范式实现 `companionReply(result)`——按 `phonemes` 汇总生成墨墨的针对性台词
  （「有 2 个字的声调再听听」/「全对！」三挡以上），读完一轮墨墨接话、可点击重听。
  台词表放 `FollowReadView.vue` 或 `data/mascotLines.js`（后者改动归 #8，一段追加）。
  不接任何云端对话服务——「AI 学伴对话面」的 R8 口径 = 基于评分结果的规则对话，
  全离线（与 `round7-hongen-final-audit.md` §4-#10 的口径判定一致）。
- smoke 交互段（`ROUND8_H5_SMOKE`）：无头无麦环境走 selfcheck 档——断言
  ①降级提示可见（三档链不退化）；②结果图例含「声调」字样；③学伴台词区在场、
  无控制台报错。不要求真识别（无头 Chrome 没有 SpeechRecognition）。

---

## 6. 契约六 · Lighthouse Perf ≥ 95 双 App + a11y 余项（H6，所有者 #9）

### 6.1 门禁与测法（不新造）

测法与 R7 完全一致：`npm run test:acceptance`（gzip 静态服 + headless Chrome
移动模拟 + simulate 节流，Lighthouse 版本随 lockfile 锁定），`MIN_LH_*` 环境阈值
**不调**（脚本门槛 0.90 是下限，0.95 是 R8 验收线，由 acceptance-log 回填 +
H6 探针裁决）。R7 终点：识字 **97**/100/100、数学 **94**/100/100——本轮主战场是
**数学 +1 分**、识字守住 95+。

### 6.2 手段白名单（归因驱动，audit id 说话）

- 数学侧候选（按嫌疑排序，逐项附 Lighthouse audit id 归因后再动手）：预缓存清单
  排序（入口 chunk/CSS 前置）、`HomeView` 首屏动效延迟挂载、首页大元素
  `content-visibility`、manualChunks 微调消除瀑布、SW 注册时机复核；
- 识字侧只做**守成**：R8 新增（songs / skill-graph 不在识字、etymology-index
  +0.9 KB、跟读 v2 纯函数）都在懒加载域或误差内，`check:bundle` 与指纹检查抓回归;
- **禁**：删 aria 结构、懒加载首屏文本、调低 `acceptance.sh` 任何阈值、
  为分数去掉 `vite-offline-plugin` 的 runtime 前缀两段式（R7 契约 §1.5 成果）。

### 6.3 acceptance-log-round8.md 回填格式（探针可读，锁定）

H6 探针取「首个『识字』后的首个 `dd / dd / dd`」——§2.1 表格改写为**斜杠三连制**：

```markdown
### 2.1 Lighthouse Perf ≥ 95

| App | P / A / BP | 判定 |
|---|---|---|
| 识字 | 97 / 100 / 100 | PASS |
| 数学 | 95 / 100 / 100 | PASS |
```

- 该表必须是全文**第一次**出现「识字」「数学」字样的地方之前没有任何
  `dd/dd/dd` 形态的三连数字（`26/26`、`8/8` 两连不算，别在它前面写日期外的
  三连斜杠数字即可）；文档其余部分自由。
- 数值只认 `test:acceptance` 链的输出；达不到 95 的项必须附 audit id 级归因，
  不许只贴分数（沿 R7 契约七）。

### 6.4 a11y 余项与证据侧

- `axe-states.mjs` 四主题 × 全交互态 critical/serious 维持 **0/0**；Brief 点名的
  「数学首页对比度等」若走查再冒 serious，修 `design-tokens.css` 语义层
  （组件零硬编码，`check:tokens:wiring` 回归），修完把四主题对比度表
  `round7-theme-contrast.md` 增补 R8 复测列（新建 round8 文件亦可，报告引用为准）。
- **证据落盘归 #9**：LH 原始 JSON 双 App + axe 双扫描输出，按 §7.1 的路径规范
  写进 `.agent_workspace/evidence/r8/`（H6 探针查目录存在，git 空目录不存在——
  必须有已提交文件）。

---

## 7. 契约七 · 证据包 + GLOBAL-SUMMARY Round 8 + Android（H7/G6，所有者 #10，#9 供件）

### 7.1 证据包路径规范（锁定，全体引用这一份）

```text
.agent_workspace/evidence/r8/
  README.md                       ← 索引：逐文件清单 + SHA-256 + 工具版本 + 复现命令
  lighthouse/literacy.report.json ← LH 原始 JSON（mobile/simulate，#9 落盘）
  lighthouse/math.report.json
  axe/literacy-routes.json        ← axe 全路由扫描原始输出（#9）
  axe/literacy-states.json        ← axe-states 四主题交互态（#9）
  axe/math-routes.json
  axe/math-states.json
  checks/round6.txt round7.txt round8.txt android.txt
                                  ← 各门禁逐行输出快照（#10）
  bundle/literacy.txt math.txt    ← check:bundle 输出 + 首屏 gzip 记录（#9）
```

- 文件名小写连字符；JSON **原样入库不精简**（这是「证据包完备性」在 R7 审计里
  被点名的缺口）；`README.md` 必须能让第三方照着复现每一个数字。
- 所有权分区：`lighthouse/`、`axe/`、`bundle/` 归 #9；`checks/`、`README.md` 归 #10
  ——两人不碰同一文件，README 由 #10 在 #9 供件后收口。

### 7.2 GLOBAL-SUMMARY-REPORT.md 刷新规则（H7）

H7 = 长度 > 4000 字符（基线 11 KB 已满足）&& 含 `Round 8` && ❌ 计数 0 &&
`⬜/待回填/[P/F]` 计数 0 && 命中 `/evidence\/r8|证据包/i`。改写规则沿 R7 契约八：

- 新增 **Round 8 终态章**：31/31 模块对标全表（数据源 #2 的
  `round8-hongen-module-audit`——L-M6 字源 800、L-M11 剧情/儿歌、M-M1 技能图谱
  三行的状态翻转是本轮主叙事）+ R8 门禁快照（check:round8 8/8 全文粘贴）+
  §7.1 证据包索引（逐文件 + SHA-256）；
- 历史数字不删改；实测值只认终验链（G1–G7 全链）输出；测不了的项写豁免理由与
  替代证据，不留空、不写 ❌、不写「待回填」（这仨都是探针反向命中面）。

### 7.3 Android 重同步（G6）

- 全部功能分支合并后 `npm run sync:android` → `npm run check:android` **26/26**
  不退化（重跑不重建）；
- R8 对 APK 的体积增量预期：仅字源派生语料（~+80 KB 级）与儿歌文案，
  无新二进制资产——体积表回填 acceptance-log-round8 §2.2 并注明来源；
- 儿歌在 WebView 里依赖 TTS：Android 壳无中文语音时 `voiceStatus()` 既有降级
  提示生效，不为壳写原生插件（v1 边界不变）。

---

## 8. 文件所有权与冲突矩阵

| 热点文件 | 触碰者 | 隔离规则 |
|---|---|---|
| literacy `scripts/data/etymology-seed.txt`、`gen-etymology.mjs`、`data/etymology-derived.js`、`data/etymology-index.js` | #4 独占 | 生成物只经生成器改 |
| literacy `data/unit-stories.js` | #5 独占 | 只追加 41 键，导出面/兜底函数不动 |
| literacy `data/songs.js`、`views/SongsView.vue` | #5 新建 | — |
| literacy `src/router/index.js` | #5（`/songs` 一条） | 纯追加区段 |
| literacy `views/HomeView.vue` | #5（儿歌入口卡） | 只加卡不动布局骨架 |
| literacy `scripts/check-data.mjs` | #4（L320 阈值 800）、#5（剧情覆盖 + 儿歌覆盖规则段） | 各自追加独立段，既有规则只加不改 |
| literacy `scripts/smoke.mjs` | #4（字源样例路由行）、#5（songs 路由行）、#8（`ROUND8_H5_SMOKE` 常量 + 交互段） | 各自追加，不改既有段 |
| literacy `views/CharDetailView.vue` | #7 独占（`buildListen` L274 一处） | import 区与 `similarDistractors(` 字样不许消失（H4/R7-H2 双探针命中面） |
| literacy `scripts/test-ocr-accuracy.mjs`、`gen-ocr-benchmark.mjs`、`scripts/data/ocr-benchmark/`、`scripts/test-distractors.mjs` | #7 新建 | — |
| literacy `package.json` | #7 独占（`test:ocr:accuracy` + test 链） | — |
| literacy `utils/speechEval.js`、`utils/pinyin.js`、`composables/useSpeechEval.js`、`components/FollowReadPanel.vue`、`views/FollowReadView.vue` | #8 独占 | 旧导出/旧事件 payload 只加不改 |
| literacy `data/mascotLines.js` | #8（学伴台词段，可选落点） | 纯追加 |
| math `src/router/index.js` | #6（`/skill-map` 一条） | 纯追加 |
| math `data/skill-graph.js`、`modules/progress/SkillGraphView.vue` | #6 新建 | — |
| math `modules/progress/ProgressView.vue` | #6（入口卡一段） | — |
| math `scripts/check-content.mjs` | #6（图谱一致性段） | 既有规则只加不改 |
| math `scripts/smoke.mjs` | #6（一行路由） | 纯追加 |
| `.agent_workspace/acceptance-log-round8.md` | #9（§2.1/§2.3 Perf 区）、#10（其余） | 按节分区 |
| `.agent_workspace/evidence/r8/` | #9（lighthouse/ axe/ bundle/）、#10（checks/ README） | 按子目录分区（§7.1） |
| `.agent_workspace/GLOBAL-SUMMARY-REPORT.md` | #10 独占 | #2 审计只写自己的 audit 文件 |

**合并顺序建议**：#4 / #5 / #6 / #7 / #8 五条功能线互不依赖可乱序（`smoke.mjs` /
`check-data.mjs` 交叉点按上表「各自追加」规则先到先得）→ #9 Perf（要在全量功能上
量分数、落证据）→ #10 报告 + Android + 终验收尾。#3 的验收强化随时可合，但
**探针语义只许加严**：已定契约的命中面（路径、导出名、格式）变更须回改本文档。

---

## 9. 契约 → 门禁映射

| 契约 | check:round8 探针 | 所有者 | 回归红线 |
|---|---|---|---|
| §1 字源 800 | H1：`ETYMOLOGY_CHARS` ≥ 800 且无重复 | #4 | check-data 阈值 800 禁回调；R7-H3 自动覆盖；主包 +0.9 KB 内 |
| §2 剧情 99 + 儿歌 | H2：字面量键 u1–u99 ≥99 + `songs.js` id ≥3 + `/songs` 路由 | #5 | 导出面冻结；儿歌零音频资产、不写主存档 |
| §3 技能图谱 | H3：`/skill-map` 动态路由 + 视图 + `skill-graph.js` | #6 | curriculum 唯一真源；不锁节点；不新增持久化键 |
| §4 OCR 精度 | H4：`test-ocr-accuracy.mjs` 存在 + quizWired 不退 | #7 | 阈值只升不降；基准图集冻结入库；听音剔同音 |
| §5 跟读 v2 | H5：三文件代码级关键词 + `ROUND8_H5_SMOKE` | #8 | 三档降级与隐私提示不退；旧评分单测冻结 |
| §6 Perf 95 | H6：log 斜杠三连 ≥95×2 + `evidence/r8` 目录 | #9 | 不调 MIN_LH_*；不删 aria；axe 四主题 0/0 |
| §7 全局报告 | H7：Round 8 + 零 ❌ 零占位 + 证据索引 | #10 | 历史数字不删改；实测不伪造 |
| §7.3 Android | （G6）sync:android + check:android 26/26 | #10 | 体积增量入 log |
| 全体 | H8：`check:round7` 8/8（+G3 `check:round6` 7/7） | 每个分支 | 合并前 npm test 全绿 |

---

## 10. 明确不做（Out of scope）

- 字源不为凑 800 收生僻构件声旁、不谎报六书分类、不动 `EtymologyStage.vue` 动画协议；
- 儿歌不引入音频文件/曲谱资产、不接任何在线曲库、不做录音跟唱评分（那是跟读的地盘）、
  不为儿歌加主存档字段；
- 技能图谱不做自动学径推荐（adaptive.js 地盘）、不动星球解锁经济、不做可拖拽编辑；
- OCR 不做手写体基准、不做拍照端到端 UI 自动化精度回归（基准量引擎，UI 链归 smoke）、
  不调运行时识别参数去过基准（基准适配引擎现状，不许反向拟合）；
- 跟读 v2 不接云端 ASR/对话模型、不做真声学音素分析（浏览器拿不到音素流，
  v2 口径 = 识别文本 × 拼音知识的音素/声调诊断，界面如实说明）；
- Perf 不调阈值、不删无障碍结构换分、不动 `vite-offline-plugin` 无 runtime 前缀时
  的逐字节等价行为；
- 不改识字主存档 `happy-literacy:v1` 顶层结构与 FSRS 参数；不动数学
  `mathquest/settings` 的 sanitize 白名单。
