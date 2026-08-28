# Play 引擎交付说明（Round 15 · 子代理 #4）

分支 `cursor/r15-play-engine-9f67`（from `cursor/r15-orchestration-9f67`）。
探针记号：源码里搜 `ROUND15_H2`。

## 交付物

| 文件 | 作用 |
|---|---|
| `apps/literacy-app/src/data/char-play.js` | `getCharPlay(char)` 运行时：三层剧本解析 + 方言归一 |
| `apps/literacy-app/src/components/CharPlayStage.vue` | 舞台；六种互动渲染器；`complete` / `skip` / `interact` |
| `apps/literacy-app/scripts/test-char-play.mjs` | 全库道具校验（`npm run test:play`，已进 `npm test`） |

剧本数据本身不归这一岗：`char-play-rich.js`（富脚本岗，272 条）与
`char-play-generated.js` + `char-play-templates.js`（自动补齐岗，1820 条）
由各自的岗位维护，这里只负责读得进、渲染得出。

## 一件要紧的事：三套方言，一个舞台

剧本从三处来，本来是三套写法：

| 来源 | 谁写的 | props 长相 | 本轮字数 |
|---|---|---|---|
| 富脚本 | 人手写 `char-play-rich.js` | `{hero, items, goal}` / `{pairs:[{a,b}]}` | 272 |
| 自动补齐 | 生成器 `char-play-generated.js` | `{options, rounds}` / `{whole, slots, pieces}` | 1548 |
| 兜底合成 | `char-play.js` 内部 | 字表图标凑一桌 | 字表外的生字 |

模板 id 加起来 19 个。舞台不该认识 19 套写法，所以 `getCharPlay` 把它们
**归一成六种渲染器**，`CharPlayStage` 只认归一后的那一份 `props`：

| kind | 玩法 | 归到这儿的模板 |
|---|---|---|
| `pick` | 从几个里点中对的 | emoji-hunt / scene-tap / pair-match(选择题版) / sound-echo / sound-pop / tap-reveal(选择题版) |
| `catch` | 点够次数（会掉的也算） | rain-catch / count-tap / pop-bubbles / scene-poke / color-fill / sound-tap / tap-reveal(揭开版) |
| `assemble` | 零件送回位置 | drag-parts / word-build |
| `watch` | 一帧一帧看完 | morph-story / mirror-move / grow-tap |
| `match` | 左边一个右边一个 | sort-buckets / pair-match(连线版) |
| `push` | 顺着一个方向推 | swipe-motion / trace-path |

归类先看道具形状，再看模板 id，最后看 `interaction`——因为**同名不同玩法**确实存在：

- `tap-reveal`：生成器给 `options`，是「揭开找出对的那张」；富脚本只给 `items`，
  是「盖着的全揭开」。都按选择题渲染的话，后者会变成三张牌全对，随手一点就过。
- `pair-match`：富脚本的 `{a, b}` 是连线，生成器的 `{char, emoji}` 是选择题。
- `word-build`：富脚本把候选字写在 `parts`，只读 `pieces` 会只剩一张牌。

归一是纯函数：种子取自字的哈希，同一个字每次算出来的选项、乱序、落点都一样，
孩子重进看到的还是那一关，单测也因此可断言。

## 给「五步改造」岗的接线

```vue
<script setup>
const CharPlayStage = defineAsyncComponent(() => import('@/components/CharPlayStage.vue'))

function onPlayComplete({ skipped }) {
  // 玩过了才记账；跳过的只放行，不算完成
  if (!skipped) done.play = true
  scheduleAdvance('intro', DELAY.played)
}
</script>

<template>
  <CharPlayStage
    v-if="phase === 'play'"
    :char="decoded"
    @complete="onPlayComplete"
  />
</template>
```

- 组件按需加载即可：`char-play.js` 连同两份剧本表都跟着这个异步块走，不进首屏。
- `autoStart`（默认 true）控制会掉的道具要不要立刻开始落；这一步还没切到台前时传 false。
- `complete` 的 payload：`{ char, template, kind, templateFallback, interactions, skipped }`。
  跳过也会 emit（`skipped: true`），父级的步骤机不会被一个小游戏卡住。
- 组件自带「跳过这一步」按钮与 `aria-live` 播报，父级不必再补。
- DOM 契约（smoke 用）：根节点带 `data-char-play`、`.char-play-stage`、
  `data-char` / `data-template` / `data-kind` / `data-state`（`playing` → `done`）。

## 数据契约

```ts
getCharPlay(char: string): {
  char: string
  theme: string              // 两套主题表的 id 都收
  themeLabel: string
  themeEmoji: string
  accent: string             // 设计令牌，如 var(--leaf-500)
  template: string           // PLAY_TEMPLATE_IDS 之一（19 个）
  templateLabel: string      // 「找一找」这样的玩法名
  kind: string               // PLAY_KINDS 之一（6 个）—— 舞台按这个渲染
  emoji: string
  narration: string
  prompt: string
  props: object              // 形状由 kind 决定，见下表
  templateFallback: boolean  // true = 自动补齐，没有人手写的剧本
  source: 'rich' | 'generated' | 'runtime' | 'emergency'
}
```

