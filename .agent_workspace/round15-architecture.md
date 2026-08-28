# Round 15 架构 · Play 层（一字一动画：玩→认→练→写→说）

> 岗位：r15-arch-contracts（子代理 #1）
> 分支：`cursor/r15-arch-contracts-9f67`（基于 `cursor/r15-orchestration-9f67`）
> 本文是实现岗（engine / phase-remap / catalog / autofill / write-guide / tests）的共同契约。
> 契约代码已落地并通过 Node 全库验证：`getCharPlay` 1820/1820 非空、0 空洞。

## 0. 一页话总览

孩子点开任意一个字，先玩（和字义相关的小互动）→ 再认（有字源的自动播演变动画）→
练（听音找字）→ 写（先看示范再描红）→ 说（读一读 + 意思题 + 领星星）。
「玩什么」由一个轻量的 **CharPlay 描述对象**回答，三层解析（富脚本 → 生成索引 →
运行时合成）保证 **任何字都拿得到剧本、任何调用都不判空**；「怎么玩」由
`CharPlayStage` 按模板渲染，模板场景代码按需加载。

## 1. Play 数据契约（已落地：`apps/literacy-app/src/data/char-play.js`）

```js
/**
 * @typedef {Object} CharPlay
 * @property {string} char       目标汉字
 * @property {string} theme      number|nature|body|animal|family|action|food|object|position|abstract|general
 * @property {string} template   玩法模板 id，必须是 PLAY_TEMPLATES 的 key
 * @property {string} narration  开场引导语（TTS 播报 + 屏显），孩子能听懂的一句，≤30 字
 * @property {string} emoji      主图标（OpenMoji 渲染；缺省取 char-index 卡片图标）
 * @property {Object} [props]    模板参数，schema 见 PLAY_TEMPLATES[template].props
 * @property {boolean} [templateFallback] true = 自动补齐；缺省/false = 富脚本（H3 只数后者）
 * @property {('rich'|'generated'|'runtime')} [source] 解析来源，调试/探针用
 */
```

**入口函数（对全仓的唯一契约）：**

```js
import { getCharPlay } from '@/data/char-play.js'
const play = getCharPlay(char)   // 同步、纯函数、永不返回 null/undefined
```

- **同步**：探针 `check-round15.mjs` H2 在 Node 里同步遍历 1820 字；CharDetailView
  默认从玩步开始，进页面就要剧本，等不起一个 import() 往返。
- **Node 可跑**：`char-play.js` 只 import 纯数据模块（char-index / etymology-index /
  radicals / rich / generated），**禁止**引 Vue、DOM、GSAP、`import.meta.glob`。
- **永不 null**：字表内 1820 字层层兜底；字表外的字（拍照识字可能识出表外字）
  也返回通用 `tap-reveal` 剧本。调用方一律不判空。
- 辅助导出：`PLAY_TEMPLATES`（模板注册表）、`TEMPLATE_IDS`、`RICH_PLAY`、
  `countRichPlays()`（H3 运行时计数钩子）、`synthesizePlay()`（生成器对拍用）。

### 模板注册表 v1（6 个，引擎岗按此实现场景）

| id | 玩法 | props schema | 适用 |
|---|---|---|---|
| `tap-reveal` | 点 N 次主图标，字浮现 | `{ emoji, taps:1–3 }` | 万能保底 |
| `emoji-hunt` | 多图案里找出和字义相关的 | `{ target, decoys[] }` | 名词/方位 |
| `rain-catch` | 接住落下的目标图标/字 | `{ target, drops:2–4 }` | 数量/动作 |
| `sound-pop` | 听音点破目标字泡泡 | `{ rounds:1–3, decoys[] }` | 形近字多的 |
| `morph-story` | 图标程序化渐变为字形 | `{ emoji }` | 有字源的字 |
| `drag-parts` | 拖部件拼整字 | `{ parts[], hint }` | 会意/形声（**仅富脚本/生成器**用，运行时兜底不选它——没有部件数据拼不了） |

每个模板的硬要求（引擎岗验收线）：**≥1 次有效交互可完成**，或点「跳过」直接完成；
reduced-motion 下有静态可玩变体（不建时间线，交互照常）；props 缺字段按注册表
`defaults` 兜底，不许抛错。新增模板 = 在 `PLAY_TEMPLATES` 注册 + CharPlayStage
里加对应场景实现，两处都改才算加上。

## 2. 三层解析与文件归属

```
getCharPlay(char)
  1. RICH_MAP     ← char-play-rich.js   富脚本（catalog 岗扩到 ≥200 条，H3）
  2. GENERATED    ← char-play-index.js  gen-char-play.mjs 生成（autofill 岗，H5）
  3. synthesizePlay(char)               运行时合成，规则与生成器一致（架构岗已落地）
```

