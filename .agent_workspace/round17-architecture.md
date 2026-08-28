# Round 17 架构 · 覆盖加深（富 Play ≥900 · 精品剖析 · 学伴关键接线 · 走查证据）

> 岗位：r17-arch-contracts（子代理 #1）
> 分支：`cursor/r17-arch-contracts-9f67`（基于 `cursor/r17-orchestration-9f67`）
> 本文是 H2 / H3 / H4 / H5 / H6 各实现岗的共同契约。改契约先改本文档。
> 已随本文落地一个数据层空壳：`apps/math-app/src/data/word-problem-explains.js`
> （H4 登记表 + 规范化器 + count API，已过 Node 自验）。UI 一律没做——那是实现岗的活。

## 0. 一页话总览（含本岗实测基线）

R16 把门槛推绿了，R17 要把「高频路径」做到精品课密度。本岗在编排分支上实测的起点：

| 维度 | 实测现状（f9f8cf1） | R17 目标 |
|---|---|---|
| 富 Play | `countRichPlays()` = **640**（u1–u40），narration 去重 **640/640** | ≥900（seed 续到 **u55**），去重 ≥720 |
| 学演示 | `learn-demos.js` 字面量 `skillId:` **21 个**（34 技能里覆盖 21） | ≥27（+≥6 条） |
| 应用题剖析 | `wpAnalysis.js` 通用算式解析链，**0 条手写** explain | ≥20 母题手写分步链 |
| 学伴 | 阶段剧本（`pickMascotStage`）已在 Home/Learn 等页；**CharDetailView、QuizShell 均未接** | 两侧关键路径接上阶段台词 |
| 走查证据 | `.agent_workspace/evidence/r17/` 空 | walkthrough.md + ≥4 张截图/录屏 |

四块延续同一设计原则：**数据层同步纯函数、永不 null、Node 可跑；UI 层可跳过、
reduced-motion 完整可用**。所有 `ROUND17_H*` 标记必须落在**可执行代码**里
（探针 strip 注释后再 grep，写注释里等于没写）。

## 1. 富 Play 增量到 ≥900 的契约（H2 · r17-play-rich-900 岗）

### 1.1 只改 seed，不改运行时

流水线不动：`scripts/data/char-play-seed.txt`（五段式：`汉字 | 主题 | 模板 | 旁白 | 道具`）
→ `node scripts/gen-char-play-rich.mjs` → `src/data/char-play-rich.js`（每条
`templateFallback: false`）→ `char-play.js` 的 `countRichPlays()/listRichPlays()`。
运行时三层兜底（rich → generated → emergency）一行不改。

### 1.2 增量范围与配额

- 字表共 99 单元 1820 字；累计到 **u53 才到 900 字**，所以 seed 从 u40 续写到
  **u55**（本岗实测 u41–u55 共约 290+ 字，写完落在 930±，给探针留余量）；
- `gen-char-play-rich.mjs` 的 `RICH_UNIT_LIMIT` 由 `40` 改 **`55`**（校验会跟着放宽）；
- 每条旁白仍要「照着字义写」（雨接雨滴、火添柴那个标准），≤30 字口语；
- **旁白撞句生成器直接判错**（现有校验，不许放松）——这是 narration 去重 ≥720 的
  结构保证：640 条老旁白 + 新写的必须全库唯一，去重数 = 总数。

### 1.3 探针标记（ROUND17_H2）

探针在 `char-play.js` / `char-play-rich.js` / `gen-char-play-rich.mjs` 三处任一
strip 后 grep `ROUND17_H2`。落法：生成器把探针标记常量升级为
`ROUND17_H2`（可执行字符串，随生成物一起落进 `char-play-rich.js` 头部的
`export const RICH_PLAY_PROBE = 'ROUND17_H2'` 之类），生成器自身也保留同名字面量。
**不许**只在注释里写。

### 1.4 不退化红线（H8 联动）

