# Round 4 架构契约 · 数学错题本 + 自适应调度 + 可复现题目 ID（M-M10 / M-M9 / M-M2）

> 面向实现子代理 #6（错题本 + adaptive）与 #7（seed PRNG + 日冒险）的**实现契约**。
> 两个子代理共享本文的 questionId 与 PRNG 契约——这是它们唯一的交叉点，必须先对齐。
> 基线：`cursor/openmoji-integration-9f67` · App：`apps/math-app/`
> 关联：`SURPASS-HONGEN-MASTER-PLAN.md` §3（M-M2/M-M9/M-M10/M-M12）、`ROUND4-BRIEF.md`、
> `round3-sota-final-audit.md` §H（错题本/seed 的定案口径）

---

## 0. 现状与目标差距

| 现状 | 目标（Round 4） |
|---|---|
| `utils/random.js` 全部 `Math.random()`，题目不可复现 | mulberry32 可种子 PRNG；同 seed 同题 |
| 题目 `id` 是题面拼串（如 `ArithmeticView` 的 `` `${a}${sign}${b}` ``），跨模块不唯一、不可反解 | 全局唯一、可反解重生成的 `questionId`（§2） |
| 答错只记 `errorTagCounts`（错因聚合），无按题记录 | `wrongBook[questionId]` 按题记录 + 重练答对移出（§3） |
| `mastery.js` EMA 只记录；`pickNextSkill` 只管技能维度，无难度档调度 | `utils/adaptive.js`：连对升档/连错降档/弱项优先（§4） |
| 题目生成散在各视图（`makeQuestion` 私有函数） | 母题注册表：按 `templateId + seed` 确定性生成（§2.2） |

**不变式（实现必须保持）**：
- `QuizShell` 的题目协议向后兼容：老字段（`answer/options/unit/hints/stars/xp/tag/errorTags/skill`）
  语义不变，只**新增**字段。
- `progress.recordAnswer` 两种既有调用签名不变（`(moduleId, ok, opts)` 与 `(question, ok)`）。
- `utils/random.js` 既有导出（`randInt/sample/shuffle/pick/numericOptions/distractors/uid`）
  签名不变——全 App 到处在用，只加不改。
- localStorage 结构只增字段：`mergeState` 给老档回落，`BACKUP_VERSION` 保持 `1`
  （纯增量，老备份导入新版本、新备份导入老版本都不炸）。

---

## 1. PRNG 契约（`utils/random.js` 增量）

```js
/** mulberry32：32 位种子 → [0,1) 均匀分布。同 seed 序列完全一致。 */
export function mulberry32(seed) { /* 标准实现，返回 () => number */ }

/** 任意字符串 → 32 位无符号整数种子（FNV-1a 或 xmur3，实现方选定后写注释）。 */
export function hashSeed(str) {}

/** 下列函数与既有 API 同形，但第一个参数注入 rng（mulberry32 返回值）。 */
export const seededInt = (rng, min, max) => {}
export const seededSample = (rng, arr) => {}
export function seededShuffle(rng, arr) {}
export function seededOptions(rng, answer, opts) {}   // numericOptions 的可种子版
```

规则：
- 既有的 `randInt/sample/...` 保留原实现（UI 场景如星空粒子不需要可复现）；
  **出题路径一律换 seeded 版**。
- 生成器内部**只允许**用传入的 `rng` 取随机数——夹带一次 `Math.random()`
  就破坏可复现性，`check:questions` 门禁（§5）靠双跑 deep-equal 抓这种回归。

---

## 2. questionId 契约

### 2.1 格式

```
<templateId>@<seed36>
例：arith.add.100@k3f9z  ·  wp.combine@1x  ·  ns.compare@a0
```

- `templateId`：母题 id，**点分命名** `<模块缩写>.<母题名>[.<档位>]`，
  全局唯一，注册进注册表（§2.2）。模块缩写与 `MODULES.id` 对照：
  `arith`(arithmetic) / `ns`(counting·number-sense) / `geo`(geometry) /
  `logic` / `sudoku` / `wp`(word) / `cmp`(比较模块，M-M4 新入口)。
- `seed36`：32 位无符号种子的 base36 编码（小写）。
- `@` 为分隔符（templateId 里禁用）。解析函数：

```js
// src/core/questions/id.js（新文件）
export const makeQuestionId = (templateId, seed) => `${templateId}@${seed.toString(36)}`
export function parseQuestionId(qid) {}  // -> { templateId, seed:Number } | null（格式非法）
```

### 2.2 母题注册表（新目录 `src/core/questions/`）

