# Round 3 全量回归测试基线

记录日期：2026-08-26
环境：Linux 6.12.94+ x86_64、Node.js v22.14.0、npm 10.9.7

## 全量回归入口

```bash
npm run test:round3
```

`test:round3` 按失败即停顺序执行以下门禁：

| 阶段 | 命令 | Round 3 门禁 |
| --- | --- | --- |
| 双 App 功能回归 | `npm test` | 单元/数据校验、生产构建、全路由与交互 smoke 全通过 |
| 双 App 离线回归 | `npm run test:offline` | 关闭 HTTP 服务后仍由 Service Worker 启动并读取预缓存 |
| 最终自动验收 | `npm run test:acceptance` | 构建/首屏包体、Lighthouse（环境可用时）与 axe 门禁全通过 |

识字 FSRS 单测仍固定使用 UTC 时间，覆盖 8 个调度场景；它位于识字默认测试链最前面，
纯函数回归会先于构建和浏览器 smoke 失败。

## Round 3 smoke 增量

| 探针 | Round 2 栏 | Round 3 栏 |
| --- | --- | --- |
| 识字分页 | 至少 100 字；全部可达；同时挂载 ≤ 50 张 | 至少 200 字；全部可达；同时挂载 ≤ 50 张（Round 4 提到 500 字） |
| FSRS 到期卡 | “日”到期可见，“月”未到期不可见 | 保留筛选断言，并要求到期“日”可打开到单字复习页 |
| 数学家长面板 | 未覆盖 | 独立路由、口算家长门、正确率/时长/能力报表、难度/声音/动效/时长设置、导出入口与刷新持久化 |

这些是行为断言，不以按钮或说明文字存在代替通过：分页会逐页收集实际 DOM 中的汉字，
FSRS 会写入真实进度存档，家长面板会提交口算、切换设置并刷新复核。

## 边界压力测试

```bash
node scripts/stress-test.js
```

| 门槛 | Round 2 栏 | Round 3 栏 |
| --- | ---: | ---: |
| 汉字标记生成规模 | 50,000 张 | 100,000 张 |
| 数学题生成规模 | 250,000 题 | 500,000 题 |
| 单项耗时上限 | 2,000 ms | 1,500 ms |
| 峰值堆增量上限 | 128 MiB | 128 MiB |
| 静态汉字数据下限 | 100 字 | 200 字（Round 4 实测 500 字） |
| 静态数学题下限 | 80 题 | 300 题 |
| 数学题型下限 | 9 类 | 9 类 |

Round 2 的单次冷运行基线为：50,000 张汉字卡片 74.77 ms / 32.27 MiB，
250,000 道数学题 21.31 ms / 18.25 MiB，结果 PASS。

Round 3 扩大负载探针在保留旧数据下限（仅用于隔离性能预算）时实测：

| 探针 | Round 3 规模 | 实测耗时 | 内存/产物 | 完整性 |
| --- | ---: | ---: | ---: | --- |
| 汉字卡片标记生成 | 100,000 张 | 166.64 ms | 堆增量 62.82 MiB；HTML 12.77 MiB | PASS |
| 数学题生成 | 500,000 题 | 41.83 ms | 堆增量 38.50 MiB；约 11,953,101 题/秒 | 0 无效题 |

环境变量 `STRESS_HANZI_COUNT`、`STRESS_MATH_COUNT`、`STRESS_MAX_DURATION_MS`、
`STRESS_MAX_HEAP_MB`、`STRESS_MIN_HANZI_DATASET`、`STRESS_MIN_MATH_DATASET` 和
`STRESS_MIN_MATH_TYPES` 可用于诊断分档；不设置时执行表中的 Round 3 发布门禁。

## 基础分支集成状态

基于提交 `99e6197` 实跑新门禁；这记录的是待集成缺口，不是 Round 3 发布通过结论。

| 命令 | 状态 | 结果 |
| --- | --- | --- |
| `npm run test:round3` | FAIL | FSRS 8/8 通过；到期“日”位于锁定单元而不可打开；课程字 106/200，链在识字 smoke 失败即停 |
| 数学 App `npm test` | FAIL | 原有内容校验与 14 项交互通过；`/#/parent` 无口算家长门 |
| `npm run test:offline` | PASS | 服务关闭后识字详情与数学数独均可由 Service Worker 启动 |
| `npm run test:acceptance` | FAIL | 构建/包体通过；axe 为 critical=4、serious=63；环境无 Lighthouse CLI，未执行 Lighthouse |
| `node scripts/stress-test.js` | FAIL | Round 4 已把字库补到 500 字，卡在数学静态题库（85 题 < 300 题门槛） |

## 边界说明

1. Node 压力探针测量字符串标记构造与题目生成，不代表浏览器布局、绘制、LCP 或帧率。
2. 浏览器分页另设 50 张同时挂载上限，避免数据规模达标但一次性创建全部 DOM。
3. 耗时与堆增量会受硬件和 GC 时机影响；以门槛判定为准，不要求复现实测小数。
