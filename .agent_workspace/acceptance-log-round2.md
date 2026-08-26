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

首轮实现完成后填写。

## 未达标项与责任模块

首轮实现完成后填写。
