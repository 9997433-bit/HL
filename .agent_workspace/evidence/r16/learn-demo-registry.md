# ROUND16_H4 学演示注册表

数学 App 的「学演示」回答的是开练之前的那个问题：**这个知识点到底在讲什么**。
每条演示都走同一个三段契约，缺一段就不算数：

| 段 | 内容 | 作用 |
|---|---|---|
| ① 实物 | 孩子在生活里见过的东西 | 看得见、数得清 |
| ② 图形 | 同构的点 / 格子 / 对称轴 | 数量关系还在，具体的物没了 |
| ③ 算式 | 一行符号 | 把图形关系压成算式 |

旁白正好三句，一段一句，跳过时单独一句也读得懂。

| 件 | 路径 |
|---|---|
| 数据（标记 `ROUND16_H4`） | `apps/math-app/src/data/learn-demos.js` |
| 技能清单（练习入口静态引用的轻量索引） | `apps/math-app/src/data/learn-demo-index.js` |
| 播放壳 | `apps/math-app/src/components/LearnDemo.vue` |
| 玩法页入口（按钮 + 弹层） | `apps/math-app/src/components/LearnDemoLauncher.vue` |
| 演示中心 `/#/visual-demos` | `apps/math-app/src/modules/visual-demos/VisualDemosView.vue` |
| 定点验收 | `apps/math-app/scripts/verify-learn-demo.mjs` |

## 覆盖清单（21 个技能点 ≥ 12）

一个技能点最多挂一条演示，`check:content` 会对重复报错。

| # | 技能点 | 名称 | 档 | 模块 | 演示 id | 实物 | 图形 | 算式 |
|---|---|---|---|---|---|---|---|---|
| 1 | `count-to-5` | 5以内点数 | L1 | number-sense | `count-to-5` | 池塘里 4 只小鸭 | 4 个圆点 | `4` |
| 2 | `count-to-10` | 10以内点数 | L1 | number-sense | `counting` | 5 个苹果 | 5 个圆点 | `5` |
| 3 | `count-to-20` | 20以内点数 | L2 | number-sense | `teen-ten-frame` | 13 颗糖：装满一盒外加 3 颗 | 一框满十，另放 3 个 | `10 + 3 = 13` |
| 4 | `number-order` | 数序与相邻数 | L2 | number-sense | `number-order` | 三摞积木：5、6、7 块 | 一列比一列多一个点 | `5 < 6 < 7` |
| 5 | `compare-to-10` | 10以内比大小 | L1 | number-sense | `comparison` | 5 块和 3 块饼干 | 上下配对，多出 2 个 | `5 > 3` |
| 6 | `compare-to-20` | 20以内比大小 | L2 | number-sense | `compare-teen` | 12 个和 15 个贝壳 | 每行 5 个摆齐，右边多 3 个 | `12 < 15` |
| 7 | `compose-ten` | 10的分与合 | L2 | number-sense | `compose-ten` | 10 颗弹珠分两舱 | 十格框里 6 格和 4 格 | `6 + 4 = 10` |
| 8 | `add-within-10` | 10以内加法 | L2 | arithmetic | `addition` | 3 艘和 2 艘飞船 | 两组圆点合在一起 | `3 + 2 = 5` |
| 9 | `sub-within-10` | 10以内减法 | L2 | arithmetic | `subtraction` | 6 颗星拿走 2 颗 | 划掉最后 2 个圆点 | `6 − 2 = 4` |
| 10 | `add-carry-20` | 20以内进位加 | L3 | arithmetic | `make-ten-add` | 9 盒果汁又来 5 盒 | 左边先填满十，右边剩 4 | `9 + 5 = 14` |
| 11 | `sub-borrow-20` | 20以内退位减 | L3 | arithmetic | `break-ten-sub` | 13 个面包吃掉 5 个 | 拆成 10 和 3，只从 10 里拿 | `13 − 5 = 8` |
| 12 | `add-within-100` | 100以内加法 | L3 | arithmetic | `add-tens-ones` | 3 捆小棒再加 2 捆零 5 根 | 先合整十，再补个位 | `30 + 25 = 55` |
| 13 | `sub-within-100` | 100以内减法 | L3 | arithmetic | `sub-tens-ones` | 46 根小棒：4 捆零 6 根 | 只从捆里拿，散的没少 | `46 − 20 = 26` |
| 14 | `mul-table` | 乘法口诀 | L4 | arithmetic | `multiplication` | 2 盆花，每盆 3 朵 | 2 组，每组 3 个圆点 | `2 × 3 = 6` |
| 15 | `div-basic` | 表内除法 | L4 | arithmetic | `division` | 6 颗草莓平均放 3 盘 | 3 个圈，每圈 2 个点 | `6 ÷ 3 = 2` |
| 16 | `shape-2d` | 认识平面图形 | L1 | geometry | `fraction` | 一张完整的披萨 | 平均分成 2 份取 1 份 | `1 ÷ 2 = ½` |
| 17 | `symmetry` | 对称图形 | L3 | geometry | `symmetry-fold` | 蝴蝶沿身体中线对折 | 对称轴两边点数一样多 | `3 = 3` |
| 18 | `pattern-abab` | 循环规律(ABAB) | L1 | logic | `pattern-abab` | 红蓝红蓝……串珠 | 每 2 颗一节，反复 3 次 | `2 × 3 = 6` |
| 19 | `pattern-number` | 数列规律 | L3 | logic | `pattern-number` | 三堆金币：2、4、6 枚 | 每堆比前一堆多 2 个点 | `6 + 2 = 8` |
| 20 | `wp-combine` | 合并问题 | L2 | word-problems | `wp-combine` | 鱼缸 4 条又放进 3 条 | 两部分并成一个整体 | `4 + 3 = 7` |
| 21 | `wp-remain` | 剩余问题 | L2 | word-problems | `wp-remain` | 8 个气球飞走 3 个 | 划掉飞走的那部分 | `8 − 3 = 5` |

