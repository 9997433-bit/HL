# Round 5B · Play Layer 架构契约

> Model slug: claude-fable-5（Round 5B 子代理 #1 · `cursor/r5b-arch-contracts-9f67`）
> 基线：`cursor/openmoji-integration-9f67` @ Round 5 闭合（`check:round5` 12/12）
> 性质：**只定契约与文件路径约定，不含实现**。功能由子代理 #4–#9 按本契约落地。
> 关联：`ROUND5B-BRIEF.md`、`ROUND5B-ACCEPTANCE.md`、`scripts/check-round5b.mjs`、
> `literacy-architecture.md`、`math-architecture.md`

---

## 0. 总原则（对所有 Play Layer 交付生效）

1. **探针即契约**。`scripts/check-round5b.mjs` 已存在且路径写死，本文档所有文件路径
   与命名以探针能匹配为准，禁止另起路径再回头改探针。
2. **数据驱动**。台词、剧情、任务定义、游戏注册一律放 `data/*.js` 纯数据文件，
   组件只渲染，方便脚本校验与后续扩量。
3. **reduced-motion / 可跳过是红线**。所有新增动画必须读取既有降级开关：
   识字 `<html data-motion>`（`stores/progress.js#applyAppearance`）、
   数学 `utils/motion.js#reducedMotion()`。庆祝一律走既有可跳过的庆祝层。
4. **不破坏 Round 5 门禁**。`data/games.js`、`data/modules.js` 等被 `check:round5`
   读取的文件**只加字段不删字段**；合并前 `npm run check:round5` 必须仍 12/12。
5. **跨 App 共享代码只进 `shared/`**，两 App 均已配置 `@shared` 别名
   （`apps/*/vite.config.js`）。共享代码不得 import 任何 App 内部路径；
   App 相关能力（音效、语音、动效开关）以适配器参数注入。
6. **存储向后兼容**。识字主存档键 `happy-literacy:v1` 的 `migrate()` 已经很厚，
   本轮新增持久化一律用**独立 localStorage 键**，不往主存档里塞新顶层字段
   （P4 的一次性信号除外，它不持久化）。

---

## 1. 契约一 · 每日冒险 store（识字 P1）

### 1.1 文件路径

| 文件 | 角色 | 所有者 |
|---|---|---|
| `apps/literacy-app/src/stores/dailyQuest.js` | Pinia store，唯一状态源（探针 P1 读取此路径） | #4 |
| `apps/literacy-app/src/components/DailyQuestCard.vue` | 首页「今日冒险」卡片 UI | #4 |
| `apps/literacy-app/src/views/HomeView.vue` | 在 hero 与单元地图之间插入一个 `<section>` 挂载卡片 | #4（仅此一处改动） |

### 1.2 任务模型

每天固定 **3 个槽位**，覆盖简报里的四类候选（学新字 / 复习 / 绘本或成语 / 小游戏）：

| 槽位 | type | 目标（goal） | 完成判定数据源 |
|---|---|---|---|
| 1 | `learn` | 学 `min(3, dailyNewLimit || 3)` 个新字 | `progress.newCharsToday` |
| 2 | `review` | 完成 5 次答题/描红（当日无到期卡时目标降为 3） | 当日 `quizRight + quizWrong + traced` 增量 |
| 3 | 轮换：`story`（绘本）/ `idiom`（成语）/ `game`（小游戏） | 读完 1 本 / 读 1 条 / 玩 3 局 | `booksFinished` / `idiomsSeen` / `game.rounds` 增量 |

- 槽位 3 按 `dateKey` 的天序号 `% 3` 轮换，保证一周内三类都出现。
- 任务对象形状（store 内部与 UI 共用）：

```js
{
  id: 'learn',            // learn | review | story | idiom | game
  title: '学 3 个新字',    // 展示文案，来自 store 内常量表
  emoji: '✏️',
  goal: 3,
  progress: 1,            // 实时进度，clamp 到 goal
  done: false,
  doneAt: null            // 时间戳，首次达成时写入
}
```

### 1.3 完成判定：基线快照 + 派生，不改动业务视图

**禁止**在 LearnView / BookReadView / 游戏视图里手动调 `dailyQuest.noteXxx()`。
完成状态一律从 `useProgressStore` 的既有 computed **派生**：

