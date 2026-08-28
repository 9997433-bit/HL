# Round 15 验收标准 · 一字一动画（玩·认·练·写·说）

> 版本：**v1.1**（可执行细则；探针 `PROBE ROUND15-v1.1`）  
> 简报：`.agent_workspace/ROUND15-BRIEF.md`  
> 探针：`npm run check:round15` → `scripts/check-round15.mjs`  
> 回填：`.agent_workspace/acceptance-log-round15.md`

## G 总则

- **G1** 不复制洪恩 IP/美术；OpenMoji + 程序化动画。
- **G2** 1820 字 Play 覆盖率 100%；空洞=失败（H2/H5）。
- **G3** 五步默认顺序：玩 → 认 → 练 → 写 → 说；可手动跳步但不伪造 `done`。
- **G4** `prefers-reduced-motion` / 家长「减少动态」下仍可完成全流程。
- **G5** 每步可跳过；自动衔接保留「等一下」停表（沿用 CharDetailView 既有 WCAG 模式）。
- **G6** 往轮探针不因本轮回退（H8）。

## 标记约定（全体 H 适用）

`ROUND15_Hx` 标记**必须出现在可执行代码里**（标识符或字符串常量，例如
`const ROUND15_H4_AUTO_ORIGIN = true` 或日志字符串）。探针匹配前会剥掉
HTML/JS 注释——**写在注释里等于没写**。标记是辅助信号，不能单独过线：
每条 H 的结构性最低要求（见下）必须同时满足。

## H1–H8 判定细则（与探针一一对应）

### H1 五步对齐

三项全部满足才绿：

1. **id 顺序**：`PHASES` 数组（可留在 `CharDetailView.vue`，或抽到
   `src/composables/useCharPhases.js` / `src/data/char-phases.js`，变量名保持 `PHASES`）
   的 id 序列满足 `play` 在**第 0 位**，且
   `play → intro → listen → trace → (quiz|speak)` 相对顺序成立（练在写前）。
2. **默认从玩起**：`phase = ref('play')` 或 `ref(PHASE_IDS[0])`；若初始 phase 由函数
   决定（如断点续学），该函数须默认返回 `'play'` 并携带 `ROUND15_H1` 标记。
3. **舞台真挂载**：模板存在 `phase === 'play'` 门控，且文件中出现
   `<CharPlayStage` / `<PlayStage`（或 `Play(Stage|Scene|Ground)` 命名的等价组件）标签。

红线兑现：只把 label 改成「玩」而不满足 1+3 → 红。

### H2 Play 引擎 + 全库 resolve

- **模块位置**：`getCharPlay(char)` 须从以下候选之一导出（首选第一个）：
  `apps/literacy-app/src/data/char-play.js`、`src/data/char-play/index.js`、
  `src/data/char-play-index.js`、`src/data/charPlay.js`、`src/data/play-index.js`、
  `src/play/char-play.js`、`src/utils/charPlay.js`。放别处请先改本细则再改探针。
- **有效 play 定义**：返回对象且 `template`、`narration` **均为非空字符串**。
  返回 `null`、抛异常、或缺任一字段的字都计为空洞；空洞 >0 即红，探针报缺字样本。
- **全库口径**：`CHARACTERS` ≥1800 条，逐字调用；库不足 1800 视为数据异常直接红。
- **模块洁净**：play 模块（含其依赖链）必须能被 Node 直接 import——**不得引入
  `.vue`/`.css`/资源文件**；`@/` 别名可用（探针挂了 alias-loader）。v1.1 起探针对
  play 模块与 `characters.js` 分开诊断：characters 加载失败会明说「与 play 引擎无关」，
  不再笼统报「加载失败」冤枉引擎；同理 play 模块导入失败时会指名具体文件与报错。

### H3 富脚本 ≥200（如何计「富」）

- **富的定义**：`templateFallback !== true` **且** `narration` 非空的有效 play。
  `templateFallback: true`（自动补齐产物）一律不计——红线兑现。
- **去重**：按 `char` 去重后 ≥ **200**；同字多脚本只算 1。
- **防复制**：富脚本的 `narration` 文本去重后须 ≥ **160**（约 80%）。把同一句话
  复制两百份、或把模板句套 200 个字，都会在这里翻红。
- **计数来源优先级**：
  1. 运行时：全库跑 `getCharPlay` 数未打标条目（首选，最难伪造）。
     **防伪门**：若全库 0 条 `templateFallback: true` 且富计数 >400，判为
     「补齐管道未打标」，运行时计数作废，退回来源 2。
  2. 源文件：`src/data/char-play-rich.js` / `char-play-catalog.js` /
     `scripts/data/char-play-rich.json` 中结构化条目（须含 `narration`）。
- v1.1 起**不再信任** `countRichPlays()` 等模块自报数字；纯字表 `.txt`（无 narration）
  只能当 seed 参考，不计入 H3。

### H4 认步字源默认播（判定）

行为要求：孩子进入「认」步时，有字源语料的字**无需任何点击**即看到/听到字源
演变动画（EtymologyStage 或等价）；「找按钮才展开」= 红。