`check:round16` H3 只认运行时口径 `countRichPlays()≥500` + narration 去重 ≥400，
本岗确认它**不 grep `ROUND16_H3` 字样**——升级标记安全。交活前必跑：

```
node scripts/gen-char-play-rich.mjs --check
node apps/literacy-app/scripts/test-char-play.mjs   # 如有
npm run check:round16 && npm run check:round17
```

## 2. 精品剖析数据协议（H4 · r17-wp-explain-hand 岗）

### 2.1 为什么要新文件

`wpAnalysis.js` 的通用链是「解析 equation 逐步算」——能把式子念对，讲不出
「为什么先算这一步」。R16 架构文里预留过母题 `explain(made)` 字段，本轮正式
落成**独立登记表**（不散进 1200 行的 `wordProblems.js`，20 条手写文案会把母题库
淹掉）：

**文件路径（探针 grep 的就是它，一个字不许错）：**
`apps/math-app/src/data/word-problem-explains.js`（本岗已放空壳）。

### 2.2 条目 schema（探针按每条字面量 `masterId:` 计数）

```js
export const WORD_PROBLEM_EXPLAINS = [
  {
    masterId: 'chicken-rabbit',   // wordProblems.js 母题 id，每条必须字面量写 masterId:
    explain(made) {               // made = 母题 make() 的产物 { text, equation, answer, unit, hint, visual }
      return [
        { say: '假设全是鸡：每只 2 只脚，先算假设下一共几只脚。', math: `${h} × 2 = ${h * 2}` },
        { say: '真实脚数比假设多出来的，都是兔子每只多的那 2 只脚贡献的。', math: `${feet} − ${h * 2} = ${diff}` },
        { say: '多出的脚数除以每只兔多的 2 只，就是兔子的只数。', math: `${diff} ÷ 2 = ${made.answer}` },
      ]
    },
  },
]
```

手写步骤两个字段：

| 字段 | 约束 |
|---|---|
| `say` | 必填。讲「为什么这么算」，8–60 字口语，像老师说话；**不许出现最终得数**（防绕开盖答案） |
| `math` | 可选。本步算式 `'a op b = c'`，数字从 `made` 里取（母题是随机出数的，写死数字＝换个实例就講错题） |

### 2.3 规范化与兜底（本岗已实现在空壳里，实现岗不用重写）

`handExplainSteps(masterId, made)`：

1. 查表取 `explain`，跑出 raw steps；抛错 / 非数组 / **少于 3 步** / 带 `math` 的
   步少于 2 → 返回 `null`（调用方退通用链，**永不因手写文案坏掉而白屏**）；
2. 每步规范化成剖析面板已经会渲染的形状：
   `{ kind:'hand', say, expr, display, masked:'?', asked, why: say }`
   （`math` 按最后一个 `=` 切成 `expr` / `display`；没 `math` 的步 `expr` 为空串，
   面板照 `say` 渲染成纯文字步）；
3. **最后一个带 `math` 的步自动置 `asked: true`**，且强校验其得数按数字 token
   含 `made.answer`（`'5 …… 3'` 这类带余数的显示也认）、该步 `say` 里**不含**
   得数 token——盖得数的机制（判题前显示 `masked`）由面板现有 `resultOf()`
   原样生效，手写链不需要也不允许自己搞第二套遮罩。asked 步的 `say` 尽量不放
   数字，把数字留给会被盖住的 `math`。

### 2.4 接线（同岗，两处小改）

1. `wpAnalysis.js` 的 `buildAnalysis(question)`：开头查
   `handExplainSteps(question.id, question)`，命中则
   `steps = 手写链`、`handcrafted = true`（其余 knowns/ask/diagram 照旧）；
   未命中走现有通用链。`question.id` 就是母题 id（WordProblemsView 的
   `VARIANT_MAKERS.get(question.id)` 已在用这个事实）——**出题侧不用改**。
