# Round 4 架构契约 · 识字单字状态机（L-M2 / L-M3 / L-M14）

> 面向实现子代理 #4（opus-fast，`cursor/r4-literacy-statemachine-*`）的**实现契约**。
> 本文只定义接口、状态、事件与文件边界；实现细节（样式、文案微调）由实现方自由发挥。
> 基线：`cursor/openmoji-integration-9f67` · App：`apps/literacy-app/`
> 关联：`SURPASS-HONGEN-MASTER-PLAN.md` §2（L-M2/L-M3/L-M14）、`ROUND4-BRIEF.md`、
> `literacy-architecture.md` §3.3（数据流原型，本文取代其中的状态机部分）

---

## 0. 现状与目标差距

| 现状（`CharDetailView.vue`） | 目标（Round 4） |
|---|---|
| 单页平铺：笔顺盒、组词、例句、「我认识啦」按钮同时可见，无先后引导 | `intro→trace→listen→quiz→reward` 五阶段**自动衔接**，一个阶段完成自动进入下一个 |
| 听音识字只在 `/game/listen` 独立路由 | 单字闭环内嵌一轮 2×2 听音小测（listen 阶段），复用形近干扰项 |
| `HanziStrokeBox` 描红错笔只播 `sfx.wrong()` + 文字提示 | 同一笔**错满 3 次自动示范该笔**，示范后继续 quiz（L-M3） |
| 星星/庆祝有，无徽章 | 徽章体系 v1：progress store 记录 + 成就展示（L-M14） |

**不变式（实现必须保持）**：
- 现有路由 `/learn/:char` 不变；直接访问仍可用（状态机是增强，不是门槛）。
- 现有 store 事件（`visitChar`/`markHeard`/`markTraced`/`recordAnswer`）语义不变，
  状态机只是**编排**它们，不重写掌握度逻辑（0–3 级 `recomputeLevel` 不动）。
- 描红的键盘替代通道（空格写下一笔 / Esc 跳过）与 live region 播报全部保留（R3 a11y 成果）。
- 每个阶段都可跳过（儿童挫败感控制 + D-6「庆祝可跳过」延伸到全部环节）。

---

## 1. 状态机定义

### 1.1 状态集合

```
intro → trace → listen → quiz → reward → (done)
```

| phase | 内容 | 完成条件 | 对应 store 事件 |
|---|---|---|---|
| `intro` | 大字 + 拼音朗读 + 释义 + 部首/字源提示，自动 TTS 读一遍字与组词 | 朗读完成或点「继续」 | `visitChar(char)`（进入时）、`markHeard(char)`（TTS 实际播放后） |
| `trace` | `HanziStrokeBox` 直接进 quiz 模式描红 | `quiz-complete`（含键盘替代写完）或 `quiz-skip` | `markTraced(char)`（仅 complete 时；skip 不记） |
| `listen` | 2×2 听音选字：正确字 + `distractors` 形近字 + 已学字补位 | 选中任意项（对错都算完成） | `recordAnswer(char, ok)`（走 `recordQuiz`，更新 FSRS 卡） |
| `quiz` | 组词测验：给出该字组词，四选一补全（干扰项来自其他字的词） | 选中任意项 | `recordAnswer(char, ok)` |
| `reward` | 星星结算 + 掌握度变化展示 + 徽章判定 + 「下一个字 / 回字表」 | 点击去向按钮（或 3s 自动推荐下一个） | `completeFlow(char)`（新增，见 §3.1）；内部触发 `checkBadges()` |

### 1.2 事件与转移表

机器只认 5 种事件，全部由视图层派发：

