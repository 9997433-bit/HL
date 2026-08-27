Model slug: gpt-sol
# Round 5B 验收记录

> 状态：**功能分支合并前基线已记录** — `check:round5b` 为预期红灯；既有 smoke 与性能门槛另有红灯
> 判定标准：`.agent_workspace/ROUND5B-ACCEPTANCE.md`

记录日期：2026-08-27
基线分支：`cursor/openmoji-integration-9f67`（`3cf37eb`）
回归门禁分支：`cursor/r5b-regression-gate-9f67`

## 0. 基线门禁总览

| # | 门禁 | 命令 | 结果 | 备注 |
| --- | --- | --- | --- | --- |
| G1 | 全量单测 | `npm test` | **FAIL** | 识字 smoke：“家长中心没有徽章墙”；数学未执行 |
| G2 | Round 5 不退化 | `npm run check:round5` | **PASS 12/12** | 0 pending / 0 fail |
| G3 | Round 5B Play | `npm run check:round5b` | **预期 FAIL 0/6** | 其它 R5B 分支尚未合并 |
| G4 | Round 3 全链 | `npm run test:round3` | **FAIL** | 在内层 `npm test` 的同一识字 smoke 处停止 |

## 1. Lighthouse 基线

`test:round3` 因前置 smoke 失败未进入 acceptance。单独运行 `npm run test:acceptance`
时，本机因缺少 Lighthouse CLI 明确输出 `[SKIP]`，其余构建、包体和 axe 门槛通过。
为取得可复现分数，补装临时 Lighthouse `13.4.1` 后，以
`LIGHTHOUSE_BIN=<npx cache>/lighthouse npm run test:acceptance` 复跑。移动端模拟，
Performance / Accessibility / Best Practices 门槛均为 90。

| App | Performance | Accessibility | Best Practices | 判定 |
| --- | ---: | ---: | ---: | --- |
| 识字 | **87** | 100 | 100 | **FAIL（Performance < 90）** |
| 数学 | **84** | 100 | 100 | **FAIL（Performance < 90）** |

同轮附带结果：识字首屏 JS gzip `108,149 bytes`，数学 `102,651 bytes`，均低于
`256,000 bytes`；axe 路由 `20/20` 与识字 `3 × 22` 交互状态均为
`critical=0, serious=0`。

## 2. `check:round5b` 功能分支合并前基线

| 项 | 基线实测 | 待合入能力 |
| --- | --- | --- |
| P1 | FAIL：任务 `0/3`，首页/勾选/完成庆祝均未接线 | 每日冒险 |
| P2 | FAIL：`6/5` 路由，但识字 `0`、数学 `6`，且数学缺点触语音 | 吉祥物扩面 |
| P3 | FAIL：仅数学定义；引用识字 `0` / 数学 `8`；能力与三类使用面不全 | 统一 `useFeedback` |
| P4 | FAIL：无同时满足灰显、剧情、过渡与动效降级的地图 | 地图叙事 |
| P5 | FAIL：4/4 玩法说明已有，但街机视觉与大厅卡片网格未接线 | 街机大厅 |
| P6 | FAIL：双 App 均未检测到递进/节拍及答题接线 | 答对节奏 |

结论：`0/6` 是其它 R5B 功能分支未合并时的预期状态，不表示本回归门禁自身异常。

## 3. 已知基线回归

`npm test`、单独复跑 `npm --prefix apps/literacy-app run smoke`、以及
`npm run test:round3` 三次均复现：

```text
✗ 徽章：学会第一个字就点亮，首页与家长中心都看得见 — 家长中心没有徽章墙
```

单独 smoke 的一次复跑还出现过 `.cel` 等待超时，但后续 `test:round3` 中该项通过，
判定为时序波动；徽章项则是稳定红灯。该问题存在于基线 `3cf37eb`，本分支仅修改
门禁脚本与验收记录。

## 4. 集成分支回填模板

> 回填触发：所有 Round 5B 功能分支合入
> 集成提交：`[待回填 SHA]`
> 回填日期：`[YYYY-MM-DD]`

| # | 门禁 | 期望 | 集成实测 |
| --- | --- | --- | --- |
| G1 | `npm test` | PASS | `[待回填]` |
| G2 | `npm run check:round5` | 12/12 PASS | `[待回填]` |
| G3 | `npm run check:round5b` | 6/6 PASS | `[待回填]` |
| G4 | `npm run test:round3` | PASS | `[待回填]` |
| G5 | Lighthouse 识字 | ≥90 / ≥90 / ≥90 | `[P/A/BP]` |
| G6 | Lighthouse 数学 | ≥90 / ≥90 / ≥90 | `[P/A/BP]` |

集成回填时附上 `check:round5b` 的 P1–P6 输出；若 Lighthouse 相对本页基线下降，
记录分差、受影响指标和责任分支。最终结论填写：

`Round 5B Play Layer 门禁 [PASS/FAIL]；Round 5 与 Round 3 回归 [无/有]退化。`
