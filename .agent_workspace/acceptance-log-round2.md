# Round 2 自动化验收记录

记录日期：2026-08-26  
执行入口：`npm run test:acceptance`

## 自动化门槛

| 检查项 | 默认阈值 | 对应标准 |
| --- | ---: | --- |
| 单 App 构建时间 | ≤ 60 秒 | Round 2 构建回归门槛 |
| 首屏 JS gzip | < 256,000 bytes | L-P4 / M-P4（< 250KB gzip） |
| Lighthouse Performance | ≥ 95 | L-P1 / M-P1 |
| Lighthouse Accessibility | ≥ 95 | L-A1 / M-A1 |
| Lighthouse Best Practices | ≥ 90 | 共同质量门槛 |
| axe-core critical 节点 | 0 | 本轮无障碍硬门槛 |

阈值可分别通过 `ACCEPTANCE_MAX_BUILD_SECONDS`、
`ACCEPTANCE_MAX_INITIAL_JS_GZIP_BYTES`、`ACCEPTANCE_MIN_LH_PERFORMANCE`、
`ACCEPTANCE_MIN_LH_ACCESSIBILITY` 与 `ACCEPTANCE_MIN_LH_BEST_PRACTICES`
覆盖。Lighthouse 仅在本机同时存在 Lighthouse CLI 与 Chrome/Chromium 时执行；
跳过时会明确打印 `SKIP`，不会伪造通过结果。axe-core 扫描为必跑项。

## 实测结果

最终执行：`npm run test:acceptance`，退出码 `0`。

| 检查项 | 识字 App | 数学 App | 结果 |
| --- | ---: | ---: | --- |
| 构建时间 | 1,614ms | 2,083ms | PASS |
| 首屏 JS gzip | 93,985 bytes | 138,764 bytes | PASS |
| axe 扫描页面 | 11/11 | 8/8 | PASS |
| axe critical 节点 | 0 | 0 | PASS |
| axe serious 节点 | 48 | 5 | 仅记录 |
| Lighthouse | CLI 不可用，明确 `SKIP` | CLI 不可用，明确 `SKIP` | 未测量 |

运行环境存在 `/usr/local/bin/google-chrome`，但没有 Lighthouse CLI，因此本轮没有
Performance、Accessibility、Best Practices 的有效分数，不能把跳过记作达标。

首轮扫描曾检出 4 个 critical 节点：字表筛选器错误的 tab 语义、数独棋盘错误的
grid 子级语义，以及成就页两个无可访问名称的开关。修正控件语义和开关名称后，
19/19 路由复扫达到 `critical=0`。

## 未达标项与责任模块

- **Lighthouse 分数未测量**：执行环境缺少 Lighthouse CLI；责任模块为验收运行环境。
- **axe serious 尚有 53 个节点**：SOTA 文档 L-A1/M-A1 要求 critical 与 serious
  均为零，所以完整 SOTA 门槛仍未达标。本轮任务指定的硬门槛仅为 critical=0。
  - 识字 App 48 个均为 `color-contrast`，集中在底部导航、字卡拼音和偏旁选择器；
    责任模块为识字主题/组件样式。
  - 数学 App 5 个均为 `aria-prohibited-attr`，集中在通用答题进度点 `.dots`；
    责任模块为数学 `QuizShell`/进度组件。