```js
// src/core/questions/registry.js
/**
 * 注册一个母题。generate 必须是纯函数：同 (rng) 序列 → 深等的题目对象。
 * @param {{
 *   id: string,            // templateId（§2.1）
 *   module: string,        // 玩法模块 id（MODULES.id，进 wrongBook/统计）
 *   skill: string,         // curriculum 技能点 id（isKnownSkill 必须为 true）
 *   level?: string,        // L1-L5，adaptive 档位筛选用
 *   generate: (rng) => QuizShellQuestion,  // 不含 id 字段，registry 统一盖章
 * }} tpl
 */
export function registerTemplate(tpl) {}
export function generateQuestion(templateId, seed) {}   // 盖好 id 的完整题目 | null(未知模板)
export function regenerateFromId(qid) {}                // parse + generate 的组合 | null
export function listTemplates() {}                      // 门禁脚本与日冒险枚举用
export const templateCount = () => listTemplates().length
```

- 各模块的母题定义放 `src/core/questions/<module>.js`，由 `index.js` 统一
  import 注册（显式 import，保证 tree-shaking 可分析、SSR/测试环境无副作用惊喜）。
- **Round 4 迁移范围**：`arithmetic`（加/减 × 3 档 ≥6 母题）、`word-problems`
  （现有 ~34 母题模板化）、`ns.compare`/`cmp`（比较新玩法）必须走注册表；
  geometry/logic/sudoku 允许保留视图内生成到 R5，但**发给 QuizShell 的题目
  也要有 id**——用 `makeQuestionId('geo.pick-shape', seed)` 风格现场盖章，
  seed 记录生成时用的种子；暂不可复现的模块靠 wrongBook 的 snapshot 兜底（§3.1）。
- 日冒险（M-M12，子代理 #7）的种子约定：`hashSeed('daily:' + 'YYYY-MM-DD' + ':' + n)`，
  n = 0..4 —— 同一天全球同 5 题，天然可复现、可分享。

### 2.3 QuizShell 题目协议增量

```js
{
  id: String,        // 【升级为必填】questionId（§2.1）。QuizShell 原样透传，不解析。
  skill: String,     // 既有
  template: String,  // 【新增，可选】templateId，省一次 parse
  snapshot: Object,  // 【新增，可选】{ prompt, answer, options?, unit? } 错题本兜底渲染用
  // ...其余既有字段不变
}
```

---

## 3. wrongBook 契约（M-M10）

### 3.1 Schema（`stores/progress.js` state 增量）

```js
wrongBook: {
  [questionId]: {
    module: String,        // MODULES.id，入口按星球分组
    skill: String|null,    // curriculum 技能点，adaptive 弱项联动
    addedAt: Number,       // 首次答错 ms
    lastWrongAt: Number,   // 最近一次答错 ms（排序键）
    wrongCount: Number,    // 累计答错次数（含重练中再错）
    retryCount: Number,    // 重练发起次数
    errorTags: String[],   // 最近一次的错因标签（覆盖式，不累计——聚合已有 errorTagCounts）
    snapshot: {            // 模板缺席时的静态兜底（模块未迁移注册表 / 版本漂移）
      prompt: String,      // 题面文本（如 '37 + 25 = ?'）
      answer: Number,
      options: Number[]|null,
      unit: String|null,
    }|null,
  }
}
```

规则：
- **容量上限 200 条**：超出时按 `lastWrongAt` 最旧的先淘汰（错太多不追着孩子屁股记账）。
- `mergeState` 回落 `wrongBook: {}`，逐条洗形状（照 `mergeDaily` 的防脏模式）。
- **移出规则（验收口径）**：该 `questionId` 任意一次答对即删除条目——
  无论来自错题本重练还是日常练习中原题重现。一次答对即移出（brief 定案：「答对移出」）。

### 3.2 store API 增量

```js
// 动作
function recordWrong(questionId, { module, skill, errorTags, snapshot }) {}  // 建条/累计
function resolveWrong(questionId) {}                                         // 答对移出
// 派生
const wrongBookEntries = computed(() => /* Object.entries 按 lastWrongAt 倒序的数组 */)
const wrongBookCount = computed(() => wrongBookEntries.value.length)
const wrongBookByModule = (moduleId) => {}                                   // 星球入口分组
```

**接线点：`recordAnswer` 内部自动分流**（调用方零改动是本设计的核心）：

```js
function recordAnswer(target, isCorrect, opts = {}) {
  // ...既有逻辑不动...
  const qid = (typeof target === 'object' ? target.id : opts.questionId) ?? null
  if (qid && parseQuestionId(qid)) {                // 老拼串 id（'37+25'）解析为 null，不进错题本
    if (isCorrect) resolveWrong(qid)
    else recordWrong(qid, { module: moduleId, skill: skillId, errorTags,
                            snapshot: opts.snapshot ?? target.snapshot ?? null })
  }
}
```

### 3.3 QuizShell 接线（一处小改）