机读清单（技能 id，与 `learn-demo-index.js` 逐项对齐）：

- `count-to-5`
- `count-to-10`
- `count-to-20`
- `number-order`
- `compare-to-10`
- `compare-to-20`
- `compose-ten`
- `add-within-10`
- `sub-within-10`
- `add-carry-20`
- `sub-borrow-20`
- `add-within-100`
- `sub-within-100`
- `mul-table`
- `div-basic`
- `shape-2d`
- `symmetry`
- `pattern-abab`
- `pattern-number`
- `wp-combine`
- `wp-remain`

## 按学科模块

| 模块 | 覆盖 / 图谱技能数 | 还没有演示的技能点 |
|---|---|---|
| number-sense 数量星云 | 7 / 8 | `number-trace` |
| arithmetic 算术恒星 | 8 / 8 | — |
| geometry 形状卫星 | 2 / 4 | `tangram-basic`、`shape-3d` |
| logic 规律环带 | 2 / 5 | `classify`、`maze-condition`、`deduction` |
| word-problems 生活行星 | 2 / 6 | `wp-diff`、`wp-times`、`wp-share`、`wp-two-step` |
| sudoku 数独空间站 | 0 / 3 | `sudoku-4`、`sudoku-6`、`sudoku-9` |
| **合计** | **21 / 34** | 13 |

没覆盖的这 13 个是有意留的，不是漏掉：数独、迷宫、七巧板这类技能的核心不是
「一个数量关系怎么抽象成算式」，硬套三段只会得到一条编出来的算式。它们本来就
靠玩法本身的操作反馈来教，演示入口按 `learn-demo-index.js` 判断有没有，
没有就不摆按钮，不给死链接。

## 入口

| 位置 | 交互 | 钩子 |
|---|---|---|
| 首页「动手学数学」 | 卡片直达演示中心，副标题写出技能点总数 | `HomeView.vue` → `/visual-demos` |
| 演示中心 | 按星球分组的技能点卡；深链 `?demo=` / `?skill=` | `[data-demo-select]`、`[data-demo-select-skill]` |
| 技能图谱详情卡 | 「🎞️ 先看演示」，只在该技能有演示时出现 | `[data-learn-demo-link]` |
| 星球练习页题头 | 「🎞️ 看演示」就地弹层，收起后继续练 | `[data-learn-demo-open]`、`[data-learn-demo-layer]` |

题头入口挂在这几处，覆盖了全部 21 个有演示的技能点：

