# Round 16 架构 · 体验密度反超（认步补全 · 数学「学」 · 人格与可解释）

> 岗位：r16-arch-contracts（子代理 #1）
> 分支：`cursor/r16-arch-contracts-9f67`（基于 `cursor/r16-orchestration-9f67`）
> 本文是 H2 / H4 / H5 / H6 / H7 各实现岗的共同契约。改契约先改本文档。
> 已随本文落地两个数据层桩：`apps/literacy-app/src/data/char-intro.js`（H2 解析器，
> 已过 Node 全库自验）与 `apps/math-app/src/data/learn-demos.js`（H4 注册表空壳）。
> UI 一律没做——那是实现岗的活。

## 0. 一页话总览

R15 把「玩认练写说」跑通了，但四块体验还是「有骨头没肉」：

1. **认步**：有字源的 808 字很精彩，其余 1012 字进「认」只有一行释义（H2 要补的洞）；
2. **数学「学」**：星球刷题强，但孩子刷题前看不到「为什么 3+2=5」的演示（H4）；
3. **应用题**：错了只有一句 hint，没有「图示 + 分步 + 再来一道」的剖析（H5）；
4. **可解释**：墨墨/小算台词不看情境（H6），家长报表有数字没结论（H7）。

四块共用一个设计原则：**数据层同步纯函数、永不 null；UI 层按需 chunk、可跳过、
reduced-motion 完整可用**——和 R15 的 `getCharPlay` 同一套打法。

## 1. 认步无字源舞台契约（H2 · r16-literacy-intro-fallback 岗）

### 1.1 数据解析器（架构岗已落地：`apps/literacy-app/src/data/char-intro.js`）

```js
import { getCharIntro } from '@/data/char-intro.js'
const intro = getCharIntro(char, { words })   // 同步、纯函数、永不返回 null
```

```js
/**
 * @typedef {Object} CharIntro
 * @property {string} char
 * @property {'radical'|'parts'|'word'} mode  三选一讲解模式
 * @property {string} narration   开场讲解词，≤40 字口语，TTS + aria-live 用
 * @property {string} emoji       主图标（取 char-index 卡片图标，OpenMoji 渲染）
 * @property {string} pinyin
 * @property {{glyph,name,hint,meaning,siblings:string[]}} radical
 *           部首讲解块，任何模式下都非空（radical 模式的主角，其他模式当脚注）
 * @property {string[]} [parts]   mode==='parts' 时的零件序列（emoji/字形），≥2 个
 * @property {Array<{w,p}>} [words] mode==='word' 时的组词（来自调用方，≤3 条）
 * @property {'char-intro'} source
 */
```

**模式选择规则（决定性，`hashSeed(char)` 做种，无随机）：**

1. 候选池按可用性组装：`radical` 永远在池里；富剧本里该字是 `drag-parts`
   且 `props.parts.length ≥ 2` → `parts` 入池；调用方传了 `words`（≥1 条）→ `word` 入池。
2. `mode = 候选池[hashSeed(char) % 池长]`。同一个字、同样的入参，永远同一模式。
3. 兜底链：`parts` 数据坏了退 `word`，`word` 没词退 `radical`，`radical` 查不到
   部首资料就用「字形本身 + 笔画数」凑一块讲解——**任何输入都拿得到可讲的东西**。

**words 入参约定**：CharDetailView 本来就 `loadCharacter(char)` 拿单元详情
（`item.words`），把它透传即可；详情没到时不传，解析器自然落到 radical/parts。
组件**mount 时解析一次就冻结**，详情晚到不换模式——孩子看到一半换台词是事故不是升级。

### 1.2 舞台组件契约（实现岗新建：`src/components/CharIntroStage.vue`）

> 文件名只能是 `CharIntroStage.vue` 或 `IntroFallbackStage.vue`（探针只认这两个名字
> + CharDetailView），本契约定 **CharIntroStage.vue**。

```
props:  { char: String（必填）, words: Array（可选，透传给 getCharIntro）, size?: Number }
emits:  played()   —— 讲解播完（或用户点「跳过」）；CharDetailView 拿它记 done.intro
内部：  const intro = getCharIntro(props.char, { words: props.words })
标记：  <script> 里可执行代码导出 export const ROUND16_H2 = 'char-intro-stage'
```

三种模式的舞台内容（全部 OpenMoji + 程序化 SVG/GSAP，禁位图）：