| 文件 | 归属 | 现状 |
|---|---|---|
| `src/data/char-play.js` | **架构岗（本岗）**，改契约需先改本文档 | ✅ 已落地 |
| `src/data/char-play-rich.js` | catalog 岗（r15-play-catalog-rich）扩写 | ✅ 已落地 5 条 u1 示例，扩到 ≥200 |
| `src/data/char-play-index.js` | autofill 岗（r15-play-autofill）生成覆盖 | ✅ 空索引占位（运行时合成兜底，不阻塞任何人） |
| `scripts/gen-char-play.mjs` | autofill 岗新建（契约见第 6 节） | ⬜ |
| `src/components/CharPlayStage.vue` | engine 岗新建（契约见第 5 节） | ⬜ |
| `CharDetailView.vue` 五步改造 | phase-remap 岗（契约见第 4 节） | ⬜ |

**富脚本写作规范**（`char-play-rich.js` 头注释同款）：template 取自注册表、props 守
schema、narration ≤30 字口语、只用 emoji + 程序化参数、每条 ~120 字节、200 条合计
≤40KB 源码。同字重复以先出现的为准，生成器要报告重复。

## 3. templateFallback 语义与 H3 计数口径

- `templateFallback: true`：这条剧本是**自动补齐**（generated 或 runtime）。
- 缺省 / false：**富脚本**，即「有人为这个字想过怎么玩」。
- H3 只数富脚本：`countRichPlays()` 返回 `RICH_MAP.size`，探针也会静态数
  `RICH_PLAY` 数组长度，两个口径必须一致——**禁止**给生成条目去掉标记凑数（验收红线）。
- `source` 字段只作调试/探针辅助，UI 不得依赖它做分支（避免「富脚本才好玩」的退化）。

## 4. 阶段机契约：玩→认→练→写→说（phase-remap 岗）

现有 `CharDetailView.vue` 是五步状态机（intro/trace/listen/quiz/reward）。Round 15
**改成六格轨道、五个学习步 + 领奖尾步**，id 与标签固定如下（H1 探针对齐）：

| 序 | id | 标签 | 内容 | done 记账 |
|---|---|---|---|---|
| 1 | `play` | 玩 | CharPlayStage 小互动 | 完成 ≥1 有效交互或点跳过 → `done.play = true`（跳过也算过，玩是热身不是考试） |
| 2 | `intro` | 认 | 现「认一认」+ **有字源的字自动挂载 EtymologyStage（autoplay）** | 听读/看完 → `done.intro` |
| 3 | `listen` | 练 | 现「听一听」（形近字听音三选一），不动逻辑只换标签 | 同现状 |
| 4 | `trace` | 写 | **先播笔顺示范（可跳过）再进描红**（write-guide 岗，H6） | 同现状（描红完成才算） |
| 5 | `speak` | 说 | 现「考一考」改名 + 增加「跟我读一遍」朗读钮（读了/答了都记 `done.speak`） | 原 quiz 逻辑保留 |
| 6 | `reward` | 领奖励 | 现状不动 | 凭 `done` 五键齐全才记账 |

必须保留的既有机制（**禁止在改造中丢掉**，H7/G4/G5）：

- `pendingNext` + 「等一下」停表的自动衔接（WCAG §2.2.1）；玩→认的衔接同样走
  `scheduleAdvance('intro', …)`。
- `canJump` 解锁规则、`done` 只记真完成、`reached` 回看不受限。
- `reduceMotion` 下 `playPhaseTransition` 不跑；CharPlayStage 收到后走静态变体。
- 默认从 `play` 开始（`phase = ref('play')`，`resetFlow` 同步改）。
- `restartFlow` / `resetFlow` 里补 `done.play`、`done.speak` 的清零。

## 5. CharPlayStage 组件契约（engine 岗）

```
props:  { char: String（必填）, size?: Number, autoplay?: Boolean = true }
emits:  complete()  —— 有效交互达标或用户点「跳过这一步」
        skip()      —— 用户显式跳过（complete 也要跟着发，调用方只听 complete 亦可）
内部：  const play = getCharPlay(props.char)   // 自己解析，不要求父层传剧本
```

- 组件本体在 CharDetailView 里 `defineAsyncComponent(() => import(...))` 按需加载
  （与 EtymologyStage 同款模式）。
- 各模板场景实现放 `src/components/play/` 下，由 CharPlayStage 内部
  **按 template 动态 import**：孩子玩哪个模板才下载哪个场景。
- 视觉素材只允许：字表 emoji（OpenMoji 字形/SVG 管线，`scripts/fetch-openmoji.mjs`
  既有链路）、程序化 SVG、GSAP 补间。**禁止**新增位图/外链图/任何洪恩风格素材。
- a11y：narration 进 `aria-live` 播报 + TTS（走 `utils/speech.js` 现有链路）；
  「跳过这一步」按钮常驻可见；所有交互可点击（不依赖拖拽长按的唯一路径——
  drag-parts 必须提供「点选部件」等价操作）。
- 反馈统一走 `useFeedback()`（音效/粒子/震动），别自造一套。

