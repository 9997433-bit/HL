# Play 引擎交付说明（Round 15 · 子代理 #4）

分支 `cursor/r15-play-engine-9f67`（from `cursor/r15-orchestration-9f67`）。
探针记号：源码里搜 `ROUND15_H2`。

## 交付物

| 文件 | 作用 |
|---|---|
| `apps/literacy-app/src/data/char-play.js` | `getCharPlay(char)` 运行时；富脚本注册表 + 模板补齐 |
| `apps/literacy-app/src/data/char-play-rich.js` | 手写脚本层（本轮 28 条，u1–u3），富脚本岗在此扩写 |
| `apps/literacy-app/src/components/CharPlayStage.vue` | 五模板舞台；`complete` / `skip` 两个事件 |
| `apps/literacy-app/scripts/test-char-play.mjs` | 全库逐模板道具校验（`npm run test:play`） |

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

- 组件按需加载即可：`char-play.js` 连同富脚本表都跟着这个异步块走，不进首屏。
- `autoStart`（默认 true）控制「接一接」要不要立刻下雨；这一步还没切到台前时传 false。
- `complete` 的 payload：`{ char, template, templateFallback, interactions, skipped }`。
  跳过也会 emit（`skipped: true`），所以父级的步骤机不会被一个小游戏卡住。
- 组件自带「跳过这一步」按钮与 `aria-live` 播报，父级不必再补。

## 数据契约

```ts
getCharPlay(char: string): {
  char: string
  theme: string            // PLAY_THEMES 的 key
  themeLabel: string
  themeEmoji: string
  accent: string           // 设计令牌，如 var(--leaf-500)
  template: string         // PLAY_TEMPLATE_IDS 之一
  templateLabel: string
  emoji: string
  narration: string
  props: object            // 见下表，模板不同字段不同
  templateFallback: boolean  // true = 自动补齐
}
```

**永远不返回 null。** 字表外的字（绘本 / 搜索点进来的生字）、空串、多字串都会落到一个
能玩完的模板关；模板不认识的 id 退回「点一点」。

| 模板 | props |
|---|---|
| `tap-reveal` | `items[{id,emoji,label,isChar}]`、`reveal`、`prompt` |
| `morph-story` | `frames[{id,emoji?,glyph?,caption}]`、`target`、`button` |
| `emoji-hunt` | `target`、`targetLabel`、`need`、`cells[{id,emoji,label,hit}]` |
| `drag-parts` | `whole`、`answer`、`answerName`、`options[{id,glyph,name,correct}]`、`hint` |
| `rain-catch` | `target`、`need`、`drops[{id,emoji,label,hit,x,delay,duration}]`、`staticCells[]` |

## 给富脚本岗 / 自动补齐岗

- 写一条最少三个字段：`{ char, template, narration }`；`props` 只写要换的那几件，
  其余照模板补齐，所以补脚本不会把舞台写空。
- `char-play-rich.js` 导出名不限：数组或 `{汉字: 条目}` 映射都会被自动收进注册表。
- 生成脚本可以在运行时注册：`import { registerCharPlays } from '@/data/char-play.js'`，
  传数组或映射即可，`countRichPlays()` 会把它算进富脚本数（H3 探针读这个）。
- `findPlayHoles(chars?)` 返回玩不成的字，正常永远是空数组，可直接用在 check:data / smoke。

## 自测结果

`npm run test:play`（node，全库）：

```
char-play 自测：1820 字，模板分布 morph-story 460 / emoji-hunt 419 / tap-reveal 407 / drag-parts 370 / rain-catch 164
富脚本 28 条，模板补齐 1792 字，空洞 0
✓ 全库每个字都有玩得完的场景
```

真机（无头 Chrome）逐关走通：五个模板样板 + 20 个无富脚本的冷门字，共 25 个舞台，
在 **默认 / prefers-reduced-motion: reduce / 全部按跳过** 三档下都走到 `data-state=done`，
`complete` 事件 25/25，控制台零报错零 Vue 警告。截图见同目录 `play-*.png`
（点一点 / 变一变 / 找一找 / 拼一拼 / 接一接各一张，420×900 移动视口）。