2. `WpAnalysisPanel.vue` 分步区加一个渲染分支：`handcrafted` 时每步先渲 `say`
   （大字、可朗读），带 `expr` 的再渲 `expr = resultOf(step)`；「一次摊一步」、
   判题前盖最后一步得数、跳过按钮、变式入口——**全部沿用，不新增交互**。

### 2.5 选题清单（≥20，从 66 个母题里挑「通用链讲不清」的）

优先级从高到低（进阶 ≥2 步、hint 一句话说不透的）：

`chicken-rabbit`、`meet`、`distance`、`sum-diff`、`sum-times`、`age-later`、
`average`、`work-days`、`planting`、`div-remainder`（进一/去尾语义）、`ceil-pack`、
`left-over`、`money-change`、`unit-price`、`two-step-buy`、`compare-total`、
`times-multiple`、`quotitive`、`perimeter`、`area`、`duration`、`fraction-part`。
（22 个候选，写满 20 即达标，多写不拦。）

### 2.6 红线与自验

- ACCEPTANCE 红线：**禁止空 `explain()` 返回空数组凑数**——规范化器对 <3 步直接
  判 null，探针数的是 `masterId:` 字面量，两头都堵了，别试；
- 空壳自带 `findExplainHoles(masters)`（注入 `WORD_PROBLEMS` 数组，避免数据文件
  反向 import 母题库）：每条跑 3 个随机实例，校验步数 / answer 对齐 / say 里
  不含得数。交活前 Node 里跑一遍断言 `[]`：

```
node --input-type=module -e "
import { WORD_PROBLEMS } from './apps/math-app/src/data/wordProblems.js'
import { findExplainHoles, countHandExplains } from './apps/math-app/src/data/word-problem-explains.js'
console.log(countHandExplains(), findExplainHoles(WORD_PROBLEMS))"
```

（直接跑需要处理 `@/utils/random` 别名：照 `scripts/check-round17.mjs` 的
`register('./alias-loader.mjs', …)` 起法即可。）

## 3. 学演示 +≥6 契约（H3 · r17-math-learn-demo-plus 岗，简版）

- 只往 `apps/math-app/src/data/learn-demos.js` 加条目（R16 协议原样），每条
  字面量 `skillId:`；已覆盖 21 技能，缺口里**适合「实物→图形→算式」三态**的：
  `wp-diff`、`wp-times`、`wp-share`、`wp-two-step`、`shape-3d`、`classify`、
  `number-trace`（挑 ≥6 条；sudoku / maze-condition / deduction 不适合三态，别硬凑）；
- 标记：文件里现有 `ROUND16_H4` 保留（round16 探针还在数它），另加可执行
  `export const ROUND17_H3 = 'learn-demo-27'`；探针对两个标记文件内的
  `skillId:` 去重计数，去重后须 ≥27；
- 三态词证（实物/图形/算式）与「跳过」词证都在 learn-demos.js / LearnDemo 组件的
  可执行代码里已有，别删；
- 登记表 `.agent_workspace/evidence/r16/learn-demo-registry.md` **同步追加**新行
  （round16 H4 的参考口径读它）。

## 4. 学伴关键路径接线点清单（H5 · r17-mascot-wire 岗）

探针：两 App src 下扫可执行 `ROUND17_H5`，其所在文件合并后须同时命中
`/CharDetail|useMascotCoach|QuizShell|recentWrong|pickMascotStage/` 和
`/mascot|学伴|台词|stage/i`。**两侧都接**（探针「至少一侧」，BRIEF 成功体验第 4 条
要的是两侧都响）。

### 4.1 识字侧 · CharDetailView.vue（单字页五步流）

现状：页面有 `speak()`、`stepAnnounce`（aria-live），**没有学伴**。接线点：