## 6. 自动补齐管道契约（autofill 岗：`gen-char-play.mjs`）

- 输入：`src/data/char-index.js`（1820 字）、`char-play-rich.js`（富脚本，跳过不生成）、
  `etymology-index.js`、`radicals.js`。
- 输出：**整体覆盖** `src/data/char-play-index.js`，导出
  `GENERATED_PLAY: Record<char, CharPlay>`，每条 `templateFallback: true`、
  `source` 留给 normalize 补（写 `'generated'` 亦可），文件头保留「生成文件请勿手改」。
- **生成规则必须与 `char-play.js` 里 `synthesizePlay()` 一字不差**（那是唯一事实源，
  可直接 `import { synthesizePlay }` 复用后去掉 `source:'runtime'`）：
  1. `hasEtymology(char)` → `morph-story`；
  2. 否则按 `RADICAL_THEME` 定 theme，按 `hashOf(char)` 从
     `[tap-reveal, emoji-hunt, rain-catch, sound-pop]` 轮换取模板（决定性、无随机）。
- 附带校验（构建期，H5 的 0 空洞断言）：富脚本 template ∉ 注册表 / props 缺必填 /
  同字重复 → 报错退出；生成后合并三层数 1820/1820。
- 接进 `npm run check:data` 或独立 `check` 子命令均可，探针两个口径都认。

## 7. 包体与按需加载边界

| 层 | 打包位置 | 预算 |
|---|---|---|
| `char-play.js` + `char-play-rich.js` + `char-play-index.js` | 学习路由 chunk（随 CharDetailView），**同步** | 三件合计源码 ≤200KB / gzip ≤60KB；rich ≤40KB、generated ≤120KB（够 1820 条紧凑条目） |
| `CharPlayStage.vue` | 独立 async chunk（defineAsyncComponent） | 组件壳 ≤15KB |
| `components/play/*` 模板场景 | 每模板一个 async chunk | 单模板 ≤20KB |
| OpenMoji 资源 | 复用现有管线，不新增 | 0 新增 |

- GSAP 已在主依赖里（CharDetailView 本来就用），模板场景直接 import 不算新增。
- **禁止**把 play 数据塞进 `char-index.js`（那是主包）；禁止在首页/字表页 import
  `char-play.js`——它只属于学习路由。
- 生成条目要紧凑：能由 normalize 兜底的字段（emoji、narration、props defaults）
  生成器可省略不写，靠 `getCharPlay` 归一化补全，换包体空间。

## 8. 与 etymology 的关系

- **分工**：玩步是「字义热身」（emoji + 程序化互动），认步才是「字形字源」
  （EtymologyStage 全套演变）。`morph-story` 模板只做 emoji→字形的轻量渐变，
  **不要**去 import `etymology.js` / `etymologySketch.js` 的重语料——那是认步
  按需 chunk 的东西，玩步嚼一遍既重复又背包体。
- `char-play.js` 只引 `etymology-index.js`（轻索引，主包已有）判断 morph-story 适用性。
- 认步（H4）：`hasEtymology(char)` 为真时进入 `intro` 即自动挂载
  `<EtymologyStage :char autoplay />`（不再要求先点按钮）；「去字源馆」链接保留。
  reduced-motion 下 EtymologyStage 自带静态两帧并排，行为已合规，直接复用。
- 本轮**不**要求字源扩到 1820（现 808 字），但 Play 必须 1820/1820——两者覆盖率
  是两回事，探针也分开测（H2 vs H4）。

## 9. 禁止事项（验收红线，来自 BRIEF/ACCEPTANCE）

1. **禁止**复制洪恩 IP/美术/音频；只用 OpenMoji + 程序化 SVG/GSAP。
2. **禁止** `getCharPlay` 对缺字返回 null 却声称 H2 绿；也禁止返回占位剧本但
   CharPlayStage 渲染空白——任何模板必须可玩完（≥1 有效交互或可跳过完成）。
3. **禁止**把 `templateFallback: true` 的条目计入 H3 富脚本数。
4. **禁止**只改 PHASES 的 label 不接 Play 舞台糊弄 H1。
5. **禁止**丢掉「等一下」停表、跳步、reduced-motion 静态变体（G3–G5）。
6. **禁止**手改生成文件 `char-play-index.js`（改生成器再跑）。
7. **禁止**在主包（char-index / 首页路由）引入 play 数据或场景代码。

## 10. 契约自验（本岗已跑通）

```
node --input-type=module -e "import { getCharPlay } ..."
→ chars: 1820  miss: 0  rich: 5  countRichPlays: 5
→ 模板分布：morph-story 803 / emoji-hunt 268 / tap-reveal 256 / sound-pop 247 / rain-catch 246
→ 字表外字（齉）→ 通用 tap-reveal，templateFallback: true，不为 null
```

引擎、目录、autofill 岗合入后请重跑上述断言 + `npm run check:round15`。