| mode | 演什么 | 交互 |
|---|---|---|
| `radical` | 部首 glyph 放大登场 → hint 一句 → 同部首兄弟字（siblings ≤3）逐个亮相 → 目标字落位 | 点兄弟字听读音；「跳过」常驻 |
| `parts` | 零件 emoji 依次飞入 → 合体成目标字（复用玩步 drag-parts 的 parts 数据，但这里是**看**不是拖） | 点一下推进一步 |
| `word` | 目标字 + 组词逐条弹出并朗读（词条自带拼音），字在词里高亮 | 点词条重听 |

硬要求（验收线）：

- narration 走 `utils/speech.js` 朗读 + `aria-live` 屏显；
- `reduceMotion` 下不建 GSAP 时间线，改静态分帧（点击推进），交互照常、`played` 照发；
- 「跳过讲解」按钮常驻可见，点了立即 `played`；
- 组件按需加载：CharDetailView 里 `defineAsyncComponent(() => import('@/components/CharIntroStage.vue'))`，与 EtymologyStage 同款。

### 1.3 CharDetailView 接线（同岗）

「认」步面板改成显式二分支（探针的 wired 正则要看到 `hasOrigin` 分支 + 组件名）：

```html
<template v-else-if="phase === 'intro'">
  <div class="intro">
    <div v-if="hasOrigin" class="intro__origin">
      <EtymologyStage :char="item.char" :size="196" autoplay @played="onOriginPlayed" />
      …（现状不动）
    </div>
    <div v-else class="intro__origin">
      <!-- ROUND16_H2 注释不算数，标记要在 CharIntroStage 的 script 里 -->
      <CharIntroStage :char="item.char" :words="item.words" @played="onOriginPlayed" />
    </div>
    …听读音按钮、释义、笔画（现状保留，两个分支都在下面）
  </div>
</template>
```

- `onOriginPlayed` 原样复用（`done.intro = true` + `scheduleAdvance('listen')`）；
- `introIdle` 18s 干等自动往下走的机制**不许拆**；
- 底部「这个字的来历」折叠卡仍只在 `hasOrigin` 时出现，无字源字不需要第二入口。

### 1.4 抽查口径

探针只查标记和接线；成功体验按 BRIEF 抽查冷门字（u21+ 无 etymology 的字，如
u99 生僻字）——进「认」必须有舞台在动/可点，不是一行 meaning。实现岗自验脚本
建议：Node 里对全部 `!hasEtymology(char)` 的字跑 `getCharIntro`，断言 0 空洞
（`char-intro.js` 已带 `findIntroHoles()`，直接调）。

## 2. 数学 LearnDemo 协议：实物→图形→算式（H4 · r16-math-learn-demo 岗）

### 2.1 现状与打法

`visualDemos.js` + `VisualMathDemo.vue` 已经是标准的三段播放器
（object → visual → equation，带跳过/重播/逐步），且 8 条 demo 各挂了 `skill`。
**H4 不另造播放器**：新建注册表 `learn-demos.js` 把「技能 → 演示」补到 ≥12，
播放仍交给 `VisualMathDemo`。

### 2.2 注册表契约（架构岗已放空壳：`apps/math-app/src/data/learn-demos.js`）

```js
/**
 * @typedef {Object} LearnDemo
 * @property {string} skillId    curriculum.js SKILLS 的 id —— 探针数的就是这个字段名，
 *                               每条必须字面量写 `skillId:`，不许解构/循环生成糊过去
 * @property {string} id         demo id（/visual-demos?demo= 路由参数，全表唯一）
 * @property {string} title
 * @property {string} subtitle
 * @property {Object} object     实物段  { emoji, count|groups, removed?, label }
 * @property {Object} visual     图形段  { groups, crossedGroup?, fraction?, label }
 * @property {string} equation   算式段
 * @property {string[]} narration 三句起：实物一句、图形一句、算式一句
 */
export const LEARN_DEMOS = [ /* 实现岗填 ≥12 条 */ ]
export const ROUND16_H4 = 'learn-demo-registry'
learnDemoForSkill(skillId)  // → LearnDemo | null（唯一查询入口，调用方判 null 走「无演示」态）
countLearnDemos()           // 按 skillId 去重后的条数（探针备用口径）
```

- 已有 8 条 `VISUAL_DEMOS` **迁移进来挂 skillId**（counting→count-to-10、
  addition→add-within-10、subtraction→sub-within-10、compose-ten、
  comparison→compare-to-10、multiplication→mul-table、division→div-basic、
  fraction→shape-2d），`visualDemos.js` 改从 `learn-demos.js` re-export 保持旧引用不炸；