`grade()` 里两个 `progress.recordAnswer(props.moduleId, ...)` 调用的 opts 各加两个字段：

```js
progress.recordAnswer(props.moduleId, right, {
  skill: q.skill, /* ...既有... */
  questionId: q.id,
  snapshot: q.snapshot ?? null,
})
```

其余判题/星星/连击逻辑零改动。答对时 `recordAnswer` 内部的 `resolveWrong`
自动生效——重练视图**不需要**特殊的"重练模式"标记。

### 3.4 重练入口（新视图 `modules/wrong-book/WrongBookView.vue` + 路由 `/wrong-book`）

- 列表页：按模块分组展示 `wrongBookEntries`（题面用 `regenerateFromId` 的
  prompt，模板缺席回落 `snapshot.prompt`），显示错误次数与错因标签
  （文案走 `errorTagInfo`，与家长报表同源）。
- 「重练」：取 ≤5 条生成 `questions` 数组喂 `QuizShell`（`moduleId` 用原模块 id，
  掌握度/星星照常记账）：
  - 可复现条目：`regenerateFromId(qid)` —— **原题原样重练**；
  - 仅 snapshot 条目：用 snapshot 构造静态题（无 options 时走 keypad 模式）。
  - 发起时对涉及条目 `retryCount += 1`。
- 入口暴露（验收口径 ≥2 处）：HomeView（有错题时显示角标 chip）、
  ParentView 错因分区（"去重练"按钮）；ProgressView 可选。
- 空态：无错题时显示鼓励空态页，不藏路由。

---

## 4. adaptive 调度器契约（M-M9 · 新文件 `utils/adaptive.js`）

与既有 `utils/mastery.js` 的分工：**mastery.js 管"练哪个技能"（不动），
adaptive.js 管"这个技能练多难 + 下一轮出什么题"（新增）**。全部纯函数/纯工厂，
不 import store、不碰 localStorage——由视图把 store 数据喂进来，Vitest 可全覆盖。

### 4.1 难度档调度（连对升档 / 连错降档）

```js
/**
 * @param {{
 *   levels: any[],          // 档位数组（如 ArithmeticView 的 [10,20,100]）
 *   initialLevel?: any,     // 默认 levels[0]；接家长年龄档时传 LEVEL_BY_AGE_BAND 值
 *   upStreak?: number,      // 连对 N 升一档，默认 3
 *   downStreak?: number,    // 连错 N 降一档，默认 2
 * }} cfg
 * @returns {{
 *   level: () => any,                 // 当前档
 *   record: (correct: boolean) => (
 *     { changed: false } |
 *     { changed: true, direction: 'up'|'down', from: any, to: any }
 *   ),                                // 每题判完喂一次；变档时内部清零连击计数
 *   reset: () => void,
 * }}
 */
export function createAdaptiveSession(cfg) {}
```

- 变档在**题与题之间**生效（QuizShell 的 `graded` 事件里 record，`advance`/下一轮
  应用新档），一轮进行中不换当前题。
- 到顶/到底不变档（`changed: false`），不回绕。
- 降档时返回值供视图弹「我们先退一步练稳」的鼓励文案 + 教具提示（M-F5 口径：
  连错给教具提示——视图层责任，调度器只报 direction）。

### 4.2 弱项优先出题计划

```js
/**
 * 生成下一轮的出题计划（不生成题目本身，只出「配方」）。
 * 默认配比：60% 当前档常规 + 20% 错题重练 + 20% 弱项技能。
 * 桶为空时向常规桶回填，总数恒等于 count。
 * @param {{
 *   count: number,                       // 轮次题数（如 10）
 *   moduleId: string,
 *   mastery: Record<string, number>,     // progress.mastery
 *   wrongBook: Record<string, object>,   // progress.state.wrongBook
 *   rng?: () => number,                  // 注入 mulberry32；缺省 Math.random（仅交互路径）
 * }} input
 * @returns {Array<
 *   { kind: 'regular' } |
 *   { kind: 'retry', questionId: string } |
 *   { kind: 'weak', skill: string }
 * >}
 */
export function planRound(input) {}

/** 弱项 = 0 < mastery < MASTERY_THRESHOLD(0.8)，按掌握度升序取 n 个。 */
export function pickWeakSkills(masteryMap, skills, n) {}
```

- `retry` 项由视图用 `regenerateFromId` 落地；`weak` 项传给该技能对应母题
  （registry 按 `skill` 字段筛模板）；`regular` 走视图现有当前档生成逻辑。
- `pickNextSkill`（mastery.js 的 70/20/10 调度）继续负责"跨技能推进"场景
  （日冒险选题、HomeView 推荐），两者不合并——职责不同，合并会把
  纯技能维度和轮次配方搅在一起。