| # | 位置（现有代码锚点） | 接什么 |
|---|---|---|
| 1 | `<script setup>` 顶部 | `const coach = useMascotCoach('learn', { char: () => item.value?.char ?? '', combo, recentWrong, justMastered })`——`useMascotCoach` 第二参 moment 早就支持这四个键（`unref` 解包，可传 getter/ref） |
| 2 | `goPhase(id)`（约 L306，写 `stepAnnounce` 那里） | 进入新 phase 后取一句当前阶段台词（`coach.line` / `next()`），追加进 `stepAnnounce` 或渲染在头部气泡——**别抢 phase 播报的 aria-live**，台词放视觉气泡 + 点击朗读 |
| 3 | 答错处（listen/speak 判错分支） | 置 `recentWrong` moment → 阶段自动切到安慰组（literacy 的 `encourage` 阶段 `when` 看 `recentWrong`） |
| 4 | `speak` 步结账（约 L475 `done.speak = true`） | 置 `justMastered` → `mastered` 阶段夸一句 |
| 5 | 组件 script | `export const ROUND17_H5 = 'char-detail-mascot'`（可执行） |

渲染载体：头部 hero 区加 `<MascotCompanion>`（LearnView 同款）或轻量气泡；
`reduceMotion` 下无动画只有字；**朗读跟 settings 总开关**（useMascotCoach 已处理）。

### 4.2 数学侧 · QuizShell.vue（所有刷题模块的共用壳）

现状：`mood`/`message` 是壳自己管的（新题 `sample(props.prompts)`，判对 cheer、
判错 sad+答案播报），有 `mascot` 插槽。接线点：

| # | 位置（现有代码锚点） | 接什么 |
|---|---|---|
| 1 | `<script setup>` | 引 `pickMascotStage` / `mascotStageLines`（`@/data/mascotLines.js` 纯函数，比整个 useMascotCoach 轻，不跟壳自己的 message 状态机打架） |
| 2 | 壳内已有的连击 / 错误状态 | 组 ctx：`{ combo, recentWrong: 刚判错? 1 : 0, stars: progress.state.stars, … }`——`recentWrong` 这个词必须以变量形式出现（探针词证） |
| 3 | 新题装台（约 L328 `message.value = sample(props.prompts)`） | 改为：`pickMascotStage(ctx)` 命中非 idle 阶段时取 `mascotStageLines(stage.id, ctx)` 轮换一句（`hashSeed` 决定性），否则保留 prompts 原逻辑 |
| 4 | 判错反馈（约 L262） | 播完「正确答案是 …」后，下一题装台自然带出安慰阶段台词；**不许改判题 / 星星 / 错题本一个字** |
| 5 | 组件 script | `export const ROUND17_H5 = 'quiz-shell-mascot'`（可执行） |

### 4.3 红线

- 台词不催氪不贬低（R16 红线延续）；答错先安慰再给路子；
- 两处接线都是**加话不改流程**：phase 推进、判题、计分、错题本、`introIdle` 兜底
  一律不动；动了要能对 `check:round16` H6/H8 全绿自证；
- 台词字面量继续放 `mascotLines.js`（round16 H6 在数那里的去重中文串），
  **不许把新台词写死在视图里**。

## 5. 走查证据目录约定（H6 · r17-walkthrough-bundle 岗）

```
.agent_workspace/evidence/r17/
├── walkthrough.md            # 总文档（探针读它，>400 字，含「认/演示/剖析/周报」词证）
├── h2-play-rich-<char>.png   # 富 Play：u41+ 某字「玩」步舞台（旁白可见）
├── h3-learn-demo-<skillId>.png   # 新增学演示：三态之一 + 跳过按钮入镜
├── h4-wp-explain-<masterId>.png  # 精品剖析：手写 say 步骤 + 盖住的得数入镜
├── h5-mascot-<side>.png      # 学伴：CharDetail 或 QuizShell 阶段台词气泡
├── h7-weekly-report.png      # 家长周报卡
└── *.mp4 / *.webp            # 录屏同目录，命名同前缀
```

