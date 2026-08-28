# R18 · H4 应用题 steps 与剖析步数对齐

> 分支 `cursor/r18-wp-steps-align-9f67`（基线 `cursor/r18-orchestration-9f67` @ `770bded`）
> 门槛：**H4 一致率 ≥ 90%（≥193/214）** —— 实测 **214/214（100.0%）**

## 一句话结论

母题写着 `steps: 2`、剖析面板却只摊得出一步，孩子看到的两个数字对不上，先信哪个都是错的。
214 道母题里有 **56 道**这样（26%）。这一轮把它修到 **0 道**：一致率 **73.8% → 100.0%**，
其中 22 道是解析器真的少记了一步，34 道是 `steps` 字段一直兼着「难度档」这个不相干的职责。

难度档分布**一格没动**（一步 93 / 两步 86 / 进阶 35），所以这不是把题都摊平成一步换来的过关。

## 对齐前后

| | 对齐前 | 对齐后 |
|---|---|---|
| 一致 | 158 / 214 | **214 / 214** |
| 一致率 | 73.8% | **100.0%** |
| 不一致 | 56 | **0** |
| 剖析只有 1 步的母题 | 104 | 93 |
| 难度档（一步 / 两步 / 进阶） | 93 / 86 / 35 | 93 / 86 / 35（未变） |

56 道不一致按成因分两堆，修法完全不同：

| 成因 | 母题数 | 修在哪 |
|---|---|---|
| 有余数除法被压成一行，第二步兑不出来 | 22 | `analyzeEquation()` 拆步 |
| `steps` 兼职难度档，声明的不是字面步数 | 34 | `steps` 归还字面步数，难度另立 `tier` |

## 成因一：有余数的除法只记了一步（22 道）

`26 ÷ 4 = 6 …… 2` 从前在剖析里是**一行**：`display` 写成 `6 …… 2`，
「装满几份」和「还剩几个」被当成一个复合结果。于是 `div-remainder` / `left-over`
声明 2 步只讲得出 1 句，`minibus` / `ceil-pack` 声明 3 步只讲得出 2 句。

拆成两条并列的步骤：

```
① 26 ÷ 4     = 6   一份一份地分，分得出几份
② 26 − 4 × 6 = 2   分掉的拿走，剩下的才是余数
```

余数那一步写成**减法**而不是取模，是因为孩子手上真做的就是这个减法：
「装满的 6 袋每袋 4 颗，从 26 颗里减掉，手里剩的就是答案」。

两个细节：

- **问商的题不许提商。** 现有母题问的都是余数，但解析器不该假设这一点：
  `asked && !asksRemainder` 时，第二步的算式写成 `26 − 4 × ?`、文案里也不出现商，
  否则「盖住答案」的第一步会被第二步的说明白白念出来。
- **手写剖析补句时不能提商。** 商（装满几份）和余数可能撞成同一个数
  （`bags = 3` 且 `rest = 3`），被盖住的那一步一提商，`leaksAnswer()` 就判定泄题、
  整条链退回公式兜底。所以 `div-remainder` / `left-over` 的第二句只讲被除数和除数。

涉及母题：`div-remainder`、`minibus`、`left-over` ×10、`ceil-pack` ×10 = 22 道。

## 成因二：`steps` 一直兼着难度档（34 道）

原来的注释写得很直白：

> steps 表示解题步数，**也是难度分档**：1 = 一步题，2 = 两步题，>=3 = 进阶题
> （和差倍、鸡兔同笼、相遇这类需要先转换再计算的题型）。

一个字段扛两件事，冲突就出现在两头：

- `meet`、`sum-diff`、`sum-times`、`sum-gap` 声明 **3** 步，算式上只有 **2** 次计算
  （`(22 + 4) ÷ 2`）——难的是想到那一次假设，不是多算一步。
- `average`、`mean` 声明 **2** 步，三天的页数要加两次再除一次，实际 **3** 次计算。

现在把两件事拆开写：

```js
steps: 2,        // 字面上要算几步，必须和 buildAnalysis() 拆出来的对得上
tier: 'multi',   // 难度档（one / two / multi），不写就按 steps 推
```

`tierOf(problem)` 统一兜底（`>=3 → multi`，`2 → two`，其余 `one`），
`WORD_PROBLEM_TIERS` 的三个匹配器改成走它。校正后：