### 4.3 视图接线（以 ArithmeticView 为样板，其余模块 R5 跟进）

```
setup:  session = createAdaptiveSession({ levels: [10,20,100],
          initialLevel: LEVEL_BY_AGE_BAND[settings.ageBand] })
graded: const r = session.record(result.correct)
        if (r.changed) → 播报变档文案；记 pendingLevel = r.to
finished/replay: level.value = pendingLevel ?? level.value
                 questions = planRound(...) 展开为新一轮题目数组
```

家长中心（M-M14 报表深化，可选）：ParentView 增「自适应」开关
（`settings.adaptive`，默认 true）；关掉时视图不建 session，行为回落手动选档。

---

## 5. 题库门禁（M-M2 · `check:questions` ≥300 可复现）

新脚本 `scripts/check-questions.mjs` + 根 `package.json` script `check:questions`
（并挂进 `test:round3` 链或其 Round 4 后继，由子代理 #10 收口）：

1. import 注册表，枚举 `listTemplates()`；
2. 每模板 × 16 个固定种子（`hashSeed(templateId + ':' + i)`）生成题目：
   - **可复现断言**：同 (templateId, seed) 生成两次，`JSON.stringify` 深等；
   - **合法性断言**：`answer` 有限数；有 `options` 时含 `answer` 且互异；
     `skill` 过 `isKnownSkill`；`id === makeQuestionId(...)` 且 `parseQuestionId` 可逆；
3. 统计**互异题目**数（按 `id` 去重后再按题面 `JSON.stringify` 去重），
   `< 300` 即 exit 1 并打印各模板产量表。

口径说明：34+ 母题 × 16 种子 ≈ 544 生成位，参数域重叠去重后 ≥300 是保守可达值；
如不足，优先给 arithmetic 补档位母题而不是调低门禁。

---

## 6. 验收清单（供子代理 #3 的 acceptance-log 引用）

| # | 验收项 | 验证方式 |
|---|---|---|
| W1 | 答错自动入 `wrongBook`，条目含错因标签与可反解 id | Vitest（store 单测） |
| W2 | 重练答对移出；日常练习原题答对同样移出 | Vitest + smoke |
| W3 | `/wrong-book` 列表 + 重练走 QuizShell；空态可达 | smoke |
| W4 | 老存档导入不炸（无 `wrongBook` 字段回落 `{}`）；导出→导入往返保真 | Vitest（mergeState） |
| W5 | 同 seed 同题：`regenerateFromId(qid)` 与首次生成深等 | `check:questions` |
| W6 | 题库门禁 ≥300 互异可复现题目 | `check:questions` exit 0 |
| A1 | 连对 3 升档、连错 2 降档、到边界不回绕 | Vitest（adaptive 单测） |
| A2 | `planRound` 配比正确、空桶回填、注入 rng 后确定性 | Vitest |
| A3 | ArithmeticView 实际接线：变档有文案播报，轮间生效 | smoke |
| A4 | 日冒险 5 题同日同题（date seed） | Vitest（子代理 #7） |

## 7. 文件清单（新增/修改）

```
apps/math-app/src/
├── core/questions/
│   ├── id.js            [新增] makeQuestionId / parseQuestionId
│   ├── registry.js      [新增] registerTemplate / generateQuestion / regenerateFromId
│   ├── arithmetic.js    [新增] 加减母题（从 ArithmeticView.makeQuestion 迁出）
│   ├── word-problems.js [新增] 应用题母题（从 data/wordProblems.js 模板化）
│   ├── compare.js       [新增] 比较母题（M-M4，子代理 #7）
│   └── index.js         [新增] 统一注册出口
├── utils/random.js      [修改] mulberry32/hashSeed/seeded* 增量（§1）
├── utils/adaptive.js    [新增] createAdaptiveSession / planRound / pickWeakSkills（§4）
├── stores/progress.js   [修改] wrongBook 字段 + recordWrong/resolveWrong + recordAnswer 分流（§3）
├── components/QuizShell.vue [修改] recordAnswer opts 加 questionId/snapshot（§3.3，两行）
├── modules/wrong-book/WrongBookView.vue [新增] 列表 + 重练（§3.4）
└── router/index.js      [修改] /wrong-book 路由（懒加载）

scripts/check-questions.mjs  [新增] 题库门禁（§5）
```

冲突提示：子代理 #6 与 #7 都要动 `utils/random.js` 与 `core/questions/`——
**#7 负责 §1 PRNG 与 §2 注册表基建 + compare/日冒险，#6 在其上做 §3 错题本与
§4 adaptive**；若并行起跑，两边都按本契约写同名文件，合并时以本文签名为准，
先合 #7 再 rebase #6。`stores/progress.js` 只有 #6 动。