- walkthrough.md 里引用路径**必须写成 `evidence/r17/<文件名>` 形式**（探针正则
  `evidence\/r17\/[^\s)]+\.(png|jpg|webp|mp4)`，再按 `.agent_workspace/<路径>`
  验落盘）；≥4 张，H2 认步 / 学演示 / 剖析 / 周报四景各至少一张；
- 截图来自本地 `npm run dev` 或 `vite preview` 的真渲染页面；**伪造路径 = 验收
  红线**，宁可少一张诚实标 BLOCKED；
- 每张图配一句「在哪个路由、点了什么、证明了哪条门槛」。

## 6. 探针对齐表（文件名一个都不许写错）

| 门槛 | 探针认的确切路径 | 可执行标记 |
|---|---|---|
| H2 | `apps/literacy-app/src/data/char-play.js` 的 `countRichPlays()≥900` + narration 去重 ≥720；标记在 char-play.js / char-play-rich.js / gen-char-play-rich.mjs 任一 | `ROUND17_H2` |
| H3 | `apps/math-app/src` 下带标记文件里 `skillId:`/`demoId:` 字面量去重 ≥27 + 三态 + 跳过词证 | `ROUND17_H3`（`ROUND16_H4` 继续算） |
| H4 | `apps/math-app/src/data/word-problem-explains.js`（+ wpAnalysis.js / modules/word-problems/explains.js 也在扫描名单）里 `masterId:` 字面量 ≥20 | `ROUND17_H4` |
| H5 | 两 App src 任意文件，但按第 4 节落在 CharDetailView.vue + QuizShell.vue | `ROUND17_H5` |
| H6 | `.agent_workspace/evidence/r17/walkthrough.md` + ≥4 个落盘文件 | — |
| H8 | `npm run check:round16` 8/8（v1.1）——凡动 char-play / learn-demos / WpAnalysisPanel / mascotLines / QuizShell 的岗，交活前必跑 | — |

## 7. 包体与依赖边界

| 产物 | 打包位置 | 预算（源码增量） |
|---|---|---|
| char-play-seed u41–u55 + 再生成的 char-play-rich.js | 学习路由 chunk（现有位置） | 数据行性质，不设上限但旁白 ≤30 字/条 |
| `word-problem-explains.js`（≥20 条） | word-problems 路由 chunk（只被 wpAnalysis / 面板引） | ≤14KB |
| learn-demos 新 6+ 条 | visual-demos 路由 chunk（现有位置） | ≤6KB |
| CharDetailView / QuizShell 学伴接线 | 各自现有 chunk | 每处 ≤3KB |
| 新依赖 | **零** | — |

禁止：数学主包 import `word-problem-explains.js` 全表（只许 word-problems
链路引）；把学伴台词字面量写进视图。

## 8. 契约自验（本岗已跑通）

```
node：countRichPlays() = 640，narration 去重 640          # H2 起点确认
word-problem-explains.js（Node 全过）：
  countHandExplains() = 0；handExplainSteps('nope', {}) = null；findExplainHoles([]) = []
  临时填 3 条样例复验规范化器：鸡兔链 3 步 asked 落最后一步、余数链 '5 …… 3' 认得数、
  得数写进 say → null、display 与 answer 失配 → null（坏链全部退通用链，不白屏）
npm run check:round17 → 1/8（预期启动态）：
  ✗ H2 rich=640 标记=false   ✗ H3 计数=21   ✗ H4 标记=true 计数=0（空壳已就位）
  ✗ H5 / H1 / H6 待各岗     ✗ H8 ← check:round16 7/8
npm run check:round16 → 7/8：唯一红项是 H8（round15 连锁，干净环境缺双 APK，
  需 `npm run android:sim` 重建——#10 回归岗职责，与数据/契约无关）
```

实现岗合入后请重跑上述断言 + `npm run check:round17` + `npm run check:round16`。