- 每天第一次进入应用时，store 记录一份基线快照
  `base = { quizRight, quizWrong, traced, booksFinished, idiomsSeen, gameRounds }`。
  数据源只用 progress 的**已导出**成员：`badgeStats.traced`、`booksFinished`、
  `idiomsSeen`、`game.rounds`；quiz 两项由扁平视图 `chars` 汇总
  （`quizTotals` 未导出，禁止为此改 progress.js 的导出面）；
- 任务进度 = 当前值 − 基线值（`learn` 槽直接读 `newCharsToday`，天然按日归零）；
- 这样 P1 子代理的改动面收敛在 3 个文件内，与 #5/#6/#7 零冲突。

### 1.4 持久化与 API

- localStorage 键：`happy-literacy:daily-quest:v1`，形状
  `{ dateKey: 'YYYY-MM-DD', base: {...}, doneAt: { learn: ts|null, ... }, celebratedAt: ts|null }`。
  日期翻转（`dateKey` 不等于今天）时整体重置。写入失败静默（同主存档策略）。
- store 导出面（冻结，UI 只允许用这些）：

```js
export const useDailyQuestStore = defineStore('dailyQuest', ...)
// state/getter
tasks            // computed: 上述 3 任务数组（含 title/emoji/goal/progress/done）
completedCount   // computed: 0..3
allDone          // computed: completedCount === 3
// action
refresh()        // 校验 dateKey，翻天则重置基线；App 挂载与 visibilitychange 时调用
claimCelebration() // allDone 且未庆祝过 → 标记 celebratedAt 并返回 true（幂等）
```

### 1.5 奖励与庆祝

- `allDone` 首次达成：`DailyQuestCard` 调 `claimCelebration()`，成功后调
  `progress.grantDailyQuestBonus()` —— 这是**本契约要求在 `stores/progress.js`
  追加导出的唯一新函数**（内部 `addStars(3) + addXp(15) + celebrate({ kind: 'daily-quest', ... })`），
  庆祝复用既有 `CelebrationLayer`（天然可跳过）。
- UI 勾选框为**只读指示器**（`role="checkbox"` + `aria-checked` + `disabled` 语义），
  完成靠真实学习行为驱动，不提供手动打勾。

### 1.6 探针对齐（P1）

探针读 `HomeView.vue + stores/dailyQuest.js + composables/useDailyQuest.js` 中的
`dailyQuest|今日冒险|tasks+completed` 关键词。本契约用 store 方案，
`composables/useDailyQuest.js` **不创建**。

---

## 2. 契约二 · 统一 `useFeedback`（P3，兼 P6 接口）

### 2.1 现状与决策

数学已有 `apps/math-app/src/composables/useFeedback.js`（GSAP：
`pop/correct/wrong/burst/flyStar/enter/countTo/prefersReducedMotion`），识字没有。
**决策：核心逻辑上收到 `shared/`，两 App 各留一个薄绑定文件，数学现有调用方零改动。**

### 2.2 文件路径

| 文件 | 角色 | 所有者 |
|---|---|---|
| `shared/composables/useFeedback.js` | 唯一实现：`export function createFeedback(adapters)` | #6 |
| `apps/math-app/src/composables/useFeedback.js` | 薄绑定：注入数学 sfx/motion，**导出面与现状完全一致** | #6 |
| `apps/literacy-app/src/composables/useFeedback.js` | 薄绑定：注入识字 sfx/motion | #6 |

薄绑定形如（示意，非实现）：

```js
// apps/literacy-app/src/composables/useFeedback.js
import { createFeedback } from '@shared/composables/useFeedback.js'
import { sfx } from '@/utils/audio.js'
import { useProgressStore } from '@/stores/progress.js'
export function useFeedback() {
  return createFeedback({ sfx, reducedMotion: () => /* data-motion === 'reduced' */ })
}
```

### 2.3 适配器契约

```js
createFeedback({
  sfx,             // 必填：{ correct(opts?), wrong(), star(), combo?(), tap?() }
  reducedMotion,   // 必填：() => boolean
  haptics,         // 选填：(pattern: number|number[]) => void；缺省用 navigator.vibrate 并做存在性守卫
})
```

