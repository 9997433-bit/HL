# Round 17 验收回填日志

> 编排启动基线：功能未合入时 `check:round17` 预期红  
> 目标：H1–H8 全绿；`check:round16` 保持 8/8

## 启动基线

| 门禁 | 实测 | 证据 |
|---|---|---|
| `npm run check:round17` | **2/8**（H7 继承 r13 报告 + H8） | `evidence/r17/baseline-check.txt` |
| `npm run check:round16` | 应 8/8 | 继承 R16 编排 |

| 探针 | 状态 | Owner |
|---|---|---|
| H1 差距续表 | ⬜ | r17-hongen-gap-audit |
| H2 富 Play ≥900 | ⬜ | r17-play-rich-900 |
| H3 学演示 ≥27 | ⬜ | r17-math-learn-demo-plus |
| H4 精品剖析 ≥20 | ⬜ | r17-wp-explain-hand |
| H5 学伴关键接线 | ⬜ | r17-mascot-wire |
| H6 走查证据包 | ⬜ | r17-walkthrough-bundle |
| H7 真机/模拟闭环 | ⬜ | r17-regression-gate |
| H8 往轮 round16 | ⬜ | r17-regression-gate |

## 修订记录

| 日期 | 变更 |
|---|---|
| 2026-08-28 | v1.0 编排启动，十路发射 |

## 十路子代理

| # | 模型 | 分支 |
|---|---|---|
| 1 | fable | r17-arch-contracts |
| 2 | fable | r17-hongen-gap-audit |
| 3 | fable | r17-acceptance-spec |
| 4 | opus-fast | r17-play-rich-900 |
| 5 | opus-fast | r17-math-learn-demo-plus |
| 6 | opus-fast | r17-wp-explain-hand |
| 7 | opus-fast | r17-mascot-wire |
| 8 | opus-fast | r17-walkthrough-bundle |
| 9 | gpt-sol | r17-smoke-tests |
| 10 | gpt-sol | r17-regression-gate |