| 母题 | steps | tier | 为什么 |
|---|---|---|---|
| `meet` | 3 → **2** | `multi` | 求速度和 + 求时间；难在想到要先合速度 |
| `sum-diff` / `sum-gap` ×11 | 3 → **2** | `multi` | 补齐 + 对半分；难在那一次假设 |
| `sum-times`（手写 + 语义 ×10）×11 | 3 → **2** | `multi` | 凑份数 + 求一份；难在把倍数看成份数 |
| `average` / `mean` ×11 | 2 → **3** | `two` | 算式三次计算；想法仍是「先合起来再平分」两步 |

因为进阶档的题靠 `tier` 顶住、平均数靠 `tier` 留在两步档，**难度档分布一格没动**。
界面上的星星数、XP、错因标签（`one-step` / `two-step` / `multi-step`）和角标文字
一并改成跟着 `tier` 走，而不是字面步数——否则校正 `steps` 会顺手把给分改了。

```js
const TIER_REWARD = {
  one:   { stars: 2, xp: 14, tag: 'one-step',   label: '一步' },
  two:   { stars: 3, xp: 20, tag: 'two-step',   label: '两步' },
  multi: { stars: 4, xp: 26, tag: 'multi-step', label: '进阶' },
}
```

## 落点

| 文件 | 干了什么 |
|---|---|
| `apps/math-app/src/utils/wpAnalysis.js` | 有余数除法拆成商 / 余数两步；步骤带 `part` 字段；导出 `ROUND18_H4` |
| `apps/math-app/src/utils/wpSteps.js` | **新增**：`auditStepAlignment()` 等纯函数，门禁 / 报表 / 探针共用 |
| `apps/math-app/src/data/wordProblems.js` | `steps` 归还字面步数；新增 `tier` 与 `tierOf()`；难度档匹配器改走 `tier` |
| `apps/math-app/src/data/word-problem-explains.js` | 四条余数剖析各补上余数那一句（1→2 / 2→3 句） |
| `apps/math-app/src/modules/word-problems/WordProblemsView.vue` | 星星 / XP / 错因标签 / 角标改看 `tier` |
| `apps/math-app/scripts/check-content.mjs` | 落 ROUND18_H4 门禁（每题抽 60 次，验收线 90%） |
| `apps/math-app/scripts/wp-steps-report.mjs` | **新增**：可复现报表，`npm run report:wp-steps` |

## 计数口径（探针可复用）

对账逻辑抽成 `src/utils/wpSteps.js` 的纯函数，因为在这之前已经有三处各写一份
for 循环了，各算各的迟早算出三个数：

```js
import { auditStepAlignment, STEPS_ALIGN_TARGET } from '@/utils/wpSteps.js'

const report = auditStepAlignment(WORD_PROBLEMS, { tries: 60, seed: 20250418 })
// → { total, aligned, rate, rows, mismatched: [{ id, declared, analyzed, equation }], tries }
report.rate >= STEPS_ALIGN_TARGET   // 验收线 0.9
```

一个母题算「对齐」，要它在 `tries` 次随机取值下**每次**都拆出声明的步数——
只抽一次会漏掉「取值碰巧才多一步」的母题。`seed` 给了就逐字复现。

`wpAnalysis.js` 导出 `ROUND18_H4 = 'wp-steps-alignment'`，Round 18 的探针
（`apps/math-app/scripts/verify-wp-steps.mjs`，子代理 #3）据此从观测模式自动切到断言模式。

## 实际渲染抽样

`reseed('r18-h4-evidence')`，`?` 是判题前盖住的得数：