- `shared/composables/useFeedback.js` 只允许依赖 `gsap`（两 App 均已打包）与浏览器 API，
  **禁止** import 任一 App 的内部模块。
- GSAP 全部动画在 `reducedMotion()` 为真时直接 return（沿用数学版行为）。

### 2.4 API 面（冻结）

保留数学版八个成员不改签名；新增两个：

| 成员 | 签名 | 说明 |
|---|---|---|
| `pop` | `(target, { scale })` | 点按弹跳 |
| `correct` | `(target, { sound = true, streak = 0 })` | **新增 `streak` 透传给 `sfx.correct({ streak })`**（见 §6），动画不变 |
| `wrong` | `(target, { sound = true, haptic = true })` | **新增震动降级**：动画被 reduced-motion 关掉时仍触发 `haptics([60, 40, 60])` |
| `burst` | `(target, { count, colors })` | 星星粒子（DOM，自动回收） |
| `flyStar` | `(from, toSelector, { onArrive })` | 飞星到 `[data-star-counter]` |
| `enter` | `(targets, { stagger, y, delay })` | 入场错落 |
| `countTo` | `(obj, key, value, { duration })` | 数字滚动 |
| `prefersReducedMotion` | `() => boolean` | 透出注入的开关 |
| `streakPulse` **新增** | `(target, streak)` | 连对 ≥3 时的节拍强化视觉（缩放脉冲随 streak 加强，封顶 streak 7） |
| `buzz` **新增** | `(pattern)` | 直接触发震动，供游戏自定义时刻使用；无 vibrate API 时空操作 |

### 2.5 最低接线要求（P3 探针：composable 存在 + 全仓 ≥3 处引用）

| App | 场景 | 文件 | 最低要求 |
|---|---|---|---|
| 数学 | Quiz | `components/QuizShell.vue` | 已在用，改走薄绑定后行为不变 |
| 识字 | Quiz | `views/ListenGameView.vue` | 答对 `correct+burst`、答错 `wrong` 各 1 处 |
| 识字 | 写字 | `views/CharDetailView.vue`（或其描红子组件 `HanziStrokeBox.vue`） | 一笔写对 `pop`、整字完成 `burst` |
| 识字 | 游戏 | `views/MazeGameView.vue` / `MemoryGameView.vue` / `SpotGameView.vue` 任一 | ≥1 处 |

---

## 3. 契约三 · 吉祥物组件边界（P2）

### 3.1 角色与边界划分

| 角色 | 组件（保持现路径） | 边界 |
|---|---|---|
| 识字·墨墨 | `apps/literacy-app/src/components/MascotCompanion.vue` | **纯展示+单点交互**：props `mood/say/size/speakOnTap/bubbleSide`，点按 `sfx.tap + react + speak(say)`。不感知路由、不读 store。**本轮不改此文件。** |
| 数学·MascotBot | `apps/math-app/src/components/MascotBot.vue` | 纯展示：props `mood/size`。**本轮允许的唯一扩展**：新增可选 `say`（视觉气泡）与点按 tap 音效；不接 TTS（数学无 speech util）。 |

### 3.2 常驻 dock 包装层（新增）

「常驻陪跑」的定位、台词选择、免打扰逻辑收敛到包装组件，视图只挂一行：

| 文件 | 角色 | 所有者 |
|---|---|---|
| `apps/literacy-app/src/components/MascotCompanionDock.vue` | 固定角落 dock：内部渲染 `MascotCompanion`，按 `route.name` + 场景键从台词表取词 | #5 |
| `apps/literacy-app/src/data/mascotLines.js` | 墨墨台词表（纯数据） | #5 |
| `apps/math-app/src/data/mascotLines.js` | MascotBot 鼓励语表（纯数据） | #5 |

> **命名即探针**：P2 探针对视图源文件做 `/MascotCompanion|MascotBot/` 正则匹配。
> 包装组件必须叫 `MascotCompanionDock`（含 `MascotCompanion` 子串），
> 视图 import 它即可命中探针；**禁止**改名成 `MascotDock` 之类。

台词表形状：