| 事件 | 载荷 | 允许的当前态 | 转移 |
|---|---|---|---|
| `ADVANCE` | `{ result? }` | 任意非 `done` | 进入下一阶段（按 §1.1 顺序） |
| `SKIP` | — | 任意非 `reward/done` | 同 `ADVANCE`，但打 `skipped` 标记（不计学习事件） |
| `RETRY` | — | `trace/listen/quiz` | 留在当前阶段，重置该阶段局部状态 |
| `GOTO` | `{ phase }` | 任意 | 直接跳到指定阶段（阶段导航点点用；不发学习事件） |
| `RESET` | `{ char }` | 任意 | 换字：回 `intro`，清空全部局部状态 |

守卫（guard）规则：
- `trace` 的 `ADVANCE` 只能由 `quiz-complete`/`quiz-skip` 回调触发，视图不得提供"直接下一步"按钮绕过（`SKIP` 按钮除外，它语义就是跳过）。
- `listen`/`quiz` 答错**不阻塞**转移：记 `recordAnswer(char, false)` 后照常 `ADVANCE`（掌握度和 FSRS 会自己把这个字排回复习队列，不在闭环里罚站）。
- `reduceMotion`（`settings.motion === 'reduced'`）时跳过所有转场动画，直接切 DOM（见 §4）。

### 1.3 实现载体：`composables/useCharFlow.js`（新文件）

**纯组合式函数，不建新 store**——阶段状态是单页会话态，刷新即回 `intro`，
没有持久化诉求；持久化的只有学习事件本身（已由 progress store 负责）。

```js
// apps/literacy-app/src/composables/useCharFlow.js
export const PHASES = ['intro', 'trace', 'listen', 'quiz', 'reward']

/**
 * @param {Ref<string>} char  当前字（CharDetailView 的 decoded）
 * @param {object} opts { onPhaseChange(from, to), autoAdvanceDelayMs = 800 }
 * @returns {{
 *   phase: Ref<'intro'|'trace'|'listen'|'quiz'|'reward'>,
 *   phaseIndex: ComputedRef<number>,        // 0..4，阶段进度点用
 *   results: Ref<Record<string, 'done'|'skipped'|'right'|'wrong'|null>>,
 *   advance(result?: string): void,          // ADVANCE
 *   skip(): void,                            // SKIP
 *   retry(): void,                           // RETRY
 *   goTo(phase: string): void,               // GOTO
 * }}
 */
export function useCharFlow(char, opts = {}) { /* ... */ }
```

要求：
- `watch(char)` 内部自动 `RESET`（换字回 intro），CharDetailView 不需要手动管。
- `results` 供 reward 阶段结算文案用（"描红满分 / 听音答对 / 组词跳过"）。
- 转移逻辑必须是纯函数可单测：内部导出 `nextPhase(phase)`、`canGoto(phase)`
  供 `apps/literacy-app/test/`（或现有测试目录）写 Vitest 用例。

### 1.4 CharDetailView 改造边界

- 模板改为 `<component>` 级的阶段分区：每个阶段一个 `<section>`，`v-show`/`v-if`
  由 `phase` 驱动；组词/例句区并入 `intro`（朗读素材）与 `quiz`（出题素材）。
- 顶部加**阶段进度点**（5 个圆点，当前点放大），每个点是可点的 `<button>`
  （触发 `GOTO`），`aria-label="第 n 步：描红"`、`aria-current="step"`。
- 保留「我认识这个字啦」按钮作为 intro 的 `ADVANCE` 入口之一（语义不变，仍走 `markKnown`）。
- 阶段切换时把焦点移到新阶段的标题（`tabindex="-1"` + `.focus()`），并向现有的
  `role="status"` live region 写一句"进入第 n 步：xxx"（读屏用户能跟上自动衔接）。
- `?phase=trace` query 支持深链（家长报表"去练这个字的描红"可直达）；非法值回落 `intro`。

---

## 2. L-M3 · 描红错 3 次自动示范该笔

### 2.1 契约（`HanziStrokeBox.vue` 内部实现，对外只加 props/emits）

