# R19 · H5 精品剖析 ≥150（手写剖析链续写）

> 分支 `cursor/r19-wp-explain-150-9f67`（基线 `origin/cursor/r19-orchestration-9f67`）
> 门槛：**H5 精品剖析 ≥150** —— 去重母题手写链 ≥150，去重中文讲解句 ≥400，可执行 `ROUND19_H5`

## 一句话结论

手写剖析由 **85 → 150** 条（+65 条皮肤专写），`explainSentences()` 去重中文句 **298 → 517**（≥400）。
经语义模板 × 场景皮肤展开后仍覆盖 **214 / 214** 个应用题母题；步数与 `buildAnalysis` 对齐 **214/214（100%）**，判题前不泄答案。

## 落点

| 文件 | 干了什么 |
|---|---|
| `apps/math-app/src/data/word-problem-explains.js` | 续写 65 条皮肤专写；导出 `ROUND19_H5 = 'crafted-explain-chain-150'` |
| `apps/math-app/src/utils/wpAnalysis.js` | 再导出 `ROUND19_H5`（与 R17/R18 标记并存） |
| `apps/math-app/src/components/WpAnalysisPanel.vue` | `data-explain-chain` 挂到 `ROUND19_H5` |

## 数字线

| 口径 | R18 末 | 本轮 | 门槛 |
|---|---|---|---|
| `EXPLAIN_COUNT`（登记条数） | 85 | **150** | ≥150 |
| `EXPLAIN_SENTENCE_COUNT`（去重讲解句） | 298 | **517** | ≥400 |
| 门禁静态去重中文句（引号/` 切分） | — | **548** | ≥400 |
| 母题覆盖（展开后） | 214/214 | **214/214** | — |
| 步数对齐（ROUND18_H4） | 214/214 | **214/214（100%）** | ≥90% |

分层：

| 层 | 条数 | 说明 |
|---|---|---|
| 手写母题 | 34 | 题面独一份，点名道姓（含与语义同名的 `share` / `sum-times`） |
| 语义模板 | 16 | 一条管住十张皮肤，不许写死皮肤名词 |
| 皮肤专写 | **100** | R18 的 35 + 本轮 65；id = `语义-皮肤`，可点名道姓 |

## 本轮补的 65 个组合

优先把 R18 没轮到的难讲结构补齐：

- **和差** `sum-gap`：post / market / reef / snow / mine（5）
- **和倍** `sum-times`：shell / bakery / space / bug / bamboo（5）
- **进一法** `ceil-pack`：bakery / bug / post / reef / mine（5）
- **有余数** `left-over`：shell / space / bamboo / market / snow（5）
- **比多少两步** `both`：bamboo / post / market / reef / snow / mine（6）
- **两步拿走** `twice-away`：space / bug / bamboo / post / market / reef（6）
- **先乘再减** `pack-loss`：shell / bakery / post / market / reef / snow / mine（7）
- **一进一出** `flow`：十张皮肤全补（10）
- **比多少一步** `gap`：shell / bakery / space / bug / market / reef / snow / mine（8）
- **比…少** `fewer`：shell / bakery / space / bug / bamboo / post / snow / mine（8）

## 红线（R18 交接，本轮复验）

1. **steps 长度 = `buildAnalysis` 步数。** 进一法 3 步（有余数拆两步 + 再加一）、有余数 2 步、和差/和倍 2 步。写错长度则 `handwritten` 招牌挂不上。
2. **判题前不泄答案。** 被问的那一步文案不许出现得数；有余数第二句不提商（商可能和余数撞号）。
3. **语义条仍不许写死皮肤名词**；皮肤专写可以点名道姓。

## 实际渲染抽样

`reseed('r19-h5-evidence')` 下抽 8 道（`?` 是判题前盖住的得数）：

```
### sum-gap-post
题面：大熊和朵朵一共写了 28 张明信片，大熊比朵朵多写了 4 张。大熊写了多少张？
思路：两人一共写了多少张、谁比谁多写几张都知道——先把少的那位补齐，再把补齐后的总数对半分。
1. 28 + 4 = 32  —— 先假装写得少的那位也写到同样多：合起来的 28 张再添上相差的 4 张。
2. 32 ÷ 2 = ?   —— 现在两堆一样多了，把 32 张明信片平均分成 2 份，一份就是写得多的那位的。

### ceil-pack-bakery
题面：有 9 个可颂，每袋最多装 4 个。至少要几袋才能全部装下？
1. 9 ÷ 4 = 2        —— 一共 9 个可颂，每袋最多装 4 个，能装满 2 袋。
2. 9 − 4 × 2 = 1    —— 装满的部分从 9 个里减掉，剩下的就是还没袋装的。
3. 2 + 1 = ?        —— 余下的可颂也要有地方放，所以在装满的 2 袋上再加 1 袋。

### left-over-shell
题面：有 29 个贝壳，每 6 个装一桶。装满若干桶后，还剩多少个？
1. 29 ÷ 6 = 4           —— 能装满 4 桶。
2. 29 − 6 × 4 = ?       —— 把装进桶里的都从 29 个里拿走，剩的那几个就是答案（不提商）。
```

## 复现命令

```bash
# 内容自检（含手写剖析 200 次/母题 + 步数对齐）
npm --prefix apps/math-app run check:content

# 条数 / 去重句
node --import apps/math-app/scripts/register-alias.mjs -e "
import { EXPLAIN_COUNT, EXPLAIN_SENTENCE_COUNT, ROUND19_H5 } from './apps/math-app/src/data/word-problem-explains.js'
console.log({ EXPLAIN_COUNT, EXPLAIN_SENTENCE_COUNT, ROUND19_H5 })
"
```

## 复现输出（节选）

```
应用题步数对齐：214/214（100.0%，验收线 90.0%）
手写剖析 150 条覆盖 214/214 个母题：200 次随机取值共 71600 句（去重 19042），
整题思路 / 图示说明 / 每一步都是手写，且判题前不写出答案
全部通过。

{ EXPLAIN_COUNT: 150, EXPLAIN_SENTENCE_COUNT: 517, ROUND19_H5: 'crafted-explain-chain-150' }
```

## 不退化

| 项 | 结果 |
|---|---|
| `check:content` | 全部通过 |
| ROUND18_H4 步数对齐 | 214/214（100%） |
| ROUND17_H4 / ROUND18_H5 | 标记保留，可执行 |