```js
// data/mascotLines.js
export const MASCOT_LINES = {
  home:  { idle: ['今天想先玩哪个？'], praise: ['你真棒！'] },
  learn: { idle: ['一笔一画慢慢来。'], ... },
  games: { ... }, books: { ... }, idioms: { ... },
}
```

### 3.3 视图接线矩阵（探针 P2 要求下列 7 文件中 ≥5 出现组件名）

| 文件 | 现状 | 本轮要求 | 所有者 |
|---|---|---|---|
| `apps/literacy-app/src/views/HomeView.vue` | 无（墨墨只在 App.vue 休息弹窗） | 挂 `<MascotCompanionDock />` | #5 |
| `apps/literacy-app/src/views/LearnView.vue` | 无 | 挂 dock | #5 |
| `apps/literacy-app/src/views/GamesView.vue` | 无 | 挂 dock（与 #8 街机改造并存，见 §7 冲突矩阵） | #5 |
| `apps/literacy-app/src/views/BooksView.vue` | 无 | 挂 dock | #5 |
| `apps/literacy-app/src/views/IdiomsView.vue` | 无 | 挂 dock | #5 |
| `apps/math-app/src/modules/home/HomeView.vue` | 已引用 MascotBot | 保持 | — |
| `apps/math-app/src/modules/daily/DailyView.vue` | 无 | 挂 `<MascotBot :mood>`（随答题状态切换） | #5 |

### 3.4 行为契约

- dock 固定视口角落（识字右下），`z-index` 低于弹窗/庆祝层，**不遮挡主操作区**：
  移动端宽 ≤480px 时缩到 64px 且气泡默认收起。
- 点按 = 唯一交互：换一句台词 + `speak()`（识字）/ tap 音效（数学）。
- a11y：整体是一个 `<button>`，`aria-label` 含当前台词（MascotCompanion 已实现，dock 沿用）；
  气泡文案变化不用 aria-live 轰炸，读屏以点按为准。
- reduced-motion：呼吸浮动 / 眨眼定时器不启动（在 dock 层判断后以 prop 或 CSS 控制）。
- App.vue 休息弹窗里的墨墨用法**保持不变**，dock 与其互不感知。

---

## 4. 契约四 · 地图叙事状态（P4）

### 4.1 数据文件

| 文件 | 形状 | 所有者 |
|---|---|---|
| `apps/literacy-app/src/data/unitStories.js` | `export const UNIT_STORIES = { [unitId]: { tease, unlockLine, emoji } }` | #7 |
| `apps/math-app/src/data/modules.js` | 每个星球**新增** `story: { tease, unlockLine }` 字段（只加不删，`check:round5` 安全） | #7 |

- `tease`：锁定时那句剧情（≤20 字，例：「墨墨说：山那边住着会飞的字。」）；
- `unlockLine`：解锁瞬间的播报词（同时作为 aria-live 文案）。

### 4.2 解锁状态与一次性信号

解锁**判定**沿用既有唯一真源，不新建平行状态：

- 识字：`progress.unlockedUnits`（上一单元 60% 规则不变）；
- 数学：`progress.isModuleUnlocked(id)`（`starsToUnlock` 规则不变）。

解锁**瞬间**需要一次性信号驱动过渡动画：

- 数学已有 `progress.takeUnlock()`，沿用；
- 识字在 `stores/progress.js` **新增对齐的最小 API**（本契约允许对 progress.js 的
  第二处、也是最后一处追加）：

```js
pendingUnitUnlock   // ref<string|null>，unlockedUnits 的 watcher 检测 false→true 时写入 unitId
takeUnitUnlock()    // 读取并清空，返回 unitId|null（语义与数学 takeUnlock 一致）
```

不持久化：刷新丢失只损失一次动画，不损失任何进度。

### 4.3 渲染契约

| 状态 | 识字 LearnView 单元页 | 数学 HomeView 星球 |
|---|---|---|
| 锁定 | 灰显（现有 🔒 保持）+ `tease` 一句话 + 解锁条件（现有文案保持） | 灰显（现有）+ `story.tease` 一句话 |
| 解锁瞬间 | `takeUnitUnlock()` 命中 → 过渡动画 + `unlockLine` | `takeUnlock()` 命中 → 过渡动画 + `story.unlockLine` |
| 已解锁 | 现状不变 | 现状不变 |

