# Round 2 FSRS、E2E 与压力测试基线

记录日期：2026-08-26
环境：Linux 6.12.94+ x86_64、Node.js v22.14.0、npm 10.9.7

## FSRS 调度单元测试

命令：

```bash
npm --prefix apps/literacy-app run test:srs
```

结果：**PASS（8/8）**

覆盖初始卡创建、四档评分、首次复习基线、遗忘回退、难度修正与上下限、到期边界、
到期队列筛选/排序、指数保持率，以及 `schedule()` / `dueCards()` 不修改输入对象。
测试使用固定 UTC 时间，不依赖系统时钟或网络。

`apps/literacy-app` 的默认 `test` 链已把该单元测试放在数据校验、生产构建和浏览器冒烟
之前；FSRS 纯函数回归会最先失败并给出具体用例。

## 浏览器 E2E 门禁

命令：

```bash
npm --prefix apps/literacy-app run build
npm --prefix apps/literacy-app run smoke
```

原有 17 条路由和 6 项交互保留，并新增两项硬断言：

1. 从单字页真实提交“认识”评分，确认持久化层生成 FSRS 卡；把“日”设为已到期、
   “月”设为未来到期后，复习筛选必须只显示“日”。
2. 字表声明至少 100 字；首屏不得一次挂载全部卡片；翻页过程中同时挂载不超过
   50 张卡片，且在 20 次翻页内能够覆盖全部字。

这两项探针通过抛错决定退出状态，不把“按钮存在”或说明文字当作功能通过。它们是
Round 2 FSRS 接线、100 字数据和分页实现的合并门禁；单独运行在 Round 1 功能基线上会
按预期失败。

## Round 2 边界压力测试

命令：

```bash
node scripts/stress-test.js
```

结果：**PASS**（固定种子 `20260826`，单次冷运行）

| 探针 | Round 2 规模 | 实测耗时 | 内存/产物 | 完整性 |
| --- | ---: | ---: | ---: | --- |
| 汉字卡片标记生成 | 50,000 张 | 74.77 ms | 堆增量 32.27 MiB；HTML 6.38 MiB | PASS |
| 数学题生成 | 250,000 题 | 21.31 ms | 堆增量 18.25 MiB；约 11,732,476 题/秒 | 0 无效题 |

Round 2 默认预算为单项不超过 2,000 ms、峰值堆增量不超过 128 MiB；静态输入门槛提升为
至少 100 个汉字、80 道数学题和 9 类题型。当前输入为 100 字、85 题、9 类。

环境变量 `STRESS_HANZI_COUNT`、`STRESS_MATH_COUNT`、`STRESS_MAX_DURATION_MS`、
`STRESS_MAX_HEAP_MB`、`STRESS_MIN_HANZI_DATASET`、`STRESS_MIN_MATH_DATASET` 和
`STRESS_MIN_MATH_TYPES` 可用于 CI 分档，但默认值就是 Round 2 门禁。

## 边界说明

1. 50,000 张卡片的字符串标记已达 6.38 MiB；浏览器真实 DOM 的布局和绘制成本更高，
   因此 E2E 另设 50 张同时挂载上限。
2. Node 压力探针不代表浏览器帧率、LCP 或交互延迟；这些指标仍由 Lighthouse 和真机
   性能探针负责。
3. 耗时与堆增量会因硬件和 GC 时机波动；是否通过以预算为准，不要求复现实测小数。