- 新增 ≥4 条补到 ≥12，优先：`add-carry-20`（凑十法：9+4 → 拆 4 成 1+3）、
  `sub-borrow-20`（破十法）、`pattern-abab`（实物排队 → 色块 → 「ABAB」）、
  `wp-combine`（部分+部分=整体的线段图）；还缺再上 `number-order` / `symmetry`；
- 数值全部写死在条目里（演示不是刷题，不需要随机），narration 每句 ≤20 字。

### 2.3 入口组件与接线（同岗）

```
SkillLearnDemo.vue（src/components/，async chunk）
props:  { skillId: String（必填）, compact?: Boolean }
emits:  done()  —— 演示播完或点「跳过演示」
内部：  const demo = learnDemoForSkill(props.skillId)；null 时渲染 null 并立即 done
        有 demo 时渲染 <VisualMathDemo :demo="demo" /> + 「跳过，直接刷题」按钮
```

接线两处（都是「先看 20 秒演示再刷题」的入口，不强制看）：

1. `/visual-demos` 页：picker 数据源换成 `LEARN_DEMOS`（页面零改动，条目变多）；
2. 技能落点：`skill-practice.js` 的 `practiceEntry()` 返回值加一个可选
   `demoTo`（`learnDemoForSkill(skill)` 非空时给 `/visual-demos?skill=<id>` 路由），
   SkillGraph / 星球页把它渲染成次按钮「📽 先看演示」。推荐排序、落点优先级
   **一个字不改**——演示是加项不是改道。

### 2.4 证据

`.agent_workspace/evidence/r16/learn-demo-registry.md`，每条一行
`- <skillId> · <title> · <equation>`（探针数 `^- \S+` 行，≥12）。

## 3. 应用题剖析面板 API（H5 · r16-math-wp-analysis 岗）

### 3.1 组件契约（新建：`apps/math-app/src/components/WpAnalysisPanel.vue`——探针认这个路径名）

```
props:  {
  question: Object,   // useQuestionRunner 当前题（text/equation/answer/unit/hint/visual）
  master:   Object,   // 母题元数据 { id, skill, tag, steps, emoji, scene }
  answered: Boolean,  // 是否已作答（决定得数遮不遮）
}
emits:  close()
        variant()    // 「再来一道同款」——父层用同一母题 make() 重生成，不在面板里出题
标记：  export const ROUND16_H5 = 'wp-analysis-panel'（script 可执行代码）
```

面板三段，从上到下：

1. **图示**：复用 `question.visual`（icon + groups + strike）的圆点/实物阵列渲染，
   把 WordProblemsView 里那块 `.visual` 模板抽成小组件 `WpVisual.vue` 两处共用；
2. **分步**：`analyzeProblem(master, question)` 产出的 steps 列表逐条展示 + 朗读，
   `answered=false` 时最后一步的得数打码（显示 `?`）——剖析教列式，不代答；
3. **变式入口**：按钮「换个数字再来一道」→ emit `variant`。

### 3.2 剖析数据推导（`wordProblems.js` 加薄薄一层）

```js
/**
 * @returns {Array<{say: string, math?: string}>} 2–4 步
 */
export function analyzeProblem(master, made)
```

- 母题可选新字段 `explain(made) => steps[]`：鸡兔同笼、相遇这类 CRAFTED 进阶题
  一道道手写（和母题住一起，改题面时顺手改剖析）；
- 没写 `explain` 的走通用推导：
  `[ {say:'先找题里的数字：…'}, {say: made.hint}, {say:'列式', math: made.equation}, {say:'算出得数', math: '… = ' + made.answer + made.unit} ]`
  ——`hint` 本来就是「为什么这样列式」的一句话，通用链路已经能讲明白一步题；
- 纯函数、Node 可跑、永不 null（explain 抛错/返回空也退通用链路）。

### 3.3 接线（WordProblemsView）

- 题面右上加「🔍 看剖析」按钮，**作答前/中随时可开**（BRIEF 措辞），不扣星
  （hint 扣星机制不动，剖析是另一个通道：看剖析不给本题记满分即可，口径由实现岗
  在现有 scoring 里就近实现并写注释）；
- `variant` 事件 → 用当前 `master.make()` 重新出一道压进队列，当前题跳过不记错。
- 面板 async chunk（`defineAsyncComponent`），reduced-motion 无时间线、逐步点看。