过渡动画契约：GSAP timeline **≤1.2s**（锁图标碎裂/星球点亮 + 文案浮现），
reduced-motion 下**跳过动画**，直接切换状态并用既有 `.sr-only` aria-live 区播报 `unlockLine`。

### 4.4 探针对齐（P4）

探针在 `LearnView.vue + math HomeView.vue` 里找
`/unlock|locked|剧情|故事|章节|chapterStory|planetStory/i`——现状已命中 `unlocked`，
本契约的 `tease/unlockLine` 让「剧情」从探针词变成真体验。

---

## 5. 契约五 · 街机大厅组件树（P5）

### 5.1 组件树（识字 `GamesView`）

```text
views/GamesView.vue                      ← 只保留布局与数据装配（#8）
├── <MascotCompanionDock/>               ← §3，#5 所有
├── header.game-hall__marquee            ← 街机跑马灯标题（CSS 动画；reduced-motion 静止）
├── ul.games-grid                        ← 响应式卡片网格（≥2 列，移动端 1 列）
│   └── <ArcadeCabinetCard v-for="g in GAMES"/>   × N
│       ├── .arcade-card__neon           ← 霓虹描边（box-shadow 呼吸；纯装饰 aria-hidden）
│       ├── <OpenMojiIcon> 招牌 emoji
│       ├── h3 游戏名 + p.arcade-card__howto（一句话玩法）
│       ├── .arcade-card__stats          ← 能力标签 trains + 战绩（progress.game / 各游戏局数）
│       └── RouterLink「开始」           ← 整卡可点，键盘可达
└── footer.game-hall__hint               ← 「已学 N 字，字越多越好玩」（现有文案迁移）
```

| 文件 | 角色 | 所有者 |
|---|---|---|
| `apps/literacy-app/src/views/GamesView.vue` | 大厅骨架改造 | #8 |
| `apps/literacy-app/src/components/ArcadeCabinetCard.vue` | 单卡组件（新增） | #8 |
| `apps/literacy-app/src/data/games.js` | 注册表扩展字段（见下） | #8 |

### 5.2 数据收敛：`data/games.js` 是唯一真源

现状 GamesView 内联了一份 GAMES 数组，与 `data/games.js` 注册表重复。本轮**合并**：

- `data/games.js` 每项扩展为
  `{ id, name, route, skill, view, emoji, howTo, trains, desc, color }`
  （既有五字段 `id/name/route/skill/view` **不得改名/删除**，其中 `id` 与 `route`
  被 `check:round5` H6 逐项校验；`howTo` 即「一句话玩法」）；
- **纯数据红线**：`check:round5` 用 Node 直接 `await import` 该文件，
  因此它必须保持零依赖纯数据模块——禁止 `@/` 别名、Vue、浏览器 API；
  `color` 只能存 CSS 变量字符串（如 `'var(--mint-400)'`），由组件消费；
- GamesView 删除内联数组，改 `import { GAMES } from '@/data/games.js'`；
- 新游戏未来只改 games.js + router，大厅自动长出新柜子。

### 5.3 探针与红线

- P5 探针在 GamesView 源码找 `/arcade|街机|neon|game-hall|games-grid/i`——
  按 §5.1 的 class 命名（`game-hall__*`、`games-grid`、`arcade-card__*`）天然命中。
- 霓虹/跑马灯是**纯装饰**：信息（名称、玩法、战绩）不得只靠霓虹色传达；
  暗色 `night` 主题下对比度仍须过 AA；reduced-motion 时霓虹静止为单层描边。

---

## 6. 契约六 · 答对音效节奏接口（P6，供 #9 与 #6 对接）

P6 由 #9 落地，但签名在此冻结，避免 #6（useFeedback）与 #9 相互等待：

| 文件 | 变更 | 所有者 |
|---|---|---|
| `apps/literacy-app/src/utils/audio.js` | `sfx.correct(opts?)` 接受 `{ streak = 0 }`：每连对 1 题整体音高 +1 半音（封顶 +7）；`streak % 3 === 0 && streak > 0` 时叠播 combo 型琶音 | #9 |
| `apps/math-app/src/utils/sound.js` | 同上；已有 `CUES.combo` 直接复用 | #9 |
| 接线 | 识字 `ListenGameView`（已维护 streak）≥1 条链路；数学 `QuizShell`（progress 已有 combo 计数）≥1 条链路。调用方式统一走 `useFeedback().correct(el, { streak })` | #6/#9 |