探针接受两种证据（满足其一，且文件里必须引用 `EtymologyStage`）：

- **(a) 结构证据**：某个 `<EtymologyStage` 的挂载条件（其前 400 字符窗口内的
  `v-if`/`v-show`）包含 `intro`/`phase`，即随认步进入自动挂载；
- **(b) 标记证据**：`ROUND15_H4` 标记（放在进入认步时自动展开的代码路径里）**加**
  自动展开赋值信号（`originOpen.value = true` / `autoOrigin` / `autoplay` 类）。
  仅有 `toggleOrigin` 按钮式翻转不算。

无字源的字（1820−808）认步走常规讲解，不因此判红；reduced-motion 下自动播可降级为
静态首帧+可点播放，但仍须默认可见（W3/W5 走查兜底运行时行为）。

### H5 自动补齐管道

- `apps/literacy-app/scripts/gen-char-play.mjs`（或 `gen-play.mjs`）存在，**去注释后
  >400 字符**，且有写盘信号（`writeFile`/`writeFileSync`/`createWriteStream`）。
  空壳脚本过不了。
- **数据侧真打标**：运行时至少 1 条 play 带 `templateFallback: true`，或 play 数据层
  源码（含 `char-play-templates.js` / `char-play-generated.js`）含该字段。打标代码
  可以住在 gen 脚本里，也可以住在它委托的数据层——探针看的是**打标是否真实生效**。
  0 空洞由 H2 断言，此处管「补的东西可识别」，与 H3 防伪门联动。

### H6 写步引导

进入「写」步须**先示范再描红**的显式编排（自动播示范、可跳过），仅保留手动
「看笔顺」按钮不算。探针认三种证据之一：

- `ROUND15_H6` 标记（放在进入写步自动编排的代码路径）；
- `phase === 'trace'` 门控 + `enterTrace`/`onEnterTrace`/`guideThenQuiz`/
  `demoBeforeQuiz`/`writeGuide` 类编排标识；
- `src/composables/useWriteGuide.js` 存在且被 CharDetailView 引用。

示范必须可跳过（W4 走查兑现）。

### H7 smoke / a11y

`apps/literacy-app/scripts/smoke.mjs` 须同时满足：

1. **play 覆盖**：`getCharPlay` × `CHARACTERS` 全库循环（或 `ROUND15_H7` 标记的等价
   覆盖段），且带**断言信号**（`problems` 计数 / `process.exit(1)` / `throw`）——
   只 import 不断言不算；
2. **reduced-motion 覆盖**：smoke 或 literacy 任一 `*.test.*`/`*.spec.*` 文件中出现
   reduced-motion / `reduceMotion` 检查。

### H8 往轮不退化（必绿项口径，与回归门禁岗一致）

`check:round13` 的 **H1–H6 与 H8 逐项保持绿**；仅 H7 可因外部 Play Console 账号
继续红。**不看总分**——否则 round13 的 H7 哪天翻绿，总分能掩盖其他必绿项退化。
round13 的 `--json` 输出解析失败或结果数 ≠8 一律判红，不做文本猜分。

**环境注记**：round13 的 H6 校验 APK 构建产物（`apps/*/android/.../app-debug.apk`
sha256），这些产物**未入 git**。干净克隆下 H8 必红——这是**环境红**不是回退，
**不降门槛**；先 `npm run android:sim` 重建双 APK（或在含产物的编排环境如
`/workspace` 复测），并在 log 里注明测试环境。

## 走查（人工 / 代理；探针管不到的运行时行为靠这里兜底）

| ID | 检查 |
|---|---|
| W1 | 点 u1「一」：先玩后认，有动效或可感知互动 |
| W2 | 点无富脚本冷门字：仍有模板互动，能点完成；抽 20 字不是同一张空白卡 |
| W3 | 有字源字：认步自动播演变，无需先找按钮 |
| W4 | 写步：先示范再描红；可跳过示范 |
| W5 | 开减少动态：五步仍可走完 |
| W6 | 街机厅游戏不回归 |

## 红线

- 禁止 `getCharPlay` 对缺字返回 `null` 却声称 H2 绿
- 禁止把 `templateFallback` 补齐脚本计数进 H3
- 禁止为过门禁把 PHASES 只改 label 不接 Play 舞台
- 禁止只在注释里塞 `ROUND15_Hx` 标记（探针剥注释后匹配）
- 禁止靠 `countRichPlays()` 之类自报数字过 H3（v1.1 探针已不采信）
- 探针改动（含放宽正则/阈值）须同步更新本文件版本号与 acceptance-log 修订记录

## 修订记录

| 版本 | 变更 |
|---|---|
| v1.0 | 编排启动版：H1–H8 骨架 + 红线 |
| v1.1 | 细则化：H3 富脚本计法（去重/防复制/防伪门）、H2 全库口径与模块洁净（分离诊断，无关模块不再误归因）、H4 默认播两类证据、H1 id 顺序+默认 play+舞台挂载三合一、H5 非平凡 gen+数据侧打标、H7 断言+reduced-motion、H8 必绿项口径（与回归门禁岗对齐）+环境注记、标记约定成文 |
