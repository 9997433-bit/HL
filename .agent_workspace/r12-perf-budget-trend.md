Model slug: gpt-5.6-sol-xhigh-fast
# Round 12 mobile Lighthouse 与路由预算趋势

标记：`ROUND12_H6`

## 结论

- 2026-08-28 UTC 在基线 `7c2e6e7` 运行
  `ACCEPTANCE_LH_PROFILE=mobile ACCEPTANCE_EVIDENCE_DIR=.agent_workspace/evidence/r12
  node scripts/lighthouse-ci.mjs`。归档的两份 Lighthouse 12.8.2 原始报告均为
  `formFactor=mobile`：识字 P/A/BP `97/100/100`，数学 `95/100/100`，通过
  Performance `>=95`、Accessibility/Best Practices `>=90` 门槛。
- R11 没有采集 mobile 原始报告；其
  `evidence/r11/math-lighthouse-trend.json` 只冻结了 R8→R9 mobile 与 R10 desktop。
  因此不能虚构 R11→R12 mobile 差值。可比的最近 mobile 样本是 R9：识字
  Performance `98→97`（`-1 pp`），数学 `98→95`（`-3 pp`）。数学刚好在门槛，
  不是性能提升。
- 路由拆包预算有可重建的 R11 基线。分别在 R11 闭合提交 `53d125b` 和 R12
  起点 `7c2e6e7` 独立安装、构建并运行
  `npm --prefix apps/math-app run check:route-budget -- --json`，18/18 组均通过，
  每组 gzip 字节逐项一致，R11→R12 差值全部为 `0 B`。
- 最紧的绝对余量是 `/word-problems` 的 `4,694 B`；最高利用率是首屏 `/` 的
  `90.9%`。后续 R12 功能分支合入后必须复跑，不能拿本分支的零差值替代集成终验。

## mobile Lighthouse 证据

| App | 报告 | formFactor | P / A / BP | R9 P | 可比变化 | 判定 |
|---|---|---|---:|---:|---:|---|
| 识字 | `evidence/r12/lighthouse-literacy-app-mobile.json` | mobile | 97 / 100 / 100 | 98 | -1 pp | PASS |
| 数学 | `evidence/r12/lighthouse-math-app-mobile.json` | mobile | 95 / 100 / 100 | 98 | -3 pp | PASS（门槛边缘） |

两轮报告均由 Lighthouse `12.8.2`、Chrome headless、`simulate` throttling 生成。
归档轮的 benchmark index 为识字 `3300`、数学 `3408.5`，低于 R9 的
`3698.5`、`3782.5`，故耗时指标只用于门禁和方向性观察，不解释成真机性能。
并发负载下的一次隔离复跑曾降到 `91/86`，同时 benchmark index 降到
`2459/1739`；该轮没有作为通过证据归档。这一波动进一步说明 Lighthouse mobile
是实验室仿真，不替代 Android 真机签核。

## R11→R12 路由拆包预算

口径：生产构建后，以 gzip level 9 计算首次进入路由新增的 JS 静态闭包及同名
CSS；首页为 eager app shell，其余为 lazy 路由增量。两次独立构建均使用 Node
`22.14.0`、锁文件安装。两个提交的 `apps/math-app` tree id 同为
`5a18be31efa53f02573cb6e04a9a4fbfdf9e7ae4`，`package-lock.json` blob id 同为
`a7e8a4256509a7e1bddab1c7d3cea895a2b4cb7a`；构建产物哈希与测量字节也逐项一致。

| 路由组 | R11 gzip B | R12 gzip B | Δ | 预算 B | R12 利用率 | 状态 |
|---|---:|---:|---:|---:|---:|---|
| `/` | 89,402 | 89,402 | 0 | 98,304 | 90.9% | PASS |
| `/number-sense`, `/compare` | 7,111 | 7,111 | 0 | 49,152 | 14.5% | PASS |
| `/compose-ten` | 3,606 | 3,606 | 0 | 24,576 | 14.7% | PASS |
| `/daily` | 36,707 | 36,707 | 0 | 49,152 | 74.7% | PASS |
| `/arithmetic`, `/sprint` | 38,414 | 38,414 | 0 | 49,152 | 78.2% | PASS |
| `/column-arithmetic` | 4,117 | 4,117 | 0 | 32,768 | 12.6% | PASS |
| `/geometry` | 4,078 | 4,078 | 0 | 49,152 | 8.3% | PASS |
| `/tangram` | 4,568 | 4,568 | 0 | 32,768 | 13.9% | PASS |
| `/visual-demos` | 4,983 | 4,983 | 0 | 24,576 | 20.3% | PASS |
| `/logic` | 5,088 | 5,088 | 0 | 49,152 | 10.4% | PASS |
| `/memory-pairs` | 5,997 | 5,997 | 0 | 32,768 | 18.3% | PASS |
| `/maze` | 6,973 | 6,973 | 0 | 40,960 | 17.0% | PASS |
| `/sudoku` | 6,282 | 6,282 | 0 | 40,960 | 15.3% | PASS |
| `/word-problems` | 36,266 | 36,266 | 0 | 40,960 | 88.5% | PASS |
| `/skill-graph` | 14,064 | 14,064 | 0 | 32,768 | 42.9% | PASS |
| `/progress` | 9,309 | 9,309 | 0 | 65,536 | 14.2% | PASS |
| `/parent` | 16,569 | 16,569 | 0 | 65,536 | 25.3% | PASS |
| `/privacy` | 2,491 | 2,491 | 0 | 16,384 | 15.2% | PASS |

## 集成终验规则

1. R12 各功能提交合入后重新构建并运行 route-budget 门禁；任何组超预算直接失败。
2. 首屏 `/` 或 `/word-problems` 只要增加，评审必须说明来源；利用率达到 95%
   时先拆包再放行，不等到硬上限才处理。
3. 重新运行 mobile Lighthouse；数学 Performance 必须仍 `>=95`，并优先确认
   当前 `95` 是否在低并发环境可复现。
4. Lighthouse 与路由预算只覆盖 Web 实验室档；Android WebView、触控、音频、
   温升和内存仍按 `ANDROID-DEVICE-CHECKLIST.md` 真机签核。