- 兼容：`sfx.correct()` 无参调用行为与现状完全一致（streak=0 → 原始琶音）。
- 探针 P6 在两 App 的 sfx/useFeedback 源码找 `/streak|combo|pitch|音高|连对/i`。
- 答错不做节奏惩罚音（保持现有柔和下行小二度，低龄挫败感保护）。

---

## 7. 文件所有权与冲突矩阵

同文件多子代理触碰点（合并顺序按左→右）：

| 热点文件 | 触碰者 | 隔离规则 |
|---|---|---|
| `literacy views/HomeView.vue` | #4（插 DailyQuest section）、#5（挂 dock） | #4 只在 hero 之后插一个新 `<section>`；#5 只在模板根末尾加一行 dock。互不改对方区域 |
| `literacy stores/progress.js` | #4（`grantDailyQuestBonus`）、#7（`pendingUnitUnlock/takeUnitUnlock`） | 都是**纯追加**：函数体 + return 导出各一处，不改既有行 |
| `literacy views/GamesView.vue` | #8（街机改造）、#5（挂 dock） | #8 先合；#5 的 dock 是模板尾部单行，rebase 成本≈0 |
| `literacy views/LearnView.vue` | #7（叙事+过渡）、#5（挂 dock） | 同上，#7 先合 |
| `literacy utils/audio.js` | #9 | 独占 |
| `math utils/sound.js` | #9 | 独占 |
| `math composables/useFeedback.js` | #6 | 独占（改为薄绑定，导出面不变，QuizShell 等调用方零改动） |
| `math data/modules.js` | #7 | 独占（只加 `story` 字段） |
| `math components/MascotBot.vue` | #5 | 独占（只加可选 `say` 气泡 + tap 音效） |
| `literacy data/games.js` | #8 | 独占（只加字段） |

新建文件（零冲突）：`stores/dailyQuest.js`、`components/DailyQuestCard.vue`、
`components/MascotCompanionDock.vue`、`components/ArcadeCabinetCard.vue`、
`data/mascotLines.js`（两 App 各一）、`data/unitStories.js`、
`shared/composables/useFeedback.js`、`literacy composables/useFeedback.js`。

---

## 8. 契约 → 门禁映射

| 契约 | check:round5b 探针 | 负责子代理 | 回归红线 |
|---|---|---|---|
| §1 每日冒险 store | P1：`stores/dailyQuest.js` + HomeView 关键词 | #4 | `check:round5` L 系不退化 |
| §2 useFeedback | P3：composable 存在 + ≥3 处引用 | #6 | 数学既有 QuizShell 动画行为不变 |
| §3 吉祥物边界 | P2：7 视图中 ≥5 命中组件名 | #5 | App.vue 休息弹窗不动 |
| §4 地图叙事 | P4：LearnView/math HomeView 关键词 | #7 | 解锁规则数值不变（60% / starsToUnlock） |
| §5 街机大厅 | P5：GamesView class 探针 | #8 | `data/games.js` 旧字段保留（check:round5） |
| §6 节奏音效 | P6：sfx/useFeedback 关键词 | #9 | `sfx.correct()` 无参行为不变 |

全部合并后：`npm test` → `npm run check:round5` → `npm run check:round5b` →
`npm run test:round3`，并回填 `.agent_workspace/acceptance-log-round5b.md`。

---

## 9. 明确不做（Out of scope）

- 不新增路由、不改 `router/index.js`（两 App）；
- 不动 FSRS / 掌握度 / 解锁阈值等学习算法数值；
- 不引入新 npm 依赖（GSAP、Pinia、OpenMoji 资产已够用）；
- 不在本轮实现「每日冒险」的家长侧配置项（目标数暂用 §1.2 规则，家长面板扩展留给后续轮次）；
- 吉祥物不做拖拽、不做常驻语音自动播报（只响应点按，避免打扰与读屏噪音）。