| 页面 | 当前技能点从哪来 |
|---|---|
| 算术恒星 `/arithmetic`、速算冲刺、今日冒险、生活行星 | `QuizShell` 的当前题 `skill` |
| 数量星云 `/number-sense`、比大小擂台 | `countingSkill(current)` |
| 形状卫星 `/geometry` | `geometrySkill(current.target)` |
| 规律环带 `/logic` | `logicSkill(current.type)` |
| 10 的分与合 `/compose-ten` | 整页只练 `compose-ten` |

技能点取的都是判题时上报掌握度的同一条口径，弹的演示和这道题算在同一个技能上。
七巧板、数独、配对记忆、逻辑迷宫的技能点还没有演示，按 `learn-demo-index.js`
判断后不渲染按钮，不摆死入口。

弹层不打断本轮：题序、连击、计时都不重置，弹层盖着时数字键不再落到选项上
（`Esc` 收起）。换到下一题会自动收起上一题的演示。

## 可跳过与 reduced-motion

| 状态 | 行为 | 标记 |
|---|---|---|
| 播放态 | 三段每 1.5 秒自动推进；「跳过演示」直接到算式段，「重播」回实物段，「下一步」手动推进 | `data-demo-motion="play"` |
| 静态态 | 不播了：三段同屏铺开、三句旁白按 ①②③ 一次列全；不再给「重播」 | `data-demo-motion="static"` |

静态态在两种情况下生效：系统 `prefers-reduced-motion: reduce`，或家长在设置里
关掉动效（两者都由 `utils/motion.js` 的 `reducedMotion()` 统一判定）。关键点是
**关掉动画不等于只看得到第一段**——逐句旁白没人替孩子翻页，所以静态态把三句
一次列全，整条「实物 → 图形 → 算式」的推理链在静止画面里读得完。

## 门禁

| 检查 | 结果 |
|---|---|
| `npm run check:content -w math-app` | ✅ 21 个技能点、三段齐全、三句旁白、技能点唯一且在图谱里、模块与图谱一致、`learn-demo-index` 与注册表逐项对齐 |
| `node scripts/verify-learn-demo.mjs`（定点） | ✅ 11/11：演示中心 21 个技能点、跳过到算式、换条重播、`?skill=` 深链、reduced-motion 静态三态、五处玩法页入口弹出收起、图谱只给有演示的技能挂链接 |
| `node scripts/smoke.mjs`（math 全量） | ✅ 20 条路由 + 38 项交互全绿；三条断言进了权威门禁（演示中心 / reduced-motion / 算术恒星入口 + 数字键不误判），摘录见 `learn-demo-smoke.md` |
| `npm run check:route-budget -w math-app` | ✅ 18/18 组通过，`/visual-demos` 5.7 / 24 KiB gzip；演示壳与注册表按需加载，练习路由只静态引技能清单 |
| `npm run check:round16` | ✅ H4 21 ≥ 12（计数取注册表 `skillId` 条数与本文清单的最大值） |

定点验收输出：

```
 ✓ 演示中心：21 个技能点 + 跳过到算式 —— 21 个技能点，object → equation（4）
 ✓ 演示中心：换一条演示重新从实物段播 —— division / div-basic 从 object 段重播
 ✓ 演示中心：?skill= 深链直接定位 —— ?skill=symmetry → symmetry-fold
 ✓ reduced-motion：静态三态仍可读 —— 三面板不透明度 1/1/1，旁白 3 句全列，算式 4
 ✓ 算术恒星：练习入口就地弹出演示 —— add-within-10（🎯 10以内加法）弹出并收起，练习壳还在
 ✓ 生活行星：练习入口就地弹出演示 —— wp-remain（🎯 剩余问题）弹出并收起，练习壳还在
 ✓ 数量星云：练习入口就地弹出演示 —— count-to-10（🎯 10以内点数）弹出并收起，练习壳还在
 ✓ 形状卫星：练习入口就地弹出演示 —— shape-2d（🎯 认识平面图形）弹出并收起，练习壳还在
 ✓ 规律环带：练习入口就地弹出演示 —— pattern-number（🎯 数列规律）弹出并收起，练习壳还在
 ✓ 10 的分与合：练习入口就地弹出演示 —— compose-ten（🎯 10的分与合）弹出并收起，练习壳还在
 ✓ 技能图谱：只给有演示的技能点挂链接 —— mul-table 有「先看演示」，sudoku-4 没有

ROUND16_H4 学演示定点验收：11/11 通过。
```