## 4. 学伴人格剧本契约（H6 · r16-mascot-parent-week 岗）

### 4.1 数据结构（两个 App 的 `mascotLines.js` 各自扩展，同一形状）

现有 `MASCOT_SCENES` 是「路由级」台词；R16 加「时刻级」剧本，二者并存：

```js
export const MASCOT_MOMENTS = {
  newChar:   (ctx) => trim([...]),  // 开学一个新字/新技能
  combo:     (ctx) => trim([...]),  // 连对 ≥3（ctx.combo）
  struggle:  (ctx) => trim([...]),  // 同一题连错 ≥2（安抚 + 给路子，不催）
  review:    (ctx) => trim([...]),  // 进复习/错题重做
  fatigue:   (ctx) => trim([...]),  // 本次会话 >10 分钟（劝休息，不加码）
  comeback:  (ctx) => trim([...]),  // 距上次学习 >3 天
  reward:    (ctx) => trim([...]),  // 结账领星星时刻
  goodbye:   (ctx) => trim([...]),  // 离开页面/收工
}
export function mascotMoment(moment, ctx = {}) // 查不到退 reward 组，永远有话说
export const ROUND16_H6 = 'mascot-moments'
```

- **阶段化**：每组 builder 拿 `ctx.stage`（识字 App 按 `learnedCount` 分
  `'starter' | 'grower' | 'master'` 三档，数学按 `stars`），同一时刻不同阶段说不同话——
  启蒙期多示范（「跟我一起读」），成长期多放手（「你先试，我看着」）；
- **量**：识字墨墨 ≥28 条、数学小算 ≥16 条（合计 ≥44 > 探针 40，留余量）；
  每条 8–30 字、口语、**不放 emoji**（TTS 会念出「笑脸」，沿用现有注释的约定）；
- `useMascotCoach` 加 `sayMoment(moment)`：解析 ctx（进度 store）→ 取一条
  （同一时刻内轮换，`hashSeed(moment + 次数)` 决定性）→ 交给现有 speak 链路。
  触发点由实现岗埋在 CharDetailView（newChar/combo/reward）、复习入口（review）、
  会话计时器（fatigue）——每个触发点一行 `sayMoment(...)`，别把判定逻辑散进视图。

### 4.2 红线

- 台词不许催氪、不许贬低（「怎么又错了」这类禁止）；疲劳时刻只能劝休息；
- 探针数的是**两个 mascotLines.js + useMascotCoach.js 里 ≥8 字的字符串**——
  凑数写进注释不算（strip 后才 grep），必须是可执行代码里的字面量。

## 5. 家长可解释周报数据结构（H7 · r16-mascot-parent-week 岗）

### 5.1 纯函数契约（两个 App 各一份：`src/utils/weeklyReport.js`——探针认这个路径）

```js
export const ROUND16_H7 = 'weekly-report'
/**
 * @typedef {Object} WeeklyReport
 * @property {string} rangeLabel        '8月22日 – 8月28日'
 * @property {{ text, kind: 'char'|'skill'|'none', targetId }} weakSpot
 *           本周弱项一句话。样例：
 *           识字：'「休」和「体」这周认混了 3 次，是最需要陪练的一个字。'
 *           数学：'「20以内退位减」这周错了 5 道，是最卡的一个技能点。'
 *           没有弱项时 kind:'none'，text 说人话（'这周状态很稳，没有明显卡点。'）
 * @property {Array<{ label, hint, to }>} suggestions  建议练习 ≤3，to 是路由对象，可点开练
 * @property {{ activeDays, newLearned, reviewed, correctRate }} stats
 */
export function buildWeeklyReport(snapshot, now = Date.now())
```

- **本地生成**：只吃进度 store 的持久化快照，不打网络；Node 可跑（单测直接喂快照）；
- 弱项判定（决定性，同快照同结论）：
  - 识字：`chars` 里近 7 天 `wrong` 次数最高的字；平手取复习拖最久（`lastAt` 最早）
    的；一个错都没有 → 看 `dueCount`（积压 >5 提「复习积压」），再没有 → `none`；
  - 数学：`wrongCountsBySkill(wrongBook)` 取最大（复用 skill-practice.js 现成函数），
    平手取 `SKILLS` 里 level 更低的（地基优先）；空错题本 → `none`；