```
### div-remainder（steps 2 / 难度档 two）
题面：小星有 8 颗糖，每 3 颗装一袋。装满若干袋后，还剩多少颗糖？
思路：有余数的除法要报两个数：装满了几袋、还剩几颗。这道题问的是剩下的那几颗。
1. 8 ÷ 3 = 2       —— 8 颗糖每 3 颗装一袋，一袋一袋地装下去，装到凑不满一袋为止，能装满 2 袋。
2. 8 − 3 × 2 = ?   —— 装满的每一袋都正好 3 颗，把装进袋子的糖都从 8 颗里拿走，手里剩下的那几颗就是答案。

### minibus（steps 3 / 难度档 multi）
题面：25 个小朋友去春游，每辆小车最多坐 6 人。至少要几辆车才能都坐下？
思路：进一法：除完余下的小朋友不能丢在路边，哪怕只剩 1 个也要再派一辆车。
1. 25 ÷ 6 = 4       —— 25 个小朋友、每车 6 人，一辆一辆地坐，能坐满 4 辆。
2. 25 − 6 × 4 = 1   —— 坐满的车每辆 6 人、一共 4 辆，把坐上车的从 25 个小朋友里减掉，剩下的还在路边等。
3. 4 + 1 = ?        —— 余下的人也要上车，所以在坐满的 4 辆上再加 1 辆。

### left-over-bakery（steps 2 / 难度档 two）
题面：有 23 个可颂，每 4 个装一袋。装满若干袋后，还剩多少个？
思路：有余数的除法要报两个数：装满了几份、还剩几个。这道题问的是剩下的那几个。
1. 23 ÷ 4 = 5       —— 23 个每 4 个装一份，一份一份地装下去，能装满 5 份。
2. 23 − 4 × 5 = ?   —— 装满的每一份都正好 4 个，把装进去的都从 23 个里拿走，剩下的就是答案。

### ceil-pack-reef（steps 3 / 难度档 multi）
题面：有 11 条小丑鱼，每缸最多装 4 条。至少要几缸才能全部装下？
思路：进一法：除完余下的那几个也得有地方放，所以要在装满的份数上再加一份。
1. 11 ÷ 4 = 2       —— 一共 11 个，每缸最多装 4 个，一缸一缸地装，能装满 2 缸。
2. 11 − 4 × 2 = 3   —— 装满的部分每缸 4 个、一共 2 缸，从 11 个里减掉，剩下的就是还没地方放的。
3. 2 + 1 = ?        —— 余下的也要装，所以在装满的 2 缸上再加 1 缸。

### meet（steps 2 / 难度档 multi）
题面：小星和朵朵从相距 249 米的两地同时出发，面对面走来。小星每分钟走 42 米，朵朵每分钟走 41 米。几分钟后两人相遇？
思路：相遇题先把两人的速度合成「每分钟一共靠近多少米」，再看这段路里有几个这么多。
1. 42 + 41 = 83     —— 两人面对面走，一个每分钟 42 米、一个 41 米，一分钟两人之间就近这么多。
2. 249 ÷ 83 = ?     —— 两地相距 249 米，每分钟近 83 米，看看 249 里面有几个 83。

### sum-diff（steps 2 / 难度档 multi）
题面：乐乐和朵朵一共有 22 张卡片，乐乐比朵朵多 4 张。乐乐有多少张卡片？
思路：和差问题：先把少的那个人补齐到和多的一样多，总数就能干干净净地对半分。
1. 22 + 4 = 26      —— 假装少的那个人也有那么多：总数 22 张再添上相差的 4 张。
2. 26 ÷ 2 = ?       —— 现在两人一样多了，把 26 张平均分成 2 份，一份就是多的那个人的。

### mean-snow（steps 3 / 难度档 two）
题面：阿光三天分别滚了 6、9、12 个雪球。平均每天滚多少个？
思路：平均数是「先合起来再平分」：把多的匀给少的，让三天变得一样多。
1. 6 + 9 = 15       —— 先把前两天的 6 个和 9 个加起来。
2. 15 + 12 = 27     —— 再添上第三天的 12 个，三天一共这么多。
3. 27 ÷ 3 = ?       —— 三天共 27 个，平均分回 3 天，每天摊到的就是平均数。

### chicken-rabbit（steps 3 / 难度档 multi）—— 基线就对齐，回归对照用
题面：笼子里有鸡和兔一共 9 只，数一数腿有 24 条。笼子里有多少只兔子？
1. 9 × 2 = 18       —— 先假设笼子里全是鸡：9 个头，每只 2 条腿。
2. 24 − 18 = 6      —— 实际数出 24 条腿，比假设的 18 条多，多出来的都是兔子多长的。
3. 6 ÷ 2 = ?        —— 一只兔子比一只鸡多 2 条腿，多出的 6 条里有几个 2，就有几只兔子。
```

`ceil-pack-reef` 说「装一缸」、`left-over-bakery` 说「装一份」——量词仍是从
`question.unit` 取的，同一条语义剖析套十张皮肤都不串味（Round 17 的约束没被拆步破坏）。

## 顺带修的一处内容 bug

