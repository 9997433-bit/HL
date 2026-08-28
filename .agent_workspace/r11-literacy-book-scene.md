Model slug: claude-opus-4-6-20260315
# Round 11 绘本页级场景组合样板

标记：`ROUND11_H4`（落在 `src/data/books.js`、`src/data/books/core.js`、
`src/components/BookPageScene.vue`、`scripts/smoke.mjs`）

## 结论

- 三本手写绘本共 **20 页**从「一页一个大 emoji」升级为多元素场景：
  `b1《我看大自然》`（L1，5 页）、`b10《小鸟回家》`（L2，7 页）、
  `b14《春夏秋冬》`（L3，8 页）。三本分属三个分级，用来验 DSL 在不同
  句长和情节密度下都够用。
- 其余 129 本一个字段没动，仍走单 emoji 路径；退化由 smoke 里的
  `data-scene="emoji"` 断言和 `check:data` 的兜底 emoji 断言双向守住。
- 用字零越界：场景旁白（读屏念的那句）与正文同规格校验，
  `verifySceneCoverage()` 接进 `check:data`，当前 0 越界。
- 体积：场景数据只落在按需加载的绘本块，首屏 JS 一个字节没变。

## DSL

场景写在页对象上，三个字段，都可选；不写就是老样子的单 emoji 页：

```js
{
  emoji: '🌅',                                  // 兜底插图，场景页也必须留着
  text: '天上有日，天上有月。',
  p: 'tiān shàng yǒu rì, tiān shàng yǒu yuè.',
  sceneBg: 'dawn',                              // 背景预设 id，缺省用绘本 palette
  sceneAlt: '天上有日，也有月',                   // 读屏念的一句话，受用字约束
  scene: [                                      // 元素数组，2–6 件
    { e: '☀️', x: 72, y: 24, s: 1.3, m: 'float' },
    { e: '🌙', x: 26, y: 28, s: 1,   m: 'float' },
    { e: '☁️', x: 48, y: 44, s: 1.1, m: 'drift' },
    { e: '⛰️', x: 34, y: 80, s: 1.8 }
  ]
}
```

| 字段 | 含义 | 约束 |
|---|---|---|
| `e` | 一个图形 | 必填；**不许放汉字**——要给孩子读的字都在正文里 |
| `x` / `y` | 舞台内百分比坐标 | 0–100；`y` 越大越靠近读者，渲染时按 `y` 排前后 |
| `s` | 相对大小 | 0.4–3，缺省 1 |
| `m` | 轻微动效 | `float` / `sway` / `drift` / `still`，缺省 `still` |
| `sceneBg` | 背景预设 | `SCENE_BACKDROPS` 九选一：dawn / sky / water / field / storm / dusk / night / snow / room |
| `sceneAlt` | 读屏旁白 | 必填；只能用字表内的汉字 + 标点 |

一页元素上限 `SCENE_ITEM_LIMIT = 6`：再多就挤成一团，孩子找不到主角。
下限是 2——只摆一件不如直接用 `emoji`，DSL 的意义就是「一页不止一件东西」。

## 渲染

`src/components/BookPageScene.vue`：

- 按 `y` 升序渲染，后画的自然压在前面，靠这个做前后层次；
- 元素按数据顺序错开 90 ms 入场，一件件落进画面；
- `role="img"` + `aria-label=sceneAlt`，元素本身 `aria-hidden`——
  读屏听到的是一句完整的话，不是四个 emoji 名字；
- 家长中心「减少动态」或系统 `prefers-reduced-motion` 开着时，
  入场和浮动一起停，画面照样是完整的多元素场景（规范 §3.4：
  动效不能是理解画面的唯一通道）；
- `scene` 为空时渲染原来的单 emoji（`data-scene="emoji"`）。

`BookReadView` 用 `:key="book.id + pageIndex"` 挂它，翻页整幅重挂，
所以每页的入场动画都会重放；朗读、点字、进度那几条线一行没改。

## 校验

`src/data/books.js` 出两个自检函数，都接进 `npm run check:data`：

- `verifyScenes()`——结构：元素是对象、坐标在画框内、大小在 0.4–3、
  动效在白名单、背景预设存在、旁白非空、兜底 emoji 还在、件数 2–6；
- `verifySceneCoverage()`——用字：旁白逐字比对 `CHARACTER_MAP`。

坐标越界这类错误不会抛异常，只会让半只小鸟挂在画框外边——静态数据错得
越安静越难发现，所以这些必须由门禁挡住，而不是等谁在真机上看见。

`check:data` 新增四条断言（实测全绿）：

```
✓ 页级场景样板 3 本 / 20 页（要求 ≥ 1 本且 ≥ 5 页）
✓ 场景元素的坐标、大小、动效和背景预设都合法（一页最多 6 件）
✓ 场景旁白也只用了字表内的汉字
✓ 每个场景页都至少两件元素且留着兜底 emoji
```

## 体积

`vite build`，同一台机器上基线（`7652d59`）与本分支对比：

| 产物 | 基线 | 本分支 | Δ |
|---|---|---|---|
| 入口 `index-*.js` | 312.17 kB（gzip 110.16 kB） | 312.17 kB（gzip 110.16 kB） | 0 |
| 绘本块 `books-*.js` | 119.36 kB（gzip 53.62 kB） | 123.34 kB（gzip 55.14 kB） | +3.98 kB（gzip +1.52 kB） |

场景数据全部落在按需加载的绘本块里，首屏预算不动；
`check:bundle` 实测首屏 JS 322 KB / 预算 420 KB，4 项通过 0 项失败。

## 回归

`scripts/smoke.mjs` 新增 `ROUND11_H4_SMOKE`（书是从数据里挑的，样板换本书
测试跟着走），一次交互里验五件事：

1. 首页场景渲染出的元素数与 `data-scene-items` 声明一致，且 ≥3 件；
2. 每件元素的中心点都落在舞台矩形内（坐标写错时半只小鸟挂在框外）；
3. 元素尺寸不止一种——`--s` 真的接上了，否则多元素退化成一排贴纸；
4. `role="img"` 且 `aria-label` 有实际内容；翻到下一页后整幅换掉；
5. 模拟 `prefers-reduced-motion: reduce` 重载后，所有元素
   `animationName === 'none'` 且件数不减；再挑一本没升级的书，
   断言它仍是单 emoji（`data-scene="emoji"`，`.scene__solo` 恰好 1 个）。