- 建议 ≤3 条、每条**必须可点**：
  - 识字：`/learn/<char>`（重学）、`/games/listen?focus=<char>`（听音练）、
    含该字的绘本 `/books/<id>`（book-index 反查，查不到就少一条，不硬凑）；
  - 数学：直接 `practiceEntry({ id: skill })` 的 `to`（错题本/日冒险/星球三选一
    的既有逻辑），外加 `learnDemoForSkill` 非空时补一条「先看演示」——H4/H7 在这里接上。

### 5.2 UI 接线（两个 ParentView 各加一张「本周小结」卡，放在最顶上）

- 一句话（weakSpot.text）大字号，suggestions 渲染成 ≤3 个按钮，stats 一行小字；
- 家长闸门（现有 PIN/算术题闸）内展示，不新开路由；
- 「不用看懂图表也知道这周练什么」是验收体验线——卡片里**不许放图表**，就是话和按钮。

## 6. 包体与按需加载边界

| 产物 | 打包位置 | 预算（源码） |
|---|---|---|
| `char-intro.js` | 学习路由 chunk（与 char-play 同仓，同步 import） | ≤8KB |
| `CharIntroStage.vue` + 三模式渲染 | 独立 async chunk（defineAsyncComponent） | ≤14KB |
| `learn-demos.js`（≥12 条） | visual-demos 路由 chunk；`skill-practice.js` 若要引它判 demoTo，改为只引 **id 清单**（新导出 `LEARN_DEMO_SKILLS` 数组，≤300B）避免把整表拖进主包 | ≤14KB |
| `SkillLearnDemo.vue` | async chunk | ≤8KB |
| `WpAnalysisPanel.vue` + `WpVisual.vue` | word-problems 路由内 async chunk | ≤12KB |
| `analyzeProblem` + 各 `explain` | 随 `wordProblems.js`（本来就在 word-problems chunk） | ≤6KB 增量 |
| `MASCOT_MOMENTS` ×2 | 主包（纯文本） | 每 App ≤6KB 增量 |
| `weeklyReport.js` ×2 | parent 路由 chunk | 每份 ≤6KB |

- 新依赖：**零**。GSAP、OpenMoji 管线、speech/sfx/feedback 全部复用现有；
- 禁止：首页/字表页 import `char-intro.js`；数学主包 import `LEARN_DEMOS` 全表；
  ParentView 之外 import `weeklyReport.js`。

## 7. 探针对齐表（文件名一个都不许写错）

| 门槛 | 探针 grep 的确切路径 | 标记 |
|---|---|---|
| H2 | `apps/literacy-app/src/components/CharIntroStage.vue`（或 IntroFallbackStage.vue）+ CharDetailView 里 `hasOrigin` else 分支挂组件 | `ROUND16_H2` 在组件 script |
| H3 | `apps/literacy-app/src/data/char-play.js` 的 `countRichPlays()`（沿用 R15 v1.1 口径：`templateFallback≠true`、按 char 去重、narration 去重达标）或 `scripts/data/char-play-seed.txt` ≥500 有效行 | — |
| H4 | `apps/math-app/src/data/learn-demos.js`（每条字面量 `skillId:` ≥12）+ evidence `learn-demo-registry.md`（`- <skillId>` 行） | `ROUND16_H4` |
| H5 | `apps/math-app/src/components/WpAnalysisPanel.vue` | `ROUND16_H5` |
| H6 | 两个 `src/data/mascotLines.js` + `useMascotCoach.js`，≥40 条 ≥8 字字符串 | `ROUND16_H6` |
| H7 | `src/utils/weeklyReport.js`（两 App）或 `useWeeklyReport.js` + `ParentView.vue` | `ROUND16_H7` |
| H8 | `check:round15` 8/8——凡动 CharDetailView / char-play / visualDemos 的岗，交活前必跑 | — |

红线重申（ACCEPTANCE）：标记必须在**可执行代码**（strip 注释后仍在）；
templateFallback 条目不算 H3；H4 不许只有壳没有实物/图形/算式三态。

## 8. 契约自验（本岗已跑通）

```
node --input-type=module -e "import { findIntroHoles } from './apps/literacy-app/src/data/char-intro.js' ..."
→ 全库 1820 字 getCharIntro 0 空洞；无字源 1012 字静态模式分布 radical 1006 / parts 6，
  word 模式在调用方传入组词时命中（已验：'一' + words → mode 'word'）；
  字表外字（齉）→ radical 兜底块非空，不为 null
```

实现岗合入后请重跑上述断言 + `npm run check:round16` + `npm run check:round15`。
