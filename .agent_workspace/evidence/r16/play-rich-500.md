# Round 16 · H3 富 Play 从 272 扩到 640 条（u1–u40）

分支：`cursor/r16-play-rich-500-9f67`（基线 `cursor/r16-orchestration-9f67` @ 1634b8e）
Model slug：claude-opus-5-thinking-high-fast
门槛：`countRichPlays() ≥ 500`，`templateFallback ≠ true`，旁白去重达标

## 结论

| 口径 | R15 | 本批 |
|---|---|---|
| 手写富脚本 | 272 条（u1–u20） | **640 条（u1–u40）** |
| 旁白不重样 | 272 | **640**（撞句率 0） |
| 模板补齐（`templateFallback: true`） | 1548 字 | 1180 字 |
| 全库空洞 | 0 | 0 |

`check-round16.mjs` 的 H3 从红转绿：`✓ H3 富 Play 640 ≥ 500`。

## 实测

```
$ npm run check:play:rich
[play-rich] seed 校验通过：640 条，覆盖 40 个单元、16 个模板，旁白 640 句不重样。

$ npm run gen:play:rich
[play-rich] 640 条富脚本，覆盖 40 个单元（u1–u40），约 176 KB。
[play-rich] 模板分布：count-tap 59、swipe-motion 99、morph-story 17、sound-tap 30、
grow-tap 51、emoji-hunt 36、tap-reveal 61、drag-parts 50、trace-path 43、scene-poke 50、
sort-buckets 42、pair-match 29、pop-bubbles 33、rain-catch 16、word-build 6、color-fill 18

$ npm run test:play
char-play 自测：1820 字
  模板 19 种 / 互动 6 种：pick 772 / assemble 369 / catch 356 / push 142 / watch 110 / match 71
  来源：generated 1180 / rich 640（模板补齐 1180 字，空洞 0）
✓ 全库每个字都有玩得完的场景

$ node scripts/check-round16.mjs
✓ H3 富 Play 640 ≥ 500

$ node scripts/check-round15.mjs
✓ H3 富 play 脚本 640 ≥ 200，narration 去重 640 ≥ 160（runtime，fallback=1180）

$ npm run check:data
内容自检：80 项通过，0 项失败。

$ npm run build && npm run check:bundle
✓ 首屏 JS 325 KB（预算 420 KB）；构建产物体检：4 项通过，0 项失败。
```

## 新写的 368 条长什么样

一条脚本合格的标准不是「有模板有旁白」，是**玩法本身就在解释这个字**。
抽几条新单元的：

| 字 | 单元 | 模板 | 玩什么 |
|---|---|---|---|
| 慢 | u21 | `trace-path` | 小蜗牛一点一点往前挪，快不了 |
| 静 | u21 | `pop-bubbles` | 把喇叭、铃铛、收音机一个个关掉，剩下安静 |
| 干 | u23 | `morph-story` | 湿衣服晒着晒着，最后一帧落成「干」字 |
| 井 | u23 | `drag-parts` | 两横两竖拼出字形 |
| 森 | u24 | `drag-parts` | 三个「木」挤到一起 |
| 蟹 | u25 | `swipe-motion` | 只能往旁边横着划 |
| 熟 | u26 | `morph-story` | 青果子 🟢→🟠→「熟」 |
| 离 / 迎 | u27 | `swipe-motion` | 一个划开、一个划回，方向正好相反 |
| 因 / 为 | u30 | `pair-match` | 下雨配伞、冷了配外套，连的是因果不是图案 |
| 休 | u33 | `drag-parts` | 「亻」靠着「木」，人靠树就是休 |
| 改 | u34 | `morph-story` | ❌ → 🧽 → 「改」 |
| 秤 | u40 | `sort-buckets` | 沉的往下压、飘的往上翘 |

方向类的字互相之间也对得上：`拉/推`（R15）、`近/远`、`迎/离`、`回/去`
用的是相反的 `dir`，孩子连着玩能感觉出来这一组是一对。

## 管道侧改了两处

1. `RICH_UNIT_LIMIT` 20 → 40。这个常量只管「超出手写覆盖」的提醒，
   往后写 u41+ 继续抬。
2. **旁白撞句从没人管改成判错**。这是这批扩写最需要的护栏：500 条的门槛
   很容易用「一句话复制 200 份」凑出来，条数骗得过探针，孩子听三个字就
   听出来了。现在生成阶段直接报错并指出和哪个字撞了，同时导出
   `countRichNarrations()` 给探针复核（R15 v1.1 的 narration 去重口径）。

## 包体

`char-play-rich.js` 76 KB → 176 KB 源码。它只被「玩」这一步用，落在
`CharDetailView` 的懒加载块里（275 KB / gzip 97 KB），首屏 325 KB 不受影响，
`check:bundle` 4 项全绿。**别把它 import 进同步入口**。

## 接口没变

```js
import { getRichPlay, countRichPlays, countRichNarrations } from '@/data/char-play-rich.js'
```

条目形状仍是 `{ char, unit, theme, template, interaction, narration, props, templateFallback: false }`，
`char-play.js` 的归一层（六种 kind）一行没动，#4/#7 那两岗不用跟着改。

## 后面还能扩

u41–u99 共 1180 字仍走模板补齐。seed 行格式没变，续写时先确认
`RICH_UNIT_LIMIT` 盖得住，再跑 `npm run check:play:rich` —— 撞句和道具缺件
都会在落盘前拦下来。