| 新增 | 类型 | 说明 |
|---|---|---|
| prop `autoDemoAfter` | `Number`，默认 `3` | 同一笔连续错满 N 次触发示范；`0` 表示关闭 |
| emit `stroke-demo` | `(strokeNum: number)` | 示范开始时触发，供上层播报/统计 |

### 2.2 行为规范

1. 在 `writer.quiz({ onMistake })` 里按 `strokeNum` 维护 `mistakesOnStroke` 计数
   （换笔清零；hanzi-writer 已保证 `strokeNum` 是当前笔）。
2. 计满 `autoDemoAfter` 次：
   - 暂停 quiz（`writer.cancelQuiz()`）；
   - 用 `writer.animateStroke(strokeNum)`（hanzi-writer 3 原生 API）演示该笔一遍；
   - 演示完毕 `writer.quiz({ ...原有选项, quizStartStrokeNum: strokeNum })`
     从**当前笔**恢复测验（`quizStartStrokeNum` / `animateStroke` 已在锁定版本
     hanzi-writer 3.7.3 的 dist 中确认存在，可放心使用）；
   - `hint`（live region）写入"看我写一遍第 n 笔，跟着写试试"。
3. 与现有 `showHintAfterMisses: 2` 的关系：保留。时序为
   错 2 次 → 高亮提示（现有），错第 3 次 → 自动示范（本契约）。
4. 示范期间屏蔽指针输入（quiz 已 cancel 天然屏蔽），键盘替代通道在示范结束后照常可用。
5. `settings.reduceMotion` 时示范动画用最快速档（复用现有 `strokeAnimationSpeed: 3` 的取值逻辑）。

### 2.3 状态机联动

`stroke-demo` 事件冒泡到 CharDetailView 只做播报，**不改变 phase**；
示范后写完照常触发 `quiz-complete` → `ADVANCE`。`onQuizComplete` 的
`mistakes === 0` 判定不变（示范不清零 mistakes，满分仍要求全程无错）。

---

## 3. L-M14 · 徽章体系 v1

### 3.1 progress store 增量（`stores/progress.js`）

```js
// state 新增（migrate() 里给老档回落 {}，与现有 books/idioms 同款容错）
badges: {},            // { [badgeId]: unlockedAtMs }

// 新增动作
function completeFlow(char) {}   // reward 阶段调用：flowsDone 计数 +1 并 checkBadges()
function checkBadges() {}        // 遍历 BADGES 定义，新解锁的写入 state.badges
                                 // 并 celebrate({ kind:'badge', badgeId, title, emoji })
// 新增派生
const unlockedBadges = computed(() => /* BADGES × state.badges 合成，带 unlockedAt */)
const lockedBadges = computed(() => /* 未解锁的，家长/成就页显示灰态 */)
```

另在 `state` 增 `flowsDone: 0`（完成过多少次完整五阶段闭环，徽章判据之一）。
`exportJson`/`importJson` 不需要动——它们整档序列化 `state`，新字段自动随行；
`migrate()` 必须补 `badges: {}`、`flowsDone: 0` 回落。

### 3.2 徽章定义（新文件 `data/badges.js`，数据驱动同 math 侧 `data/achievements.js` 风格）

```js
export const BADGES = [
  // { id, name, emoji, desc, test(snapshot) => boolean }
]
```

`snapshot` 至少含：`learnedCount, masteredCount, stars, streakDays, flowsDone,
booksFinished, idiomsRead, listenBestStreak, quizTotals`。
v1 至少 10 枚，覆盖：首字掌握 / 学满 10·50·100 字 / 掌握 25 字 / 连续 3·7 天 /
首次五阶段闭环 / 闭环 20 次 / 描红满分 10 次 / 听音连对 5。
（具体文案实现方定，`test` 必须是纯函数，异常按 false 处理——照抄 math 侧
`checkAchievements` 的 try/catch 模式。）

### 3.3 展示

- 成就页：并入 `HomeView` 的进度区或 `ParentView` 报表页新增「徽章墙」分区
  （实现方二选一，验收口径是**至少一处可见全部徽章 + 解锁态区分**）。
