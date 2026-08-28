Model slug: gpt-5.6-sol
# Round 11 数学性能趋势与路由拆包预算

标记：`ROUND11_H6`

## 结论

- R8 → R9 的同口径 mobile Lighthouse Performance 从 `0.99` 到 `0.98`
  （`-1` 个百分点），不是提升；但仍高于 `0.95` 门槛。
- 同口径的 FCP / LCP / TBT 分别变化 `+0.12% / +0.37% / +4.32%`，
  均在相对退化 `<=10%` 与绝对上限内；总传输量增加 `148 B`（`+0.12%`）。
- R10 desktop Performance 为 `1.00`、LCP `448.29 ms`、TBT `0 ms`。
  desktop 与 mobile 不做跨 profile 差分，避免把设备仿真差异当成优化收益。
- 数学 App 的 `/` 首页维持 eager，其余 19 条非重定向业务路径归入 17 个
  lazy chunk 组；门禁按“首次进入路由新增的 JS 静态依赖 + 同名 CSS”的
  gzip 总和计算。

机读冻结记录：
`.agent_workspace/evidence/r11/math-lighthouse-trend.json`。记录含三份原始
Lighthouse 报告的 SHA-256、采集口径、原始值、差值、预算及 PASS/FAIL。

## Lighthouse 趋势口径

仅当 Lighthouse 版本和 `formFactor` 相同才计算趋势。本轮可比较序列为
Lighthouse `12.8.2` 的 R8 mobile → R9 mobile；R10 desktop 只冻结为独立基线。

数学公式：

```text
分数差（百分点） = (newScore - oldScore) × 100
相对变化（%）    = (newValue - oldValue) ÷ oldValue × 100
```

对耗时、CLS 与字节数，正值代表退化。零基线采用：`0 → 0 = 0%`；
`0 → 非零` 不计算百分比，必须单独通过绝对上限。

| 指标 | R8 mobile | R9 mobile | 变化 | R9 绝对预算 | 相对退化预算 | 状态 |
|---|---:|---:|---:|---:|---:|---|
| Performance | 0.99 | 0.98 | -1 pp | >= 0.95 | <= 3 pp | PASS |
| FCP | 1202.36 ms | 1203.80 ms | +0.12% | <= 1800 ms | <= 10% | PASS |
| LCP | 1851.45 ms | 1858.25 ms | +0.37% | <= 2500 ms | <= 10% | PASS |
| Speed Index | 1202.36 ms | 1203.80 ms | +0.12% | <= 3000 ms | <= 10% | PASS |
| TBT | 124.09 ms | 129.45 ms | +4.32% | <= 200 ms | <= 10% | PASS |
| CLS | 0 | 0 | 0% | <= 0.1 | 0 → 0 | PASS |
| TTI | 1856.24 ms | 1863.50 ms | +0.39% | <= 3500 ms | <= 10% | PASS |
| 总传输量 | 124859 B | 125007 B | +0.12% | <= 184320 B | <= 5% | PASS |

## 路由拆包预算

`apps/math-app/scripts/check-route-budget.mjs` 直接检查生产 `dist`：

1. 首页 app shell 与 `HomeView` 同步加载，gzip 预算 `96 KiB`；
2. 每个业务视图必须保持 `() => import(...)`，否则门禁失败；
3. 每个 lazy 路由必须恰好产出一个命名块；
4. 冷启动进入该路由时，累计该块、静态 JS 依赖及对应 CSS，再扣除 app shell
   已加载文件；以下预算均指该增量的 gzip level 9 字节数；
5. `/compare`、`/sprint` 等复用同一视图的路径共享同一预算组，不重复制造块。

| 路径 | 构建块 | gzip 上限 |
|---|---|---:|
| `/` | app shell + HomeView（eager） | 96 KiB |
| `/number-sense`, `/compare` | NumberSenseView | 48 KiB |
| `/compose-ten` | ComposeTenView | 24 KiB |
| `/daily` | DailyView | 48 KiB |
| `/arithmetic`, `/sprint` | ArithmeticView | 48 KiB |
| `/column-arithmetic` | ColumnArithmeticView | 32 KiB |
| `/geometry` | GeometryView | 48 KiB |
| `/tangram` | TangramView | 32 KiB |
| `/visual-demos` | VisualDemosView | 24 KiB |
| `/logic` | LogicView | 48 KiB |
| `/memory-pairs` | MemoryPairsView | 32 KiB |
| `/maze` | MazeView | 40 KiB |
| `/sudoku` | SudokuView | 40 KiB |
| `/word-problems` | WordProblemsView | 40 KiB |
| `/skill-graph` | SkillGraphView | 32 KiB |
| `/progress` | ProgressView | 64 KiB |
| `/parent` | ParentView | 64 KiB |
| `/privacy` | PrivacyView | 16 KiB |

数学 App 的 `test` 链已在生产构建后的原有首屏 bundle gate 之后执行该路由门禁。

## 复现

```bash
node scripts/check-r11-perf-trend.mjs
npm --prefix apps/math-app run build
npm --prefix apps/math-app run check:route-budget
npm run check:round11 -- --json
npm run check:round10
```

更新 Lighthouse 原始报告后，必须人工确认 profile/版本与预算，再运行
`node scripts/check-r11-perf-trend.mjs --write` 重建冻结 evidence；默认命令会校验
原报告与 evidence 逐字节一致，不允许报告漂移后继续沿用旧趋势。