`average` 的三天页数是 `avg − d`、`avg`、`avg + d`，而 `d = randInt(0, 2)`。
`d` 落到 0 时题面成了「三天分别读了 3、3、3 页书。平均每天读多少页？」——
平均数不用算就知道。收成 `randInt(1, 2)`，与语义模板 `mean` 早就写死的 `randInt(1, 3)` 对齐。
（抽样时撞见的，就在同一段代码里，顺手带上。）

## 复现命令

```bash
# 对齐报表（不判对错，只打数）
npm --prefix apps/math-app run report:wp-steps
npm --prefix apps/math-app run report:wp-steps -- --json --tries=200

# 内容自检（含 ROUND18_H4 门禁，每题抽 60 次）
npm --prefix apps/math-app run check:content

# Round 18 探针（子代理 #3 的脚本，标记就位后自动进断言模式）
node apps/math-app/scripts/verify-wp-steps.mjs --samples=8
```

## 复现输出

```
$ npm --prefix apps/math-app run report:wp-steps
ROUND18_H4 应用题 steps 对齐：214/214（100.0%），验收线 90.0%，每个母题抽 40 次
  声明步数分布：1 步 ×93 · 2 步 ×98 · 3 步 ×23
  剖析步数分布：1 步 ×93 · 2 步 ×98 · 3 步 ×23
  难度档分布：一步 93 · 两步 86 · 进阶 35
  ✓ 每一道母题声明的步数都和剖析拆出来的一致

$ npm --prefix apps/math-app run check:content
应用题母题 214 个：
  28 类语义标签 / 42 种场景，一步 93 · 两步 86 · 进阶 35，每个母题各生成 2000 道
应用题步数对齐：214/214（100.0%，验收线 90.0%），每题抽 60 次；声明 1 步 ×93 · 2 步 ×98 · 3 步 ×23
应用题剖析：214 个母题 × 30 次共 6420 道，图示 / 分步 / 盖住答案全部成立
手写剖析 50 条覆盖 214/214 个母题：200 次随机取值共 71600 句（去重 15346），
整题思路 / 图示说明 / 每一步都是手写，且判题前不写出答案
...
全部通过。

$ node apps/math-app/scripts/verify-wp-steps.mjs --samples=8
ROUND18_H4: 214/214 templates aligned (100.0%), 8 sample(s) each
✓ ROUND18_H4 target met (≥90%)
```

对齐前同一条探针的输出（基线 `770bded`）：

```
ROUND18_H4: 158/214 templates aligned (73.8%), 5 sample(s) each
  - div-remainder: declared=2, analysis=1
  - minibus: declared=3, analysis=2
  - meet: declared=3, analysis=2
  - sum-diff: declared=3, analysis=2
  - sum-times: declared=3, analysis=2
  - average: declared=2, analysis=3
  - sum-times-shell: declared=3, analysis=2
  … 44 more mismatch(es)
○ ROUND18_H4 PENDING: marker not available; metric and stable assertions passed
```

## 不退化

| 项 | 结果 |
|---|---|
| `check:content` | 全部通过（新增步数对齐一节；手写剖析 214/214 覆盖不变） |
| `vite build` | ✓ built in 7.72s，无告警 |
| `check:bundle` | 数学首屏 93936 B gzip < 250 KiB |
| `check:route-budget` | 18/18 组通过 |
| 难度档题量 | 一步 93 / 两步 86 / 进阶 35，与基线逐档相同 |
| 星星 · XP | 逐档相同（2/14、3/20、4/26），只是改由 `tier` 决定 |

剖析壳分包 `WpAnalysisPanel` 19.57 kB raw / 10.19 kB gzip（余数拆步 + 四条剖析补句
带来的增量在 0.3 KiB 量级）。它只在孩子点「🔍 剖析这道题」时才下载，不进首屏。

## 给编排的两条提醒

1. **和 #7（手写剖析 50→≥80）改同一个文件。** 本分支动了
   `word-problem-explains.js` 里 `div-remainder` / `left-over` / `minibus` / `ceil-pack`
   四条的 `steps` 数组（各多一句），合入时按条取并集即可。
2. **新写剖析的句数要跟着新的拆步走。** 有余数除法现在是**两步**，
   写 `left-over` 那类母题的剖析必须给两句，少一句 `check:content` 会报
   「第 N 步退回了公式兜底」。`npm run report:wp-steps` 可以直接查每道题该写几句。