- 解锁瞬间复用 `pendingCelebration` → `CelebrationLayer`（`kind: 'badge'`），
  可跳过（沿用现有跳过机制，D-6 不回退）。

---

## 4. GSAP 钩子契约

GSAP 已在依赖里（`package.json`），现有用法散在各视图。状态机转场统一收口：

### 4.1 新文件 `composables/usePhaseTransition.js`

```js
/**
 * 阶段转场：旧阶段元素退场 → 新阶段元素入场，一条 timeline 编排。
 * @returns {{ transition(fromEl, toEl, direction: 1|-1): Promise<void> }}
 */
export function usePhaseTransition() {}
```

规范：
- 入场：`gsap.fromTo(toEl, { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.35, ease: 'back.out(1.6)' })`；
  退场对称（`y: -16`，duration 0.2）。方向参数供 `GOTO` 往回跳时镜像。
- `document.documentElement.dataset.motion === 'reduced'`（settings store 已写入）时
  **不建 timeline**，直接 resolve——转场必须是纯增强，动画被禁用时状态机行为完全一致。
- reward 阶段的星星爆发沿用现有 `StarBurst`/`CelebrationLayer`，不在本 composable 内重复。
- timeline 必须在组件卸载时 `kill()`（转场中路由跳走不能泄漏）。
- 转场期间给容器上 `aria-busy="true"`，结束移除。

### 4.2 各阶段专属动画点（可选增强，非验收项）

| phase | 钩子 | 说明 |
|---|---|---|
| intro | 拼音气泡逐字 stagger 入场 | `enter([...], { stagger: 0.05 })` 风格，参考 math 侧 `useFeedback.enter` |
| trace | 示范笔画时田字格轻微 scale 呼吸 | 提示"现在看演示" |
| reward | 掌握度等级条从旧值补间到新值 | `gsap.to` 数值补间 + `onUpdate` 写文本 |

---

## 5. 验收清单（供子代理 #3 的 acceptance-log 引用）

| # | 验收项 | 验证方式 |
|---|---|---|
| S1 | `/learn/:char` 进入后五阶段自动衔接，全程无需回退浏览器 | smoke：Playwright 走完一个字的闭环 |
| S2 | 每阶段可跳过；跳过不记学习事件（`traced`/`quizRight` 不增） | 单测 + smoke |
| S3 | 同一笔错 3 次触发示范，示范后可继续写完 | smoke（用错误笔画模拟）|
| S4 | 描红键盘替代与 Esc 跳过在状态机内仍可用；阶段切换焦点移动 + live region 播报 | 手动键盘走查 |
| S5 | 徽章 ≥10 枚，解锁弹层可跳过，老存档导入不炸（`badges` 回落） | 单测 `migrate` + smoke |
| S6 | `useCharFlow` 转移纯函数单测全绿（合法转移/非法 GOTO/换字 RESET） | Vitest |
| S7 | `data-motion="reduced"` 下无 GSAP 转场但流程完整 | smoke 断言 |

## 6. 文件清单（新增/修改）

```
apps/literacy-app/src/
├── composables/useCharFlow.js        [新增] 状态机（纯逻辑 + refs）
├── composables/usePhaseTransition.js [新增] GSAP 转场收口
├── data/badges.js                    [新增] 徽章定义（数据驱动）
├── stores/progress.js                [修改] badges/flowsDone/completeFlow/checkBadges + migrate 回落
├── components/HanziStrokeBox.vue     [修改] autoDemoAfter + stroke-demo（§2）
└── views/CharDetailView.vue          [修改] 阶段分区 + 进度点 + 深链（§1.4）
```

冲突提示：子代理 #5（500 字/懒加载）会动 `data/characters.js` 与路由懒加载，
与本任务文件集合**无交集**，可并行；`stores/progress.js` 若两边都改，
以本契约的字段名为准合并。