**永远不返回 null。** 字表外的字（绘本 / 搜索 / 拍照认出来的生字）、空串、多字串
都会落到一个玩得完的关；多字串取第一个字。

| kind | props |
|---|---|
| `pick` | `options[{id,emoji,glyph,label,correct,reveal}]`、`need`、`cover`、`scene`、`sceneLabel`、`say`、`pinyin` |
| `catch` | `items[{id,emoji,glyph,label,hit,x,delay,duration}]`、`need`、`moving`、`cover`、`tool`、`target`、`sound` |
| `assemble` | `mode:'parts'\|'word'`、`whole`、`slots[{id,glyph}]`、`pieces[{id,glyph,label,correct}]`、`hint`（word 模式另有 `chars`、`blank`） |
| `watch` | `frames[{id,emoji,glyph,caption}]`（最后一帧必是这个字）、`button` |
| `match` | `left[{id,emoji,glyph,key}]`、`right[...]`、`need`（key 相同的算一对，允许多对一） |
| `push` | `hero`、`dir:'up'\|'down'\|'left'\|'right'`、`dirLabel`、`need` |

## 给富脚本岗 / 自动补齐岗

- 写一条最少三个字段：`{ char, template, narration }`；`props` 只写要换的那几件，
  缺的由归一层补齐，所以补脚本不会把舞台写空。
- `char-play-rich.js` 导出名不限：数组或 `{汉字: 条目}` 映射都会被自动收进注册表。
- 生成脚本可以在运行时注册：`import { registerCharPlays } from '@/data/char-play.js'`，
  `countRichPlays()` 会把它算进富脚本数（H3 探针读这个）。
- `findPlayHoles(chars?)` 返回玩不成的字，正常永远是空数组，可直接用在 check:data / smoke。
- 加新模板：在 `char-play.js` 的 `TEMPLATE_KIND` 里登记它归哪个 kind，再补一行
  `TEMPLATE_LABEL`。没登记也不会崩——按 `interaction` 归类，再不行归到 `catch`。

## 自测结果

`npm run test:play`（node，全库 1820 字）。校验的是**舞台真正读的那份道具**
（kind + props），不是 template 字段有没有值——`return { template: 'x' }` 骗得过探针，
骗不过孩子。六种 kind 各有一套「玩得完」的判据：对的选项够不够 need、
能接住的够不够、零件对不对得上空格、连线的左边在右边找不找得到伴。

```
char-play 自测：1820 字
  模板 19 种：emoji-hunt 303 / word-build 293 / tap-reveal 271 / pair-match 216 /
             scene-tap 204 / drag-parts 149 / rain-catch 125 / mirror-move 53 /
             swipe-motion 38 / sound-echo 31 / count-tap 24 / scene-poke 24 /
             sound-tap 19 / grow-tap 17 / sort-buckets 16 / pop-bubbles 13 /
             trace-path 10 / morph-story 7 / color-fill 7
  互动 6 种：pick 977 / assemble 442 / catch 246 / watch 77 / push 48 / match 30
  来源：generated 1548 / rich 272（模板补齐 1548 字，空洞 0）
✓ 全库每个字都有玩得完的场景
```

真机（无头 Chrome，520×1400 移动视口）逐关点完：

- 六种 kind × 两种来源的样板字 + 字表外的 `龘 A 7`，共 38 个舞台，在
  **默认 / `prefers-reduced-motion: reduce` / 全部按跳过** 三档下都走到
  `data-state=done`，`complete` 事件 38/38，控制台零报错零 Vue 警告。
- 全库等距抽 70 字（每 26 个取一个）默认档再走一遍：70/70 通关。

走查里改掉的三处：拼一拼的零件字号偏小（提到 `--fs-xl`）；道具只有一两件时
四等分网格把那张牌顶到左上角（改成居中换行）；`opened` 集合重开一关时没清空。

截图（同目录）：

- `play-kinds.png` —— 六种互动各一张（数一数 / 找一找 / 拼一拼 / 分一分 / 变一变 / 划一划）
- `play-templates.png` —— 接一接 / 揭一揭 / 补词语 / 听音点亮 / 场景点亮 / 戳一戳
- `play-reduced.png` —— 同上六关在 `prefers-reduced-motion: reduce` 下：
  会掉的道具改成静止网格，题面和通关条件一个字不变

浏览器走查用的是临时宿主（挂一排舞台 + puppeteer 点完），没有进仓：
仓里的常驻护栏是 `test:play`（数据契约）与 `scripts/smoke.mjs` 的 H7（真应用五步）。
**留给 smoke 岗一个缺口**：H7 目前只走「日」一个字，走的是 `watch`；
`match` / `assemble` 的判定写反了它看不出来。建议 H7 再带上 `不`（match）和
`山`（assemble）两个字，各点到 `data-state=done`。
